#!/usr/bin/env python3
"""
散户参与度指标计算器
基于L2逐笔成交数据，计算散户参与人数和行为特征

支持三种统计粒度：
  --minute  按分钟统计（实时监控，默认）
  --day     按日统计（当日汇总）
  --week    按周统计（跨日汇总，需多日数据文件）

输入：ocr_logic.py 输出的逐笔成交JSON
输出：散户参与度报告（JSON + 人类可读）
"""

import os, sys, json, re
from collections import Counter, defaultdict
from datetime import datetime

# ========== 散户判定阈值 ==========
RETAIL_MAX_VOL = 100       # ≤100手为散户
TINY_ORDER_MAX = 10        # ≤10手为超级小散
INST_MIN_VOL = 500         # ≥500手为机构嫌疑
REPEAT_THRESHOLD = 3       # 同模式出现≥3次视为同一人

# ========== 核心计算 ==========
def classify_orders(trades):
    """订单分类：散户/中户/机构"""
    retail = []    # 1-100手
    mid = []       # 101-499手
    inst = []      # 500+手
    for t in trades:
        v = t['v']
        if v <= RETAIL_MAX_VOL:
            retail.append(t)
        elif v < INST_MIN_VOL:
            mid.append(t)
        else:
            inst.append(t)
    return retail, mid, inst

