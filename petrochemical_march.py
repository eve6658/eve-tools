#!/usr/bin/env python3
"""A股石油化工板块 2026年3月行情分析 - 挑选涨幅前10"""

import tushare as ts
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

ts.set_token('e0dc18fc3ef8b9aa6a77b3e02a98f909097a237d7aa3cf82bfe1ad19')
pro = ts.pro_api()

# 1. 获取石油化工行业成分股 (申万行业分类 - 石油石化)
# 申万一级行业: C30 石油石化
print("=" * 60)
print("📊 A股石油化工板块 2026年3月行情分析")
print("=" * 60)

# 先尝试用申万行业分类获取石油石化成分股
print("\n🔍 正在获取石油化工行业成分股...")

# 尝试多种方式获取石油化工板块股票
dfs = []

# 方法1: 申万行业
try:
    df_sw = pro.index_member_all(index_code='801010.SI')  # 申万石油石化
    if df_sw is not None and len(df_sw) > 0:
        dfs.append(df_sw)
        print(f"  ✅ 申万石油石化(801010.SI): {len(df_sw)} 只")
except Exception as e:
    print(f"  ⚠️ 申万石油石化失败: {e}")

# 方法2: 东方财富行业 - 石油化工
try:
    df_east = pro.index_member_all(index_code='CI005001.WI')  # 万得石油化工
    if df_east is not None and len(df_east) > 0:
        dfs.append(df_east)
        print(f"  ✅ 万得石油化工(CI005001.WI): {len(df_east)} 只")
except Exception as e:
    print(f"  ⚠️ 万得石油化工失败: {e}")

# 方法3: 用板块成分股接口
try:
    df_ths = pro.ths_member(industry='石油化工')
    if df_ths is not None and len(df_ths) > 0:
        dfs.append(df_ths)
        print(f"  ✅ 同花顺石油化工: {len(df_ths)} 只")
except Exception as e:
    print(f"  ⚠️ 同花顺石油化工失败: {e}")

# 方法4: 直接用 stock_basic 按行业筛选
try:
    df_basic = pro.stock_basic(exchange='', list_status='L', 
                               fields='ts_code,name,industry,market')
    if df_basic is not None:
        # 筛选石油化工相关行业
        keywords = ['石油', '石化', '化工', '炼化', '油气']
        mask = df_basic['industry'].str.contains('|'.join(keywords), na=False) | \
               df_basic['name'].str.contains('|'.join(keywords), na=False)
        df_industry = df_basic[mask]
        if len(df_industry) > 0:
            print(f"  ✅ 按行业关键词筛选: {len(df_industry)} 只")
            # 只保留石油化工核心企业，排除纯化工
            core_keywords = ['石油', '石化', '炼化', '油气', '中油', '中海']
            core_mask = df_industry['industry'].str.contains('|'.join(core_keywords), na=False) | \
                        df_industry['name'].str.contains('|'.join(core_keywords), na=False)
            df_core = df_industry[core_mask]
            if len(df_core) > 0:
                dfs.append(df_core)
                print(f"  ✅ 石油石化核心企业: {len(df_core)} 只")
except Exception as e:
    print(f"  ⚠️ 行业筛选失败: {e}")

if not dfs:
    print("\n❌ 无法获取石油化工板块成分股，使用已知核心股票列表")
    # 石油石化核心A股上市公司
    known_codes = [
        '601857.SH', '600028.SH', '601808.SH', '600583.SH', '601898.SH',
        '600688.SH', '600028.SH', '000059.SZ', '002493.SZ', '002629.SZ',
        '600871.SH', '600968.SH', '603619.SH', '600232.SH', '600546.SH',
        '000096.SZ', '002207.SZ', '002476.SZ', '002554.SZ', '600989.SH',
        '601001.SH', '000698.SZ', '002221.SZ', '600346.SH', '600339.SH',
        '002267.SZ', '600759.SH', '002278.SZ', '002490.SZ', '002778.SZ',
    ]
    df_codes = pd.DataFrame({'ts_code': known_codes})
    dfs.append(df_codes)

# 合并所有来源
df_all = pd.concat(dfs, ignore_index=True)
# 统一代码列名
code_col = None
for col in ['ts_code', 'code', 'stock_code']:
    if col in df_all.columns:
        code_col = col
        break
if code_col != 'ts_code':
    df_all = df_all.rename(columns={code_col: 'ts_code'})

codes = df_all['ts_code'].unique().tolist()
print(f"\n📋 共获取 {len(codes)} 只石油化工相关股票")

# 2. 获取3月份行情数据 (2026-03-01 至 2026-03-28)
print("\n📈 正在获取2026年3月行情数据...")

start_date = '20260301'
end_date = '20260328'

all_data = []
batch_size = 50
for i in range(0, len(codes), batch_size):
    batch = codes[i:i+batch_size]
    codes_str = ','.join(batch)
    try:
        df_daily = pro.daily(ts_code=codes_str, start_date=start_date, end_date=end_date,
                             fields='ts_code,trade_date,open,high,low,close,vol,amount,chg,pct_chg')
        if df_daily is not None and len(df_daily) > 0:
            all_data.append(df_daily)
            print(f"  ✅ 批次 {i//batch_size + 1}: {len(df_daily)} 条记录")
    except Exception as e:
        print(f"  ⚠️ 批次 {i//batch_size + 1} 失败: {e}")

