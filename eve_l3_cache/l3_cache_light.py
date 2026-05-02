#!/usr/bin/env python3
"""
L3 Semantic Cache - 轻量版（TF-IDF + 余弦相似度）
零模型依赖，内存占用 <50MB
16G 内存到位后切换到 neural 版本（l3_semantic_cache.py）

架构：
  Query → TF-IDF向量化 → 余弦相似度 → Hit? → Return cached
                                          → Miss → Execute → Cache
"""

import json
import os
import time
import hashlib
import re
import numpy as np
from pathlib import Path
from typing import Optional
from collections import Counter
from math import sqrt, log

CACHE_DIR = Path("/tmp/eve_cache/l3")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

INDEX_PATH = CACHE_DIR / "index.json"
RESPONSES_PATH = CACHE_DIR / "responses.json"

SIMILARITY_THRESHOLD = 0.45   # TF-IDF 余弦阈值（比神经模型低）
TTL = 3600

# ── 分词（简单按字符+常用词切分）─────────────────────
def tokenize(text: str) -> list[str]:
    """简单中文分词：字符 + 英文单词"""
    # 中文字符逐字切分，英文按词切分
    tokens = []
    text = text.lower().strip()
    # 英文单词
    en_words = re.findall(r'[a-z0-9]+', text)
    tokens.extend(en_words)
    # 中文字符（去标点）
    zh_chars = re.findall(r'[\u4e00-\u9fff]', text)
    tokens.extend(zh_chars)
    # 2-gram 中文
    for i in range(len(zh_chars) - 1):
        tokens.append(zh_chars[i] + zh_chars[i+1])
    return tokens

# ── TF-IDF 向量化 ─────────────────────────────────────
class TfIdfVectorizor:
    def __init__(self):
        self.vocab: dict[str, int] = {}  # word → index
        self.idf: dict[str, float] = {}  # word → idf
        self.doc_count = 0
    
    def fit(self, documents: list[str]):
        """从文档集合学习词汇表和 IDF"""
        self.doc_count = len(documents)
        df = Counter()  # document frequency
        vocab_set = set()
        
        for doc in documents:
            tokens = set(tokenize(doc))
            for t in tokens:
                df[t] += 1
                vocab_set.add(t)
        
        self.vocab = {w: i for i, w in enumerate(sorted(vocab_set))}
        self.idf = {}
        for w, d in df.items():
            self.idf[w] = log((self.doc_count + 1) / (d + 1)) + 1
    
    def transform(self, text: str) -> np.ndarray:
        """文本 → TF-IDF 向量"""
        tokens = tokenize(text)
        tf = Counter(tokens)
        vec = np.zeros(len(self.vocab), dtype=np.float32)
        
        for word, count in tf.items():
            if word in self.vocab:
                idx = self.vocab[word]
                tf_val = 1 + log(count) if count > 0 else 0
                vec[idx] = tf_val * self.idf.get(word, 1.0)
        
        # L2 归一化
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec
    
    def save(self, path: Path):
        path.write_text(json.dumps({
            "vocab": self.vocab,
            "idf": self.idf,
            "doc_count": self.doc_count
        }))
    
    def load(self, path: Path):
        data = json.loads(path.read_text())
        self.vocab = data["vocab"]
        self.idf = data["idf"]
        self.doc_count = data["doc_count"]

