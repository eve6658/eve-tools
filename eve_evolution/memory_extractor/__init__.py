"""
Memory Extractor — 从会话中自动提取知识

参考 ECC 的 Continuous Learning：
- 对话结束后自动提取有价值的信息
- 转为可搜索的、可复用的知识卡片
- 支持错误学习 + 经验教训
"""

import time
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KnowledgeCard:
    """知识卡片"""
    title: str
    content: str
    card_type: str          # error_lesson / pattern / decision / fact / tip
    tags: list[str] = field(default_factory=list)
    source: str = ""        # 会话来源
    timestamp: float = field(default_factory=time.time)
    importance: float = 0.5
    reusable: bool = True   # 是否可复用到未来场景
    
    def to_markdown(self) -> str:
        return f"""## {self.title}

**类型**: {self.card_type} | **重要性**: {self.importance:.0%} | **可复用**: {'✅' if self.reusable else '❌'}

{self.content}

**标签**: {', '.join(self.tags)}
**来源**: {self.source}
"""


class MemoryExtractor:
    """
    从对话/任务结果中提取知识卡片。
    
    对应 ECC 的 session learning：
    - 扫描会话历史
    - 识别错误/决策/模式
    - 生成 KnowledgeCard
    - 存储到 knowledge base
    """
    
    # 错误模式识别
    ERROR_PATTERNS = [
        (r'Error:?\s*(.+?)[\n.]', "error"),
        (r'失败:?\s*(.+?)[\n.]', "failure"),
        (r'❌\s*(.+?)[\n.]', "error_emoji"),
        (r'traceback|trace back', "traceback"),
        (r'timeout|timed?\s*out', "timeout"),
        (r'connection\s+(refused|error|reset)', "connection"),
    ]
    
    # 决策模式
    DECISION_PATTERNS = [
        (r'决定[:：]\s*(.+?)[\n.]', "decision"),
        (r'最终选择了?[:：]\s*(.+?)[\n.]', "choice"),
        (r'经过比较.*?选择[:：]?\s*(.+?)[\n.]', "comparison"),
    ]
    
    def __init__(self, workspace: str = "."):
        self.workspace = workspace
        self.knowledge_base: list[KnowledgeCard] = []
    
    def extract_from_text(self, text: str, source: str = "") -> list[KnowledgeCard]:
        """从文本中提取知识卡片"""
        cards = []
        
        # 1. 提取错误教训
        cards.extend(self._extract_errors(text, source))
        
        # 2. 提取决策记录
        cards.extend(self._extract_decisions(text, source))
        
        # 3. 提取技术要点
        cards.extend(self._extract_tips(text, source))
        
        # 4. 提取数据事实
        cards.extend(self._extract_facts(text, source))
        
        # 去重
        cards = self._deduplicate(cards)
        
        return cards
    
    def extract_from_session(self, session_messages: list[dict], source: str = "session") -> list[KnowledgeCard]:
        """从会话消息列表中提取"""
        # 合并所有消息
        full_text = ""
        for msg in session_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            full_text += f"\n[{role}] {content}\n"
        
        return self.extract_from_text(full_text, source)
    
    def _extract_errors(self, text: str, source: str) -> list[KnowledgeCard]:
        """提取错误教训"""
        cards = []
        
        for pattern, error_type in self.ERROR_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                error_desc = match.group(1) if match.lastindex else match.group(0)
                error_desc = error_desc.strip()[:200]
                
                # 尝试找上下文中的解决方案
                context = self._get_context(text, match.start(), chars=500)
                solution = self._try_extract_solution(context)
                
                content = f"**错误**: {error_desc}\n"
                if solution:
                    content += f"**解决方案**: {solution}\n"
                content += f"**上下文**: {context[:300]}"
                
                cards.append(KnowledgeCard(
                    title=f"错误教训: {error_desc[:50]}",
                    content=content,
                    card_type="error_lesson",
                    tags=["error", error_type],
                    source=source,
                    importance=0.7,
                    reusable=True,
                ))
        
        return cards
    
    def _extract_decisions(self, text: str, source: str) -> list[KnowledgeCard]:
        """提取决策记录"""
        cards = []
        
        for pattern, decision_type in self.DECISION_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                decision_desc = match.group(1) if match.lastindex else match.group(0)
                decision_desc = decision_desc.strip()[:200]
                
                context = self._get_context(text, match.start(), chars=300)
                
                cards.append(KnowledgeCard(
                    title=f"决策: {decision_desc[:50]}",
                    content=f"**决策**: {decision_desc}\n**背景**: {context[:300]}",
                    card_type="decision",
                    tags=["decision", decision_type],
                    source=source,
                    importance=0.6,
                    reusable=True,
                ))
        
        return cards
    
    def _extract_tips(self, text: str, source: str) -> list[KnowledgeCard]:
        """提取技术要点"""
        cards = []
        
        # 匹配经验法则
        tip_patterns = [
            r'(?:经验|技巧|要点|注意)[:：]\s*(.+?)(?:\n|$)',
            r'(?:记住|记住|注意)[:：]?\s*(.+?)(?:\n|$)',
            r'(?:建议|推荐)[:：]?\s*(.+?)(?:\n|$)',
        ]
        
        for pattern in tip_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                tip = match.group(1).strip()[:200]
                cards.append(KnowledgeCard(
                    title=f"经验要点: {tip[:50]}",
                    content=tip,
                    card_type="tip",
                    tags=["tip"],
                    source=source,
                    importance=0.5,
                    reusable=True,
                ))
        
        return cards
    
    def _extract_facts(self, text: str, source: str) -> list[KnowledgeCard]:
        """提取数据事实"""
        cards = []
        
        # 匹配数字数据
        fact_patterns = [
            r'(\d+(?:\.\d+)?%?\s*(?:元|万|亿|股|手))',
            r'(代码[:：]\s*\w+)',
            r'(PE[:：]\s*\d+(?:\.\d+)?)',
        ]
        
        for pattern in fact_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                fact = match.group(0).strip()
                context = self._get_context(text, match.start(), chars=100)
                
                cards.append(KnowledgeCard(
                    title=f"数据: {fact}",
                    content=f"**数据**: {fact}\n**上下文**: {context}",
                    card_type="fact",
                    tags=["data"],
                    source=source,
                    importance=0.4,
                    reusable=False,
                ))
        
        return cards
    
    def _get_context(self, text: str, pos: int, chars: int = 300) -> str:
        """获取指定位置的上下文"""
        start = max(0, pos - chars // 2)
        end = min(len(text), pos + chars // 2)
        return text[start:end].replace("\n", " ").strip()
    
    def _try_extract_solution(self, context: str) -> Optional[str]:
        """尝试从上下文中提取解决方案"""
        sol_patterns = [
            r'解决[:：]?\s*(.+?)(?:\n|$)',
            r'修复[:：]?\s*(.+?)(?:\n|$)',
            r'改[为成][:：]?\s*(.+?)(?:\n|$)',
            r'换成[:：]?\s*(.+?)(?:\n|$)',
        ]
        for pat in sol_patterns:
            m = re.search(pat, context)
            if m:
                return m.group(1).strip()[:200]
        return None
    
    def _deduplicate(self, cards: list[KnowledgeCard]) -> list[KnowledgeCard]:
        """去重"""
        seen = set()
        unique = []
        for card in cards:
            key = card.title[:50]
            if key not in seen:
                seen.add(key)
                unique.append(card)
        return unique
    
    # ============================================================
    # 知识库管理
    # ============================================================
    
    def save_to_kb(self, cards: list[KnowledgeCard]):
        """保存到知识库"""
        self.knowledge_base.extend(cards)
    
    def search(self, query: str, card_type: str = None) -> list[KnowledgeCard]:
        """搜索知识卡片"""
        query_lower = query.lower()
        results = []
        for card in self.knowledge_base:
            if card_type and card.card_type != card_type:
                continue
            if (query_lower in card.title.lower() or 
                query_lower in card.content.lower() or
                any(query_lower in tag for tag in card.tags)):
                results.append(card)
        return sorted(results, key=lambda c: c.importance, reverse=True)
    
    def export_kb(self, path: str = None) -> str:
        """导出知识库为 Markdown"""
        if path is None:
            path = os.path.join(self.workspace, "knowledge_base.md")
        
        lines = ["# 知识库\n"]
        for card in sorted(self.knowledge_base, key=lambda c: c.importance, reverse=True):
            lines.append(card.to_markdown())
            lines.append("")
        
        content = "\n".join(lines)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return path
    
    def get_stats(self) -> dict:
        """知识库统计"""
        return {
            "total_cards": len(self.knowledge_base),
            "by_type": {
                t: sum(1 for c in self.knowledge_base if c.card_type == t)
                for t in ["error_lesson", "pattern", "decision", "fact", "tip"]
            },
            "reusable": sum(1 for c in self.knowledge_base if c.reusable),
        }
