#!/usr/bin/env python3
"""
小单占比分析工具 — 用于判断主力行为（吸筹/出货/散户主导）
基于《A股不对称战场操盘手册》第二章：小单占比阈值

使用方法:
  方式1: 手动输入数据（交互模式）
  方式2: python3 small_order_analysis.py --csv <逐笔成交.csv>
  方式3: 直接调用 analyze() 函数

数据来源: 财达股市通Level-2 逐笔成交截图/导出
"""

import sys
import csv
import os

# ============================================================
# 经验阈值（手册量化，可调）
# ============================================================
SMALL_ORDER_THRESHOLD = 100  # 小单定义：<100手

# 吸筹信号阈值
ACCUM_SELL_SMALL_PCT = 80.0   # 卖盘小单占比 > 80%
ACCUM_BUY_SMALL_PCT = 30.0    # 买盘小单占比 < 30%

# 出货信号阈值
DUMP_BUY_SMALL_PCT = 80.0     # 买盘小单占比 > 80%
DUMP_SELL_SMALL_PCT = 30.0    # 卖盘小单占比 < 30%

# 散户主导阈值
RETAIL_BOTH_PCT = 70.0        # 买卖双方小单占比均 > 70%


def analyze(orders: list[dict], threshold: int = SMALL_ORDER_THRESHOLD) -> dict:
    """
    分析逐笔成交数据的小单占比
    
    参数:
        orders: list of dict, 每个dict包含:
            {
                'price': float,      # 成交价
                'volume': int,       # 成交量(手)
                'direction': str,    # 买卖方向: 'B'(主动买入/红色) 或 'S'(主动卖出/绿色)
                'time': str,         # 成交时间 (可选)
            }
        threshold: int, 小单定义阈值(手), 默认100
    
    返回:
        dict: 分析结果
    """
    if not orders:
        return {'error': '无数据'}
    
    # 分买盘/卖盘
    buy_orders = [o for o in orders if o.get('direction', '').upper() == 'B']
    sell_orders = [o for o in orders if o.get('direction', '').upper() == 'S']
    
    # 总量
    total_vol = sum(o['volume'] for o in orders)
    total_amt = sum(o['price'] * o['volume'] for o in orders)
    buy_vol = sum(o['volume'] for o in buy_orders)
    sell_vol = sum(o['volume'] for o in sell_orders)
    buy_amt = sum(o['price'] * o['volume'] for o in buy_orders)
    sell_amt = sum(o['price'] * o['volume'] for o in sell_orders)
    
    # 小单统计
    buy_small = [o for o in buy_orders if o['volume'] < threshold]
    sell_small = [o for o in sell_orders if o['volume'] < threshold]
    
    buy_small_vol = sum(o['volume'] for o in buy_small)
    sell_small_vol = sum(o['volume'] for o in sell_small)
    buy_small_amt = sum(o['price'] * o['volume'] for o in buy_small)
    sell_small_amt = sum(o['price'] * o['volume'] for o in sell_small)
    
    # 占比计算
    buy_small_pct = (buy_small_vol / buy_vol * 100) if buy_vol > 0 else 0
    sell_small_pct = (sell_small_vol / sell_vol * 100) if sell_vol > 0 else 0
    total_small_vol = buy_small_vol + sell_small_vol
    total_small_pct = (total_small_vol / total_vol * 100) if total_vol > 0 else 0
    
    # 大单统计（>= threshold）
    buy_large = [o for o in buy_orders if o['volume'] >= threshold]
    sell_large = [o for o in sell_orders if o['volume'] >= threshold]
    buy_large_avg = (sum(o['volume'] for o in buy_large) / len(buy_large)) if buy_large else 0
    sell_large_avg = (sum(o['volume'] for o in sell_large) / len(sell_large)) if sell_large else 0
    
    # 每笔平均
    buy_avg = (buy_vol / len(buy_orders)) if buy_orders else 0
    sell_avg = (sell_vol / len(sell_orders)) if sell_orders else 0
    
    # 主力行为判断
    signal = '不明'
    confidence = '低'
    reason = []
    
    if sell_small_pct > ACCUM_SELL_SMALL_PCT and buy_small_pct < ACCUM_BUY_SMALL_PCT:
        signal = '🔴 吸筹（压盘吸货）'
        confidence = '高'
        reason.append(f'卖盘小单{sell_small_pct:.1f}% > {ACCUM_SELL_SMALL_PCT}%（散户恐慌抛售）')
        reason.append(f'买盘小单{buy_small_pct:.1f}% < {ACCUM_BUY_SMALL_PCT}%（主力大单承接）')
        if buy_large_avg > 0:
            reason.append(f'买盘大单平均每笔{buy_large_avg:.0f}手 vs 卖盘大单{sell_large_avg:.0f}手')
    
    elif buy_small_pct > DUMP_BUY_SMALL_PCT and sell_small_pct < DUMP_SELL_SMALL_PCT:
        signal = '🟢 出货（拉高出货）'
        confidence = '高'
        reason.append(f'买盘小单{buy_small_pct:.1f}% > {DUMP_BUY_SMALL_PCT}%（散户追高买入）')
        reason.append(f'卖盘小单{sell_small_pct:.1f}% < {DUMP_SELL_SMALL_PCT}%（主力大单卖出）')
    
    elif buy_small_pct > RETAIL_BOTH_PCT and sell_small_pct > RETAIL_BOTH_PCT:
        signal = '⚪ 散户主导'
        confidence = '中'
        reason.append(f'买盘小单{buy_small_pct:.1f}%，卖盘小单{sell_small_pct:.1f}%')
        reason.append('双方都是散户，主力未参与')
    
    elif sell_small_pct > 60 and buy_small_pct < 50:
        signal = '🟡 偏吸筹'
        confidence = '中'
        reason.append(f'卖盘小单偏高{sell_small_pct:.1f}%，买盘小单偏低{buy_small_pct:.1f}%')
    
    elif buy_small_pct > 60 and sell_small_pct < 50:
        signal = '🟡 偏出货'
        confidence = '中'
        reason.append(f'买盘小单偏高{buy_small_pct:.1f}%，卖盘小单偏低{sell_small_pct:.1f}%')
    
    else:
        signal = '⚪ 多空平衡'
        confidence = '低'
        reason.append(f'买盘小单{buy_small_pct:.1f}%，卖盘小单{sell_small_pct:.1f}%')
    
    # 操作建议
    if '吸筹' in signal:
        suggestion = '主力在吸筹，持有/逢低加仓。止损位看铁底是否破。'
    elif '出货' in signal:
        suggestion = '主力在出货，减仓/清仓。不要追高。'
    elif '散户主导' in signal:
        suggestion = '无主力参与，观望。等主力进场信号。'
    else:
        suggestion = '信号不明确，按当前趋势操作，严格止损。'
    
    return {
        '小单阈值(手)': threshold,
        '总成交(手)': total_vol,
        '总成交额(元)': round(total_amt, 0),
        '买盘总量(手)': buy_vol,
        '卖盘总量(手)': sell_vol,
        '买卖比': round(buy_vol / sell_vol, 2) if sell_vol > 0 else '∞',
        '买盘小单占比': round(buy_small_pct, 1),
        '卖盘小单占比': round(sell_small_pct, 1),
        '总小单占比': round(total_small_pct, 1),
        '买盘每笔平均(手)': round(buy_avg, 1),
        '卖盘每笔平均(手)': round(sell_avg, 1),
        '买盘大单平均每笔(手)': round(buy_large_avg, 1),
        '卖盘大单平均每笔(手)': round(sell_large_avg, 1),
        '买盘大单数': len(buy_large),
        '卖盘大单数': len(sell_large),
        '主力行为': signal,
        '判断依据': reason,
        '操作建议': suggestion,
    }


