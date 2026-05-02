"""
Buddy 数据类型定义

参考 Claude Code src/buddy/types.ts：
- 18 种物种（用 emoji 代替 ASCII art）
- 5 级稀有度（common → legendary）
- 5 项属性（用中文名）
"""

from dataclasses import dataclass, field
from enum import Enum
import time


# ============================================================
# 物种（18 种，对应 Claude Code 的 18 种 ASCII art）
# ============================================================

SPECIES = [
    ("🐱", "猫"),
    ("🐉", "龙"),
    ("🐙", "章鱼"),
    ("🦉", "猫头鹰"),
    ("🐧", "企鹅"),
    ("🐢", "乌龟"),
    ("👻", "幽灵"),
    ("🤖", "机器人"),
    ("🐰", "兔子"),
    ("🍄", "蘑菇"),
    ("🌵", "仙人掌"),
    ("🦊", "狐狸"),
    ("🐸", "青蛙"),
    ("🦈", "鲨鱼"),
    ("🦥", "树懒"),
    ("🐲", "麒麟"),
    ("🦋", "蝴蝶"),
    ("🐝", "蜜蜂"),
]

SPECIES_NAMES = [f"{emoji} {name}" for emoji, name in SPECIES]


# ============================================================
# 稀有度
# ============================================================

class Rarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

RARITY_ORDER = [Rarity.COMMON, Rarity.UNCOMMON, Rarity.RARE, Rarity.EPIC, Rarity.LEGENDARY]

RARITY_WEIGHTS = {
    Rarity.COMMON: 60,
    Rarity.UNCOMMON: 25,
    Rarity.RARE: 10,
    Rarity.EPIC: 4,
    Rarity.LEGENDARY: 1,
}

RARITY_STARS = {
    Rarity.COMMON: "★",
    Rarity.UNCOMMON: "★★",
    Rarity.RARE: "★★★",
    Rarity.EPIC: "★★★★",
    Rarity.LEGENDARY: "★★★★★",
}

RARITY_COLORS = {
    Rarity.COMMON: "white",
    Rarity.UNCOMMON: "green",
    Rarity.RARE: "blue",
    Rarity.EPIC: "magenta",
    Rarity.LEGENDARY: "yellow",
}

RARITY_FLOOR = {
    Rarity.COMMON: 5,
    Rarity.UNCOMMON: 15,
    Rarity.RARE: 25,
    Rarity.EPIC: 35,
    Rarity.LEGENDARY: 50,
}


# ============================================================
# 属性（5 项，对应 Claude Code 的 DEBUGGING/PATIENCE/CHAOS/WISDOM/SNARK）
# ============================================================

STAT_NAMES = ["代码力", "耐心", "混乱度", "智慧", "毒舌"]

STAT_COLORS = {
    "代码力": "cyan",
    "耐心": "green",
    "混乱度": "red",
    "智慧": "blue",
    "毒舌": "yellow",
}

STAT_EMOJI = {
    "代码力": "💻",
    "耐心": "🧘",
    "混乱度": "🌀",
    "智慧": "📖",
    "毒舌": "🔥",
}


# ============================================================
# 数据类
# ============================================================

@dataclass
class CompanionBones:
    """确定性生成的部分（从 userId hash 得到，不可篡改）"""
    rarity: Rarity
    species: str        # "🐱 猫" 格式
    eye: str = "◉"      # 眼睛字符
    hat: str = ""       # 帽子（稀有度 ≥ uncommon 才有）
    shiny: bool = False  # 闪光（1% 概率）
    stats: dict[str, int] = field(default_factory=dict)

@dataclass
class CompanionSoul:
    """LLM 生成的部分（可变，存入 config）"""
    name: str
    personality: str

@dataclass
class Companion(CompanionBones, CompanionSoul):
    """完整的 Companion 对象（继承 bones + soul）"""
    hatched_at: float = 0.0
    
    @property
    def rarity_stars(self) -> str:
        return RARITY_STARS.get(self.rarity, "")
    
    @property
    def rarity_color(self) -> str:
        return RARITY_COLORS.get(self.rarity, "white")
    
    def stat_block(self) -> str:
        """格式化属性字符串"""
        parts = []
        for name in STAT_NAMES:
            val = self.stats.get(name, 10)
            emoji = STAT_EMOJI.get(name, "")
            parts.append(f"{emoji}{name}:{val}")
        return " ".join(parts)
    
    def full_display(self) -> str:
        """完整显示"""
        return (
            f"{self.rarity_stars} {self.species} {self.name}\n"
            f"  稀有度: {self.rarity.value}\n"
            f"  {self.stat_block()}"
        )