def estimate_participants(orders, avg_trades_per_person=3):
    """估算参与人数 = 总笔数 / 平均每人交易笔数"""
    if not orders:
        return 0
    return max(1, len(orders) // avg_trades_per_person)

def detect_repeat_patterns(trades):
    """检测重复交易模式（同一人反复下单）"""
    patterns = Counter()
    for t in trades:
        key = (t['p'], t['v'], t['a'])
        patterns[key] += 1
    repeats = {k: v for k, v in patterns.items() if v >= REPEAT_THRESHOLD}
    return repeats

def price_distribution(trades):
    """价格分布统计"""
    dist = Counter(round(t['p'], 2) for t in trades)
    return dict(sorted(dist.items(), key=lambda x: -x[1]))

def volume_distribution(trades):
    """手数分布统计"""
    ranges = [
        (1, 10, '1-10手'),
        (11, 50, '11-50手'),
        (51, 100, '51-100手'),
        (101, 500, '101-500手'),
        (501, 1000, '501-1000手'),
        (1001, 99999, '1000+手')
    ]
    result = {}
    for lo, hi, label in ranges:
        cnt = len([t for t in trades if lo <= t['v'] <= hi])
        if cnt > 0:
            result[label] = cnt
    return result

def calc_retail_ratio(trades):
    """散户占比（小单占比）"""
    retail, mid, inst = classify_orders(trades)
    total = len(trades)
    if total == 0:
        return 0
    return round(len(retail) / total * 100, 2)

def calc_participation_index(trades):
    """
    散户参与度指数（0-100）
    综合指标：小单占比 × 价格集中度 × 交易频率
    """
    if not trades:
        return 0
    
    # 1. 小单占比（权重40%）
    retail_ratio = calc_retail_ratio(trades)
    
    # 2. 价格集中度（权重30%）：散户越集中在某个价位，参与度越高
    price_dist = price_distribution(trades)
    if price_dist:
        top_price_ratio = list(price_dist.values())[0] / len(trades) * 100
    else:
        top_price_ratio = 0
    
    # 3. 超级小散占比（权重30%）：≤10手的占比
    tiny_count = len([t for t in trades if t['v'] <= TINY_ORDER_MAX])
    tiny_ratio = tiny_count / len(trades) * 100
    
    # 综合指数
    index = retail_ratio * 0.4 + top_price_ratio * 0.3 + tiny_ratio * 0.3
    return round(min(100, index), 1)

def interpret_index(index):
    """解读参与度指数"""
    if index >= 80:
        return "🔴 极高（散户密集，控制者可能撤墙洗盘）"
    elif index >= 60:
        return "🟡 偏高（散户较多，注意风险）"
    elif index >= 40:
        return "🟢 中性（散户适中）"
    elif index >= 20:
        return "🔵 偏低（散户较少，筹码真空可能突破）"
    else:
        return "⚪ 极低（机构主导，散户几乎不参与）"

# ========== 分钟统计 ==========
def minute_analysis(trades):
    """按分钟聚合统计"""
    by_minute = defaultdict(list)
    for t in trades:
        minute = t['t'][:5]  # "13:16"
        by_minute[minute].append(t)
    
    results = []
    for minute in sorted(by_minute.keys()):
        mt = by_minute[minute]
        retail, mid, inst = classify_orders(mt)
        results.append({
            'minute': minute,
            'total_trades': len(mt),
            'retail_trades': len(retail),
            'mid_trades': len(mid),
            'inst_trades': len(inst),
            'retail_ratio': calc_retail_ratio(mt),
            'participation_index': calc_participation_index(mt),
            'top_price': price_distribution(mt),
            'vol_dist': volume_distribution(mt),
            'buy_count': len([t for t in mt if t['a'] == 'Buy']),
            'sell_count': len([t for t in mt if t['a'] == 'Sell']),
        })
    return results

# ========== 日统计 ==========
def day_analysis(trades):
    """当日汇总统计"""
    retail, mid, inst = classify_orders(trades)
    
    return {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time_range': f"{trades[-1]['t']} - {trades[0]['t']}" if trades else "",
        'total_trades': len(trades),
        'retail_trades': len(retail),
        'mid_trades': len(mid),
        'inst_trades': len(inst),
        'retail_ratio': calc_retail_ratio(trades),
        'participation_index': calc_participation_index(trades),
        'interpretation': interpret_index(calc_participation_index(trades)),
        'price_distribution': price_distribution(trades),
        'volume_distribution': volume_distribution(trades),
        'buy_count': len([t for t in trades if t['a'] == 'Buy']),
        'sell_count': len([t for t in trades if t['a'] == 'Sell']),
        'sell_ratio': round(len([t for t in trades if t['a'] == 'Sell']) / len(trades) * 100, 1) if trades else 0,
        'repeat_patterns': [
            {'price': k[0], 'vol': k[1], 'side': k[2], 'count': v}
            for k, v in sorted(detect_repeat_patterns(trades).items(), key=lambda x: -x[1])[:10]
        ]
    }

# ========== 周统计 ==========
def week_analysis(data_files):
    """
    按周统计：合并多个日数据文件
    data_files: list of JSON files (每日逐笔数据)
    """
    all_trades = []
    for f in data_files:
        with open(f) as fh:
            all_trades.extend(json.load(fh))
    
    # 按日分组
    by_day = defaultdict(list)
    # 如果数据没有日期，用文件名推断
    for f in data_files:
        day = os.path.basename(f).split('_')[0]  # 假设格式 YYYY-MM-DD_xxx.json
        with open(f) as fh:
            by_day[day].extend(json.load(fh))
    
    daily_summaries = []
    for day in sorted(by_day.keys()):
        dt = by_day[day]
        daily_summaries.append({
            'date': day,
            'total_trades': len(dt),
            'retail_ratio': calc_retail_ratio(dt),
            'participation_index': calc_participation_index(dt),
        })
    
    return {
        'week': f"{daily_summaries[0]['date']} ~ {daily_summaries[-1]['date']}" if daily_summaries else "",
        'total_trades': len(all_trades),
        'avg_participation_index': round(sum(d['participation_index'] for d in daily_summaries) / len(daily_summaries), 1) if daily_summaries else 0,
        'daily': daily_summaries
    }

# ========== 人类可读报告 ==========
def format_report(result, mode='minute'):
    """格式化输出报告"""
    lines = []
    
    if mode == 'minute':
        lines.append("📊 散户参与度 — 按分钟统计")
        lines.append("=" * 50)
        for m in result:
            idx = m['participation_index']
            bar = '█' * int(idx / 5) + '░' * (20 - int(idx / 5))
            lines.append(f"\n⏱ {m['minute']} | {m['total_trades']}笔 | 散户{m['retail_trades']}笔({m['retail_ratio']}%)")
            lines.append(f"  参与度: [{bar}] {idx}/100")
            lines.append(f"  买卖: 买{m['buy_count']} / 卖{m['sell_count']}")
            top_prices = list(m['top_price'].items())[:3]
            lines.append(f"  热点价位: {', '.join(f'{p:.2f}({c}笔)' for p, c in top_prices)}")
    
    elif mode == 'day':
        lines.append("📊 散户参与度 — 日统计")
        lines.append("=" * 50)
        r = result
        idx = r['participation_index']
        bar = '█' * int(idx / 5) + '░' * (20 - int(idx / 5))
        lines.append(f"📅 {r['date']} | {r['time_range']}")
        lines.append(f"总笔数: {r['total_trades']}")
        lines.append(f"散户: {r['retail_trades']}笔 ({r['retail_ratio']}%)")
        lines.append(f"中户: {r['mid_trades']}笔 | 机构: {r['inst_trades']}笔")
        lines.append(f"买卖: 买{r['buy_count']} / 卖{r['sell_count']} (卖比{r['sell_ratio']}%)")
        lines.append(f"\n参与度指数: [{bar}] {idx}/100")
        lines.append(f"解读: {r['interpretation']}")
        
        if r.get('repeat_patterns'):
            lines.append(f"\n🔁 重复模式（疑似同一人）:")
            for p in r['repeat_patterns'][:5]:
                lines.append(f"  {p['price']:.2f} {p['vol']}手 {p['side']}: {p['count']}次")
    
    return '\n'.join(lines)

# ========== 主函数 ==========
def main():
    if len(sys.argv) < 2:
        print("用法: python3 retail_participation.py <逐笔JSON文件> [--minute|--day|--week file1 file2 ...]")
        print("  --minute: 按分钟统计（默认）")
        print("  --day:    按日统计")
        print("  --week:   按周统计（后接多个日JSON文件）")
        sys.exit(1)
    
    mode = 'minute'
    if '--day' in sys.argv:
        mode = 'day'
        sys.argv.remove('--day')
    elif '--week' in sys.argv:
        mode = 'week'
        sys.argv.remove('--week')
    elif '--minute' in sys.argv:
        sys.argv.remove('--minute')
    
    if mode == 'week':
        # 周统计：所有参数都是文件
        data_files = sys.argv[1:]
        result = week_analysis(data_files)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("\n" + format_report(result, mode))
    else:
        # 读取单个JSON文件
        json_file = sys.argv[1]
        with open(json_file) as f:
            trades = json.load(f)
        
        if mode == 'minute':
            result = minute_analysis(trades)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("\n" + format_report(result, mode))
        else:
            result = day_analysis(trades)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("\n" + format_report(result, mode))

if __name__ == "__main__":
    main()
