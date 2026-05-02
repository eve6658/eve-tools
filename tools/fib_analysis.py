#!/usr/bin/env python3
"""
fib_analysis.py — 斐波那契实盘统计工具
用法:
  python3 fib_analysis.py add <股票代码> <买入价> <卖出价> <低点> <高点> [日期] [备注]
  python3 fib_analysis.py list
  python3 fib_analysis.py stats
  python3 fib_analysis.py fib <低点> <高点> [当前价]
  python3 fib_analysis.py report
"""

import sys
import csv
import os
from datetime import datetime

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
TRADES_FILE = os.path.join(DATA_DIR, "fib_data", "trades.csv")

# 斐波那契回调比例
FIB_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786, 0.886]
FIB_NAMES = ["23.6%", "38.2%", "50.0%", "61.8%", "78.6%", "88.6%"]

def ensure_trades_file():
    if not os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["date", "stock", "stock_name", "action", "price", "shares", "low_point", "high_point", "note"])

def load_trades():
    ensure_trades_file()
    trades = []
    with open(TRADES_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append(row)
    return trades

def add_trade(stock, buy_price, sell_price, low, high, date=None, note=""):
    ensure_trades_file()
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # 查股票名
    stock_names = {"600666": "奥瑞德", "002788": "鹭燕医药", "688347": "华虹公司"}
    name = stock_names.get(stock, "")
    
    with open(TRADES_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([date, stock, name, "buy", buy_price, "", low, high, note])
        writer.writerow([date, stock, name, "sell", sell_price, "", low, high, note])
    
    # 计算这笔交易的斐波那契位置
    涨幅 = float(high) - float(low)
    buy_fib = (float(buy_price) - float(low)) / 涨幅 if 涨幅 > 0 else 0
    sell_fib = (float(sell_price) - float(low)) / 涨幅 if 涨幅 > 0 else 0
    
    print(f"✅ 已添加: {stock} {name}")
    print(f"   买入: {buy_price} (回调位 {buy_fib*100:.1f}%)")
    print(f"   卖出: {sell_price} (回调位 {sell_fib*100:.1f}%)")
    print(f"   盈亏: {float(sell_price) - float(buy_price):.2f} ({(float(sell_price)/float(buy_price)-1)*100:.1f}%)")

def calc_fib_levels(low, high):
    """计算斐波那契支撑/压力位"""
    low, high = float(low), float(high)
    spread = high - low
    levels = {}
    for ratio, name in zip(FIB_LEVELS, FIB_NAMES):
        # 回调位（从高点往下）
        levels[name] = round(high - spread * ratio, 3)
    return levels

def fib_command(low, high, current=None):
    levels = calc_fib_levels(low, high)
    print(f"📊 斐波那契位 | 低点:{low} → 高点:{high}")
    print(f"{'比例':<10} {'价位':>10} {'与当前价距离':>12}")
    print("─" * 35)
    for name, price in levels.items():
        if current:
            dist = (float(current) - price) / float(current) * 100
            print(f"{name:<10} {price:>10.3f} {dist:>+10.1f}%")
        else:
            print(f"{name:<10} {price:>10.3f}")

def list_trades():
    trades = load_trades()
    if not trades:
        print("暂无交易记录")
        return
    
    print(f"{'日期':<12} {'股票':<8} {'方向':<6} {'价格':>8} {'回调位':>8} {'备注'}")
    print("─" * 60)
    
    for t in trades:
        low = float(t.get('low_point', 0) or 0)
        high = float(t.get('high_point', 0) or 0)
        price = float(t.get('price', 0) or 0)
        spread = high - low
        fib_pos = (price - low) / spread * 100 if spread > 0 else 0
        
        print(f"{t['date']:<12} {t['stock']:<8} {t['action']:<6} {price:>8.2f} {fib_pos:>7.1f}% {t.get('note','')}")

def calc_stats():
    trades = load_trades()
    if not trades:
        print("暂无交易记录，无法统计")
        return None
    
    # 按股票分组，配对买卖
    by_stock = {}
    for t in trades:
        key = t['stock']
        if key not in by_stock:
            by_stock[key] = {"buys": [], "sells": []}
        if t['action'] == 'buy':
            by_stock[key]['buys'].append(t)
        else:
            by_stock[key]['sells'].append(t)
    
    results = []
    for stock, data in by_stock.items():
        for buy in data['buys']:
            for sell in data['sells']:
                low = float(buy.get('low_point', 0) or 0)
                high = float(buy.get('high_point', 0) or 0)
                spread = high - low
                buy_price = float(buy['price'])
                sell_price = float(sell['price'])
                
                buy_fib = (buy_price - low) / spread * 100 if spread > 0 else 0
                sell_fib = (sell_price - low) / spread * 100 if spread > 0 else 0
                profit = sell_price - buy_price
                profit_pct = (sell_price / buy_price - 1) * 100
                
                # 判断买入在哪个斐波那契位
                buy_level = "其他"
                for ratio, name in zip(FIB_LEVELS, FIB_NAMES):
                    if abs(buy_fib - (1 - ratio) * 100) < 5:
                        buy_level = name
                        break
                
                results.append({
                    "stock": stock,
                    "stock_name": buy.get('stock_name', ''),
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "buy_fib": buy_fib,
                    "sell_fib": sell_fib,
                    "buy_level": buy_level,
                    "profit": profit,
                    "profit_pct": profit_pct,
                    "low": low,
                    "high": high,
                    "date": buy.get('date', ''),
                })
    return results

def stats_command():
    results = calc_stats()
    if not results:
        return
    
    print("📈 交易统计")
    print("─" * 70)
    
    total_profit = 0
    win_count = 0
    level_stats = {}
    
    for r in results:
        status = "✅" if r['profit'] > 0 else "❌"
        if r['profit'] > 0:
            win_count += 1
        total_profit += r['profit']
        
        level = r['buy_level']
        if level not in level_stats:
            level_stats[level] = {"count": 0, "win": 0, "total_profit": 0}
        level_stats[level]["count"] += 1
        level_stats[level]["total_profit"] += r['profit']
        if r['profit'] > 0:
            level_stats[level]["win"] += 1
        
        print(f"{status} {r['stock']} {r['stock_name']} | 买{r['buy_price']:.2f} 卖{r['sell_price']:.2f} | "
              f"盈亏{r['profit']:+.2f}({r['profit_pct']:+.1f}%) | 买入位{r['buy_fib']:.1f}%")
    
    print()
    print("═" * 50)
    print(f"总计: {len(results)}笔 | 胜率: {win_count/len(results)*100:.0f}% | 总盈亏: {total_profit:+.2f}")
    print()
    
    # 按斐波那契位统计
    print("📊 按买入斐波那契位统计")
    print(f"{'位置':<10} {'笔数':>5} {'胜率':>8} {'总盈亏':>10}")
    print("─" * 35)
    for level, stats in sorted(level_stats.items()):
        win_rate = stats['win'] / stats['count'] * 100 if stats['count'] > 0 else 0
        print(f"{level:<10} {stats['count']:>5} {win_rate:>7.0f}% {stats['total_profit']:>+10.2f}")

def report_command():
    results = calc_stats()
    if not results:
        return
    
    print("📋 斐波那契实盘分析报告")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    stats_command()
    
    print()
    print("═" * 50)
    print("💡 初步结论（数据量不足时仅供参考）:")
    
    if len(results) < 5:
        print("⚠️ 当前样本量不足5笔，结论可靠性低，继续积累数据")
    
    # 检查哪个斐波那契位买入胜率最高
    level_stats = {}
    for r in results:
        level = r['buy_level']
        if level not in level_stats:
            level_stats[level] = {"count": 0, "win": 0}
        level_stats[level]["count"] += 1
        if r['profit'] > 0:
            level_stats[level]["win"] += 1
    
    best_level = None
    best_winrate = 0
    for level, stats in level_stats.items():
        if stats['count'] >= 2:
            win_rate = stats['win'] / stats['count']
            if win_rate > best_winrate:
                best_winrate = win_rate
                best_level = level
    
    if best_level:
        print(f"🎯 当前数据显示: 在{best_level}附近买入胜率最高({best_winrate*100:.0f}%)")
    else:
        print("🎯 数据不足以判断最优买入位")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    cmd = sys.argv[1]
    
    if cmd == "add" and len(sys.argv) >= 7:
        stock = sys.argv[2]
        buy = float(sys.argv[3])
        sell = float(sys.argv[4])
        low = float(sys.argv[5])
        high = float(sys.argv[6])
        date = sys.argv[7] if len(sys.argv) > 7 else None
        note = sys.argv[8] if len(sys.argv) > 8 else ""
        add_trade(stock, buy, sell, low, high, date, note)
    
    elif cmd == "list":
        list_trades()
    
    elif cmd == "stats":
        stats_command()
    
    elif cmd == "fib" and len(sys.argv) >= 4:
        low = sys.argv[2]
        high = sys.argv[3]
        current = sys.argv[4] if len(sys.argv) > 4 else None
        fib_command(low, high, current)
    
    elif cmd == "report":
        report_command()
    
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
