"""
Hook 系统 — 工具调用前后的自动钩子

参考 ECC (Everything Claude Code) 的 Hook 概念：
- tools 在执行前/后触发钩子
- matcher 用简单表达式过滤
- command/callback 执行具体逻辑

对应 Claude Code 的 bashPermissions.ts hooks + settings.json hook 配置。
"""

import re
import time
import json
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Optional


class HookType(Enum):
    PRE_TOOL = "pre_tool"        # 工具调用前
    POST_TOOL = "post_tool"      # 工具调用后
    ON_ERROR = "on_error"        # 出错时
    ON_MESSAGE = "on_message"    # 收到消息时
    SESSION_START = "session_start"
    SESSION_END = "session_end"


@dataclass
class HookEvent:
    """Hook 触发事件"""
    hook_type: HookType
    tool_name: str = ""
    tool_input: dict = None
    tool_result: dict = None
    success: bool = True
    context: dict = None
    timestamp: float = field(default_factory=time.time)


class Hook:
    """单个 Hook 定义"""

    def __init__(
        self,
        name: str,
        hook_type: HookType,
        matcher: str,
        callback: Callable = None,
        command: str = "",
        enabled: bool = True,
    ):
        self.name = name
        self.hook_type = hook_type
        self.matcher = matcher
        self.callback = callback
        self.command = command
        self.enabled = enabled
        self.trigger_count = 0

    def matches(self, event: HookEvent) -> bool:
        """检查事件是否匹配此 hook 的 matcher"""
        if not self.enabled:
            return False
        if self.hook_type != event.hook_type:
            return False
        return self._eval_matcher(event)

    def _eval_matcher(self, event: HookEvent) -> bool:
        """
        简单表达式求值。

        支持的语法（对应 ECC hooks.matcher）：
        - 'tool == "shell"'
        - 'tool_input.file_path matches "\\.py$"'
        - 'success == False'
        - 'tool == "shell" || tool == "read_file"'
        """
        expr = self.matcher.strip()

        # 处理 && 和 || 逻辑
        if " && " in expr:
            parts = expr.split(" && ")
            return all(self._eval_single(part.strip(), event) for part in parts)
        elif " || " in expr:
            parts = expr.split(" || ")
            return any(self._eval_single(part.strip(), event) for part in parts)

        return self._eval_single(expr, event)

    def _eval_single(self, expr: str, event: HookEvent) -> bool:
        """求值单个条件"""

        # equality: tool == "shell"
        m = re.match(r'(\w+)\s*==\s*"([^"]*)"', expr)
        if m:
            field_name, expected = m.group(1), m.group(2)
            actual = getattr(event, field_name, "")
            return actual == expected

        # matches (regex): tool_input.file_path matches "\\.py$"
        m = re.match(r'(\w+(?:\.\w+)*)\s+matches\s+"([^"]*)"', expr)
        if m:
            field_path, pattern = m.group(1), m.group(2)
            val = self._resolve_field(field_path, event)
            return bool(re.search(pattern, val)) if val else False

        # equality direct: success == True/False
        m = re.match(r'(\w+)\s*==\s*(True|true|False|false)', expr)
        if m:
            field_name, expected = m.group(1), m.group(2).lower() == "true"
            actual = getattr(event, field_name, True)
            return actual == expected

        return True  # unknown matcher defaults to true

    def _resolve_field(self, path: str, event: HookEvent) -> str:
        """解析点分隔的字段路径，如 tool_input.file_path"""
        obj = event
        for part in path.split("."):
            if isinstance(obj, dict):
                obj = obj.get(part, "")
            else:
                obj = getattr(obj, part, "")
        return str(obj) if obj else ""

    def execute(self, event: HookEvent) -> dict:
        """执行 hook 回调"""
        self.trigger_count += 1
        if self.callback:
            return self.callback(event)
        return {"hook": self.name, "executed": True}


