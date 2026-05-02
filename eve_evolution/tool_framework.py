"""
tool_framework.py — Eve 统一工具接口框架

设计思路：
---------
参考 Claude Code 的 buildTool() 模式。在 Claude Code 中，每个工具（Read、Write、Bash、Edit 等）
都遵循统一的接口规范：接收参数、执行操作、返回结构化结果、提供摘要。

核心设计理念：
1. **结构化结果** — 所有工具返回 ToolResult，包含 success/data/summary/error/metadata
   → 对应 Claude Code 的 tool_result 结构
2. **权限检查** — 每个工具可声明自己的安全属性（只读/破坏性/并发安全）
   → 对应 Claude Code 的 permission system
3. **摘要机制** — 每个工具可自定义摘要生成，控制 token 消耗
   → 对应 Claude Code 的 result summarization
4. **验证机制** — 执行前验证参数合法性
   → 对应 Claude Code 的 input validation

与 Claude Code 的对应关系：
- ToolResult ≈ Claude Code 的 ToolResult（结构化返回）
- EveTool ≈ Claude Code 的 BuiltInTool 基类
- PermissionResult ≈ Claude Code 的 ToolPermissions
- ValidationResult ≈ Claude Code 的 tool input schema validation
- ToolContext ≈ Claude Code 的 ToolContext（注入运行时依赖）
"""

from __future__ import annotations

import time
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


# ============================================================
# 权限枚举
# ============================================================

class PermissionResult(Enum):
    """
    权限检查结果。
    
    对应 Claude Code 的 permission system：
    - ALLOW: 工具可直接执行（如只读操作）
    - DENY: 工具被禁止执行（如策略限制）
    - ASK: 需要用户确认（如破坏性操作）
    """
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


# ============================================================
# 验证结果
# ============================================================

@dataclass
class ValidationResult:
    """
    参数验证结果。
    
    对应 Claude Code 的 input schema validation。
    每个工具在 execute 前会调用 validate() 检查参数。
    """
    valid: bool
    errors: list[str] = field(default_factory=list)
    
    def __bool__(self) -> bool:
        return self.valid


# ============================================================
# 工具执行结果
# ============================================================

@dataclass
class ToolResult:
    """
    工具执行结果的统一结构。
    
    对应 Claude Code 的 tool_result：
    - success: 执行是否成功
    - data: 实际返回数据（任意类型）
    - summary: 给 LLM 的简短摘要（控制 token 用量的关键）
    - error: 错误信息（如果有）
    - metadata: 附加元数据（执行时间、token 消耗等）
    
    设计要点：
    - summary 是核心字段，LLM 只看到 summary 而非完整 data
    - 这样可以有效控制上下文窗口不被工具返回值撑爆
    """
    success: bool
    data: Any = None
    summary: str = ""
    error: str | None = None
    metadata: dict = field(default_factory=dict)
    
    @classmethod
    def ok(cls, data: Any = None, summary: str = "", metadata: dict = None) -> ToolResult:
        """快捷创建成功结果"""
        return cls(
            success=True,
            data=data,
            summary=summary or f"操作成功，返回 {type(data).__name__}",
            metadata=metadata or {},
        )
    
    @classmethod
    def fail(cls, error: str, summary: str = "", metadata: dict = None) -> ToolResult:
        """快捷创建失败结果"""
        return cls(
            success=False,
            error=error,
            summary=summary or f"操作失败: {error}",
            metadata=metadata or {},
        )
    
    def to_dict(self) -> dict:
        """序列化为字典"""
        return asdict(self)


# ============================================================
# 工具上下文（运行时依赖注入）
# ============================================================

