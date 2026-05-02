"""
Eve Session Persistence v2 — 基于 Claude Code 的 transcript + resume 设计

核心功能：
1. 对话转录持久化 — assistant 消息 fire-and-forget，user 消息 await
2. 会话恢复 — 断点续传，恢复上下文和状态
3. 文件状态快照 — 缓存文件修改状态（FileStateCache 模式）
4. 去重追踪 — discoveredSkillNames + loadedNestedMemoryPaths 模式

参考源码：claude_code_src/src/QueryEngine.ts (submitMessage, transcript 写入)
"""

import json
import os
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

from eve_evolution.context_compressor import Message, ContextCompressor, CompressConfig


@dataclass
class SessionState:
    """会话状态快照"""
    session_id: str
    created_at: str
    updated_at: str
    message_count: int = 0
    total_tokens: int = 0
    discovered_skills: List[str] = field(default_factory=list)
    loaded_memory_paths: List[str] = field(default_factory=list)
    file_snapshots: Dict[str, str] = field(default_factory=dict)  # path -> hash
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        return cls(**data)


@dataclass
class TranscriptEntry:
    """转录条目"""
    role: str
    content: str
    timestamp: str
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tokens: Optional[int] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "TranscriptEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class FileStateCache:
    """文件状态缓存 — 检测文件是否被修改"""

    def __init__(self):
        self._cache: Dict[str, str] = {}  # path -> content_hash

    def snapshot(self, filepath: str) -> Optional[str]:
        """获取文件内容哈希"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            file_hash = hashlib.md5(content.encode()).hexdigest()[:12]
            self._cache[filepath] = file_hash
            return file_hash
        except (FileNotFoundError, PermissionError):
            return None

    def is_changed(self, filepath: str) -> bool:
        """检测文件是否变化"""
        current = self.snapshot(filepath)
        if current is None:
            return False
        return self._cache.get(filepath) != current

    def get_snapshot(self) -> Dict[str, str]:
        return self._cache.copy()

    def restore(self, snapshot: Dict[str, str]):
        self._cache = snapshot


class SkillTracker:
    """技能发现追踪 — 去重（参考 discoveredSkillNames Set）"""

    def __init__(self):
        self._discovered: set = set()

    def track(self, skill_name: str) -> bool:
        """追踪技能，返回是否是新发现"""
        if skill_name in self._discovered:
            return False
        self._discovered.add(skill_name)
        return True

    def has_discovered(self, skill_name: str) -> bool:
        return skill_name in self._discovered

    def get_all(self) -> List[str]:
        return list(self._discovered)


class MemoryPathTracker:
    """记忆路径去重 — 防止同一文件重复注入（参考 loadedNestedMemoryPaths）"""

    def __init__(self):
        self._loaded: set = set()

    def track(self, filepath: str) -> bool:
        """追踪路径，返回是否是首次加载"""
        if filepath in self._loaded:
            return False
        self._loaded.add(filepath)
        return True

    def has_loaded(self, filepath: str) -> bool:
        return filepath in self._loaded

    def get_all(self) -> List[str]:
        return list(self._loaded)


class TranscriptWriter:
    """转录写入器 — 支持 fire-and-forget 和 await 两种模式"""

    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.transcript_file = session_dir / "transcript.jsonl"
        self.state_file = session_dir / "state.json"

    def write_entry(self, entry: TranscriptEntry, await_write: bool = False):
        """写入转录条目"""
        line = json.dumps(entry.to_dict(), ensure_ascii=False) + "\n"
        if await_write:
            # user 消息：同步写入，确保不丢
            with open(self.transcript_file, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
        else:
            # assistant 消息：追加写入，fire-and-forget
            with open(self.transcript_file, "a", encoding="utf-8") as f:
                f.write(line)

    def read_all(self) -> List[TranscriptEntry]:
        """读取所有转录"""
        if not self.transcript_file.exists():
            return []
        entries = []
        with open(self.transcript_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(TranscriptEntry.from_dict(json.loads(line)))
                    except json.JSONDecodeError:
                        continue
        return entries

    def save_state(self, state: SessionState):
        """保存会话状态"""
        state.updated_at = datetime.now().isoformat()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)

    def load_state(self) -> Optional[SessionState]:
        """加载会话状态"""
        if not self.state_file.exists():
            return None
        with open(self.state_file, "r", encoding="utf-8") as f:
            return SessionState.from_dict(json.load(f))


class SessionManager:
    """会话管理器 — 整合持久化、恢复、去重"""

    def __init__(self, workspace_dir: str, session_id: Optional[str] = None):
        self.workspace = Path(workspace_dir)
        self.session_id = session_id or self._generate_session_id()
        self.session_dir = self.workspace / ".eve" / "sessions" / self.session_id

        # 子模块
        self.writer = TranscriptWriter(self.session_dir)
        self.file_cache = FileStateCache()
        self.skill_tracker = SkillTracker()
        self.memory_tracker = MemoryPathTracker()
        self.compressor = ContextCompressor()

        # 状态
        self.state = self.writer.load_state() or SessionState(
            session_id=self.session_id,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        # 恢复追踪器状态
        self.skill_tracker._discovered = set(self.state.discovered_skills)
        self.memory_tracker._loaded = set(self.state.loaded_memory_paths)
        self.file_cache._cache = self.state.file_snapshots

        # 消息缓存（内存中）
        self.messages: List[Message] = []

    def _generate_session_id(self) -> str:
        return f"eve-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"

    def add_message(self, role: str, content: str, tool_name: str = None,
                    tool_call_id: str = None, await_write: bool = False):
        """添加消息并持久化"""
        msg = Message(
            role=role,
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            timestamp=datetime.now().isoformat()
        )
        self.messages.append(msg)

        # 持久化到磁盘
        entry = TranscriptEntry(
            role=role,
            content=content,
            timestamp=msg.timestamp,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            tokens=msg.estimate_tokens()
        )
        self.writer.write_entry(entry, await_write=await_write)

        # 更新状态
        self.state.message_count = len(self.messages)
        self.state.total_tokens += msg.estimate_tokens()

    def track_skill(self, skill_name: str) -> bool:
        """追踪技能发现"""
        is_new = self.skill_tracker.track(skill_name)
        self.state.discovered_skills = self.skill_tracker.get_all()
        return is_new

    def track_memory(self, filepath: str) -> bool:
        """追踪记忆路径"""
        is_new = self.memory_tracker.track(filepath)
        self.state.loaded_memory_paths = self.memory_tracker.get_all()
        return is_new

    def snapshot_file(self, filepath: str) -> Optional[str]:
        """快照文件状态"""
        h = self.file_cache.snapshot(filepath)
        self.state.file_snapshots = self.file_cache.get_snapshot()
        return h

    def compress_history(self) -> List[Message]:
        """压缩历史，返回压缩后的消息列表"""
        self.messages = self.compressor.process(self.messages)
        self.state.metadata["last_compress"] = datetime.now().isoformat()
        self.state.metadata["compress_stats"] = self.compressor.get_stats()
        return self.messages

    def save(self):
        """保存会话状态"""
        self.writer.save_state(self.state)

    def resume(self) -> Dict[str, Any]:
        """恢复会话，返回恢复的上下文"""
        entries = self.writer.read_all()
        self.messages = []
        for entry in entries:
            self.messages.append(Message(
                role=entry.role,
                content=entry.content,
                tool_name=entry.tool_name,
                tool_call_id=entry.tool_call_id,
                timestamp=entry.timestamp,
                token_count=entry.tokens
            ))

        return {
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "total_tokens": sum(m.estimate_tokens() for m in self.messages),
            "discovered_skills": self.skill_tracker.get_all(),
            "loaded_memories": self.memory_tracker.get_all(),
            "file_snapshots": len(self.file_cache.get_snapshot()),
        }

    def get_context(self, max_tokens: int = 30000) -> List[Message]:
        """获取适合发送给 LLM 的上下文（控制在 max_tokens 以内）"""
        total = 0
        result = []
        # 从后往前取，优先保留最近的消息
        for msg in reversed(self.messages):
            tokens = msg.estimate_tokens()
            if total + tokens > max_tokens:
                break
            result.insert(0, msg)
            total += tokens
        return result

    def list_sessions(self) -> List[str]:
        """列出所有会话"""
        sessions_dir = self.workspace / ".eve" / "sessions"
        if not sessions_dir.exists():
            return []
        return [d.name for d in sessions_dir.iterdir() if d.is_dir()]


# === 便捷函数 ===

def create_session(workspace_dir: str, session_id: str = None) -> SessionManager:
    """创建新会话"""
    return SessionManager(workspace_dir, session_id)


def resume_session(workspace_dir: str, session_id: str) -> SessionManager:
    """恢复已有会话"""
    mgr = SessionManager(workspace_dir, session_id)
    ctx = mgr.resume()
    print(f"✅ 会话恢复: {ctx['message_count']} 条消息, {ctx['total_tokens']} tokens")
    return mgr


# === 测试 ===

def demo():
    """演示会话持久化"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建会话
        mgr = create_session(tmpdir, "demo-session")

        # 模拟对话
        mgr.add_message("system", "你是 Eve，一只 AI 助手。", await_write=True)
        mgr.add_message("user", "分析 600666", await_write=True)
        mgr.add_message("assistant", "好的，正在分析...", tool_name="stock_tool")
        mgr.add_message("tool", "股价: 6.20, 涨幅: 2.3%")

        # 追踪技能
        mgr.track_skill("stock-analysis")
        mgr.track_skill("tushare-data")

        # 追踪记忆
        mgr.track_memory("/home/eve/.openclaw/workspace/MEMORY.md")

        # 保存
        mgr.save()

        print(f"会话 ID: {mgr.session_id}")
        print(f"消息数: {len(mgr.messages)}")
        print(f"Token 数: {sum(m.estimate_tokens() for m in mgr.messages)}")
        print(f"发现技能: {mgr.skill_tracker.get_all()}")
        print(f"加载记忆: {mgr.memory_tracker.get_all()}")

        # 恢复会话
        print("\n--- 恢复会话 ---")
        mgr2 = resume_session(tmpdir, "demo-session")
        print(f"恢复消息: {len(mgr2.messages)} 条")
        print(f"恢复技能: {mgr2.skill_tracker.get_all()}")

        # 测试压缩
        print("\n--- 测试压缩 ---")
        # 添加大量消息触发压缩
        for i in range(20):
            mgr2.add_message("tool", f"X" * 1000)
        compressed = mgr2.compress_history()
        stats = mgr2.compressor.get_stats()
        print(f"压缩统计: {stats}")


if __name__ == "__main__":
    demo()
