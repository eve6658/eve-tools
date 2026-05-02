#!/usr/bin/env python3
"""
L3 Semantic Cache for OpenClaw Agent
基于 text2vec-base-chinese 的语义缓存系统

架构：
  Query → Embed → Vector Search → Hit? → Return cached response
                                 → Miss → Execute → Cache → Return

三层缓存：
  L1: Prefix Cache (system prompt 固定)
  L2: Prompt Hash Cache (精确匹配)
  L3: Semantic Cache (语义相似度匹配) ← 本模块
"""

import json
import os
import time
import hashlib
import numpy as np
from pathlib import Path
from typing import Optional
from sentence_transformers import SentenceTransformer

# ── 配置 ──────────────────────────────────────────────
CACHE_DIR = Path("/tmp/eve_cache/l3")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

INDEX_PATH = CACHE_DIR / "index.json"
VECTORS_PATH = CACHE_DIR / "vectors.npy"
RESPONSES_PATH = CACHE_DIR / "responses.json"

SIMILARITY_THRESHOLD = 0.92   # 直接命中
RERANK_THRESHOLD = 0.85       # 候选重排阈值
TOP_K = 10                    # 候选数
TTL = 3600                    # 缓存过期时间（秒）

# ── 模型加载 ──────────────────────────────────────────
_model = None

def get_model():
    global _model
    if _model is None:
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model

# ── 向量工具 ──────────────────────────────────────────
def embed(text: str) -> np.ndarray:
    """单条文本编码为 L2 归一化向量"""
    model = get_model()
    vec = model.encode([text], normalize_embeddings=True)
    return vec[0].astype(np.float32)

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """余弦相似度（向量已归一化，直接点积）"""
    return float(np.dot(a, b))

