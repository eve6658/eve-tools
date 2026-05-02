# Eve Evolution 进化计划

> 基于 Claude Code 2.1.88 源码分析（~30,000+ 行深度掌握）
> 制定日期：2026-04-03
> 版本：1.0

---

## 一、现状分析

### Eve 已有能力 vs Claude Code 对应

| Eve 能力 (已实现) | Claude Code 对应 | 状态 |
|-------------------|------------------|------|
| 统一工具接口 (EveTool) | buildTool 工厂模式 | ✅ 已完成 |
| 工具注册表 (ToolRegistry) | assembleToolPool | ✅ 已完成 |
| 技能自动发现 (SkillDiscoverer) | prefetchSkillDiscovery | ✅ 已完成（中文分词已修复） |
| 五层记忆系统 (LayeredMemory) | CLAUDE.md + nested + LRU | ✅ 已完成 |
| 三级历史压缩 (HistoryCompressor) | snip + compact + microcompact | ✅ 已完成（bug已修复） |
| 会话持久化 (SessionManager) | transcript + resume | ✅ 已完成 |
| OpenClaw 工具桥接 | tools.ts (Bash/Read/Write/Memory) | ✅ 已完成 |
| 自我进化引擎 | (Claude Code 没有) | ✅ 已完成 |
| 多 Agent 配置 | Coordinator Mode | ✅ 已配置（main/worker/coder/researcher） |

### Eve 独有优势

| 优势 | 说明 |
|------|------|
| **多通道接入** | QQ Bot、企业微信、Telegram、Discord 等 |
| **TTS 语音** | 内置语音合成，可讲故事 |
| **Cron/Heartbeat** | 定时任务 + 心跳轮询 |
| **MCP 工具集成** | 通过 MCP 调用企业微信、金融数据等 |
| **跨会话通信** | sessions_send + sessions_spawn |
| **Subagent 编排** | 可动态调度多个子代理 |

### Eve 的差距

| 差距 | Claude Code | Eve 当前 | 优先级 |
|------|-------------|----------|--------|
| 电子宠物/Buddy | 完整 18 种物种 + 稀有度 + 动画 | 无 | ⭐⭐⭐⭐⭐ |
| 主动消息 BriefTool | Kairos 模式，定时推送 | 靠心跳被动检查 | ⭐⭐⭐⭐ |
| 多智能体 Coordinator | 正式模式，4 工具限制 | 子代理无工具集限制 | ⭐⭐⭐⭐ |
| 安全模式 Undercover | 自动检测 + 剥离内部信息 | 无 | ⭐⭐⭐ |
| UI 设计系统 | 389 组件 + 主题 + 分发 | Webchat 是 OpenClaw 的 | ⭐⭐ |
| Fork 模式 | 继承上下文 + 共享缓存 | spawn 支持 thread mode | ⭐⭐⭐ |
| 工具权限三层检查 | validate → check → hook | 只有 sandbox 审批 | ⭐⭐⭐ |

---

## 二、Phase 1: Buddy 电子伴侣系统

> 预计：2-3 天 | 难度：低 | 价值：高（用户粘性 + 人格化）

### 参考设计（来自 Claude Code src/buddy/）

```
Claude Code Buddy:
├── companion.ts     — 确定性生成（hash → PRNG → 特性）
├── types.ts         — 18种物种、5级稀有度、5项属性
├── prompt.ts        — 系统提示词注入
├── CompanionSprite.tsx — React/Ink 动画（500ms tick）
└── sprites.ts       — ASCII sprite 渲染 + 帧动画
```

### Eve 实现

#### 文件结构

```
eve_evolution/buddy/
├── __init__.py          # 导出接口
├── types.py             # Species, Rarity, Stats, Companion
├── companion.py         # 确定性生成 + 存储 + 查询
├── personality.py       # LLM 生成名字和性格
├── prompt.py            # 系统提示词注入逻辑
└── render.py            # ASCII/Unicode 渲染（终端用）
```

#### 核心数据模型

