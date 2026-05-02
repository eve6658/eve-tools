#!/usr/bin/env python3
"""
A股政策市量化选股工具 v1.0
基于今日交流成果：政策市分类 + 资金流向 + 技术指标
"""

import akshare as ak
import pandas as pd
import numpy as np
import sys
import time
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════
# 第一层：政策市行业分类
# ═══════════════════════════════════════════════════

POLICY_AVOID = [
    '化肥', '种植业', '养殖业', '农业综合', '饲料', '林业',
    '渔业', '农产品加工', '粮食', '电力', '燃气', '水务',
    '公共交通', '公路铁路'
]

POLICY_BOOST = [
    '半导体', '光伏设备', '电池', '风电设备', '计算机设备',
    '软件开发', '通信设备', '医疗器械', '生物制品',
    '航空装备', '航天装备', '军工电子'
]

MARKET_PRICE = [
    '化学原料', '化学制品', '化学纤维', '非金属矿物',
    '有色金属', '钢铁', '煤炭开采', '石油开采',
    '航运港口', '造纸', '化纤', '玻璃玻纤',
    '工业金属', '贵金属', '稀有金属'
]

def classify_industry(industry):
    """政策市行业分类"""
    if pd.isna(industry):
        return '未知'
    for kw in POLICY_AVOID:
        if kw in str(industry):
            return '政策稳价型'
    for kw in POLICY_BOOST:
        if kw in str(industry):
            return '政策鼓励型'
    for kw in MARKET_PRICE:
        if kw in str(industry):
            return '市场定价型'
    return '中性'


# ═══════════════════════════════════════════════════
# 第二层：技术指标计算
# ═══════════════════════════════════════════════════

def calc_indicators(df):
    """计算核心指标"""
    df = df.copy()
    
    # 均线
    df['MA5'] = df['收盘'].rolling(5).mean()
    df['MA10'] = df['收盘'].rolling(10).mean()
    df['MA20'] = df['收盘'].rolling(20).mean()
    df['MA60'] = df['收盘'].rolling(60).mean()
    
    # MACD (12,26,9)
    ema12 = df['收盘'].ewm(span=12, adjust=False).mean()
    ema26 = df['收盘'].ewm(span=26, adjust=False).mean()
    df['DIF'] = ema12 - ema26
    df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['MACD'] = 2 * (df['DIF'] - df['DEA'])
    
    # 乖离率
    df['BIAS'] = ((df['收盘'] - df['MA20']) / df['MA20']) * 100
    
    # 量比 (当日成交量 / 5日均量)
    df['VOL_MA5'] = df['成交量'].rolling(5).mean()
    df['量比'] = df['成交量'] / df['VOL_MA5']
    
    # 成交额 (亿元)
    if '成交额' in df.columns:
        df['成交额亿'] = df['成交额'] / 1e8
    
    return df


def get_fund_flow(code, name):
    """
    获取个股资金流向数据（东方财富）
    返回：dict 包含主力净流入、超大单、大单、中单、小单
    """
    try:
        # 判断市场
        if code.startswith('6') or code.startswith('9'):
            market = 'sh'
        elif code.startswith('0') or code.startswith('3'):
            market = 'sz'
        elif code.startswith('8') or code.startswith('4'):
            market = 'bj'
        else:
            return None
        
        df_flow = ak.stock_individual_fund_flow(stock=code, market=market)
        if df_flow is None or len(df_flow) == 0:
            return None
        
        latest = df_flow.iloc[-1]
        return {
            '主力净流入(万)': round(latest['主力净流入-净额'] / 1e4, 2),
            '主力净占比(%)': round(latest['主力净流入-净占比'], 2),
            '超大单净流入(万)': round(latest['超大单净流入-净额'] / 1e4, 2),
            '大单净流入(万)': round(latest['大单净流入-净额'] / 1e4, 2),
            '中单净流入(万)': round(latest['中单净流入-净额'] / 1e4, 2),
            '小单净流入(万)': round(latest['小单净流入-净额'] / 1e4, 2),
            '资金日期': str(latest['日期']),
        }
    except Exception:
        return None