# ── 索引管理 ──────────────────────────────────────────
class CacheIndex:
    def __init__(self):
        self.entries: list[dict] = []       # [{id, query, hash, ts, ttl, tags}]
        self.vectors: np.ndarray = None     # (N, 768)
        self.responses: dict = {}           # {id: {response, tool_calls, metadata}}
        self._load()
    
    def _load(self):
        if INDEX_PATH.exists():
            self.entries = json.loads(INDEX_PATH.read_text())
        if VECTORS_PATH.exists():
            self.vectors = np.load(VECTORS_PATH)
        else:
            self.vectors = np.empty((0, 768), dtype=np.float32)
        if RESPONSES_PATH.exists():
            self.responses = json.loads(RESPONSES_PATH.read_text())
    
    def _save(self):
        INDEX_PATH.write_text(json.dumps(self.entries, ensure_ascii=False))
        np.save(VECTORS_PATH, self.vectors)
        RESPONSES_PATH.write_text(json.dumps(self.responses, ensure_ascii=False))
    
    def _gc(self):
        """清理过期条目"""
        now = time.time()
        valid = []
        valid_ids = set()
        for i, e in enumerate(self.entries):
            if now - e["ts"] < e.get("ttl", TTL):
                valid.append(e)
                valid_ids.add(e["id"])
            else:
                self.responses.pop(e["id"], None)
        
        if len(valid) < len(self.entries):
            self.entries = valid
            if self.vectors.shape[0] > 0:
                mask = np.array([i for i, e in enumerate(self.entries) if e["id"] in valid_ids])
                # Rebuild vectors array
                all_vecs = []
                for e in self.entries:
                    # Find vector by id in old array
                    pass
            self._save()
    
    def lookup(self, query: str) -> Optional[dict]:
        """语义查找缓存"""
        if len(self.entries) == 0:
            return None
        
        q_vec = embed(query)
        
        # 计算所有相似度
        if self.vectors.shape[0] == 0:
            return None
        
        sims = np.dot(self.vectors, q_vec)  # (N,)
        
        # 找 top-k
        top_k = min(TOP_K, len(sims))
        top_indices = np.argsort(sims)[::-1][:top_k]
        
        for idx in top_indices:
            sim = sims[idx]
            entry = self.entries[idx]
            
            # 检查过期
            if time.time() - entry["ts"] > entry.get("ttl", TTL):
                continue
            
            # 直接命中
            if sim >= SIMILARITY_THRESHOLD:
                resp = self.responses.get(entry["id"])
                if resp:
                    return {
                        "hit": "direct",
                        "similarity": round(sim, 4),
                        "cached_query": entry["query"],
                        **resp
                    }
            
            # 候选重排
            if sim >= RERANK_THRESHOLD:
                resp = self.responses.get(entry["id"])
                if resp:
                    return {
                        "hit": "rerank",
                        "similarity": round(sim, 4),
                        "cached_query": entry["query"],
                        **resp
                    }
        
        return None
    
    def store(self, query: str, response: str, 
              tool_calls: list = None, metadata: dict = None,
              ttl: int = TTL, tags: list = None):
        """存储到缓存"""
        q_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        q_vec = embed(query)
        entry_id = f"{q_hash}_{int(time.time())}"
        
        entry = {
            "id": entry_id,
            "query": query[:200],  # 截断存储
            "hash": q_hash,
            "ts": time.time(),
            "ttl": ttl,
            "tags": tags or []
        }
        
        self.entries.append(entry)
        
        # 追加向量
        if self.vectors.shape[0] == 0:
            self.vectors = q_vec.reshape(1, -1)
        else:
            self.vectors = np.vstack([self.vectors, q_vec.reshape(1, -1)])
        
        self.responses[entry_id] = {
            "response": response,
            "tool_calls": tool_calls or [],
            "metadata": metadata or {}
        }
        
        self._save()
        return entry_id
    
    def stats(self) -> dict:
        """缓存统计"""
        now = time.time()
        active = sum(1 for e in self.entries if now - e["ts"] < e.get("ttl", TTL))
        return {
            "total_entries": len(self.entries),
            "active_entries": active,
            "vectors_shape": list(self.vectors.shape) if self.vectors is not None else [0, 0],
            "responses_count": len(self.responses),
            "cache_dir": str(CACHE_DIR),
            "index_size_kb": round(INDEX_PATH.stat().st_size / 1024, 1) if INDEX_PATH.exists() else 0,
            "vectors_size_kb": round(VECTORS_PATH.stat().st_size / 1024, 1) if VECTORS_PATH.exists() else 0,
            "responses_size_kb": round(RESPONSES_PATH.stat().st_size / 1024, 1) if RESPONSES_PATH.exists() else 0,
        }
    
    def clear(self):
        """清空缓存"""
        self.entries = []
        self.vectors = np.empty((0, 768), dtype=np.float32)
        self.responses = {}
        self._save()

# ── CLI 接口 ──────────────────────────────────────────
def main():
    import sys
    cache = CacheIndex()
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python l3_semantic_cache.py lookup <query>")
        print("  python l3_semantic_cache.py store <query> <response>")
        print("  python l3_semantic_cache.py stats")
        print("  python l3_semantic_cache.py clear")
        print("  python l3_semantic_cache.py bench")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "lookup":
        query = " ".join(sys.argv[2:])
        result = cache.lookup(query)
        if result:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("CACHE_MISS")
    
    elif cmd == "store":
        query = sys.argv[2]
        response = " ".join(sys.argv[3:])
        cid = cache.store(query, response)
        print(f"CACHED: {cid}")
    
    elif cmd == "stats":
        print(json.dumps(cache.stats(), indent=2))
    
    elif cmd == "clear":
        cache.clear()
        print("CACHE_CLEARED")
    
    elif cmd == "bench":
        # 基准测试：编码速度
        import time
        model = get_model()
        texts = [f"这是一个测试查询，编号{i}" for i in range(100)]
        
        t0 = time.time()
        vecs = model.encode(texts, normalize_embeddings=True)
        dt = time.time() - t0
        
        print(f"编码 100 条文本: {dt*1000:.0f}ms")
        print(f"平均: {dt*10:.1f}ms/条")
        print(f"向量维度: {vecs.shape}")

if __name__ == "__main__":
    main()
