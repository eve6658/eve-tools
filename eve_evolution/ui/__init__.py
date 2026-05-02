"""
UI 设计系统 — 主题 + 颜色 Token + 消息类型分发

参考 Claude Code 的 design-system/ + utils/theme.ts：
- 语义化颜色 token
- 暗/亮主题
- 消息类型分发架构
"""

import os
from dataclasses import dataclass
from enum import Enum


# ============================================================
# 主题（对应 Claude Code 的 ThemeName）
# ============================================================

class ThemeName(Enum):
    DARK = "dark"
    LIGHT = "light"


# ============================================================
# 颜色 Token（对应 Claude Code 的 Theme 对象）
# ============================================================

@dataclass(frozen=True)
class ThemeColors:
    """
    语义化颜色 token。
    
    对应 Claude Code utils/theme.ts 的 Theme 类型：
    - 每个颜色有语义含义，不是任意 RGB
    """
    # 基础
    text: str
    text_dim: str
    text_inverse: str
    background: str
    
    # 语义
    success: str
    error: str
    warning: str
    info: str
    
    # 功能
    claude: str           # Claude/Eve 品牌色
    claude_shimmer: str   # 加载动画用
    permission: str       # 权限相关
    suggestion: str       # 建议/提示
    
    # Diff
    diff_added: str
    diff_removed: str
    diff_added_dimmed: str
    diff_removed_dimmed: str
    
    # Agent 颜色
    agent_colors: tuple   # 多 agent 颜色轮转


# 预定义主题（ANSI 转义码）
DARK_THEME = ThemeColors(
    text="\033[37m",           # 白
    text_dim="\033[90m",       # 灰
    text_inverse="\033[7m",    # 反色
    background="\033[40m",     # 黑底
    success="\033[32m",        # 绿
    error="\033[31m",          # 红
    warning="\033[33m",        # 黄
    info="\033[36m",           # 青
    claude="\033[94m",         # 亮蓝
    claude_shimmer="\033[96m", # 亮青
    permission="\033[35m",     # 紫
    suggestion="\033[34m",     # 蓝
    diff_added="\033[32m",     # 绿
    diff_removed="\033[31m",   # 红
    diff_added_dimmed="\033[2;32m",
    diff_removed_dimmed="\033[2;31m",
    agent_colors=("\033[91m", "\033[94m", "\033[92m", "\033[93m", "\033[95m", "\033[96m"),
)

LIGHT_THEME = ThemeColors(
    text="\033[30m",           # 黑
    text_dim="\033[90m",       # 灰
    text_inverse="\033[7m",
    background="\033[47m",     # 白底
    success="\033[32m",
    error="\033[31m",
    warning="\033[33m",
    info="\033[36m",
    claude="\033[34m",
    claude_shimmer="\033[36m",
    permission="\033[35m",
    suggestion="\033[34m",
    diff_added="\033[32m",
    diff_removed="\033[31m",
    diff_added_dimmed="\033[2;32m",
    diff_removed_dimmed="\033[2;31m",
    agent_colors=("\033[31m", "\033[34m", "\033[32m", "\033[33m", "\033[35m", "\033[36m"),
)

THEMES = {
    ThemeName.DARK: DARK_THEME,
    ThemeName.LIGHT: LIGHT_THEME,
}

RESET = "\033[0m"


# ============================================================
# 主题管理器
# ============================================================

class ThemeManager:
    """
    主题管理器（对应 Claude Code 的 ThemeProvider）。
    
    支持：
    - 暗/亮主题切换
    - 自动检测终端主题
    - 颜色 token 访问
    """
    
    def __init__(self, theme: ThemeName = ThemeName.DARK):
        self._theme = theme
    
    @property
    def colors(self) -> ThemeColors:
        return THEMES[self._theme]
    
    @property
    def name(self) -> str:
        return self._theme.value
    
    def set_theme(self, theme: ThemeName):
        self._theme = theme
    
    def auto_detect(self):
        """自动检测终端主题"""
        color_fg = os.environ.get("COLORFGBG", "")
        if color_fg:
            # 最后一个分号后的数字是前景色
            try:
                fg = int(color_fg.split(";")[-1])
                if fg > 8:  # 亮色系 → dark theme
                    self._theme = ThemeName.DARK
                else:
                    self._theme = ThemeName.LIGHT
            except ValueError:
                pass
    
    def styled(self, text: str, style: str) -> str:
        """应用颜色样式"""
        return f"{style}{text}{RESET}"
    
    def styled_text(self, text: str, bold: bool = False, dim: bool = False) -> str:
        """格式化文字"""
        codes = []
        if bold:
            codes.append("\033[1m")
        if dim:
            codes.append("\033[2m")
        codes.append(self.colors.text)
        return f"{''.join(codes)}{text}{RESET}"


