"""
memory_layered.py — Eve 分层记忆系统

设计思路：
---------
参考 Claude Code 的 nested_memory + LRU cache 模式。
在 Claude Code 中，记忆系统按优先级分层加载：
- 高层（不变）：SOUL.md、IDENTITY.md 等核心身份文件
- 中层（策展）：MEMORY.md 等长期记忆
- 低层（日志）：每日日志文件

分层的好处：
1. 高层记忆始终加载，不重复读取
2. 低层记忆按需加载，节省 token
3. LRU 缓存避免重复磁盘 I/O
4. 去重机制（loadedNestedMemoryPaths）防止重复加载同一文件

与 Claude Code 的对应关系：
- MemoryLayer ≈ Claude Code 的 memory type（soul/project/memory）
- LayeredMemory ≈ Claude Code 的 loadNestedMemory()
- loaded_paths ≈ Claude Code 的 loadedNestedMemoryPaths（去重）
- cache ≈ Claude Code 的 LRU memory cache
- load_relevant() ≈ Claude Code 的 loadRelevantMemory()
"""

from __future__ import annotations

import os
import time
import hashlib
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# 记忆层级定义
# ============================================================

class MemoryLayer(Enum):
    """
    记忆层级 — 从上到下优先级递减。
    
    CORE: 核心身份层（SOUL.md, IDENTITY.md, USER.md）
          → 每次会话都加载，不参与缓存过期
          
    LONG_TERM: 长期记忆层（MEMORY.md）
               → 策展过的长期记忆，每次主会话加载
               
    DAILY: 日常日志层（memory/YYYY-MM-DD.md）
           → 按日期索引，通常只加载最近几天
           
    PROJECT: 项目上下文层（context/项目/*.md）
             → 按项目按需加载
             
    SKILL: 技能记忆层（.eve/skill-memory/*.md）
           → 技能特定的上下文，按需加载
    """
    CORE = "core"
    LONG_TERM = "long"
    DAILY = "daily"
    PROJECT = "project"
    SKILL = "skill"


# 各层级的文件路径模式
LAYER_PATHS = {
    MemoryLayer.CORE: ["SOUL.md", "IDENTITY.md", "USER.md", "AGENTS.md"],
    MemoryLayer.LONG_TERM: ["MEMORY.md"],
    MemoryLayer.DAILY: ["memory/{date}.md"],
    MemoryLayer.PROJECT: ["context/{key}.md"],
    MemoryLayer.SKILL: [".eve/skill-memory/{key}.md"],
}

# 各层级的默认缓存 TTL（秒）
LAYER_TTL = {
    MemoryLayer.CORE: float('inf'),      # 永不过期
    MemoryLayer.LONG_TERM: 3600,         # 1 小时
    MemoryLayer.DAILY: 600,              # 10 分钟
    MemoryLayer.PROJECT: 1800,           # 30 分钟
    MemoryLayer.SKILL: 900,              # 15 分钟
}


# ============================================================
# 缓存条目
# ============================================================

@dataclass
class CacheEntry:
    """缓存条目"""
    content: str
    timestamp: float
    layer: MemoryLayer
    ttl: float
    
    @property
    def expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl


# ============================================================
# 分层记忆管理器
# ============================================================

