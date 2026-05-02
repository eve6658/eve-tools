#!/usr/bin/env python3
"""
A股基本面事实调查工具
数据源：akshare（免费）+ 东方财富网页
"""

import akshare as ak
import pandas as pd
import sys
import json
from datetime import datetime, timedelta

pd.set_option('display.max_rows', 50)
pd.set_option('display.width', 120)
pd.set_option('display.float_format', '{:.2f}'.format)


def get_stock_basic(symbol: str) -> dict:
    """获取股票基本信息"""
    try:
        df = ak.stock_individual_info_em(symbol=symbol)
        info = dict(zip(df['item'], df['value']))
        return info
    except Exception as e:
        return {"error": str(e)}


def get_valuation_data(symbol: str) -> dict:
    """获取估值数据"""
    results = {}
    try:
        df = ak.stock_zh_a_spot_em()
        stock = df[df['代码'] == symbol]
        if len(stock) > 0:
            row = stock.iloc[0]
            results['price'] = float(row['最新价']) if pd.notna(row['最新价']) else None
            results['pe_ttm'] = float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else None
            results['pb'] = float(row['市净率']) if pd.notna(row['市净率']) else None
            results['total_mv'] = float(row['总市值']) if pd.notna(row['总市值']) else None
            results['circ_mv'] = float(row['流通市值']) if pd.notna(row['流通市值']) else None
            results['name'] = row['名称']
            results['turnover_rate'] = float(row['换手率']) if pd.notna(row['换手率']) else None
            results['volume_ratio'] = float(row['量比']) if pd.notna(row['量比']) else None
    except Exception as e:
        results['valuation_error'] = str(e)
    return results


def get_historical_price(symbol: str, days: int = 60) -> pd.DataFrame:
    """获取历史行情"""
    try:
        end = datetime.now().strftime('%Y%m%d')
        start = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start, end_date=end, adjust="qfq")
        return df.tail(days)
    except Exception as e:
        print(f"获取历史行情失败: {e}")
        return pd.DataFrame()


def get_yjbb(symbol: str) -> dict:
    """从业绩报表获取最新财务数据"""
    try:
        df = ak.stock_yjbb_em()
        row = df[df['股票代码'] == symbol]
        if len(row) > 0:
            r = row.iloc[0]
            return {
                '每股收益': r.get('每股收益'),
                '营业总收入': r.get('营业总收入-营业总收入'),
                '营收同比': r.get('营业总收入-同比增长'),
                '净利润': r.get('净利润-净利润'),
                '净利同比': r.get('净利润-同比增长'),
                '报告期': r.get('报告期'),
            }
    except:
        pass
    return {}


def get_balance_sheet(symbol: str) -> pd.DataFrame:
    """获取资产负债表"""
    try:
        df = ak.stock_financial_report_sina(stock=symbol, symbol='资产负债表')
        return df.head(4)
    except:
        return pd.DataFrame()


def get_profit_report(symbol: str) -> pd.DataFrame:
    """获取利润表"""
    try:
        df = ak.stock_financial_report_sina(stock=symbol, symbol='利润表')
        return df.head(4)
    except:
        return pd.DataFrame()


def get_money_flow(symbol: str) -> pd.DataFrame:
    """获取个股资金流向"""
    try:
        market = "sh" if symbol.startswith('6') else "sz"
        df = ak.stock_individual_fund_flow(stock=symbol, market=market)
        return df.tail(10)
    except Exception as e:
        print(f"获取资金流向失败: {e}")
        return pd.DataFrame()


def full_analysis(symbol: str):
    """执行完整的事实调查"""
    print(f"\n{'='*60}")
    print(f"📊 事实调查报告：{symbol}")
    print(f"{'='*60}")

    # 1. 基本信息
    print(f"\n【1. 公司画像】")
    basic = get_stock_basic(symbol)
    if "error" not in basic:
        for k, v in basic.items():
            print(f"  {k}: {v}")
    else:
        print(f"  获取失败: {basic['error']}")

    # 2. 估值数据
    print(f"\n【2. 当前估值】")
    val = get_valuation_data(symbol)
    if "valuation_error" not in val:
        print(f"  名称: {val.get('name', 'N/A')}")
        print(f"  最新价: {val.get('price', 'N/A')}")
        print(f"  PE(TTM): {val.get('pe_ttm', 'N/A')}")
        print(f"  PB: {val.get('pb', 'N/A')}")
        print(f"  总市值: {val.get('total_mv', 'N/A')}")
        print(f"  流通市值: {val.get('circ_mv', 'N/A')}")
        print(f"  换手率: {val.get('turnover_rate', 'N/A')}")
    else:
        print(f"  获取失败: {val['valuation_error']}")

    # 3. 资金流向
    print(f"\n【3. 近期资金流向（10日）】")
    mf = get_money_flow(symbol)
    if len(mf) > 0:
        print(mf.to_string(index=False))
    else:
        print("  暂无数据")

    # 4. 历史行情
    print(f"\n【4. 近60日行情概况】")
    hp = get_historical_price(symbol, 60)
    if len(hp) > 0:
        print(f"  区间: {hp['日期'].iloc[0]} ~ {hp['日期'].iloc[-1]}")
        print(f"  区间涨跌幅: {((hp['收盘'].iloc[-1] / hp['收盘'].iloc[0]) - 1) * 100:.2f}%")
        print(f"  最高: {hp['最高'].max():.2f}")
        print(f"  最低: {hp['最低'].min():.2f}")
        print(f"  日均成交额: {hp['成交额'].mean()/1e8:.2f}亿")
    else:
        print("  暂无数据")

    # 5. 业绩报表（最新财务数据）
    print(f"\n【5. 最新财务数据】")
    yjbb = get_yjbb(symbol)
    if yjbb:
        for k, v in yjbb.items():
            print(f"  {k}: {v}")
    else:
        print("  暂无数据")

    # 6. 资产负债表摘要
    print(f"\n【6. 资产负债表摘要】")
    bs = get_balance_sheet(symbol)
    if len(bs) > 0:
        print(bs.to_string(index=False))
    else:
        print("  暂无数据")

    print(f"\n{'='*60}")
    print("⚠️  以上为量化数据摘要，完整分析需结合慧博研报观点")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
        full_analysis(symbol)
    else:
        print("用法: python fact_check.py <股票代码>")
        print("示例: python fact_check.py 600666")
