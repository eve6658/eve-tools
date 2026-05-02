"""
Buddy 终端渲染

参考 Claude Code src/buddy/CompanionSprite.tsx + sprites.ts：
- 静态渲染（终端文本）
- Speech bubble（对话气泡）
- 心形动画（/buddy pet）
"""

from .types import (
    Companion, RARITY_STARS, RARITY_COLORS,
    STAT_NAMES, STAT_EMOJI, STAT_COLORS,
)


# ============================================================
# 简易 ASCII/Unicode sprite
# ============================================================

# 每种物种的简易 Unicode 表情（替代 Claude Code 的复杂 ASCII art）
SPECIES_SPRITES = {
    "🐱 猫":    ["  /\\_/\\ ", " ( ^.^ ) ", "  > ^ <  "],
    "🐉 龙":    ["  /\\^/\\ ", " (o.o)  ", "  \\ V /  "],
    "🐙 章鱼":  ["  ~~~   ", " (/o o\\) ", "  ( ) "],
    "🦉 猫头鹰": ["  /o o\\ ", " ( > < ) ", "  |___|  "],
    "🐧 企鹅":  ["  (°°)  ", "  \\__/  ", "  |  |  "],
    "🐢 乌龟":  ["   ___  ", "  / _ \\ ", "  \\___/ "],
    "👻 幽灵":  ["  .-.   ", "  | o o |", "  |  ^  |"],
    "🤖 机器人": ["  [===] ", "  |*_*| ", "  |___| "],
    "🐰 兔子":  ["  /|\\  ", " (o o)  ", "  |/ \\  "],
    "🍄 蘑菇":  ["   ___  ", "  / _ \\ ", "  |___| "],
    "🌵 仙人掌": ["   |   ", "  /|\\  ", "   |   "],
    "🦊 狐狸":  ["  /\\_/\\ ", " ( >.^ )", "  >-<  "],
    "🐸 青蛙":  [" (o o) ", " /)|  (\\", "  /  \\  "],
    "🦈 鲨鱼":  ["  /\\  /\\", " /  \\/  \\", "  \\    / "],
    "🦥 树懒":  ["  /o o\\ ", " (\\. .) ", "  |___| "],
    "🐲 麒麟":  ["  /\\^/\\ ", " (* *)  ", "  \\ V /  "],
    "🦋 蝴蝶":  [" /)  (\\ ", " (/)(\\) ", "  \\  /  "],
    "🐝 蜜蜂":  ["  /o o\\ ", " =@  @= ", "  \\  /  "],
}


def render_sprite(companion: Companion) -> str:
    """渲染宠物 sprite"""
    lines = SPECIES_SPRITES.get(companion.species, ["  ?  ", " (.) ", "  |  "])
    
    # Shiny: add sparkle
    if companion.shiny:
        return lines[0] + " ✨", lines[1] + " ✨", lines[2]
    
    return lines


def render_companion(companion: Companion, with_name: bool = True) -> str:
    """渲染完整宠物显示（sprite + 名字 + 稀有度）"""
    sprite_lines = render_sprite(companion)
    
    result = []
    if with_name:
        stars = companion.rarity_stars
        result.append(f"{stars} {companion.name}")
    
    for line in sprite_lines:
        result.append(line)
    
    if companion.shiny:
        result.append("✨ 闪光 ✨")
    
    return "\n".join(result)


# ============================================================
# Speech Bubble（对话气泡）
# ============================================================

def render_bubble(text: str, max_width: int = 30, fading: bool = False) -> str:
    """
    渲染对话气泡（对应 Claude Code 的 SpeechBubble 组件）
    
    ┌──────────────────────────┐
    │ 你好，Adam！今天过得     │
    │ 怎么样？                 │
    └──────────────────────^-┘
    """
    # Word-wrap
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > max_width and current:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip() if current else word
    if current:
        lines.append(current)
    
    if not lines:
        return ""
    
    border_style = "─" if not fading else "┄"
    top = f"┌{border_style * (max_width + 2)}┐"
    bottom = f"└{border_style * (max_width + 1)}┘"
    
    result = [top]
    for line in lines:
        padded = line.ljust(max_width)
        result.append(f"│ {padded} │")
    result.append(f"{bottom}┘")
    
    return "\n".join(result)


# ============================================================
# Pet hearts animation（/buddy pet 心形飘浮）
# ============================================================

HEART_FRAMES = [
    ["   ♥    ♥  ", "  ♥  ♥   ♥ ", " ♥   ♥   ♥ "],
    ["  ♥  ♥  ♥  ", " ♥  ♥   ♥  ", "♥   ♥      "],
    [" ♥  ♥   ♥  ", "♥   ♥      ", " ·   ·   · "],
    ["♥   ♥      ", " ·   ·   · ", "           "],
]


def render_pet_hearts(frame: int = 0) -> str:
    """渲染心形飘浮动画的一帧"""
    if 0 <= frame < len(HEART_FRAMES):
        return "\n".join(HEART_FRAMES[frame])
    return ""


# ============================================================
# 状态条
# ============================================================

def render_stat_bars(companion: Companion) -> str:
    """渲染属性条"""
    lines = []
    for stat_name in ["代码力", "耐心", "混乱度", "智慧", "毒舌"]:
        val = companion.stats.get(stat_name, 10)
        filled = val // 10
        bar = "█" * filled + "░" * (10 - filled)
        emoji = {
            "代码力": "💻", "耐心": "🧘", "混乱度": "🌀",
            "智慧": "📖", "毒舌": "🔥",
        }.get(stat_name, "")
        lines.append(f"  {emoji} {stat_name}: {bar} {val}")
    return "\n".join(lines)
