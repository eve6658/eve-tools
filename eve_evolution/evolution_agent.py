#!/usr/bin/env python3
"""
evolution_agent.py — Eve 自我进化引擎

核心模块，实现基于 Claude Code 设计理念的自我进化：
1. 错误学习：捕获错误 → 分析原因 → 记录教训 → 避免重犯
2. 模式识别：从历史操作中发现重复模式，自动提取经验规则
3. 能力扩展：发现新技能/工具 → 评估安全性 → 注册使用
4. 记忆维护：定期整理记忆文件，压缩/归档/提炼

与 memory_layered.py 的区别：
- memory_layered.py 是存储层（存什么、存在哪、TTL）
- evolution_agent.py 是决策层（学什么、怎么改、何时进化）

运行：
    python3 evolution_agent.py
    
使用示例：
    agent = EvolutionAgent(workspace="/home/adam/.openclaw/workspace")
    agent.record_error("exec", "rm -rf /", "权限被拒绝", "不要执行危险命令")
    lessons = agent.get_lessons_for("exec")
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import Counter


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ErrorLesson:
    """一次错误学习记录"""
    timestamp: str          # ISO 格式
    tool_name: str          # 工具名称
    command: str            # 触发错误的操作
    error_type: str         # 错误分类
    error_message: str      # 错误信息
    lesson: str             # 学到的教训
    confidence: float = 1.0 # 置信度 (0-1)
    times_applied: int = 0  # 被应用次数
    avoided: int = 0        # 成功避免次数
    
    def key(self) -> str:
        """唯一标识，用于去重"""
        return hashlib.md5(
            f"{self.tool_name}:{self.error_type}:{self.lesson}".encode()
        ).hexdigest()[:12]


@dataclass
class PatternRule:
    """从历史中提取的经验规则"""
    pattern: str            # 模式描述（触发条件）
    action: str             # 建议操作
    source: str             # 来源（"error_history" / "manual" / "auto"）
    confidence: float = 0.5 # 置信度
    usage_count: int = 0    # 使用次数
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Capability:
    """一个能力/技能描述"""
    name: str
    description: str
    category: str               # "tool" / "skill" / "knowledge"
    source: str                 # 来源路径或 URL
    safe: bool = True           # 安全评估
    registered: bool = False    # 是否已注册
    vetted_at: str = ""         # 审核时间
    notes: str = ""             # 备注


# ============================================================
# 进化引擎
# ============================================================

class EvolutionAgent:
    """
    Eve 自我进化引擎
    
    核心循环：
    1. 遇到错误 → record_error()
    2. 查询教训 → get_lessons_for()
    3. 提取模式 → extract_patterns()
    4. 评估能力 → assess_capability()
    5. 整理记忆 → maintain_memory()
    """
    
    def __init__(self, workspace: str = None):
        self.workspace = workspace or "/home/adam/.openclaw/workspace"
        self.evolution_dir = os.path.join(self.workspace, "eve-evolution")
        self.memory_dir = os.path.join(self.evolution_dir, "memory")
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # 数据文件路径
        self.errors_file = os.path.join(self.memory_dir, "error_lessons.json")
        self.patterns_file = os.path.join(self.memory_dir, "patterns.json")
        self.capabilities_file = os.path.join(self.memory_dir, "capabilities.json")
        
        # 加载已有数据
        self.error_lessons: Dict[str, ErrorLesson] = self._load_errors()
        self.patterns: List[PatternRule] = self._load_patterns()
        self.capabilities: Dict[str, Capability] = self._load_capabilities()
    
    # ---- 持久化 ----
    
    def _load_errors(self) -> Dict[str, ErrorLesson]:
        if not os.path.exists(self.errors_file):
            return {}
        try:
            with open(self.errors_file, "r") as f:
                data = json.load(f)
            return {k: ErrorLesson(**v) for k, v in data.items()}
        except Exception:
            return {}
    
    def _load_patterns(self) -> List[PatternRule]:
        if not os.path.exists(self.patterns_file):
            return []
        try:
            with open(self.patterns_file, "r") as f:
                data = json.load(f)
            return [PatternRule(**d) for d in data]
        except Exception:
            return []
    
    def _load_capabilities(self) -> Dict[str, Capability]:
        if not os.path.exists(self.capabilities_file):
            return {}
        try:
            with open(self.capabilities_file, "r") as f:
                data = json.load(f)
            return {k: Capability(**v) for k, v in data.items()}
        except Exception:
            return {}
    
    def save(self):
        """保存所有数据到文件"""
        # 错误教训
        with open(self.errors_file, "w") as f:
            json.dump(
                {k: asdict(v) for k, v in self.error_lessons.items()},
                f, ensure_ascii=False, indent=2
            )
        # 模式规则
        with open(self.patterns_file, "w") as f:
            json.dump(
                [asdict(p) for p in self.patterns],
                f, ensure_ascii=False, indent=2
            )
        # 能力清单
        with open(self.capabilities_file, "w") as f:
            json.dump(
                {k: asdict(v) for k, v in self.capabilities.items()},
                f, ensure_ascii=False, indent=2
            )
    
    # ---- 错误学习 ----
    
    def record_error(self, tool_name: str, command: str,
                     error_message: str, lesson: str,
                     error_type: str = "runtime") -> ErrorLesson:
        """
        记录一次错误和学到的教训
        
        Args:
            tool_name: 工具名（如 "exec", "shell"）
            command: 触发错误的操作描述
            error_message: 错误信息
            lesson: 学到的教训
            error_type: 错误分类（"runtime" / "permission" / "validation" / "network"）
        """
        lesson_obj = ErrorLesson(
            timestamp=datetime.now().isoformat(),
            tool_name=tool_name,
            command=command[:200],  # 截断防止过长
            error_type=error_type,
            error_message=error_message[:500],
            lesson=lesson,
        )
        
        key = lesson_obj.key()
        if key in self.error_lessons:
            # 已有类似记录，增加置信度
            existing = self.error_lessons[key]
            existing.confidence = min(1.0, existing.confidence + 0.1)
            existing.times_applied += 1
            return existing
        
        self.error_lessons[key] = lesson_obj
        self.save()
        return lesson_obj
    
    def get_lessons_for(self, tool_name: str = None,
                        error_type: str = None) -> List[ErrorLesson]:
        """查询相关教训"""
        results = list(self.error_lessons.values())
        
        if tool_name:
            results = [e for e in results if e.tool_name == tool_name]
        if error_type:
            results = [e for e in results if e.error_type == error_type]
        
        # 按置信度排序
        results.sort(key=lambda e: e.confidence, reverse=True)
        return results
    
    def mark_avoided(self, lesson_key: str):
        """标记某条教训成功避免了一次错误"""
        if lesson_key in self.error_lessons:
            self.error_lessons[lesson_key].avoided += 1
            self.save()
    
    # ---- 模式提取 ----
    
    def extract_patterns(self) -> List[PatternRule]:
        """
        从错误历史中自动提取模式规则
        
        例如：
        - 多次 "权限被拒绝" → 规则：检查权限再执行
        - 多次 "文件不存在" → 规则：先检查文件是否存在
        """
        if not self.error_lessons:
            return []
        
        # 按 error_type 分组统计
        type_count = Counter()
        tool_errors = Counter()
        
        for lesson in self.error_lessons.values():
            type_count[lesson.error_type] += 1
            tool_errors[f"{lesson.tool_name}:{lesson.error_type}"] += 1
        
        new_patterns = []
        
        # 如果某个错误类型出现 >=3 次，提取规则
        for error_type, count in type_count.items():
            if count >= 3:
                matching = [e for e in self.error_lessons.values() 
                           if e.error_type == error_type]
                lessons_text = " | ".join(e.lesson for e in matching[:3])
                
                pattern = PatternRule(
                    pattern=f"遇到 {error_type} 类错误 (出现{count}次)",
                    action=lessons_text,
                    source="auto",
                    confidence=min(0.8, 0.3 + count * 0.1),
                    usage_count=count,
                )
                new_patterns.append(pattern)
        
        # 工具+错误类型组合
        for combo, count in tool_errors.items():
            if count >= 2:
                tool, err = combo.split(":", 1)
                matching = [e for e in self.error_lessons.values()
                           if e.tool_name == tool and e.error_type == err]
                lessons_text = " | ".join(e.lesson for e in matching[:2])
                
                pattern = PatternRule(
                    pattern=f"使用 {tool} 时遇到 {err} (出现{count}次)",
                    action=lessons_text,
                    source="auto",
                    confidence=min(0.8, 0.3 + count * 0.15),
                    usage_count=count,
                )
                new_patterns.append(pattern)
        
        # 合并到已有模式（去重）
        existing_keys = {(p.pattern, p.action) for p in self.patterns}
        for p in new_patterns:
            if (p.pattern, p.action) not in existing_keys:
                self.patterns.append(p)
        
        self.save()
        return new_patterns
    
    def get_relevant_patterns(self, context: str) -> List[PatternRule]:
        """根据当前上下文返回相关模式"""
        context_lower = context.lower()
        relevant = []
        
        for p in self.patterns:
            # 简单关键词匹配
            pattern_words = p.pattern.lower().split()
            if any(w in context_lower for w in pattern_words):
                relevant.append(p)
        
        relevant.sort(key=lambda p: p.confidence, reverse=True)
        return relevant[:5]
    
    # ---- 能力管理 ----
    
    def assess_capability(self, name: str, description: str,
                          category: str, source: str,
                          safety_notes: str = "") -> Capability:
        """
        评估一个新能力/技能
        
        简单安全检查：
        - 不允许修改系统核心文件
        - 不允许网络外发
        - 不允许权限提升
        """
        safe = True
        notes = safety_notes
        
        # 安全扫描
        danger_keywords = ["rm -rf", "/etc/", "/usr/bin", "sudo", "chmod 777",
                          "wget | sh", "curl | bash", "> /dev/", "mkfs"]
        for kw in danger_keywords:
            if kw in description.lower() or kw in source.lower():
                safe = False
                notes += f" [警告: 包含危险关键词 '{kw}']"
                break
        
        cap = Capability(
            name=name,
            description=description,
            category=category,
            source=source,
            safe=safe,
            vetted_at=datetime.now().isoformat(),
            notes=notes,
        )
        
        self.capabilities[name] = cap
        self.save()
        return cap
    
    def register_capability(self, name: str) -> bool:
        """标记一个能力已注册"""
        if name in self.capabilities:
            self.capabilities[name].registered = True
            self.save()
            return True
        return False
    
    # ---- 记忆维护 ----
    
    def maintain_memory(self) -> dict:
        """
        整理记忆：
        1. 清理过期教训（置信度 < 0.2 且未被应用过）
        2. 提取模式
        3. 生成维护报告
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "before": {
                "errors": len(self.error_lessons),
                "patterns": len(self.patterns),
                "capabilities": len(self.capabilities),
            }
        }
        
        # 清理低置信度教训
        to_remove = []
        for key, lesson in self.error_lessons.items():
            if lesson.confidence < 0.2 and lesson.times_applied == 0:
                to_remove.append(key)
        
        for key in to_remove:
            del self.error_lessons[key]
        
        # 提取新模式
        new_patterns = self.extract_patterns()
        
        report["cleaned"] = len(to_remove)
        report["new_patterns"] = len(new_patterns)
        report["after"] = {
            "errors": len(self.error_lessons),
            "patterns": len(self.patterns),
            "capabilities": len(self.capabilities),
        }
        
        self.save()
        return report
    
    # ---- 状态报告 ----
    
    def status(self) -> dict:
        """返回进化引擎状态"""
        errors = list(self.error_lessons.values())
        return {
            "workspace": self.workspace,
            "total_errors": len(errors),
            "total_patterns": len(self.patterns),
            "total_capabilities": len(self.capabilities),
            "error_types": dict(Counter(e.error_type for e in errors)),
            "top_tools": dict(Counter(e.tool_name for e in errors).most_common(5)),
            "avoidance_rate": (
                sum(e.avoided for e in errors) / max(1, sum(e.times_applied for e in errors))
            ),
            "confidence_avg": (
                sum(e.confidence for e in errors) / max(1, len(errors))
            ),
        }