# ============================================================
# 消息类型分发（对应 Claude Code 的 Message.tsx switch 分发）
# ============================================================

class MessageType(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    COMPANION = "companion"      # 宠物消息
    COMPACT = "compact"          # 历史压缩
    ERROR = "error"


@dataclass
class FormattedMessage:
    """格式化后的消息"""
    type: MessageType
    content: str
    prefix: str = ""
    color: str = ""
    icon: str = ""


class MessageFormatter:
    """
    消息类型分发器（对应 Claude Code 的 Message.tsx + messages/ 目录）。
    
    每种消息类型有独立的格式化逻辑：
    - User: "你>" 前缀
    - Assistant: 直接输出
    - System: 灰色 + [系统] 前缀
    - Tool Use: 绿色 + 工具图标
    - Tool Result: 蓝色 + 结果图标
    - Companion: 宠物 emoji 前缀
    - Error: 红色 + ❌
    """
    
    def __init__(self, theme: ThemeManager = None):
        self.theme = theme or ThemeManager()
    
    def format(self, msg_type: MessageType, content: str, **kwargs) -> FormattedMessage:
        """根据消息类型格式化"""
        formatters = {
            MessageType.USER: self._format_user,
            MessageType.ASSISTANT: self._format_assistant,
            MessageType.SYSTEM: self._format_system,
            MessageType.TOOL_USE: self._format_tool_use,
            MessageType.TOOL_RESULT: self._format_tool_result,
            MessageType.COMPANION: self._format_companion,
            MessageType.COMPACT: self._format_compact,
            MessageType.ERROR: self._format_error,
        }
        
        formatter = formatters.get(msg_type, self._format_assistant)
        return formatter(content, **kwargs)
    
    def _format_user(self, content: str, **kw) -> FormattedMessage:
        return FormattedMessage(
            type=MessageType.USER,
            content=content,
            prefix="> ",
            color=self.theme.colors.text,
        )
    
    def _format_assistant(self, content: str, **kw) -> FormattedMessage:
        return FormattedMessage(
            type=MessageType.ASSISTANT,
            content=content,
            color=self.theme.colors.text,
        )
    
    def _format_system(self, content: str, **kw) -> FormattedMessage:
        return FormattedMessage(
            type=MessageType.SYSTEM,
            content=content,
            prefix="[系统] ",
            color=self.theme.colors.text_dim,
        )
    
    def _format_tool_use(self, content: str, tool_name: str = "", **kw) -> FormattedMessage:
        icon = {"shell": "⚡", "read_file": "📖", "write_file": "✏️", 
                "edit_file": "📝", "web_search": "🔍"}.get(tool_name, "🔧")
        return FormattedMessage(
            type=MessageType.TOOL_USE,
            content=content,
            prefix=f"{icon} {tool_name}: ",
            color=self.theme.colors.success,
        )
    
    def _format_tool_result(self, content: str, **kw) -> FormattedMessage:
        return FormattedMessage(
            type=MessageType.TOOL_RESULT,
            content=content,
            prefix="✓ ",
            color=self.theme.colors.info,
        )
    
    def _format_companion(self, content: str, name: str = "Eve", **kw) -> FormattedMessage:
        return FormattedMessage(
            type=MessageType.COMPANION,
            content=content,
            prefix=f"{name}: ",
            color=self.theme.colors.claude_shimmer,
        )
    
    def _format_compact(self, content: str, **kw) -> FormattedMessage:
        return FormattedMessage(
            type=MessageType.COMPACT,
            content=content,
            prefix="[压缩] ",
            color=self.theme.colors.text_dim,
        )
    
    def _format_error(self, content: str, **kw) -> FormattedMessage:
        return FormattedMessage(
            type=MessageType.ERROR,
            content=content,
            prefix="❌ ",
            color=self.theme.colors.error,
        )
    
    def render(self, formatted: FormattedMessage) -> str:
        """渲染为最终字符串"""
        return self.theme.styled(
            f"{formatted.prefix}{formatted.content}",
            formatted.color,
        )


# ============================================================
# 快捷工具函数
# ============================================================

def get_theme(name: str = "dark") -> ThemeManager:
    """获取主题管理器"""
    theme = ThemeName.DARK if name == "dark" else ThemeName.LIGHT
    tm = ThemeManager(theme)
    tm.auto_detect()
    return tm
