"""
Fork 模式增强

在 OpenClaw sessions_spawn 基础上增加 Fork 语义：
- 继承最近 N 条对话消息到 scratchpad
- 共享 workspace 目录
- 子代理通过 scratchpad 回传结果
"""

import os
import time
import uuid
from dataclasses import dataclass, field


@dataclass
class InheritedMessage:
    """继承的消息片段"""
    role: str        # "user" / "assistant"
    content: str
    timestamp: float = 0.0


@dataclass
class ForkContext:
    """Fork 上下文（传给子代理）"""
    fork_id: str
    parent_session: str
    workspace: str
    scratchpad_dir: str
    inherited_messages: list[InheritedMessage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
    def save_context_file(self):
        """将继承的上下文写入 scratchpad 文件"""
        os.makedirs(self.scratchpad_dir, exist_ok=True)
        path = os.path.join(self.scratchpad_dir, f"{self.fork_id}_context.md")
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Fork Context: {self.fork_id}\n")
            f.write(f"Parent: {self.parent_session}\n")
            f.write(f"Workspace: {self.workspace}\n\n")
            
            if self.inherited_messages:
                f.write("## Inherited Context (last messages)\n\n")
                for msg in self.inherited_messages[-20:]:  # 最近 20 条
                    f.write(f"### {msg.role}\n{msg.content}\n\n")
            
            if self.metadata:
                f.write("## Metadata\n\n")
                for k, v in self.metadata.items():
                    f.write(f"- **{k}**: {v}\n")
        
        return path


class ForkManager:
    """
    管理 Fork 生命周期。
    
    对应 Claude Code 的 forkSubagent.ts：
    - fork 继承上下文
    - 共享 prompt cache（通过共享 workspace 模拟）
    - 结果通过 scratchpad 回传
    """
    
    def __init__(self, workspace: str = "."):
        self.workspace = workspace
        self.scratchpad_dir = os.path.join(workspace, ".scratchpad", "forks")
        self.active_forks: dict[str, ForkContext] = {}
    
    def fork(
        self,
        parent_session: str,
        messages: list[dict],
        task: str,
        name: str = "",
        inherit_last_n: int = 20,
    ) -> dict:
        """
        创建一个 Fork。
        
        Args:
            parent_session: 父会话标识
            messages: 父会话的消息列表 [{"role": "...", "content": "..."}]
            task: fork 的任务描述
            name: fork 名称（可选）
            inherit_last_n: 继承最近 N 条消息
        
        Returns:
            Fork 信息字典，可直接传给 sessions_spawn 的 task 参数
        """
        fork_id = f"fork_{uuid.uuid4().hex[:8]}"
        if not name:
            name = f"fork-{fork_id[:8]}"
        
        # 提取继承消息
        inherited = []
        for msg in messages[-inherit_last_n:]:
            inherited.append(InheritedMessage(
                role=msg.get("role", "unknown"),
                content=msg.get("content", "")[:2000],  # 每条限 2000 字符
                timestamp=msg.get("timestamp", time.time()),
            ))
        
        ctx = ForkContext(
            fork_id=fork_id,
            parent_session=parent_session,
            workspace=self.workspace,
            scratchpad_dir=self.scratchpad_dir,
            inherited_messages=inherited,
            metadata={"task": task, "created_at": time.time()},
        )
        
        # 保存上下文文件
        ctx_path = ctx.save_context_file()
        self.active_forks[fork_id] = ctx
        
        # 构建任务描述（继承上下文 + 新任务）
        inherited_text = ""
        if inherited:
            recent_summary = " | ".join(
                f"{m.role}: {m.content[:80]}" for m in inherited[-3:]
            )
            inherited_text = f"上下文（{len(inherited)} 条消息）：{recent_summary}\n\n"
        
        return {
            "fork_id": fork_id,
            "name": name,
            "task": f"{inherited_text}新任务：{task}",
            "workspace": self.workspace,
            "context_file": ctx_path,
            "inherited_count": len(inherited),
        }
    
    def get_fork(self, fork_id: str) -> ForkContext | None:
        """获取 Fork 上下文"""
        return self.active_forks.get(fork_id)
    
    def complete_fork(self, fork_id: str, result: str):
        """标记 Fork 完成"""
        if fork_id in self.active_forks:
            self.active_forks[fork_id].metadata["result"] = result
            self.active_forks[fork_id].metadata["completed_at"] = time.time()
    
    def cleanup_fork(self, fork_id: str):
        """清理 Fork 的 scratchpad 文件"""
        path = os.path.join(self.scratchpad_dir, f"{fork_id}_context.md")
        if os.path.exists(path):
            os.remove(path)
        self.active_forks.pop(fork_id, None)
    
    def read_fork_result(self, fork_id: str) -> str | None:
        """从 scratchpad 读取 Fork 的输出结果"""
        path = os.path.join(self.scratchpad_dir, f"{fork_id}_result.md")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return None
    
    def write_fork_result(self, fork_id: str, result: str):
        """写入 Fork 的输出结果到 scratchpad"""
        os.makedirs(self.scratchpad_dir, exist_ok=True)
        path = os.path.join(self.scratchpad_dir, f"{fork_id}_result.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Fork Result: {fork_id}\n\n{result}")
