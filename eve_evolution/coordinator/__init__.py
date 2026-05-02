"""
Coordinator 多智能体协调器

参考 Claude Code src/coordinator/coordinatorMode.ts + src/tools/AgentTool/：
- Coordinator 只有 4 个工具（Agent/TaskStop/SendMessage/SyntheticOutput）
- Worker 拥有完整工具集（但不能 spawn 子代理）
- Fork 模式（继承上下文 + 共享缓存）
- Scratchpad 共享知识空间
"""

import enum
import os
import time
import uuid
from dataclasses import dataclass, field


# ============================================================
# 工具集限制（对应 Claude Code 的 COORDINATOR_MODE_ALLOWED_TOOLS）
# ============================================================

COORDINATOR_ALLOWED_TOOLS = {
    "sessions_spawn",   # AgentTool — spawn worker
    "subagents",        # TaskStop — list/steer/kill
    "sessions_send",    # SendMessage — 给 worker 发消息
    "shell",            # SyntheticOutput — 基础状态检查
}

WORKER_ALLOWED_TOOLS = [
    "shell", "read_file", "write_file", "edit_file",
    "memory_io", "web_search", "web_fetch",
    "skill", "self_improve",
]

WORKER_DENIED_TOOLS = [
    "sessions_spawn",   # 不能 spawn 子子代理
    "sessions_send",    # 不能直接给用户发消息
    "subagents",        # 不能管理其他 agent
]


# ============================================================
# Task（任务定义）
# ============================================================

class TaskStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    id: str = ""
    description: str = ""
    prompt: str = ""
    workspace: str = "."
    status: TaskStatus = TaskStatus.PENDING
    result: str = ""
    error: str = ""
    created_at: float = 0.0
    completed_at: float = 0.0
    
    def __post_init__(self):
        if not self.id:
            self.id = f"task_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()


# ============================================================
# Worker Handle
# ============================================================

@dataclass
class WorkerHandle:
    """Worker 的句柄（对应 Claude Code 的 agent handle）"""
    task_id: str
    agent_id: str
    label: str
    status: TaskStatus = TaskStatus.PENDING
    result: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0


# ============================================================
# Coordinator（协调器核心）
# ============================================================