class HookManager:
    """
    Hook 管理器。

    对应 ECC 的 hook 系统：
    - 注册/触发/列出 hook
    - 简单 matcher 表达式
    - 内置 hook（权限检查、审计日志、频率限制）
    """

    def __init__(self):
        self.hooks: dict[str, Hook] = {}
        self.audit_log: list[dict] = []
        self._max_audit = 1000

    # ============================================================
    # 注册 + 触发
    # ============================================================

    def register(self, hook: Hook):
        """注册 hook"""
        self.hooks[hook.name] = hook

    def unregister(self, name: str):
        """移除 hook"""
        self.hooks.pop(name, None)

    def trigger(self, event: HookEvent) -> list[dict]:
        """触发所有匹配的 hook，返回结果列表"""
        results = []
        for hook in self.hooks.values():
            if hook.matches(event):
                result = hook.execute(event)
                results.append(result)

        # 写入审计日志
        self._audit(event, results)
        return results

    # ============================================================
    # 内置 Hook
    # ============================================================

    def add_audit_hook(self):
        """审计日志 hook（记录所有工具调用）"""
        def audit_callback(event: HookEvent) -> dict:
            return {
                "tool": event.tool_name,
                "type": event.hook_type.value,
                "success": event.success,
                "time": time.strftime("%H:%M:%S"),
            }

        self.register(Hook(
            name="audit_log",
            hook_type=HookType.POST_TOOL,
            matcher="",
            callback=audit_callback,
        ))

    def add_rate_limit_hook(self, max_calls: int = 30, window_seconds: int = 60):
        """频率限制 hook"""
        call_times: list[float] = []

        def rate_check(event: HookEvent) -> dict:
            now = time.time()
            # 清理过期记录
            while call_times and call_times[0] < now - window_seconds:
                call_times.pop(0)

            if len(call_times) >= max_calls:
                return {
                    "blocked": True,
                    "message": f"频率限制: {window_seconds}秒内最多{max_calls}次调用",
                }

            call_times.append(now)
            return {"blocked": False}

        self.register(Hook(
            name="rate_limit",
            hook_type=HookType.PRE_TOOL,
            matcher="",
            callback=rate_check,
        ))

    def add_sensitive_filter_hook(self, patterns: list[str] = None):
        """敏感信息过滤 hook"""
        if patterns is None:
            patterns = [r'sk-[a-zA-Z0-9]{20,}', r'password\s*[:=]\s*\S+']

        def filter_check(event: HookEvent) -> dict:
            if event.tool_name == "shell" and event.tool_input:
                cmd = str(event.tool_input.get("command", ""))
                for pat in patterns:
                    if re.search(pat, cmd):
                        return {
                            "blocked": True,
                            "message": f"命令包含敏感信息，已阻止",
                        }
            return {"blocked": False}

        self.register(Hook(
            name="sensitive_filter",
            hook_type=HookType.PRE_TOOL,
            matcher="",
            callback=filter_check,
        ))

    # ============================================================
    # 审计日志
    # ============================================================

    def _audit(self, event: HookEvent, results: list[dict]):
        """写入审计日志"""
        entry = {
            "type": event.hook_type.value,
            "tool": event.tool_name,
            "success": event.success,
            "hooks_fired": len(results),
            "time": time.time(),
        }
        self.audit_log.append(entry)
        if len(self.audit_log) > self._max_audit:
            self.audit_log = self.audit_log[-self._max_audit:]

    def get_audit_log(self, n: int = 10) -> list[dict]:
        """获取最近 n 条审计日志"""
        return self.audit_log[-n:]

    # ============================================================
    # 查询
    # ============================================================

    def list_hooks(self) -> list[dict]:
        """列出所有 hook"""
        return [
            {"name": h.name, "type": h.hook_type.value, "matcher": h.matcher, "enabled": h.enabled}
            for h in self.hooks.values()
        ]

    def enable(self, name: str):
        if name in self.hooks:
            self.hooks[name].enabled = True

    def disable(self, name: str):
        if name in self.hooks:
            self.hooks[name].enabled = False
