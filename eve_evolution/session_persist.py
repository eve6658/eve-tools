"""
session_persist.py — 会话持久化系统

设计思路：
---------
参考 Claude Code 的 session persistence 模式。Claude Code 会将会话状态
保存到磁盘，支持：
1. 断点续传 — 关闭后重新打开可以恢复
2. 历史查看 — 可以回看之前的对话
3. 会话管理 — 列出、搜索、删除旧会话

核心功能：
- 保存会话消息、元数据到 JSON 文件
- 按 session_id 加载和恢复
- 列出所有可用会话
- 支持自动清理过期会话

与 Claude Code 的对应关系：
- SessionManager ≈ Claude Code 的 SessionStore
- save() ≈ Claude Code 的 persistSession()
- load() ≈ Claude Code 的 restoreSession()
- list_sessions() ≈ Claude Code 的 listSessions()
"""

from __future__ import annotations

import json
import time
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SessionData:
    """
    会话数据结构。
    
    包含会话的所有状态：
    - messages: 对话消息列表
    - metadata: 会话元数据（创建时间、最后活跃时间等）
    - context: 附加上下文（工具发现状态等）
    """
    session_id: str
    messages: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "metadata": self.metadata,
            "context": self.context,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SessionData":
        return cls(
            session_id=data["session_id"],
            messages=data.get("messages", []),
            metadata=data.get("metadata", {}),
            context=data.get("context", {}),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


class SessionManager:
    """
    会话状态持久化管理器。
    
    支持：
    1. 保存会话到磁盘（JSON 格式）
    2. 加载会话恢复状态
    3. 列出所有会话
    4. 删除过期会话
    
    存储结构：
        sessions_dir/
        ├── session_1703275200_abc123.json
        ├── session_1703280000_def456.json
        └── ...
    
    使用示例：
        manager = SessionManager("/path/to/sessions")
        
        # 保存
        manager.save("session_001", messages, {"model": "gpt-4"})
        
        # 加载
        data = manager.load("session_001")
        
        # 列出
        sessions = manager.list_sessions()
        
        # 清理 30 天前的会话
        cleaned = manager.cleanup(max_age_days=30)
    """
    
    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_path(self, session_id: str) -> Path:
        """获取会话文件路径"""
        # 清理 session_id 中的非法字符
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
        return self.sessions_dir / f"session_{safe_id}.json"
    
    def save(self, session_id: str, messages: list[dict], metadata: dict = None) -> bool:
        """
        保存会话状态到磁盘。
        
        Args:
            session_id: 会话唯一标识
            messages: 消息列表（每个是 dict，包含 role/content 等）
            metadata: 会话元数据
            
        Returns:
            是否保存成功
        """
        try:
            path = self._get_path(session_id)
            
            # 如果已存在，加载并合并
            existing = self.load(session_id)
            if existing:
                session_data = existing
                session_data.messages = messages
                session_data.metadata.update(metadata or {})
                session_data.updated_at = time.time()
            else:
                session_data = SessionData(
                    session_id=session_id,
                    messages=messages,
                    metadata=metadata or {},
                )
            
            path.write_text(
                json.dumps(session_data.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return True
        except Exception as e:
            print(f"保存会话失败: {e}")
            return False
    
    def load(self, session_id: str) -> Optional[SessionData]:
        """
        加载会话状态。
        
        Args:
            session_id: 会话唯一标识
            
        Returns:
            SessionData 或 None（不存在时）
        """
        path = self._get_path(session_id)
        if not path.exists():
            return None
        
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return SessionData.from_dict(data)
        except Exception:
            return None
    
    def list_sessions(self, sort_by: str = "updated_at", reverse: bool = True) -> list[dict]:
        """
        列出所有会话。
        
        Args:
            sort_by: 排序字段 (created_at | updated_at)
            reverse: 是否降序（最新的在前）
            
        Returns:
            会话概要列表
        """
        sessions = []
        
        for path in self.sessions_dir.glob("session_*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                sessions.append({
                    "session_id": data.get("session_id", path.stem),
                    "created_at": data.get("created_at", 0),
                    "updated_at": data.get("updated_at", 0),
                    "message_count": len(data.get("messages", [])),
                    "metadata": data.get("metadata", {}),
                    "file_size": path.stat().st_size,
                })
            except Exception:
                continue
        
        # 排序
        sessions.sort(key=lambda s: s.get(sort_by, 0), reverse=reverse)
        return sessions
    
    def delete(self, session_id: str) -> bool:
        """删除会话"""
        path = self._get_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False
    
    def cleanup(self, max_age_days: int = 30) -> int:
        """
        清理过期会话。
        
        Args:
            max_age_days: 最大保留天数
            
        Returns:
            清理的会话数
        """
        cutoff = time.time() - max_age_days * 86400
        cleaned = 0
        
        for path in self.sessions_dir.glob("session_*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                updated = data.get("updated_at", 0)
                if updated < cutoff:
                    path.unlink()
                    cleaned += 1
            except Exception:
                continue
        
        return cleaned
    
    def get_stats(self) -> dict:
        """获取存储统计"""
        sessions = self.list_sessions()
        total_size = sum(s["file_size"] for s in sessions)
        
        return {
            "total_sessions": len(sessions),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "sessions_dir": str(self.sessions_dir),
        }
    
    def exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        return self._get_path(session_id).exists()
