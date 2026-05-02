#!/usr/bin/env python3
"""
踩油门指标 - 盘后分析脚本
比对盘口数据与K线图，找主力踩油门的数学特征
"""

import json
import os
import glob
from datetime import datetime, timedelta
from collections import defaultdict

DATA_DIR = '/home/adam/.openclaw/workspace/orderbook_data'
OCR_DIR = '/home/adam/.openclaw/workspace/skills/local-ocr'  # OCR输出
OUTPUT_DIR = '/home/adam/.openclaw/workspace/stock-monitor/analysis'
os.makedirs(OUTPUT_DIR, exist_ok=True)

STOCKS = {
    '002594': '比亚迪',
    '601899': '紫金矿业',
    '601345': '工业妇联',
    '300274': '阳光电源',
    '300308': '中际旭创',
    '300502': '新易盛',
    '300394': '天孚通信',
    '002281': '光迅科技',
}

def load_orderbook_data(stock_code, date_str=None):
    """加载盘口数据"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')
    pattern = f'{DATA_DIR}/{stock_code}_{date_str}_*.json'
    files = sorted(glob.glob(pattern))
    data = []
    for f in files:
        with open(f, 'r') as fp:
            data.append(json.load(fp))
    return data

def calc_wall_metrics(snapshot):
    """
    计算单个快照的价格墙指标
    返回: dict of metrics
    """
    bids = snapshot.get('bids', [])
    asks = snapshot.get('asks', [])
    
    if not bids or not asks:
        return None
    
    # 卖墙：卖1-卖5的总量和均价
    ask_volume = sum(a[1] for a in asks[:5])
    ask_avg_price = sum(a[0] * a[1] for a in asks[:5]) / ask_volume if ask_volume > 0 else 0
    
    # 买墙：买1-买5的总量和均价
    bid_volume = sum(b[1] for b in bids[:5])
    bid_avg_price = sum(b[0] * b[1] for b in bids[:5]) / bid_volume if bid_volume > 0 else 0
    
    # 买卖力量对比
    total_volume = ask_volume + bid_volume
    buy_sell_ratio = bid_volume / total_volume if total_volume > 0 else 0.5
    
    # 价格墙厚度（最近5档的价格跨度）
    ask_wall_thickness = asks[-1][0] - asks[0][0] if len(asks) > 1 else 0
    bid_wall_thickness = bids[0][0] - bids[-1][0] if len(bids) > 1 else 0
    
    return {
        'ask_volume_5': ask_volume,
        'bid_volume_5': bid_volume,
        'buy_sell_ratio': buy_sell_ratio,
        'ask_avg_price': ask_avg_price,
        'bid_avg_price': bid_avg_price,
        'ask_wall_thickness': ask_wall_thickness,
        'bid_wall_thickness': bid_wall_thickness,
        'spread': asks[0][0] - bids[0][0] if bids and asks else 0,
    }

def analyze_wall_changes(snapshots):
    """
    分析价格墙变化序列
    找出：墙突变、大单涌入、惯性启动点
    """
    metrics_series = []
    for snap in snapshots:
        m = calc_wall_metrics(snap)
        if m:
            m['timestamp'] = snap.get('timestamp', '')
            metrics_series.append(m)
    
    if len(metrics_series) < 2:
        return []
    
    changes = []
    for i in range(1, len(metrics_series)):
        prev = metrics_series[i-1]
        curr = metrics_series[i]
        
        change = {
            'timestamp': curr['timestamp'],
            'bid_volume_change': curr['bid_volume_5'] - prev['bid_volume_5'],
            'ask_volume_change': curr['ask_volume_5'] - prev['ask_volume_5'],
            'buy_sell_ratio_change': curr['buy_sell_ratio'] - prev['buy_sell_ratio'],
            'spread_change': curr['spread'] - prev['spread'],
            'bid_wall_thickness_change': curr['bid_wall_thickness'] - prev['bid_wall_thickness'],
            'ask_wall_thickness_change': curr['ask_wall_thickness'] - prev['ask_wall_thickness'],
        }
        
        # 标记异常变化（踩油门信号候选）
        signals = []
        
        # 买墙突然加厚（主力托盘）
        if change['bid_volume_change'] > 500:
            signals.append('BUY_WALL_BUILD')
        
        # 卖墙突然撤薄（主力拉升准备）
        if change['ask_volume_change'] < -500:
            signals.append('SELL_WALL_REMOVE')
        
        # 买卖比突然失衡（单边行情启动）
        if abs(change['buy_sell_ratio_change']) > 0.15:
            signals.append('IMBALANCE_SPIKE')
        
        # 价差突变（流动性变化）
        if abs(change['spread_change']) > 0.05:
            signals.append('SPREAD_SHIFT')
        
        change['signals'] = signals
        changes.append(change)
    
    return changes

def detect_acceleration_pattern(changes):
    """
    识别踩油门模式
    典型模式：
    1. 卖墙撤除 → 惯性启动（25分钟窗口）
    2. 买墙加厚 → 主力护盘
    3. 买卖比骤变 → 方向选择
    """
    patterns = []
    
    for i, c in enumerate(changes):
        # 模式1：卖墙撤除+买墙不变 → 要拉
        if 'SELL_WALL_REMOVE' in c['signals'] and c['bid_volume_change'] < 100:
            patterns.append({
                'time': c['timestamp'],
                'type': 'PULL_UP_PREPARE',
                'confidence': 'high',
                'detail': f"卖墙撤除{abs(c['ask_volume_change'])}手，买墙稳定"
            })
        
        # 模式2：买墙加厚+卖墙不变 → 要托
        if 'BUY_WALL_BUILD' in c['signals'] and c['ask_volume_change'] > -100:
            patterns.append({
                'time': c['timestamp'],
                'type': 'SUPPORT_BUILD',
                'confidence': 'medium',
                'detail': f"买墙加厚{c['bid_volume_change']}手，卖墙稳定"
            })
        
        # 模式3：买卖比骤变 → 方向选择
        if 'IMBALANCE_SPIKE' in c['signals']:
            direction = '买方占优' if c['buy_sell_ratio_change'] > 0 else '卖方占优'
            patterns.append({
                'time': c['timestamp'],
                'type': 'DIRECTION_CHOICE',
                'confidence': 'high',
                'detail': f"买卖比骤变{c['buy_sell_ratio_change']:.3f}，{direction}"
            })
    
    return patterns

def generate_analysis_report(stock_code, stock_name, changes, patterns):
    """生成分析报告"""
    report = f'# {stock_code} {stock_name} 踩油门分析\n\n'
    report += f'分析时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n'
    report += f'数据点: {len(changes)} 个时间窗口\n'
    report += f'踩油门信号: {len(patterns)} 个\n\n'
    
    if patterns:
        report += '## 踩油门信号\n\n'
        for p in patterns:
            emoji = '🔴' if p['type'] == 'PULL_UP_PREPARE' else '🟢' if p['type'] == 'SUPPORT_BUILD' else '⚡'
            report += f"{emoji} **{p['time']}** - {p['type']} (置信度: {p['confidence']})\n"
            report += f"  {p['detail']}\n\n"
    
    # 统计信号类型
    signal_counts = defaultdict(int)
    for p in patterns:
        signal_counts[p['type']] += 1
    
    if signal_counts:
        report += '## 信号统计\n\n'
        for sig_type, count in signal_counts.items():
            report += f"- {sig_type}: {count} 次\n"
    
    return report

if __name__ == '__main__':
    print("踩油门盘后分析")
    print("=" * 50)
    
    today = datetime.now().strftime('%Y%m%d')
    
    for code, name in STOCKS.items():
        print(f'\n分析 {code} {name}...')
        data = load_orderbook_data(code, today)
        print(f'  今日数据: {len(data)} 条')
        
        if len(data) >= 2:
            changes = analyze_wall_changes(data)
            patterns = detect_acceleration_pattern(changes)
            report = generate_analysis_report(code, name, changes, patterns)
            
            report_path = f'{OUTPUT_DIR}/{code}_{name}_{today}.md'
            with open(report_path, 'w') as f:
                f.write(report)
            print(f'  报告: {report_path}')
            print(f'  踩油门信号: {len(patterns)} 个')
        else:
            print(f'  数据不足，需要至少2个时间点的数据')
    
    print('\n分析完成。')