if not all_data:
    print("\n❌ 无法获取行情数据")
    exit(1)

df_merged = pd.concat(all_data, ignore_index=True)
print(f"\n📊 共获取 {len(df_merged)} 条日线记录，涉及 {df_merged['ts_code'].nunique()} 只股票")

# 3. 计算3月各项指标
print("\n🧮 正在计算各项指标...")

results = []
for code, group in df_merged.groupby('ts_code'):
    group = group.sort_values('trade_date')
    
    if len(group) < 5:  # 至少5个交易日才纳入
        continue
    
    # 月初开盘价（第一个交易日的open）
    first_day = group.iloc[0]
    last_day = group.iloc[-1]
    
    # 月涨跌幅
    pct_chg_month = (last_day['close'] - first_day['open']) / first_day['open'] * 100
    
    # 月内最高/最低
    high_month = group['high'].max()
    low_month = group['low'].min()
    
    # 振幅
    amplitude = (high_month - low_month) / first_day['open'] * 100
    
    # 平均成交量（万股）
    avg_vol = group['vol'].mean() / 10000 if 'vol' in group.columns else 0
    
    # 总成交额（亿元）
    total_amount = group['amount'].sum() / 1e8 if 'amount' in group.columns else 0
    
    # 上涨天数 / 下跌天数
    if 'pct_chg' in group.columns:
        up_days = (group['pct_chg'] > 0).sum()
        down_days = (group['pct_chg'] < 0).sum()
        flat_days = (group['pct_chg'] == 0).sum()
    else:
        up_days = down_days = flat_days = 0
    
    # 月末收盘
    close月末 = last_day['close']
    
    results.append({
        'ts_code': code,
        '月初开盘': first_day['open'],
        '月末收盘': close月末,
        '月涨跌幅(%)': round(pct_chg_month, 2),
        '月内最高': high_month,
        '月内最低': low_month,
        '振幅(%)': round(amplitude, 2),
        '上涨天数': up_days,
        '下跌天数': down_days,
        '平盘天数': flat_days,
        '日均成交额(亿)': round(total_amount / max(len(group), 1), 2),
        '总成交额(亿)': round(total_amount, 2),
        '交易天数': len(group),
    })

df_results = pd.DataFrame(results)

# 4. 获取股票名称
print("\n🏷️ 正在获取股票信息...")
try:
    df_info = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name,industry')
    df_results = df_results.merge(df_info[['ts_code', 'name', 'industry']], on='ts_code', how='left')
except:
    pass

# 5. 按月涨跌幅排序，输出前10
df_sorted = df_results.sort_values('月涨跌幅(%)', ascending=False).reset_index(drop=True)
df_top10 = df_sorted.head(10)

print("\n" + "=" * 90)
print("🏆 2026年3月 A股石油化工板块 涨幅TOP 10")
print("=" * 90)

display_cols = ['ts_code', 'name', '月涨跌幅(%)', '月末收盘', '振幅(%)', '上涨天数', '下跌天数', '日均成交额(亿)', '总成交额(亿)', '交易天数']
available_cols = [c for c in display_cols if c in df_top10.columns]
print(df_top10[available_cols].to_string(index=False))

# 6. 板块整体统计
print("\n" + "=" * 60)
print("📊 板块整体统计")
print("=" * 60)
total = len(df_results)
up_count = (df_results['月涨跌幅(%)'] > 0).sum()
down_count = (df_results['月涨跌幅(%)'] < 0).sum()
flat_count = (df_results['月涨跌幅(%)'] == 0).sum()
avg_return = df_results['月涨跌幅(%)'].mean()
median_return = df_results['月涨跌幅(%)'].median()
max_return = df_results['月涨跌幅(%)'].max()
min_return = df_results['月涨跌幅(%)'].min()

print(f"  石油化工板块股票总数: {total} 只")
print(f"  3月上涨: {up_count} 只 ({up_count/total*100:.1f}%)")
print(f"  3月下跌: {down_count} 只 ({down_count/total*100:.1f}%)")
print(f"  3月平盘: {flat_count} 只 ({flat_count/total*100:.1f}%)")
print(f"  平均涨幅: {avg_return:.2f}%")
print(f"  中位数涨幅: {median_return:.2f}%")
print(f"  最大涨幅: {max_return:.2f}%")
print(f"  最大跌幅: {min_return:.2f}%")

# 7. 倒序看跌幅前5
df_bottom5 = df_sorted.tail(5).sort_values('月涨跌幅(%)', ascending=True)
print(f"\n📉 3月跌幅前5:")
for _, row in df_bottom5.iterrows():
    name = row.get('name', row['ts_code'])
    print(f"  {row['ts_code']} {name:8s}  涨跌幅: {row['月涨跌幅(%)']:+.2f}%")

# 8. 导出完整结果
output_file = '/home/adam/.openclaw/workspace/petrochemical_march_2026.csv'
df_sorted.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"\n📁 完整结果已导出: {output_file}")

print("\n✅ 分析完成！")
