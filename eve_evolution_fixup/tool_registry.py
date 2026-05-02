"""
tool_registry.py — Eve 工具注册表

设计思路：
---------
参考 Claude Code 的 assembleToolPool() 模式。在 Claude Code 启动时，
会将所有内置工具（Read/Write/Bash/Edit）和 MCP 工具合并到一个 tool pool 中，
然后根据权限配置过滤可用工具。

核心功能：
1. **注册与查找** — 支持按名称和别名查找工具
2. **权限过滤** — 根据规则过滤出可用工具子集
3. **关键词搜索** — 基于 search_hint 的模糊匹配（用于技能发现）
4. **MCP 合并** — 将内置工具和外部 MCP 工具统一管理

与 Claude Code 的对应关系：
- ToolRegistry ≈ Claude Code 的 ToolPool
- register() ≈ Claude Code 的 addTool()
- assemble_pool() ≈ Claude Code 的 assembleToolPool()
- filter_by_permissions() ≈ Claude Code 的 filterToolsByPermissions()
"""

from __future__ import annotations

from typing import Optional
from tool_framework import EveTool, PermissionResult, ToolContext


class ToolRegistry:
    """
    工具注册表 — Eve 的工具中枢。
    
    所有工具（内置 + MCP）都注册到这里，通过统一接口访问。
    支持按名称、别名、关键词查找，以及权限过滤。
    
    使用示例：
        registry = ToolRegistry()
        registry.register(ReadTool())
        registry.register(WriteTool())
        
        tool = registry.get("read")     # 按名称
        tool = registry.get("cat")      # 按别名
        tools = registry.search("file") # 关键词搜索
    """
    
    def __init__(self):
        # 主索引: name → tool
        self._tools: dict[str, EveTool] = {}
        # 别名索引: alias → tool
        self._aliases: dict[str, EveTool] = {}
        # 保留所有工具的有序列表（注册顺序）
        self._order: list[str] = []
    
    def register(self, tool: EveTool) -> None:
        """
        注册一个工具。
        
        自动注册其所有别名到别名索引。
        如果名称已存在，覆盖旧工具（类似 Claude Code 的 tool override）。
        """
        name = tool.name
        if not name:
            raise ValueError("工具必须有 name 属性")
        
        # 如果已存在，先清理旧的别名引用
        if name in self._tools:
            old_tool = self._tools[name]
            for alias in old_tool.aliases:
                self._aliases.pop(alias, None)
            # 保持原注册顺序位置
        else:
            self._order.append(name)
        
        self._tools[name] = tool
        
        # 注册别名
        for alias in tool.aliases:
            self._aliases[alias] = tool
    
    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name not in self._tools:
            return False
        tool = self._tools.pop(name)
        for alias in tool.aliases:
            self._aliases.pop(alias, None)
        if name in self._order:
            self._order.remove(name)
        return True
    
    def get(self, name: str) -> Optional[EveTool]:
        """
        按名称或别名查找工具。
        
        优先按精确名称匹配，找不到再查别名。
        这样即使别名和名称冲突，名称优先。
        """
        if name in self._tools:
            return self._tools[name]
        if name in self._aliases:
            return self._aliases[name]
        return None
    
    def has(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools or name in self._aliases
    
    def list_tools(self, include_aliases: bool = False) -> list[dict]:
        """
        列出所有注册工具。
        
        Args:
            include_aliases: 是否包含别名信息
        """
        result = []
        for name in self._order:
            tool = self._tools[name]
            info = tool.to_dict()
            if not include_aliases:
                info.pop("aliases", None)
            result.append(info)
        return result
    
    def filter_by_permissions(self, rules: dict[str, str] | None = None) -> list[EveTool]:
        """
        根据权限规则过滤工具。
        
        Args:
            rules: 工具名 → 权限级别映射，如 {"write": "allow", "bash": "ask"}
                   如果为 None，返回所有工具
                   
        返回满足权限规则的工具列表。
        
        对应 Claude Code 的 filterToolsByPermissions()：
        根据用户配置的权限策略，过滤出可使用的工具。
        """
        if rules is None:
            return [self._tools[name] for name in self._order]
        
        result = []
        for name in self._order:
            tool = self._tools[name]
            # 如果工具在规则中被显式允许或询问，加入结果
            if name in rules:
                perm = rules[name]
                if perm in ("allow", "ask"):
                    result.append(tool)
            else:
                # 不在规则中的工具默认允许（安全策略可调整）
                result.append(tool)
        return result
    
    def search(self, query: str) -> list[EveTool]:
        """
        基于关键词搜索工具。
        
        搜索范围：工具名称、描述、search_hint。
        使用简单的子串匹配（不区分大小写）。
        
        用于技能自动发现：根据用户输入找到相关工具。
        """
        query_lower = query.lower()
        results = []
        for name in self._order:
            tool = self._tools[name]
            searchable = f"{tool.name} {tool.description} {tool.search_hint}".lower()
            if query_lower in searchable:
                results.append(tool)
        return results
    
    def search_multi(self, keywords: list[str]) -> list[EveTool]:
        """
        多关键词搜索，返回匹配任意关键词的工具。
        
        用于 SkillDiscoverer 的技能发现。
        """
        results = []
        seen = set()
        for kw in keywords:
            for tool in self.search(kw):
                if tool.name not in seen:
                    results.append(tool)
                    seen.add(tool.name)
        return results
    
    def assemble_pool(
        self,
        builtins: list[EveTool] | None = None,
        mcp_tools: list[EveTool] | None = None,
    ) -> "ToolRegistry":
        """
        合并内置工具和 MCP 工具到注册表。
        
        对应 Claude Code 的 assembleToolPool()：
        在启动时将所有工具源合并到一个统一的工具池中。
        
        Args:
            builtins: 内置工具列表
            mcp_tools: 外部 MCP 工具列表
            
        Returns:
            self（支持链式调用）
        """
        if builtins:
            for tool in builtins:
                self.register(tool)
        
        if mcp_tools:
            for tool in mcp_tools:
                # MCP 工具标记来源
                tool.metadata = getattr(tool, 'metadata', {})
                tool.metadata['source'] = 'mcp'
                self.register(tool)
        
        return self
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __iter__(self):
        """迭代所有工具（按注册顺序）"""
        for name in self._order:
            yield self._tools[name]
    
    def __contains__(self, name: str) -> bool:
        return self.has(name)
    
    def __repr__(self) -> str:
        return f"<ToolRegistry: {len(self._tools)} tools>"
