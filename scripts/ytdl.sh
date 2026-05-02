#!/bin/bash
# YouTube/视频下载 CLI — 独立调用，不消耗AI token
# 用法: ytdl <命令> <参数>
#
# 命令:
#   ytdl video <url>              下载视频（默认720p）
#   ytdl video <url> 1080p        下载视频指定画质
#   ytdl audio <url>              仅下载音频（mp3）
#   ytdl info <url>               查看视频信息（不下载）
#   ytdl list <url>               列出所有可用画质
#   ytdl subtitle <url>           下载字幕
#   ytdl batch <file.txt>         批量下载（每行一个url）
#
# 示例:
#   ytdl video "https://www.youtube.com/watch?v=xxx"
#   ytdl audio "https://www.youtube.com/watch?v=xxx"
#   ytdl info "https://youtu.be/xxx"
#   ytdl list "https://www.youtube.com/watch?v=xxx"

set -euo pipefail

YTDLP="/home/adam/open_claw_env/bin/yt-dlp"
PROXY="http://127.0.0.1:7897"
OUTPUT_DIR="/home/adam/Downloads/ytdl"
WHISPER="/home/adam/open_claw_env/bin/python3 /home/adam/.openclaw/workspace/scripts/whisper_transcribe.py"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "$OUTPUT_DIR"

usage() {
    echo -e "${GREEN}YouTube/视频下载 CLI${NC}"
    echo ""
    echo "用法: ytdl <命令> <参数>"
    echo ""
    echo "命令:"
    echo "  ytdl video <url> [画质]     下载视频（默认best，可选1080p/720p/480p）"
    echo "  ytdl audio <url>            仅下载音频（mp3格式）"
    echo "  ytdl info <url>             查看视频信息"
    echo "  ytdl list <url>             列出所有可用画质"
    echo "  ytdl subtitle <url>         下载字幕（如有）"
    echo "  ytdl transcribe <url>       下载音频+Whisper转录"
echo "  ytdl analyze <file>         将转录文件分段（每段约3000字符）"
echo "  ytdl video <douyin_url>      抖音视频自动解析（无需额外参数）"
    echo "  ytdl batch <file.txt>       批量下载（每行一个url）"
    echo ""
    echo "画质选项: best, 1080p, 720p, 480p, audio"
    echo "输出目录: $OUTPUT_DIR"
    echo ""
    echo "示例:"
    echo "  ytdl video 'https://www.youtube.com/watch?v=xxx'"
    echo "  ytdl video 'https://www.youtube.com/watch?v=xxx' 1080p"
    echo "  ytdl audio 'https://www.youtube.com/watch?v=xxx'"
    echo "  ytdl transcribe 'https://www.youtube.com/watch?v=xxx'"
}

cmd_video() {
    local url="$1"
    local quality="${2:-best}"
    
    # 抖音特殊处理
    if [[ "$url" == *douyin.com* || "$url" == *v.douyin.com* ]]; then
        echo -e "${GREEN}🎵 抖音视频，使用专用解析...${NC}"
        cmd_douyin "$url"
        return
    fi
    
    echo -e "${GREEN}📥 正在下载视频...${NC}"
    echo -e "URL: $url"
    echo -e "画质: $quality"
    echo ""
    
    local -a format_args=()
    # 抖音无多画质，直接best
    case "$quality" in
        1080p|1080)  format_args=(-f "bestvideo[height<=1080]+bestaudio/best[height<=1080]") ;;
        720p|720)    format_args=(-f "bestvideo[height<=720]+bestaudio/best[height<=720]") ;;
        480p|480)    format_args=(-f "bestvideo[height<=480]+bestaudio/best[height<=480]") ;;
        audio)       format_args=(--extract-audio --audio-format mp3) ;;
        best)        format_args=() ;;
        *)           format_args=(-f "$quality") ;;
    esac
    # 抖音/TikTok：用cookies绕过登录墙（如有）
    if [[ "$url" == *douyin.com* || "$url" == *tiktok.com* ]]; then
        local cookies_file="/home/adam/.config/yt-dlp/cookies.txt"
        if [[ -f "$cookies_file" ]]; then
            format_args+=(--cookies "$cookies_file")
        fi
    fi
    
    "$YTDLP" --proxy "$PROXY" \
        -o "$OUTPUT_DIR/%(title).80s.%(ext)s" \
        --merge-output-format mp4 \
        --no-playlist \
        "${format_args[@]}" \
        "$url" 2>&1
    
    echo ""
    echo -e "${GREEN}✅ 下载完成！文件在: $OUTPUT_DIR${NC}"
}

