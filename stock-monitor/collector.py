#!/usr/bin/env python3
"""
踩油门指标研究 - 数据采集与分析
目标：从盘口数据中找到主力踩油门的数学标志
"""

import json
import os
import glob
from datetime import datetime, timedelta
from collections import defaultdict

DATA_DIR = '/home/adam/.openclaw/workspace/orderbook_data'
OUTPUT_DIR = '/home/adam/.openclaw/workspace/stock-monitor/analysis'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 研究标的
STOCKS = {
    '002594': '比亚迪',
    '601899': '紫金矿业',
    '601345': '工业妇联',
    '300274': '阳光电源',
}

def load_stock_data(stock_code, days=90):
    """加载指定股票的盘口数据"""
    pattern = f'{DATA_DIR}/{stock_code}_*.json'
    files = sorted(glob.glob(pattern))
    
    # 按日期筛选
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
    files = [f for f in files if os.path.basename(f).split('_')[1] >= cutoff]
    
    data = []
    for f in files:
        with open(f, 'r') as fp:
            record = json.load(fp)
            record['_file'] = os.path.basename(f)
            data.append(record)
    
    return data

def calc_price_wall_changes(data):
    """
    计算价格墙变化指标
    - 卖墙撤单速度
    - 买墙撤单速度  
    - 墙体厚度变化率
    """
    if len(data) < 2:
        return []
    
    changes = []
    for i in range(1, len(data)):
        prev = data[i-1]
        curr = data[i]
        
        # 提取买卖盘数据（根据实际数据结构调整）
        # 这里用占位符，实际字段名取决于orderbook数据格式
        change = {
            'timestamp': curr.get('timestamp', ''),
            'sell_wall_change': None,  # 卖墙变化量
            'buy_wall_change': None,   # 买墙变化量
            'large_order_net': None,   # 大单净流入
            'small_order_ratio': None, # 小单占比
            'price_momentum': None,    # 价格动量
        }
        changes.append(change)
    
    return changes

def find_acceleration_signals(changes):
    """
    识别踩油门信号
    - 大单突然涌入的时刻
    - 价格墙突然撤除的时刻
    - 小单占比骤降的时刻（散户卖，主力买）
    """
    signals = []
    for c in changes:
        # TODO: 根据实际数据定义信号阈值
        pass
    return signals

def generate_report(stock_code, stock_name, signals):
    """生成分析报告"""
    report = f'# {stock_code} {stock_name} 踩油门信号分析\n\n'
    report += f'分析时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n'
    report += f'数据量: {len(signals)} 个信号\n\n'
    
    if signals:
        report += '## 信号列表\n'
        for s in signals[:50]:  # 最多显示50个
            report += f"- {s}\n"
    else:
        report += '暂无数据，需要先采集盘口数据。\n'
    
    return report

if __name__ == '__main__':
    print("踩油门指标分析器")
    print("=" * 50)
    
    for code, name in STOCKS.items():
        print(f'\n分析 {code} {name}...')
        data = load_stock_data(code)
        print(f'  加载 {len(data)} 条记录')
        
        if len(data) >= 2:
            changes = calc_price_wall_changes(data)
            signals = find_acceleration_signals(changes)
            report = generate_report(code, name, signals)
            
            report_path = f'{OUTPUT_DIR}/{code}_{name}_analysis.md'
            with open(report_path, 'w') as f:
                f.write(report)
            print(f'  报告已生成: {report_path}')
        else:
            print(f'  数据不足，需要更多盘口数据')
    
    print('\n完成。')
