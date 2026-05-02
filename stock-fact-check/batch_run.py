#!/usr/bin/env python3
"""批量跑三个标的的事实调查"""
import subprocess
import sys

stocks = {
    "688981": "中芯国际（芯片半导体）",
    "600547": "山东黄金（有色贵金属）",
    "603019": "中科曙光（大模型算力）",
}

for code, name in stocks.items():
    print(f"\n{'#'*60}")
    print(f"# {name}")
    print(f"{'#'*60}")
    result = subprocess.run(
        ["python3", "fact_check.py", code],
        capture_output=True, text=True, timeout=90
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[:500])
