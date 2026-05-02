#!/bin/bash
# OpenClaw macOS 迁移脚本
# 使用方法：
#   1. 在Ubuntu上运行: bash migrate_to_macos.sh export
#   2. 把 openclaw_migration.tar.gz 拷到Mac
#   3. 在Mac上运行: bash migrate_to_macos.sh import

set -e

ACTION="${1:-help}"
MIGRATION_FILE="openclaw_migration.tar.gz"

case "$ACTION" in

  export)
    echo "=== Step 1: 导出 OpenClaw 配置 ==="
    mkdir -p /tmp/openclaw_migrate

    # OpenClaw config
    cp -r ~/.openclaw/config* /tmp/openclaw_migrate/ 2>/dev/null || true
    cp -r ~/.openclaw/channels* /tmp/openclaw_migrate/ 2>/dev/null || true
    cp ~/.openclaw/*.json /tmp/openclaw_migrate/ 2>/dev/null || true
    cp ~/.openclaw/*.yaml /tmp/openclaw_migrate/ 2>/dev/null || true
    cp ~/.openclaw/*.yml /tmp/openclaw_migrate/ 2>/dev/null || true

    echo "=== Step 2: 导出 Workspace ==="
    cp -r ~/.openclaw/workspace /tmp/openclaw_migrate/workspace

    echo "=== Step 3: 导出 Python 环境依赖 ==="
    if [ -f ~/open_claw_env/bin/pip3 ]; then
      ~/open_claw_env/bin/pip3 freeze > /tmp/openclaw_migrate/requirements.txt
      echo "已生成 requirements.txt ($(wc -l < /tmp/openclaw_migrate/requirements.txt) 个包)"
    fi

    echo "=== Step 4: 导出 extensions ==="
    cp -r ~/.openclaw/extensions /tmp/openclaw_migrate/extensions 2>/dev/null || true

    echo "=== Step 5: 打包 ==="
    cd /tmp/openclaw_migrate
    tar czf ~/$MIGRATION_FILE .
    cd -
    echo "✅ 导出完成: ~/$MIGRATION_FILE ($(du -h ~/$MIGRATION_FILE | cut -f1))"

    echo ""
    echo "下一步：把 $MIGRATION_FILE 拷到Mac，然后运行:"
    echo "  bash migrate_to_macos.sh import"
    ;;

  import)
    echo "=== macOS 迁移开始 ==="

    # 检查Node.js
    if ! command -v node &>/dev/null; then
      echo "❌ 未安装Node.js，请先安装:"
      echo "  brew install node"
      exit 1
    fi
    echo "✅ Node.js $(node -v)"

    # Step 1: 安装OpenClaw
    echo "=== Step 1: 安装 OpenClaw ==="
    if ! command -v openclaw &>/dev/null; then
      npm install -g openclaw
      echo "✅ OpenClaw 已安装"
    else
      echo "✅ OpenClaw 已存在: $(openclaw --version)"
    fi

    # Step 2: 解压迁移文件
    echo "=== Step 2: 解压数据 ==="
    mkdir -p ~/.openclaw
    mkdir -p /tmp/openclaw_import
    tar xzf $MIGRATION_FILE -C /tmp/openclaw_import

    # Step 3: 恢复配置
    echo "=== Step 3: 恢复配置 ==="
    cp /tmp/openclaw_import/config* ~/.openclaw/ 2>/dev/null || true
    cp /tmp/openclaw_import/channels* ~/.openclaw/ 2>/dev/null || true
    cp /tmp/openclaw_import/*.json ~/.openclaw/ 2>/dev/null || true
    cp /tmp/openclaw_import/*.yaml ~/.openclaw/ 2>/dev/null || true
    cp /tmp/openclaw_import/*.yml ~/.openclaw/ 2>/dev/null || true
    echo "✅ 配置已恢复"

    # Step 4: 恢复workspace
    echo "=== Step 4: 恢复 Workspace ==="
    cp -r /tmp/openclaw_import/workspace ~/.openclaw/workspace
    echo "✅ Workspace 已恢复"

    # Step 5: 恢复extensions
    echo "=== Step 5: 恢复 Extensions ==="
    cp -r /tmp/openclaw_import/extensions ~/.openclaw/extensions 2>/dev/null || true
    echo "✅ Extensions 已恢复"

    # Step 6: 重建Python环境
    echo "=== Step 6: 重建 Python 环境 ==="
    python3 -m venv ~/open_claw_env
    source ~/open_claw_env/bin/activate

    # 安装基础依赖
    pip3 install --upgrade pip

    # 安装迁移的依赖
    if [ -f /tmp/openclaw_import/requirements.txt ]; then
      echo "安装Python依赖..."
      pip3 install -r /tmp/openclaw_import/requirements.txt 2>&1 | tail -5
    fi

    # 单独确认关键包
    pip3 install tushare yfinance playwright 2>/dev/null || true

    # 安装playwright浏览器
    ~/open_claw_env/bin/playwright install chromium 2>/dev/null || true

    echo "✅ Python 环境已重建"

    # Step 7: 安装Lightpanda
    echo "=== Step 7: 安装 Lightpanda ==="
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
      LP_URL="https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-aarch64-macos"
    else
      LP_URL="https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-x86_64-macos"
    fi
    mkdir -p ~/.local/bin
    curl -sL "$LP_URL" -o ~/.local/bin/lightpanda
    chmod +x ~/.local/bin/lightpanda
    echo "✅ Lightpanda 已安装 ($(uname -m))"

    # Step 8: 设置环境变量
    echo "=== Step 8: 环境变量 ==="
    echo 'export PATH="$HOME/.local/bin:$HOME/open_claw_env/bin:$PATH"' >> ~/.zshrc
    echo 'export TUSHARE_TOKEN="e0dc18fc3ef8b9aa6a77b3e02a98f909097a237d7aa3cf82bfe1ad19"' >> ~/.zshrc
    echo "✅ 环境变量已写入 ~/.zshrc"

    # 清理
    rm -rf /tmp/openclaw_import

    echo ""
    echo "=========================================="
    echo "✅ 迁移完成！"
    echo "=========================================="
    echo ""
    echo "下一步："
    echo "  1. source ~/.zshrc"
    echo "  2. openclaw gateway start"
    echo "  3. 测试: 发一条QQ消息验证"
    echo ""
    echo "Python环境路径: ~/open_claw_env"
    echo "Lightpanda: ~/.local/bin/lightpanda"
    ;;

  help|*)
    echo "用法:"
    echo "  在Ubuntu上:  bash migrate_to_macos.sh export"
    echo "  在Mac上:     bash migrate_to_macos.sh import"
    ;;
esac
