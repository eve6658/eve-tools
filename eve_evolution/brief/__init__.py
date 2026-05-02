"""
BriefTool 主动消息系统

参考 Claude Code src/tools/BriefTool/ + Kairos 模式：
- 定时检查（5分钟间隔）
- 消息分类：normal / proactive
- 通过 OpenClaw 通道发送
"""

import enum
import time
from dataclasses import dataclass


class BriefStatus(enum.Enum):
    NORMAL = "normal"       # 回应用户刚问的
    PROACTIVE = "proactive" # 主动推送


@dataclass
class BriefMessage:
    message: str
    status: BriefStatus = BriefStatus.NORMAL
    attachments: list[str] = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


class BriefTool:
    """
    BriefTool — 向用户发送消息（对应 Claude Code 的 SendUserMessage）
    
    设计理念（来自 Claude Code）:
    - text outside tool is visible in detail view, but most won't open it
    - the answer lives here
    - status: 'normal' when replying, 'proactive' when initiating
    """
    
    NAME = "send_user_message"
    DESCRIPTION = "向用户发送消息。支持 Markdown 格式。"
    ALIASES = ["brief", "notify", "SendUserMessage"]
    
    def __init__(self, send_callback=None):
        self.send_callback = send_callback or self._default_send
    
    def _default_send(self, message: str, status: BriefStatus) -> dict:
        """默认发送（打印到日志）"""
        prefix = "[主动]" if status == BriefStatus.PROACTIVE else "[回复]"
        print(f"{prefix} {message}")
        return {"sent": True, "status": status.value}
    
    def execute(self, message: str, status: str = "normal") -> dict:
        """执行发送"""
        brief_status = BriefStatus.PROACTIVE if status == "proactive" else BriefStatus.NORMAL
        return self.send_callback(message, brief_status)
    
    def __repr__(self):
        return f"BriefTool(name={self.NAME})"


# ============================================================
# 主动检查逻辑
# ============================================================

import os
import glob

class ProactiveChecker:
    """
    定时检查是否需要主动告知用户。
    
    对应 Claude Code Kairos 模式的定时检查：
    - 每 5 分钟扫描工作区
    - 判断是否有值得告知的变化
    """
    
    CHECK_INTERVAL = 300  # 5分钟
    
    def __init__(self, workspace: str = "."):
        self.workspace = workspace
        self.last_check: float = 0
        self.last_file_hashes: dict[str, str] = {}
    
    def should_check(self) -> bool:
        """是否到了检查时间"""
        return time.time() - self.last_check >= self.CHECK_INTERVAL
    
    def check(self) -> list[dict]:
        """
        执行主动检查。
        返回需要推送的消息列表。
        """
        if not self.should_check():
            return []
        
        messages = []
        
        # 1. 检测新文件创建
        new_files = self._detect_new_files()
        if new_files:
            messages.append({
                "message": f"📁 检测到 {len(new_files)} 个新文件:\n" + 
                          "\n".join(f"  • {f}" for f in new_files[:5]),
                "status": "proactive",
            })
        
        # 2. 检测文件修改
        modified = self._detect_modified_files()
        if modified:
            messages.append({
                "message": f"📝 {len(modified)} 个文件有更新:\n" +
                          "\n".join(f"  • {f}" for f in modified[:5]),
                "status": "proactive",
            })
        
        self.last_check = time.time()
        return messages
    
    def _scan_files(self) -> dict[str, str]:
        """扫描工作区文件（简化版：只记录文件列表和修改时间）"""
        files = {}
        for pattern in ["*.py", "*.md", "*.txt", "*.json", "*.yaml", "*.yml"]:
            for f in glob.glob(os.path.join(self.workspace, "**", pattern), recursive=True):
                if ".git" in f or "__pycache__" in f:
                    continue
                rel = os.path.relpath(f, self.workspace)
                files[rel] = str(os.path.getmtime(f))
        return files
    
    def _detect_new_files(self) -> list[str]:
        """检测新文件"""
        current = self._scan_files()
        if not self.last_file_hashes:
            self.last_file_hashes = current
            return []
        
        new = [f for f in current if f not in self.last_file_hashes]
        self.last_file_hashes = current
        return new
    
    def _detect_modified_files(self) -> list[str]:
        """检测修改的文件"""
        current = self._scan_files()
        if not self.last_file_hashes:
            return []
        
        modified = []
        for f, mtime in current.items():
            if f in self.last_file_hashes and self.last_file_hashes[f] != mtime:
                modified.append(f)
        
        self.last_file_hashes = current
        return modified


# ============================================================
# 消息分类器
# ============================================================

class MessageClassifier:
    """
    分类消息的紧迫程度。
    
    对应 Claude Code 的 status='normal' vs 'proactive'。
    """
    
    URGENCY_KEYWORDS = {
        "urgent": ["紧急", "立即", "马上", "urgent", "critical", "error"],
        "info": ["完成", "done", "完成", "updated", "通知"],
    }
    
    def classify(self, message: str, context: dict = None) -> BriefStatus:
        """分类消息"""
        msg_lower = message.lower()
        
        # 检查是否是紧急的
        for kw in self.URGENCY_KEYWORDS.get("urgent", []):
            if kw in msg_lower:
                return BriefStatus.PROACTIVE
        
        # 检查是否是信息性的
        for kw in self.URGENCY_KEYWORDS.get("info", []):
            if kw in msg_lower:
                return BriefStatus.PROACTIVE
        
        # 默认为 normal
        return BriefStatus.NORMAL


# ============================================================
# 集成：与 OpenClaw Heartbeat 对接
# ============================================================

class BriefSystem:
    """
    完整的 Brief 系统，可直接集成到 heartbeat。
    
    使用方式：
        brief = BriefSystem(workspace="/home/adam/.openclaw/workspace")
        brief.register_send_handler(my_send_func)
        # 在 heartbeat 中调用
        messages = await brief.heartbeat_check()
    """
    
    def __init__(self, workspace: str = "."):
        self.checker = ProactiveChecker(workspace)
        self.classifier = MessageClassifier()
        self.brief_tool = BriefTool()
        self._send_handler = None
        self._pending: list[dict] = []
    
    def register_send_handler(self, handler):
        """注册发送处理器"""
        self._send_handler = handler
        self.brief_tool.send_callback = handler
    
    def heartbeat_check(self) -> list[dict]:
        """
        在 heartbeat 中调用。
        返回本轮产生的消息。
        """
        return self.checker.check()
    
    def send(self, message: str, status: BriefStatus = None) -> dict:
        """发送消息"""
        if status is None:
            status = self.classifier.classify(message)
        return self.brief_tool.execute(message, status.value)
    
    def queue(self, message: str):
        """排队一条消息（下次心跳时发送）"""
        self._pending.append({"message": message})
    
    def flush(self) -> list[dict]:
        """发送所有排队的消息"""
        results = []
        for item in self._pending:
            results.append(self.send(item["message"]))
        self._pending.clear()
        return results
