#!/usr/bin/env python3
"""长图分段OCR：先切成小段，再逐段识别"""
import sys
import subprocess
import json
from pathlib import Path
from PIL import Image

def split_image(img_path, segment_height=800):
    """将长图切成若干段"""
    img = Image.open(img_path)
    w, h = img.size
    segments = []
    for i, y in enumerate(range(0, h, segment_height)):
        box = (0, y, w, min(y + segment_height, h))
        seg = img.crop(box)
        seg_path = f"/tmp/ocr_seg_{i}.png"
        seg.save(seg_path)
        segments.append((seg_path, y, min(y + segment_height, h)))
    return segments

def ocr_segment(seg_path):
    """对单段跑OCR"""
    cmd = ["/home/adam/open_claw_env/bin/python3",
           "/home/adam/.openclaw/workspace/skills/local-ocr/ocr_logic.py", seg_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r.stdout, r.stderr

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 split_ocr.py <图片路径> [段高=800]")
        sys.exit(1)
    
    img_path = sys.argv[1]
    seg_h = int(sys.argv[2]) if len(sys.argv) > 2 else 800
    
    segments = split_image(img_path, seg_h)
    print(f"切成 {len(segments)} 段，每段高 {seg_h}px\n")
    
    all_results = []
    for seg_path, y1, y2 in segments:
        print(f"=== 段 {y1}-{y2}px ===")
        stdout, stderr = ocr_segment(seg_path)
        print(stdout)
        if stderr:
            print(stderr)
        all_results.append({"y_range": [y1, y2], "stdout": stdout})
    
    print(f"\n共处理 {len(segments)} 段")
