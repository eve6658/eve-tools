#!/bin/bash
# 逐笔成交截图 → 一键分析流水线
# 用法: ./analyze_tick.sh <截图路径> [--minute|--day]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OCR="$SCRIPT_DIR/ocr_logic.py"
PARTICIPATION="$SCRIPT_DIR/retail_participation.py"
PYTHON="/home/adam/open_claw_env/bin/python3"

if [ -z "$1" ]; then
    echo "用法: $0 <截图路径> [--minute|--day]"
    exit 1
fi

IMAGE="$1"
MODE="${2:---minute}"
TMP_JSON="/tmp/tick_$(date +%s).json"

# Step 1: OCR识别
echo "🔍 Step 1: OCR识别中..." >&2
$PYTHON "$OCR" "$IMAGE" > "$TMP_JSON" 2>/tmp/ocr_stats.txt
cat /tmp/ocr_stats.txt >&2

# Step 2: 散户参与度分析
echo "" >&2
echo "📊 Step 2: 散户参与度分析..." >&2
$PYTHON "$PARTICIPATION" "$TMP_JSON" "$MODE"

# 清理
rm -f "$TMP_JSON"
