import tushare as ts
import os

token = os.environ.get('TUSHARE_TOKEN', 'e0dc18fc3ef8b9aa6a77b3e02a98f909097a237d7aa3cf82bfe1ad19')
pro = ts.pro_api(token)

# 获取今日A股涨跌数据
df = pro.daily(trade_date='20260402')

if df is None or df.empty:
    print('NO_DATA')
else:
    print(f'总股票数: {len(df)}')
    
    # 涨幅前20
    top = df.nlargest(20, 'pct_chg')[['ts_code', 'name', 'close', 'pct_chg', 'vol', 'amount']]
    print('\n=== 涨幅榜 TOP20 ===')
    for _, r in top.iterrows():
        print(f"{r['ts_code']} {r['name']} 收盘:{r['close']} 涨幅:{r['pct_chg']:.2f}% 成交额:{r['amount']/10000:.0f}万")
    
    # 跌幅前20
    bottom = df.nsmallest(20, 'pct_chg')[['ts_code', 'name', 'close', 'pct_chg', 'vol', 'amount']]
    print('\n=== 跌幅榜 TOP20 ===')
    for _, r in bottom.iterrows():
        print(f"{r['ts_code']} {r['name']} 收盘:{r['close']} 跌幅:{r['pct_chg']:.2f}% 成交额:{r['amount']/10000:.0f}万")
    
    # 涨跌统计
    up = len(df[df['pct_chg'] > 0])
    down = len(df[df['pct_chg'] < 0])
    flat = len(df[df['pct_chg'] == 0])
    limit_up = len(df[df['pct_chg'] >= 9.9])
    limit_down = len(df[df['pct_chg'] <= -9.9])
    
    print(f'\n=== 涨跌统计 ===')
    print(f'上涨: {up} 下跌: {down} 平盘: {flat}')
    print(f'涨停: {limit_up} 跌停: {limit_down}')
    
    # 成交额最大的20只
    top_vol = df.nlargest(20, 'amount')[['ts_code', 'name', 'close', 'pct_chg', 'amount']]
    print('\n=== 成交额 TOP20 ===')
    for _, r in top_vol.iterrows():
        print(f"{r['ts_code']} {r['name']} 收盘:{r['close']} 涨跌:{r['pct_chg']:.2f}% 成交额:{r['amount']/100000000:.2f}亿")
