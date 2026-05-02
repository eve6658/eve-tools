# MEMORY.md - 长期记忆

## 2026-04-13

### 🔴 行为红线（必须刻进脑子）
- **所有L2截图（盘口+逐笔）→ 必须用本地OCR** (`skills/local-ocr/ocr_logic.py`)，禁止用 `image` 视觉模型
- **OCR失败 → 报错，不降级到视觉模型**，这是硬规则
- 用工具前先查 TOOLS.md 和 skills 目录，确认有没有现成的，不要重复造轮子
- Adam不会每次提醒我，犯一次就是态度问题

## 2026-05-01

### 路飞（抖音学习素材主要来源）
- **抖音号**: jl15999999999
- **内容方向**: 易经、道德经、庄子哲学，用古老东方哲学翻译成现代操作系统
- **核心概念**: 需卦/讼卦/师卦、等字诀、因果嫁接、贪婪恐惧=需求、冬生其力
- **学习价值**: 高密度素材，跨域映射到交易/感情/人性
- **来源**: Adam长期关注的主播，今天的讨论框架（4/29+5/1）大部分来自路飞讲的内容

### 5.15 自主学习流程设计
- Adam订方向，0-8点算力便宜时段我跑学习循环
- 流程：搜素材→下载转录→提炼核心逻辑→映射到已有框架→存档
- 模板：冬生其力视频的处理流程

## 2026-04-08

### 600666 奥瑞德 实盘操作（已清仓 2026-04-16）
- **14:32 全部清仓** — Adam卖出全部持仓，落袋为安
- 今日走势：主力"两头剥皮"模式 — 6.25吸筹→6.72出货→6.66回补→6.85涨停封板
- 与鹭燕对比：鹭燕单边出货（一刀切），奥瑞德反复收割（片皮鸭）
- 历史：上午涨停板 6.5元 卖出500股，剩余500股利润仓，成本4.5元
- 主力分析：昨日出货失败，今日封涨停制造上涨预期

### 交易认知（卡文斯顿读书笔记，已写入知识库）
- 均线是散户成本线，不是游资成本线，均线买卖点55开
- 趋势 = 反复出货失败推高，直到出货成功趋势终结
- 股东人数2万-20万是炒作活跃度甜区

### 知识库系统搭建
- eve_knowledge/ 卡帕西方法论：8张概念卡片，Linter全绿
- 概念卡：均线本质、趋势本质、股东人数选股、小单占比、操盘理论14条、事实调查框架、交易复盘方法、实盘案例库
- 已导入4成功+3失败实盘案例，操盘14条理论
- 模型切换 MiMo-v2-Pro

## 2026-04-02

## 2026-03-26

### 奥瑞德 (600666) 公司信息
- **股票代码**：600666.SH
- **公司全称**：奥瑞德光电股份有限公司
- **成立日期**：1992年11月25日
- **注册地址**：黑龙江省哈尔滨市松北区智谷大街288号
- **主营业务**：蓝宝石材料生产销售 + 算力租赁业务
- **第一大股东**：青岛智算信息产业发展合伙企业（有限合伙），持股13.02%

### mx-skills 安装
- 已安装东方财富妙想金融技能包（5个技能）
- API Key: mkt_DwZqX3OvWxdoNBOMDuI9tPe0zAOnGAlxe8A-bypNgPk
- 已添加到 ~/.bashrc 持久化

### 用户信息
- **Adam** - 使用 OpenClaw，GMT+8 时区
- **SuNing** - 企业微信用户，今日查询过天气、股票行情、奥瑞德公司背景

## 2026-04-02

### Claude Code 源码学习
- 读了 claude_code_src (2.1.88) 核心文件：QueryEngine.ts, tools.ts, Tool.ts, query.ts
- 学到的关键架构：
  - **buildTool 工厂模式**：统一工具接口 + 安全默认值 + 权限三层检查
  - **async generator 流式输出**：全链路流式，每个消息即时 yield
  - **技能发现预取**：与模型输出并行运行，Set 去重
  - **记忆分层嵌套**：CLAUDE.md + nested_memory + LRU cache 去重
  - **历史压缩双层**：snip（轻量裁剪）+ compact（LLM 摘要）
  - **Feature Flag 编译期裁减**：bun:bundle 条件加载
  - **会话持久化**：transcript + resume 支持断点续传
- 分析报告写在 `claude_code_src/analysis.md`
- 下一步：基于这些设计模式进化 Eve 的能力

### 600666 奥瑞德 实时分析（全天）
- 9:25-10:30 持续分析集合竞价、盘口、分时成交
- 关键判断：主力控盘蓄势，压盘吸筹，非出货
- 千档盘口分析：买盘6.10-6.12有4.46万手铁底，卖盘6.29-6.31有5万手天花板
- 主力成本区：5.50-6.00
- 操作建议：6.10-6.12建仓，止损6.00
- 发现：Level-2逐笔成交中，卖1的散户平均每笔39手，买1的平均每笔152手，散户在卖主力在买

