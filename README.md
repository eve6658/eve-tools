# Eve Tools 🐾

AI 交易助手的工具集和知识库。

## 项目

### 📡 通达信 L2 数据捕获
Frida 动态注入 hook，实时捕获通达信客户端网络数据流。
- 协议逆向：FD magic + zlib + JSON(GBK)
- 自动捕获脚本（按天分文件）
- [详见](l2-hook/)

### 🎙 Jarvis Voice Server
Apple Watch 语音指令服务器，支持 Siri 快捷指令 + WebSocket 实时通信。
- 语音 → 文字 → AI 处理 → 语音回复
- [详见](jarvis-server/)

### 🧠 Eve Knowledge
交易知识库：均线理论、趋势判断、小单占比、操盘分析框架。
- [概念卡片](eve_knowledge/concept_cards/)
- [分析框架](eve_knowledge/frameworks/)
- [实战案例](eve_knowledge/wiki/)

## 工具

| 工具 | 用途 |
|------|------|
| `tdx_capture.py` | 通达信 L2 自动捕获 |
| `hook_recv_v2.py` | Frida recv hook |
| `ocr_orderbook.py` | 盘口截图 OCR |
| `nodriver_finance.py` | 反检测爬虫（东财/巨潮） |
| `trading-coach` | 交易复盘教练 |

## 环境

- **主机**: Linux (Ubuntu 6.17)
- **采集机**: Windows 10 (192.168.1.32, 用户 John)
- **AI**: OpenClaw + MiMo-v2.5
