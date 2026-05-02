"""
Strategy Parser — 自然语言策略 → 参数化交易规则

参考 Polystrat 的 Layer 1 架构：
- 用户用自然语言描述交易策略
- LLM 解析为结构化 JSON 规则
- 规则引擎自动检查是否满足条件
- 支持策略版本管理和历史对比

核心理念（来自 Polystrat）：
策略不应该是写死的代码，应该是人类可读、LLM 可执行的自然语言描述。
"""

import re
import time
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ConditionOp(Enum):
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="
    NEQ = "!="
    IN = "in"
    MATCHES = "matches"
    BETWEEN = "between"


@dataclass
class Condition:
    """单个条件"""
    field: str              # 字段名: volume_ratio, price, change_pct 等
    op: str                 # 操作符: > >= < <= == != in matches between
    value: any              # 值
    description: str = ""   # 可读描述

    def check(self, data: dict) -> bool:
        """检查数据是否满足此条件"""
        actual = data.get(self.field)
        if actual is None:
            return False

        try:
            if self.op == ">":     return actual > self.value
            if self.op == ">=":    return actual >= self.value
            if self.op == "<":     return actual < self.value
            if self.op == "<=":     return actual <= self.value
            if self.op == "==":    return actual == self.value
            if self.op == "!=":    return actual != self.value
            if self.op == "in":    return actual in self.value
            if self.op == "matches": return bool(re.search(self.value, str(actual)))
            if self.op == "between": return self.value[0] <= actual <= self.value[1]
        except (TypeError, ValueError):
            return False
        return False


@dataclass
class RuleSet:
    """一组规则（入场/出场/仓位）"""
    name: str
    conditions: list[Condition]
    logic: str = "and"  # and / or
    action: str = ""    # buy / sell / hold
    confidence: str = "medium"  # low / medium / high

    def evaluate(self, data: dict) -> bool:
        """评估是否满足所有条件"""
        if not self.conditions:
            return True
        results = [c.check(data) for c in self.conditions]
        if self.logic == "and":
            return all(results)
        return any(results)

    def explain(self) -> str:
        """人类可读的规则解释"""
        parts = [f"{c.description or f'{c.field} {c.op} {c.value}'}" for c in self.conditions]
        connector = " 且 " if self.logic == "and" else " 或 "
        return connector.join(parts)


@dataclass
class TradingStrategy:
    """完整的交易策略"""
    name: str
    description: str
    entry_rules: RuleSet          # 入场条件
    exit_rules: RuleSet           # 出场条件
    stop_loss: Optional[RuleSet] = None     # 止损
    take_profit: Optional[RuleSet] = None   # 止盈
    position_rules: dict = None   # 仓位规则
    source_text: str = ""         # 原始自然语言
    confidence: str = "medium"
    created_at: float = field(default_factory=time.time)

    def evaluate_entry(self, market_data: dict) -> dict:
        """评估是否应该入场"""
        entry_ok = self.entry_rules.evaluate(market_data)
        return {
            "action": "buy" if entry_ok else "wait",
            "strategy": self.name,
            "entry_met": entry_ok,
            "reason": self.entry_rules.explain() if entry_ok else "入场条件不满足",
        }

    def evaluate_exit(self, market_data: dict, position: dict) -> dict:
        """评估是否应该出场"""
        exit_ok = self.exit_rules.evaluate(market_data)
        sl_ok = self.stop_loss.evaluate(market_data) if self.stop_loss else False
        tp_ok = self.take_profit.evaluate(market_data) if self.take_profit else False

        if exit_ok or sl_ok or tp_ok:
            reason = []
            if exit_ok: reason.append(f"出场: {self.exit_rules.explain()}")
            if sl_ok: reason.append(f"止损: {self.stop_loss.explain()}")
            if tp_ok: reason.append(f"止盈: {self.take_profit.explain()}")
            return {"action": "sell", "reason": " | ".join(reason)}

        return {"action": "hold", "reason": "出场条件不满足"}

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "confidence": self.confidence,
            "entry_rules": {
                "conditions": [
                    {"field": c.field, "op": c.op, "value": str(c.value), "desc": c.description}
                    for c in self.entry_rules.conditions
                ],
                "logic": self.entry_rules.logic,
            },
            "exit_rules": {
                "conditions": [
                    {"field": c.field, "op": c.op, "value": str(c.value), "desc": c.description}
                    for c in self.exit_rules.conditions
                ],
            },
            "stop_loss": self.stop_loss.explain() if self.stop_loss else "无",
            "take_profit": self.take_profit.explain() if self.take_profit else "无",
            "position_rules": self.position_rules or {},
        }

    def to_markdown(self) -> str:
        """输出为 Markdown 格式（策略配置文件）"""
        lines = [
            f"# 策略: {self.name}",
            "",
            f"> {self.description}",
            "",
            "## 入场条件",
            "",
        ]
        for c in self.entry_rules.conditions:
            lines.append(f"- {c.description or f'{c.field} {c.op} {c.value}'}")

        lines.append("")
        lines.append("## 出场条件")
        lines.append("")
        for c in self.exit_rules.conditions:
            lines.append(f"- {c.description or f'{c.field} {c.op} {c.value}'}")

        if self.stop_loss:
            lines.extend(["", "## 止损", "", f"- {self.stop_loss.explain()}"])
        if self.take_profit:
            lines.extend(["", "## 止盈", "", f"- {self.take_profit.explain()}"])
        if self.position_rules:
            lines.extend(["", "## 仓位规则", ""])
            for k, v in self.position_rules.items():
                lines.append(f"- {k}: {v}")

        lines.extend(["", "## 策略置信度", "", f"- {self.confidence}"])
        return "\n".join(lines)


