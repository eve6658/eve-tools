#!/usr/bin/env python3
"""
Cache Orchestrator — 统一编排器
整合 Phase 1-4：Canonicalization + L2 Cache + Context Retrieval + Tool Cache

用法:
  python3 cache_orchestrator.py before_prompt <user_input> [model] [prompt_mode]
  python3 cache_orchestrator.py before_tool <tool_name> <args_json>
  python3 cache_orchestrator.py after_tool <tool_name> <args_json> <result>
  python3 cache_orchestrator.py agent_end <metrics_json>
  python3 cache_orchestrator.py stats
"""

import sys
import json
import hashlib
import time
from pathlib import Path

# 导入各模块
sys.path.insert(0, str(Path(__file__).parent))
from canonicalize import canonicalize
from prompt_cache import (
    make_prompt_key, prompt_check, prompt_store,
    make_tool_key, tool_check, tool_store
)
from context_retriever import retrieve, format_chunks

# ── Phase 0: Metrics ──────────────────────────────────
METRICS_PATH = Path("/tmp/eve_cache/metrics.json")

def load_metrics() -> dict:
    if METRICS_PATH.exists():
        return json.loads(METRICS_PATH.read_text())
    return {"turns": 0, "prompt_hits": 0, "prompt_misses": 0, "tool_hits": 0, "tool_misses": 0, "tokens_saved": 0}

def save_metrics(m: dict):
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(m, ensure_ascii=False))

def record_hit(cache_type: str, tokens_saved: int = 0):
    m = load_metrics()
    if cache_type == "prompt":
        m["prompt_hits"] += 1
    elif cache_type == "tool":
        m["tool_hits"] += 1
    m["tokens_saved"] += tokens_saved
    save_metrics(m)

def record_miss(cache_type: str):
    m = load_metrics()
    if cache_type == "prompt":
        m["prompt_misses"] += 1
    elif cache_type == "tool":
        m["tool_misses"] += 1
    save_metrics(m)

# ── Phase 1+2+4: before_prompt ───────────────────────
def before_prompt(user_input: str, model: str = "default", prompt_mode: str = "full") -> dict:
    """
    在 prompt 构建前执行：
    1. Canonicalize 用户输入
    2. 检查 L2 Prompt Cache
    3. 如果未命中，检索相关上下文
    """
    # Phase 1: Canonicalize
    canon = canonicalize(user_input)
    
    # Phase 2: L2 Prompt Cache 检查
    # 简化 tool_sig（实际使用时由调用方传入）
    tool_sig = "none"
    prompt_key = make_prompt_key(model, canon["intent"], canon["hash"], tool_sig, prompt_mode)
    
    cached = prompt_check(prompt_key)
    if cached.get("hit"):
        record_hit("prompt", tokens_saved=len(canon["text"]) * 2)  # 估算节省
        return {
            "cache": "L2_HIT",
            "key": prompt_key,
            "canonical": canon,
            "response": cached.get("response", ""),
            "tokens_saved": len(canon["text"]) * 2
        }
    
    record_miss("prompt")
    
    # Phase 4: Context Retrieval（仅注入相关块）
    context = ""
    if prompt_mode == "full":
        chunks = retrieve(user_input, top_k=3)
        if chunks:
            context = format_chunks(chunks)
    
    return {
        "cache": "MISS",
        "key": prompt_key,
        "canonical": canon,
        "context": context,
        "context_blocks": len(chunks) if chunks else 0
    }

# ── Phase 3: before_tool / after_tool ─────────────────
def before_tool(tool_name: str, args_json: str) -> dict:
    """工具调用前检查缓存"""
    key = make_tool_key(tool_name, args_json)
    cached = tool_check(key)
    
    if cached.get("hit"):
        record_hit("tool", tokens_saved=500)  # 估算
        return {
            "cache": "TOOL_HIT",
            "key": key,
            "result": cached.get("result", "")
        }
    
    record_miss("tool")
    return {
        "cache": "MISS",
        "key": key
    }

def after_tool(tool_name: str, args_json: str, result: str):
    """工具调用后存入缓存"""
    key = make_tool_key(tool_name, args_json)
    tool_store(key, result)
    return {"stored": True, "key": key}

# ── Phase 5: agent_end ────────────────────────────────
def agent_end(metrics: dict):
    """一轮结束，记录指标"""
    m = load_metrics()
    m["turns"] += 1
    m["last_turn"] = time.time()
    if metrics:
        m["last_tokens"] = metrics.get("tokens", 0)
        m["last_latency_ms"] = metrics.get("latency_ms", 0)
    save_metrics(m)
    
    # 计算命中率
    total_prompt = m["prompt_hits"] + m["prompt_misses"]
    total_tool = m["tool_hits"] + m["tool_misses"]
    
    return {
        "turn": m["turns"],
        "prompt_hit_rate": round(m["prompt_hits"] / max(total_prompt, 1), 2),
        "tool_hit_rate": round(m["tool_hits"] / max(total_tool, 1), 2),
        "tokens_saved": m["tokens_saved"],
        "total_prompt_hits": m["prompt_hits"],
        "total_tool_hits": m["tool_hits"]
    }

# ── Stats ─────────────────────────────────────────────
def stats():
    m = load_metrics()
    total_prompt = m["prompt_hits"] + m["prompt_misses"]
    total_tool = m["tool_hits"] + m["tool_misses"]
    
    return {
        "metrics": {
            "turns": m["turns"],
            "prompt_hit_rate": round(m["prompt_hits"] / max(total_prompt, 1), 2),
            "tool_hit_rate": round(m["tool_hits"] / max(total_tool, 1), 2),
            "tokens_saved": m["tokens_saved"]
        }
    }

# ── CLI ───────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("用法: before_prompt|before_tool|after_tool|agent_end|stats")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "before_prompt":
        user_input = sys.argv[2]
        model = sys.argv[3] if len(sys.argv) > 3 else "default"
        prompt_mode = sys.argv[4] if len(sys.argv) > 4 else "full"
        result = before_prompt(user_input, model, prompt_mode)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif cmd == "before_tool":
        tool_name = sys.argv[2]
        args_json = sys.argv[3]
        result = before_tool(tool_name, args_json)
        print(json.dumps(result, ensure_ascii=False))
    
    elif cmd == "after_tool":
        tool_name = sys.argv[2]
        args_json = sys.argv[3]
        result_text = " ".join(sys.argv[4:])
        result = after_tool(tool_name, args_json, result_text)
        print(json.dumps(result, ensure_ascii=False))
    
    elif cmd == "agent_end":
        metrics = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        result = agent_end(metrics)
        print(json.dumps(result, indent=2))
    
    elif cmd == "stats":
        print(json.dumps(stats(), indent=2))
    
    else:
        print(f"Unknown: {cmd}")

if __name__ == "__main__":
    main()
