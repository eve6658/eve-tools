#!/usr/bin/env python3
"""
Eve Knowledge Compiler v2
=========================
卡帕西方法论：从每日日记中发现值得编译的概念，建议创建概念卡片。

与v1的区别：不再暴力正则提取，而是分析日记内容，
输出"建议创建的概念"列表，由LLM决定是否创建。

用法：
    python3 compiler.py                    # 扫描所有日记，输出建议
    python3 compiler.py --date 2026-04-08  # 扫描指定日期
    python3 compiler.py --stats            # 仅输出统计
"""

import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

WORKSPACE = Path(os.environ.get("EVE_WORKSPACE", "/home/adam/.openclaw/workspace"))
MEMORY_DIR = WORKSPACE / "memory"
WIKI_DIR = WORKSPACE / "eve_knowledge" / "wiki"
CONCEPTS_DIR = WIKI_DIR / "concepts"
STATE_FILE = WORKSPACE / "eve_knowledge" / "compiler_state.json"

# 需要过滤的噪声模式（不是概念）
NOISE_PATTERNS = [
    r'^Session', r'^Source', r'^Timestamp', r'^Account',
    r'^\d{4}-\d{2}-\d{2}',  # 日期
    r'^APK', r'^v\d+\.\d+',  # 版本号
]

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"scanned": {}, "suggestions": []}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

def get_existing_concepts():
    """获取已有概念卡片列表"""
    return {f.stem for f in CONCEPTS_DIR.glob("*.md")}

def scan_memory_file(filepath):
    """扫描日记文件，提取可能的概念主题"""
    text = filepath.read_text()
    lines = text.split('\n')
    
    candidates = []
    
    for i, line in enumerate(lines):
        # 查找章节标题（## 或 ### 开头）
        title_match = re.match(r'^#{2,3}\s+(.+?)(?:\s*[—–-]\s*.+)?$', line)
        if title_match:
            title = title_match.group(1).strip()
            # 过滤噪声
            if is_noise(title):
                continue
            # 获取后续几行作为上下文
            context = '\n'.join(lines[i+1:i+6])
            candidates.append({
                "title": title,
                "type": "section",
                "line": i + 1,
                "context": context[:200],
                "file": str(filepath),
            })
        
        # 查找带冒号的定义行（"xxx：描述" 或 "xxx - 描述"）
        def_match = re.match(r'^[-*]\s+(.{2,30}?)[：:]\s+(.{10,})', line)
        if def_match:
            term = def_match.group(1).strip()
            desc = def_match.group(2).strip()
            if not is_noise(term) and len(desc) > 10:
                candidates.append({
                    "title": term,
                    "type": "definition",
                    "line": i + 1,
                    "context": desc[:200],
                    "file": str(filepath),
                })
    
    return candidates

def is_noise(text):
    """判断是否是噪声（不是有意义的概念）"""
    for pattern in NOISE_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    # 太短
    if len(text) < 3:
        return True
    # 纯数字/符号
    if re.match(r'^[\d\s\.\-\*]+$', text):
        return True
    # 常见噪声词
    noise_words = {'核心', '关键', '重要', '注意', '总结', '结论', '建议', '判断',
                   '已完成', '进行中', '待执行', '状态', '目标', '背景', '原因',
                   '特征', '持仓', '策略', '止损', '收益', '建仓', '卖出'}
    if text in noise_words:
        return True
    return False

def rank_suggestion(candidate, existing):
    """给建议打分，判断是否值得做成概念卡片"""
    score = 0
    title = candidate["title"]
    
    # 已有卡片，不建议
    if title in existing:
        return -1
    
    # 交易相关关键词加分
    trading_words = ['均线', '趋势', '主力', '游资', '散户', '涨停', '出货', '吸筹',
                     '筹码', '股东', '盘口', '分时', '封单', '小单', '成本', '支撑',
                     '压力', '突破', '回调', '放量', '缩量', '背驰', '缠论', '中枢']
    for w in trading_words:
        if w in title:
            score += 3
    
    # 有具体定义的加分
    if candidate["type"] == "definition":
        score += 2
    
    # 章节标题加分
    if candidate["type"] == "section":
        score += 1
    
    # 上下文长度适中加分
    if 50 < len(candidate["context"]) < 200:
        score += 1
    
    return score

def scan_all(date_str=None):
    """扫描日记，输出建议"""
    existing = get_existing_concepts()
    
    if date_str:
        files = [MEMORY_DIR / f"{date_str}.md"]
        # 也检查可能的后缀
        for suffix in ['-daily-chat', '-backtest-results', '-ths-data-connect', '-claude-code-src-download']:
            alt = MEMORY_DIR / f"{date_str}{suffix}.md"
            if alt.exists():
                files.append(alt)
    else:
        files = sorted(MEMORY_DIR.glob("*.md"))
    
    all_suggestions = []
    
    for mf in files:
        if not mf.exists():
            continue
        
        candidates = scan_memory_file(mf)
        for c in candidates:
            score = rank_suggestion(c, existing)
            if score >= 3:  # 阈值
                c["score"] = score
                all_suggestions.append(c)
    
    # 按分数排序，去重
    seen = set()
    ranked = []
    for c in sorted(all_suggestions, key=lambda x: -x["score"]):
        if c["title"] not in seen:
            seen.add(c["title"])
            ranked.append(c)
    
    return ranked[:15]  # 最多15个建议

def print_stats():
    """输出知识库统计"""
    existing = get_existing_concepts()
    cards = list(CONCEPTS_DIR.glob("*.md"))
    
    print("📊 Eve Knowledge Wiki 统计")
    print(f"   概念卡片：{len(cards)}")
    print(f"   Wiki目录：{WIKI_DIR}")
    print()
    
    if cards:
        print("   现有卡片：")
        for c in sorted(cards):
            size = c.stat().st_size
            print(f"   - {c.stem} ({size}B)")

def main():
    parser = argparse.ArgumentParser(description="Eve Knowledge Compiler v2")
    parser.add_argument("--date", help="扫描指定日期 (YYYY-MM-DD)")
    parser.add_argument("--stats", action="store_true", help="仅输出统计")
    parser.add_argument("--workspace", help="覆盖工作目录路径")
    args = parser.parse_args()
    
    if args.workspace:
        global WORKSPACE, MEMORY_DIR, WIKI_DIR, CONCEPTS_DIR
        WORKSPACE = Path(args.workspace)
        MEMORY_DIR = WORKSPACE / "memory"
        WIKI_DIR = WORKSPACE / "eve_knowledge" / "wiki"
        CONCEPTS_DIR = WIKI_DIR / "concepts"
    
    if args.stats:
        print_stats()
        return
    
    print("📚 Eve Knowledge Compiler v2")
    print(f"   日记目录: {MEMORY_DIR}")
    print(f"   现有概念: {len(get_existing_concepts())} 个")
    print()
    
    suggestions = scan_all(args.date)
    
    if not suggestions:
        print("✨ 没有新的概念建议（或所有概念已有卡片）")
        return
    
    print(f"💡 建议创建 {len(suggestions)} 个概念卡片：\n")
    for i, s in enumerate(suggestions, 1):
        print(f"  {i}. **{s['title']}** (分数: {s['score']})")
        print(f"     来源: {Path(s['file']).name}:{s['line']}")
        if s['context']:
            ctx = s['context'].replace('\n', ' ')[:80]
            print(f"     上下文: {ctx}...")
        print()

if __name__ == "__main__":
    main()
