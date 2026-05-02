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

## sandbox 模式

⚠️ 当前 sandbox.mode 可能为 `tool-policy`，导致每次 exec 都需要审批。
建议设置为 `off` 以获得流畅体验（已记录在 TOOLS.md，提醒用户配置）。

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