cmd_audio() {
    local url="$1"
    
    echo -e "${GREEN}🎵 正在下载音频...${NC}"
    echo -e "URL: $url"
    echo ""
    
    $YTDLP --proxy "$PROXY" \
        -o "$OUTPUT_DIR/%(title)s.%(ext)s" \
        --extract-audio \
        --audio-format mp3 \
        --audio-quality 0 \
        --no-playlist \
        "$url" 2>&1
    
    echo ""
    echo -e "${GREEN}✅ 音频下载完成！文件在: $OUTPUT_DIR${NC}"
}

cmd_info() {
    local url="$1"
    
    echo -e "${GREEN}ℹ️  视频信息:${NC}"
    echo ""
    
    $YTDLP --proxy "$PROXY" \
        --no-download \
        --print "%(title)s" \
        --print "%(duration_string)s" \
        --print "%(view_count)s views" \
        --print "%(uploader)s" \
        --print "%(upload_date)s" \
        --print "%(webpage_url)s" \
        "$url" 2>/dev/null
    
    echo ""
}

cmd_list() {
    local url="$1"
    
    echo -e "${GREEN}📋 可用画质:${NC}"
    echo ""
    
    $YTDLP --proxy "$PROXY" \
        -F \
        "$url" 2>&1 | grep -E "^(ID|---|[0-9])" | head -30
    
    echo ""
}

cmd_subtitle() {
    local url="$1"
    
    echo -e "${GREEN}📝 正在下载字幕...${NC}"
    
    $YTDLP --proxy "$PROXY" \
        -o "$OUTPUT_DIR/%(title)s.%(ext)s" \
        --write-sub \
        --write-auto-sub \
        --sub-lang "zh-Hans,zh,en" \
        --sub-format srt \
        --skip-download \
        --no-playlist \
        "$url" 2>&1
    
    echo ""
    echo -e "${GREEN}✅ 字幕下载完成！文件在: $OUTPUT_DIR${NC}"
}

