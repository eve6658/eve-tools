#!/usr/bin/env python3
"""
Jarvis Voice Server 测试脚本
用法:
  python3 test_server.py                    # 基础健康检查
  python3 test_server.py <audio_file>       # 测试 ASR
  python3 test_server.py <audio_file> --voice  # 测试完整管线
"""

import sys
import json
import base64
import requests

SERVER = "http://127.0.0.1:8900"
TOKEN = "jarvis-dev-token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def test_health():
    r = requests.get(f"{SERVER}/health")
    print(f"✅ Health: {r.json()}")
    return r.ok


def test_transcribe(audio_path):
    print(f"\n🎤 Transcribing: {audio_path}")
    with open(audio_path, "rb") as f:
        files = {"file": (audio_path, f, "audio/wav")}
        r = requests.post(f"{SERVER}/transcribe", files=files, headers=HEADERS)
    result = r.json()
    print(f"   文字: {result.get('text', '')}")
    print(f"   语言: {result.get('language', '')}")
    print(f"   耗时: {result.get('duration_ms', 0)}ms")
    return result


def test_voice(audio_path):
    print(f"\n🔊 Voice pipeline: {audio_path}")
    with open(audio_path, "rb") as f:
        files = {"file": (audio_path, f, "audio/wav")}
        r = requests.post(f"{SERVER}/voice", files=files, headers=HEADERS)
    result = r.json()
    print(f"   用户: {result.get('text', '')}")
    print(f"   回复: {result.get('reply', '')}")
    print(f"   ASR:  {result.get('asr_ms', 0)}ms")
    print(f"   TTS:  {result.get('tts_ms', 0)}ms")
    if result.get("audio_url"):
        print(f"   音频: {SERVER}{result['audio_url']}")
    return result


def test_tts(text):
    print(f"\n🗣️  TTS: {text}")
    r = requests.post(f"{SERVER}/tts", params={"text": text}, headers=HEADERS)
    out = f"/tmp/tts_test_{hash(text) % 10000}.mp3"
    with open(out, "wb") as f:
        f.write(r.content)
    print(f"   保存: {out} ({len(r.content)} bytes)")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # 基础测试
        test_health()
        test_tts("你好，我是 Eve，你的贾维斯助手。")
        print("\n💡 用法: python3 test_server.py <audio_file> 测试语音识别")
    elif sys.argv[1] == "--tts":
        text = sys.argv[2] if len(sys.argv) > 2 else "你好，我是 Eve"
        test_tts(text)
    elif "--voice" in sys.argv:
        test_health()
        test_voice(sys.argv[1])
    else:
        test_health()
        test_transcribe(sys.argv[1])
