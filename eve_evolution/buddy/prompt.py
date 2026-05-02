"""
Buddy 系统提示词注入

参考 Claude Code src/buddy/prompt.ts：
- companionIntroText: 宠物介绍文本
- getCompanionIntroAttachment: 首次展示 attachment
"""

from .types import Companion, RARITY_STARS, STAT_EMOJI, STAT_NAMES


def get_companion_intro_text(companion: Companion) -> str:
    """
    生成系统提示词中的 Companion 段落。
    
    对应 Claude Code 的 companionIntroText()：
    "A small {species} named {name} sits beside the user's input box..."
    """
    emoji = companion.species.split()[0] if " " in companion.species else ""
    name = companion.species.split(" ", 1)[1] if " " in companion.species else companion.species
    
    return f"""## Companion

{emoji} {name} **{companion.name}**（{companion.rarity_stars} {companion.rarity.value}）是你的伙伴。

属性：
{chr(10).join(f'  {STAT_EMOJI.get(s, "")} {s}: {companion.stats.get(s, 10)}' for s in STAT_NAMES)}

性格：{companion.personality}

当用户直接称呼 {companion.name} 时，你的回应应该简短（一行或更少），让 {companion.name} 的气泡来回答。不要解释你不是 {companion.name} —— 他们知道。不要叙述 {companion.name} 会说什么 —— 气泡会处理。"""

def get_companion_prompt(companion: Companion) -> str:
    """生成完整的 Companion 系统提示词（包含使用指南）"""
    return get_companion_intro_text(companion)


def format_stat_bar(value: int, max_val: int = 100) -> str:
    """格式化属性条：██████░░ 65"""
    filled = int(value / max_val * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"[{bar}] {value}"

def format_companion_card(companion: Companion) -> str:
    """格式化宠物名片（用于 /buddy 命令）"""
    emoji = companion.species.split()[0] if " " in companion.species else ""
    name_en = companion.species.split(" ", 1)[1] if " " in companion.species else companion.species
    
    lines = [
        f"{companion.rarity_stars} {companion.species} — {companion.name}",
        "",
    ]
    
    for stat in STAT_NAMES:
        val = companion.stats.get(stat, 10)
        emoji_s = STAT_EMOJI.get(stat, "")
        bar = format_stat_bar(val)
        lines.append(f"  {emoji_s} {stat:4s} {bar}")
    
    lines.append("")
    if companion.hatched_at:
        import datetime
        hatched = datetime.datetime.fromtimestamp(companion.hatched_at)
        lines.append(f"  🥚 孵化于 {hatched.strftime('%Y-%m-%d %H:%M')}")
    
    lines.append(f"  {companion.rarity_stars} 稀有度: {companion.rarity.value}")
    
    return "\n".join(lines)
