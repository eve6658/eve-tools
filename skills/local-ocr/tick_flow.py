#!/usr/bin/env python3
"""
逐笔委托（Tick Flow）分析工具
从L2逐笔成交截图中提取数据，分析主力资金流向
"""

import sys
import json
import re
import os
import csv
from datetime import datetime, timedelta
from collections import defaultdict

import pytesseract
from PIL import Image, ImageEnhance

TICK_LOG_DIR = '/home/adam/.openclaw/workspace/data/tick_logs'
TICK_CSV = os.path.join(TICK_LOG_DIR, 'tick_flow.csv')
TICK_HEADER = [
    'timestamp', 'stock', 'price', 'volume', 'direction',  # direction: 买单/卖单
    'batch_time'  # 截图时间
]


def preprocess(img):
    img = img.convert('L')
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = img.point(lambda x: 0 if x < 180 else 255, '1')
    return img


def ocr_tick_data(image_path):
    """OCR识别逐笔成交截图"""
    img = Image.open(image_path)
    w, h = img.size

    # 跳过顶部标题区（约400px）
    region = img.crop((0, 400, w, min(h, 8000)))
    gray = preprocess(region)
    config = r'--psm 6'
    text = pytesseract.image_to_string(gray, lang='chi_sim+eng', config=config)

    transactions = []
    for line in text.split('\n'):
        # 匹配: 时间 价格 手数 买单/卖单
        m = re.search(r'(\d{2}:\d{2}:\d{2})\s+([\d.]+)\s+(\d+)\s*(买单|卖单)', line)
        if m:
            ts, price, vol, direction = m.groups()
            transactions.append({
                'timestamp': ts,
                'price': float(price),
                'volume': int(vol),
                'direction': 'buy' if '买' in direction else 'sell'
            })

    return transactions


def analyze_tick_flow(transactions):
    """分析逐笔成交数据"""
    if not transactions:
        return {'error': '未识别到逐笔成交数据'}

    buys = [t for t in transactions if t['direction'] == 'buy']
    sells = [t for t in transactions if t['direction'] == 'sell']

    total_buy_vol = sum(t['volume'] for t in buys)
    total_sell_vol = sum(t['volume'] for t in sells)
    total_vol = total_buy_vol + total_sell_vol

    # 委比
    weibi = round((total_buy_vol - total_sell_vol) / total_vol * 100, 2) if total_vol > 0 else 0

    # 主动买卖比（外盘/内盘）
    active_buy = sum(t['volume'] for t in buys if t['volume'] >= 100)
    active_sell = sum(t['volume'] for t in sells if t['volume'] >= 100)
    active_ratio = round(active_buy / active_sell, 2) if active_sell > 0 else 0

    # 大单分析（>=100手）
    big_buys = sorted([t for t in buys if t['volume'] >= 100], key=lambda x: -x['volume'])
    big_sells = sorted([t for t in sells if t['volume'] >= 100], key=lambda x: -x['volume'])

    # 超大单（>=500手）
    huge_buys = [t for t in buys if t['volume'] >= 500]
    huge_sells = [t for t in sells if t['volume'] >= 500]

    # 价格区间
    buy_prices = [t['price'] for t in buys]
    sell_prices = [t['price'] for t in sells]

    # 成交密度（每秒笔数）
    if len(transactions) >= 2:
        time_format = '%H:%M:%S'
        try:
            t_start = datetime.strptime(transactions[-1]['timestamp'], time_format)
            t_end = datetime.strptime(transactions[0]['timestamp'], time_format)
            duration = (t_end - t_start).total_seconds()
            tps = round(len(transactions) / max(duration, 1), 1)
        except:
            duration = 0
            tps = 0
    else:
        duration = 0
        tps = 0

    # 逐笔方向变化（连续买单/卖单统计）
    streaks = []
    current_dir = None
    current_count = 0
    for t in reversed(transactions):
        if t['direction'] == current_dir:
            current_count += 1
        else:
            if current_dir:
                streaks.append((current_dir, current_count))
            current_dir = t['direction']
            current_count = 1
    if current_dir:
        streaks.append((current_dir, current_count))

    max_buy_streak = max([c for d, c in streaks if d == 'buy'], default=0)
    max_sell_streak = max([c for d, c in streaks if d == 'sell'], default=0)

    # 最新N笔的短期趋势
    recent_n = min(20, len(transactions))
    recent = transactions[:recent_n]
    recent_buy_vol = sum(t['volume'] for t in recent if t['direction'] == 'buy')
    recent_sell_vol = sum(t['volume'] for t in recent if t['direction'] == 'sell')
    recent_weibi = round((recent_buy_vol - recent_sell_vol) / (recent_buy_vol + recent_sell_vol) * 100, 2) if (recent_buy_vol + recent_sell_vol) > 0 else 0

    return {
        'total_trades': len(transactions),
        'buy_trades': len(buys),
        'sell_trades': len(sells),
        'total_buy_volume': total_buy_vol,
        'total_sell_volume': total_sell_vol,
        'weibi': weibi,
        'active_buy_volume': active_buy,
        'active_sell_volume': active_sell,
        'active_ratio': active_ratio,
        'big_buys_count': len(big_buys),
        'big_sells_count': len(big_sells),
        'huge_buys': [{'price': t['price'], 'volume': t['volume'], 'time': t['timestamp']} for t in huge_buys],
        'huge_sells': [{'price': t['price'], 'volume': t['volume'], 'time': t['timestamp']} for t in huge_sells],
        'buy_price_range': [min(buy_prices), max(buy_prices)] if buy_prices else [0, 0],
        'sell_price_range': [min(sell_prices), max(sell_prices)] if sell_prices else [0, 0],
        'trades_per_second': tps,
        'duration_seconds': duration,
        'max_buy_streak': max_buy_streak,
        'max_sell_streak': max_sell_streak,
        'recent_weibi': recent_weibi,
        'recent_n': recent_n,
        'top_buys': [{'price': t['price'], 'volume': t['volume'], 'time': t['timestamp']} for t in big_buys[:5]],
        'top_sells': [{'price': t['price'], 'volume': t['volume'], 'time': t['timestamp']} for t in big_sells[:5]],
        'transactions': transactions[:10]  # 最新10笔
    }


