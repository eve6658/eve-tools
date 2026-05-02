import csv
import os
from datetime import datetime

CSV_PATH = os.path.expanduser("~/.openclaw/workspace/skills/local-ocr/data/trade_logs/trade_logs.csv")

def log_trade_data(stock, sell1, buy1, total_sell, total_buy, s_big, b_big):
    # 计算委比
    try:
        weibi = (total_buy - total_sell) / (total_buy + total_sell) * 100
    except ZeroDivisionError:
        weibi = 0
    
    # 确保目录存在
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    
    # 准备字段
    file_exists = os.path.isfile(CSV_PATH)
    headers = ["timestamp", "stock", "sell1_price", "buy1_price", "spread", "total_sell", "total_buy", "weibi", "sell_big5k", "buy_big5k"]
    
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stock": stock,
        "sell1_price": sell1,
        "buy1_price": buy1,
        "spread": round(abs(sell1 - buy1), 3),
        "total_sell": total_sell,
        "total_buy": total_buy,
        "weibi": f"{weibi:.2f}%",
        "sell_big5k": s_big,
        "buy_big5k": b_big
    }
    
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    
    return weibi