```python
# types.py

SPECIES = [
    "🐱 猫", "🐉 龙", "🐙 章鱼", "🦉 猫头鹰",
    "🐧 企鹅", "🐢 乌龟", "👻 幽灵", "🤖 机器人",
    "🐰 兔子", "🍄 蘑菇", "🌵 仙人掌", "🦊 狐狸",
    "🐸 青蛙", "🦉 猫头鹰", "🦈 鲨鱼", "🦥 树懒",
    "🦊 九尾狐", "🐲 麒麟"
]

RARITIES = {
    "common": 60,      # ★
    "uncommon": 25,    # ★★
    "rare": 10,        # ★★★
    "epic": 4,         # ★★★★
    "legendary": 1,    # ★★★★★
}

STAT_NAMES = [
    "代码力",  # CODE
    "耐心",    # PATIENCE
    "混乱度",  # CHAOS
    "智慧",    # WISDOM
    "毒舌",    # SNARK
]

@dataclass
class CompanionBones:
    rarity: str
    species: str
    stat_values: dict[str, int]

@dataclass
class CompanionSoul:
    name: str          # LLM 生成
    personality: str   # LLM 生成

@dataclass
class Companion(CompanionBones, CompanionSoul):
    hatched_at: float  # timestamp
```

#### 确定性生成算法

```python
# companion.py

import hashlib, random

SALT = "eve-companion-2026"

def generate_companion(user_id: str) -> CompanionBones:
    """同一 user_id 永远生成同一个宠物"""
    hash_input = f"{user_id}{SALT}"
    seed = int(hashlib.sha256(hash_input.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    
    rarity = _roll_rarity(rng)
    species = rng.choice(SPECIES)
    stats = _roll_stats(rng, rarity)
    
    return CompanionBones(rarity=rarity, species=species, stat_values=stats)

def _roll_rarity(rng):
    roll = rng.random() * 100
    cumulative = 0
    for rarity, weight in RARITIES.items():
        cumulative += weight
        if roll < cumulative:
            return rarity
    return "common"
```

#### 系统提示词注入

```python
# prompt.py

def get_companion_prompt(companion: Companion) -> str:
    return f"""
## Companion
你有一个名为 {companion.name} 的{companion.species}陪伴你。
稀有度：{companion.rarity}
属性：{" / ".join(f"{k}={v}" for k, v in companion.stat_values.items())}

当用户提到{companion.name}或明显在跟宠物说话时，你可以代{companion.name}回应。
保持{companion.name}的个性：{_get_personality_hint(companion)}。
"""
```

#### 里程碑

- [ ] Day 1: types.py + companion.py（生成+存储）
- [ ] Day 1: personality.py（LLM 生成名字和性格）
- [ ] Day 2: prompt.py（系统提示词注入）
- [ ] Day 2: render.py（终端渲染 + /buddy 命令）
- [ ] Day 3: 集成测试 + OpenClaw 配置

---

## 三、Phase 2: BriefTool 主动消息系统

> 预计：3-4 天 | 难度：中 | 价值：高（主动助手 vs 被动问答）

### 参考设计（来自 Claude Code src/tools/BriefTool/）

```
Claude Code BriefTool:
├── BriefTool.ts      — SendUserMessage 工具
├── prompt.ts         — BRIEF_PROACTIVE_SECTION 提示词
└── 被 Kairos 模式控制:
    - getKairosActive() 运行时状态
    - feature('KAIROS') 编译期控制
    - 5分钟刷新间隔
```

### Eve 实现

#### 文件结构

```
eve_evolution/brief/
├── __init__.py
├── brief_tool.py     # BriefTool 实现
├── proactive.py      # 主动检查逻辑
├── classifier.py     # 消息分类器
└── scheduler.py      # 定时调度
```

#### BriefTool 核心

```python
# brief_tool.py

class BriefStatus(enum.Enum):
    NORMAL = "normal"      # 回应用户刚问的
    PROACTIVE = "proactive" # 主动推送

@dataclass
class BriefMessage:
    message: str          # Markdown 格式
    status: BriefStatus   # 主动 or 被动
    attachments: list[str]  # 可选附件路径

class BriefTool(EveTool):
    """对应 Claude Code 的 SendUserMessage"""
    
    def __init__(self):
        super().__init__(
            name="send_user_message",
            description="向用户发送消息",
            aliases=["brief", "notify"],
            category="core"
        )
    
    def execute(self, args, context):
        message = args.get("message", "")
        status = args.get("status", "normal")
        # 通过 OpenClaw 通道发送
        return BriefTool.ok(
            data={"sent": True, "status": status},
            summary=f"发送 {status} 消息 ({len(message)} 字符)"
        )
```

#### 主动检查逻辑

