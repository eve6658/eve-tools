#!/bin/bash
# Jarvis Voice Server 启动脚本
# 用法: ./start.sh [port]

PORT=${1:-8900}
MODEL=${WHISPER_MODEL:-base}

export WHISPER_MODEL=$MODEL
export WHISPER_DEVICE=cpu
export WHISPER_COMPUTE=int8
export JARVIS_AUTH_TOKEN=jarvis-dev-token
export JARVIS_PORT=$PORT

cd "$(dirname "$0")"

echo "🎙️  Jarvis Voice Server"
echo "   Model: $MODEL | Device: cpu | Port: $PORT"
echo "   Auth: $JARVIS_AUTH_TOKEN"
echo ""

/home/adam/open_claw_env/bin/python3 server.py