def save_tick_csv(stock, transactions, batch_time):
    """保存逐笔数据到CSV"""
    os.makedirs(TICK_LOG_DIR, exist_ok=True)
    if not os.path.exists(TICK_CSV):
        with open(TICK_CSV, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(TICK_HEADER)

    with open(TICK_CSV, 'a', newline='') as f:
        writer = csv.writer(f)
        for t in transactions:
            writer.writerow([
                batch_time + ' ' + t['timestamp'],
                stock,
                t['price'],
                t['volume'],
                t['direction'],
                batch_time
            ])


def format_tick_analysis(analysis, stock='600666'):
    """格式化分析结果为可读文本"""
    lines = []
    lines.append(f'📊 {stock} 逐笔委托分析')
    lines.append(f'总笔数: {analysis["total_trades"]}笔 (买{analysis["buy_trades"]}/卖{analysis["sell_trades"]})')
    lines.append(f'成交密度: {analysis["trades_per_second"]}/秒 | 跨度: {analysis["duration_seconds"]}秒')
    lines.append('')

    # 成交量
    bv = analysis['total_buy_volume']
    sv = analysis['total_sell_volume']
    lines.append(f'📈 成交量: 买{bv:,}手 / 卖{sv:,}手')
    lines.append(f'  逐笔委比: {analysis["weibi"]:+.2f}%')
    lines.append(f'  主动买/卖: {analysis["active_buy_volume"]:,}/{analysis["active_sell_volume"]:,} (比值{analysis["active_ratio"]})')
    lines.append(f'  最近{analysis["recent_n"]}笔委比: {analysis["recent_weibi"]:+.2f}%')
    lines.append('')

    # 连续方向
    lines.append(f'🔄 连续记录: 最长买{analysis["max_buy_streak"]}笔 / 最长卖{analysis["max_sell_streak"]}笔')
    lines.append('')

    # 价格区间
    bp = analysis['buy_price_range']
    sp = analysis['sell_price_range']
    lines.append(f'💰 价格区间:')
    lines.append(f'  买单: {bp[0]:.2f} ~ {bp[1]:.2f}')
    lines.append(f'  卖单: {sp[0]:.2f} ~ {sp[1]:.2f}')
    lines.append('')

    # 超大单（>=500手）
    if analysis['huge_buys']:
        lines.append(f'🟢 超大买单(500+): {len(analysis["huge_buys"])}笔')
        for t in analysis['huge_buys'][:5]:
            lines.append(f'  {t["time"]} {t["price"]:.2f} {t["volume"]:,}手')
        lines.append('')

    if analysis['huge_sells']:
        lines.append(f'🔴 超大卖单(500+): {len(analysis["huge_sells"])}笔')
        for t in analysis['huge_sells'][:5]:
            lines.append(f'  {t["time"]} {t["price"]:.2f} {t["volume"]:,}手')
        lines.append('')

    # 前5大成交
    if analysis['top_buys']:
        lines.append('前5大买单:')
        for t in analysis['top_buys']:
            lines.append(f'  {t["time"]} {t["price"]:.2f} {t["volume"]:,}手')
        lines.append('')

    if analysis['top_sells']:
        lines.append('前5大卖单:')
        for t in analysis['top_sells']:
            lines.append(f'  {t["time"]} {t["price"]:.2f} {t["volume"]:,}手')
        lines.append('')

    # 判断
    weibi = analysis['weibi']
    recent = analysis['recent_weibi']
    if weibi > 20:
        lines.append('🟢 买盘强势，主力在吃货')
    elif weibi > 5:
        lines.append('🟢 买盘略强')
    elif weibi > -5:
        lines.append('➡️ 多空平衡')
    elif weibi > -20:
        lines.append('🟡 卖盘略强')
    else:
        lines.append('🔴 卖盘强势，主力在出货')

    if recent - weibi > 10:
        lines.append('📈 短期趋势：买盘在增强')
    elif recent - weibi < -10:
        lines.append('📉 短期趋势：卖盘在增强')

    return '\n'.join(lines)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python3 tick_flow.py <截图路径> [股票代码]')
        sys.exit(1)

    image_path = sys.argv[1]
    stock = sys.argv[2] if len(sys.argv) > 2 else '600666'
    batch_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 1. OCR识别
    transactions = ocr_tick_data(image_path)

    if not transactions:
        print('❌ 未识别到逐笔成交数据，请确认截图内容')
        sys.exit(1)

    # 2. 保存CSV
    save_tick_csv(stock, transactions, batch_time)

    # 3. 分析
    analysis = analyze_tick_flow(transactions)

    # 4. 输出
    print(format_tick_analysis(analysis, stock))
