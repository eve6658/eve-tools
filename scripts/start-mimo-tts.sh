#!/bin/bash
# Start MiMo TTS proxy as a background service
export MIMO_API_KEY="sk-cc8aar6i0b94n219jpf7qfevr2qi711xo3a0n01sflg9z5jz"

# Kill existing instance
pkill -f "mimo-tts-proxy.mjs" 2>/dev/null
sleep 1

# Start proxy
exec node /home/adam/.openclaw/workspace/scripts/mimo-tts-proxy.mjs
