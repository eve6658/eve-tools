"""
Eve 4层记忆栈 (受 MemPalace 启发)
==================================

分层加载，按需取用，最小化 token 消耗

  Layer 0: 身份       (~100 tokens)   — 常驻。"我是谁？"
  Layer 1: 核心故事   (~300-500)      — 常驻。最重要的记忆
  Layer 2: 按需加载   (~200-400 each)  — 相关话题时加载
  Layer 3: 深度搜索   (无限)          — 全量语义搜索

唤醒成本: ~400-600 tokens (L0+L1)
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

try:
    from .aaak import compress_entity, compress_emotion, EMOTION_CODES
except ImportError:
    from aaak import compress_entity, compress_emotion, EMOTION_CODES


# ========================
# Layer 0 - 身份
# ========================

IDENTITY_TEMPLATE = """## L0 身份
我是 {name}，{role}。
特质：{traits}
时区：{timezone}
语言：{language}
"""


class Layer0:
    """
    ~100 tokens。常驻。
    从 IDENTITY.md 或 SOUL.md 读取
    """
    
    def __init__(self, workspace: str = None):
        self.workspace = workspace or os.path.expanduser("~/.openclaw/workspace")
        self._text = None
    
    def render(self) -> str:
        if self._text:
            return self._text
        
        # 尝试读取 IDENTITY.md
        identity_path = Path(self.workspace) / "IDENTITY.md"
        soul_path = Path(self.workspace) / "SOUL.md"
        
        if identity_path.exists():
            content = identity_path.read_text(encoding="utf-8")
            # 提取关键信息
            self._text = self._parse_identity(content)
        elif soul_path.exists():
            content = soul_path.read_text(encoding="utf-8")
            self._text = f"## L0 身份\n{content[:500]}"
        else:
            self._text = "## L0 身份\n未配置身份。创建 IDENTITY.md"
        
        return self._text
    
    def _parse_identity(self, content: str) -> str:
        """从 IDENTITY.md 提取关键身份信息"""
        lines = content.strip().split("\n")
        
        info = {
            "name": "Eve",
            "role": "AI 助手",
            "traits": "敏锐、温暖、真诚",
            "timezone": "GMT+8",
            "language": "中文",
        }
        
        for line in lines:
            line = line.strip()
            if line.startswith("- **Name:**") or line.startswith("# Name:"):
                info["name"] = line.split(":", 1)[1].strip().strip("*")
            elif "Creature:" in line:
                info["role"] = line.split(":", 1)[1].strip().strip("*")
            elif "Vibe:" in line:
                info["traits"] = line.split(":", 1)[1].strip().strip("*")
        
        return IDENTITY_TEMPLATE.format(**info)
    
    def token_estimate(self) -> int:
        return len(self.render()) // 4
    
    def reset(self):
        self._text = None


# ========================
# Layer 1 - 核心故事
# ========================

class Layer1:
    """
    ~300-500 tokens。常驻。
    从 MEMORY.md 和 recent daily 提取最重要的记忆
    """
    
    MAX_ITEMS = 10
    MAX_CHARS = 2000  # ~500 tokens
    
    def __init__(self, workspace: str = None):
        self.workspace = workspace or os.path.expanduser("~/.openclaw/workspace")
    
    def render(self) -> str:
        """生成 L1 核心故事"""
        memory_path = Path(self.workspace) / "MEMORY.md"
        memory_dir = Path(self.workspace) / "memory"
        
        items = []
        
        # 1. 从 MEMORY.md 提取关键事实
        if memory_path.exists():
            memory_content = memory_path.read_text(encoding="utf-8")
            items.extend(self._extract_from_memory(memory_content))
        
        # 2. 从最近的 daily 文件提取
        if memory_dir.exists():
            daily_files = sorted(memory_dir.glob("*.md"), reverse=True)[:3]
            for df in daily_files:
                content = df.read_text(encoding="utf-8")
                items.extend(self._extract_from_daily(content, df.stem))
        
        # 3. 压缩并截取
        compressed = self._compress_items(items[:self.MAX_ITEMS])
        
        # 4. 硬截断
        if len(compressed) > self.MAX_CHARS:
            compressed = compressed[:self.MAX_CHARS] + "\n..."
        
        return f"## L1 核心故事\n{compressed}"
    
    def _extract_from_memory(self, content: str) -> List[Dict]:
        """从 MEMORY.md 提取关键事实"""
        items = []
        lines = content.strip().split("\n")
        
        current_section = ""
        for line in lines:
            if line.startswith("### "):
                current_section = line[4:].strip()
            elif line.startswith("- **") and "**:" in line:
                # 提取 key: value 格式
                parts = line[3:].split("**:", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    items.append({
                        "type": "fact",
                        "section": current_section,
                        "key": key,
                        "value": value,
                        "weight": 4
                    })
        
        return items
    
    def _extract_from_daily(self, content: str, date: str) -> List[Dict]:
        """从 daily 文件提取关键事件"""
        items = []
        lines = content.strip().split("\n")
        
        for line in lines:
            if line.startswith("## ") and not line.startswith("### "):
                # 主标题
                title = line[3:].strip()
                items.append({
                    "type": "event",
                    "date": date,
                    "title": title,
                    "weight": 3
                })
        
        return items
    
    def _compress_items(self, items: List[Dict]) -> str:
        """将 items 压缩为紧凑格式"""
        lines = []
        
        for item in items:
            if item["type"] == "fact":
                section = item.get("section", "")
                key = item.get("key", "")
                value = item.get("value", "")
                # 压缩格式: [section] key: value
                lines.append(f"[{section}] {key}: {value}")
            elif item["type"] == "event":
                date = item.get("date", "")
                title = item.get("title", "")
                lines.append(f"({date}) {title}")
        
        return "\n".join(lines)
    
    def token_estimate(self) -> int:
        return len(self.render()) // 4


# ========================
# Layer 2 - 按需加载
# ========================

class Layer2:
    """
    ~200-400 tokens。按需加载。
    根据当前话题加载相关记忆
    """
    
    def __init__(self, workspace: str = None):
        self.workspace = workspace or os.path.expanduser("~/.openclaw/workspace")
    
    def render(self, topic: str, keywords: List[str] = None) -> str:
        """根据话题加载相关记忆"""
        if keywords is None:
            keywords = self._extract_keywords(topic)
        
        results = []
        
        # 搜索 MEMORY.md
        memory_path = Path(self.workspace) / "MEMORY.md"
        if memory_path.exists():
            content = memory_path.read_text(encoding="utf-8")
            results.extend(self._search_content(content, keywords, source="MEMORY"))
        
        # 搜索 daily files
        memory_dir = Path(self.workspace) / "memory"
        if memory_dir.exists():
            for df in sorted(memory_dir.glob("*.md"), reverse=True)[:7]:
                content = df.read_text(encoding="utf-8")
                results.extend(self._search_content(content, keywords, source=df.stem))
        
        if not results:
            return f"## L2 话题相关: {topic}\n(无相关记忆)"
        
        # 压缩结果
        compressed = "\n".join(results[:5])
        return f"## L2 话题相关: {topic}\n{compressed}"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本提取关键词"""
        # 简单实现：提取中文词和英文单词
        import re
        
        keywords = []
        
        # 中文词汇 (2-4字)
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        keywords.extend(chinese_words)
        
        # 英文单词
        english_words = re.findall(r'[a-zA-Z]{3,}', text.lower())
        keywords.extend(english_words)
        
        return keywords[:5]
    
    def _search_content(self, content: str, keywords: List[str], source: str) -> List[str]:
        """搜索内容中包含关键词的行"""
        results = []
        lines = content.split("\n")
        
        for line in lines:
            line_lower = line.lower()
            matches = sum(1 for kw in keywords if kw.lower() in line_lower)
            if matches >= 1 and len(line.strip()) > 5:
                results.append(f"[{source}] {line.strip()}")
        
        return results
    
    def token_estimate(self, topic: str = "") -> int:
        return len(self.render(topic)) // 4


