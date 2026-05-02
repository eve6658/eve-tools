#!/usr/bin/env python3
"""600666 奥瑞德 实时分析"""
import sys
sys.path.insert(0, '.')
from scripts.stock_screener import get_fund_flow, calc_indicators
import akshare as ak
from datetime import datetime, timedelta

code = '600666'
name = '奥瑞德'

print(f"{'='*60}")
print(f"📊 {code} {name} 综合分析")
print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"{'='*60}")

# 1. 获取日线数据
print("\n📥 获取日线数据...")
df = ak.stock_zh_a_hist(
    symbol=code,
    period="daily",
    adjust="qfq",
    start_date=(datetime.now() - timedelta(days=120)).strftime('%Y%m%d'),
    end_date=datetime.now().strftime('%Y%m%d')
)
print(f"  获取 {len(df)} 个交易日数据")

# 2. 计算技术指标
df = calc_indicators(df)
latest = df.iloc[-1]
prev = df.iloc[-2]

print(f"\n{'─'*60}")
print("📈 技术指标")
print(f"{'─'*60}")
print(f"  最新价: {latest['收盘']}  涨跌: {df.iloc[-1]['收盘'] - df.iloc[-2]['收盘']:.2f}")
print(f"  MA5:  {latest['MA5']:.3f}")
print(f"  MA10: {latest['MA10']:.3f}")
print(f"  MA20: {latest['MA20']:.3f}")
print(f"  MA60: {latest['MA60']:.3f}")
print(f"  MACD DIF:  {latest['DIF']:.4f}")
print(f"  MACD DEA:  {latest['DEA']:.4f}")
print(f"  MACD柱:    {latest['MACD']:.4f}")
print(f"  量比:      {latest['量比']:.2f}")
print(f"  乖离率:    {latest['BIAS']:.2f}%")

# 3. 均线排列
print(f"\n{'─'*60}")
print("📐 均线排列")
print(f"{'─'*60}")
ma5 = latest['MA5']
ma10 = latest['MA10']
ma20 = latest['MA20']
ma60 = latest['MA60']
price = latest['收盘']

if ma5 > ma10 > ma20 > ma60:
    print("  🟢 多头排列 (MA5>MA10>MA20>MA60)")
elif ma5 < ma10 < ma20 < ma60:
    print("  🔴 空头排列 (MA5<MA10<MA20<MA60)")
else:
    print(f"  🟡 交织排列")
    print(f"    价格{'>' if price > ma5 else '<'}MA5 {'✓' if price > ma5 else '✗'}")
    print(f"    MA5{'>' if ma5 > ma10 else '<'}MA10 {'✓' if ma5 > ma10 else '✗'}")
    print(f"    MA10{'>' if ma10 > ma20 else '<'}MA20 {'✓' if ma10 > ma20 else '✗'}")

# 4. 近5日走势
print(f"\n{'─'*60}")
print("📊 近5个交易日")
print(f"{'─'*60}")
for i in range(-5, 0):
    r = df.iloc[i]
    print(f"  {r['日期']}  收:{r['收盘']:.3f}  涨跌:{r.get('涨跌幅', 0):.2f}%  量比:{r.get('量比', 0):.2f}  成交额:{r.get('成交额', 0)/1e8:.2f}亿")

# 5. 资金流向
print(f"\n{'─'*60}")
print("💰 资金流向（东方财富）")
print(f"{'─'*60}")
flow = get_fund_flow(code, name)
if flow:
    print(f"  数据日期: {flow['资金日期']}")
    print(f"  主力净流入: {flow['主力净流入(万)']}万 (占比 {flow['主力净占比(%)']}%)")
    print(f"    超大单:   {flow['超大单净流入(万)']}万")
    print(f"    大单:     {flow['大单净流入(万)']}万")
    print(f"    中单:     {flow['中单净流入(万)']}万")
    print(f"    小单:     {flow['小单净流入(万)']}万")
    
    main_pct = flow['主力净占比(%)']
    if main_pct > 5:
        print(f"\n  🟢 主力强势流入，占比{main_pct}%")
    elif main_pct > 0:
        print(f"\n  🔵 主力小幅流入，占比{main_pct}%")
    elif main_pct > -5:
        print(f"\n  🟡 主力小幅流出，占比{main_pct}%")
    else:
        print(f"\n  🔴 主力明显流出，占比{main_pct}%")
    
    # 近5日资金趋势
    try:
        if code.startswith('6'):
            market = 'sh'
        else:
            market = 'sz'
        df_flow_all = ak.stock_individual_fund_flow(stock=code, market=market)
        if df_flow_all is not None and len(df_flow_all) >= 5:
            recent = df_flow_all.tail(5)
            print(f"\n  近5日主力净流入趋势:")
            total_main = 0
            for _, row in recent.iterrows():
                amt = round(row['主力净流入-净额']/1e4, 2)
                total_main += amt
                pct = round(row['主力净流入-净占比'], 2)
                print(f"    {row['日期']}  主力: {amt:>10}万 ({pct:>6.2f}%)")
            print(f"    ─────────────────────────")
            print(f"    5日合计: {round(total_main, 2)}万")
    except:
        pass
else:
    print("  ⚠️ 获取资金流向数据失败")

# 6. 综合判断
print(f"\n{'='*60}")
print("🧠 主力动向综合判断")
print(f"{'='*60}")

signals = []

# 价格与均线
if price > ma20:
    signals.append("✅ 价格站上MA20")
else:
    signals.append("❌ 价格跌破MA20")

# MACD
if latest['MACD'] > 0:
    signals.append("✅ MACD柱为正（多头动能）")
else:
    signals.append("❌ MACD柱为负（空头动能）")

if latest['DIF'] > latest['DEA']:
    signals.append("✅ DIF>DEA（金叉状态）")
else:
    signals.append("❌ DIF<DEA（死叉状态）")

# 量能
if latest['量比'] > 1.5:
    signals.append(f"✅ 放量（量比{latest['量比']:.2f}）")
elif latest['量比'] > 0.8:
    signals.append(f"➡️ 平量（量比{latest['量比']:.2f}）")
else:
    signals.append(f"❌ 缩量（量比{latest['量比']:.2f}）")

for s in signals:
    print(f"  {s}")

print(f"\n{'─'*60}")