# ── 缓存核心 ──────────────────────────────────────────
class L3Cache:
    def __init__(self):
        self.vectorizor = TfIdfVectorizor()
        self.entries: list[dict] = []
        self.vectors: np.ndarray = np.empty((0, 0), dtype=np.float32)
        self.responses: dict = {}
        self._load()
    
    def _load(self):
        if INDEX_PATH.exists():
            data = json.loads(INDEX_PATH.read_text())
            self.entries = data.get("entries", [])
            self.vectorizor.vocab = data.get("vocab", {})
            self.vectorizor.idf = data.get("idf", {})
            self.vectorizor.doc_count = data.get("doc_count", 0)
            vec_list = data.get("vectors", [])
            if vec_list:
                self.vectors = np.array(vec_list, dtype=np.float32)
        if RESPONSES_PATH.exists():
            self.responses = json.loads(RESPONSES_PATH.read_text())
    
    def _save(self):
        data = {
            "entries": self.entries,
            "vocab": self.vectorizor.vocab,
            "idf": self.vectorizor.idf,
            "doc_count": self.vectorizor.doc_count,
            "vectors": self.vectors.tolist() if self.vectors.size > 0 else []
        }
        INDEX_PATH.write_text(json.dumps(data, ensure_ascii=False))
        RESPONSES_PATH.write_text(json.dumps(self.responses, ensure_ascii=False))
    
    def _rebuild_vectors(self):
        """从 entries 重建向量矩阵"""
        if not self.entries:
            self.vectors = np.empty((0, 0), dtype=np.float32)
            return
        vecs = []
        for e in self.entries:
            vecs.append(self.vectorizor.transform(e["query"]))
        self.vectors = np.array(vecs, dtype=np.float32)
    
    def lookup(self, query: str) -> Optional[dict]:
        """语义查找"""
        if len(self.entries) == 0 or self.vectors.size == 0:
            return None
        
        q_vec = self.vectorizor.transform(query)
        sims = np.dot(self.vectors, q_vec)
        
        best_idx = np.argmax(sims)
        best_sim = float(sims[best_idx])
        
        if best_sim >= SIMILARITY_THRESHOLD:
            entry = self.entries[best_idx]
            if time.time() - entry["ts"] < entry.get("ttl", TTL):
                resp = self.responses.get(entry["id"])
                if resp:
                    return {
                        "hit": "L3_semantic",
                        "similarity": round(best_sim, 4),
                        "cached_query": entry["query"],
                        **resp
                    }
        return None
    
    def store(self, query: str, response: str,
              tool_calls: list = None, metadata: dict = None,
              ttl: int = TTL, tags: list = None):
        """存入缓存（先增量更新向量库）"""
        q_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        entry_id = f"{q_hash}_{int(time.time())}"
        
        entry = {
            "id": entry_id,
            "query": query[:200],
            "hash": q_hash,
            "ts": time.time(),
            "ttl": ttl,
            "tags": tags or []
        }
        
        self.entries.append(entry)
        
        # 增量更新向量
        new_vec = self.vectorizor.transform(query).reshape(1, -1)
        if self.vectors.size == 0:
            self.vectors = new_vec
            # 需要先 fit 才能 transform
            self.vectorizor.fit([query])
            new_vec = self.vectorizor.transform(query).reshape(1, -1)
            self.vectors = new_vec
        else:
            # 扩展 vocab 并重新计算所有向量
            old_queries = [e["query"] for e in self.entries]
            self.vectorizor.fit(old_queries)
            self._rebuild_vectors()
        
        self.responses[entry_id] = {
            "response": response,
            "tool_calls": tool_calls or [],
            "metadata": metadata or {}
        }
        
        self._save()
        return entry_id
    
    def store_batch(self, items: list[tuple[str, str]]):
        """批量存入（更高效）"""
        queries = [q for q, r in items]
        self.vectorizor.fit(queries)
        
        for query, response in items:
            q_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
            entry_id = f"{q_hash}_{int(time.time())}"
            
            self.entries.append({
                "id": entry_id,
                "query": query[:200],
                "hash": q_hash,
                "ts": time.time(),
                "ttl": TTL,
                "tags": []
            })
            
            self.responses[entry_id] = {
                "response": response,
                "tool_calls": [],
                "metadata": {}
            }
        
        self._rebuild_vectors()
        self._save()
    
    def stats(self) -> dict:
        return {
            "type": "L3_tfidf_light",
            "total_entries": len(self.entries),
            "vocab_size": len(self.vectorizor.vocab),
            "vector_dim": self.vectors.shape[1] if self.vectors.size > 0 else 0,
            "cache_dir": str(CACHE_DIR),
            "index_kb": round(INDEX_PATH.stat().st_size / 1024, 1) if INDEX_PATH.exists() else 0,
            "responses_kb": round(RESPONSES_PATH.stat().st_size / 1024, 1) if RESPONSES_PATH.exists() else 0,
            "threshold": SIMILARITY_THRESHOLD,
            "ttl_seconds": TTL
        }
    
    def clear(self):
        self.entries = []
        self.vectors = np.empty((0, 0), dtype=np.float32)
        self.responses = {}
        self.vectorizor = TfIdfVectorizor()
        self._save()


# ── CLI ───────────────────────────────────────────────
def main():
    import sys
    cache = L3Cache()
    
    if len(sys.argv) < 2:
        print("L3 TF-IDF Semantic Cache")
        print("用法:")
        print("  python l3_cache_light.py lookup <query>")
        print("  python l3_cache_light.py store <query> <response>")
        print("  python l3_cache_light.py stats")
        print("  python l3_cache_light.py clear")
        print("  python l3_cache_light.py bench")
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
        import time
        cache = L3Cache()
        
        # 批量存入
        data = [
            (f"分析股票{i}的走势", f"股票{i}现价{10+i}元") for i in range(100)
        ]
        t0 = time.time()
        cache.store_batch(data)
        dt = time.time() - t0
        print(f"批量存储 100 条: {dt*1000:.0f}ms")
        
        # 查询
        t0 = time.time()
        for i in range(100):
            cache.lookup(f"股票{i}怎么样")
        dt = time.time() - t0
        print(f"查询 100 次: {dt*1000:.0f}ms ({dt*10:.1f}ms/次)")
        
        print(json.dumps(cache.stats(), indent=2))


if __name__ == "__main__":
    main()
