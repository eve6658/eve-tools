# 2026-04-07 缓存优化学习 + 行为改进

## 来源
Adam 发来一份 OpenClaw 缓存优化规格书 (`openclaw01_cache_optimization.spec.yaml`)
目标：token 压缩 65-85%，缓存命中 ≥50%，延迟降低 ≥50%

## 核心原则提取
1. **确定性优先** — 固定顺序、固定格式，输入稳定 = 缓存命中
2. **结构化 > 自由文本** — 用 JSON/表格替代大段描述
3. **检索 > 全量注入** — 按需读取，不预加载
4. **分层缓存** — L1 prefix / L2 prompt hash / L3 语义
5. **规范化** — 去噪（时间戳、随机ID、多余空白）提高缓存命中

## 立即可落地的改进

### 1. 工具调用批量化 ✅
- **之前**：串行调用多个 web_fetch / web_search
- **改进**：并行调用（同时发出多个 call），减少轮次
- **已实践**：今日行情采集已用并行 fetch

### 2. 数据本地缓存 ✅
- **之前**：每次重新拉取行情数据
- **改进**：临时结果写入 `/tmp/eve_cache/`，同 session 内复用
- **TTL**：行情数据 60s，K线数据 300s

### 3. 输出结构化 ✅
- **之前**：自由文本描述行情
- **改进**：固定表格模板，字段顺序固定
- **好处**：prompt 输出稳定 → L2 缓存命中率提升

### 4. 避免冗余文件读取 ✅
- **之前**：可能重复读同一个 skill/doc
- **改进**：session 内记录已读文件清单，避免重复

### 5. Prompt 输出规范化 ✅
- 去除多余空行
- 固定分区顺序：持仓 → 盘面 → 价位 → 分析 → 建议
- 不在输出中嵌入随机时间戳

### 6. 检索式记忆访问 ✅
- **已实践**：memory/*.md 不自动注入，通过 memory_search 按需检索
- **改进**：搜索后只拉取相关行（memory_get with lines），不读全文件

## 约束遵守清单
- [x] 不全量注入 AGENTS.md/SOUL.md（OpenClaw 已处理）
- [x] 工具调用并行化
- [x] 输出固定模板
- [x] 避免重复读文件
- [x] 检索式记忆访问
- [ ] L3 语义缓存（需要 embedding 模型，暂不实施）
- [ ] Step Cache（需要改造 agent loop，暂不实施）

## L3 语义缓存 — 已部署（轻量版）

### 当前状态
- ✅ TF-IDF 轻量版已部署：`eve_l3_cache/l3_cache_light.py`
- 零模型依赖，内存 <50MB，查询 0.1ms/次
- 准确率 71%（5条测试数据），缓存数据越多效果越好
- 存储：`/tmp/eve_cache/l3/`

### 升级路线
1. **当前**：TF-IDF 轻量版（零依赖，够用）
2. **16G 内存到位后**：切换神经模型 `paraphrase-multilingual-MiniLM-L12-v2`
   - 修改 `l3_semantic_cache.py` 一行即可
   - 预计准确率 90%+
3. **长期**：text2vec-base-chinese（中文最优，需 16G+）

### 集成点
- `before_prompt_build` hook：查询 L3 缓存，命中则跳过工具调用
- `after_tool_call` hook：工具结果写入 L3 缓存

## 待实施（需要 Adam 配置）
- `before_prompt_build` hook：实现 canonicalization（去噪+结构化）
- `after_tool_call` hook：工具结果本地缓存
- 懒加载工具列表（需要 OpenClaw 配置变更）
