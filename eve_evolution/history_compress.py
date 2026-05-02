"""
history_compress.py — 历史压缩系统

设计思路：
---------
参考 Claude Code 的 snip + compact 双层压缩机制。
在 Claude Code 中，当对话历史过长时：
1. snip（轻量裁剪）: 保留开头和结尾，中间的工具调用替换为摘要
2. compact（重量压缩）: 用 LLM 将整个历史压缩为一段摘要
3. microcompact: 单个超长工具结果自动截断

为什么需要压缩？
- LLM 的上下文窗口是有限的
- 长对话会导致 token 消耗巨大
- 历史越长，模型处理越慢
- 大部分历史内容对当前任务关联度低

压缩策略（参考 Claude Code）：
1. 保留 system prompt 和最近 N 条消息
2. 中间的历史：只保留摘要，移除详细内容
3. 工具结果：超过阈值自动截断

与 Claude Code 的对应关系：
- HistoryCompressor ≈ Claude Code 的 HistoryCompressor
- snip() ≈ Claude Code 的 snipMessages()
- compact() ≈ Claude Code 的 compactMessages()
- microcompact() ≈ Claude Code 的 truncateToolResult()
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, Optional


# ============================================================
# 消息结构
# ============================================================

@dataclass
class Message:
    """
    统一消息结构。
    
    对应 LLM 对话中的消息格式。
    """
    role: str           # "system" | "user" | "assistant" | "tool"
    content: str        # 消息内容
    name: str = ""      # 工具名称（role=tool 时）
    tool_call_id: str = ""  # 工具调用 ID
    timestamp: float = field(default_factory=time.time)
    tokens: int = 0     # 估算 token 数
    
    def is_tool_result(self) -> bool:
        return self.role == "tool"
    
    def is_system(self) -> bool:
        return self.role == "system"
    
    def is_user(self) -> bool:
        return self.role == "user"
    
    def is_assistant(self) -> bool:
        return self.role == "assistant"
    
    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d
    
    @classmethod
    def system(cls, content: str) -> "Message":
        return cls(role="system", content=content)
    
    @classmethod
    def user(cls, content: str) -> "Message":
        return cls(role="user", content=content)
    
    @classmethod
    def assistant(cls, content: str) -> "Message":
        return cls(role="assistant", content=content)
    
    @classmethod
    def tool(cls, content: str, name: str = "", tool_call_id: str = "") -> "Message":
        return cls(role="tool", content=content, name=name, tool_call_id=tool_call_id)


# ============================================================
# 历史压缩器
# ============================================================

class HistoryCompressor:
    """
    双层历史压缩器。
    
    提供三种压缩级别：
    1. microcompact — 单条消息截断（最轻量）
    2. snip — 结构化裁剪（保留关键结构）
    3. compact — LLM 摘要压缩（最彻底）
    
    使用策略（参考 Claude Code）：
    - 工具结果超长 → microcompact
    - 历史消息较多 → snip（保留最近 N 条 + 摘要）
    - 历史消息极多 → compact（LLM 生成摘要）
    
    使用示例：
        compressor = HistoryCompressor()
        
        # 单条截断
        result = compressor.microcompact(long_text, max_chars=2000)
        
        # 结构化裁剪
        short = compressor.snip(messages, keep_last_n=5)
        
        # LLM 压缩
        compressed = await compressor.compact(messages, my_llm_call)
    """
    
    def microcompact(self, tool_result: str, max_chars: int = 2000) -> str:
        """
        单个超长工具结果的自动截断。
        
        策略：
        - 保留前半部分（开头通常有关键信息）
        - 保留后半部分（结尾通常有结果/状态）
        - 中间用省略号连接
        
        对应 Claude Code 的 tool result truncation。
        
        Args:
            tool_result: 原始工具结果
            max_chars: 最大字符数
            
        Returns:
            截断后的结果
        """
        if len(tool_result) <= max_chars:
            return tool_result
        
        marker = f"\n\n... [截断，原始 {len(tool_result)} 字符，保留 {max_chars} 字符]\n\n"
        reserve = len(marker) + 10
        
        if max_chars < reserve + 50:
            # 空间太小，只保留头部
            return tool_result[:max(max_chars - reserve, 20)] + marker
        
        head_size = int((max_chars - reserve) * 0.6)
        tail_size = max_chars - reserve - head_size
        
        head = tool_result[:head_size]
        tail = tool_result[-tail_size:]
        
        return f"{head}{marker}{tail}"
    
    def snip(self, messages: list[Message], keep_last_n: int = 5) -> list[Message]:
        """
        轻量结构化裁剪。
        
        策略（参考 Claude Code snipMessages）：
        1. 保留 system prompt（第一或前几条）
        2. 保留最近 N 条消息完整保留
        3. 中间的消息：
           - user 消息：保留为 [摘要]
           - tool 结果：替换为 [工具结果摘要]
           - assistant 的工具调用：保留结构但精简
        
        这种方式保留了对话结构，LLM 可以理解上下文。
        
        Args:
            messages: 原始消息列表
            keep_last_n: 保留最近几条完整消息
            
        Returns:
            裁剪后的消息列表
        """
        if len(messages) <= keep_last_n + 2:
            return messages  # 太短，不需要裁剪
        
        result = []
        
        # 1. 保留 system messages
        for msg in messages:
            if msg.is_system():
                result.append(msg)
        
        # 2. 计算需要保留的范围
        #    从末尾往前数 keep_last_n 条非 system 消息
        non_system = [m for m in messages if not m.is_system()]
        
        if len(non_system) <= keep_last_n:
            result.extend(non_system)
            return result
        
        # 3. 中间部分：生成摘要
        middle = non_system[:len(non_system) - keep_last_n]
        recent = non_system[len(non_system) - keep_last_n:]
        
        # 为中间部分生成摘要
        if middle:
            # 统计中间部分的信息
            user_msgs = [m for m in middle if m.is_user()]
            tool_msgs = [m for m in middle if m.is_tool_result()]
            
            summary_parts = []
            if user_msgs:
                summary_parts.append(f"{len(user_msgs)} 条用户消息")
            if tool_msgs:
                summary_parts.append(f"{len(tool_msgs)} 条工具结果")
            
            summary = f"[历史摘要：{'、'.join(summary_parts)}，共 {len(middle)} 条消息]"
            result.append(Message.user(summary))
        
        # 4. 添加最近的完整消息
        result.extend(recent)
        
        return result
    
    async def compact(
        self,
        messages: list[Message],
        llm_call: Callable[[list[Message]], Awaitable[str]],
    ) -> list[Message]:
        """
        重量压缩 — 用 LLM 生成整个历史的摘要。
        
        策略（参考 Claude Code compactMessages）：
        1. 将历史消息发送给 LLM
        2. 请求 LLM 生成一个简洁的摘要
        3. 用摘要替换原始历史
        
        这是最彻底的压缩方式，适合对话非常长的场景。
        
        Args:
            messages: 原始消息列表
            llm_call: LLM 调用函数，接收消息列表返回摘要文本
            
        Returns:
            压缩后的消息列表（system + 摘要 + 最近几条）
        """
        if len(messages) <= 3:
            return messages  # 太短不需要压缩
        
        # 构建压缩请求
        system_msgs = [m for m in messages if m.is_system()]
        non_system = [m for m in messages if not m.is_system()]
        
        # 如果历史不长，直接返回
        if len(non_system) <= 6:
            return messages
        
        # 用 LLM 生成摘要
        compact_prompt = Message.user(
            "请将以上对话历史压缩为一段简洁的摘要（200字以内），"
            "保留关键信息、决策和上下文，忽略细节。"
            "摘要应该帮助未来的对话理解之前发生了什么。"
        )
        
        try:
            summary_text = await llm_call([compact_prompt])
        except Exception:
            # LLM 调用失败，降级到 snip
            return self.snip(messages, keep_last_n=5)
        
        # 构建压缩后的消息列表
        result = system_msgs.copy() if system_msgs else []
        result.append(Message.user(f"[对话历史摘要]\n{summary_text}"))
        
        # 保留最近 3 条消息以保持连续性
        recent = non_system[-3:]
        result.extend(recent)
        
        return result
    
    def estimate_tokens(self, messages: list[Message]) -> int:
        """
        估算消息列表的 token 数。
        
        简单估算：中文 1 字 ≈ 1.5 token，英文 1 词 ≈ 1.3 token
        实际应使用 tiktoken，这里做粗略估算。
        """
        total = 0
        for msg in messages:
            content = msg.content
            # 粗略估算
            cn_chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])
            en_chars = len(content) - cn_chars
            tokens = int(cn_chars * 1.5 + en_chars * 0.3)
            msg.tokens = tokens
            total += tokens
        return total
    
    def should_compress(self, messages: list[Message], threshold: int = 4000) -> bool:
        """
        判断是否需要压缩。
        
        Args:
            messages: 当前消息列表
            threshold: token 阈值
        """
        total_tokens = self.estimate_tokens(messages)
        return total_tokens > threshold
