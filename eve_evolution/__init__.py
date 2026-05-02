"""
eve_evolution — Eve 自进化工具框架
"""
import sys, os
# 确保当前目录在 path 中
_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from tool_framework import EveTool, ToolResult, ToolContext, ValidationResult
from tool_registry import ToolRegistry
from skill_discovery import SkillDiscoverer
from memory_layered import LayeredMemory, MemoryLayer, LAYER_TTL, LAYER_PATHS
from history_compress import HistoryCompressor, Message
from session_persist import SessionManager, SessionData
from session_persist_v2 import SessionManager as SessionManagerV2, SessionState
from context_compressor import ContextCompressor, CompressConfig, Message as CompressedMessage
from openclaw_bridge import OpenClawBridge
from evolution_agent import EvolutionAgent

__all__ = [
    "EveTool", "ToolResult", "ToolContext", "ValidationResult",
    "ToolRegistry", "SkillDiscoverer",
    "LayeredMemory", "MemoryLayer", "LAYER_TTL", "LAYER_PATHS",
    "HistoryCompressor", "Message",
    "SessionManager", "SessionData",
    "OpenClawBridge", "EvolutionAgent",
]
