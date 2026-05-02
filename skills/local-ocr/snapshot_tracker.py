#!/usr/bin/env python3
"""
L2 盘口快照时序存储 + 变化对比
每次识别后存入 JSONL，下次识别时自动对比
"""

import json
import os
from datetime import datetime

SNAPSHOT_DIR = '/home/adam/.openclaw/workspace/data/l2_snapshots'


def ensure_dir():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)


def save_snapshot(stock_code, ocr_result):
    """保存一次盘口快照"""
    ensure_dir()
    filepath = os.path.join(SNAPSHOT_DIR, f'{stock_code}.jsonl')
    
    if isinstance(ocr_result, str):
        data = json.loads(ocr_result)
    else:
        data = ocr_result
    
    snapshot = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'stock': stock_code,
        **data
    }
    
    with open(filepath, 'a') as f:
        f.write(json.dumps(snapshot, ensure_ascii=False) + '\n')
    
    return snapshot


def load_last_two(stock_code):
    """加载最近两次快照用于对比"""
    filepath = os.path.join(SNAPSHOT_DIR, f'{stock_code}.jsonl')
    if not os.path.exists(filepath):
        return None, None
    
    lines = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(json.loads(line))
    
    if len(lines) >= 2:
        return lines[-2], lines[-1]
    elif len(lines) == 1:
        return None, lines[-1]
    return None, None


def diff_snapshots(prev, curr):
    """对比两次快照，找出变化"""
    if not prev:
        return {'type': 'first_snapshot', 'message': '首次快照，无历史对比'}
    
    changes = {
        'time_range': f"{prev['timestamp']} → {curr['timestamp']}",
        'price_changes': [],
        'big_order_changes': [],
        'volume_changes': {},
        'alerts': []
    }
    
    # 价格变化
    prev_sell1 = prev['sell'][0]['price'] if prev.get('sell') else 0
    curr_sell1 = curr['sell'][0]['price'] if curr.get('sell') else 0
    prev_buy1 = prev['buy'][0]['price'] if prev.get('buy') else 0
    curr_buy1 = curr['buy'][0]['price'] if curr.get('buy') else 0
    
    if prev_sell1 != curr_sell1:
        changes['price_changes'].append(f'卖1: {prev_sell1} → {curr_sell1} ({curr_sell1-prev_sell1:+.2f})')
    if prev_buy1 != curr_buy1:
        changes['price_changes'].append(f'买1: {prev_buy1} → {curr_buy1} ({curr_buy1-prev_buy1:+.2f})')
    
    # 总量变化
    prev_total_sell = prev.get('total_sell', 0)
    curr_total_sell = curr.get('total_sell', 0)
    prev_total_buy = prev.get('total_buy', 0)
    curr_total_buy = curr.get('total_buy', 0)
    
    sell_delta = curr_total_sell - prev_total_sell
    buy_delta = curr_total_buy - prev_total_buy
    
    changes['volume_changes'] = {
        'sell': f'{prev_total_sell:,} → {curr_total_sell:,} ({sell_delta:+,})',
        'buy': f'{prev_total_buy:,} → {curr_total_buy:,} ({buy_delta:+,})',
        'sell_delta': sell_delta,
        'buy_delta': buy_delta
    }
    
    # 卖买比变化
    prev_ratio = prev.get('sell_buy_ratio', 0)
    curr_ratio = curr.get('sell_buy_ratio', 0)
    if prev_ratio != curr_ratio:
        changes['volume_changes']['ratio'] = f'{prev_ratio} → {curr_ratio} ({curr_ratio-prev_ratio:+.2f})'
    
    # 大单变化追踪
    def make_order_key(order):
        return f"{order['price']:.2f}"
    
    prev_sell_orders = {make_order_key(o): o for o in prev.get('sell', [])}
    curr_sell_orders = {make_order_key(o): o for o in curr.get('sell', [])}
    prev_buy_orders = {make_order_key(o): o for o in prev.get('buy', [])}
    curr_buy_orders = {make_order_key(o): o for o in curr.get('buy', [])}
    
    # 卖盘大单变化
    for price_key, curr_order in curr_sell_orders.items():
        if curr_order['volume'] >= 5000:
            if price_key in prev_sell_orders:
                delta = curr_order['volume'] - prev_sell_orders[price_key]['volume']
                if abs(delta) > 100:
                    changes['big_order_changes'].append({
                        'side': '卖',
                        'price': curr_order['price'],
                        'before': prev_sell_orders[price_key]['volume'],
                        'after': curr_order['volume'],
                        'delta': delta
                    })
            else:
                changes['big_order_changes'].append({
                    'side': '卖',
                    'price': curr_order['price'],
                    'before': 0,
                    'after': curr_order['volume'],
                    'delta': curr_order['volume'],
                    'event': '新出现'
                })
    
    # 检查之前的大单是否消失
    for price_key, prev_order in prev_sell_orders.items():
        if prev_order['volume'] >= 5000 and price_key not in curr_sell_orders:
            changes['big_order_changes'].append({
                'side': '卖',
                'price': prev_order['price'],
                'before': prev_order['volume'],
                'after': 0,
                'delta': -prev_order['volume'],
                'event': '消失'
            })
    
    # 买盘大单变化
    for price_key, curr_order in curr_buy_orders.items():
        if curr_order['volume'] >= 5000:
            if price_key in prev_buy_orders:
                delta = curr_order['volume'] - prev_buy_orders[price_key]['volume']
                if abs(delta) > 100:
                    changes['big_order_changes'].append({
                        'side': '买',
                        'price': curr_order['price'],
                        'before': prev_buy_orders[price_key]['volume'],
                        'after': curr_order['volume'],
                        'delta': delta
                    })
            else:
                changes['big_order_changes'].append({
                    'side': '买',
                    'price': curr_order['price'],
                    'before': 0,
                    'after': curr_order['volume'],
                    'delta': curr_order['volume'],
                    'event': '新出现'
                })
    
    for price_key, prev_order in prev_buy_orders.items():
        if prev_order['volume'] >= 5000 and price_key not in curr_buy_orders:
            changes['big_order_changes'].append({
                'side': '买',
                'price': prev_order['price'],
                'before': prev_order['volume'],
                'after': 0,
                'delta': -prev_order['volume'],
                'event': '消失'
            })
    
    # 生成告警
    if sell_delta > 50000:
        changes['alerts'].append(f'⚠️ 卖盘暴增 {sell_delta:,}手，主力可能在加压出货')
    if buy_delta > 50000:
        changes['alerts'].append(f'✅ 买盘暴增 {buy_delta:,}手，有大资金在接')
    if sell_delta < -50000:
        changes['alerts'].append(f'📉 卖盘减少 {abs(sell_delta):,}手，可能在撤单或成交')
    if buy_delta < -50000:
        changes['alerts'].append(f'⚠️ 买盘减少 {abs(buy_delta):,}手，支撑可能在松动')
    
    if curr_ratio > 3.0:
        changes['alerts'].append(f'🔴 卖买比 {curr_ratio}，卖压极重')
    elif curr_ratio < 1.0:
        changes['alerts'].append(f'🟢 卖买比 {curr_ratio}，买盘占优')
    
    return changes