def print_result(result: dict):
    """美化打印分析结果"""
    print("\n" + "=" * 50)
    print("  📊 小单占比分析报告")
    print("=" * 50)
    
    if 'error' in result:
        print(f"  ❌ {result['error']}")
        return
    
    print(f"\n  📈 成交概况")
    print(f"  ├─ 总成交: {result['总成交(手)']:,}手")
    print(f"  ├─ 总成交额: {result['总成交额(元)']:,.0f}元")
    print(f"  ├─ 买盘: {result['买盘总量(手)']:,}手  卖盘: {result['卖盘总量(手)']:,}手")
    print(f"  └─ 买卖比: {result['买卖比']}")
    
    print(f"\n  🔍 小单占比（阈值<{result['小单阈值(手)']}手')'")
    print(f"  ├─ 卖盘小单占比: {result['卖盘小单占比']}% {'🔴' if result['卖盘小单占比'] > 80 else ''}")
    print(f"  ├─ 买盘小单占比: {result['买盘小单占比']}% {'🟢' if result['买盘小单占比'] < 30 else ''}")
    print(f"  └─ 总小单占比: {result['总小单占比']}%")
    
    print(f"\n  📊 每笔均量")
    print(f"  ├─ 买盘平均每笔: {result['买盘每笔平均(手)']}手")
    print(f"  ├─ 卖盘平均每笔: {result['卖盘每笔平均(手)']}手")
    print(f"  ├─ 买盘大单(>{result['小单阈值(手)']}手)均量: {result['买盘大单平均每笔(手)']}手 ({result['买盘大单数']}笔)")
    print(f"  └─ 卖盘大单(>{result['小单阈值(手)']}手)均量: {result['卖盘大单平均每笔(手)']}手 ({result['卖盘大单数']}笔)")
    
    print(f"\n  🎯 主力行为判断")
    print(f"  └─ {result['主力行为']}")
    for line in result['判断依据']:
        print(f"     · {line}")
    
    print(f"\n  💡 操作建议")
    print(f"  └─ {result['操作建议']}")
    print("=" * 50)