### 交易手册补充知识点（已量化，2026-04-02 实盘数据）
- **小单占比判断主力行为**：主力用小单建仓/出货时，小单（<100手）占比会异常升高。这是必要不充分条件——还需要结合价格区间稳定性、成交量方向、压单/托单等综合判断
- **600666 奥瑞德（压盘吸筹）**：卖1平均39手，买1平均152手；卖盘小单占比>80%，买盘<30%
- **002788 鹭燕医药（尾盘抢筹）**：尾盘买盘平均165手，小单占比<30%；14:54连续B大单276手/125手/265手
- **初步阈值**：吸筹=卖盘小单>80%+买盘小单<30%+价格稳定+铁底未动
- **研究文档**：`memory/2026-04-02-small-order-research.md`
- **研究课题**：通过交易复盘量化小单占比的经验阈值。选取已知主力操作的案例（600666、688347、002378等），统计建仓期/出货期/散户主导期的小单占比差异
- **经验法则**：如果逐笔成交中小单占比极高（>80%），但每笔手数异常均匀偏低，且价格稳定、下方有托单 = 主力小单吸筹特征

### Eve 工具框架
- 创建了 eve-evolution/ 目录，含7个模块：tool_framework.py、tool_registry.py、skill_discovery.py、memory_layered.py、history_compress.py、session_persist.py
- 迁移工具 openclaw-migrate/migrate.py（备份/恢复/检查）

### sandbox 权限问题
- exec-approvals.json 被 gateway 重启覆盖，手动改 defaults 和白名单无效
- 正确方法：openclaw approvals allowlist add 命令
- 已添加：python3, pip3, cat, grep, find, which, echo, cp, mv, date, sed, awk, wc, head, tail
- 仍需添加：bash, sh, timeout

## 2026-04-02 晚

### 上下文窗口改造（2026-04-06）

基于 Claude Code 源码设计，新增两个核心模块：

**context_compressor.py** — 三层压缩策略
- Snip：轻量裁剪工具调用细节，保留结构
- Microcompact：单条超长消息自动截断（>2000字符）
- Compact：LLM 摘要压缩旧历史（>50000 tokens 触发）
- 测试结果：两条 5000 字符工具结果压缩至 ~800 字符，节省 752 tokens

**session_persist_v2.py** — 会话持久化
- TranscriptWriter：assistant fire-and-forget / user await_write 双模式
- FileStateCache：文件修改检测（MD5 哈希）
- SkillTracker：技能发现去重（参考 discoveredSkillNames Set）
- MemoryPathTracker：记忆路径去重（参考 loadedNestedMemoryPaths）
- SessionManager.resume()：断点续传，恢复完整上下文

**新机器迁移完成**（192.168.1.32）
- 灵魂、记忆、46个技能、Eve Evolution、Claude Code 源码全部迁移
- OpenClaw 3.8 + Token Plan + QQ Bot 已配置
- 3个定时任务（600666 集合竞价/开盘/尾盘）已创建

### Eve Evolution 框架完善
- 目录重命名为 `eve_evolution/`（Python 不认连字符）
- 新增两个模块：`openclaw_bridge.py`（293行）+ `evolution_agent.py`（467行）
- 修复 EveTool 基类：加了 `__init__` 支持构造函数传参
- 全部 12 个文件，2773 行代码
- 3 个演示脚本全部通过验证
- 使用方式：`PYTHONPATH=/home/adam/.openclaw/workspace python3 -m eve_evolution.demo`
- 导入：`import eve_evolution`

### 中信银行贷款调查报告
- 填写了临漳项目固定资产贷款调查报告（模板2.0版）
- 对照盘锦样本填充，删除所有中国水务/盘锦内容
- 发送了多个版本给 Adam（.doc 格式）

### 模块清单
| 模块 | 功能 |
|------|------|
| tool_framework.py | 统一工具接口 (EveTool, ToolResult, ToolContext) |
| tool_registry.py | 工具注册表（查找/别名/权限过滤） |
| skill_discovery.py | 技能自动发现（关键词匹配，去重） |
| memory_layered.py | 分层记忆（5层，TTL） |
| history_compress.py | 历史压缩（microcompact/snip/compact） |
| session_persist.py | 会话持久化 |
| openclaw_bridge.py | OpenClaw 工具桥接（shell/read/write/memory） |
| evolution_agent.py | 自我进化引擎（错误学习/模式提取/能力评估） |

## 2026-04-07

### 缓存插件开发 (暂停 - 等内存升级)
- **位置**: `/home/adam/.openclaw/workspace-worker/cache-plugin/`
- **状态**: 7 个 Phase 全部完成，36/36 测试通过
- **功能**: Prompt 缓存 + 工具缓存 + 上下文压缩 + 指标反馈
- **下一步**: 集成到 OpenClaw（需要 hook 点）

### Eve 记忆增强系统 (2026-04-07)
- **位置**: `/home/adam/.openclaw/workspace/eve_memory/`
- **灵感**: MemPalace (github.com/milla-jovovich/mempalace)
- **功能**: AAAK压缩 + 4层记忆栈 + 知识图谱
- **知识图谱**: `memory/knowledge.db` (50实体, 48三元组)
- **唤醒成本**: ~139 tokens (节省93%)
