#!/usr/bin/env python3
"""
Phase 1: Canonicalization 规范化
将用户输入标准化，提高 prompt 稳定性和缓存命中率

用法:
  python3 canonicalize.py "帮我分析一下600666的走势"
  python3 canonicalize.py --intent "查一下奥瑞德"
"""

import sys
import re
import json
import hashlib

# ── 意图检测规则 ──────────────────────────────────────
INTENT_PATTERNS = {
    "stock_analysis": r"[A-Z0-9]{4,6}|股票|走势|行情|涨|跌|K线|技术分析|基本面",
    "stock_query": r"持仓|成本|浮盈|浮亏|盈亏|仓位",
    "weather": r"天气|温度|下雨|气温|湿度",
    "news": r"新闻|资讯|消息|热点|时事",
    "file_op": r"文件|读|写|创建|删除|目录|文件夹",
    "shell_cmd": r"执行|命令|运行|安装|启动|停止",
    "web_search": r"搜索|查一下|查查|找一下|帮我查",
    "coding": r"代码|编程|脚本|Python|函数|bug|调试",
    "memory": r"记住|记得|提醒|备忘|记录",
    "greeting": r"你好|嗨|hello|hi|在吗|早上|晚上",
    "trading": r"买|卖|建仓|清仓|止损|止盈|挂单|涨停|跌停",
}

def detect_intent(text: str) -> str:
    """检测用户意图"""
    text_lower = text.lower()
    scores = {}
    for intent, pattern in INTENT_PATTERNS.items():
        matches = re.findall(pattern, text_lower)
        scores[intent] = len(matches)
    
    if not scores or max(scores.values()) == 0:
        return "general"
    
    return max(scores, key=scores.get)

def canonicalize(text: str) -> dict:
    """规范化输入"""
    # 1. 去空白
    cleaned = text.strip()
    # 2. 合并多余空格
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # 3. 全角转半角
    cleaned = cleaned.replace('（', '(').replace('）', ')')
    cleaned = cleaned.replace('，', ',').replace('。', '.')
    cleaned = cleaned.replace('：', ':').replace('；', ';')
    # 4. 去除不可见字符
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned)
    
    intent = detect_intent(cleaned)
    
    # 提取实体（股票代码、数字等）
    entities = {
        "stock_codes": re.findall(r'[0-9]{6}', cleaned),
        "numbers": re.findall(r'\d+\.?\d*', cleaned),
    }
    
    # 生成 hash（用于 L2 缓存 key）
    hash_input = f"{intent}:{cleaned.lower()}"
    content_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    return {
        "text": cleaned,
        "intent": intent,
        "entities": entities,
        "hash": content_hash,
        "len": len(cleaned)
    }

def main():
    if len(sys.argv) < 2:
        print("用法: python3 canonicalize.py <text>")
        sys.exit(1)
    
    text = " ".join(sys.argv[1:])
    result = canonicalize(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