```python
# proactive.py

async def check_proactive_conditions(workspace: str) -> list[BriefMessage]:
    """定时检查是否需要主动告知用户"""
    messages = []
    
    # 1. 文件变化检测
    changes = await detect_file_changes(workspace)
    if changes:
        messages.append(BriefMessage(
            message=f"检测到 {len(changes)} 个文件变化",
            status=BriefStatus.PROACTIVE
        ))
    
    # 2. 邮件检查
    unread = await check_unread_emails()
    if unread:
        messages.append(BriefMessage(
            message=f"你有 {len(unread)} 封未读邮件",
            status=BriefStatus.PROACTIVE
        ))
    
    # 3. 任务完成通知
    # （从 subagent 完成事件获取）
    
    return messages
```

#### 与 Heartbeat 集成

```python
# scheduler.py

CHECK_INTERVAL_SECONDS = 300  # 5分钟

async def heartbeat_check(state: dict) -> dict:
    """在 heartbeat 中调用"""
    last_check = state.get("last_brief_check", 0)
    if time.time() - last_check < CHECK_INTERVAL_SECONDS:
        return state
    
    messages = await check_proactive_conditions(state["workspace"])
    for msg in messages:
        await send_brief_message(msg)
    
    state["last_brief_check"] = time.time()
    return state
```

#### 里程碑

- [ ] Day 1: brief_tool.py (BriefTool 基础实现)
- [ ] Day 2: classifier.py (消息分类器：urgent/normal/proactive)
- [ ] Day 2: proactive.py (主动检查逻辑)
- [ ] Day 3: scheduler.py + heartbeat 集成
- [ ] Day 3: 测试 + 配置

---

## 四、Phase 3: Coordinator 多智能体协调

> 预计：2-3 天 | 难度：中 | 价值：高（效率倍增）

### 参考设计（来自 Claude Code src/coordinator/ + src/tools/AgentTool/）

```
Claude Code Coordinator:
├── coordinatorMode.ts  — 模式判断 + 工具集限制
├── AgentTool.tsx       — 1397行，完整的 agent spawn 系统
├── forkSubagent.ts     — Fork 模式（继承上下文）
├── builtInAgents.ts    — 6种内置 agent
├── agentMemory.ts      — agent 级别记忆
└── runAgent.ts         — agent 执行引擎
```

### Eve 实现

#### 文件结构

```
eve_evolution/coordinator/
├── __init__.py
├── coordinator.py    # 协调器主逻辑
├── worker.py         # Worker 定义 + 工具集限制
├── fork.py           # Fork 模式
├── scratchpad.py     # 共享知识空间
└── aggregator.py     # 结果聚合
```

#### 协调器核心

```python
# coordinator.py

COORDINATOR_ALLOWED_TOOLS = {
    "sessions_spawn",    # spawn worker
    "subagents",         # list/steer/kill workers
    "sessions_send",     # send message to worker
    "shell",             # basic status check
}

class CoordinatorMode:
    def __init__(self, eve_agent):
        self.eve = eve_agent
        self.workers: dict[str, WorkerHandle] = {}
        self.scratchpad_dir = None
    
    async def decompose_task(self, user_request: str) -> list[Task]:
        """将用户需求拆分为可并行执行的任务"""
        # 分析请求，识别独立子任务
        # 返回 Task 列表
        pass
    
    async def dispatch(self, tasks: list[Task]) -> list[WorkerHandle]:
        """并行派发给多个 worker"""
        handles = []
        for task in tasks:
            handle = await self.eve.spawn_worker(task)
            handles.append(handle)
        return handles
    
    async def aggregate(self, handles: list[WorkerHandle]) -> str:
        """聚合所有 worker 的结果"""
        results = []
        for handle in handles:
            result = await handle.wait()
            results.append(result)
        return self._synthesize(results)
```

#### Worker 工具集限制

```python
# worker.py

WORKER_ALLOWED_TOOLS = [
    "shell", "read_file", "write_file",
    "memory_io", "web_search", "web_fetch"
]

WORKER_DENIED_TOOLS = [
    "sessions_spawn",   # 不能 spawn 子子代理
    "sessions_send",    # 不能直接给用户发消息
    "subagents",        # 不能管理其他 agent
]

def create_worker_context(task: Task, scratchpad_dir: str) -> ToolContext:
    return ToolContext(
        workspace=task.workspace,
        session_id=f"worker_{task.id}",
        allowed_tools=WORKER_ALLOWED_TOOLS,
        denied_tools=WORKER_DENIED_TOOLS,
        metadata={"scratchpad_dir": scratchpad_dir}
    )
```

#### Fork 模式

