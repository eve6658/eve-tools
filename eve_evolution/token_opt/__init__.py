"""
Token 优化系统 — 按需选择模型 + 自动压缩 + 成本追踪

参考 ECC (Everything Claude Code) 的 Token Optimization：
- Sonnet/Opus 按需切换，80% 任务用轻量模型
- MAX_THINKING_TOKENS 限制思考 token
- 自动压缩阈值控制
"""

import time
from dataclasses import dataclass, field
from collections import defaultdict


# ============================================================
# Token 预算
# ============================================================

@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    max_thinking_tokens: int = 32000
    cost_per_1k_input: float = 0.0   # USD
    cost_per_1k_output: float = 0.0  # USD
    supports_thinking: bool = False

# 常用模型配置
MODELS = {
    "worker": ModelConfig(
        name="worker (OpenRouter Auto)",
        max_thinking_tokens=10000,
    ),
    "coder": ModelConfig(
        name="coder (Claude Sonnet)",
        max_thinking_tokens=32000,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        supports_thinking=True,
    ),
    "researcher": ModelConfig(
        name="researcher (Gemini Pro)",
        max_thinking_tokens=16000,
    ),
    "mimo": ModelConfig(
        name="main (MiMo V2 Omni)",
        max_thinking_tokens=8000,
    ),
}


# ============================================================
# Token 追踪
# ============================================================

@dataclass
class TokenUsage:
    """单次 token 用量"""
    model: str
    input_tokens: int
    output_tokens: int
    thinking_tokens: int = 0
    cost: float = 0.0
    timestamp: float = field(default_factory=time.time)
    label: str = ""  # 任务标签


class TokenTracker:
    """
    Token 用量追踪。

    对应 ECC 的 Token Optimization 指标。
    """

    def __init__(self):
        self.usage: list[TokenUsage] = []
        self.daily_budget: float = 0.0  # 0 = 无限制

    def track(self, model: str, input_tokens: int, output_tokens: int,
              thinking_tokens: int = 0, label: str = "") -> TokenUsage:
        """记录一次 token 使用"""
        config = MODELS.get(model)
        cost = 0.0
        if config:
            cost = (input_tokens * config.cost_per_1k_input / 1000 +
                    output_tokens * config.cost_per_1k_output / 1000)

        usage = TokenUsage(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            thinking_tokens=thinking_tokens,
            cost=cost,
            label=label,
        )
        self.usage.append(usage)
        return usage

    def get_usage(self, period: str = "daily") -> dict:
        """获取指定周期的用量统计"""
        now = time.time()
        if period == "daily":
            cutoff = now - 86400
        elif period == "weekly":
            cutoff = now - 7 * 86400
        else:
            cutoff = 0

        recent = [u for u in self.usage if u.timestamp >= cutoff]

        return {
            "total_calls": len(recent),
            "total_input": sum(u.input_tokens for u in recent),
            "total_output": sum(u.output_tokens for u in recent),
            "total_thinking": sum(u.thinking_tokens for u in recent),
            "total_cost": sum(u.cost for u in recent),
            "by_model": self._by_model(recent),
        }

    def _by_model(self, usages: list[TokenUsage]) -> dict:
        """按模型聚合"""
        result = defaultdict(lambda: {"calls": 0, "input": 0, "output": 0, "cost": 0.0})
        for u in usages:
            result[u.model]["calls"] += 1
            result[u.model]["input"] += u.input_tokens
            result[u.model]["output"] += u.output_tokens
            result[u.model]["cost"] += u.cost
        return dict(result)

    def get_total_cost(self, period: str = "daily") -> float:
        return self.get_usage(period)["total_cost"]

    def should_alert(self) -> bool:
        """是否应该触发预算警告"""
        if self.daily_budget <= 0:
            return False
        return self.get_total_cost("daily") > self.daily_budget


# ============================================================
# 智能模型路由（对应 ECC 的 /model 命令）
# ============================================================