cmd_transcribe() {
    local url="$1"
    local skip_analysis="${2:-}"
    
    echo -e "${GREEN}🎙️  下载音频 + Whisper转录...${NC}"
    echo -e "URL: $url"
    echo ""
    
    # 先下载音频
    local tmp_audio="/tmp/ytdl_audio_$$.mp3"
    $YTDLP --proxy "$PROXY" \
        -o "$tmp_audio" \
        --extract-audio \
        --audio-format mp3 \
        --audio-quality 0 \
        --no-playlist \
        "$url" 2>&1 || \
    # 抖音音频用已下载的视频提取
    if [[ -f "$OUTPUT_DIR"/*.mp4 ]]; then
        local video_file=$(ls -t "$OUTPUT_DIR"/*.mp4 2>/dev/null | head -1)
        if [[ -n "$video_file" ]]; then
            /home/adam/.local/bin/ffmpeg -i "$video_file" -vn -acodec libmp3lame -q:a 2 "$tmp_audio" -y 2>&1
        fi
    fi
    
    echo ""
    echo -e "${GREEN}🔄 Whisper转录中...${NC}"
    
    # 转录
    $WHISPER "$tmp_audio" --language zh 2>&1
    
    # 清理临时文件
    rm -f "$tmp_audio"
    
    echo ""
    echo -e "${GREEN}✅ 转录完成！${NC}"
    echo -e "${YELLOW}提示: 使用 'ytdl analyze <转录文件>' 进行分段分析${NC}"
}

cmd_douyin() {
    local url="$1"
    
    # 用Python解析抖音视频
    /home/adam/open_claw_env/bin/python3 << PYEOF
import requests, re, json, subprocess, os, sys

url = "$url"
output_dir = "$OUTPUT_DIR"

# 1. 获取短链重定向 → 视频ID
try:
    resp = requests.get(url, headers={
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X)',
    }, allow_redirects=True, timeout=15)
    match = re.search(r'/video/(\d+)', resp.url)
    if not match:
        print("❌ 无法获取视频ID")
        sys.exit(1)
    vid = match.group(1)
    print(f"Video ID: {vid}")
except Exception as e:
    print(f"❌ 获取视频ID失败: {e}")
    sys.exit(1)

# 2. 从页面_ROUTER_DATA提取视频URL
try:
    body = resp.text
    router_match = re.search(r'window\._ROUTER_DATA\s*=\s*({.*?});?\s*</script>', body, re.DOTALL)
    if not router_match:
        print("❌ 未找到_ROUTER_DATA")
        sys.exit(1)
    
    data = json.loads(router_match.group(1))
    
    # 递归查找视频URL和标题
    video_url = None
    title = None
    def find_video(obj, depth=0):
        nonlocal video_url, title
        if depth > 12 or video_url:
            return
        if isinstance(obj, dict):
            if 'desc' in obj and 5 < len(str(obj.get('desc',''))) < 200:
                title = obj['desc']
            for key in ['play_addr', 'play_url']:
                if key in obj:
                    val = obj[key]
                    if isinstance(val, dict):
                        url_list = val.get('url_list', [])
                        if url_list:
                            video_url = url_list[0]
                    elif isinstance(val, str) and val.startswith('http'):
                        video_url = val
            for v in obj.values():
                find_video(v, depth+1)
        elif isinstance(obj, list):
            for item in obj:
                find_video(item, depth+1)
    
    find_video(data)
    
    if not video_url:
        print("❌ 未找到视频URL")
        sys.exit(1)
    
    # 清理标题
    if title:
        title = re.sub(r'[\\/:*?"<>|]', '', title)[:80]
    else:
        title = f"douyin_{vid}"
    
    output = f"{output_dir}/{title}.mp4"
    print(f"标题: {title}")
    print(f"📥 下载中...")
    
    # 下载（先试无水印）
    no_wm = video_url.replace('/playwm/', '/play/')
    result = subprocess.run(
        ['curl', '-sL', '-o', output, '-H', 'User-Agent: com.ss.android.ugc.aweme/230901', no_wm],
        capture_output=True, timeout=180
    )
    
    if os.path.exists(output) and os.path.getsize(output) > 10000:
        size = os.path.getsize(output)
        print(f"✅ 下载完成! {output} ({size/1024/1024:.1f}MB)")
    else:
        # 尝试带水印
        if os.path.exists(output):
            os.remove(output)
        subprocess.run(
            ['curl', '-sL', '-o', output, '-H', 'User-Agent: com.ss.android.ugc.aweme/230901', video_url],
            capture_output=True, timeout=180
        )
        if os.path.exists(output):
            size = os.path.getsize(output)
            print(f"✅ 下载完成(带水印)! {output} ({size/1024/1024:.1f}MB)")
        else:
            print("❌ 下载失败")
except Exception as e:
    print(f"❌ 解析失败: {e}")
    sys.exit(1)
PYEOF
}

cmd_analyze() {
    local file="$1"
    
    if [[ ! -f "$file" ]]; then
        echo -e "${RED}❌ 文件不存在: $file${NC}"
        exit 1
    fi
    
    local total_lines=$(wc -l < "$file")
    local total_chars=$(wc -c < "$file")
    echo -e "${GREEN}📄 分段分析: $file${NC}"
    echo -e "行数: $total_lines, 字数: $total_chars"
    echo ""
    
    # 按段落分段（空行分隔），每段不超过3000字符
    local segment_size=3000
    local segment_num=0
    local segment_file=""
    local char_count=0
    local segment_content=""
    
    while IFS= read -r line; do
        segment_content+="$line\n"
        char_count=$((char_count + ${#line} + 1))
        
        if [[ $char_count -ge $segment_size ]]; then
            segment_num=$((segment_num + 1))
            segment_file="/tmp/ytdl_segment_${segment_num}.txt"
            echo -n "$segment_content" > "$segment_file"
            echo -e "${YELLOW}段${segment_num}: $(wc -c < "$segment_file") 字符 → $segment_file${NC}"
            segment_content=""
            char_count=0
        fi
    done < "$file"
    
    # 剩余内容
    if [[ -n "$segment_content" ]]; then
        segment_num=$((segment_num + 1))
        segment_file="/tmp/ytdl_segment_${segment_num}.txt"
        echo -n "$segment_content" > "$segment_file"
        echo -e "${YELLOW}段${segment_num}: $(wc -c < "$segment_file") 字符 → $segment_file${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}共分成 $segment_num 段，每段可独立调用AI分析${NC}"
    echo -e "${YELLOW}建议: 每段单独丢给Eve分析，避免一次性超载${NC}"
}

cmd_batch() {
    local file="$1"
    
    if [[ ! -f "$file" ]]; then
        echo -e "${RED}❌ 文件不存在: $file${NC}"
        exit 1
    fi
    
    local count=$(wc -l < "$file")
    echo -e "${GREEN}📦 批量下载: $count 个视频${NC}"
    echo ""
    
    local i=0
    while IFS= read -r url; do
        [[ -z "$url" || "$url" == \#* ]] && continue
        i=$((i + 1))
        echo -e "${YELLOW}[$i/$count] $url${NC}"
        cmd_video "$url" "best"
        echo ""
    done < "$file"
    
    echo -e "${GREEN}✅ 批量下载完成！${NC}"
}

# 主入口
case "${1:-help}" in
    video)      shift; cmd_video "$@" ;;
    audio)      shift; cmd_audio "$@" ;;
    info)       shift; cmd_info "$@" ;;
    list)       shift; cmd_list "$@" ;;
    subtitle)   shift; cmd_subtitle "$@" ;;
    transcribe) shift; cmd_transcribe "$@" ;;
    batch)      shift; cmd_batch "$@" ;;
    help|--help|-h)  usage ;;
    *)          echo -e "${RED}未知命令: $1${NC}"; usage; exit 1 ;;
esac