def detect_signal(df):
    """
    检测买入信号（改进版 + 资金流向增强）
    条件：收盘>MA20 + 刚突破(昨日≤MA20) + MACD>0 + 量比>2 + 乖离率<12%
    + 额外条件：MA5>MA10 (确认短期趋势)
    + 资金流向：主力净流入占比>0（加分项，非硬性条件）
    """
    if len(df) < 25:
        return False, [], {}
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    reasons = []
    flow_info = {}
    
    # 基础条件
    if latest['收盘'] > latest['MA20']:
        reasons.append('收盘>MA20')
    else:
        return False, reasons, flow_info
    
    # 刚突破
    if prev['收盘'] <= prev['MA20']:
        reasons.append('刚突破MA20')
    else:
        return False, reasons, flow_info
    
    # MACD
    if latest['MACD'] > 0:
        reasons.append('MACD>0')
    else:
        return False, reasons, flow_info
    
    # 量比
    if latest['量比'] > 2.0:
        reasons.append(f'量比{latest["量比"]:.1f}')
    elif latest['量比'] > 1.5:
        reasons.append(f'量比{latest["量比"]:.1f}(弱)')
    else:
        return False, reasons, flow_info
    
    # 乖离率
    bias = abs(latest['BIAS'])
    if bias < 12:
        reasons.append(f'乖离率{latest["BIAS"]:.1f}%')
    else:
        return False, reasons, flow_info
    
    # 短期趋势确认
    if latest['MA5'] > latest['MA10']:
        reasons.append('MA5>MA10')
    
    return True, reasons, flow_info


# ═══════════════════════════════════════════════════
# 主程序
# ═══════════════════════════════════════════════════

