# Jarvis Voice Server

**Apple Watch ↔ AI Agent 语音通道服务端**

为随身设备（Apple Watch + AirPods）提供语音交互能力：录音 → 文字 → AI 回复 → 语音播报。

## 架构

```
Watch/AirPods ──HTTP POST──▶ FastAPI Server ──▶ ASR ──▶ Agent ──▶ TTS
                              (port 8900)                        │
                           ◀── MP3 audio ────────────────────────┘
```

## 功能

| 端点 | 方法 | 功能 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/transcribe` | POST | 音频 → 文字（ASR） |
| `/voice` | POST | 完整管线：音频 → 文字 → Agent → 语音 |
| `/tts` | POST | 文字 → 语音 MP3 |
| `/audio/{id}` | GET | 获取 TTS 音频 |

## 快速开始

```bash
# 安装依赖
pip install fastapi uvicorn edge-tts httpx python-multipart

# 启动（本地 ASR）
ASR_BACKEND=local JARVIS_PORT=8900 python server.py

# 启动（OpenAI API ASR，需 API Key）
ASR_BACKEND=openai OPENAI_API_KEY=sk-xxx python server.py
```

## 测试

```bash
# 健康检查
curl http://127.0.0.1:8900/health

# 语音识别
curl -X POST http://127.0.0.1:8900/transcribe \
  -H "Authorization: Bearer jarvis-dev-token" \
  -F "file=@audio.wav"

# 完整管线
curl -X POST http://127.0.0.1:8900/voice \
  -H "Authorization: Bearer jarvis-dev-token" \
  -F "file=@audio.wav"

# TTS
curl -X POST "http://127.0.0.1:8900/tts?text=你好" \
  -H "Authorization: Bearer jarvis-dev-token" \
  -o output.mp3
```

## ASR 后端

| 后端 | 延迟 | 质量 | 内存 | 适用场景 |
|------|------|------|------|----------|
| `local` (whisper tiny) | ~5s/CPU | 中 | 子进程隔离 | 低内存服务器验证 |
| `openai` (Whisper API) | ~2s | 高 | 无本地占用 | 生产环境 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ASR_BACKEND` | `openai` | ASR 后端：local / openai |
| `TTS_VOICE` | `zh-CN-YunxiNeural` | TTS 语音（edge-tts） |
| `JARVIS_AUTH_TOKEN` | `jarvis-dev-token` | API 认证 Token |
| `JARVIS_PORT` | `8900` | 监听端口 |
| `OPENAI_API_KEY` | — | OpenAI API Key（openai 后端必填） |

## Apple Watch 集成

详见 [Apple Watch Jarvis 可行性调研](docs/apple-watch-jarvis-feasibility.md)

## License

MIT
