#!/usr/bin/env python3
"""语音/视频转文字工具 - faster-whisper (CPU版)"""
import sys
import os
import argparse

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from faster_whisper import WhisperModel

def transcribe(file_path, model_size="base", language=None):
    print(f"📂 文件: {file_path}")
    print(f"🧠 模型: {model_size}")
    
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    kwargs = {}
    if language:
        kwargs["language"] = language
    
    segments, info = model.transcribe(file_path, **kwargs)
    
    print(f"🌐 检测语言: {info.language} (置信度: {info.language_probability:.1%})")
    print(f"⏱️  时长: {info.duration:.1f}秒")
    print("-" * 50)
    
    full_text = []
    for seg in segments:
        line = f"[{seg.start:.1f}s -> {seg.end:.1f}s] {seg.text}"
        print(line)
        full_text.append(seg.text)
    
    print("-" * 50)
    text = " ".join(full_text)
    
    # 保存到文件
    out_path = file_path.rsplit(".", 1)[0] + ".txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"💾 文字已保存: {out_path}")
    
    return text

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="语音/视频转文字")
    parser.add_argument("file", help="音频或视频文件路径")
    parser.add_argument("-m", "--model", default="base", help="模型: tiny/base/small (默认: base)")
    parser.add_argument("-l", "--language", default=None, help="指定语言 (如: zh, en)")
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"❌ 文件不存在: {args.file}")
        sys.exit(1)
    
    transcribe(args.file, args.model, args.language)
