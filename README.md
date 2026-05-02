# eve-tools

Token-efficient CLI tools for building local AI knowledge bases.

Collect knowledge from video/audio sources without burning tokens on transcription when you don't have to.

## Tools

| Tool | What it does | Usage |
|------|-------------|-------|
| `kb-transcribe` | Universal transcriber (YouTube / Bilibili / Douyin). Subtitle-first strategy — grabs existing captions (near-zero cost) before falling back to Whisper. | `kb-transcribe <url>` |
| `douyin-transcribe` | Douyin specialist. Handles slideshows and image-heavy posts via OCR when there's no audio. | `douyin-transcribe <url>` |
| `ytdl` | Video downloader. Pull raw media for offline processing. | `ytdl video/audio/info <url>` |

## Why

Building a local knowledge base from video content is expensive if you transcribe everything. Most videos already have subtitles — `kb-transcribe` grabs those first, only invoking Whisper when needed.

**Before (token-heavy):**
```
AI downloads video → AI calls ffmpeg → AI calls Whisper → AI formats output
= 4-6 tool calls + massive output tokens
```

**After (token-efficient):**
```
AI runs one command → gets result
= 1 tool call
```

## Quick Start

```bash
# Single URL
kb-transcribe https://www.youtube.com/watch?v=...

# Batch mode — one URL per line, process overnight
cat urls.txt | kb-transcribe --batch

# Douyin (video or image posts)
douyin-transcribe https://v.douyin.com/...

# Just download
ytdl video "https://www.youtube.com/watch?v=..."
ytdl audio "https://www.youtube.com/watch?v=..."
ytdl info "https://youtu.be/..."
```

## Install

```bash
git clone https://github.com/eve6658/eve-tools.git
cd eve-tools
chmod +x *
export PATH="$PWD:$PATH"
```

## Dependencies

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — `pip install yt-dlp`
- ffmpeg
- [whisper](https://github.com/openai/whisper) — `pip install openai-whisper`
- tesseract (OCR, optional)
- Python 3

## Philosophy

Knowledge should be extracted, not generated. Subtitles are free. OCR is cheap. Whisper is a last resort. Save your tokens for thinking, not transcribing.

## License

MIT