def format_diff(diff):
    """格式化对比结果为可读文本"""
    lines = []
    
    if diff.get('type') == 'first_snapshot':
        return '📸 首次快照已保存，15分钟后再发截图对比'
    
    lines.append(f'📊 盘口变化 [{diff["time_range"]}]')
    lines.append('')
    
    if diff['price_changes']:
        lines.append('💰 价格变化:')
        for c in diff['price_changes']:
            lines.append(f'  {c}')
        lines.append('')
    
    vc = diff.get('volume_changes', {})
    if vc:
        lines.append('📈 总量变化:')
        lines.append(f'  卖盘: {vc.get("sell", "")}')
        lines.append(f'  买盘: {vc.get("buy", "")}')
        if 'ratio' in vc:
            lines.append(f'  卖买比: {vc["ratio"]}')
        lines.append('')
    
    if diff['big_order_changes']:
        lines.append('🔍 大单变化 (5000+手):')
        for c in diff['big_order_changes']:
            side = c['side']
            price = c['price']
            before = c['before']
            after = c['after']
            delta = c['delta']
            event = c.get('event', '')
            if delta > 0:
                lines.append(f'  {side}{price:.2f}: {before:,} → {after:,} (+{delta:,}) {event}')
            else:
                lines.append(f'  {side}{price:.2f}: {before:,} → {after:,} ({delta:,}) {event}')
        lines.append('')
    
    if diff['alerts']:
        lines.append('🚨 告警:')
        for a in diff['alerts']:
            lines.append(f'  {a}')
    
    return '\n'.join(lines)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('用法: python3 snapshot_tracker.py <stock_code> <json_result>')
        sys.exit(1)
    
    stock = sys.argv[1]
    json_data = sys.argv[2]
    
    # 保存当前快照
    curr = save_snapshot(stock, json_data)
    
    # 加载上一次快照
    prev, _ = load_last_two(stock)
    
    # 对比
    diff = diff_snapshots(prev, curr)
    
    # 输出
    print(format_diff(diff))
