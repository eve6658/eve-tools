#!/usr/bin/env python3
"""
心跳提取器 - 自动从最近活动提取知识图谱事实
设计为在心跳检查时调用
"""

import sys
import os
import re
import json
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from knowledge_graph import KnowledgeGraph

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
KG_PATH = os.path.join(WORKSPACE, "memory", "knowledge.db")
STATE_PATH = os.path.join(WORKSPACE, "memory", "kg_state.json")


def load_state() -> dict:
    """加载状态（上次提取位置）"""
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_daily": {}, "last_memory_md": 0}


def save_state(state: dict):
    """保存状态"""
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def extract_facts_from_text(text: str, source: str) -> list:
    """从文本提取事实"""
    facts = []
    
    # 1. 股票代码 (6位数字)
    stock_codes = re.findall(r'\b(\d{6})\b', text)
    for code in set(stock_codes):
        facts.append({
            "type": "stock_mention",
            "subject": "Adam",
            "predicate": "提及",
            "object": code,
            "source": source
        })
    
    # 2. 人物提及
    people = {
        "SuNing": "苏宁",
        "利文斯顿": "Livingston",
    }
    for name, _ in people.items():
        if name in text:
            facts.append({
                "type": "person_mention",
                "subject": "Adam",
                "predicate": "提及",
                "object": name,
                "source": source
            })
    
    # 3. 关键词触发
    keyword_triggers = {
        "趋势": ("关注", "趋势理论"),
        "出货": ("关注", "趋势理论"),
        "利文斯顿": ("引用", "利文斯顿"),
        "买入": ("交易意向", "买入信号"),
        "卖出": ("交易意向", "卖出信号"),
        "止损": ("交易意向", "止损策略"),
        "缓存": ("开发", "缓存插件"),
        "记忆": ("开发", "记忆系统"),
        "代码": ("开发", "编程工作"),
        "debug": ("开发", "调试"),
    }
    
    for keyword, (predicate, obj) in keyword_triggers.items():
        if keyword in text:
            facts.append({
                "type": "keyword_trigger",
                "subject": "Adam",
                "predicate": predicate,
                "object": obj,
                "source": source
            })
    
    # 4. 情感/决策关键词
    decision_words = ["决定", "选择", "改为", "换成", "放弃", "坚持"]
    for word in decision_words:
        if word in text:
            # 提取上下文
            idx = text.find(word)
            context = text[max(0, idx-20):idx+30].replace("\n", " ")
            facts.append({
                "type": "decision",
                "subject": "Adam",
                "predicate": "决策",
                "object": context[:50],
                "source": source,
                "flags": ["DECISION"]
            })
    
    return facts


def process_daily_file(fpath: str, kg: KnowledgeGraph) -> int:
    """处理单个 daily 文件"""
    content = open(fpath, encoding="utf-8").read()
    fname = os.path.basename(fpath)
    
    facts = extract_facts_from_text(content, fname)
    
    count = 0
    for fact in facts:
        try:
            kg.add_triple(
                fact["subject"],
                fact["predicate"],
                fact["object"],
                valid_from=fname.replace(".md", ""),
                source=fact["source"]
            )
            count += 1
        except Exception:
            pass  # 跳过重复
    
    return count


def process_memory_md(kg: KnowledgeGraph) -> int:
    """处理 MEMORY.md"""
    memory_path = os.path.join(WORKSPACE, "MEMORY.md")
    if not os.path.exists(memory_path):
        return 0
    
    content = open(memory_path, encoding="utf-8").read()
    
    # 检查是否有修改
    mtime = os.path.getmtime(memory_path)
    
    facts = extract_facts_from_text(content, "MEMORY.md")
    
    count = 0
    for fact in facts:
        try:
            kg.add_triple(
                fact["subject"],
                fact["predicate"],
                fact["object"],
                valid_from=datetime.now().strftime("%Y-%m-%d"),
                source=fact["source"]
            )
            count += 1
        except Exception:
            pass
    
    return count


def run_heartbeat_extract(verbose: bool = True) -> dict:
    """
    心跳提取主函数
    
    返回: {"new_facts": int, "entities": int, "triples": int}
    """
    kg = KnowledgeGraph(KG_PATH)
    state = load_state()
    
    total_new = 0
    
    # 1. 处理最近 3 天的 daily 文件
    memory_dir = os.path.join(WORKSPACE, "memory")
    if os.path.exists(memory_dir):
        today = datetime.now()
        for i in range(3):
            date = today - timedelta(days=i)
            fname = f"{date.strftime('%Y-%m-%d')}.md"
            fpath = os.path.join(memory_dir, fname)
            
            if os.path.exists(fpath):
                # 检查是否已处理
                mtime = os.path.getmtime(fpath)
                if state.get("last_daily", {}).get(fname, 0) < mtime:
                    n = process_daily_file(fpath, kg)
                    total_new += n
                    if "last_daily" not in state:
                        state["last_daily"] = {}
                    state["last_daily"][fname] = mtime
    
    # 2. 处理 MEMORY.md
    memory_md = os.path.join(WORKSPACE, "MEMORY.md")
    if os.path.exists(memory_md):
        mtime = os.path.getmtime(memory_md)
        if state.get("last_memory_md", 0) < mtime:
            n = process_memory_md(kg)
            total_new += n
            state["last_memory_md"] = mtime
    
    # 保存状态
    save_state(state)
    
    # 获取统计
    stats = kg.stats()
    
    result = {
        "new_facts": total_new,
        "entities": stats["entities"],
        "triples": stats["triples"],
        "current": stats["current_facts"],
    }
    
    if verbose:
        if total_new > 0:
            print(f"📊 知识图谱更新: +{total_new} 个新事实")
            print(f"   实体: {stats['entities']}, 三元组: {stats['triples']}")
        else:
            print(f"✓ 知识图谱无需更新 (实体: {stats['entities']}, 三元组: {stats['triples']})")
    
    return result


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Eve 心跳知识提取器")
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式")
    parser.add_argument("--reset", action="store_true", help="重置状态")
    
    args = parser.parse_args()
    
    if args.reset:
        if os.path.exists(STATE_PATH):
            os.remove(STATE_PATH)
            print("状态已重置")
    
    run_heartbeat_extract(verbose=not args.quiet)


if __name__ == "__main__":
    main()
