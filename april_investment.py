#!/usr/bin/env python3
"""拉取4月投资建议所需数据 - 煤化工/油气核心标的"""

import tushare as ts
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

ts.set_token('e0dc18fc3ef8b9aa6a77b3e02a98f909097a237d7aa3cf82bfe1ad19')
pro = ts.pro_api()

# 核心标的池
targets = {
    # 煤化工
    '600989.SH': '宝丰能源',
    '600426.SH': '华鲁恒升',
    '601898.SH': '中煤能源',
    '002648.SZ': '卫星化学',
    '601011.SH': '宝泰隆',
    # 油气开采
    '601857.SH': '中国石油',
    '600938.SH': '中国海油',
    '601808.SH': '中海油服',
    '600583.SH': '海油工程',
    # 炼化
    '002493.SZ': '荣盛石化',
    '600346.SH': '恒力石化',
    # 化工品龙头
    '600309.SH': '万华化学',
    '000830.SZ': '鲁西化工',
}

codes = list(targets.keys())
codes_str = ','.join(codes)

print("=" * 80)
print("📊 4月投资建议 - 核心标的数据采集")
print("=" * 80)

# 1. 近期日线数据 (近30个交易日)
print("\n📈 拉取近30个交易日日线...")
df_daily = pro.daily(ts_code=codes_str, start_date='20260215', end_date='20260328',
                     fields='ts_code,trade_date,open,high,low,close,vol,amount,pct_chg')
if df_daily is not None:
    print(f"  获取 {len(df_daily)} 条记录")

# 2. 获取最新交易日行情快照
print("\n📊 获取最新交易日行情...")
df_rt = pro.daily(ts_code=codes_str, start_date='20260327', end_date='20260328',
                  fields='ts_code,trade_date,open,high,low,close,vol,amount,pct_chg,turnover_rate')

# 3. 获取PE/PB等估值指标
print("\n📊 获取估值数据...")
df_val = None
try:
    df_val = pro.daily_basic(ts_code=codes_str, trade_date='20260328',
                             fields='ts_code,trade_date,pe_ttm,pb,ps_ttm,dv_ttm,total_mv,circ_mv')
except Exception as e:
    print(f"  ⚠️ daily_basic无权限，跳过估值数据: {e}")
    df_val = None

# 4. 拉取年初至今的数据计算年初至今涨幅
print("\n📈 拉取年初至今数据...")
df_ytd = pro.daily(ts_code=codes_str, start_date='20260101', end_date='20260328',
                   fields='ts_code,trade_date,close')

# 分析每只股票
results = []
for code in codes:
    name = targets[code]
    
    # 近期数据
    df_stock = df_daily[df_daily['ts_code'] == code].sort_values('trade_date') if df_daily is not None else pd.DataFrame()
    
    if len(df_stock) == 0:
        continue
    
    latest = df_stock.iloc[-1]
    first = df_stock.iloc[0]
    
    # 近30日涨跌幅
    pct_30d = (latest['close'] - first['close']) / first['close'] * 100
    
    # 近5日涨跌幅
    df_5d = df_stock.tail(5)
    if len(df_5d) >= 2:
        pct_5d = (df_5d.iloc[-1]['close'] - df_5d.iloc[0]['close']) / df_5d.iloc[0]['close'] * 100
    else:
        pct_5d = 0
    
    # YTD
    df_ytd_stock = df_ytd[df_ytd['ts_code'] == code].sort_values('trade_date') if df_ytd is not None else pd.DataFrame()
    if len(df_ytd_stock) >= 2:
        ytd = (df_ytd_stock.iloc[-1]['close'] - df_ytd_stock.iloc[0]['close']) / df_ytd_stock.iloc[0]['close'] * 100
    else:
        ytd = 0
    
    # 波动率 (近20日收益率标准差 * sqrt(252))
    if len(df_stock) >= 20:
        returns = df_stock['pct_chg'].tail(20).values / 100
        volatility = returns.std() * (252 ** 0.5) * 100
    else:
        volatility = 0
    
    # 量比 (近5日均量 / 近20日均量)
    if len(df_stock) >= 20:
        vol_5d = df_stock['vol'].tail(5).mean()
        vol_20d = df_stock['vol'].tail(20).mean()
        vol_ratio = vol_5d / vol_20d if vol_20d > 0 else 1
    else:
        vol_ratio = 1
    
    # 最高价/最低价近20日
    high_20d = df_stock['high'].tail(20).max()
    low_20d = df_stock['low'].tail(20).min()
    close = latest['close']
    # 距离20日高点回撤
    drawdown = (close - high_20d) / high_20d * 100
    
    results.append({
        '代码': code,
        '名称': name,
        '最新收盘': close,
        '5日涨幅(%)': round(pct_5d, 2),
        '30日涨幅(%)': round(pct_30d, 2),
        '年初至今(%)': round(ytd, 2),
        '20日最高': high_20d,
        '20日最低': low_20d,
        '距高点回撤(%)': round(drawdown, 2),
        '年化波动率(%)': round(volatility, 2),
        '量比(5/20)': round(vol_ratio, 2),
    })

df_analysis = pd.DataFrame(results)

# 合并估值数据
if df_val is not None and len(df_val) > 0:
    df_val_clean = df_val[['ts_code', 'pe_ttm', 'pb', 'dv_ttm', 'total_mv']].copy()
    df_val_clean.columns = ['代码', 'PE(TTM)', 'PB', '股息率(%)', '总市值(亿)']
    df_val_clean['总市值(亿)'] = df_val_clean['总市值(亿)'] / 1e8
    df_analysis = df_analysis.merge(df_val_clean, on='代码', how='left')

# 输出
print("\n" + "=" * 120)
print("📊 核心标的一览（按30日涨幅排序）")
print("=" * 120)
df_sorted = df_analysis.sort_values('30日涨幅(%)', ascending=False)
cols_display = ['代码', '名称', '最新收盘', '5日涨幅(%)', '30日涨幅(%)', '年初至今(%)', 
                '距高点回撤(%)', '年化波动率(%)', '量比(5/20)', 'PE(TTM)', 'PB', '股息率(%)', '总市值(亿)']
available_cols = [c for c in cols_display if c in df_sorted.columns]
print(df_sorted[available_cols].to_string(index=False))

# 导出CSV
df_sorted.to_csv('/home/adam/.openclaw/workspace/april_targets_data.csv', index=False, encoding='utf-8-sig')
print(f"\n📁 数据已导出: april_targets_data.csv")
print("✅ 数据采集完成")