# ============================================================
# 预设策略模板（对应 Polystrat 的 risky/balanced 预设）
# ============================================================

PRESET_STRATEGIES = {
    "强势打板": TradingStrategy(
        name="强势打板",
        description="只做强势板，严格止损，快进快出",
        entry_rules=RuleSet("entry", conditions=[
            Condition("volume_ratio", ">", 3, "集合竞价量比 > 3"),
            Condition("open_change_pct", "between", (0.02, 0.05), "高开2%-5%"),
            Condition("is_limit_up", "==", False, "非一字板"),
            Condition("sector_alignment", "==", True, "板块内有共振"),
        ]),
        exit_rules=RuleSet("exit", conditions=[
            Condition("days_held", ">", 3, "3天不涨出局"),
        ]),
        stop_loss=RuleSet("sl", conditions=[
            Condition("loss_pct", ">", 0.05, "亏损超过5%"),
        ], action="sell"),
        take_profit=RuleSet("tp", conditions=[
            Condition("gain_pct", ">", 0.15, "盈利超过15%"),
        ], action="sell"),
        position_rules={"单只最大仓位": "20%", "同板块最多": "2只", "杠杆": "无"},
    ),
    "低吸回踩": TradingStrategy(
        name="低吸回踩",
        description="强势股回踩支撑位买入，不追高",
        entry_rules=RuleSet("entry", conditions=[
            Condition("price_vs_high", "<", 0.85, "距近20日高点回落超过15%"),
            Condition("volume_ratio", "<", 0.7, "缩量到均量70%以下"),
            Condition("support_test", "==", True, "触及关键支撑位"),
            Condition("rsi", "between", (25, 40), "RSI 处于超卖区间"),
        ]),
        exit_rules=RuleSet("exit", conditions=[
            Condition("gain_pct", ">", 0.08, "反弹8%以上考虑出场"),
            Condition("days_held", ">", 10, "最长持有10天"),
        ]),
        stop_loss=RuleSet("sl", conditions=[
            Condition("break_support", "==", True, "跌破支撑位"),
        ], action="sell"),
        position_rules={"单只最大仓位": "15%", "分批建仓": "3次"},
    ),
    "趋势跟踪": TradingStrategy(
        name="趋势跟踪",
        description="均线多头排列时持有，跌破均线离场",
        entry_rules=RuleSet("entry", conditions=[
            Condition("ma5_vs_ma20", ">", 0, "5日线在20日线上方"),
            Condition("price_vs_ma5", ">", 0, "价格在5日线上方"),
            Condition("volume_trend", "==", "increasing", "量能趋势向上"),
        ]),
        exit_rules=RuleSet("exit", conditions=[
            Condition("price_below_ma5", "==", True, "收盘跌破5日线"),
        ]),
        stop_loss=RuleSet("sl", conditions=[
            Condition("loss_pct", ">", 0.08, "亏损超过8%"),
        ], action="sell"),
        position_rules={"单只最大仓位": "30%", "加仓规则": "盈利5%后加仓一次"},
    ),
}


