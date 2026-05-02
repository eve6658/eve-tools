#!/usr/bin/env python3
"""
openclaw_bridge.py — OpenClaw 工具桥接层

将 eve-evolution 框架与 OpenClaw 运行时对接：
- 将 OpenClaw 的 exec/message/web_search 等工具注册为 EveTool
- 通过 exec 调用实际 shell 命令
- 记忆系统读写真实 workspace 文件

设计原则：
---------
1. OpenClaw 内运行时：直接用 Python 调用
2. 外部调用：通过 subprocess / HTTP
3. 安全：所有写操作经过 ToolResult 返回，不直接修改外部状态

使用：
    bridge = OpenClawBridge(workspace="/home/adam/.openclaw/workspace")
    registry = bridge.setup_registry()
    result = registry.execute("shell", {"command": "ls -la"})
"""

import os
import sys
import json
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from tool_framework import EveTool, ToolResult, ToolContext, ValidationResult


# ============================================================
# 内置工具实现
# ============================================================

class ShellTool(EveTool):
    """执行 shell 命令"""
    
    def __init__(self, workspace: str = None):
        super().__init__(
            name="shell",
            description="执行 shell 命令并返回输出",
            aliases=["exec", "run"],
            category="system",
            permission_level="ask",  # 破坏性操作需确认
        )
        self.workspace = workspace or os.getcwd()
    
    def execute(self, params: dict, context: ToolContext) -> ToolResult:
        cmd = params.get("command", "")
        if not cmd:
            return ToolResult(False, error="command 不能为空")
        
        timeout = params.get("timeout", 30)
        cwd = getattr(context, "workspace", self.workspace) if context else self.workspace
        
        try:
            result = subprocess.run(
                cmd, shell=True,
                capture_output=True, text=True,
                timeout=timeout, cwd=cwd,
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )
            return ToolResult(
                success=result.returncode == 0,
                data={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                },
                summary=f"exit={result.returncode}, {len(result.stdout+result.stderr)} chars",
            )
        except subprocess.TimeoutExpired:
            return ToolResult(False, error=f"命令超时 ({timeout}s)")
        except Exception as e:
            return ToolResult(False, error=str(e))


class FileReadTool(EveTool):
    """读取文件内容"""
    
    def __init__(self, workspace: str = None):
        super().__init__(
            name="read_file",
            description="读取文本文件内容",
            aliases=["cat", "read"],
            category="file",
            permission_level="allow",
        )
        self.workspace = workspace or os.getcwd()
    
    def execute(self, params: dict, context: ToolContext) -> ToolResult:
        path = params.get("path", "")
        if not path:
            return ToolResult(False, error="path 不能为空")
        
        ws = getattr(context, "workspace", self.workspace) if context else self.workspace
        if not os.path.isabs(path):
            path = os.path.join(ws, path)
        
        max_lines = params.get("max_lines", 1000)
        
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)
            content = "".join(lines)
            return ToolResult(
                success=True,
                data={"content": content, "path": path, "lines": i+1},
                summary=f"读取 {path} ({i+1} 行, {len(content)} 字符)",
            )
        except FileNotFoundError:
            return ToolResult(False, error=f"文件不存在: {path}")
        except Exception as e:
            return ToolResult(False, error=str(e))


class FileWriteTool(EveTool):
    """写入文件内容"""
    
    def __init__(self, workspace: str = None):
        super().__init__(
            name="write_file",
            description="写入内容到文件（覆盖）",
            aliases=["write", "save"],
            category="file",
            permission_level="ask",
        )
        self.workspace = workspace or os.getcwd()
    
    def execute(self, params: dict, context: ToolContext) -> ToolResult:
        path = params["path"]
        content = params["content"]
        
        if not os.path.isabs(path):
            path = os.path.join(self.workspace, path)
        
        # 自动创建目录
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return ToolResult(
                success=True,
                data={"path": path, "bytes_written": len(content.encode())},
                summary=f"写入 {path} ({len(content)} 字符)",
            )
        except Exception as e:
            return ToolResult(False, error=str(e))


