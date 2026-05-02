#!/usr/bin/env python3
"""
Eve 记忆查询工具 - 命令行接口
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from knowledge_graph import KnowledgeGraph
from layers import MemoryStack

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
KG_PATH = os.path.join(WORKSPACE, "memory", "knowledge.db")


def cmd_query(args):
    """查询实体"""
    kg = KnowledgeGraph(KG_PATH)
    
    entity = args[0] if args else "Adam"
    direction = args[1] if len(args) > 1 else "both"
    
    results = kg.query_entity(entity, direction=direction)
    
    if not results:
        print(f"未找到 '{entity}' 的相关事实")
        return
    
    print(f"\n{'='*50}")
    print(f"  {entity} 的关系")
    print(f"{'='*50}\n")
    
    for r in results:
        status = "🟢" if r["current"] else "⚪"
        date = f" ({r['valid_from']})" if r.get("valid_from") else ""
        print(f"{status} {r['subject']} → {r['predicate']} → {r['object']}{date}")


def cmd_timeline(args):
    """查看时间线"""
    kg = KnowledgeGraph(KG_PATH)
    
    entity = args[0] if args else None
    timeline = kg.timeline(entity)
    
    print(f"\n{'='*50}")
    print(f"  时间线" + (f" - {entity}" if entity else ""))
    print(f"{'='*50}\n")
    
    for t in timeline:
        date = t["valid_from"] or "?"
        status = "🟢" if t["current"] else "⚪"
        print(f"{date}: {status} {t['subject']} [{t['predicate']}] → {t['object']}")


def cmd_stats(args):
    """统计信息"""
    kg = KnowledgeGraph(KG_PATH)
    stats = kg.stats()
    
    print(f"\n{'='*50}")
    print(f"  知识图谱统计")
    print(f"{'='*50}\n")
    
    print(f"实体数: {stats['entities']}")
    print(f"三元组数: {stats['triples']}")
    print(f"当前事实: {stats['current_facts']}")
    print(f"过期事实: {stats['expired_facts']}")
    print(f"\n关系类型:")
    for rt in stats['relationship_types']:
        print(f"  - {rt}")


def cmd_wakeup(args):
    """唤醒 - 加载 L0+L1"""
    stack = MemoryStack(WORKSPACE)
    context = stack.wake_up()
    
    print(context)
    print(f"\n[统计]")
    stats = stack.stats()
    print(f"L0 tokens: {stats['L0_tokens']}")
    print(f"L1 tokens: {stats['L1_tokens']}")
    print(f"唤醒总成本: ~{stats['wake_up_tokens']} tokens")


def cmd_topic(args):
    """按需加载话题"""
    if not args:
        print("用法: eve_memory/query.py topic <话题>")
        return
    
    stack = MemoryStack(WORKSPACE)
    topic = " ".join(args)
    context = stack.load_topic(topic)
    
    print(context)


def cmd_export(args):
    """导出紧凑格式"""
    kg = KnowledgeGraph(KG_PATH)
    print(kg.export_compact())


def main():
    if len(sys.argv) < 2:
        print("""
Eve 记忆查询工具
================

用法: python query.py <命令> [参数]

命令:
  query <实体> [方向]   查询实体关系 (方向: outgoing/incoming/both)
  timeline [实体]       查看时间线
  stats                 统计信息
  wakeup                唤醒 (加载 L0+L1)
  topic <话题>          按需加载话题
  export                寧出紧凑格式

示例:
  python query.py query Adam
  python query.py timeline 600666
  python query.py stats
  python query.py wakeup
  python query.py topic 股票
        """)
        return
    
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    commands = {
        "query": cmd_query,
        "timeline": cmd_timeline,
        "stats": cmd_stats,
        "wakeup": cmd_wakeup,
        "topic": cmd_topic,
        "export": cmd_export,
    }
    
    if cmd in commands:
        commands[cmd](args)
    else:
        print(f"未知命令: {cmd}")
        print("可用命令:", ", ".join(commands.keys()))


if __name__ == "__main__":
    main()