# ============================================================
# 策略解析器（LLM 辅助）
# ============================================================

class StrategyParser:
    """
    将自然语言策略解析为结构化规则。
    
    支持两种模式：
    1. 预设匹配：检测关键词匹配预设策略
    2. LLM 解析：用 LLM 从自然语言提取规则
    
    对应 Polystrat 的 "Control trading strategy in plain English"。
    """

    # 关键词 → 预设策略名的映射
    KEYWORD_MAP = {
        "打板": "强势打板",
        "强势板": "强势打板",
        "追板": "强势打板",
        "封板": "强势打板",
        "低吸": "低吸回踩",
        "回踩": "低吸回踩",
        "超卖": "低吸回踩",
        "均线": "趋势跟踪",
        "趋势": "趋势跟踪",
        "MA": "趋势跟踪",
        "5日线": "趋势跟踪",
    }

    def parse(self, text: str) -> TradingStrategy:
        """解析自然语言策略描述"""
        # 先尝试匹配预设
        preset = self._match_preset(text)
        if preset:
            # 用用户描述覆盖原描述
            preset.source_text = text
            return preset

        # 如果没有匹配，返回一个通用框架（需要 LLM 补充）
        return self._build_generic(text)

    def _match_preset(self, text: str) -> Optional[TradingStrategy]:
        """匹配预设策略"""
        for keyword, strategy_name in self.KEYWORD_MAP.items():
            if keyword in text:
                return self._copy_strategy(PRESET_STRATEGIES[strategy_name])
        return None

    def _copy_strategy(self, strategy: TradingStrategy) -> TradingStrategy:
        """深拷贝策略"""
        return TradingStrategy(
            name=strategy.name,
            description=strategy.description,
            entry_rules=self._copy_ruleset(strategy.entry_rules),
            exit_rules=self._copy_ruleset(strategy.exit_rules),
            stop_loss=self._copy_ruleset(strategy.stop_loss) if strategy.stop_loss else None,
            take_profit=self._copy_ruleset(strategy.take_profit) if strategy.take_profit else None,
            position_rules=dict(strategy.position_rules) if strategy.position_rules else None,
            confidence=strategy.confidence,
        )

    def _copy_ruleset(self, ruleset: RuleSet) -> RuleSet:
        return RuleSet(
            name=ruleset.name,
            conditions=[
                Condition(c.field, c.op, c.value, c.description)
                for c in ruleset.conditions
            ],
            logic=ruleset.logic,
            action=ruleset.action,
            confidence=ruleset.confidence,
        )

    def _build_generic(self, text: str) -> TradingStrategy:
        """从自然语言构建通用策略框架"""
        return TradingStrategy(
            name="自定义策略",
            description=text,
            entry_rules=RuleSet("entry", conditions=[], ),
            exit_rules=RuleSet("exit", conditions=[], ),
            source_text=text,
            confidence="low",
        )


# ============================================================
# 策略引擎（运行策略检查）
# ============================================================