def run_screen():
    """运行选股器"""
    print('=' * 70)
    print('🔍 A股政策市量化选股工具 v1.0')
    print(f'📅 {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 70)
    
    # 获取全市场行情
    print('\n📥 获取全市场行情数据...')
    try:
        df_realtime = ak.stock_zh_a_spot_em()
        print(f'  获取 {len(df_realtime)} 只股票')
    except Exception as e:
        print(f'❌ 获取行情失败: {e}')
        return
    
    # 基础筛选
    print('\n🔍 第一步：基础筛选')
    
    # 过滤条件
    df_screen = df_realtime[
        (df_realtime['成交额'] > 3e8) &  # 成交额>3亿
        (df_realtime['涨跌幅'] > 0) &     # 今日上涨
        (df_realtime['涨跌幅'] < 9.5) &    # 非涨停
        (df_realtime['换手率'] > 2) &      # 换手率>2%
        (~df_realtime['名称'].str.contains('ST|退', na=False))  # 排除ST
    ].copy()
    
    print(f'  基础筛选后: {len(df_screen)} 只')
    
    # 行业分类
    print('\n🔍 第二步：政策市分类')
    if '所属行业' in df_screen.columns:
        df_screen['行业类型'] = df_screen['所属行业'].apply(classify_industry)
    else:
        df_screen['行业类型'] = '未知'
    
    # 优先选择市场定价型和政策鼓励型
    df_priority = df_screen[
        df_screen['行业类型'].isin(['市场定价型', '政策鼓励型'])
    ].copy()
    
    print(f'  市场定价型+政策鼓励型: {len(df_priority)} 只')
    
    if len(df_priority) == 0:
        print('⚠️ 无符合条件的标的，使用全部基础筛选结果')
        df_priority = df_screen.copy()
    
    # 第三步：技术指标验证
    print('\n🔍 第三步：技术指标验证')
    print('  逐只下载日线数据并分析（可能需要几分钟）...')
    
    signal_candidates = []  # 技术信号命中的
    checked = 0
    errors = 0
    
    for _, row in df_priority.head(100).iterrows():  # 最多检查100只
        code = row['代码']
        name = row['名称']
        
        try:
            # 获取历史数据
            df_hist = ak.stock_zh_a_hist(
                symbol=code, 
                period="daily", 
                adjust="qfq",
                start_date=(datetime.now() - timedelta(days=120)).strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d')
            )
            
            if df_hist is None or len(df_hist) < 25:
                continue
            
            # 计算指标
            df_hist = calc_indicators(df_hist)
            
            # 检测信号
            has_signal, reasons, _ = detect_signal(df_hist)
            
            if has_signal:
                latest = df_hist.iloc[-1]
                signal_candidates.append({
                    '代码': code,
                    '名称': name,
                    '行业类型': row.get('行业类型', '未知'),
                    '最新价': round(latest['收盘'], 2),
                    '涨幅(%)': round(row.get('涨跌幅', 0), 2),
                    '量比': round(latest.get('量比', 0), 2),
                    'MACD': round(latest.get('MACD', 0), 4),
                    '乖离率(%)': round(latest.get('BIAS', 0), 2),
                    '信号': ' | '.join(reasons),
                })
            
            checked += 1
            time.sleep(0.3)  # 限速，避免被反爬
            
        except Exception as e:
            errors += 1
            if errors > 10:
                print(f'  ⚠️ 错误过多，跳过剩余')
                break
            continue
        
        # 进度
        if checked % 10 == 0:
            print(f'  已检查 {checked} 只，发现 {len(signal_candidates)} 个技术信号')
    
    # 第四步：资金流向验证
    print(f'\n🔍 第四步：资金流向验证（{len(signal_candidates)} 只信号股）')
    if signal_candidates:
        print('  查询资金流向数据...')
    
    results = []
    for item in signal_candidates:
        code = item['代码']
        flow = get_fund_flow(code, item['名称'])
        if flow:
            item.update(flow)
            # 主力净流入占比标记
            main_pct = flow.get('主力净占比(%)', 0)
            if main_pct > 3:
                item['资金信号'] = '🟢 主力强势流入'
            elif main_pct > 0:
                item['资金信号'] = '🔵 主力小幅流入'
            elif main_pct > -3:
                item['资金信号'] = '🟡 主力流出(弱)'
            else:
                item['资金信号'] = '🔴 主力流出'
        else:
            item['主力净流入(万)'] = 'N/A'
            item['主力净占比(%)'] = 'N/A'
            item['资金信号'] = '⚠️ 无数据'
        
        results.append(item)
        time.sleep(0.2)
    
    # 输出结果
    print(f'\n{"=" * 70}')
    print(f'📊 选股结果')
    print(f'{"=" * 70}')
    
    if results:
        df_result = pd.DataFrame(results)
        
        # 按主力净流入占比排序（有资金数据的优先）
        if '主力净占比(%)' in df_result.columns:
            df_result['_sort'] = pd.to_numeric(df_result['主力净占比(%)'], errors='coerce')
            df_result = df_result.sort_values('_sort', ascending=False, na_position='last')
            df_result = df_result.drop(columns=['_sort'])
        
        print(f'\n共发现 {len(results)} 个符合信号的标的：\n')
        
        for _, row in df_result.iterrows():
            print(f'  🎯 {row["代码"]} {row["名称"]}')
            print(f'     行业: {row["行业类型"]} | 价格: {row["最新价"]} | 涨幅: {row["涨幅(%)"]}%')
            print(f'     量比: {row["量比"]} | MACD: {row["MACD"]} | 乖离率: {row["乖离率(%)"]}%')
            print(f'     资金: {row.get("资金信号","")}')
            main_inflow = row.get("主力净流入(万)", "N/A")
            main_pct = row.get("主力净占比(%)", "N/A")
            print(f'     主力净流入: {main_inflow}万 (占比{main_pct}%)')
            print(f'     信号: {row["信号"]}')
            print()
        
        # 保存结果
        output_file = f'/home/adam/.openclaw/workspace/选股结果_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
        df_result.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f'📁 结果已保存: {output_file}')
    else:
        print('\n  今日无符合条件的买入信号。')
        print('  提示：好机会值得等待，不要为了交易而交易。')
    
    # 政策市风险提示
    print(f'\n{"=" * 70}')
    print('⚠️ 风险提示')
    print(f'{"=" * 70}')
    print('  1. 本工具仅为技术指标初筛，不构成投资建议')
    print('  2. 入选标的需进一步验证：资金流向、筹码分布、行业政策')
    print('  3. 政策稳价型行业已被过滤，但仍需关注政策变化')
    print('  4. 严格执行止损纪律：单票亏损超15%无条件卖出')
    print('  5. 请先用模拟盘验证后再实盘操作')


if __name__ == '__main__':
    run_screen()
