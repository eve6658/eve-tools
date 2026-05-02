"""
Swarm Coordinator — 多级 Swarm 协调器

参考 ECC 的 Cross-Harness Parity + OpenClaw 的 subagent 系统：
- 支持多级子代理（Coordinator → Worker → Sub-worker）
- 任务分发 + 进度追踪 + 结果聚合
- 支持并行执行 + 依赖链
- Worker 沙箱隔离

与 coordinator/ 的区别：
- coordinator 是单级调度（Coordinator → Worker）
- swarm 支持多级递归调度（Coordinator → Worker → Sub-worker）
"""

import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"  # 等待依赖完成


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class SwarmTask:
    """Swarm 任务"""
    id: str
    description: str
    prompt: str
    agent_type: str = "worker"     # worker / researcher / coder / analyst
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    result: str = ""
    error: str = ""
    dependencies: list[str] = field(default_factory=list)  # 依赖的任务 ID
    parent_id: str = ""     # 父任务 ID
    children: list[str] = field(default_factory=list)      # 子任务 ID
    depth: int = 0          # 层级深度
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    
    @property
    def duration(self) -> float:
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return 0


@dataclass
class SwarmWorker:
    """Swarm Worker"""
    id: str
    agent_type: str
    status: TaskStatus = TaskStatus.PENDING
    current_task: str = ""
    tasks_completed: int = 0
    tasks_failed: int = 0


# ============================================================
# Agent 类型定义
# ============================================================

AGENT_TYPES = {
    "worker": {
        "tools": ["shell", "read_file", "write_file", "edit_file", "memory_io"],
        "description": "通用执行 Worker",
    },
    "researcher": {
        "tools": ["web_search", "web_fetch", "shell", "read_file"],
        "description": "信息搜索研究员",
    },
    "coder": {
        "tools": ["shell", "read_file", "write_file", "edit_file", "memory_io"],
        "description": "代码编写专家",
    },
    "analyst": {
        "tools": ["shell", "read_file", "memory_io", "web_search"],
        "description": "数据分析专家",
    },
    "verifier": {
        "tools": ["shell", "read_file"],
        "description": "结果验证器",
    },
}


# ============================================================
# Swarm Coordinator
# ============================================================