@dataclass
class ToolContext:
    """
    工具运行时上下文。
    
    对应 Claude Code 的 ToolContext，注入运行时需要的依赖：
    - workspace: 工作目录路径
    - session_id: 当前会话 ID
    - env: 环境变量
    - user_id: 用户标识
    - extra: 其他扩展字段
    
    设计思路：工具不直接访问全局状态，所有依赖通过 context 注入，
    这样便于测试和隔离。
    """
    workspace: str = "."
    session_id: str = ""
    env: dict = field(default_factory=dict)
    user_id: str = ""
    extra: dict = field(default_factory=dict)


# ============================================================
# 抽象工具基类
# ============================================================

class EveTool(ABC):
    """
    Eve 统一工具接口 — 所有工具的基类。
    """
    
    def __init__(self, name: str = "", description: str = "",
                 aliases: list = None, search_hint: str = "",
                 category: str = "general", permission_level: str = "ask",
                 is_read_only: bool = True, is_destructive: bool = False,
                 is_concurrency_safe: bool = True, max_result_size: int = 50000):
        self.name = name
        self.description = description
        self.aliases = aliases or []
        self.search_hint = search_hint
        self.category = category
        self.permission_level = permission_level
        self.is_read_only = is_read_only
        self.is_destructive = is_destructive
        self.is_concurrency_safe = is_concurrency_safe
        self.max_result_size = max_result_size
    
    @abstractmethod
    def execute(self, args: dict, context: ToolContext) -> ToolResult:
        """
        执行工具操作。
        
        这是每个工具必须实现的核心方法。
        对应 Claude Code BuiltInTool.execute()。
        
        Args:
            args: 工具参数字典
            context: 运行时上下文
            
        Returns:
            ToolResult: 结构化执行结果
        """
        ...
    
    def validate(self, args: dict) -> ValidationResult:
        """
        验证参数合法性。
        
        在 execute 之前调用。默认接受所有参数。
        子类应覆盖此方法实现具体的验证逻辑。
        
        对应 Claude Code 的 tool input schema validation。
        """
        return ValidationResult(valid=True)
    
    def check_permissions(self, args: dict, context: ToolContext) -> PermissionResult:
        """
        检查工具执行权限。
        
        默认策略：
        - 只读工具 → ALLOW
        - 破坏性工具 → ASK（需用户确认）
        - 其他 → ALLOW
        
        对应 Claude Code 的 permission check flow。
        """
        if self.is_destructive:
            return PermissionResult.ASK
        if self.is_read_only:
            return PermissionResult.ALLOW
        return PermissionResult.ALLOW
    
    def summarize(self, args: dict, result: ToolResult) -> str:
        """
        生成结果摘要（给 LLM 的简短描述）。
        
        默认返回 ToolResult.summary。
        子类可覆盖以生成更精准的摘要。
        
        这是控制 token 消耗的关键：完整 result.data 可能很大，
        但 LLM 只看到这里的 summary。
        """
        return result.summary
    
    def truncate_result(self, result: ToolResult) -> ToolResult:
        """
        自动截断超长结果。
        
        如果 result.data 转字符串后超过 max_result_size，
        自动截断并添加省略提示。
        
        对应 Claude Code 的 result size limiting。
        """
        if result.data is None:
            return result
        
        data_str = json.dumps(result.data) if not isinstance(result.data, str) else result.data
        
        if len(data_str) > self.max_result_size:
            truncated = data_str[:self.max_result_size]
            result.data = truncated + f"\n... [截断，原始长度 {len(data_str)} 字符]"
            result.metadata["truncated"] = True
            result.metadata["original_size"] = len(data_str)
        
        return result
    
    def to_dict(self) -> dict:
        """导出工具元信息（用于注册表/文档）"""
        return {
            "name": self.name,
            "description": self.description,
            "aliases": self.aliases,
            "search_hint": self.search_hint,
            "is_read_only": self.is_read_only,
            "is_destructive": self.is_destructive,
            "is_concurrency_safe": self.is_concurrency_safe,
        }
    
    def __repr__(self) -> str:
        return f"<EveTool {self.name}: {self.description[:40]}...>"