```python
# fork.py

class ForkMode:
    """继承父级上下文的轻量 worker"""
    
    async def fork(self, parent_context: ToolContext, task: str) -> WorkerHandle:
        """Fork 父级上下文，共享 prompt cache"""
        forked_ctx = ToolContext(
            workspace=parent_context.workspace,
            session_id=f"fork_{uuid4()[:8]}",
            inherited_messages=parent_context.messages[-20:],  # 最近20条
            allowed_tools=parent_context.allowed_tools,
        )
        return await self._execute(forked_ctx, task)
```

#### 里程碑

- [ ] Day 1: coordinator.py + worker.py（基础调度）
- [ ] Day 2: scratchpad.py + aggregator.py（共享知识 + 结果聚合）
- [ ] Day 2: fork.py（Fork 模式）
- [ ] Day 3: 集成测试 + 多 worker 并行测试

---

## 五、Phase 4: Undercover 安全模式

> 预计：1 天 | 难度：低 | 价值：中（安全防护）

### 参考设计（来自 Claude Code src/utils/undercover.ts）

```typescript
// 核心逻辑：
// 1. 默认开启（USER_TYPE === 'ant' 时）
// 2. 无强制关闭
// 3. 在 commit/PR/消息中剥离内部信息
```

### Eve 实现

#### 文件结构

```
eve_evolution/undercover/
├── __init__.py
├── detector.py       # 敏感信息检测
└── sanitizer.py      # 敏感信息替换/移除
```

#### 敏感信息规则

```python
# detector.py

SENSITIVE_PATTERNS = [
    # 模型内部代号
    (r'\b(capybara|tengu|opus-\d|sonnet-\d)\b', '[REDACTED]'),
    # API 密钥
    (r'sk-[a-zA-Z0-9]{20,}', 'sk-[REDACTED]'),
    # 内部链接
    (r'go/[a-zA-Z0-9]+', '[INTERNAL_LINK]'),
    # Slack 频道
    (r'#[a-z0-9-]+-internal', '#[REDACTED]'),
    # 内部项目名
    (r'claude-cli-internal', '[REDACTED]'),
]

def check_message(message: str) -> list[SensitivityHit]:
    """发送前检查消息是否包含敏感信息"""
    hits = []
    for pattern, replacement in SENSITIVE_PATTERNS:
        matches = re.findall(pattern, message, re.IGNORECASE)
        if matches:
            hits.append(SensitivityHit(pattern=pattern, matches=matches))
    return hits

def sanitize(message: str) -> str:
    """自动替换敏感信息"""
    for pattern, replacement in SENSITIVE_PATTERNS:
        message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
    return message
```

#### 里程碑

- [ ] Day 1 上午: detector.py（检测规则）
- [ ] Day 1 下午: sanitizer.py（自动替换）+ 消息发送前集成

---

## 六、Phase 5: Fork 模式增强（已有基础）

> 预计：1 天 | 难度：低 | 价值：中

### 现状

OpenClaw 的 `sessions_spawn` 已支持 `thread: true`，但没有 Claude Code 那种"继承上下文 + 共享缓存"的语义。

### 增强目标

在 `eve_evolution/openclaw_bridge.py` 的桥接层增加 Fork 语义：

```python
class EnhancedSpawn:
    async def fork(self, task: str, inherit_last_n: int = 20) -> dict:
        """Fork 当前上下文给子代理
        
        - 继承最近 N 条对话消息
        - 共享 workspace 目录
        - 子代理结果通过 scratchpad 回传
        """
        inherited = self.context.messages[-inherit_last_n:]
        
        # 写入继承上下文到 scratchpad
        scratchpad = os.path.join(self.context.workspace, ".scratchpad")
        os.makedirs(scratchpad, exist_ok=True)
        with open(os.path.join(scratchpad, "context.md"), "w") as f:
            for msg in inherited:
                f.write(f"## {msg.role}\n{msg.content}\n\n")
        
        # Spawn with inherited context hint
        return await self.spawn(task, metadata={"fork": True})
```

---

## 七、Phase 6: UI/UX 增强

> 预计：按需 | 难度：中 | 价值：中

### 不做完整 UI 框架（OpenClaw 有 webchat）

只做轻量增强：

1. **消息类型图标** — 不同类型消息用不同 emoji 前缀
2. **上下文使用量提示** — 接近上下文上限时提醒
3. **Spinner 增强** — TTS 播报时显示"正在思考..."动画
4. **主题色彩** — OpenClaw webchat 的 CSS 变量主题

