#!/bin/bash
# PDF转Word工具 (本地运行，无需联网)
# 用法: ./pdf2word.sh <输入.pdf> [输出目录]

if [ -z "$1" ]; then
    echo "用法: ./pdf2word.sh <输入.pdf> [输出目录]"
    echo "示例: ./pdf2word.sh 手册.pdf ./output"
    exit 1
fi

INPUT="$1"
OUTPUT_DIR="${2:-.}"

if [ ! -f "$INPUT" ]; then
    echo "❌ 文件不存在: $INPUT"
    exit 1
fi

echo "🔄 正在转换: $INPUT"
echo "   输出目录: $OUTPUT_DIR"

# 使用LibreOffice转换
libreoffice --headless --convert-to docx --outdir "$OUTPUT_DIR" "$INPUT" 2>&1

if [ $? -eq 0 ]; then
    BASENAME=$(basename "$INPUT" .pdf)
    echo "✅ 转换完成: $OUTPUT_DIR/$BASENAME.docx"
else
    echo "❌ 转换失败"
    exit 1
fi
