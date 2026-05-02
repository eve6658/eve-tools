#!/usr/bin/env python3
"""
extract_l2.py — 本地L2逐笔成交识别工具 v2
用法: python3 extract_l2.py <图片路径> [--small-threshold 10]
"""

import sys
import time
import re
from rapidocr_onnxruntime import RapidOCR

def extract_trades(img_path, small_threshold=10):
    engine = RapidOCR()
    start = time.time()
    result, elapse = engine(img_path)
    
    if not result:
        return {"error": "未识别到数据", "time": elapse}
    
    # 按y坐标排序，同一行内按x排序
    items = []
    for line in result:
        box, txt, conf = line
        y = box[0][1]
        x = box[0][0]
        items.append({"x": x, "y": y, "text": txt.strip(), "conf": conf})
    
    items.sort(key=lambda i: (round(i["y"] / 15) * 15, i["x"]))
    
    # 按y分组（同一行）
    rows = []
    current_row = []
    current_y = None
    for item in items:
        y_key = round(item["y"] / 15) * 15
        if current_y is None or abs(y_key - current_y) < 20:
            current_row.append(item)
            current_y = y_key
        else:
            rows.append(sorted(current_row, key=lambda i: i["x"]))
            current_row = [item]
            current_y = y_key
    if current_row:
        rows.append(sorted(current_row, key=lambda i: i["x"]))
    
    # 解析每行：找时间戳，后面跟价格、手数、方向
    time_pat = re.compile(r'^\d{2}:\d{2}:\d{2}$')
    price_pat = re.compile(r'^\d{1,3}\.\d{2}$')
    vol_pat = re.compile(r'^\d+(\.\d+)?$')
    
    trades = []
    for row in rows:
        texts = [i["text"] for i in row]
        # 找时间戳位置
        time_idx = None
        for idx, t in enumerate(texts):
            if time_pat.match(t):
                time_idx = idx
                break
        
        if time_idx is None:
            continue
        
        trade = {"time": texts[time_idx]}
        remaining = texts[time_idx + 1:]
        
        # 从剩余文本中找价格、手数、方向
        prices = []
        vols = []
        dirs = []
        
        for t in remaining:
            if price_pat.match(t):
                prices.append(float(t))
            elif vol_pat.match(t.replace('.', '', 1)) if '.' in t else vol_pat.match(t):
                vols.append(float(t))
            elif any(c in t for c in ['买', '卖', 'B', 'S']):
                if '卖' in t or 'S' in t:
                    dirs.append('卖')
                else:
                    dirs.append('买')
        
        if prices:
            trade["price"] = prices[0]
        if vols:
            trade["volume"] = vols[0]
        if dirs:
            trade["direction"] = dirs[0]
        else:
            trade["direction"] = "?"
        
        trades.append(trade)
    
    # 统计
    small_buy = [t for t in trades if t.get("direction") == "买" and t.get("volume", 999) < small_threshold]
    small_sell = [t for t in trades if t.get("direction") == "卖" and t.get("volume", 999) < small_threshold]
    all_buy = [t for t in trades if t.get("direction") == "买"]
    all_sell = [t for t in trades if t.get("direction") == "卖"]
    
    times_list = [t["time"] for t in trades]
    
    stats = {
        "total_trades": len(trades),
        "buy_trades": len(all_buy),
        "sell_trades": len(all_sell),
        "buy_volume": sum(t.get("volume", 0) for t in all_buy),
        "sell_volume": sum(t.get("volume", 0) for t in all_sell),
        "small_buy_volume": sum(t.get("volume", 0) for t in small_buy),
        "small_sell_volume": sum(t.get("volume", 0) for t in small_sell),
        "small_total": sum(t.get("volume", 0) for t in small_buy) + sum(t.get("volume", 0) for t in small_sell),
        "small_threshold": small_threshold,
        "time_range": f"{times_list[-1]} - {times_list[0]}" if times_list else "N/A",
        "ocr_time": round(elapse[0] if isinstance(elapse, list) else elapse, 2),
    }
    
    # 每分钟成交量
    if len(times_list) >= 2:
        try:
            from datetime import datetime
            t1 = datetime.strptime(times_list[-1], "%H:%M:%S")
            t2 = datetime.strptime(times_list[0], "%H:%M:%S")
            span = abs((t2 - t1).total_seconds())
            if span > 0:
                stats["span_sec"] = span
                stats["vol_per_min"] = round((stats["buy_volume"] + stats["sell_volume"]) / span * 60)
                stats["small_vol_per_min"] = round(stats["small_total"] / span * 60)
        except:
            pass
    
    return {"trades": trades, "stats": stats}

def main():
    if len(sys.argv) < 2:
        print("用法: python3 extract_l2.py <图片路径> [--small-threshold N]")
        sys.exit(1)
    
    img_path = sys.argv[1]
    small_threshold = 10
    if "--small-threshold" in sys.argv:
        idx = sys.argv.index("--small-threshold")
        small_threshold = float(sys.argv[idx + 1])
    
    result = extract_trades(img_path, small_threshold)
    if "error" in result:
        print(f"❌ {result['error']}")
        sys.exit(1)
    
    s = result["stats"]
    trades = result["trades"]
    
    print(f"📊 逐笔成交 | {s['time_range']} | {s['ocr_time']}s")
    print(f"总成交: {s['total_trades']}笔 | 买{s['buy_trades']}/卖{s['sell_trades']}")
    print()
    print(f"🔽 小单(<{small_threshold}手)")
    print(f"  买: {s['small_buy_volume']:.0f}手 | 卖: {s['small_sell_volume']:.0f}手 | 合计: {s['small_total']:.0f}手")
    if "small_vol_per_min" in s:
        print(f"  折算: {s['small_vol_per_min']}手/分钟")
    print()
    print(f"📦 总量")
    print(f"  买: {s['buy_volume']:.0f}手 | 卖: {s['sell_volume']:.0f}手")
    if "vol_per_min" in s:
        print(f"  折算: {s['vol_per_min']}手/分钟")
    print()
    print(f"{'时间':<12} {'价格':>7} {'手数':>7} {'方向'}")
    for t in trades[:30]:
        p = f"{t['price']:.2f}" if 'price' in t else "-"
        v = f"{t['volume']:.0f}" if 'volume' in t else "-"
        print(f"{t.get('time','?'):<12} {p:>7} {v:>7} {t.get('direction','?')}")
    if len(trades) > 30:
        print(f"... 共{len(trades)}笔")

if __name__ == "__main__":
    main()