# ============================================================
# 演示
# ============================================================

if __name__ == "__main__":
    agent = EvolutionAgent()
    
    print("=" * 60)
    print("Eve Evolution Agent — 自我进化引擎演示")
    print("=" * 60)
    
    # 1. 模拟错误学习
    print("\n📚 错误学习演示:")
    agent.record_error("exec", "rm -rf /important", 
                       "PermissionError: Permission denied",
                       "不要执行 rm -rf / 等危险命令，先用 trash 或 --dry-run",
                       "permission")
    agent.record_error("exec", "sudo apt install xxx",
                       "Error: lock file exists",
                       "检查是否有其他 apt 进程在运行，先 kill 或等它完成",
                       "runtime")
    agent.record_error("shell", "pip install xxx",
                       "Error: permission denied on /usr/lib",
                       "用 pip install --user 或先激活 venv",
                       "permission")
    
    lessons = agent.get_lessons_for("exec")
    for l in lessons:
        print(f"  ⚠️ [{l.error_type}] {l.command[:50]}...")
        print(f"     教训: {l.lesson}")
        print(f"     置信度: {l.confidence:.1f}")
    
    # 2. 模式提取
    print("\n🔍 模式提取:")
    new = agent.extract_patterns()
    for p in new:
        print(f"  📏 {p.pattern}")
        print(f"     → {p.action[:80]}...")
    
    # 3. 能力评估
    print("\n🧪 能力评估:")
    cap = agent.assess_capability(
        "web_search", "搜索网页内容", "tool",
        "https://github.com/example/search",
        "标准搜索工具"
    )
    print(f"  {'🟢' if cap.safe else '🔴'} {cap.name}: {cap.description}")
    
    # 4. 状态
    print("\n📊 进化状态:")
    status = agent.status()
    for k, v in status.items():
        print(f"  {k}: {v}")
    
    print("\n✅ 演示完成！")
