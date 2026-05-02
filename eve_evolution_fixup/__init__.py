"""
eve-evolution — Eve 自进化工具框架
"""

from tool_framework import EveTool, ToolResult, ToolContext, ValidationResult
from tool_registry import ToolRegistry
from skill_discovery import SkillDiscoverer
from memory_layered import LayeredMemory, MemoryLayer, LAYER_TTL, LAYER_PATHS
from history_compress import HistoryCompressor, Message
from session_persist import SessionManager, SessionData
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