class SwarmCoordinator:
    """
    多级 Swarm 协调器。
    
    对比 coordinator/:
    - 单级: Coordinator → Worker (flat)
    - Swarm:  Coordinator → Worker → Sub-worker (递归)
    
    功能:
    - 任务分解 + DAG 依赖图
    - 并行执行 + 进度追踪
    - 结果链式聚合
    - Worker 沙箱隔离
    """
    
    def __init__(self, workspace: str = "."):
        self.workspace = workspace
        self.tasks: dict[str, SwarmTask] = {}
        self.workers: dict[str, SwarmWorker] = {}
        self.max_depth = 3          # 最大递归深度
        self.max_parallel = 5       # 最大并行 Worker 数
        self.scratchpad_dir = os.path.join(workspace, ".scratchpad", "swarm")
        os.makedirs(self.scratchpad_dir, exist_ok=True)
    
    # ============================================================
    # 任务提交 + 分解
    # ============================================================
    
    def submit(self, prompt: str, agent_type: str = "worker",
               priority: TaskPriority = TaskPriority.NORMAL,
               dependencies: list[str] = None) -> SwarmTask:
        """提交任务"""
        task = SwarmTask(
            id=f"task_{uuid.uuid4().hex[:8]}",
            description=prompt[:50],
            prompt=prompt,
            agent_type=agent_type,
            priority=priority,
            dependencies=dependencies or [],
        )
        self.tasks[task.id] = task
        return task
    
    def decompose(self, user_request: str, max_subtasks: int = 5) -> list[SwarmTask]:
        """
        将复杂任务分解为子任务。
        
        支持三种分解模式：
        1. 并行分解：独立子任务同时执行
        2. 顺序分解：有依赖关系的链式执行
        3. MapReduce：分发 → 聚合
        """
        tasks = []
        
        # 简单的关键词分解（实际应由 LLM 分析）
        if "和" in user_request or "以及" in user_request:
            parts = user_request.replace("和", "|").replace("以及", "|").split("|")
            for i, part in enumerate(parts):
                agent_type = "worker"
                if "搜索" in part or "查" in part:
                    agent_type = "researcher"
                elif "代码" in part or "写" in part:
                    agent_type = "coder"
                elif "分析" in part or "数据" in part:
                    agent_type = "analyst"
                
                task = self.submit(part.strip(), agent_type)
                tasks.append(task)
        else:
            tasks.append(self.submit(user_request, "worker"))
        
        return tasks
    
    # ============================================================
    # 任务执行（与 OpenClaw sessions_spawn 对接）
    # ============================================================
    
    def get_spawn_args(self, task: SwarmTask) -> dict:
        """
        获取 sessions_spawn 的参数。
        
        返回可以直接传给 sessions_spawn() 的字典。
        """
        agent_map = {
            "worker": "worker",
            "researcher": "researcher",
            "coder": "coder",
            "analyst": "researcher",  # 用 researcher
            "verifier": "worker",     # 用 worker
        }
        
        agent_id = agent_map.get(task.agent_type, "worker")
        
        # 构建包含 scratchpad 上下文的任务描述
        parent_context = ""
        if task.parent_id and task.parent_id in self.tasks:
            parent = self.tasks[task.parent_id]
            parent_context = f"父任务上下文: {parent.description}\n\n"
        
        dep_context = ""
        for dep_id in task.dependencies:
            if dep_id in self.tasks:
                dep = self.tasks[dep_id]
                dep_context += f"前置任务 {dep.description}: {dep.result[:200]}\n"
        
        return {
            "agentId": agent_id,
            "task": f"{parent_context}{dep_context}任务: {task.prompt}",
            "label": task.description[:20],
        }
    
    def mark_running(self, task_id: str):
        """标记任务开始执行"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.RUNNING
            self.tasks[task_id].started_at = time.time()
    
    def mark_completed(self, task_id: str, result: str):
        """标记任务完成"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED
            self.tasks[task_id].result = result
            self.tasks[task_id].completed_at = time.time()
            
            # 写入 scratchpad
            self._write_result(task_id, result)
    
    def mark_failed(self, task_id: str, error: str):
        """标记任务失败"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.FAILED
            self.tasks[task_id].error = error
            self.tasks[task_id].completed_at = time.time()
    
    # ============================================================
    # 依赖管理
    # ============================================================
    
    def get_runnable_tasks(self) -> list[SwarmTask]:
        """获取可执行的任务（依赖已满足）"""
        runnable = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            if self._dependencies_met(task):
                runnable.append(task)
        
        # 按优先级排序
        runnable.sort(key=lambda t: t.priority.value, reverse=True)
        return runnable[:self.max_parallel]
    
    def _dependencies_met(self, task: SwarmTask) -> bool:
        """检查所有依赖是否完成"""
        for dep_id in task.dependencies:
            if dep_id not in self.tasks:
                return False
            dep = self.tasks[dep_id]
            if dep.status != TaskStatus.COMPLETED:
                return False
        return True
    
    # ============================================================
    # 结果聚合
    # ============================================================
    
    def aggregate(self) -> dict:
        """聚合所有任务结果"""
        completed = [t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]
        failed = [t for t in self.tasks.values() if t.status == TaskStatus.FAILED]
        pending = [t for t in self.tasks.values() if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING)]
        
        results = []
        for t in completed:
            results.append(f"✅ [{t.description}] {t.result[:200]}")
        for t in failed:
            results.append(f"❌ [{t.description}] {t.error}")
        
        return {
            "total": len(self.tasks),
            "completed": len(completed),
            "failed": len(failed),
            "pending": len(pending),
            "results": results,
            "summary": f"共 {len(self.tasks)} 个任务, {len(completed)} 完成, {len(failed)} 失败",
        }
    
    # ============================================================
    # Scratchpad
    # ============================================================
    
    def _write_result(self, task_id: str, result: str):
        """写入任务结果到 scratchpad"""
        os.makedirs(self.scratchpad_dir, exist_ok=True)
        path = os.path.join(self.scratchpad_dir, f"{task_id}.md")
        with open(path, "w", encoding="utf-8") as f:
            task = self.tasks[task_id]
            f.write(f"# Task: {task.description}\n\n")
            f.write(f"Agent: {task.agent_type}\n")
            f.write(f"Status: {task.status.value}\n")
            f.write(f"Duration: {task.duration:.1f}s\n\n")
            f.write(f"## Result\n\n{result}")
    
    def read_scratchpad(self, task_id: str = None) -> str:
        """读取 scratchpad 内容"""
        if task_id:
            path = os.path.join(self.scratchpad_dir, f"{task_id}.md")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            return ""
        
        # 读取所有
        contents = []
        for f in os.listdir(self.scratchpad_dir):
            if f.endswith(".md"):
                path = os.path.join(self.scratchpad_dir, f)
                with open(path, "r", encoding="utf-8") as fh:
                    contents.append(fh.read())
        return "\n\n---\n\n".join(contents)
    
    # ============================================================
    # 状态查询
    # ============================================================
    
    def get_status(self) -> dict:
        """获取整体状态"""
        by_status = {}
        by_agent = {}
        
        for task in self.tasks.values():
            by_status[task.status.value] = by_status.get(task.status.value, 0) + 1
            by_agent[task.agent_type] = by_agent.get(task.agent_type, 0) + 1
        
        return {
            "tasks": by_status,
            "agents": by_agent,
            "depth": self.max_depth,
            "parallel": self.max_parallel,
            "runnable": len(self.get_runnable_tasks()),
        }