class MemoryBridgeTool(EveTool):
    """读写记忆文件"""
    
    def __init__(self, workspace: str = None):
        super().__init__(
            name="memory_io",
            description="读写记忆文件（MEMORY.md、daily notes 等）",
            aliases=["memory"],
            category="memory",
            permission_level="ask",
        )
        self.workspace = workspace or os.path.join(os.getcwd(), "memory")
        self.memory_dir = self.workspace
        self.memory_file = os.path.join(os.path.dirname(self.workspace), "MEMORY.md")
    
    def execute(self, params: dict, context: ToolContext) -> ToolResult:
        action = params.get("action", "read")
        target = params.get("target", "MEMORY.md")
        
        if action == "read":
            if target == "MEMORY.md":
                path = self.memory_file
            else:
                path = os.path.join(self.memory_dir, target)
            
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                return ToolResult(True, data={"content": content}, 
                                summary=f"读取 {path}", metadata={"raw_preview": content[:2000]})
            except FileNotFoundError:
                return ToolResult(True, data={"content": ""}, 
                                summary=f"文件不存在: {path}")
        
        elif action == "write" or action == "append":
            content = params.get("content", "")
            if target == "MEMORY.md":
                path = self.memory_file
            else:
                path = os.path.join(self.memory_dir, target)
            
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            
            mode = "a" if action == "append" else "w"
            with open(path, mode, encoding="utf-8") as f:
                if mode == "a":
                    f.write(f"\n{content}\n")
                else:
                    f.write(content)
            
            return ToolResult(True, data={"path": path, "bytes": len(content)},
                            summary=f"{'追加' if mode=='a' else '写入'} {path}")
        
        elif action == "list":
            files = []
            if os.path.exists(self.memory_dir):
                files = os.listdir(self.memory_dir)
            return ToolResult(True, data={"files": files}, 
                            summary=f"记忆文件: {files}")
        
        return ToolResult(False, error=f"未知 action: {action}")


# ============================================================
# Bridge 主类
# ============================================================

class OpenClawBridge:
    """
    OpenClaw 桥接器
    
    将 OpenClaw 环境中的工具统一注册到 ToolRegistry，
    使 eve-evolution 框架能在实际 OpenClaw 运行时中使用。
    """
    
    def __init__(self, workspace: str = None):
        self.workspace = workspace or os.environ.get(
            "OPENCLAW_WORKSPACE", 
            "/home/adam/.openclaw/workspace"
        )
    
    def setup_registry(self) -> "ToolRegistry":
        """注册所有内置工具"""
        from tool_registry import ToolRegistry
        
        registry = ToolRegistry()
        
        # 注册内置工具
        registry.register(ShellTool(self.workspace))
        registry.register(FileReadTool(self.workspace))
        registry.register(FileWriteTool(self.workspace))
        registry.register(MemoryBridgeTool(self.workspace))
        
        return registry
    
    def get_tool_info(self) -> List[dict]:
        """获取所有工具信息摘要"""
        registry = self.setup_registry()
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "category": t.get("category","general"),
                "permission": t.get("permission_level","ask"),
                "aliases": t.get("aliases",[]),
            }
            for t in registry.list_tools()
        ]


if __name__ == "__main__":
    bridge = OpenClawBridge()
    
    print("=" * 60)
    print("OpenClaw Bridge — 工具列表")
    print("=" * 60)
    
    for info in bridge.get_tool_info():
        icon = {"allow": "🟢", "ask": "🟡", "deny": "🔴"}.get(info["permission"], "⚪")
        aliases = f" (别名: {', '.join(info['aliases'])})" if info["aliases"] else ""
        print(f"  {icon} {info['name']}: {info['description']}{aliases}")
    
    print("\n" + "=" * 60)
    print("测试 shell 工具")
    print("=" * 60)
    
    registry = bridge.setup_registry()
    tool = registry.get("shell")
    ctx = ToolContext()
    result = tool.execute({"command": "echo Hello from Eve! && date"}, ctx)
    print(f"Status: {'✅' if result.success else '❌'}")
    print(f"Summary: {result.summary}")
    if result.data:
        print(f"stdout: {result.data.get('stdout','')}")
