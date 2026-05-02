"""
Undercover 安全模式

参考 Claude Code src/utils/undercover.ts：
- 默认开启，无强制关闭
- 自动检测敏感信息并替换/移除
- 在消息发送前自动检查

核心原则：宁可过度保护，不泄露内部信息。
"""

import re
import os
from dataclasses import dataclass


@dataclass
class SensitivityHit:
    pattern: str
    match: str
    replacement: str
    severity: str = "warning"  # info / warning / critical


# ============================================================
# 敏感信息检测规则
# ============================================================

SENSITIVE_RULES = [
    # API 密钥
    {
        "name": "API Key",
        "pattern": r'(sk-[a-zA-Z0-9]{20,})',
        "replacement": "[API_KEY_REDACTED]",
        "severity": "critical",
    },
    # 内部项目代号
    {
        "name": "Internal Codename",
        "pattern": r'\b(capybara|tengu|opus-\d|sonnet-\d|haiku-\d)\b',
        "replacement": "[REDACTED_MODEL]",
        "severity": "critical",
    },
    # 内部短链接
    {
        "name": "Internal Shortlink",
        "pattern": r'\bgo/[a-zA-Z0-9_/-]+\b',
        "replacement": "[INTERNAL_LINK]",
        "severity": "warning",
    },
    # Slack 内部频道
    {
        "name": "Internal Slack Channel",
        "pattern": r'#[a-z0-9_-]+-internal\b',
        "replacement": "#[INTERNAL_CHANNEL]",
        "severity": "warning",
    },
    # 内部 IP
    {
        "name": "Internal IP",
        "pattern": r'\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        "replacement": "[INTERNAL_IP]",
        "severity": "warning",
    },
    # 内部域名
    {
        "name": "Internal Domain",
        "pattern": r'\b[a-z]+\.anthropic\.com\b',
        "replacement": "[INTERNAL_DOMAIN]",
        "severity": "warning",
    },
    # SSH 密钥
    {
        "name": "SSH Key",
        "pattern": r'-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----',
        "replacement": "[SSH_KEY_REDACTED]",
        "severity": "critical",
    },
    # 密码/Token
    {
        "name": "Password/Token",
        "pattern": r'(password|token|secret|api_key)["\s:=]+["\']?[a-zA-Z0-9]{16,}',
        "replacement": "[CREDENTIAL_REDACTED]",
        "severity": "critical",
    },
]


# ============================================================
# 检测器
# ============================================================

class UndercoverDetector:
    """
    消息发送前的敏感信息检测。
    
    对应 Claude Code 的 isUndercover() + getUndercoverInstructions()：
    - 自动检测敏感信息
    - 区分 severity 级别
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._rules = SENSITIVE_RULES
        self._whitelist: set[str] = set()
    
    def add_whitelist(self, pattern: str):
        """添加白名单模式（确认安全的字符串）"""
        self._whitelist.add(pattern)
    
    def check(self, text: str) -> list[SensitivityHit]:
        """
        检查文本中是否包含敏感信息。
        返回所有命中规则。
        """
        if not self.enabled:
            return []
        
        hits = []
        for rule in self._rules:
            for match in re.finditer(rule["pattern"], text, re.IGNORECASE):
                # 检查白名单
                if any(wp in match.group() for wp in self._whitelist):
                    continue
                hits.append(SensitivityHit(
                    pattern=rule["name"],
                    match=match.group(),
                    replacement=rule["replacement"],
                    severity=rule["severity"],
                ))
        
        return hits
    
    def has_critical(self, text: str) -> bool:
        """是否包含危急级别的敏感信息"""
        hits = self.check(text)
        return any(h.severity == "critical" for h in hits)
    
    def is_safe(self, text: str) -> bool:
        """文本是否安全"""
        return len(self.check(text)) == 0


# ============================================================
# 清洗器
# ============================================================

class Sanitizer:
    """
    敏感信息自动替换。
    
    对应 Claude Code 的 undercover 安全措施：
    - 自动替换所有匹配的敏感信息
    - 保留原文可读性
    """
    
    def __init__(self):
        self._rules = SENSITIVE_RULES
        self._custom_replacements: dict[str, str] = {}
    
    def add_replacement(self, pattern: str, replacement: str):
        """添加自定义替换规则"""
        self._custom_replacements[pattern] = replacement
    
    def sanitize(self, text: str) -> str:
        """替换所有敏感信息"""
        # 先用自定义规则
        for pattern, replacement in self._custom_replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # 再用内置规则
        for rule in self._rules:
            text = re.sub(rule["pattern"], rule["replacement"], text, flags=re.IGNORECASE)
        
        return text
    
    def sanitize_and_check(self, text: str) -> tuple[str, list[SensitivityHit]]:
        """清洗并返回命中的规则列表"""
        detector = UndercoverDetector()
        hits = detector.check(text)
        sanitized = self.sanitize(text)
        return sanitized, hits


# ============================================================
# Undercover 模式（完整实现）
# ============================================================

class UndercoverMode:
    """
    完整的 Undercover 安全模式。
    
    对应 Claude Code 的 undercover.ts：
    - 默认开启
    - 发送前自动检查
    - 自动清洗
    - 日志记录
    """
    
    def __init__(self, enabled: bool = True, strict: bool = False):
        """
        Args:
            enabled: 是否启用安全检查
            strict: 严格模式（有危急信息时阻止发送）
        """
        self.enabled = enabled
        self.strict = strict
        self.detector = UndercoverDetector(enabled)
        self.sanitizer = Sanitizer()
        self.stats = {
            "checks": 0,
            "hits": 0,
            "sanitized": 0,
            "blocked": 0,
        }
    
    def check_and_prepare(self, text: str) -> tuple[str, bool, list[SensitivityHit]]:
        """
        检查并准备发送。
        
        Returns:
            (processed_text, should_send, hits)
        """
        if not self.enabled:
            return text, True, []
        
        self.stats["checks"] += 1
        hits = self.detector.check(text)
        
        if not hits:
            return text, True, []
        
        self.stats["hits"] += 1
        has_critical = any(h.severity == "critical" for h in hits)
        
        if has_critical and self.strict:
            # 严格模式：阻止发送
            self.stats["blocked"] += 1
            return text, False, hits
        
        # 清洗后发送
        sanitized = self.sanitizer.sanitize(text)
        self.stats["sanitized"] += 1
        return sanitized, True, hits
    
    def get_stats(self) -> dict:
        """获取安全统计"""
        return dict(self.stats)
    
    def __repr__(self):
        status = "ON" if self.enabled else "OFF"
        strict = "strict" if self.strict else "lenient"
        return f"UndercoverMode({status}, {strict})"
