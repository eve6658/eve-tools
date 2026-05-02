#!/usr/bin/env python3
"""
Eve Memory Enhancement Demo
"""

import sys
import os

# 添加当前目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aaak import compress_memory, quick_fact, estimate_tokens, compression_ratio
from layers import MemoryStack
from knowledge_graph import KnowledgeGraph


def demo_aaak():
    """AAAK 压缩演示"""
    print("=" * 60)
    print("  AAAK 压缩记忆语言演示")
    print("=" * 60)
    
    # 原始记忆
    original = "Adam 在 2026-04-07 的盘后复盘中提到，趋势一旦产生将会超过所有人的想象。利文斯顿说过，出货失败就是趋势。当大多数人都认为趋势结束卖掉手中股票，主力反而会继续拉升。"
    
    # 压缩
    compressed = compress_memory(
        entity="Adam",
        title="趋势理论",
        content=original,
        entities=["Adam"],
        emotions=["坚定"],
        flags=["核心"],
        weight=4,
    )
    
    print(f"\n📝 原始 ({len(original)//4} tokens):")
    print(f"  {original[:80]}...")
    
    print(f"\n🗜️ 压缩后 (~{estimate_tokens(compressed)} tokens):")
    print(f"  {compressed}")
    
    print(f"\n📊 压缩率: {compression_ratio(original, compressed):.1f}x")
    
    # 快速事实
    print("\n⚡ 快速事实:")
    print(f"  {quick_fact('Adam', '关注', '趋势理论', emotions=['坚定'], flags=['核心'])}")
    print(f"  {quick_fact('Eve', '开发', '记忆系统', emotions=['信任'], flags=['技术'])}")


def demo_layers():
    """4层记忆栈演示"""
    print("\n" + "=" * 60)
    print("  4层记忆栈演示")
    print("=" * 60)
    
    workspace = os.path.expanduser("~/.openclaw/workspace")
    stack = MemoryStack(workspace)
    
    # 唤醒
    print("\n🌅 唤醒 (L0 + L1):")
    wake = stack.wake_up()
    # 只显示前 500 字符
    print(wake[:500] + "\n...")
    
    # 按需加载
    print("\n📚 按需加载 - '股票':")
    topic = stack.load_topic("股票")
    print(topic[:300] + "\n...")
    
    # 统计
    print("\n📊 统计:")
    stats = stack.stats()
    print(f"  L0 (身份): ~{stats['L0_tokens']} tokens")
    print(f"  L1 (核心): ~{stats['L1_tokens']} tokens")
    print(f"  唤醒总成本: ~{stats['wake_up_tokens']} tokens")
    print(f"  vs 全量注入 MEMORY.md: ~2000+ tokens")
    print(f"  节省: ~{(1 - stats['wake_up_tokens']/2000)*100:.0f}%")


def demo_kg():
    """知识图谱演示"""
    print("\n" + "=" * 60)
    print("  知识图谱演示")
    print("=" * 60)
    
    # 使用临时数据库
    import tempfile
    test_db = os.path.join(tempfile.gettempdir(), "eve_kg_demo.db")
    
    if os.path.exists(test_db):
        os.remove(test_db)
    
    kg = KnowledgeGraph(test_db)
    
    # 添加事实
    print("\n➕ 添加事实:")
    facts = [
        ("Adam", "交易", "600666", "2026-04-01"),
        ("600666", "属于", "奥瑞德", None),
        ("Adam", "信任", "Eve", "2026-03-26"),
        ("Eve", "开发", "缓存插件", "2026-04-07"),
        ("Adam", "关注", "趋势理论", "2026-04-07"),
    ]
    
    for sub, pred, obj, date in facts:
        kg.add_triple(sub, pred, obj, valid_from=date)
        print(f"  ✓ {sub} → {pred} → {obj}")
    
    # 查询
    print("\n🔍 查询 Adam:")
    results = kg.query_entity("Adam", direction="both")
    for r in results:
        status = "🟢" if r["current"] else "⚪"
        print(f"  {status} {r['subject']} [{r['predicate']}] → {r['object']}")
    
    # 时间线
    print("\n📅 Adam 时间线:")
    timeline = kg.timeline("Adam")
    for t in timeline:
        date = t["valid_from"] or "?"
        print(f"  {date}: {t['subject']} {t['predicate']} {t['object']}")
    
    # 统计
    print("\n📊 统计:")
    stats = kg.stats()
    print(f"  实体: {stats['entities']}")
    print(f"  三元组: {stats['triples']}")
    print(f"  当前事实: {stats['current_facts']}")
    
    # 清理
    os.remove(test_db)


def demo_comparison():
    """与传统方式对比"""
    print("\n" + "=" * 60)
    print("  Token 效率对比")
    print("=" * 60)
    
    # 传统方式：自然语言描述
    traditional = """
    Adam 是我的用户，他使用 OpenClaw，时区是 GMT+8。
    Adam 在 2026 年 4 月 1 日开始交易 600666（奥瑞德）。
    Adam 信任 Eve 来管理他的记忆系统。
    Eve 在 2026 年 4 月 7 日开发了缓存插件。
    Adam 在 2026 年 4 月 7 日的盘后复盘中提到了利文斯顿的趋势理论。
    """
    
    # AAAK 压缩方式
    aaak = """
KG|5E|5T|5C
Adam|交易|600666(2026-04-01)
600666|属于|奥瑞德
Adam|信任|Eve(2026-03-26)
Eve|开发|缓存插件(2026-04-07)
Adam|关注|趋势理论(2026-04-07)
"""
    
    trad_tokens = len(traditional) // 4
    aaak_tokens = len(aaak) // 4
    
    print(f"\n📝 传统自然语言 ({trad_tokens} tokens):")
    print(f"  {traditional.strip()[:100]}...")
    
    print(f"\n🗜️ AAAK 压缩 ({aaak_tokens} tokens):")
    print(f"  {aaak.strip()}")
    
    print(f"\n📊 节省: {trad_tokens - aaak_tokens} tokens ({(1-aaak_tokens/trad_tokens)*100:.0f}%)")
    
    # 4层记忆栈对比
    print("\n📚 4层记忆栈 vs 全量注入:")
    print(f"  全量 MEMORY.md: ~2000+ tokens")
    print(f"  L0 (身份): ~100 tokens")
    print(f"  L1 (核心): ~400 tokens")
    print(f"  唤醒总计: ~500 tokens")
    print(f"  节省: ~75%")


if __name__ == "__main__":
    demo_aaak()
    demo_layers()
    demo_kg()
    demo_comparison()
    
    print("\n" + "=" * 60)
    print("  ✅ 演示完成!")
    print("=" * 60)
