"""
Eve 知识图谱 (受 MemPalace 启发)
=================================

SQLite 本地存储，时态三元组，零依赖

数据结构:
  entities (id, name, type, properties)
  triples (id, subject, predicate, object, valid_from, valid_to, confidence, source)

示例:
  kg.add_triple("Adam", "交易", "600666", valid_from="2026-04-01")
  kg.add_triple("Adam", "信任", "Eve", valid_from="2026-03-26")
  kg.invalidate("Adam", "持仓", "某股票", ended="2026-04-07")
"""

import sqlite3
import hashlib
import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_DB_PATH = os.path.expanduser("~/.openclaw/workspace/memory/knowledge.db")


class KnowledgeGraph:
    """时态知识图谱"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT DEFAULT 'unknown',
                properties TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS triples (
                id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                valid_from TEXT,
                valid_to TEXT,
                confidence REAL DEFAULT 1.0,
                source TEXT,
                extracted_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_triples_subject ON triples(subject);
            CREATE INDEX IF NOT EXISTS idx_triples_object ON triples(object);
            CREATE INDEX IF NOT EXISTS idx_triples_predicate ON triples(predicate);
            CREATE INDEX IF NOT EXISTS idx_triples_valid ON triples(valid_from, valid_to);
        """)
        conn.commit()
        conn.close()
    
    def _conn(self):
        return sqlite3.connect(self.db_path, timeout=10)
    
    def _entity_id(self, name: str) -> str:
        """实体名转 ID"""
        return name.lower().replace(" ", "_").replace("'", "")
    
    # ========================
    # 写入操作
    # ========================
    
    def add_entity(self, name: str, entity_type: str = "unknown", 
                   properties: dict = None) -> str:
        """添加或更新实体"""
        eid = self._entity_id(name)
        props = json.dumps(properties or {}, ensure_ascii=False)
        
        conn = self._conn()
        conn.execute(
            "INSERT OR REPLACE INTO entities (id, name, type, properties) VALUES (?, ?, ?, ?)",
            (eid, name, entity_type, props)
        )
        conn.commit()
        conn.close()
        return eid
    
    def add_triple(self, subject: str, predicate: str, obj: str,
                   valid_from: str = None, valid_to: str = None,
                   confidence: float = 1.0, source: str = None) -> str:
        """
        添加三元组: subject → predicate → object
        
        示例:
            kg.add_triple("Adam", "交易", "600666", valid_from="2026-04-01")
            kg.add_triple("600666", "属于", "奥瑞德")
        """
        sub_id = self._entity_id(subject)
        obj_id = self._entity_id(obj)
        pred = predicate.lower().replace(" ", "_")
        
        conn = self._conn()
        
        # 自动创建实体
        conn.execute("INSERT OR IGNORE INTO entities (id, name) VALUES (?, ?)", 
                     (sub_id, subject))
        conn.execute("INSERT OR IGNORE INTO entities (id, name) VALUES (?, ?)", 
                     (obj_id, obj))
        
        # 检查是否已存在相同的活跃三元组
        existing = conn.execute(
            "SELECT id FROM triples WHERE subject=? AND predicate=? AND object=? AND valid_to IS NULL",
            (sub_id, pred, obj_id)
        ).fetchone()
        
        if existing:
            conn.close()
            return existing[0]  # 已存在
        
        # 生成 ID
        triple_id = f"t_{sub_id}_{pred}_{obj_id}_{hashlib.md5(f'{valid_from}{datetime.now().isoformat()}'.encode()).hexdigest()[:8]}"
        
        conn.execute(
            """INSERT INTO triples (id, subject, predicate, object, valid_from, valid_to, confidence, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (triple_id, sub_id, pred, obj_id, valid_from, valid_to, confidence, source)
        )
        conn.commit()
        conn.close()
        return triple_id
    
    def invalidate(self, subject: str, predicate: str, obj: str, 
                   ended: str = None):
        """标记事实为过期 (设置 valid_to)"""
        sub_id = self._entity_id(subject)
        obj_id = self._entity_id(obj)
        pred = predicate.lower().replace(" ", "_")
        ended = ended or date.today().isoformat()
        
        conn = self._conn()
        conn.execute(
            "UPDATE triples SET valid_to=? WHERE subject=? AND predicate=? AND object=? AND valid_to IS NULL",
            (ended, sub_id, pred, obj_id)
        )
        conn.commit()
        conn.close()
    
    # ========================
    # 查询操作
    # ========================
    
    def query_entity(self, name: str, as_of: str = None, 
                     direction: str = "outgoing") -> List[Dict]:
        """
        查询实体的所有关系
        
        direction: "outgoing" (→?), "incoming" (?→), "both"
        as_of: 只返回该时间点有效的事实
        """
        eid = self._entity_id(name)
        conn = self._conn()
        results = []
        
        if direction in ("outgoing", "both"):
            query = """
                SELECT t.*, e.name as obj_name 
                FROM triples t 
                JOIN entities e ON t.object = e.id 
                WHERE t.subject = ?
            """
            params = [eid]
            
            if as_of:
                query += " AND (t.valid_from IS NULL OR t.valid_from <= ?) AND (t.valid_to IS NULL OR t.valid_to >= ?)"
                params.extend([as_of, as_of])
            
            for row in conn.execute(query, params).fetchall():
                results.append({
                    "direction": "outgoing",
                    "subject": name,
                    "predicate": row[2],
                    "object": row[9],  # obj_name (t.* = 9 cols, +1 for e.name)
                    "valid_from": row[4],
                    "valid_to": row[5],
                    "confidence": row[6],
                    "source": row[7],
                    "current": row[5] is None,
                })
        
        if direction in ("incoming", "both"):
            query = """
                SELECT t.*, e.name as sub_name 
                FROM triples t 
                JOIN entities e ON t.subject = e.id 
                WHERE t.object = ?
            """
            params = [eid]
            
            if as_of:
                query += " AND (t.valid_from IS NULL OR t.valid_from <= ?) AND (t.valid_to IS NULL OR t.valid_to >= ?)"
                params.extend([as_of, as_of])
            
            for row in conn.execute(query, params).fetchall():
                results.append({
                    "direction": "incoming",
                    "subject": row[9],  # sub_name
                    "predicate": row[2],
                    "object": name,
                    "valid_from": row[4],
                    "valid_to": row[5],
                    "confidence": row[6],
                    "source": row[7],
                    "current": row[5] is None,
                })
        
        conn.close()
        return results
    
    def query_relationship(self, predicate: str, as_of: str = None) -> List[Dict]:
        """查询特定关系的所有三元组"""
        pred = predicate.lower().replace(" ", "_")
        conn = self._conn()
        
        query = """
            SELECT t.*, s.name as sub_name, o.name as obj_name
            FROM triples t
            JOIN entities s ON t.subject = s.id
            JOIN entities o ON t.object = o.id
            WHERE t.predicate = ?
        """
        params = [pred]
        
        if as_of:
            query += " AND (t.valid_from IS NULL OR t.valid_from <= ?) AND (t.valid_to IS NULL OR t.valid_to >= ?)"
            params.extend([as_of, as_of])
        
        results = []
        for row in conn.execute(query, params).fetchall():
            results.append({
                "subject": row[8],
                "predicate": pred,
                "object": row[9],
                "valid_from": row[4],
                "valid_to": row[5],
                "current": row[5] is None,
            })
        
        conn.close()
        return results
    
    def timeline(self, entity_name: str = None) -> List[Dict]:
        """获取时间线，可选按实体过滤"""
        conn = self._conn()
        
        if entity_name:
            eid = self._entity_id(entity_name)
            rows = conn.execute("""
                SELECT t.*, s.name as sub_name, o.name as obj_name
                FROM triples t
                JOIN entities s ON t.subject = s.id
                JOIN entities o ON t.object = o.id
                WHERE (t.subject = ? OR t.object = ?)
                ORDER BY t.valid_from ASC NULLS LAST
            """, (eid, eid)).fetchall()
        else:
            rows = conn.execute("""
                SELECT t.*, s.name as sub_name, o.name as obj_name
                FROM triples t
                JOIN entities s ON t.subject = s.id
                JOIN entities o ON t.object = o.id
                ORDER BY t.valid_from ASC NULLS LAST
                LIMIT 50
            """).fetchall()
        
        conn.close()
        return [
            {
                "subject": r[8],
                "predicate": r[2],
                "object": r[9],
                "valid_from": r[4],
                "valid_to": r[5],
                "current": r[5] is None,
            }
            for r in rows
        ]
    
    def stats(self) -> Dict:
        """统计信息"""
        conn = self._conn()
        
        entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        triples = conn.execute("SELECT COUNT(*) FROM triples").fetchone()[0]
        current = conn.execute("SELECT COUNT(*) FROM triples WHERE valid_to IS NULL").fetchone()[0]
        predicates = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT predicate FROM triples ORDER BY predicate"
            ).fetchall()
        ]
        
        conn.close()
        
        return {
            "entities": entities,
            "triples": triples,
            "current_facts": current,
            "expired_facts": triples - current,
            "relationship_types": predicates,
        }
    
    # ========================
    # 导出
    # ========================
    
    def export_compact(self) -> str:
        """导出为紧凑格式 (AAAK 风格)"""
        stats = self.stats()
        lines = [f"KG|{stats['entities']}E|{stats['triples']}T|{stats['current_facts']}C"]
        
        # 导出所有活跃三元组
        conn = self._conn()
        rows = conn.execute("""
            SELECT s.name, t.predicate, o.name, t.valid_from
            FROM triples t
            JOIN entities s ON t.subject = s.id
            JOIN entities o ON t.object = o.id
            WHERE t.valid_to IS NULL
            ORDER BY t.valid_from DESC
        """).fetchall()
        
        for sub, pred, obj, date in rows:
            date_str = f"({date})" if date else ""
            lines.append(f"{sub}|{pred}|{obj}{date_str}")
        
        conn.close()
        return "\n".join(lines)


# ========================
# 快速事实记录
# ========================

def quick_fact(kg: KnowledgeGraph, fact_str: str, source: str = None) -> str:
    """
    快速记录事实
    
    格式: "subject predicate object"
    示例: "Adam 交易 600666"
    """
    parts = fact_str.strip().split()
    if len(parts) >= 3:
        subject = parts[0]
        predicate = parts[1]
        obj = " ".join(parts[2:])
        return kg.add_triple(subject, predicate, obj, 
                            valid_from=date.today().isoformat(), 
                            source=source)
    return ""


# ========================
# 测试
# ========================

if __name__ == "__main__":
    import sys
    
    # 使用临时数据库测试
    test_db = "/tmp/test_knowledge.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    kg = KnowledgeGraph(test_db)
    
    print("=" * 60)
    print("  Eve 知识图谱演示")
    print("=" * 60)
    
    # 添加事实
    print("\n--- 添加事实 ---")
    kg.add_triple("Adam", "交易", "600666", valid_from="2026-04-01", source="交易记录")
    kg.add_triple("600666", "属于", "奥瑞德", source="股票信息")
    kg.add_triple("Adam", "信任", "Eve", valid_from="2026-03-26", source="对话")
    kg.add_triple("Eve", "开发", "缓存插件", valid_from="2026-04-07", source="开发日志")
    kg.add_triple("Adam", "关注", "趋势理论", valid_from="2026-04-07", source="复盘")
    
    print("已添加 5 个三元组")
    
    # 查询
    print("\n--- 查询 Adam ---")
    results = kg.query_entity("Adam", direction="both")
    for r in results:
        status = "当前" if r["current"] else "历史"
        print(f"  [{status}] {r['subject']} → {r['predicate']} → {r['object']}")
    
    # 时间线
    print("\n--- Adam 时间线 ---")
    timeline = kg.timeline("Adam")
    for t in timeline:
        date = t["valid_from"] or "?"
        print(f"  {date}: {t['subject']} {t['predicate']} {t['object']}")
    
    # 统计
    print("\n--- 统计 ---")
    stats = kg.stats()
    print(f"实体数: {stats['entities']}")
    print(f"三元组数: {stats['triples']}")
    print(f"当前事实: {stats['current_facts']}")
    print(f"关系类型: {', '.join(stats['relationship_types'])}")
    
    # 导出
    print("\n--- 紧凑导出 ---")
    print(kg.export_compact())
    
    # 清理
    os.remove(test_db)