def interactive_mode():
    """交互模式：手动输入逐笔成交数据"""
    print("=" * 50)
    print("  📊 小单占比分析工具（交互模式）")
    print("=" * 50)
    print("\n输入逐笔成交数据，每行一条，格式: 时间,价格,成交量(手),方向(B=买入/S=卖出)")
    print("输入完毕后按回车结束\n")
    
    orders = []
    while True:
        line = input(">>> ").strip()
        if not line:
            break
        parts = line.replace('，', ',').split(',')
        if len(parts) >= 4:
            orders.append({
                'time': parts[0].strip(),
                'price': float(parts[1].strip()),
                'volume': int(parts[2].strip()),
                'direction': parts[3].strip().upper(),
            })
        elif len(parts) == 3:
            orders.append({
                'time': '',
                'price': float(parts[0].strip()),
                'volume': int(parts[1].strip()),
                'direction': parts[2].strip().upper(),
            })
        else:
            print("  格式错误，请重试")
    
    if orders:
        result = analyze(orders)
        print_result(result)
        return result
    else:
        print("  无数据")


def csv_mode(filepath: str):
    """CSV模式：从CSV文件读取逐笔成交数据"""
    orders = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            order = {
                'time': row.get('time', row.get('时间', '')),
                'price': float(row.get('price', row.get('价格', 0))),
                'volume': int(row.get('volume', row.get('成交量', row.get('手数', 0)))),
                'direction': row.get('direction', row.get('方向', 'B')).strip().upper(),
            }
            orders.append(order)
    
    if orders:
        result = analyze(orders)
        print_result(result)
        return result
    else:
        print("  CSV无数据")