class LayeredMemory:
    """
    分层记忆管理器。
    
    参考 Claude Code 的 loadNestedMemory() 实现：
    1. 按层级优先级加载记忆文件
    2. loaded_paths 防止重复加载（对应 loadedNestedMemoryPaths）
    3. LRU cache 减少磁盘 I/O
    4. 合并返回时按层级顺序拼接
    
    使用示例：
        memory = LayeredMemory("/path/to/workspace")
        
        # 加载所有核心记忆
        core = await memory.load_relevant("identity", layer=MemoryLayer.CORE)
        
        # 加载相关记忆（自动选择层级）
        relevant = await memory.load_relevant("用户偏好")
        
        # 保存新记忆
        await memory.save("学会了新的技能", MemoryLayer.DAILY, "2024-01-15")
    """
    
    def __init__(self, workspace: str):
        self.workspace = Path(workspace)
        
        # 已加载路径集合（去重，参考 loadedNestedMemoryPaths）
        self.loaded_paths: set[str] = set()
        
        # LRU 缓存：path → CacheEntry
        self.cache: dict[str, CacheEntry] = {}
        
        # 最大缓存条目数
        self.max_cache_size: int = 50
    
    def _resolve_paths(self, layer: MemoryLayer, key: str = "") -> list[Path]:
        """
        解析某层级的记忆文件路径列表。
        
        将路径模式中的 {date}、{key} 替换为实际值。
        """
        patterns = LAYER_PATHS.get(layer, [])
        paths = []
        
        for pattern in patterns:
            resolved = pattern.replace("{key}", key)
            
            if "{date}" in pattern:
                # 今天和昨天
                from datetime import datetime, timedelta
                today = datetime.now().strftime("%Y-%m-%d")
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                paths.append(self.workspace / resolved.replace("{date}", today))
                paths.append(self.workspace / resolved.replace("{date}", yesterday))
            else:
                paths.append(self.workspace / resolved)
        
        return paths
    
    def _read_file(self, path: Path) -> Optional[str]:
        """读取文件内容，支持缓存"""
        path_str = str(path)
        
        # 检查缓存
        if path_str in self.cache:
            entry = self.cache[path_str]
            if not entry.expired:
                return entry.content
            else:
                del self.cache[path_str]
        
        # 读取文件
        if not path.exists():
            return None
        
        try:
            content = path.read_text(encoding="utf-8")
            
            # 存入缓存
            layer = MemoryLayer.CORE  # 默认
            for l, paths in LAYER_PATHS.items():
                for p in paths:
                    if path.name in p or path_str.endswith(p.replace("{key}", "").replace("{date}", "")):
                        layer = l
                        break
            
            self._cache_put(path_str, content, layer)
            return content
        except Exception:
            return None
    
    def _cache_put(self, path_str: str, content: str, layer: MemoryLayer) -> None:
        """放入缓存，容量满了则淘汰最旧条目"""
        if len(self.cache) >= self.max_cache_size:
            # 淘汰最旧的
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
            del self.cache[oldest_key]
        
        self.cache[path_str] = CacheEntry(
            content=content,
            timestamp=time.time(),
            layer=layer,
            ttl=LAYER_TTL[layer],
        )
    
    async def load_relevant(self, query: str, layer: Optional[MemoryLayer] = None) -> str:
        """
        加载相关记忆内容。
        
        Args:
            query: 查询关键词（目前用于日志，实际可做语义匹配）
            layer: 指定层级，None 则加载所有层级
            
        Returns:
            合并后的记忆文本，按层级顺序拼接
        """
        layers = [layer] if layer else list(MemoryLayer)
        
        sections = []
        for mem_layer in layers:
            paths = self._resolve_paths(mem_layer)
            
            for path in paths:
                path_str = str(path)
                
                # 去重：已加载的跳过
                if path_str in self.loaded_paths:
                    continue
                
                content = self._read_file(path)
                if content and content.strip():
                    # 添加层级标记头
                    header = f"=== {mem_layer.value.upper()} ===" 
                    sections.append(f"{header}\n{content.strip()}")
                    self.loaded_paths.add(path_str)
        
        return "\n\n".join(sections)
    
    async def save(self, content: str, layer: MemoryLayer, key: str) -> bool:
        """
        保存记忆到指定层级。
        
        Args:
            content: 记忆内容
            layer: 目标层级
            key: 键标识（日期、项目名、技能名等）
            
        Returns:
            是否保存成功
        """
        paths = self._resolve_paths(layer, key)
        if not paths:
            return False
        
        # 取第一个路径保存
        path = paths[0]
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            
            # 更新缓存
            self._cache_put(str(path), content, layer)
            return True
        except Exception:
            return False
    
    async def append(self, content: str, layer: MemoryLayer, key: str) -> bool:
        """
        追加内容到已有记忆文件。
        
        适合日记型记忆的写入。
        """
        paths = self._resolve_paths(layer, key)
        if not paths:
            return False
        
        path = paths[0]
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            
            existing = ""
            if path.exists():
                existing = path.read_text(encoding="utf-8")
            
            timestamp = time.strftime("%H:%M")
            new_entry = f"\n\n[{timestamp}] {content}"
            
            path.write_text(existing + new_entry, encoding="utf-8")
            
            # 清除缓存（内容已变）
            self.cache.pop(str(path), None)
            return True
        except Exception:
            return False
    
    def mark_loaded(self, path: str) -> None:
        """标记路径为已加载"""
        self.loaded_paths.add(path)
    
    def reset_loaded(self) -> None:
        """重置已加载标记（新会话时调用）"""
        self.loaded_paths.clear()
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()
    
    def get_stats(self) -> dict:
        """获取记忆系统统计"""
        return {
            "loaded_paths": len(self.loaded_paths),
            "cached_entries": len(self.cache),
            "workspace": str(self.workspace),
        }