class StrategyEngine:
    """
    策略引擎 — 对市场数据应用策略规则。
    
    对应 Polystrat 的实时概率重算：
    - 每次有新市场数据时调用
    - 返回买入/卖出/持有的建议
    """

    def __init__(self):
        self.strategies: dict[str, TradingStrategy] = {}
        self.active_strategy: str = ""
        self.trade_log: list[dict] = []

    def register(self, strategy: TradingStrategy):
        """注册策略"""
        self.strategies[strategy.name] = strategy
        if not self.active_strategy:
            self.active_strategy = strategy.name

    def set_active(self, name: str):
        """设置当前活跃策略"""
        if name in self.strategies:
            self.active_strategy = name

    def evaluate(self, market_data: dict, position: dict = None) -> dict:
        """
        评估当前市场数据，返回交易建议。
        
        Args:
            market_data: {
                "price": float,
                "volume_ratio": float,  # 量比
                "open_change_pct": float,  # 开盘涨幅
                "is_limit_up": bool,
                "sector_alignment": bool,
                "rsi": float,
                "ma5_vs_ma20": float,
                ...
            }
            position: 当前持仓（None = 空仓）
        
        Returns:
            {
                "action": "buy" | "sell" | "hold",
                "strategy": "策略名",
                "reason": "原因",
                "confidence": "high" | "medium" | "low"
            }
        """
        strategy = self.strategies.get(self.active_strategy)
        if not strategy:
            return {"action": "hold", "reason": "无活跃策略", "confidence": "low"}

        if position is None:
            # 空仓 → 评估入场
            result = strategy.evaluate_entry(market_data)
        else:
            # 持仓 → 评估出场
            result = strategy.evaluate_exit(market_data, position)

        result["strategy"] = strategy.name
        result["confidence"] = strategy.confidence

        # 记录日志
        self.trade_log.append({
            "time": time.time(),
            "action": result["action"],
            "reason": result["reason"],
            "market": {k: v for k, v in market_data.items() if not isinstance(v, (list, dict))},
        })

        return result

    def get_active_strategy(self) -> TradingStrategy:
        """获取当前活跃策略"""
        return self.strategies.get(self.active_strategy)

    def list_strategies(self) -> list[dict]:
        """列出所有策略"""
        return [
            {"name": s.name, "description": s.description, "confidence": s.confidence}
            for s in self.strategies.values()
        ]

    def export_strategy(self, name: str = None) -> str:
        """导出策略为 Markdown"""
        if name:
            strategy = self.strategies.get(name)
        else:
            strategy = self.get_active_strategy()
        if not strategy:
            return "策略不存在"
        return strategy.to_markdown()

    def get_trade_log(self, n: int = 10) -> list[dict]:
        """获取最近的交易日志"""
        return self.trade_log[-n:]


# ============================================================
# 与 market_data 的适配器（对接你的现有数据源）
# ============================================================

def adapt_600666_data(raw_data: dict) -> dict:
    """
    将 600666 的 Level-2 数据转为策略引擎需要的格式。
    
    输入（你的现有数据）:
        {
            "price": 6.21,
            "volume": 280000,
            "limit_up_price": 6.65,
            "open_price": 6.10,
            "prev_close": 6.05,
            "high": 6.65,
            "low": 6.05,
            "ma5": 5.8,
            "ma20": 5.2,
            "rsi": 65,
            "volume_ratio": 3.2,
            "sector": "算力",
            "sector_alignment": True,
        }
    
    输出（策略引擎格式）:
        {
            "price": 6.21,
            "volume_ratio": 3.2,
            "open_change_pct": 0.0083,  # (6.10-6.05)/6.05
            "is_limit_up": False,
            "sector_alignment": True,
            "ma5_vs_ma20": 0.6,  # (5.8-5.2)/5.2
            "rsi": 65,
            ...
        }
    """
    prev_close = raw_data.get("prev_close", raw_data.get("pre_close", 1))
    open_price = raw_data.get("open_price", raw_data.get("open", prev_close))
    ma5 = raw_data.get("ma5", 0)
    ma20 = raw_data.get("ma20", 0)

    return {
        "price": raw_data.get("price", raw_data.get("close", 0)),
        "volume_ratio": raw_data.get("volume_ratio", 1.0),
        "open_change_pct": (open_price - prev_close) / prev_close if prev_close else 0,
        "is_limit_up": raw_data.get("price", 0) >= raw_data.get("limit_up_price", float("inf")),
        "sector_alignment": raw_data.get("sector_alignment", False),
        "ma5_vs_ma20": (ma5 - ma20) / ma20 if ma20 else 0,
        "rsi": raw_data.get("rsi", 50),
        "change_pct": (raw_data.get("price", prev_close) - prev_close) / prev_close if prev_close else 0,
        "high": raw_data.get("high", 0),
        "low": raw_data.get("low", 0),
        "volume": raw_data.get("volume", 0),
    }


# ============================================================
# 快捷工具函数
# ============================================================

def quick_parse(text: str) -> TradingStrategy:
    """快速解析策略描述"""
    parser = StrategyParser()
    return parser.parse(text)

def quick_evaluate(strategy_text: str, market_data: dict) -> dict:
    """快速：解析策略 + 评估市场"""
    parser = StrategyParser()
    strategy = parser.parse(strategy_text)
    engine = StrategyEngine()
    engine.register(strategy)
    return engine.evaluate(market_data)