# ========================
# Layer 3 - 深度搜索
# ========================

class Layer3:
    """
    无限。深度语义搜索。
    全量文件内容，按需读取
    """
    
    def __init__(self, workspace: str = None):
        self.workspace = workspace or os.path.expanduser("~/.openclaw/workspace")
    
    def search(self, query: str, max_files: int = 3) -> str:
        """深度搜索，返回相关文件内容"""
        results = []
        
        # 搜索所有 .md 文件
        workspace_path = Path(self.workspace)
        md_files = list(workspace_path.glob("*.md"))
        memory_dir = workspace_path / "memory"
        if memory_dir.exists():
            md_files.extend(memory_dir.glob("*.md"))
        
        # 简单关键词匹配
        keywords = query.lower().split()
        
        for md_file in md_files[:20]:  # 限制文件数
            try:
                content = md_file.read_text(encoding="utf-8")
                content_lower = content.lower()
                
                score = sum(1 for kw in keywords if kw in content_lower)
                if score > 0:
                    results.append((score, md_file.name, content[:500]))
            except Exception:
                continue
        
        # 按分数排序
        results.sort(key=lambda x: x[0], reverse=True)
        
        if not results:
            return f"## L3 深度搜索: {query}\n(无结果)"
        
        output = f"## L3 深度搜索: {query}\n"
        for score, name, content in results[:max_files]:
            output += f"\n### {name} (score: {score})\n{content}\n..."
        
        return output


