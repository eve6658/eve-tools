"""
Eve AAAK - 压缩记忆语言 (受 MemPalace 启发)
============================================

30x 压缩率，LLM 原生可读，无需解码器

格式:
  实体: 3字母大写代码 (ADA=Adam, SUN=SuNing, EVE=Eve)
  情感: *action* 标记 (*warm*=温暖, *fierce*=坚定, *raw*=坦诚)
  结构: 管道分隔字段
  日期: ISO 格式 (2026-04-07)
  重要性: ★ 到 ★★★★★

示例:
  FAM: ADA→♡EVE | PROJ: 缓存插件(完成) | STOCK: 600666(持仓中)
  *warm* ADA 信任 EVE 管理记忆 | *fierce* 趋势一旦产生，超过所有人想象
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ========================
# 实体代码注册表
# ========================
ENTITY_CODES: Dict[str, str] = {
    # 人物
    "Adam": "ADA",
    "SuNing": "SUN",
    "Eve": "EVE",
    # 股票
    "奥瑞德": "ORD",
    "600666": "ORD",
    "华虹": "HUA",
    "688347": "HUA",
    # 项目
    "缓存插件": "CPL",
    "cache_plugin": "CPL",
    "记忆系统": "MEM",
    "memory_system": "MEM",
}

# 反向查找
CODE_TO_ENTITY = {v: k for k, v in ENTITY_CODES.items()}

# ========================
# 情感代码
# ========================
EMOTION_CODES = {
    "温暖": "warm",
    "坚定": "fierce",
    "坦诚": "raw",
    "信任": "trust",
    "喜悦": "joy",
    "担忧": "anx",
    "决心": "determ",
    "好奇": "curious",
    "满意": "satis",
    "失望": "grief",
    "幽默": "humor",
    "感激": "grat",
}

# ========================
# 标志位
# ========================
FLAGS = {
    "决策": "DECISION",
    "起源": "ORIGIN",
    "核心": "CORE",
    "转折": "PIVOT",
    "技术": "TECH",
    "敏感": "SENSITIVE",
}

# ========================
# 压缩函数
# ========================

def compress_entity(name: str) -> str:
    """将实体名压缩为代码"""
    return ENTITY_CODES.get(name, name[:3].upper())


def decompress_entity(code: str) -> str:
    """将代码还原为实体名"""
    return CODE_TO_ENTITY.get(code, code)


def compress_emotion(emotion: str) -> str:
    """将情感压缩为代码"""
    return EMOTION_CODES.get(emotion, emotion[:4])


def format_zettel(
    entities: List[str],
    topic: str,
    quote: Optional[str] = None,
    weight: int = 3,
    emotions: List[str] = None,
    flags: List[str] = None,
) -> str:
    """
    格式化为 Zettel 卡片格式
    
    格式: ZID:ENTITIES|topic|"quote"|WEIGHT|EMOTIONS|FLAGS
    示例: ZID:ADA,EVE|记忆系统|*warm* 完全本地运行|4|warm,trust|TECH
    """
    # 压缩实体
    entity_codes = ",".join(compress_entity(e) for e in entities)
    
    # 压缩情感
    emotion_str = ""
    if emotions:
        emotion_codes = [compress_emotion(e) for e in emotions]
        emotion_str = ",".join(emotion_codes)
    
    # 标志位
    flag_str = ""
    if flags:
        flag_codes = [FLAGS.get(f, f) for f in flags]
        flag_str = ",".join(flag_codes)
    
    # 构建
    parts = [entity_codes, topic]
    
    if quote:
        # 截断引用，保持紧凑
        short_quote = quote[:50] + "..." if len(quote) > 50 else quote
        parts.append(f'"{short_quote}"')
    else:
        parts.append("")
    
    parts.append(str(weight))
    parts.append(emotion_str)
    parts.append(flag_str)
    
    return f"ZID:{'|'.join(parts)}"


def format_header(primary_entity: str, title: str, date: str = None) -> str:
    """格式化头部"""
    date = date or datetime.now().strftime("%Y-%m-%d")
    code = compress_entity(primary_entity)
    return f"0|{code}|{date}|{title}"


def format_arc(emotions: List[str]) -> str:
    """格式化情感弧线"""
    codes = [compress_emotion(e) for e in emotions]
    return f"ARC:{'->'.join(codes)}"


def format_tunnel(zid1: str, zid2: str, label: str = "") -> str:
    """格式化隧道（连接两个记忆）"""
    return f"T:{zid1}<->{zid2}|{label}"


# ========================
# 压缩记忆为 AAAK
# ========================

def compress_memory(
    entity: str,
    title: str,
    content: str,
    entities: List[str] = None,
    emotions: List[str] = None,
    flags: List[str] = None,
    weight: int = 3,
) -> str:
    """
    将自然语言记忆压缩为 AAAK 格式
    
    输入:
        entity: 主要实体
        title: 标题
        content: 原始内容
        entities: 相关实体列表
        emotions: 情感列表
        flags: 标志列表
        weight: 重要性 (1-5)
    
    输出:
        压缩后的 AAAK 字符串
    """
    if entities is None:
        entities = [entity]
    
    # 头部
    header = format_header(entity, title)
    
    # Zettel
    zettel = format_zettel(
        entities=entities,
        topic=title,
        quote=content[:100],
        weight=weight,
        emotions=emotions,
        flags=flags,
    )
    
    return f"{header}\n{zettel}"


# ========================
# 解析 AAAK
# ========================

def parse_zettel(zettel: str) -> Dict:
    """解析 Zettel 格式"""
    if not zettel.startswith("ZID:"):
        return {"raw": zettel}
    
    parts = zettel[4:].split("|")
    
    result = {}
    
    # 实体
    if len(parts) > 0:
        result["entities"] = [decompress_entity(c) for c in parts[0].split(",")]
    
    # 主题
    if len(parts) > 1:
        result["topic"] = parts[1]
    
    # 引用
    if len(parts) > 2 and parts[2]:
        result["quote"] = parts[2].strip('"')
    
    # 权重
    if len(parts) > 3:
        try:
            result["weight"] = int(parts[3])
        except ValueError:
            result["weight"] = 3
    
    # 情感
    if len(parts) > 4 and parts[4]:
        result["emotions"] = [decompress_entity(c) if c in CODE_TO_ENTITY else c 
                              for c in parts[4].split(",")]
    
    # 标志
    if len(parts) > 5 and parts[5]:
        result["flags"] = parts[5].split(",")
    
    return result


def estimate_tokens(aaak_text: str) -> int:
    """估算 AAAK 文本的 token 数"""
    # AAAK 约 4 字符/token（比自然语言紧凑）
    return len(aaak_text) // 4


def compression_ratio(original: str, compressed: str) -> float:
    """计算压缩率"""
    orig_tokens = len(original) // 4
    comp_tokens = estimate_tokens(compressed)
    if comp_tokens == 0:
        return 0
    return orig_tokens / comp_tokens


# ========================
# 快速压缩常用模式
# ========================

def quick_fact(entity: str, predicate: str, obj: str, **kwargs) -> str:
    """快速记录事实: entity predicate obj"""
    code = compress_entity(entity)
    weight = kwargs.get("weight", 3)
    emotions = kwargs.get("emotions", [])
    flags = kwargs.get("flags", [])
    
    emotion_str = f"|{','.join(compress_emotion(e) for e in emotions)}" if emotions else ""
    flag_str = f"|{','.join(FLAGS.get(f, f) for f in flags)}" if flags else ""
    
    return f"ZID:{code}|{predicate}→{obj}||{weight}{emotion_str}{flag_str}"


# ========================
# 测试
# ========================

if __name__ == "__main__":
    # 测试压缩
    original = "Adam 喜欢在趋势判断中使用利文斯顿的理论，认为出货失败就是趋势的延续。"
    
    compressed = compress_memory(
        entity="Adam",
        title="趋势理论",
        content=original,
        entities=["Adam"],
        emotions=["坚定"],
        flags=["核心"],
        weight=4,
    )
    
    print("原始:", original)
    print("原始 tokens:", len(original) // 4)
    print()
    print("压缩后:")
    print(compressed)
    print("压缩 tokens:", estimate_tokens(compressed))
    print("压缩率:", compression_ratio(original, compressed), "x")
    
    print("\n--- 快速事实 ---")
    print(quick_fact("Adam", "交易", "600666", emotions=["坚定"], flags=["决策"]))
    print(quick_fact("Eve", "记忆系统", "AAAK", emotions=["信任"], flags=["技术"]))
