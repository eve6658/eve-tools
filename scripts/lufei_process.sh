#!/bin/bash
# 路飞视频夜间批量处理脚本（含文案提取）
# 用法: ./lufei_process.sh [url_file]

set -euo pipefail

PYTHON="/home/adam/open_claw_env/bin/python3"
FFMPEG="/home/adam/.local/bin/ffmpeg"
WHISPER="/home/adam/open_claw_env/bin/python3 /home/adam/.openclaw/workspace/scripts/whisper_transcribe.py"
OUTPUT_DIR="/home/adam/Downloads/ytdl/lufei"
TRANSCRIPT_DIR="/home/adam/.openclaw/workspace/memory/lufei_transcripts"
URL_FILE="${1:-/home/adam/.openclaw/workspace/scripts/lufei_urls.txt}"

mkdir -p "$OUTPUT_DIR" "$TRANSCRIPT_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

if [[ ! -f "$URL_FILE" ]]; then
    echo -e "${RED}❌ 链接文件不存在: $URL_FILE${NC}"
    exit 1
fi

# 统计未处理链接
total=$(grep -v '^#' "$URL_FILE" | grep -v '^$' | grep -v '^# DONE' | wc -l)
echo -e "${GREEN}📦 路飞视频处理: $total 个新链接${NC}"

# Step 1: 下载+提取文案
echo -e "${GREEN}=== Step 1: 下载视频+文案 ===${NC}"
i=0
while IFS= read -r url; do
    [[ -z "$url" || "$url" == \#* || "$url" == *"# DONE"* ]] && continue
    # 检查是否已处理过
    grep -qF "$url" "$URL_FILE" 2>/dev/null && grep -q "# DONE:$url" "$URL_FILE" 2>/dev/null && continue
    i=$((i + 1))
    echo -e "${YELLOW}[$i/$total] $url${NC}"
    
    $PYTHON << PYEOF
import requests, re, json, subprocess, os, sys

url = """$url"""
output_dir = "$OUTPUT_DIR"

try:
    resp = requests.get(url, headers={
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X)',
    }, allow_redirects=True, timeout=15)
    match = re.search(r'/video/(\d+)', resp.url)
    if not match:
        print("  ❌ 无法获取视频ID"); sys.exit(0)
    vid = match.group(1)
    
    router_match = re.search(r'window\\._ROUTER_DATA\\s*=\\s*({.*?});?\\s*</script>', resp.text, re.DOTALL)
    if not router_match:
        print("  ❌ 未找到ROUTER_DATA"); sys.exit(0)
    
    data = json.loads(router_match.group(1))
    video_url = None
    title = None
    desc = None
    
    def find_all(obj, depth=0):
        nonlocal video_url, title, desc
        if depth > 12: return
        if isinstance(obj, dict):
            # 取最长的desc作为文案
            if 'desc' in obj:
                d = obj['desc']
                if isinstance(d, str) and 10 < len(d) < 2000:
                    if desc is None or len(d) > len(desc):
                        desc = d
                if isinstance(d, str) and 5 < len(d) < 200 and title is None:
                    title = d
            for key in ['play_addr', 'play_url']:
                if key in obj and video_url is None:
                    val = obj[key]
                    if isinstance(val, dict):
                        urls = val.get('url_list', [])
                        if urls: video_url = urls[0]
            for v in obj.values(): find_all(v, depth+1)
        elif isinstance(obj, list):
            for item in obj: find_all(item, depth+1)
    
    find_all(data)
    
    if not video_url:
        print("  ❌ 未找到视频URL"); sys.exit(0)
    
    import re as re2
    if title:
        title = re2.sub(r'[\\\\/:*?"<>|]', '', title)[:80]
    else:
        title = f"lufei_{vid}"
    
    # 保存文案
    if desc:
        desc_file = f"{output_dir}/{title}_文案.txt"
        with open(desc_file, 'w', encoding='utf-8') as f:
            f.write(f"标题: {title}\n链接: {url}\n视频ID: {vid}\n\n{desc}")
        print(f"  📝 文案: {len(desc)}字")
    
    # 下载视频
    output = f"{output_dir}/{title}.mp4"
    no_wm = video_url.replace('/playwm/', '/play/')
    subprocess.run(['curl', '-sL', '-o', output, '-H', 'User-Agent: com.ss.android.ugc.aweme/230901', no_wm], timeout=120)
    
    if os.path.exists(output) and os.path.getsize(output) > 10000:
        print(f"  ✅ 视频: {os.path.getsize(output)/1024/1024:.1f}MB")
    else:
        if os.path.exists(output): os.remove(output)
        subprocess.run(['curl', '-sL', '-o', output, '-H', 'User-Agent: com.ss.android.ugc.aweme/230901', video_url], timeout=120)
        if os.path.exists(output):
            print(f"  ✅ 视频(水印): {os.path.getsize(output)/1024/1024:.1f}MB")
        else:
            print("  ❌ 下载失败")
except Exception as e:
    print(f"  ❌ {e}")
PYEOF
    # 标记为已处理
    echo "# DONE:$url" >> "$URL_FILE"
    sleep 2
done < "$URL_FILE"

# Step 2: 转录
echo ""
echo -e "${GREEN}=== Step 2: Whisper转录 ===${NC}"
j=0
for video in "$OUTPUT_DIR"/*.mp4; do
    [[ ! -f "$video" ]] && continue
    j=$((j + 1))
    bn=$(basename "$video" .mp4)
    tfile="$TRANSCRIPT_DIR/${bn}.txt"
    [[ -f "$tfile" ]] && echo -e "${YELLOW}[$j] 跳过: $bn${NC}" && continue
    
    echo -e "${YELLOW}[$j] 转录: $bn${NC}"
    tmp="/tmp/lufei_$$.mp3"
    $FFMPEG -i "$video" -vn -acodec libmp3lame -q:a 2 "$tmp" -y 2>/dev/null
    $WHISPER "$tmp" --language zh --model tiny 2>&1 | tail -1
    [[ -f "/tmp/$(basename "$tmp" .mp3).txt" ]] && mv "/tmp/$(basename "$tmp" .mp3).txt" "$tfile"
    rm -f "$tmp"
done

echo ""
echo -e "${GREEN}✅ 完成！${NC}"
echo -e "视频+文案: $OUTPUT_DIR"
echo -e "转录: $TRANSCRIPT_DIR"
echo -e "${YELLOW}下一步: 将转录文件用 ytdl analyze 分段后逐段分析${NC}"
