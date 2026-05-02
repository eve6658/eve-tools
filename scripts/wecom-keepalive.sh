#!/bin/bash
# 企业微信通道保活 + 自动恢复脚本
# 每5分钟检查一次通道状态，假死时自动重启 gateway

LOGFILE="/home/adam/.openclaw/logs/wecom-keepalive.log"
MAX_FAILS=3
STAMP_FILE="/tmp/wecom-keepalive-fails"
GATEWAY_PORT=18789

mkdir -p /home/adam/.openclaw/logs

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOGFILE"
}

# 获取当前失败计数
get_fails() {
    if [ -f "$STAMP_FILE" ]; then
        cat "$STAMP_FILE"
    else
        echo 0
    fi
}

set_fails() {
    echo "$1" > "$STAMP_FILE"
}

# 检查 gateway 是否在运行
check_gateway() {
    if systemctl is-active --quiet openclaw-gateway 2>/dev/null; then
        return 0
    fi
    # fallback: 直接检查进程
    if pgrep -f "openclaw-gateway" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

# 检查 gateway HTTP 是否可达
check_http() {
    # 直接检查根端口是否可达
    if curl -sf --max-time 5 "http://127.0.0.1:${GATEWAY_PORT}/" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

# 检查 openclaw 状态
check_wecom_channel() {
    local output
    output=$(timeout 10 openclaw status 2>&1)
    # 检查企业微信通道是否 OK
    if echo "$output" | grep -q "企业微信.*OK"; then
        return 0
    fi
    # 检查是否有报错
    if echo "$output" | grep -qi "企业微信.*error\|企业微信.*fail\|企业微信.*off"; then
        return 1
    fi
    return 0
}

# ===== 主逻辑 =====
log "━━━ 保活检查开始 ━━━"

# 1. 检查 gateway 进程
if ! check_gateway; then
    FAILS=$(get_fails)
    FAILS=$((FAILS + 1))
    set_fails "$FAILS"
    log "⚠️  gateway 进程不存在，累计失败 $FAILS 次"
    
    if [ "$FAILS" -ge "$MAX_FAILS" ]; then
        log "🚨 连续 $MAX_FAILS 次检测到异常，执行重启..."
        openclaw gateway restart >> "$LOGFILE" 2>&1
        sleep 3
        if check_gateway; then
            log "✅ gateway 重启成功"
            set_fails 0
        else
            log "❌ gateway 重启失败！"
        fi
    fi
    exit 0
fi

# 2. 检查 HTTP 可达性
if ! check_http; then
    FAILS=$(get_fails)
    FAILS=$((FAILS + 1))
    set_fails "$FAILS"
    log "⚠️  gateway HTTP 不可达，累计失败 $FAILS 次"
    
    if [ "$FAILS" -ge "$MAX_FAILS" ]; then
        log "🚨 连续 $MAX_FAILS 次 HTTP 异常，执行重启..."
        openclaw gateway restart >> "$LOGFILE" 2>&1
        sleep 3
        if check_http; then
            log "✅ gateway 重启成功，HTTP 恢复"
            set_fails 0
        else
            log "❌ gateway 重启后 HTTP 仍不可达！"
        fi
    fi
    exit 0
fi

# 3. 一切正常，重置计数器
set_fails 0
log "✅ 通道正常 (gateway 运行中, HTTP 可达)"

# 4. 空闲超时检测：超过30分钟无消息交互时重启（7:00-23:00内）
STAMP_FILE_MSG="/tmp/wecom-last-msg-time"
HOUR=$(date +%H)
if [ "$HOUR" -ge 7 ] && [ "$HOUR" -lt 23 ]; then
    date +%s > "$STAMP_FILE_MSG"
    if [ -f "$STAMP_FILE_MSG" ]; then
        LAST_MSG=$(cat "$STAMP_FILE_MSG")
        NOW=$(date +%s)
        DIFF=$((NOW - LAST_MSG))
        if [ "$DIFF" -gt 1800 ]; then
            log "⚠️  超过30分钟无消息交互(H:$(date +%H:%M))，执行防假死重启..."
            openclaw gateway restart >> "$LOGFILE" 2>&1
            sleep 3
            if check_gateway && check_http; then
                log "✅ 重启成功，通道恢复"
            else
                log "❌ 重启失败"
            fi
            date +%s > "$STAMP_FILE_MSG"
        fi
    fi
fi

# 清理旧日志（保留最近500行）
if [ -f "$LOGFILE" ]; then
    lines=$(wc -l < "$LOGFILE")
    if [ "$lines" -gt 1000 ]; then
        tail -500 "$LOGFILE" > "${LOGFILE}.tmp" && mv "${LOGFILE}.tmp" "$LOGFILE"
        log "📝 日志已清理"
    fi
fi

log "━━━ 保活检查结束 ━━━"
