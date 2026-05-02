#!/usr/bin/env python3
"""
Windows端盘口数据发送脚本
将抓取到的盘口数据POST到Linux服务器

使用方法：
  1. 修改 SERVER_URL 为你的服务器地址
  2. 修改 capture_orderbook() 函数，接入你的数据源
  3. 运行：python orderbook_sender.py
"""
import requests, json, time
from datetime import datetime

# ===== 配置 =====
SERVER_URL = 'http://你的服务器IP:9876'  # 改成你的服务器地址
STOCK_CODE = '688146'  # 股票代码
INTERVAL = 5  # 发送间隔（秒）

def capture_orderbook():
    """
    在这里实现你的盘口数据抓取
    返回格式：
    {
        "stock": "688146",
        "timestamp": "2026-04-28 22:30:00",
        "bids": [(价格, 手数), ...],   # 买盘，价格从高到低
        "asks": [(价格, 手数), ...]    # 卖盘，价格从低到高
    }
    """
    # ===== 示例：手动构造数据（替换为你的内存抓取代码）=====
    data = {
        "stock": STOCK_CODE,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "bids": [
            # (price, volume_in_lots)
            (74.50, 150),
            (74.45, 200),
            (74.40, 350),
            (74.35, 100),
            (74.30, 450),
        ],
        "asks": [
            (74.55, 180),
            (74.60, 320),
            (74.65, 250),
            (74.70, 400),
            (74.75, 120),
        ],
        # 可选：附加信息
        "source": "memory_scan",  # 或 "screenshot_ocr"
        "raw": {}  # 原始数据
    }
    # ===== 替换结束 =====
    return data

def send_to_server(data):
    try:
        resp = requests.post(SERVER_URL, json=data, timeout=10)
        result = resp.json()
        if result.get('status') == 'ok':
            print(f'[{data["timestamp"]}] {data["stock"]} 发送成功')
            return True
        else:
            print(f'服务器错误: {result}')
            return False
    except Exception as e:
        print(f'发送失败: {e}')
        return False

if __name__ == '__main__':
    print(f'开始发送 {STOCK_CODE} 盘口数据到 {SERVER_URL}')
    print(f'间隔: {INTERVAL}秒')
    print('按Ctrl+C停止\n')
    
    while True:
        data = capture_orderbook()
        if data:
            send_to_server(data)
        time.sleep(INTERVAL)