class Coordinator:
    """
    多智能体协调器。
    
    对应 Claude Code 的 Coordinator Mode：
    - 只有 4 个工具可用
    - 将任务拆分给多个 Worker 并行执行
    - 通过 Scratchpad 共享知识
    - 聚合 Worker 结果
    
    用法：
        coordinator = Coordinator(eve_agent)
        result = await coordinator.execute("帮我分析这几个文件")
    """
    
    def __init__(self, eve_agent=None, workspace: str = "."):
        self.eve = eve_agent
        self.workspace = workspace
        self.workers: dict[str, WorkerHandle] = {}
        self.scratchpad_dir = os.path.join(workspace, ".scratchpad")
        self.tasks_completed = 0
        self.tasks_failed = 0
    
    def is_coordinator_mode(self, context: dict = None) -> bool:
        """检查是否处于 Coordinator 模式"""
        if context and "coordinator_mode" in context:
            return context["coordinator_mode"]
        return os.environ.get("EVE_COORDINATOR_MODE", "").lower() == "1"
    
    # ============================================================
    # 任务分解（对应 Claude Code 的 prompt 要求）
    # ============================================================
    
    def decompose(self, user_request: str) -> list[Task]:
        """
        将用户需求拆分为独立子任务。
        
        Claude Code 的设计原则：
        - 识别可并行执行的子任务
        - 每个 task 要足够独立
        - 明确 task 的输入和预期输出
        """
        # 简单的关键词分解（实际应由 LLM 分析）
        tasks = []
        
        # 检测是否需要多个任务
        if "和" in user_request or "以及" in user_request or "还有" in user_request:
            parts = user_request.replace("和", "|").replace("以及", "|").replace("还有", "|").split("|")
            for i, part in enumerate(parts):
                tasks.append(Task(
                    description=part.strip(),
                    prompt=f"完成以下任务：{part.strip()}\n\n工作区：{self.workspace}",
                    workspace=self.workspace,
                ))
        else:
            tasks.append(Task(
                description=user_request,
                prompt=f"完成以下任务：{user_request}\n\n工作区：{self.workspace}",
                workspace=self.workspace,
            ))
        
        return tasks
    
    # ============================================================
    # 派发 + 执行（对应 Claude Code 的 AgentTool）
    # ============================================================
    
    def dispatch(self, task: Task) -> WorkerHandle:
        """派发任务给 Worker"""
        handle = WorkerHandle(
            task_id=task.id,
            agent_id=f"worker_{uuid.uuid4().hex[:8]}",
            label=task.description[:20],
            status=TaskStatus.RUNNING,
            started_at=time.time(),
        )
        self.workers[handle.agent_id] = handle
        
        # 实际执行会通过 OpenClaw 的 sessions_spawn 完成
        # 这里只是创建句柄
        return handle
    
    def update_worker(self, agent_id: str, result: str = "", error: str = ""):
        """更新 Worker 状态"""
        if agent_id not in self.workers:
            return
        handle = self.workers[agent_id]
        if error:
            handle.status = TaskStatus.FAILED
            handle.error = error
            self.tasks_failed += 1
        else:
            handle.status = TaskStatus.COMPLETED
            handle.result = result
            self.tasks_completed += 1
        handle.completed_at = time.time()
    
    # ============================================================
    # Scratchpad（共享知识空间）
    # ============================================================
    
    def scratchpad_write(self, agent_id: str, content: str):
        """写入 scratchpad（对应 Claude Code 的 scratchpad 目录）"""
        os.makedirs(self.scratchpad_dir, exist_ok=True)
        path = os.path.join(self.scratchpad_dir, f"{agent_id}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"<!-- Agent: {agent_id}, Time: {time.strftime('%H:%M:%S')} -->\n")
            f.write(content)
    
    def scratchpad_read(self, agent_id: str = None) -> dict[str, str]:
        """读取 scratchpad 内容"""
        if not os.path.exists(self.scratchpad_dir):
            return {}
        
        contents = {}
        for f in os.listdir(self.scratchpad_dir):
            if f.endswith(".md"):
                path = os.path.join(self.scratchpad_dir, f)
                with open(path, "r", encoding="utf-8") as fh:
                    contents[f.replace(".md", "")] = fh.read()
        
        if agent_id:
            return {agent_id: contents.get(agent_id, "")}
        return contents
    
    # ============================================================
    # Fork 模式（对应 Claude Code 的 fork subagent）
    # ============================================================
    
    def fork(self, parent_task: Task, fork_prompt: str) -> Task:
        """
        Fork 一个子任务。
        
        Fork 与普通 spawn 的区别：
        - Fork 继承父任务的上下文
        - Fork 共享 workspace 和 scratchpad
        - 适合"在已有基础上做另一个独立工作"
        """
        forked = Task(
            description=f"[fork] {fork_prompt}",
            prompt=f"在以下上下文基础上继续：\n\n{parent_task.prompt}\n\n新任务：{fork_prompt}",
            workspace=parent_task.workspace,
        )
        return forked
    
    # ============================================================
    # 结果聚合（对应 Claude Code 的 agent result synthesis）
    # ============================================================
    
    def aggregate(self) -> dict:
        """聚合所有 Worker 的结果"""
        total = len(self.workers)
        completed = sum(1 for w in self.workers.values() if w.status == TaskStatus.COMPLETED)
        failed = sum(1 for w in self.workers.values() if w.status == TaskStatus.FAILED)
        
        results = []
        for w in self.workers.values():
            if w.status == TaskStatus.COMPLETED:
                results.append(f"[{w.label}] {w.result[:200]}")
            elif w.status == TaskStatus.FAILED:
                results.append(f"[{w.label}] ❌ 失败: {w.error}")
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "results": results,
            "summary": f"共 {total} 个任务，{completed} 完成，{failed} 失败",
        }
    
    # ============================================================
    # 完整执行流程
    # ============================================================
    
    def execute(self, user_request: str) -> dict:
        """完整执行：分解 → 派发 → 等待 → 聚合"""
        # 1. 分解
        tasks = self.decompose(user_request)
        
        # 2. 派发
        handles = []
        for task in tasks:
            handle = self.dispatch(task)
            handles.append(handle)
        
        # 3.（实际执行通过外部 spawn）
        
        # 4. 返回状态供外部使用
        return {
            "mode": "coordinator",
            "tasks_created": len(tasks),
            "task_ids": [t.id for t in tasks],
            "worker_ids": [h.agent_id for h in handles],
            "message": f"已创建 {len(tasks)} 个任务，等待 worker 执行",
        }


# ============================================================
# Worker 上下文（用于创建 Worker 时的环境配置）
# ============================================================

@dataclass
class WorkerContext:
    """Worker 的运行环境"""
    agent_id: str
    task: Task
    allowed_tools: list[str] = field(default_factory=lambda: list(WORKER_ALLOWED_TOOLS))
    denied_tools: list[str] = field(default_factory=lambda: list(WORKER_DENIED_TOOLS))
    scratchpad_dir: str = ""
    
    def can_use_tool(self, tool_name: str) -> bool:
        if tool_name in self.denied_tools:
            return False
        return len(self.allowed_tools) == 0 or tool_name in self.allowed_tools
