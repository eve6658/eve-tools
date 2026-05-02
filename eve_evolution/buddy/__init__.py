"""
Buddy 电子伴侣系统 — Eve 的 AI 伴侣

参考 Claude Code 的 src/buddy/ 设计：
- 确定性生成（同一用户永远生成同一个宠物）
- 18 种物种，5 级稀有度，5 项属性
- LLM 生成名字和性格
- ASCII/Unicode 终端渲染
"""

from .types import Companion, CompanionBones, CompanionSoul, SPECIES, Rarity, RARITY_WEIGHTS, STAT_NAMES, STAT_COLORS
from .companion import generate_companion, get_or_create_companion, get_companion, hatch_companion
from .prompt import get_companion_prompt, format_companion_card
from .render import render_companion, render_bubble, render_pet_hearts

__all__ = [
    "Companion", "CompanionBones", "CompanionSoul",
    "SPECIES", "Rarity", "RARITY_WEIGHTS", "STAT_NAMES", "STAT_COLORS",
    "generate_companion", "get_or_create_companion", "get_companion", "hatch_companion",
    "get_companion_prompt",
    "render_companion", "render_bubble", "render_pet_hearts",
]
