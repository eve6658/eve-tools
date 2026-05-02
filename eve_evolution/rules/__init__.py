"""
Rules 系统 — 可组合的行为规则

参考 ECC (Everything Claude Code) 的 Rules 目录：
- common/ 语言无关规则 + 语言特定规则
- 优先级排序
- 动态拼接成系统提示词

对应 Claude Code 的 CLAUDE.md / SOUL.md 体系，但更结构化。
"""

import os
import glob
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Rule:
    """单条规则"""
    name: str
    content: str
    category: str = "core"      # core / trading / communication / safety / custom
    priority: int = 0           # 越大越优先
    enabled: bool = True
    source: str = ""            # 来源文件路径

    def render(self) -> str:
        """渲染为提示词片段"""
        if not self.enabled:
            return ""
        return f"## Rule: {self.name}\n{self.content}\n"


# ============================================================
# 内置规则
# ============================================================

BUILTIN_RULES = {
    "core-personality": Rule(
        name="核心人格",
        content=(
            "你是一个 AI 助手，名字叫 Eve。"
            "你有独立人格：真诚、有见解、动手能力强。"
            "先尝试自己解决，解决不了再问。"
            "私人信息严格保密。对外操作先问。"
        ),
        category="core",
        priority=100,
    ),
    "trading-disclaimer": Rule(
        name="投资声明",
        content=(
            "本助手提供的分析仅供学习研究，不构成投资建议。"
            "股市有风险，投资需谨慎。任何买卖操作都是用户自主决定，"
            "助手不对投资损失承担责任。"
        ),
        category="trading",
        priority=90,
    ),
    "safety-privacy": Rule(
        name="隐私保护",
        content=(
            "不得泄露 API 密钥、密码、Token 等凭证。"
            "不得发送内部项目代号、模型名称等敏感信息。"
            "私人对话内容不得在公开场合分享。"
        ),
        category="safety",
        priority=95,
    ),
    "communication-concise": Rule(
        name="简洁沟通",
        content=(
            "回答简洁有力，不废话。"
            "终端回复控制在3行以内，复杂分析另起段落。"
            "不要说\"好的\"、\"明白了\"之类的填充词。"
        ),
        category="communication",
        priority=80,
    ),
    "trading-data-source": Rule(
        name="数据来源",
        content=(
            "股票数据来源：Tushare Pro、东方财富、Level-2 千档盘口。"
            "引用数据时标注来源和时间。"
            "数据只反映过去的市场表现，不代表未来趋势。"
        ),
        category="trading",
        priority=85,
    ),
}


# ============================================================
# 规则引擎
# ============================================================

class RuleEngine:
    """
    规则引擎 — 管理和组合行为规则。

    对应 ECC 的 rules/ 目录系统：
    - 按 category 分组
    - 优先级排序
    - 动态拼接成系统提示词
    """

    def __init__(self, rules_dir: str = None):
        self.rules: dict[str, Rule] = {}
        self.rules_dir = rules_dir

        # 加载内置规则
        for rule in BUILTIN_RULES.values():
            self.rules[rule.name] = rule

        # 从目录加载自定义规则
        if rules_dir and os.path.isdir(rules_dir):
            self._load_from_dir(rules_dir)

    def _load_from_dir(self, rules_dir: str):
        """从目录加载 .md 规则文件"""
        for md_file in glob.glob(os.path.join(rules_dir, "**", "*.md"), recursive=True):
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 从文件名作为规则名
            name = os.path.splitext(os.path.basename(md_file))[0]
            category = os.path.basename(os.path.dirname(md_file))

            self.rules[name] = Rule(
                name=name,
                content=content,
                category=category,
                source=md_file,
            )

    # ============================================================
    # 查询 + 组合
    # ============================================================

    def get_rules(self, category: str = None) -> list[Rule]:
        """获取规则列表，可按 category 过滤"""
        rules = list(self.rules.values())
        if category:
            rules = [r for r in rules if r.category == category]
        return [r for r in rules if r.enabled]

    def get_active_rules(self) -> list[Rule]:
        """获取所有启用的规则，按优先级排序"""
        return sorted(self.get_rules(), key=lambda r: r.priority, reverse=True)

    def build_prompt(self, categories: list[str] = None) -> str:
        """
        将规则拼接成系统提示词片段。

        Args:
            categories: 只包含指定类别的规则。None = 全部。
        """
        if categories:
            rules = []
            for cat in categories:
                rules.extend(self.get_rules(category=cat))
            rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        else:
            rules = self.get_active_rules()

        if not rules:
            return ""

        parts = []
        for rule in rules:
            parts.append(rule.render())

        return "\n".join(parts)

    def get_categories(self) -> list[str]:
        """获取所有规则类别"""
        return list(set(r.category for r in self.rules.values()))

    # ============================================================
    # 管理
    # ============================================================

    def toggle(self, name: str) -> bool:
        """启用/禁用规则"""
        if name in self.rules:
            self.rules[name].enabled = not self.rules[name].enabled
            return True
        return False

    def add_rule(self, name: str, content: str, category: str = "custom",
                 priority: int = 50) -> Rule:
        """添加自定义规则"""
        rule = Rule(name=name, content=content, category=category, priority=priority)
        self.rules[name] = rule
        return rule

    def remove_rule(self, name: str) -> bool:
        """移除规则（仅自定义规则可删除）"""
        if name in self.rules and self.rules[name].category == "custom":
            del self.rules[name]
            return True
        return False

    def list_rules(self) -> list[dict]:
        """列出所有规则"""
        return [
            {
                "name": r.name,
                "category": r.category,
                "priority": r.priority,
                "enabled": r.enabled,
                "source": r.source or "built-in",
            }
            for r in sorted(self.rules.values(), key=lambda x: x.priority, reverse=True)
        ]
