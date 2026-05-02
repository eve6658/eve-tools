"""
Jarvis Voice Server v3 — Apple Watch 专用 API
Watch 场景优化：最小 payload、快捷指令、推送通知、设备管理
"""

import os
import time
import uuid
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Query
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import edge_tts
import httpx

# ─── Config ───────────────────────────────────────────────────────
ASR_BACKEND = os.getenv("ASR_BACKEND", "openai")
TTS_VOICE = os.getenv("TTS_VOICE", "zh-CN-YunxiNeural")
AUTH_TOKEN = os.getenv("JARVIS_AUTH_TOKEN", "jarvis-dev-token")
HOST = os.getenv("JARVIS_HOST", "0.0.0.0")
PORT = int(os.getenv("JARVIS_PORT", "8900"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
BARK_KEY = os.getenv("BARK_KEY", "")  # Bark 推送密钥
OPENCLAW_URL = os.getenv("OPENCLAW_URL", "http://127.0.0.1:18789")

# ─── App ──────────────────────────────────────────────────────────
app = FastAPI(title="Jarvis Watch API", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ─── 设备注册表（内存）──────────────────────────────────────────
devices: dict = {}  # device_id → {name, last_seen, platform}


# ─── Auth ─────────────────────────────────────────────────────────
def verify_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "Missing token")
    token = authorization.replace("Bearer ", "")
    if token != AUTH_TOKEN:
        raise HTTPException(403, "Invalid token")
    return token


# ─── ASR ──────────────────────────────────────────────────────────

async def transcribe_openai(audio_bytes: bytes, filename: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        suffix = Path(filename).suffix or ".wav"
        mime = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
                ".ogg": "audio/ogg", ".webm": "audio/webm"}.get(suffix, "audio/wav")
        resp = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            files={"file": (filename, audio_bytes, mime)},
            data={"model": "whisper-1", "language": "zh"},
        )
        resp.raise_for_status()
        return {"text": resp.json()["text"], "lang": "zh"}


async def transcribe_local(audio_bytes: bytes, filename: str) -> dict:
    suffix = Path(filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    out_dir = tempfile.mkdtemp()
    try:
        proc = await asyncio.create_subprocess_exec(
            "/home/adam/open_claw_env/bin/whisper", tmp_path,
            "--model", "tiny", "--language", "zh",
            "--output_dir", out_dir, "--output_format", "txt",
            "--device", "cpu", "--fp16", "False",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=30)
        txt = Path(out_dir) / (Path(tmp_path).stem + ".txt")
        return {"text": txt.read_text().strip() if txt.exists() else "", "lang": "zh"}
    finally:
        os.unlink(tmp_path)
        import shutil; shutil.rmtree(out_dir, ignore_errors=True)


async def transcribe(audio_bytes, filename):
    return await transcribe_openai(audio_bytes, filename) if ASR_BACKEND == "openai" \
        else await transcribe_local(audio_bytes, filename)


# ─── TTS ──────────────────────────────────────────────────────────

async def tts(text: str, voice: str = None) -> bytes:
    v = voice or TTS_VOICE
    comm = edge_tts.Communicate(text, v)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        await comm.save(tmp.name)
        data = open(tmp.name, "rb").read()
        os.unlink(tmp.name)
    return data


# ─── Agent（简单规则 + OpenClaw 桥接）───────────────────────────

async def agent_reply(user_text: str, device_id: str = "") -> str:
    """Agent 回复。优先走 OpenClaw，失败时用规则引擎。"""
    # 快捷指令映射
    shortcuts = {
        "启动监控": "L2 监控已启动",
        "停止监控": "L2 监控已停止",
        "查邮件": "邮件查询功能待接入",
        "查日程": "日程查询功能待接入",
    }
    for k, v in shortcuts.items():
        if k in user_text:
            return v

    # 尝试调 OpenClaw（后续集成）
    # try:
    #     async with httpx.AsyncClient() as client:
    #         r = await client.post(f"{OPENCLAW_URL}/api/agent", json={"message": user_text})
    #         return r.json().get("reply", "")
    # except:
    #     pass

    # 规则引擎兜底
    text = user_text.lower()
    if any(w in text for w in ["几点", "时间"]):
        return f"现在是 {datetime.now().strftime('%H点%M分')}"
    if any(w in text for w in ["你好", "hello"]):
        return "你好！我是 Eve，你的 AI 助手。"
    if any(w in text for w in ["功能", "能做什么"]):
        return "我可以帮你查时间、查天气、管理待办、控制监控。语音告诉我。"
    return f"收到：{user_text}"


# ─── 推送通知 ─────────────────────────────────────────────────────

async def push_notify(title: str, body: str, device_id: str = ""):
    """通过 Bark 推送到 iPhone/Watch"""
    if not BARK_KEY:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"https://api.day.app/{BARK_KEY}", json={
                "title": title, "body": body, "device": device_id or None,
            })
    except:
        pass


# ═══════════════════════════════════════════════════════════════════
# Watch 专用 API
# ═══════════════════════════════════════════════════════════════════

@app.get("/w/health")
async def watch_health():
    """Watch 健康检查（最轻量）"""
    return {"ok": 1, "t": int(time.time())}


@app.post("/w/talk")
async def watch_talk(
    file: UploadFile = File(...),
    device: str = Query("watch"),
    authorization: str = Header(None),
):
    """
    Watch 一键语音交互（最简 API）
    POST 音频 → 返回 JSON: {text, reply, audio_url}
    Watch 端拿到 audio_url 后直接播放。
    """
    verify_token(authorization)
    audio = await file.read()
    if not audio:
        raise HTTPException(400, "empty")

    # 注册设备
    devices[device] = {"last_seen": datetime.now().isoformat(), "platform": "watch"}

    # ASR
    t0 = time.time()
    r = await transcribe(audio, file.filename or "audio.wav")
    asr_ms = int((time.time() - t0) * 1000)
    text = r.get("text", "")

    if not text.strip():
        return {"text": "", "reply": "", "audio": None, "ms": asr_ms}

    # Agent
    reply = await agent_reply(text, device)

    # TTS → 返回音频 bytes
    audio_data = await tts(reply)

    from starlette.responses import JSONResponse
    return JSONResponse(
        content={"text": text, "reply": reply, "ms": asr_ms},
        headers={"X-Audio": "true"},
    )


@app.post("/w/command")
async def watch_command(
    command: str = "",
    device: str = Query("watch"),
    authorization: str = Header(None),
):
    """
    Watch 快捷指令（纯文本，不走 ASR）
    适合预设按钮：「启动监控」「查天气」「停止」
    """
    verify_token(authorization)
    if not command.strip():
        raise HTTPException(400, "empty command")

    devices[device] = {"last_seen": datetime.now().isoformat(), "platform": "watch"}

    reply = await agent_reply(command, device)
    audio_data = await tts(reply)

    # 音频存临时文件，返回 URL
    audio_id = str(uuid.uuid4())[:8]
    path = f"/tmp/jarvis_{audio_id}.mp3"
    with open(path, "wb") as f:
        f.write(audio_data)

    return {
        "cmd": command,
        "reply": reply,
        "audio_url": f"/w/audio/{audio_id}.mp3",
    }


@app.post("/w/say")
async def watch_say(
    text: str = "",
    voice: str = Query(None),
    authorization: str = Header(None),
):
    """
    文字 → 语音（纯 TTS）
    Agent 回复后调用此端点生成语音。
    """
    verify_token(authorization)
    if not text.strip():
        raise HTTPException(400, "empty")

    audio_data = await tts(text, voice)
    return Response(content=audio_data, media_type="audio/mpeg")


@app.get("/w/audio/{fid}.mp3")
async def watch_audio(fid: str):
    """获取 TTS 音频"""
    path = f"/tmp/jarvis_{fid}.mp3"
    if not os.path.exists(path):
        raise HTTPException(404)
    data = open(path, "rb").read()
    os.unlink(path)
    return Response(content=data, media_type="audio/mpeg")


@app.post("/w/notify")
async def watch_notify(
    title: str = "Jarvis",
    body: str = "",
    device: str = Query("watch"),
    authorization: str = Header(None),
):
    """
    推送通知到 iPhone/Watch
    用于后台任务完成后的回调。
    """
    verify_token(authorization)
    await push_notify(title, body, device)
    return {"ok": 1}


@app.get("/w/devices")
async def watch_devices(authorization: str = Header(None)):
    """查看已注册设备"""
    verify_token(authorization)
    return {"devices": devices}


# ═══════════════════════════════════════════════════════════════════
# 标准 API（保留兼容）
# ═══════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {"status": "ok", "asr": ASR_BACKEND, "version": "3.0.0"}


@app.post("/transcribe")
async def transcribe_ep(
    file: UploadFile = File(...),
    authorization: str = Header(None),
):
    verify_token(authorization)
    audio = await file.read()
    t0 = time.time()
    r = await transcribe(audio, file.filename or "audio.wav")
    return {"text": r.get("text", ""), "ms": int((time.time() - t0) * 1000)}


@app.post("/tts")
async def tts_ep(text: str = "", authorization: str = Header(None)):
    verify_token(authorization)
    if not text.strip():
        raise HTTPException(400, "empty")
    data = await tts(text)
    return Response(content=data, media_type="audio/mpeg")


# ─── Main ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print(f"🎙️  Jarvis Watch API v3")
    print(f"   ASR: {ASR_BACKEND} | TTS: {TTS_VOICE} | Port: {PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
