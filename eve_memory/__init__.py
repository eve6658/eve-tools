"""
Eve Memory Enhancement Module
==============================

受 MemPalace 启发的记忆增强系统

模块:
  - aaak: AAAK 压缩记忆语言
  - layers: 4层记忆栈
  - knowledge_graph: 时态知识图谱

用法:
    from eve_memory import MemoryStack, KnowledgeGraph, quick_fact
    
    # 4层记忆栈
    stack = MemoryStack()
    context = stack.wake_up()  # L0 + L1 (~400 tokens)
    
    # 知识图谱
    kg = KnowledgeGraph()
    kg.add_triple("Adam", "交易", "600666", valid_from="2026-04-01")
    facts = kg.query_entity("Adam")
"""

from .aaak import (
    compress_memory,
    compress_entity,
    decompress_entity,
    quick_fact as aaak_fact,
    format_zettel,
    estimate_tokens,
    compression_ratio,
)

from .layers import (
    MemoryStack,
    Layer0,
    Layer1,
    Layer2,
    Layer3,
)

from .knowledge_graph import (
    KnowledgeGraph,
    quick_fact,
)

__version__ = "0.1.0"

__all__ = [
    # AAAK
    "compress_memory",
    "compress_entity",
    "decompress_entity",
    "aaak_fact",
    "format_zettel",
    "estimate_tokens",
    "compression_ratio",
    # Layers
    "MemoryStack",
    "Layer0",
    "Layer1",
    "Layer2",
    "Layer3",
    # Knowledge Graph
    "KnowledgeGraph",
    "quick_fact",
]
