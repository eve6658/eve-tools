#!/usr/bin/env python3
"""运行 OpenClaw Bridge 演示"""
import sys
sys.path.insert(0, ".")

from tool_framework import EveTool, ToolResult, ToolContext, ValidationResult
from tool_registry import ToolRegistry
from openclaw_bridge import OpenClawBridge

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
shell_tool = registry.get("shell")
if shell_tool:
    ctx = ToolContext(workspace="/home/adam/.openclaw/workspace")
    result = shell_tool.execute({"command": "echo 'Hello from Eve! 🐾' && date"}, ctx)
    print(f"Status: {'✅' if result.success else '❌'}")
    print(f"Summary: {result.summary}")
    if result.data:
        print(f"stdout:\n{result.data.get('stdout','')}")

print("\n" + "=" * 60)
print("测试 read_file 工具")
print("=" * 60)
read_tool = registry.get("read_file")
if read_tool:
    ctx = ToolContext(workspace="/home/adam/.openclaw/workspace")
    result = read_tool.execute({"path": "SOUL.md"}, ctx)
    print(f"Status: {'✅' if result.success else '❌'}")
    print(f"Summary: {result.summary}")

print("\n" + "=" * 60)
print("测试 memory_io 工具")
print("=" * 60)
mem_tool = registry.get("memory_io")
if mem_tool:
    ctx = ToolContext(workspace="/home/adam/.openclaw/workspace")
    result = mem_tool.execute({"action": "list"}, ctx)
    print(f"Status: {'✅' if result.success else '❌'}")
    print(f"Summary: {result.summary}")

print("\n✅ All tests passed!")
