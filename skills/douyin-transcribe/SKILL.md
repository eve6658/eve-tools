# douyin-transcribe

抖音视频/图文一键转文字。自动判断类型，视频用Whisper转录，图文用Tesseract OCR。

## 触发词

"转录抖音"、"抖音转文字"、"下载抖音视频"、"douyin transcribe"

## 用法

```bash
douyin-transcribe <抖音URL> [--model base|small|medium|large] [--output-dir <dir>]
```

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--model` | medium | Whisper模型：base/small/medium/large |
| `--output-dir` | ~/Downloads/ytdl/transcribes | 输出目录 |

## 流程

1. 解析抖音短链 → 获取note_id
2. 判断类型（视频/图文）
3. 视频：下载 → ffmpeg提取音频 → Whisper转录
4. 图文：下载全部图片 → Tesseract OCR
5. 输出txt到 `~/Downloads/ytdl/transcribes/<note_id>_<标题>/`

## 模型选择

| 模型 | 大小 | 速度 | 中文质量 | 推荐场景 |
|------|------|------|----------|----------|
| base | ~1GB | 快 | 偶尔错字 | 快速预览 |
| small | ~2GB | 中 | 较准 | 日常使用 |
| medium | ~4GB | 慢 | 准确 | **推荐** |
| large | ~8GB | 很慢 | 最准 | 不急/夜间跑 |

## 依赖

- curl, ffmpeg, tesseract (chi_sim), whisper
- Python 3 + requests（解析短链）

## 示例

```bash
# 默认medium模型
douyin-transcribe https://v.douyin.com/xxx

# 用large模型（夜间跑）
douyin-transcribe https://v.douyin.com/xxx --model large

# 指定输出目录
douyin-transcribe https://v.douyin.com/xxx --output-dir /tmp/transcribes
```

## 输出结构

```
~/Downloads/ytdl/transcribes/
└── 7614701525944444155_第一章/
    ├── video.mp4          # 视频（视频类型）
    ├── audio.wav          # 音频
    ├── 全文转录.txt        # Whisper转录结果（视频类型）
    ├── page_1.webp        # 图片（图文类型）
    ├── page_2.webp
    └── 全文OCR.txt         # OCR结果（图文类型）
```

## 注意事项

- 抖音需要特殊User-Agent，脚本已内置
- Whisper首次运行会下载模型，需联网
- Tesseract中文识别率一般，建议优先用Whisper（视频有音频的情况）
- 长视频（>30分钟）建议用small或medium，large太慢
