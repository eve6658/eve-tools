"""
Buddy 确定性生成 + 持久化

参考 Claude Code src/buddy/companion.ts：
- hash(userId + SALT) → Mulberry32 PRNG → 确定性生成
- bones（不可变）+ soul（可变）分离存储
- 读取时 bones 从 hash 重新生成，soul 从 config 加载
"""

import hashlib
import json
import os
import random
import time
from pathlib import Path

from .types import (
    Companion, CompanionBones, CompanionSoul,
    SPECIES, Rarity, RARITY_WEIGHTS, RARITY_FLOOR, STAT_NAMES,
)

SALT = "eve-companion-2026"
SHINY_CHANCE = 0.01  # 1%

HATS = ["none", "👑 皇冠", "🎩 高帽", "🎓 学士帽", "🧢 帽子", "🎀 蝴蝶结", "✨ 光环"]


# ============================================================
# PRNG（对应 Claude Code 的 mulberry32）
# ============================================================

def _mulberry32(seed: int):
    """轻量确定性 PRNG"""
    a = seed & 0xFFFFFFFF
    while True:
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = (t + (t ^ (t >> 7))) & 0xFFFFFFFF
        yield ((t ^ (t >> 14)) & 0xFFFFFFFF) / 0x100000000

def _hash_seed(user_id: str) -> int:
    """hash(userId + SALT) → 32-bit seed"""
    h = hashlib.sha256(f"{user_id}{SALT}".encode()).hexdigest()
    return int(h[:8], 16)


# ============================================================
# 生成
# ============================================================

def _roll_rarity(rng) -> Rarity:
    total = sum(RARITY_WEIGHTS.values())
    roll = next(rng) * total
    cumulative = 0
    for rarity in Rarity:
        cumulative += RARITY_WEIGHTS[rarity]
        if roll < cumulative:
            return rarity
    return Rarity.COMMON

def _pick(rng, items):
    return items[int(next(rng) * len(items))]

def _roll_stats(rng, rarity: Rarity) -> dict[str, int]:
    floor = RARITY_FLOOR[rarity]
    
    # Pick peak and dump stats
    peak = _pick(rng, STAT_NAMES)
    dump = _pick(rng, STAT_NAMES)
    while dump == peak:
        dump = _pick(rng, STAT_NAMES)
    
    stats = {}
    for name in STAT_NAMES:
        if name == peak:
            stats[name] = min(100, floor + 50 + int(next(rng) * 30))
        elif name == dump:
            stats[name] = max(1, floor - 10 + int(next(rng) * 15))
        else:
            stats[name] = floor + int(next(rng) * 40)
    return stats

def generate_bones(user_id: str) -> CompanionBones:
    """从 userId 确定性生成 bones（不可变部分）"""
    seed = _hash_seed(user_id)
    rng = _mulberry32(seed)
    
    rarity = _roll_rarity(rng)
    emoji, name = _pick(rng, SPECIES)
    species = f"{emoji} {name}"
    
    # Eye style
    eyes = ["·", "✦", "×", "◉", "@", "°"]
    eye = _pick(rng, eyes)
    
    # Hat (uncommon+ only)
    hat = ""
    if rarity not in (Rarity.COMMON,):
        hat = _pick(rng, HATS)
    
    # Shiny (1%)
    shiny = next(rng) < SHINY_CHANCE
    
    # Stats
    stats = _roll_stats(rng, rarity)
    
    return CompanionBones(
        rarity=rarity,
        species=species,
        eye=eye,
        hat=hat,
        shiny=shiny,
        stats=stats,
    )


# ============================================================
# 存储
# ============================================================

def _config_path(workspace: str = ".") -> Path:
    return Path(workspace) / ".eve_buddy.json"

def _load_config(workspace: str = ".") -> dict:
    path = _config_path(workspace)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_config(workspace: str, config: dict):
    path = _config_path(workspace)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ============================================================
# 公共接口
# ============================================================

def get_companion(workspace: str = ".") -> Companion | None:
    """获取已有伴侣（如果存在）"""
    config = _load_config(workspace)
    soul_data = config.get("companion")
    if not soul_data:
        return None
    
    user_id = config.get("user_id", "anon")
    bones = generate_bones(user_id)
    soul = CompanionSoul(
        name=soul_data.get("name", "无名"),
        personality=soul_data.get("personality", ""),
    )
    
    return Companion(
        **bones.__dict__,
        name=soul.name,
        personality=soul.personality,
        hatched_at=soul_data.get("hatched_at", 0),
    )

def generate_companion(user_id: str) -> CompanionBones:
    """只生成 bones（不存 config）"""
    return generate_bones(user_id)

def hatch_companion(user_id: str, name: str, personality: str, workspace: str = ".") -> Companion:
    """首次孵化：生成 bones + 设置 soul + 存储"""
    bones = generate_bones(user_id)
    soul = CompanionSoul(name=name, personality=personality)
    
    companion = Companion(
        **bones.__dict__,
        name=soul.name,
        personality=soul.personality,
        hatched_at=time.time(),
    )
    
    config = _load_config(workspace)
    config["user_id"] = user_id
    config["companion"] = {
        "name": name,
        "personality": personality,
        "hatched_at": companion.hatched_at,
    }
    _save_config(workspace, config)
    
    return companion

def get_or_create_companion(user_id: str, workspace: str = ".") -> Companion:
    """获取已有伴侣，或自动孵化一个新的"""
    existing = get_companion(workspace)
    if existing:
        return existing
    
    # Auto-hatch with a default name (caller can customize later)
    return hatch_companion(
        user_id=user_id,
        name="小灵",
        personality="好奇、温和、偶尔调皮",
        workspace=workspace,
    )
