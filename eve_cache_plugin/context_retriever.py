#!/usr/bin/env python3
"""
Phase 4: Project Context 懒加载
用关键词检索替代全量注入 AGENTS.md / SOUL.md / TOOLS.md / MEMORY.md

用法:
  python3 context_retriever.py "帮我分析600666" [top_k=3]
  python3 context_retriever.py --query "天气" --files "MEMORY.md,TOOLS.md"
"""

import sys
import json
import re
from pathlib import Path
from typing import Optional

WORKSPACE = Path("/home/adam/.openclaw/workspace")

# ── 分块 ─────────────────────────────────────────────
def chunk_file(filepath: str, chunk_size: int = 500) -> list[dict]:
    """将文件按段落分块，每块约 chunk_size 字符"""
    path = WORKSPACE / filepath
    if not path.exists():
        return []
    
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.split("\n")
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for line in lines:
        # 遇到标题时切块
        if line.startswith("#") and current_chunk:
            chunks.append({
                "file": filepath,
                "heading": current_chunk[0][:60],
                "text": "\n".join(current_chunk),
                "size": current_size
            })
            current_chunk = []
            current_size = 0
        
        current_chunk.append(line)
        current_size += len(line)
        
        if current_size >= chunk_size and not line.startswith("#"):
            chunks.append({
                "file": filepath,
                "heading": current_chunk[0][:60],
                "text": "\n".join(current_chunk),
                "size": current_size
            })
            current_chunk = []
            current_size = 0
    
    if current_chunk:
        chunks.append({
            "file": filepath,
            "heading": current_chunk[0][:60],
            "text": "\n".join(current_chunk),
            "size": current_size
        })
    
    return chunks

# ── 关键词检索 ────────────────────────────────────────
def extract_keywords(query: str) -> list[str]:
    """从查询中提取关键词"""
    keywords = []
    
    # 股票代码
    keywords.extend(re.findall(r'[0-9]{6}', query))
    
    # 中文关键词（2字以上）
    keywords.extend(re.findall(r'[\u4e00-\u9fff]{2,}', query))
    
    # 英文单词
    keywords.extend(re.findall(r'[a-zA-Z]{3,}', query.lower()))
    
    return keywords

def score_chunk(chunk: dict, keywords: list[str]) -> float:
    """计算块与关键词的相关度"""
    text_lower = chunk["text"].lower()
    score = 0.0
    
    for kw in keywords:
        kw_lower = kw.lower()
        count = text_lower.count(kw_lower)
        if count > 0:
            # 标题命中权重更高
            if kw_lower in chunk["heading"].lower():
                score += 3.0 * count
            else:
                score += 1.0 * count
    
    # 归一化（避免长文本占优）
    if chunk["size"] > 0:
        score = score / (1 + len(chunk["text"]) / 1000)
    
    return score

def retrieve(query: str, files: list[str] = None, top_k: int = 3) -> list[dict]:
    """检索最相关的上下文块"""
    if files is None:
        files = ["AGENTS.md", "SOUL.md", "TOOLS.md", "IDENTITY.md", "USER.md", "MEMORY.md"]
    
    keywords = extract_keywords(query)
    if not keywords:
        return []
    
    all_chunks = []
    for f in files:
        all_chunks.extend(chunk_file(f))
    
    scored = []
    for chunk in all_chunks:
        s = score_chunk(chunk, keywords)
        if s > 0:
            scored.append({**chunk, "score": round(s, 2)})
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]

def format_chunks(chunks: list[dict]) -> str:
    """格式化输出，用于注入 prompt"""
    if not chunks:
        return ""
    
    parts = []
    for c in chunks:
        parts.append(f"--- [{c['file']}] (score={c['score']}) ---")
        # 截断到 500 字符
        text = c["text"][:500]
        parts.append(text)
    
    return "\n".join(parts)

# ── CLI ───────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("用法: python3 context_retriever.py <query> [top_k]")
        sys.exit(1)
    
    query = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    results = retrieve(query, top_k=top_k)
    
    if not results:
        print("NO_RELEVANT_CONTEXT")
        return
    
    print(f"找到 {len(results)} 个相关块:\n")
    print(format_chunks(results))

if __name__ == "__main__":
    main()
