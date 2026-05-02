#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转Word工具 - 本地运行版
使用方法:
  1. 安装依赖: pip install pdf2docx
  2. 运行: python pdf2word.py 输入.pdf [输出.docx]
"""

import sys
import os

def convert_pdf_to_word(pdf_path, docx_path=None):
    """将PDF转换为Word文档"""
    try:
        from pdf2docx import Converter
    except ImportError:
        print("请先安装依赖: pip install pdf2docx")
        sys.exit(1)
    
    if not os.path.exists(pdf_path):
        print(f"❌ 文件不存在: {pdf_path}")
        return False
    
    if docx_path is None:
        docx_path = pdf_path.replace('.pdf', '.docx')
    
    print(f"🔄 正在转换: {pdf_path}")
    print(f"   输出文件: {docx_path}")
    
    cv = Converter(pdf_path)
    cv.convert(docx_path)
    cv.close()
    
    print(f"✅ 转换完成: {docx_path}")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python pdf2word.py <输入.pdf> [输出.docx]")
        print("示例: python pdf2word.py 手册.pdf 手册.docx")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    docx_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    convert_pdf_to_word(pdf_file, docx_file)
