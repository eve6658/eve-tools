"""
Structured Context Compressor — 结构化语义压缩

参考 ECC 的 Token Optimization + Claude Code 的 context compression：
- 不是简单截断，而是语义保持的智能压缩
- 保留关键信息，压缩次要内容
- 支持按信息密度分级
"""

import re
from dataclasses import dataclass, field


@dataclass
class CompressedBlock:
    """压缩后的文本块"""
    content: str
    original_length: int
    compressed_length: int
    preserved_ratio: float  # 保留比例
    level: str              # full / summary / minimal
    
    @property
    def compression_ratio(self) -> float:
        return 1 - self.preserved_ratio


class StructuredCompressor:
    """
    结构化上下文压缩器。
    
    对比 Claude Code 的 microcompact:
    - 原版只是简单截断前60% + 后40%
    - 这个按语义块级别压缩，保留完整信息密度
    
    压缩策略:
    1. full: 完整保留（当前轮次、关键信息）
    2. summary: 摘要（重要但非关键的内容）
    3. minimal: 最小化（只保留实体名和结果）
    """
    
    # 压缩比率
    LEVELS = {
        "full": 1.0,       # 完整保留
        "summary": 0.3,    # 保留 30%
        "minimal": 0.05,   # 保留 5%
    }
    
    # 关键模式（这些不压缩）
    CRITICAL_PATTERNS = [
        r"错误|error|exception|traceback",
        r"决定|选择|确认",
        r"完成|完成度",
        r"结果:|答案:|结论:",
        r"TODO|FIXME|BUG",
    ]
    
    def __init__(self, max_chars: int = 4000):
        self.max_chars = max_chars
    
    def compress(self, text: str, level: str = "summary") -> CompressedBlock:
        """
        压缩文本。
        
        Args:
            text: 原始文本
            level: full / summary / minimal
        """
        if len(text) <= self.max_chars:
            return CompressedBlock(
                content=text,
                original_length=len(text),
                compressed_length=len(text),
                preserved_ratio=1.0,
                level="full",
            )
        
        ratio = self.LEVELS.get(level, 0.3)
        target_length = int(self.max_chars * ratio)
        
        if level == "summary":
            compressed = self._compress_semantic(text, target_length)
        elif level == "minimal":
            compressed = self._compress_minimal(text, target_length)
        else:
            compressed = text[:self.max_chars]
        
        return CompressedBlock(
            content=compressed,
            original_length=len(text),
            compressed_length=len(compressed),
            preserved_ratio=len(compressed) / len(text) if text else 1,
            level=level,
        )
    
    def compress_messages(self, messages: list[dict]) -> list[dict]:
        """
        压缩消息列表。
        
        策略：
        - 最新 3 条：full 保留
        - 次新 5 条：summary
        - 更早：minimal
        - 检测到 CRITICAL_PATTERNS 的：always full
        """
        if not messages:
            return messages
        
        result = []
        
        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            
            # 跳过系统消息
            if msg.get("role") == "system" and msg.get("is_compact"):
                result.append(msg)
                continue
            
            remaining = len(messages) - i
            
            if remaining <= 3:
                # 最新 3 条：完整保留
                result.append(msg)
            elif self._is_critical(content):
                # 关键内容：完整保留
                result.append(msg)
            elif remaining <= 8:
                # 次新：摘要
                compressed = self.compress(content, "summary")
                result.append({
                    **msg,
                    "content": compressed.content,
                    "_compressed": True,
                    "_original_length": compressed.original_length,
                })
            else:
                # 更早：最小化
                compressed = self.compress(content, "minimal")
                result.append({
                    **msg,
                    "content": compressed.content,
                    "_compressed": True,
                    "_original_length": compressed.original_length,
                })
        
        return result
    
    def _compress_semantic(self, text: str, target: int) -> str:
        """语义压缩：保留关键段落"""
        # 按段落分割
        paragraphs = text.split("\n\n")
        
        # 为每段评分（信息密度）
        scored = []
        for p in paragraphs:
            score = self._information_density(p)
            scored.append((score, p))
        
        # 按分数排序，选前几段达到 target 长度
        scored.sort(key=lambda x: x[0], reverse=True)
        
        selected = []
        current_len = 0
        for score, para in scored:
            if current_len + len(para) <= target:
                selected.append(para)
                current_len += len(para)
            else:
                break
        
        # 恢复原始顺序
        result_parts = []
        for para in paragraphs:
            if para in selected:
                result_parts.append(para)
        
        result = "\n\n".join(result_parts)
        
        # 如果还是太长，直接截断
        if len(result) > target:
            result = result[:target] + "..."
        
        return result
    
    def _compress_minimal(self, text: str, target: int) -> str:
        """最小化压缩：只保留关键词和数字"""
        # 提取实体名
        entities = re.findall(r'[A-Z][A-Za-z]{2,}', text)
        # 提取数字
        numbers = re.findall(r'\d+(?:\.\d+)?%?', text)
        # 提取中文关键词
        keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        
        # 组合
        parts = []
        if entities:
            parts.append(" ".join(set(entities[:10])))
        if keywords:
            parts.append(" ".join(list(dict.fromkeys(keywords))[:15]))
        if numbers:
            parts.append(" ".join(set(numbers[:10])))
        
        result = " | ".join(parts)
        if len(result) > target:
            result = result[:target] + "..."
        return result
    
    def _is_critical(self, text: str) -> bool:
        """判断是否是关键内容"""
        for pattern in self.CRITICAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _information_density(self, text: str) -> float:
        """计算信息密度评分"""
        if not text:
            return 0
        
        score = 0
        
        # 数字密度
        numbers = len(re.findall(r'\d+(?:\.\d+)?', text))
        score += min(numbers * 0.1, 0.3)
        
        # 代码块
        if "```" in text or "def " in text or "class " in text:
            score += 0.3
        
        # 关键词
        keywords = ["结果", "结论", "方案", "错误", "完成", "建议", "分析"]
        for kw in keywords:
            if kw in text:
                score += 0.1
        
        # 长度适中（太短信息少，太长可能废话）
        if 50 < len(text) < 500:
            score += 0.2
        elif len(text) >= 500:
            score += 0.1
        
        return min(score, 1.0)
    
    # ============================================================
    # 上下文窗口管理
    # ============================================================
    
    def fit_to_window(self, messages: list[dict], max_tokens: int = 8000,
                      chars_per_token: int = 4) -> list[dict]:
        """
        确保消息列表在 token 限制内。
        
        策略：
        1. 计算总字符数
        2. 如果超出，从最老的消息开始压缩
        3. 逐步提高压缩级别：summary → minimal → 删除
        """
        max_chars = max_tokens * chars_per_token
        total = sum(len(m.get("content", "")) for m in messages)
        
        if total <= max_chars:
            return messages
        
        # 逐步压缩旧消息
        result = list(messages)
        idx = 0  # 从最老的消息开始
        
        while total > max_chars and idx < len(result):
            msg = result[idx]
            if msg.get("_compressed") or msg.get("role") == "system":
                idx += 1
                continue
            
            content = msg.get("content", "")
            if len(content) > 200:  # 只压缩够大的消息
                compressed = self.compress(content, "summary")
                saved = len(content) - compressed.compressed_length
                total -= saved
                result[idx] = {
                    **msg,
                    "content": compressed.content,
                    "_compressed": True,
                }
            
            idx += 1
        
        # 如果还不够，继续压缩
        idx = 0
        while total > max_chars and idx < len(result):
            msg = result[idx]
            if msg.get("_compressed"):
                content = msg.get("content", "")
                if len(content) > 100:
                    compressed = self.compress(content, "minimal")
                    saved = len(content) - compressed.compressed_length
                    total -= saved
                    result[idx] = {
                        **msg,
                        "content": compressed.content,
                        "_compressed": True,
                    }
            idx += 1
        
        return result
    
    def get_stats(self, messages: list[dict]) -> dict:
        """压缩统计"""
        total_original = 0
        total_compressed = 0
        compressed_count = 0
        
        for m in messages:
            orig = m.get("_original_length", len(m.get("content", "")))
            curr = len(m.get("content", ""))
            total_original += orig
            total_compressed += curr
            if m.get("_compressed"):
                compressed_count += 1
        
        return {
            "total_messages": len(messages),
            "compressed_messages": compressed_count,
            "original_chars": total_original,
            "compressed_chars": total_compressed,
            "compression_ratio": 1 - total_compressed / total_original if total_original else 0,
        }
