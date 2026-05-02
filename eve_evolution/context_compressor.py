"""
Eve Context Compressor — 基于 Claude Code 源码设计的上下文压缩系统

双层压缩策略：
├── Snip（轻量）：移除中间工具调用的详细内容，保留结构和摘要
├── Compact（重量）：对整个历史做 LLM 摘要，生成紧凑上下文
└── Microcompact：单个超长工具结果自动截断+摘要

参考源码：claude_code_src/src/query.ts (applySnip, autoCompact, microcompact)
"""

import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime


@dataclass
class Message:
    """统一消息格式"""
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    timestamp: Optional[str] = None
    token_count: Optional[int] = None
    compressed: bool = False
    snip_marker: Optional[str] = None  # 裁剪标记，记录被移除的内容摘要

    def estimate_tokens(self) -> int:
        """粗略估算 token 数（中文约 1.5 token/字，英文约 1.3 token/词）"""
        if self.token_count:
            return self.token_count
        # 粗略估算：中文按字数*1.5，英文按空格分词*1.3
        text = self.content
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.4)

    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.tool_name:
            d["tool_name"] = self.tool_name
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.compressed:
            d["_compressed"] = True
        if self.snip_marker:
            d["_snip_marker"] = self.snip_marker
        return d


@dataclass
class CompressConfig:
    """压缩配置"""
    # Snip 阈值
    snip_tool_result_chars: int = 500      # 工具结果超过此长度则 snip
    snip_keep_ratio: float = 0.2           # 保留开头和结尾各多少比例

    # Compact 阈值
    compact_trigger_tokens: int = 50000    # 累计 token 超过此值触发 compact
    compact_keep_recent: int = 5           # 保留最近 N 轮对话不压缩
    compact_target_tokens: int = 10000     # 压缩后的目标 token 数

    # Microcompact 阈值
    microcompact_single_msg_chars: int = 2000  # 单条消息超过此长度触发 microcompact

    # 保留规则
    keep_system_prompts: bool = True       # 永远不压缩 system prompt
    keep_last_n_turns: int = 3             # 最近 N 轮对话不压缩


class Snipper:
    """轻量级历史裁剪 — 移除工具调用细节，保留结构"""

    def __init__(self, config: CompressConfig):
        self.config = config

    def snip_messages(self, messages: List[Message]) -> List[Message]:
        """对消息列表执行 snip 裁剪"""
        result = []
        for msg in messages:
            if self._should_snip(msg):
                result.append(self._create_snip(msg))
            else:
                result.append(msg)
        return result

    def _should_snip(self, msg: Message) -> bool:
        """判断消息是否需要 snip"""
        if msg.role == "system":
            return False  # 永远不压缩 system prompt
        if msg.compressed:
            return False  # 已经压缩过的不再处理
        if msg.role == "tool" and len(msg.content) > self.config.snip_tool_result_chars:
            return True
        if msg.role == "assistant" and msg.tool_name and len(msg.content) > self.config.snip_tool_result_chars:
            return True
        return False

    def _create_snip(self, msg: Message) -> Message:
        """创建 snip 后的消息"""
        original_len = len(msg.content)
        keep_chars = int(self.config.snip_tool_result_chars * self.config.snip_keep_ratio)

        # 保留开头和结尾
        if original_len <= keep_chars * 2:
            snipped = msg.content
        else:
            start = msg.content[:keep_chars]
            end = msg.content[-keep_chars:]
            removed_count = original_len - keep_chars * 2
            snipped = f"{start}\n\n... [已裁剪 {removed_count} 字符] ...\n\n{end}"

        return Message(
            role=msg.role,
            content=snipped,
            tool_name=msg.tool_name,
            tool_call_id=msg.tool_call_id,
            timestamp=msg.timestamp,
            compressed=True,
            snip_marker=f"snipped_from_{original_len}_to_{len(snipped)}"
        )


class Microcompactor:
    """单条消息自动截断"""

    def __init__(self, config: CompressConfig):
        self.config = config

    def compact(self, msg: Message) -> Message:
        """对单条超长消息执行 microcompact"""
        if len(msg.content) <= self.config.microcompact_single_msg_chars:
            return msg

        # 截断策略：保留前 60% + 后 20%，中间用摘要标记
        total = len(msg.content)
        keep_front = int(total * 0.6)
        keep_back = int(total * 0.2)
        removed = total - keep_front - keep_back

        front = msg.content[:keep_front]
        back = msg.content[-keep_back:] if keep_back > 0 else ""

        compacted_content = (
            f"{front}\n\n"
            f"... [自动截断 {removed} 字符，保留 {keep_front + keep_back}/{total}] ...\n\n"
            f"{back}"
        )

        return Message(
            role=msg.role,
            content=compacted_content,
            tool_name=msg.tool_name,
            tool_call_id=msg.tool_call_id,
            timestamp=msg.timestamp,
            compressed=True,
            snip_marker=f"microcompact_{total}_to_{len(compacted_content)}"
        )


