# eve-tools

减少token消耗的CLI工具集。让本地模型/Agent高效建立知识库。

## 工具列表

| 工具 | 功能 | 用法 |
|------|------|------|
| `kb-transcribe` | 通用视频转文字（YouTube/B站/抖音） | `kb-transcribe <url>` |
| `douyin-transcribe` | 抖音专用（视频+图文OCR） | `douyin-transcribe <url>` |
| `ytdl` | 视频下载（YouTube/B站/抖音） | `ytdl video/audio/info <url>` |

## 核心思路

**原始流程**（消耗大量token）：
```
AI下载视频 → AI调ffmpeg → AI调Whisper → AI整理格式
= 4-6次工具调用 + 大量输出token
```

**封装后**（节省90%+ token）：
```
AI调用一行命令 → 得到结果
= 1次工具调用
```

## 知识库构建流程

```bash
# 1. 批量转录（夜间跑，不急）
kb-transcribe https://www.youtube.com/watch?v=xxx --model large
kb-transcribe https://www.bilibili.com/video/BVxxx
kb-transcribe https://v.douyin.com/xxx

# 2. 整理成知识库
cat ~/Downloads/ytdl/knowledge/*/transcript.txt > knowledge-base.txt

# 3. 喂给本地模型
ollama run miMo-7b < knowledge-base.txt
```

## 安装

```bash
git clone https://github.com/YOUR_USERNAME/eve-tools.git
cd eve-tools
chmod +x *
export PATH="$PWD:$PATH"
```

## 依赖

- yt-dlp (`pip install yt-dlp`)
- ffmpeg
- whisper (`pip install openai-whisper`)
- tesseract (OCR, optional)
- Python 3

## License

MIT
