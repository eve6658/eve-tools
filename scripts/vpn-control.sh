#!/bin/bash
# VPN/Proxy Control Script for Clash Verge
# Usage: vpn-control.sh [on|off|status]

PROXY_PORT=7897
SOCKET="/tmp/verge/verge-mihomo.sock"

case "$1" in
    on|enable)
        # Enable system proxy
        gsettings set org.gnome.system.proxy mode 'manual'
        gsettings set org.gnome.system.proxy.http host '127.0.0.1'
        gsettings set org.gnome.system.proxy.http port $PROXY_PORT
        gsettings set org.gnome.system.proxy.https host '127.0.0.1'
        gsettings set org.gnome.system.proxy.https port $PROXY_PORT
        
        # Export proxy env vars for CLI tools
        export http_proxy=http://127.0.0.1:$PROXY_PORT
        export https_proxy=http://127.0.0.1:$PROXY_PORT
        export HTTP_PROXY=http://127.0.0.1:$PROXY_PORT
        export HTTPS_PROXY=http://127.0.0.1:$PROXY_PORT
        export no_proxy="localhost,127.0.0.1,::1"
        
        echo "✅ VPN proxy enabled (port $PROXY_PORT)"
        ;;
    off|disable)
        # Disable system proxy
        gsettings set org.gnome.system.proxy mode 'none'
        
        # Unset proxy env vars
        unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY no_proxy
        
        echo "❌ VPN proxy disabled"
        ;;
    status|check)
        MODE=$(gsettings get org.gnome.system.proxy mode)
        echo "System proxy mode: $MODE"
        
        # Check if clash is running
        if pgrep -x "verge-mihomo" > /dev/null; then
            echo "Clash service: ✅ running"
        else
            echo "Clash service: ❌ not running"
        fi
        
        # Check if port is listening
        if ss -tlnp | grep -q ":$PROXY_PORT"; then
            echo "Proxy port $PROXY_PORT: ✅ listening"
        else
            echo "Proxy port $PROXY_PORT: ❌ not listening"
        fi
        
        # Test connectivity
        if curl -s --connect-timeout 5 -x http://127.0.0.1:$PROXY_PORT https://www.google.com > /dev/null 2>&1; then
            echo "Proxy test: ✅ OK"
        else
            echo "Proxy test: ❌ FAILED"
        fi
        ;;
    *)
        echo "Usage: $0 [on|off|status]"
        echo "  on      - Enable VPN proxy"
        echo "  off     - Disable VPN proxy"
        echo "  status  - Check proxy status"
        exit 1
        ;;
esac