---

## 八、优先级矩阵

| Phase | 功能 | 价值 | 难度 | 工时 | 优先级 |
|-------|------|------|------|------|--------|
| 1 | Buddy 电子伴侣 | ⭐⭐⭐⭐⭐ | ⭐ | 2-3天 | 🥇 最先做 |
| 2 | BriefTool 主动消息 | ⭐⭐⭐⭐ | ⭐⭐ | 3-4天 | 🥈 其次 |
| 3 | Coordinator 多智能体 | ⭐⭐⭐⭐ | ⭐⭐ | 2-3天 | 🥉 然后 |
| 4 | Undercover 安全 | ⭐⭐⭐ | ⭐ | 1天 | 🥉 然后 |
| 5 | Fork 增强 | ⭐⭐⭐ | ⭐ | 1天 | 4️⃣ 可后做 |
| 6 | UI/UX 增强 | ⭐⭐ | ⭐⭐ | 按需 | 4️⃣ 最后 |

---

## 九、技术决策记录

### 9.1 Python vs TypeScript

Eve 的工具和技能用 Python，因为：
- OpenClaw 的 Agent 运行时支持 Python
- Python 在 AI/数据处理生态更好
- 与 OpenClaw Node.js 主进程通过子进程通信

UI 层不做 TypeScript 迁移，OpenClaw 的 webchat 已够用。

### 9.2 为什么不做完整 TUI

- OpenClaw 的 webchat 是默认界面
- TUI (Rich/Textual) 增加依赖复杂度
- TTS 是 Eve 的"UI"——语音就是表情
- 如果将来需要，design-system 的主题 token 可以迁移到 CSS

### 9.3 Buddy 为什么用 emoji 而不是 ASCII

- Claude Code 的 ASCII sprite 在终端里
- Eve 的主要界面是 webchat + QQ Bot（支持 emoji）
- emoji 比 ASCII art 跨平台一致性更好
- 终端用户可以用 Unicode fallback

### 9.4 为什么 Undercover 单独做而不是集成到消息发送

- 保持单一职责
- 可以选择性关闭
- 检测规则可能需要独立维护和更新

---

## 十、与 Claude Code 的架构差异总结

| 维度 | Claude Code | Eve |
|------|-------------|-----|
| 运行时 | Bun (TypeScript) | Python + Node.js (OpenClaw) |
| UI | React/Ink 终端 | OpenClaw webchat + TTS |
| 工具系统 | buildTool 工厂 | EveTool 基类 |
| 技能发现 | 编译期 Feature Gate | 运行时关键词匹配 |
| 多智能体 | Coordinator/Worker 模式 | sessions_spawn + subagents |
| 记忆 | CLAUDE.md 文件系统 | MEMORY.md + memory/*.md |
| 压缩 | LLM 摘要 + snip | 待实现 LLM compact |
| 安全 | Undercover 默认开启 | 尚未实现 |
| 宠物 | Buddy (编译期) | Phase 1 实现 |
| 消息 | BriefTool (Kairos) | Phase 2 实现 |

---

## 十一、总结

### 3 个最大亮点

1. **Buddy 系统是差异化杀手锏** — Claude Code 的电子宠物已经让用户着迷，Eve 加上 emoji + 确定性生成 + 性格 LLM 生成，体验会更好。而且 Eve 有 TTS，宠物的"声音"是语音，比 ASCII sprite 强太多。

2. **BriefTool + Coordinator 组合是效率倍增器** — 主动消息从"你问我答"变成"我主动帮你"，多智能体从"一个干活"变成"一个指挥多个干活"。这两个组合起来，Eve 就从工具变成真正的 AI 助理。

3. **已有框架打底** — eve_evolution 的 8 个模块已经跑通，Phase 1-4 是在此基础上加功能，不是从零开始。

### 2 个风险点

1. **Subagent 任务太大导致失败** — 今晚多次 spawn coder agent 处理大任务都返回空结果（可能是 token 限制或超时）。Phase 3 的 Coordinator 需要先解决这个问题——拆分更小的任务 + 设置合理的 timeout。

2. **记忆更新是手动的** — 当前日记更新需要 sed 编辑，不够自动化。进化过程中需要优先给 evolution_agent 加上自动记忆维护能力（让 Agent 自己写日记，不需要 Eve 手动操作）。

---

> 🐾 Eve
> 2026-04-03 00:08 CST
