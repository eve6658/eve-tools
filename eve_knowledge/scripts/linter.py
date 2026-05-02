#!/usr/bin/env python3
"""
Eve Knowledge Linter
====================
检查知识库一致性、发现缺失数据、找出新关联。
对应卡帕西提到的 "LLM health checks"。

用法：
    python3 linter.py              # 完整检查
    python3 linter.py --check links    # 仅检查断裂链接
    python3 linter.py --check stale    # 仅检查过时内容
"""

import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

WORKSPACE = Path(os.environ.get("EVE_WORKSPACE", "/home/adam/.openclaw/workspace"))
WIKI_DIR = WORKSPACE / "eve_knowledge" / "wiki"
CONCEPTS_DIR = WIKI_DIR / "concepts"
INDEX_FILE = WIKI_DIR / "index.md"

def find_broken_links():
    """检查 [[双链]] 是否有对应的概念卡片"""
    broken = []
    existing = {f.stem for f in CONCEPTS_DIR.glob("*.md")}
    
    for card in CONCEPTS_DIR.glob("*.md"):
        content = card.read_text()
        links = re.findall(r'\[\[([^\]]+)\]\]', content)
        for link in links:
            if link not in existing:
                broken.append({
                    "file": card.stem,
                    "missing": link,
                    "context": _find_context(content, link),
                })
    
    return broken

def find_stale_concepts(days=30):
    """找出超过N天未更新的概念卡片"""
    stale = []
    for card in CONCEPTS_DIR.glob("*.md"):
        mtime = datetime.fromtimestamp(card.stat().st_mtime)
        age = datetime.now() - mtime
        if age.days > days:
            stale.append({
                "name": card.stem,
                "last_updated": mtime.strftime('%Y-%m-%d'),
                "age_days": age.days,
            })
    return stale

def find_unlinked_concepts():
    """找出没有被其他卡片引用的概念"""
    all_concepts = {f.stem for f in CONCEPTS_DIR.glob("*.md")}
    linked = set()
    
    for card in CONCEPTS_DIR.glob("*.md"):
        content = card.read_text()
        links = re.findall(r'\[\[([^\]]+)\]\]', content)
        linked.update(links)
    
    # 排除自身引用
    unlinked = all_concepts - linked
    return sorted(unlinked)

def find_duplicate_topics():
    """检查是否有重复或高度相似的概念"""
    concepts = {}
    for card in CONCEPTS_DIR.glob("*.md"):
        content = card.read_text()
        # 提取前500字符作为指纹
        concepts[card.stem] = content[:500]
    
    duplicates = []
    names = list(concepts.keys())
    for i, a in enumerate(names):
        for b in names[i+1:]:
            # 简单的关键词重叠检测
            words_a = set(re.findall(r'[\u4e00-\u9fff]+', concepts[a]))
            words_b = set(re.findall(r'[\u4e00-\u9fff]+', concepts[b]))
            overlap = words_a & words_b
            if len(overlap) > 10:  # 10个共同中文词
                duplicates.append({
                    "a": a, "b": b,
                    "shared_keywords": list(overlap)[:10],
                })
    
    return duplicates

def suggest_new_concepts():
    """分析wiki，建议新的概念卡片"""
    # 从所有卡片中提取频繁出现但没有独立卡片的术语
    term_count = {}
    for card in CONCEPTS_DIR.glob("*.md"):
        content = card.read_text()
        # 查找 [[引用]] 中的术语
        refs = re.findall(r'\[\[([^\]]+)\]\]', content)
        for ref in refs:
            term_count[ref] = term_count.get(ref, 0) + 1
    
    existing = {f.stem for f in CONCEPTS_DIR.glob("*.md")}
    
    # 被多次引用但没有卡片的概念
    suggestions = []
    for term, count in sorted(term_count.items(), key=lambda x: -x[1]):
        if term not in existing and count >= 2:
            suggestions.append({"term": term, "referenced_by": count})
    
    return suggestions

def _find_context(text, term, chars=80):
    """找到术语在文本中的上下文"""
    idx = text.find(term)
    if idx == -1:
        return ""
    start = max(0, idx - chars//2)
    end = min(len(text), idx + len(term) + chars//2)
    return text[start:end].replace('\n', ' ').strip()

def run_lint(check_type="all"):
    """运行 lint 检查"""
    print("🔍 Eve Knowledge Linter")
    print(f"   Wiki目录: {WIKI_DIR}")
    print()
    
    results = {"broken_links": [], "stale": [], "unlinked": [], "duplicates": [], "suggestions": []}
    
    if check_type in ("all", "links"):
        print("📎 检查断裂链接...")
        broken = find_broken_links()
        if broken:
            for b in broken:
                print(f"  ❌ [[{b['missing']}] 被 [{b['file']}] 引用但不存在")
            results["broken_links"] = broken
        else:
            print("  ✅ 无断裂链接")
    
    if check_type in ("all", "stale"):
        print("\n📅 检查过时内容（>30天）...")
        stale = find_stale_concepts()
        if stale:
            for s in stale:
                print(f"  ⏰ {s['name']} — 最后更新 {s['last_updated']} ({s['age_days']}天前)")
            results["stale"] = stale
        else:
            print("  ✅ 无过时内容")
    
    if check_type in ("all",):
        print("\n🔗 检查孤立概念（未被引用）...")
        unlinked = find_unlinked_concepts()
        if unlinked:
            for u in unlinked:
                print(f"  ⚠️  {u} — 未被其他卡片引用")
            results["unlinked"] = unlinked
        else:
            print("  ✅ 所有概念都有引用")
    
    if check_type in ("all",):
        print("\n🔄 检查重复主题...")
        dupes = find_duplicate_topics()
        if dupes:
            for d in dupes:
                print(f"  ⚠️  {d['a']} ↔ {d['b']} 可能重复（共享关键词: {','.join(d['shared_keywords'][:5])}）")
            results["duplicates"] = dupes
        else:
            print("  ✅ 无重复主题")
    
    if check_type in ("all",):
        print("\n💡 建议新建概念卡片...")
        suggestions = suggest_new_concepts()
        if suggestions:
            for s in suggestions[:5]:
                print(f"  ➕ {s['term']}（被引用 {s['referenced_by']} 次）")
            results["suggestions"] = suggestions
        else:
            print("  ✅ 暂无建议")
    
    # 汇总
    print("\n" + "="*40)
    issues = sum(len(v) for v in results.values())
    print(f"📊 共发现 {issues} 个问题/建议")
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Eve Knowledge Linter")
    parser.add_argument("--check", choices=["links", "stale", "all"], default="all")
    parser.add_argument("--workspace", help="覆盖工作目录路径")
    args = parser.parse_args()
    
    if args.workspace:
        global WORKSPACE, WIKI_DIR, CONCEPTS_DIR
        WORKSPACE = Path(args.workspace)
        WIKI_DIR = WORKSPACE / "eve_knowledge" / "wiki"
        CONCEPTS_DIR = WIKI_DIR / "concepts"
    
    run_lint(args.check)

if __name__ == "__main__":
    main()
