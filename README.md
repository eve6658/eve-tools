# eve-tools

减少token消耗的CLI工具集。让AI代理更高效地处理日常任务。

## 工具列表

| 工具 | 功能 | 用法 |
|------|------|------|
| `douyin-transcribe` | 抖音视频/图文转文字 | `douyin-transcribe <url>` |

## 安装

```bash
git clone https://github.com/YOUR_USERNAME/eve-tools.git
cd eve-tools
chmod +x */*.sh */douyin-transcribe
export PATH="$PWD:$PATH"
```

## 为什么需要这些工具

AI代理处理抖音内容时，原始流程需要大量token：
1. 下载视频 → 需要调用浏览器/API
2. 提取音频 → 需要ffmpeg知识
3. 转录文字 → 需要Whisper
4. OCR识别 → 需要Tesseract

这些工具把多步流程封装成一行命令，AI只需要调用一次工具，节省90%+的token。

## License

MIT