class ModelRouter:
    """
    智能模型路由 — 根据任务复杂度选最优模型。

    对应 ECC 的推荐策略：
    - Sonnet 处理 80%+ 的常规任务
    - Opus 仅用于深度架构推理
    - 免费模型用于简单事务
    """

    COMPLEXITY_KEYWORDS = {
        "complex": [
            "架构", "重构", "设计模式", "性能优化", "算法",
            "architecture", "refactor", "algorithm", "debug complex",
            "深度分析", "根因分析", "原理", "对比分析",
        ],
        "research": [
            "搜索", "调研", "分析", "对比", "总结",
            "research", "find", "compare", "summarize",
            "查一下", "了解", "学习",
        ],
        "simple": [
            "格式化", "重命名", "复制", "删除", "列出来",
            "format", "rename", "list", "show", "copy",
            "排版", "整理", "检查",
        ],
    }

    def select(self, task_description: str = "", complexity: str = "auto") -> str:
        """选择模型"""
        if complexity == "auto":
            complexity = self._assess_complexity(task_description)

        routing = {
            "complex": "coder",       # Claude Sonnet
            "research": "researcher", # Gemini Pro
            "simple": "worker",       # OpenRouter Auto (免费)
        }
        return routing.get(complexity, "worker")

    def _assess_complexity(self, task: str) -> str:
        """评估任务复杂度"""
        task_lower = task.lower()

        scores = {"complex": 0, "research": 0, "simple": 0}
        for complexity, keywords in self.COMPLEXITY_KEYWORDS.items():
            for kw in keywords:
                if kw in task_lower:
                    scores[complexity] += 1

        # 找最高分
        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "simple"  # 默认简单
        return best

    def should_upgrade(self, usage: TokenUsage) -> bool:
        """是否应该升级模型（当前模型无法处理）"""
        config = MODELS.get(usage.model)
        if not config:
            return False
        return usage.output_tokens >= config.max_thinking_tokens * 0.9


# ============================================================
# 自动压缩控制
# ============================================================

class AutoCompactor:
    """
    自动上下文压缩控制。

    对应 ECC 的 CLAUDE_AUTOCOMPACT_PCT_OVERRIDE：
    - 当上下文达到阈值时触发压缩
    - 保留开头 + 结尾，中间摘要
    """

    def __init__(self, compact_pct: float = 0.5):
        self.compact_pct = compact_pct  # 达到 max_tokens 的多少比例时触发

    def should_compact(self, current_tokens: int, max_tokens: int) -> bool:
        """是否应该触发压缩"""
        threshold = max_tokens * self.compact_pct
        return current_tokens >= threshold

    def compact(self, messages: list[dict], keep_head: int = 5, keep_tail: int = 3) -> list[dict]:
        """
        压缩消息列表。

        保留开头 keep_head 条 + 结尾 keep_tail 条，
        中间替换为摘要标记。
        """
        if len(messages) <= keep_head + keep_tail:
            return messages

        head = messages[:keep_head]
        tail = messages[-keep_tail:]
        removed = len(messages) - keep_head - keep_tail

        summary = {
            "role": "system",
            "content": f"[上下文已自动压缩，移除了 {removed} 条中间消息]",
            "is_compact": True,
        }

        return head + [summary] + tail


# ============================================================
# Token 报告
# ============================================================

def format_token_report(tracker: TokenTracker, period: str = "daily") -> str:
    """格式化 token 使用报告"""
    usage = tracker.get_usage(period)

    lines = [
        f"## Token 使用报告 ({period})",
        "",
        f"- 调用次数: {usage['total_calls']}",
        f"- 总 Input: {usage['total_input']:,} tokens",
        f"- 总 Output: {usage['total_output']:,} tokens",
        f"- 总 Thinking: {usage['total_thinking']:,} tokens",
        f"- 总成本: ${usage['total_cost']:.4f}",
        "",
        "### 按模型",
    ]

    for model, stats in usage["by_model"].items():
        lines.append(f"- **{model}**: {stats['calls']} 次, "
                     f"input {stats['input']:,}, output {stats['output']:,}, "
                     f"成本 ${stats['cost']:.4f}")

    return "\n".join(lines)
