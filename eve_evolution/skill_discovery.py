"""
skill_discovery.py — 技能自动发现系统

设计思路：
---------
参考 Claude Code 的 prefetch skill discovery 模式。
在 Claude Code 中，系统会根据用户输入自动 prefetch 相关的 skill 和 tool，
提前加载到可用池中，避免每次都要手动查找。

核心逻辑：
1. 提取用户输入的关键词
2. 在工具注册表中搜索匹配的工具
3. 去重（已发现的不再重复返回）
4. 返回新发现的工具列表

与 Claude Code 的对应关系：
- SkillDiscoverer ≈ Claude Code 的 SkillPrefetcher
- discover() ≈ Claude Code 的 prefetchSkills()
- _extract_keywords() ≈ Claude Code 的 keyword extraction
- discovered set ≈ Claude Code 的 prefetched skills cache
"""

from __future__ import annotations

import re
from typing import Optional
from tool_framework import ToolContext, EveTool
from tool_registry import ToolRegistry


# ============================================================
# 停用词表（用于关键词提取）
# ============================================================

STOP_WORDS = frozenset({
    # 中文停用词
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
    "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
    "你", "会", "着", "没有", "看", "好", "自己", "这", "他", "她",
    "它", "吗", "什么", "哪", "哪个", "怎么", "如何", "为什么",
    "请", "帮", "帮我", "能不能", "可以", "能不能", "能不能",
    # 英文停用词
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "can", "shall", "to",
    "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above",
    "below", "between", "out", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "just", "because",
    "but", "and", "or", "if", "while", "that", "this", "these",
    "those", "i", "me", "my", "we", "our", "you", "your", "he",
    "him", "his", "she", "her", "it", "its", "they", "them",
    "their", "what", "which", "who", "whom",
    # 常见动词/助词
    "帮", "查", "看", "找", "搜", "搜一下", "帮我", "给我",
    "知道", "了解", "分析", "整理", "总结", "生成", "创建",
})


class SkillDiscoverer:
    """
    技能自动发现器。
    
    根据用户输入的自然语言，自动发现相关工具/技能。
    
    工作流程：
    1. 用户输入自然语言（如 "帮我查一下天气"）
    2. 提取关键词（去掉停用词）
    3. 在注册表中搜索匹配的工具
    4. 返回新发现的工具（已发现的跳过去重）
    
    去重机制（参考 Claude Code 的 prefetch cache）：
    - self.discovered 集合记录已发现的工具名
    - 后续发现时跳过已知工具，避免重复
    
    使用示例：
        discoverer = SkillDiscoverer(registry)
        
        # 第一次：发现 weather 工具
        tools = await discoverer.discover("今天天气怎么样", context)
        
        # 第二次：weather 工具已发现，不再重复返回
        tools = await discoverer.discover("明天会不会下雨", context)
    """
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        # 已发现的工具名集合（去重用）
        self.discovered: set[str] = set()
        # 发现历史（用于调试/分析）
        self.history: list[dict] = []
    
    def _extract_keywords(self, text: str) -> list[str]:
        """
        从用户输入中提取关键词。
        
        处理步骤：
        1. 转小写
        2. 中文分词（bigram + trigram 滑窗 + 单字）
        3. 英文按单词边界提取
        4. 去掉停用词
        5. 去重保留顺序
        
        使用 n-gram 滑窗做轻量中文分词，无需第三方依赖。
        """
        text_lower = text.lower()
        
        tokens = []
        # 提取英文单词
        en_words = re.findall(r'[a-zA-Z_]+', text_lower)
        tokens.extend(en_words)
        # 提取中文连续块
        cn_blocks = re.findall(r'[\u4e00-\u9fff]+', text_lower)
        
        for block in cn_blocks:
            # 单字
            for ch in block:
                tokens.append(ch)
            # bigram (2字滑窗)
            for i in range(len(block) - 1):
                tokens.append(block[i:i+2])
            # trigram (3字滑窗)
            for i in range(len(block) - 2):
                tokens.append(block[i:i+3])
        
        # 去停用词和短词
        keywords = []
        seen = set()
        for t in tokens:
            if t in STOP_WORDS or len(t) <= 1:
                continue
            if t not in seen:
                keywords.append(t)
                seen.add(t)
        
        return keywords
    
    def _matches(self, tool: EveTool, keywords: list[str]) -> bool:
        """
        检查工具是否匹配关键词。
        
        匹配范围：工具名称、描述、search_hint。
        只要任一关键词命中即视为匹配。
        """
        searchable = f"{tool.name} {tool.description} {tool.search_hint}".lower()
        for kw in keywords:
            if kw in searchable:
                return True
        return False
    
    async def discover(self, user_input: str, context: ToolContext) -> list[EveTool]:
        """
        根据用户输入发现相关工具。
        
        Args:
            user_input: 用户自然语言输入
            context: 工具运行时上下文
            
        Returns:
            新发现的工具列表（已发现的不重复返回）
        """
        keywords = self._extract_keywords(user_input)
        
        results = []
        for tool in self.registry:
            if tool.name in self.discovered:
                continue
            if self._matches(tool, keywords):
                results.append(tool)
                self.discovered.add(tool.name)
        
        # 记录发现历史
        self.history.append({
            "input": user_input[:100],
            "keywords": keywords,
            "found": [t.name for t in results],
        })
        
        return results
    
    def discover_sync(self, user_input: str) -> list[EveTool]:
        """
        同步版本的技能发现（不需要 ToolContext）。
        
        便捷方法，适合非异步场景。
        """
        keywords = self._extract_keywords(user_input)
        
        results = []
        for tool in self.registry:
            if tool.name in self.discovered:
                continue
            if self._matches(tool, keywords):
                results.append(tool)
                self.discovered.add(tool.name)
        
        self.history.append({
            "input": user_input[:100],
            "keywords": keywords,
            "found": [t.name for t in results],
        })
        
        return results
    
    def reset(self) -> None:
        """重置发现状态"""
        self.discovered.clear()
        self.history.clear()
    
    def get_discovered(self) -> list[str]:
        """获取已发现的工具名列表"""
        return sorted(self.discovered)
    
    def get_stats(self) -> dict:
        """获取发现统计"""
        return {
            "total_discovered": len(self.discovered),
            "discovered_tools": list(self.discovered),
            "total_queries": len(self.history),
        }
