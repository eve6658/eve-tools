"""
Kairos Lite — 轻量版主动代理系统

参考 Claude Code 的 Kairos 模式（精简版）：
- 定时（心跳）触发
- 简单场景检测
- 主动告知用户重要信息

区别于 BriefTool：
- BriefTool 是工具（LLM 调用发送消息）
- Kairos Lite 是定时检查逻辑（自动运行）
- 两者配合：Kairos Lite 检测 → BriefTool 发送
"""

import time
import os
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class KairosCheck:
    """Kairos 检查定义"""
    name: str
    check_fn: Callable[[], Optional[str]]  # 返回 None = 无消息，返回 str = 要发送
    interval: float = 300  # 检查间隔（秒）
    last_run: float = 0.0
    enabled: bool = True
    
    def should_run(self) -> bool:
        return self.enabled and (time.time() - self.last_run >= self.interval)
    
    def run(self) -> Optional[str]:
        self.last_run = time.time()
        try:
            return self.check_fn()
        except Exception:
            return None


class KairosLite:
    """
    轻量版 Kairos 系统。
    
    对应 Claude Code 的 Kairos 模式核心：
    - 定时检查工作区状态
    - 发现值得告知的事情
    - 通过 BriefTool 发送
    
    内置检查：
    - workspace_changes: 工作区文件变化
    - git_status: Git 状态变化
    - error_log: 错误日志
    - idle_reminder: 空闲提醒
    """
    
    def __init__(self, workspace: str = "."):
        self.workspace = workspace
        self.checks: dict[str, KairosCheck] = {}
        self.enabled = True
        self._last_state: dict = {}
        
        # 注册默认检查
        self._register_default_checks()
    
    def _register_default_checks(self):
        """注册默认检查"""
        self.register(KairosCheck(
            name="workspace_changes",
            check_fn=self._check_workspace_changes,
            interval=300,  # 5分钟
        ))
        
        self.register(KairosCheck(
            name="git_status",
            check_fn=self._check_git_status,
            interval=600,  # 10分钟
        ))
        
        self.register(KairosCheck(
            name="idle_reminder",
            check_fn=self._check_idle_reminder,
            interval=1800,  # 30分钟
        ))
    
    def register(self, check: KairosCheck):
        """注册检查"""
        self.checks[check.name] = check
    
    def run_checks(self) -> list[str]:
        """
        运行所有到期的检查。
        返回需要发送给用户的消息列表。
        """
        if not self.enabled:
            return []
        
        messages = []
        for check in self.checks.values():
            if check.should_run():
                result = check.run()
                if result:
                    messages.append(f"[{check.name}] {result}")
        
        return messages
    
    def is_active(self) -> bool:
        """Kairos 是否激活（对应 getKairosActive()）"""
        return self.enabled and len(self.checks) > 0
    
    # ============================================================
    # 内置检查
    # ============================================================
    
    def _check_workspace_changes(self) -> Optional[str]:
        """检查工作区文件变化"""
        current_state = {}
        
        for root, dirs, files in os.walk(self.workspace):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            
            for f in files:
                if f.startswith(".") or f.endswith(".pyc"):
                    continue
                filepath = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(filepath)
                    relpath = os.path.relpath(filepath, self.workspace)
                    current_state[relpath] = mtime
                except OSError:
                    continue
        
        if not self._last_state:
            # 首次运行，只记录状态
            self._last_state = current_state
            return None
        
        # 比较变化
        new_files = [f for f in current_state if f not in self._last_state]
        modified = [f for f in current_state 
                    if f in self._last_state and current_state[f] > self._last_state[f]]
        
        self._last_state = current_state
        
        if not new_files and not modified:
            return None
        
        parts = []
        if new_files:
            files_str = ", ".join(new_files[:3])
            parts.append(f"新文件: {files_str}")
        if modified:
            files_str = ", ".join(modified[:3])
            parts.append(f"修改: {files_str}")
        
        return " | ".join(parts)
    
    def _check_git_status(self) -> Optional[str]:
        """检查 Git 状态"""
        try:
            result = __import__("subprocess").run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=10,
                cwd=self.workspace,
            )
            if result.returncode != 0:
                return None  # 不是 git 仓库
            
            output = result.stdout.strip()
            if not output:
                return None
            
            lines = output.split("\n")
            if len(lines) == 1:
                return f"Git: {lines[0]}"
            return f"Git: {len(lines)} 个文件有变化"
        except Exception:
            return None
    
    def _check_idle_reminder(self) -> Optional[str]:
        """空闲提醒"""
        # 检查最近是否有活动
        last_activity = self._last_state.get("__last_activity__", 0)
        idle_time = time.time() - last_activity
        
        if idle_time > 3600:  # 1小时无活动
            return "已经工作很久了，要不要休息一下？"
        
        return None
    
    def touch_activity(self):
        """更新活动时间"""
        self._last_state["__last_activity__"] = time.time()
    
    # ============================================================
    # 配置
    # ============================================================
    
    def set_check_interval(self, name: str, interval: float):
        """设置检查间隔"""
        if name in self.checks:
            self.checks[name].interval = interval
    
    def enable_check(self, name: str):
        if name in self.checks:
            self.checks[name].enabled = True
    
    def disable_check(self, name: str):
        if name in self.checks:
            self.checks[name].enabled = False
    
    def list_checks(self) -> list[dict]:
        """列出所有检查"""
        return [
            {
                "name": c.name,
                "interval": c.interval,
                "last_run": c.last_run,
                "enabled": c.enabled,
            }
            for c in self.checks.values()
        ]
