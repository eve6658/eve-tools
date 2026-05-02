# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## Tushare Pro

- **Token**: `e0dc18fc3ef8b9aa6a77b3e02a98f909097a237d7aa3cf82bfe1ad19`
- **环境变量**: `TUSHARE_TOKEN`（已写入 ~/.bashrc）
- **配置时间**: 2026-03-28

### 接口权限（已验证）

| 接口 | 状态 | 说明 |
|------|------|------|
| daily | ✅ | 日线行情，无限制 |
| weekly | ✅ | 周线行情 |
| monthly | ✅ | 月线行情 |
| top10_holders | ✅ | 前十大股东 |
| major_news | ✅ | 重大新闻（800+条） |
| stock_basic | ⚠️ | 可用但限频极严（1次/小时） |
| fina_indicator | ❌ | 需升级积分 |
| income | ❌ | 需升级积分 |
| express | ❌ | 需升级积分 |
| forecast | ❌ | 需升级积分 |
| moneyflow | ❌ | 需升级积分 |
| daily_basic | ❌ | 需升级积分（PE/PB等） |
| anns_d | ❌ | 需升级积分 |
| stk_holdernumber | ❌ | 需升级积分 |

**建议**: 如需财务数据和资金流接口，需升级Tushare积分（当前为基础档）。

## QQ Bot 配置

- **AppID**: `1903737083`
- **AppSecret**: `MdiaGiwxkJemfKly`
- **状态**: 已提交，待配置（需在服务器终端运行）
- **配置命令**: `openclaw channels add --channel qqbot --token "1903737083:MdiaGiwxkJemfKly" && openclaw gateway restart`

## Local OCR（盘口截图识别）

- **路径**: `~/.openclaw/workspace/skills/local-ocr/ocr_logic.py`
- **用途**: L2千档盘口截图 → 逐笔成交数据（时间/价格/手数/方向）
- **双引擎**: Tesseract（快，3-5秒）| EasyOCR（准，60-120秒，加 `--accuracy`）
- **命令**: `/home/adam/open_claw_env/bin/python3 ~/.openclaw/workspace/skills/local-ocr/ocr_logic.py <图片路径> [--accuracy]`
- **⚠️ 规则**: 盘口截图必须用此本地OCR，严禁调用视觉模型(image工具)！
- **输出**: JSON格式逐笔数据 + stderr统计

## sandbox 模式

⚠️ 当前 sandbox.mode 可能为 `tool-policy`，导致每次 exec 都需要审批。
建议设置为 `off` 以获得流畅体验（已记录在 TOOLS.md，提醒用户配置）。

## Lightpanda 浏览器

- **路径**: `/home/adam/.local/bin/lightpanda`（已加入 PATH）
- **安装时间**: 2026-04-12
- **项目**: https://github.com/lightpanda-io/browser
- **用途**: 无头浏览器，抓网页数据优先用这个（比 web_fetch 更强，支持 JS 渲染）
- **用法**:
  - `lightpanda fetch --dump markdown <url>` → 抓网页转 markdown
  - `lightpanda fetch --dump html <url>` → 抓网页转 html
  - `lightpanda serve --host 127.0.0.1 --port 9222` → CDP 服务（Puppeteer 可连）
  - `lightpanda mcp` → MCP Server
- **优先级**: 抓取网页数据时优先使用 Lightpanda，其次 web_fetch

## Scrapling

- **版本**: v0.4.6
- **环境**: open_claw_env (`/home/adam/open_claw_env/bin/python3`)
- **安装时间**: 2026-04-14
- **用途**: 自适应网页爬取，绕过反爬（Cloudflare等）
- **依赖**: playwright (Chromium已安装), curl_cffi, browserforge

### 用法
```python
from scrapling import Fetcher
fetcher = Fetcher()
page = fetcher.get('https://example.com')
page.status          # 状态码
page.body            # bytes原始内容
page.css('div.cls')  # 返回Selector列表（⚠️ 没有css_first，用css()[0]）
page.xpath('//div')
page.re_first(r'pattern')
```

### 优先级（默认用这个）
- **网上抓信息 → Scrapling（首选）**
- 轻量快速抓取 → Lightpanda
- 简单页面 → web_fetch

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## GitHub (Eve)

- **账号**: eve6658
- **仓库**: https://github.com/eve6658/eve-tools
- **SSH Key**: `~/.ssh/id_ed25519_16082177`（⚠️ 不是默认的 id_ed25519）
- **推送命令**: `GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519_16082177" git push origin master`
- **配置时间**: 2026-05-03

## VPN/Clash 控制

- **软件**: Clash Verge (verge-mihomo)
- **端口**: 7897
- **Socket**: /tmp/verge/verge-mihomo.sock
- **控制方式**:
  - `vpn_on` — 开启代理（bash函数，已加入bashrc）
  - `vpn_off` — 关闭代理
  - `vpn_status` — 查看状态
  - 或用脚本: `~/.openclaw/workspace/scripts/vpn-control.sh [on|off|status]`
- **⚠️ 规则**: 网络不稳定/下载失败时，先 `vpn_on` 再重试，**用完立即 `vpn_off`**（省流量+安全）

### Chrome 代理配置（重要！）

**Chrome 不认 `http_proxy` 环境变量**，必须显式传 `--proxy-server` 参数：

```bash
# OpenClaw 浏览器带代理启动
/usr/bin/google-chrome-stable \
  --remote-debugging-port=18800 \
  --user-data-dir=/home/adam/.openclaw/browser/openclaw/user-data \
  --proxy-server="http://127.0.0.1:7897" \
  --no-first-run --no-default-browser-check --disable-sync \
  --disable-background-networking --disable-component-update \
  --disable-features=Translate,MediaRouter \
  --password-store=basic --disable-dev-shm-usage &
```

**流程**：vpn_on → 重启 Chrome（带 --proxy-server）→ 正常上网
