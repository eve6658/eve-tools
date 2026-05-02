"""
Dream Memory — 主动记忆整合系统

夜间/空闲时自动整理记忆、提取模式、更新长期记忆。

参考 ECC 的 Memory Persistence + Memory Extraction：
- 定期将短期记忆整合为长期记忆
- 识别重复出现的模式
- 清理过期和低价值信息
"""

import os
import time
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MemoryFragment:
    """记忆碎片"""
    content: str
    category: str          # decision / lesson / pattern / fact / todo
    importance: float      # 0.0 - 1.0
    timestamp: float
    source: str = ""       # 来源（日记文件名、会话ID等）
    tags: list[str] = field(default_factory=list)


class DreamMemory:
    """
    主动记忆整合引擎。
    
    对应 ECC 的 Memory Persistence：
    - 扫描所有短期记忆（daily notes）
    - 提取重要信息
    - 整合为长期记忆（MEMORY.md）
    - 清理过期信息
    """
    
    def __init__(self, workspace: str = "."):
        self.workspace = workspace
        self.memory_dir = os.path.join(workspace, "memory")
        self.memory_file = os.path.join(workspace, "MEMORY.md")
        self.fragments: list[MemoryFragment] = []
    
    def scan_daily_notes(self) -> list[MemoryFragment]:
        """扫描所有日记文件，提取记忆碎片"""
        fragments = []
        
        if not os.path.isdir(self.memory_dir):
            return fragments
        
        for fname in sorted(os.listdir(self.memory_dir)):
            if not fname.endswith(".md"):
                continue
            
            filepath = os.path.join(self.memory_dir, fname)
            date = fname.replace(".md", "")
            
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 提取每个二级标题下的内容
            sections = self._split_sections(content)
            for title, body in sections:
                category = self._classify(title, body)
                importance = self._estimate_importance(title, body)
                
                if importance > 0.3:  # 保留有意义的内容
                    fragments.append(MemoryFragment(
                        content=body.strip(),
                        category=category,
                        importance=importance,
                        timestamp=self._parse_date(date),
                        source=date,
                        tags=self._extract_tags(title, body),
                    ))
        
        self.fragments = fragments
        return fragments
    
    def integrate(self) -> str:
        """
        将记忆碎片整合为长期记忆。
        
        输出格式对应 ECC 的 MEMORY.md 结构：
        ## 日期 | 主题
        - 关键决策 / 学到的经验 / 值得记住的模式
        """
        fragments = self.fragments or self.scan_daily_notes()
        
        if not fragments:
            return ""
        
        # 按重要性排序
        sorted_frags = sorted(fragments, key=lambda f: f.importance, reverse=True)
        
        lines = ["# MEMORY.md - 长期记忆\n"]
        
        # 按类别分组
        categories = {
            "decision": ("🎯 重要决策", []),
            "lesson": ("📚 经验教训", []),
            "pattern": ("🔍 发现的模式", []),
            "fact": ("📌 事实信息", []),
            "todo": ("✅ 待办事项", []),
        }
        
        for frag in sorted_frags:
            if frag.category in categories:
                categories[frag.category][1].append(frag)
        
        for cat_key, (cat_title, frags) in categories.items():
            if not frags:
                continue
            lines.append(f"\n## {cat_title}\n")
            for f in frags[:10]:  # 每类最多10条
                source_info = f"[{f.source}] " if f.source else ""
                lines.append(f"- {source_info}{f.content[:200]}")
        
        return "\n".join(lines)
    
    def update_long_term_memory(self) -> bool:
        """更新长期记忆文件"""
        content = self.integrate()
        if not content:
            return False
        
        # 追加到现有 MEMORY.md
        existing = ""
        if os.path.exists(self.memory_file):
            with open(self.memory_file, "r", encoding="utf-8") as f:
                existing = f.read()
        
        # 合并（保留原有内容，在末尾追加整合后的内容）
        timestamp = time.strftime("%Y-%m-%d %H:%M")
        separator = f"\n\n---\n## 梦想整理 ({timestamp})\n\n"
        
        # 如果已有梦想整理部分，替换它
        if "梦想整理" in existing:
            parts = existing.split("## 梦想整理")
            existing = parts[0]
        
        new_content = existing + separator + content.split("\n", 1)[-1]
        
        with open(self.memory_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return True
    
    # ============================================================
    # 辅助方法
    # ============================================================
    
    def _split_sections(self, content: str) -> list[tuple[str, str]]:
        """按 ## 或 ### 标题分割内容"""
        sections = []
        current_title = ""
        current_body = ""
        
        for line in content.split("\n"):
            if line.startswith("## ") or line.startswith("### "):
                if current_body:
                    sections.append((current_title, current_body))
                current_title = line.lstrip("#").strip()
                current_body = ""
            else:
                current_body += line + "\n"
        
        if current_body:
            sections.append((current_title, current_body))
        
        return sections
    
    def _classify(self, title: str, body: str) -> str:
        """分类记忆碎片"""
        text = f"{title} {body}".lower()
        
        decision_words = ["决定", "选择", "方案", "决策", "最终", "决定用", "确认"]
        lesson_words = ["教训", "经验", "错误", "失败", "学习", "总结", "复盘", "教训是"]
        pattern_words = ["规律", "模式", "总是", "每次", "重复", "发现", "一致"]
        fact_words = ["数据", "信息", "事实", "记录", "公司", "项目", "报告"]
        todo_words = ["计划", "待办", "明天", "下周", "需要", "准备"]
        
        for w in decision_words:
            if w in text:
                return "decision"
        for w in lesson_words:
            if w in text:
                return "lesson"
        for w in pattern_words:
            if w in text:
                return "pattern"
        for w in fact_words:
            if w in text:
                return "fact"
        for w in todo_words:
            if w in text:
                return "todo"
        
        return "fact"  # default
    
    def _estimate_importance(self, title: str, body: str) -> float:
        """估算重要性 0-1"""
        score = 0.5
        text = f"{title} {body}"
        
        # 长度加权
        if len(text) > 100:
            score += 0.1
        if len(text) > 300:
            score += 0.1
        
        # 关键词加权
        important_words = ["关键", "重要", "核心", "决定", "风险", "损失", "盈利", "复盘"]
        for w in important_words:
            if w in text:
                score += 0.1
        
        # 标题权重
        if any(w in title for w in ["决策", "经验", "复盘", "总结"]):
            score += 0.2
        
        return min(score, 1.0)
    
    def _extract_tags(self, title: str, body: str) -> list[str]:
        """提取标签"""
        tags = []
        text = f"{title} {body}"
        
        tag_keywords = {
            "交易": ["交易", "买", "卖", "涨", "跌", "盘口"],
            "代码": ["代码", "编程", "bug", "函数", "变量"],
            "项目": ["项目", "里程碑", "版本", "发布"],
            "学习": ["学习", "研究", "理解", "掌握"],
        }
        
        for tag, keywords in tag_keywords.items():
            if any(k in text for k in keywords):
                tags.append(tag)
        
        return tags
    
    def _parse_date(self, date_str: str) -> float:
        """解析日期字符串为时间戳"""
        try:
            return time.mktime(time.strptime(date_str, "%Y-%m-%d"))
        except ValueError:
            return 0.0
    
    def get_stats(self) -> dict:
        """获取记忆统计"""
        fragments = self.fragments or self.scan_daily_notes()
        return {
            "total_fragments": len(fragments),
            "by_category": {
                cat: sum(1 for f in fragments if f.category == cat)
                for cat in ["decision", "lesson", "pattern", "fact", "todo"]
            },
            "avg_importance": sum(f.importance for f in fragments) / len(fragments) if fragments else 0,
            "sources": len(set(f.source for f in fragments)),
        }
