# Eve 迁移方案 → OpenClaw 3.8 新机器

## 迁移清单

| 类别 | 内容 | 大小 | 优先级 |
|------|------|------|--------|
| 🧠 灵魂 | SOUL.md, IDENTITY.md, USER.md, AGENTS.md | ~10KB | P0 |
| 📝 记忆 | MEMORY.md + memory/ (20个文件) | ~180KB | P0 |
| 🔧 技能 | skills/ (45个技能目录) | ~50MB | P0 |
| 🧬 Eve Evolution | eve_evolution/ (22个子目录, 2773行) | ~200KB | P0 |
| ⏰ 定时任务 | 3个 cron jobs (600666盯盘) | - | P0 |
| ⚙️ 配置 | openclaw.json (需适配) | 8KB | P0 |
| 📚 扩展 | extensions/ (weixin, wecom) | ~250MB | P1 |
| 📄 其他文档 | 手册、报告、分析 .md/.py | ~60MB | P2 |
| 🔊 脚本 | mimo-tts-proxy.mjs, 其他脚本 | ~50KB | P1 |

---

## 迁移步骤

### 第一步：打包核心文件（源机器）

```bash
# 创建迁移包
mkdir -p /tmp/eve-migration

# 1. 灵魂文件
cp ~/.openclaw/workspace/{SOUL.md,IDENTITY.md,USER.md,AGENTS.md,TOOLS.md,HEARTBEAT.md,BOOTSTRAP.md} /tmp/eve-migration/

# 2. 记忆
cp ~/.openclaw/workspace/MEMORY.md /tmp/eve-migration/
cp -r ~/.openclaw/workspace/memory/ /tmp/eve-migration/memory/

# 3. 技能（排除 node_modules 和 __pycache__）
rsync -av --exclude='node_modules' --exclude='__pycache__' --exclude='.git' \
  ~/.openclaw/workspace/skills/ /tmp/eve-migration/skills/

# 4. Eve Evolution
cp -r ~/.openclaw/workspace/eve_evolution/ /tmp/eve-migration/eve_evolution/

# 5. 脚本
cp -r ~/.openclaw/workspace/scripts/ /tmp/eve-migration/scripts/

# 6. 配置（仅模型和通道配置，不含 token 等敏感信息）
cp ~/.openclaw/openclaw.json /tmp/eve-migration/openclaw.json.example

# 7. 定时任务导出
openclaw cron list > /tmp/eve-migration/cron-jobs.txt

# 8. 其他重要文档
cp ~/.openclaw/workspace/stock-battle-manual.md /tmp/eve-migration/
cp ~/.openclaw/workspace/手册_第十八章_量化时代盘口新法则.md /tmp/eve-migration/

# 打包
tar -czf ~/eve-migration-$(date +%Y%m%d).tar.gz -C /tmp/eve-migration .
ls -lh ~/eve-migration-*.tar.gz
```

### 第二步：传输到新机器

```bash
# 方式1: scp（如果两台机器互通）
scp ~/eve-migration-*.tar.gz user@新机器IP:/tmp/

# 方式2: 用 U 盘/网盘中转
# 方式3: 通过 OpenClaw 自身发送（小文件）
```

### 第三步：新机器部署（OpenClaw 3.8）

```bash
# 1. 安装 OpenClaw 3.8
curl -fsSL https://openclaw.ai/install.sh | bash

# 2. 初始化
openclaw onboard

# 3. 解压迁移包
mkdir -p ~/.openclaw/workspace
tar -xzf ~/eve-migration-*.tar.gz -C /tmp/eve-migration/

# 4. 恢复灵魂文件
cp /tmp/eve-migration/{SOUL.md,IDENTITY.md,USER.md,AGENTS.md,TOOLS.md,HEARTBEAT.md} ~/.openclaw/workspace/

# 5. 恢复记忆
cp /tmp/eve-migration/MEMORY.md ~/.openclaw/workspace/
cp -r /tmp/eve-migration/memory/ ~/.openclaw/workspace/

# 6. 恢复技能
cp -r /tmp/eve-migration/skills/ ~/.openclaw/workspace/skills/

# 7. 恢复 Eve Evolution
cp -r /tmp/eve-migration/eve_evolution/ ~/.openclaw/workspace/

# 8. 恢复脚本
cp -r /tmp/eve-migration/scripts/ ~/.openclaw/workspace/

# 9. 恢复文档
cp /tmp/eve-migration/stock-battle-manual.md ~/.openclaw/workspace/
cp /tmp/eve-migration/手册_第十八章_量化时代盘口新法则.md ~/.openclaw/workspace/
```

### 第四步：配置适配（关键！）

新机器需要重新配置，不能直接复制 openclaw.json：

```bash
# 1. 运行配置向导
openclaw onboard

# 2. 手动编辑配置，添加 Token Plan
vim ~/.openclaw/openclaw.json
```

需要手动配置的内容：
- [ ] `models.providers.xiaomi` — baseUrl + apiKey (Token Plan)
- [ ] `channels.qqbot` — appId + clientSecret
- [ ] `channels.wecom` — botId + secret
- [ ] `skills.entries.tavily-search.apiKey`
- [ ] `gateway.auth.token` — 自动生成
- [ ] `plugins.entries` — 按需启用

### 第五步：恢复定时任务

```bash
# 在新机器上重新创建 cron jobs
openclaw cron add --name "600666集合竞价盯盘" \
  --schedule "25 9 * * 1-5" \
  --timezone "Asia/Shanghai" \
  --target isolated \
  --message "分析600666奥瑞德集合竞价情况，关注开盘价、成交量、买卖盘挂单"

openclaw cron add --name "600666开盘半小时分析" \
  --schedule "0 10 * * 1-5" \
  --timezone "Asia/Shanghai" \
  --target isolated \
  --message "分析600666奥瑞德开盘半小时走势，量价配合，主力动向"

openclaw cron add --name "600666尾盘分析" \
  --schedule "30 14 * * 1-5" \
  --timezone "Asia/Shanghai" \
  --target isolated \
  --message "分析600666奥瑞德尾盘走势，判断主力意图，给出次日操作建议"
```

### 第六步：验证

```bash
# 1. 检查配置
openclaw doctor

# 2. 启动 gateway
openclaw gateway start

# 3. 测试对话
openclaw tui

# 4. 检查技能加载
# 在对话中发送: 列出你的技能

# 5. 检查记忆
# 在对话中发送: 你是谁

# 6. 检查定时任务
openclaw cron list
```

---

## 注意事项

1. **配置不能直接复制** — 新机器的 IP、端口、token 都不同，必须重新配置
2. **API Key 需要重新设置** — Token Plan 的 key 可以复用，但要手动填入
3. **Extensions 可能需要重装** — wecom-openclaw-plugin 和 openclaw-weixin 需要 `openclaw plugins add` 重装
4. **Eve Evolution 的 Python 依赖** — 新机器需要 `pip3 install` 相关依赖
5. **TTS proxy** — mimo-tts-proxy.mjs 需要重新启动，且需要 MIMO_API_KEY
6. **BOOTSTRAP.md** — 部署后删除，避免重复初始化

---

## 回滚方案

如果新机器出问题：
```bash
# 回退到旧机器，只需确保旧机器的 ~/.openclaw/ 未被修改
openclaw gateway restart
```
