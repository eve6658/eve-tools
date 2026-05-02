#!/usr/bin/env python3
"""
Phase 2+3: L2 Prompt Cache + Tool Result Cache

L2 Prompt Cache:
  key = hash(model + intent + prompt_hash + tool_signature + prompt_mode)
  value = {response, tool_calls, metadata}
  TTL = 300s

Tool Cache:
  key = hash(tool_name + canonical_args)
  value = {result, timestamp}
  TTL = 300s

用法:
  python3 prompt_cache.py prompt-check <key>
  python3 prompt_cache.py prompt-store <key> <response>
  python3 prompt_cache.py tool-check <tool_name> <args_json>
  python3 prompt_cache.py tool-store <tool_name> <args_json> <result>
  python3 prompt_cache.py stats
  python3 prompt_cache.py clear
"""

import sys
import json
import hashlib
import time
from pathlib import Path

CACHE_DIR = Path("/tmp/eve_cache/l2")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PROMPT_CACHE_PATH = CACHE_DIR / "prompt_cache.json"
TOOL_CACHE_PATH = CACHE_DIR / "tool_cache.json"

TTL_PROMPT = 300   # 5分钟
TTL_TOOL = 300     # 5分钟

# ── 加载/保存 ─────────────────────────────────────────
def load_cache(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}

def save_cache(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False))

# ── Prompt Cache ──────────────────────────────────────
def make_prompt_key(model: str, intent: str, prompt_hash: str, 
                    tool_sig: str, prompt_mode: str) -> str:
    raw = f"{model}|{intent}|{prompt_hash}|{tool_sig}|{prompt_mode}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]

def prompt_check(key: str) -> dict:
    cache = load_cache(PROMPT_CACHE_PATH)
    entry = cache.get(key)
    if not entry:
        return {"hit": False}
    if time.time() - entry["ts"] > TTL_PROMPT:
        del cache[key]
        save_cache(PROMPT_CACHE_PATH, cache)
        return {"hit": False, "reason": "expired"}
    return {"hit": True, **entry}

def prompt_store(key: str, response: str, tool_calls: list = None, metadata: dict = None):
    cache = load_cache(PROMPT_CACHE_PATH)
    cache[key] = {
        "response": response,
        "tool_calls": tool_calls or [],
        "metadata": metadata or {},
        "ts": time.time()
    }
    save_cache(PROMPT_CACHE_PATH, cache)

# ── Tool Cache ────────────────────────────────────────
def make_tool_key(tool_name: str, args_json: str) -> str:
    # 规范化 args：排序 key，去空白
    try:
        args_obj = json.loads(args_json)
        normalized = json.dumps(args_obj, sort_keys=True, ensure_ascii=False)
    except:
        normalized = args_json.strip()
    raw = f"{tool_name}|{normalized}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]

def tool_check(key: str) -> dict:
    cache = load_cache(TOOL_CACHE_PATH)
    entry = cache.get(key)
    if not entry:
        return {"hit": False}
    if time.time() - entry["ts"] > TTL_TOOL:
        del cache[key]
        save_cache(TOOL_CACHE_PATH, cache)
        return {"hit": False, "reason": "expired"}
    return {"hit": True, **entry}

def tool_store(key: str, result: str):
    cache = load_cache(TOOL_CACHE_PATH)
    cache[key] = {
        "result": result,
        "ts": time.time()
    }
    save_cache(TOOL_CACHE_PATH, cache)

# ── Stats ─────────────────────────────────────────────
def stats():
    prompt_cache = load_cache(PROMPT_CACHE_PATH)
    tool_cache = load_cache(TOOL_CACHE_PATH)
    
    now = time.time()
    prompt_active = sum(1 for v in prompt_cache.values() if now - v["ts"] < TTL_PROMPT)
    tool_active = sum(1 for v in tool_cache.values() if now - v["ts"] < TTL_TOOL)
    
    return {
        "prompt_cache": {
            "total": len(prompt_cache),
            "active": prompt_active,
            "size_kb": round(PROMPT_CACHE_PATH.stat().st_size / 1024, 1) if PROMPT_CACHE_PATH.exists() else 0
        },
        "tool_cache": {
            "total": len(tool_cache),
            "active": tool_active,
            "size_kb": round(TOOL_CACHE_PATH.stat().st_size / 1024, 1) if TOOL_CACHE_PATH.exists() else 0
        },
        "ttl_prompt": TTL_PROMPT,
        "ttl_tool": TTL_TOOL
    }

def clear():
    save_cache(PROMPT_CACHE_PATH, {})
    save_cache(TOOL_CACHE_PATH, {})
    print("L2_CACHE_CLEARED")

# ── CLI ───────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("用法: prompt-check|prompt-store|tool-check|tool-store|stats|clear")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "prompt-check":
        print(json.dumps(prompt_check(sys.argv[2]), ensure_ascii=False))
    elif cmd == "prompt-store":
        prompt_store(sys.argv[2], " ".join(sys.argv[3:]))
        print("STORED")
    elif cmd == "tool-check":
        print(json.dumps(tool_check(make_tool_key(sys.argv[2], sys.argv[3])), ensure_ascii=False))
    elif cmd == "tool-store":
        tool_store(make_tool_key(sys.argv[2], sys.argv[3]), " ".join(sys.argv[4:]))
        print("STORED")
    elif cmd == "stats":
        print(json.dumps(stats(), indent=2))
    elif cmd == "clear":
        clear()
    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()