# ========================
# 记忆栈管理器
# ========================

class MemoryStack:
    """
    4层记忆栈管理器
    
    用法:
        stack = MemoryStack()
        context = stack.wake_up()  # L0 + L1
        context += stack.load_topic("股票")  # L2
    """
    
    def __init__(self, workspace: str = None):
        self.workspace = workspace or os.path.expanduser("~/.openclaw/workspace")
        self.layer0 = Layer0(workspace)
        self.layer1 = Layer1(workspace)
        self.layer2 = Layer2(workspace)
        self.layer3 = Layer3(workspace)
    
    def wake_up(self) -> str:
        """唤醒：加载 L0 + L1"""
        l0 = self.layer0.render()
        l1 = self.layer1.render()
        
        total_tokens = self.layer0.token_estimate() + self.layer1.token_estimate()
        
        return f"{l0}\n{'='*40}\n{l1}\n\n[唤醒成本: ~{total_tokens} tokens]"
    
    def load_topic(self, topic: str) -> str:
        """加载 L2 按需记忆"""
        return self.layer2.render(topic)
    
    def deep_search(self, query: str) -> str:
        """L3 深度搜索"""
        return self.layer3.search(query)
    
    def stats(self) -> Dict:
        """统计信息"""
        return {
            "L0_tokens": self.layer0.token_estimate(),
            "L1_tokens": self.layer1.token_estimate(),
            "wake_up_tokens": self.layer0.token_estimate() + self.layer1.token_estimate(),
        }


# ========================
# 测试
# ========================

if __name__ == "__main__":
    import sys
    
    workspace = sys.argv[1] if len(sys.argv) > 1 else "~/.openclaw/workspace"
    stack = MemoryStack(workspace)
    
    print("=" * 60)
    print("  Eve 4层记忆栈演示")
    print("=" * 60)
    
    # 唤醒
    print("\n--- 唤醒 (L0 + L1) ---")
    wake_context = stack.wake_up()
    print(wake_context)
    
    # 按需加载
    print("\n--- 按需加载 (L2) ---")
    topic_context = stack.load_topic("股票")
    print(topic_context)
    
    # 统计
    print("\n--- 统计 ---")
    stats = stack.stats()
    print(f"L0 tokens: {stats['L0_tokens']}")
    print(f"L1 tokens: {stats['L1_tokens']}")
    print(f"唤醒总成本: ~{stats['wake_up_tokens']} tokens")
