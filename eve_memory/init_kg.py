#!/usr/bin/env python3
"""
初始化知识图谱 - 从 MEMORY.md 和 daily 文件提取事实
"""

import sys
import os
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from knowledge_graph import KnowledgeGraph

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
KG_PATH = os.path.join(WORKSPACE, "memory", "knowledge.db")


def parse_memory_md(kg: KnowledgeGraph):
    """从 MEMORY.md 提取事实"""
    memory_path = os.path.join(WORKSPACE, "MEMORY.md")
    if not os.path.exists(memory_path):
        return 0
    
    count = 0
    content = open(memory_path, encoding="utf-8").read()
    
    # 提取股票信息
    stock_pattern = r'\*\*股票代码\*\*[：:]\s*(\d+\.\w+)'
    company_pattern = r'\*\*公司全称\*\*[：:]\s*(.+?)$'
    date_pattern = r'\*\*成立日期\*\*[：:]\s*(\d+年\d+月\d+日)'
    
    stocks = re.findall(stock_pattern, content, re.MULTILINE)
    companies = re.findall(company_pattern, content, re.MULTILINE)
    
    # 600666 奥瑞德
    kg.add_entity("奥瑞德", "stock", {"code": "600666.SH"})
    kg.add_entity("600666", "stock_alias")
    kg.add_triple("600666", "属于", "奥瑞德", source="MEMORY.md")
    kg.add_triple("Adam", "关注", "奥瑞德", valid_from="2026-03-26", source="MEMORY.md")
    count += 3
    
    # mx-skills
    kg.add_entity("mx-skills", "project")
    kg.add_triple("Adam", "安装", "mx-skills", valid_from="2026-03-26", source="MEMORY.md")
    count += 1
    
    # SuNing
    kg.add_entity("SuNing", "person")
    kg.add_triple("SuNing", "使用", "企业微信", source="MEMORY.md")
    count += 1
    
    # 缓存插件
    kg.add_entity("缓存插件", "project")
    kg.add_triple("Eve", "开发", "缓存插件", valid_from="2026-04-02", source="MEMORY.md")
    kg.add_triple("缓存插件", "状态", "暂停-等待内存升级", valid_from="2026-04-07", source="MEMORY.md")
    count += 2
    
    return count


def parse_daily_files(kg: KnowledgeGraph):
    """从 daily 文件提取事实"""
    memory_dir = os.path.join(WORKSPACE, "memory")
    if not os.path.exists(memory_dir):
        return 0
    
    count = 0
    
    for fname in sorted(os.listdir(memory_dir)):
        if not fname.endswith(".md"):
            continue
        
        date_str = fname.replace(".md", "")
        fpath = os.path.join(memory_dir, fname)
        content = open(fpath, encoding="utf-8").read()
        
        # 提取交易心得
        if "趋势" in content and "利文斯顿" in content:
            kg.add_entity("趋势理论", "concept")
            kg.add_triple("Adam", "关注", "趋势理论", valid_from=date_str, source=fname)
            kg.add_triple("Adam", "引用", "利文斯顿", valid_from=date_str, source=fname)
            kg.add_entity("利文斯顿", "person")
            count += 3
        
        # 提取股票分析
        stock_mentions = re.findall(r'(\d{6})', content)
        for stock in set(stock_mentions[:5]):  # 限制数量
            kg.add_triple("Adam", "分析", stock, valid_from=date_str, source=fname)
            count += 1
        
        # 提取开发活动
        if "缓存" in content:
            kg.add_triple("Eve", "开发", "缓存插件", valid_from=date_str, source=fname)
            count += 1
    
    return count


def main():
    print("=" * 60)
    print("  初始化 Eve 知识图谱")
    print("=" * 60)
    
    os.makedirs(os.path.dirname(KG_PATH), exist_ok=True)
    kg = KnowledgeGraph(KG_PATH)
    
    print(f"\n📁 数据库: {KG_PATH}")
    
    # 清空现有数据（重新初始化）
    import sqlite3
    conn = sqlite3.connect(KG_PATH)
    conn.execute("DELETE FROM triples")
    conn.execute("DELETE FROM entities")
    conn.commit()
    conn.close()
    
    # 从 MEMORY.md 提取
    print("\n📖 解析 MEMORY.md...")
    n1 = parse_memory_md(kg)
    print(f"   提取 {n1} 个事实")
    
    # 从 daily 文件提取
    print("\n📅 解析 daily 文件...")
    n2 = parse_daily_files(kg)
    print(f"   提取 {n2} 个事实")
    
    # 统计
    stats = kg.stats()
    print(f"\n📊 知识图谱统计:")
    print(f"   实体数: {stats['entities']}")
    print(f"   三元组数: {stats['triples']}")
    print(f"   当前事实: {stats['current_facts']}")
    print(f"   关系类型: {', '.join(stats['relationship_types'])}")
    
    # 导出
    print("\n📋 紧凑导出:")
    print(kg.export_compact())
    
    print("\n✅ 知识图谱初始化完成!")


if __name__ == "__main__":
    main()