class CompactEngine:
    """重量级历史压缩 — 基于 LLM 的摘要压缩"""

    def __init__(self, config: CompressConfig):
        self.config = config

    def should_compact(self, messages: List[Message]) -> Tuple[bool, int]:
        """判断是否需要 compact"""
        total_tokens = sum(m.estimate_tokens() for m in messages)
        return total_tokens > self.config.compact_trigger_tokens, total_tokens

    def prepare_compact_prompt(self, messages: List[Message]) -> Tuple[List[Message], List[Message]]:
        """
        准备压缩：将消息分为「保留区」和「待压缩区」
        返回：(to_compress, to_keep)
        """
        # 保留 system prompts
        system_msgs = [m for m in messages if m.role == "system"]
        # 保留最近 N 轮
        recent_msgs = messages[-self.config.compact_keep_recent * 2:]  # user+assistant 算一轮
        # 待压缩：中间部分
        compress_candidates = messages[len(system_msgs):-len(recent_msgs)] if len(messages) > len(system_msgs) + len(recent_msgs) else []

        return compress_candidates, system_msgs + recent_msgs

    def generate_compact_summary_template(self, messages: List[Message]) -> str:
        """生成压缩摘要的提示词（供外部 LLM 调用时使用）"""
        history_text = "\n".join(
            f"[{m.role}] {m.content[:200]}..." if len(m.content) > 200 else f"[{m.role}] {m.content}"
            for m in messages
        )

        return f"""请将以下对话历史压缩成简洁的上下文摘要，保留关键信息：

要求：
1. 保留所有决策和结论
2. 保留重要的人物、时间、数字
3. 保留未完成的任务和待办
4. 删除重复和冗余内容
5. 控制在 {self.config.compact_target_tokens} tokens 以内

对话历史：
{history_text}

压缩后的摘要："""


class ContextCompressor:
    """上下文压缩主控制器 — 整合三层压缩策略"""

    def __init__(self, config: Optional[CompressConfig] = None):
        self.config = config or CompressConfig()
        self.snipper = Snipper(self.config)
        self.microcompactor = Microcompactor(self.config)
        self.compact_engine = CompactEngine(self.config)

        # 统计信息
        self.stats = {
            "total_compressions": 0,
            "snip_count": 0,
            "microcompact_count": 0,
            "compact_count": 0,
            "tokens_saved": 0,
        }

    def process(self, messages: List[Message]) -> List[Message]:
        """
        完整的压缩流水线：
        1. Microcompact — 先处理单条超长消息
        2. Snip — 裁剪工具调用细节
        3. Compact — 检查是否需要 LLM 摘要（返回标记，实际 LLM 调用由外部处理）
        """
        # Step 1: Microcompact
        step1 = []
        for msg in messages:
            if not msg.compressed and len(msg.content) > self.config.microcompact_single_msg_chars:
                step1.append(self.microcompactor.compact(msg))
                self.stats["microcompact_count"] += 1
            else:
                step1.append(msg)

        # Step 2: Snip
        step2 = self.snipper.snip_messages(step1)
        self.stats["snip_count"] += sum(1 for m, o in zip(step2, step1) if m.compressed and not o.compressed)

        # Step 3: 检查是否需要 compact
        needs_compact, current_tokens = self.compact_engine.should_compact(step2)

        self.stats["total_compressions"] += 1
        self.stats["tokens_saved"] += sum(m.estimate_tokens() for m in messages) - sum(m.estimate_tokens() for m in step2)

        return step2

    def needs_compact(self, messages: List[Message]) -> Tuple[bool, int]:
        """外部调用：检查是否需要 LLM compact"""
        return self.compact_engine.should_compact(messages)

    def get_compact_prompt(self, messages: List[Message]) -> str:
        """外部调用：获取 compact 提示词"""
        to_compress, _ = self.compact_engine.prepare_compact_prompt(messages)
        return self.compact_engine.generate_compact_summary_template(to_compress)

    def get_stats(self) -> dict:
        """获取压缩统计"""
        return self.stats.copy()

    def reset_stats(self):
        """重置统计"""
        self.stats = {k: 0 for k in self.stats}


# === 便捷函数 ===

def quick_compress(text: str, max_chars: int = 2000) -> str:
    """快速截断单条文本"""
    if len(text) <= max_chars:
        return text
    keep_front = int(max_chars * 0.7)
    return text[:keep_front] + f"\n... [截断至 {max_chars} 字符] ..."


def estimate_message_tokens(messages: List[Message]) -> int:
    """估算消息列表总 token 数"""
    return sum(m.estimate_tokens() for m in messages)


# === 测试 ===

def demo():
    """演示压缩效果"""
    compressor = ContextCompressor()

    messages = [
        Message(role="system", content="你是 Eve，一只 AI 助手。"),
        Message(role="user", content="帮我分析 600666"),
        Message(role="assistant", content="我来分析奥瑞德...", tool_name="stock_analysis"),
        Message(role="tool", content="A" * 5000),  # 超长工具结果
        Message(role="user", content="继续"),
        Message(role="assistant", content="根据分析结果...", tool_name="stock_analysis"),
        Message(role="tool", content="B" * 5000),  # 另一个超长结果
        Message(role="user", content="总结一下"),
    ]

    print(f"压缩前: {estimate_message_tokens(messages)} tokens, {len(messages)} 条消息")

    compressed = compressor.process(messages)

    print(f"压缩后: {estimate_message_tokens(compressed)} tokens, {len(compressed)} 条消息")
    print(f"统计: {compressor.get_stats()}")

    for i, m in enumerate(compressed):
        marker = " [COMPRESSED]" if m.compressed else ""
        print(f"  [{i}] {m.role}: {m.content[:80]}...{marker}")


if __name__ == "__main__":
    demo()