def demo_mode():
    """演示模式：用模拟数据展示功能"""
    print("\n  🎮 演示模式 - 使用模拟数据\n")
    
    # 模拟吸筹场景（鹭燕 09:26数据）
    demo_accum = [
        # 买盘：少量大单
        {'price': 16.48, 'volume': 5202, 'direction': 'B', 'time': '09:26:01'},
        {'price': 16.48, 'volume': 8121, 'direction': 'B', 'time': '09:26:01'},
        # 卖盘：大量小单
        {'price': 16.49, 'volume': 21, 'direction': 'S', 'time': '09:26:01'},
        {'price': 16.49, 'volume': 225, 'direction': 'S', 'time': '09:26:02'},
        {'price': 16.49, 'volume': 5, 'direction': 'S', 'time': '09:26:02'},
        {'price': 16.49, 'volume': 5, 'direction': 'S', 'time': '09:26:03'},
        {'price': 16.49, 'volume': 17, 'direction': 'S', 'time': '09:26:03'},
        {'price': 16.49, 'volume': 173, 'direction': 'S', 'time': '09:26:04'},
        {'price': 16.49, 'volume': 5, 'direction': 'S', 'time': '09:26:04'},
        {'price': 16.49, 'volume': 9, 'direction': 'S', 'time': '09:26:05'},
        {'price': 16.49, 'volume': 2, 'direction': 'S', 'time': '09:26:05'},
        {'price': 16.49, 'volume': 29, 'direction': 'S', 'time': '09:26:06'},
        {'price': 16.49, 'volume': 20, 'direction': 'S', 'time': '09:26:06'},
        {'price': 16.49, 'volume': 3, 'direction': 'S', 'time': '09:26:07'},
        {'price': 16.49, 'volume': 23, 'direction': 'S', 'time': '09:26:07'},
        {'price': 16.49, 'volume': 5, 'direction': 'S', 'time': '09:26:08'},
        {'price': 16.49, 'volume': 18, 'direction': 'S', 'time': '09:26:08'},
    ]
    
    print("=" * 50)
    print("  场景1: 鹭燕 09:26 被动吸筹（模拟）")
    print("=" * 50)
    result = analyze(demo_accum)
    print_result(result)
    
    # 模拟出货场景
    demo_dump = [
        # 买盘：全是散户小单
        {'price': 17.50, 'volume': 5, 'direction': 'B'},
        {'price': 17.50, 'volume': 8, 'direction': 'B'},
        {'price': 17.50, 'volume': 12, 'direction': 'B'},
        {'price': 17.50, 'volume': 3, 'direction': 'B'},
        {'price': 17.50, 'volume': 20, 'direction': 'B'},
        {'price': 17.50, 'volume': 7, 'direction': 'B'},
        {'price': 17.50, 'volume': 15, 'direction': 'B'},
        {'price': 17.50, 'volume': 2, 'direction': 'B'},
        {'price': 17.50, 'volume': 10, 'direction': 'B'},
        {'price': 17.50, 'volume': 6, 'direction': 'B'},
        # 卖盘：主力大单
        {'price': 17.49, 'volume': 500, 'direction': 'S'},
        {'price': 17.49, 'volume': 800, 'direction': 'S'},
        {'price': 17.49, 'volume': 300, 'direction': 'S'},
    ]
    
    print("\n\n  场景2: 主力出货（模拟）")
    print("=" * 50)
    result2 = analyze(demo_dump)
    print_result(result2)


# ============================================================
# CSV模板生成
# ============================================================
def generate_template():
    """生成CSV模板"""
    template = """time,price,volume,direction
09:26:01,16.48,5202,B
09:26:01,16.48,8121,B
09:26:02,16.49,225,S
09:26:02,16.49,5,S
09:26:03,16.49,17,S"""
    path = '/home/adam/.openclaw/workspace/逐笔成交模板.csv'
    with open(path, 'w', encoding='utf-8-sig') as f:
        f.write(template)
    print(f"  CSV模板已生成: {path}")
    print("  格式: time(时间), price(价格), volume(手数), direction(B=买入/S=卖出)")


# ============================================================
# 主程序
# ============================================================
if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--csv' and len(sys.argv) > 2:
            csv_mode(sys.argv[2])
        elif sys.argv[1] == '--demo':
            demo_mode()
        elif sys.argv[1] == '--template':
            generate_template()
        elif sys.argv[1] == '--help':
            print("用法:")
            print("  python3 small_order_analysis.py              # 交互模式")
            print("  python3 small_order_analysis.py --demo       # 演示模式")
            print("  python3 small_order_analysis.py --csv <file> # CSV模式")
            print("  python3 small_order_analysis.py --template   # 生成CSV模板")
        else:
            print("未知参数，使用 --help 查看用法")
    else:
        # 默认交互模式
        demo = input("是否先看演示？(y/n): ").strip().lower()
        if demo == 'y':
            demo_mode()
        interactive_mode()
