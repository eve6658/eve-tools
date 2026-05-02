"""
Harness Audit — Agent 性能审计系统

参考 ECC (Everything Claude Code) 的 /harness-audit 命令：
- 定期检查 agent 性能指标
- Token 效率、错误率、响应时间
- 自动生成 Markdown 报告
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class AuditLevel(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class AuditMetric:
    """审计指标"""
    name: str
    value: float
    threshold_warn: float
    threshold_fail: float
    unit: str = ""
    description: str = ""

    @property
    def status(self) -> AuditLevel:
        if self.value >= self.threshold_fail:
            return AuditLevel.FAIL
        if self.value >= self.threshold_warn:
            return AuditLevel.WARN
        return AuditLevel.PASS

    @property
    def icon(self) -> str:
        return {
            AuditLevel.PASS: "✅",
            AuditLevel.WARN: "⚠️",
            AuditLevel.FAIL: "❌",
        }[self.status]


# ============================================================
# 审计引擎
# ============================================================

class TurnRecord:
    """单次 Turn 记录"""
    def __init__(self):
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.errors: int = 0
        self.tools_called: list[str] = []
        self.success: bool = True

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000 if self.end_time else 0


class HarnessAudit:
    """
    Harness 性能审计。

    检查项：
    - response_time: 平均响应时间（ms）
    - token_efficiency: 输出/输入比
    - error_rate: 错误率
    - compaction_ratio: 压缩率
    - tool_usage: 工具使用多样性
    - memory_health: 记忆系统健康度
    """

    def __init__(self):
        self.turns: list[TurnRecord] = []
        self.sessions: list[dict] = []

    # ============================================================
    # 数据收集
    # ============================================================

    def record_turn(self, record: TurnRecord):
        """记录一次 Turn"""
        self.turns.append(record)

    def track_turn(self, start_time: float, end_time: float,
                   input_tokens: int = 0, output_tokens: int = 0,
                   errors: int = 0, tools: list[str] = None,
                   success: bool = True):
        """便捷记录 Turn"""
        record = TurnRecord()
        record.start_time = start_time
        record.end_time = end_time
        record.input_tokens = input_tokens
        record.output_tokens = output_tokens
        record.errors = errors
        record.tools_called = tools or []
        record.success = success
        self.turns.append(record)

    # ============================================================
    # 审计
    # ============================================================

    def run_audit(self) -> list[AuditMetric]:
        """运行完整审计"""
        metrics = []

        # 1. 平均响应时间
        if self.turns:
            avg_duration = sum(t.duration_ms for t in self.turns) / len(self.turns)
        else:
            avg_duration = 0
        metrics.append(AuditMetric(
            name="平均响应时间",
            value=avg_duration,
            threshold_warn=5000,   # 5秒 警告
            threshold_fail=15000,  # 15秒 失败
            unit="ms",
            description="从发送到收到完整回复的平均时间",
        ))

        # 2. Token 效率（输出/输入比）
        total_input = sum(t.input_tokens for t in self.turns)
        total_output = sum(t.output_tokens for t in self.turns)
        efficiency = total_output / total_input if total_input > 0 else 0
        metrics.append(AuditMetric(
            name="Token 效率",
            value=efficiency,
            threshold_warn=0.5,   # 低效
            threshold_fail=0.1,   # 极低效
            unit="",
            description="输出 token / 输入 token，过低说明输入浪费",
        ))

        # 3. 错误率
        total_turns = len(self.turns)
        error_turns = sum(1 for t in self.turns if not t.success or t.errors > 0)
        error_rate = error_turns / total_turns if total_turns > 0 else 0
        metrics.append(AuditMetric(
            name="错误率",
            value=error_rate * 100,
            threshold_warn=10,  # 10% 警告
            threshold_fail=30,  # 30% 失败
            unit="%",
            description="失败 Turn 占比",
        ))

        # 4. 工具使用多样性
        all_tools = set()
        for t in self.turns:
            all_tools.update(t.tools_called)
        tool_variety = len(all_tools)
        metrics.append(AuditMetric(
            name="工具多样性",
            value=tool_variety,
            threshold_warn=999,  # 不会警告
            threshold_fail=999,
            unit="种",
            description="使用过的工具种类数",
        ))

        # 5. 总 Token 消耗
        total_tokens = total_input + total_output
        metrics.append(AuditMetric(
            name="总 Token 消耗",
            value=total_tokens,
            threshold_warn=100000,
            threshold_fail=500000,
            unit="tokens",
            description="本会话总 token 消耗",
        ))

        # 6. 平均 Turn Token
        avg_tokens = total_tokens / total_turns if total_turns > 0 else 0
        metrics.append(AuditMetric(
            name="平均 Turn Token",
            value=avg_tokens,
            threshold_warn=5000,
            threshold_fail=15000,
            unit="tokens",
            description="每次 Turn 平均消耗",
        ))

        return metrics

    # ============================================================
    # 报告
    # ============================================================

    def generate_report(self) -> str:
        """生成 Markdown 审计报告"""
        metrics = self.run_audit()
        total_turns = len(self.turns)

        lines = [
            "## 🔍 Harness Audit 报告",
            "",
            f"审计时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"总 Turn 数: {total_turns}",
            "",
            "### 指标",
            "",
        ]

        # 汇总
        passes = sum(1 for m in metrics if m.status.value == "pass")
        warns = sum(1 for m in metrics if m.status.value == "warn")
        fails = sum(1 for m in metrics if m.status.value == "fail")
        score = passes * 100 + warns * 50  # / (passes+warns+fails) * 100
        max_score = (passes + warns + fails) * 100
        pct = score / max_score * 100 if max_score > 0 else 0

        for m in metrics:
            val_str = f"{m.value:.2f}{m.unit}" if m.unit else f"{m.value:.2f}"
            lines.append(f"- {m.icon} **{m.name}**: {val_str} "
                        f"(警告>{m.threshold_warn}{m.unit}, 失败>{m.threshold_fail}{m.unit})")

        lines.append("")
        lines.append(f"**健康度: {pct:.0f}%** "
                     f"({passes} 通过 / {warns} 警告 / {fails} 失败)")

        # 最近的 Turn
        if self.turns:
            lines.append("")
            lines.append("### 最近 Turn")
            for t in self.turns[-5:]:
                status = "✅" if t.success else "❌"
                tools_str = ", ".join(t.tools_called[:3]) if t.tools_called else "无工具"
                lines.append(f"- {status} {t.duration_ms:.0f}ms | "
                           f"{t.input_tokens}→{t.output_tokens} tokens | "
                           f"工具: {tools_str}")

        return "\n".join(lines)

    def get_summary(self) -> dict:
        """获取简要摘要"""
        metrics = self.run_audit()
        return {
            "turns": len(self.turns),
            "metrics": {m.name: {"value": m.value, "status": m.status.value} for m in metrics},
        }

    def reset(self):
        """重置审计数据"""
        self.turns.clear()
