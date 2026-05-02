#!/usr/bin/env python3
"""
基金申购日历 + 持仓股交集筛选器
从天天基金抓取半导体/科技主题基金持仓，输出持仓股交集

用法:
  python3 fund_flow_screen.py                    # 默认分析
  python3 fund_flow_screen.py --theme 半导体      # 只看半导体主题
  python3 fund_flow_screen.py --top 20           # 输出前20大持仓交集
"""

import requests
import re
import sys
import argparse
import html
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://fundf10.eastmoney.com/",
}

# 半导体/科技核心基金（ETF + 联接 + 主动管理）
CORE_FUNDS = {
    # ETF
    "159995": {"name": "华夏国证半导体芯片ETF", "theme": "半导体", "type": "ETF"},
    "512760": {"name": "国泰CES半导体芯片行业ETF", "theme": "半导体", "type": "ETF"},
    "512480": {"name": "国泰中证半导体材料设备ETF", "theme": "半导体", "type": "ETF"},
    "159813": {"name": "鹏华国证半导体芯片ETF", "theme": "半导体", "type": "ETF"},
    "516160": {"name": "南方中证新能源ETF", "theme": "新能源", "type": "ETF"},
    # 联接基金（持仓为ETF份额，但也可能有股票）
    "007300": {"name": "国联安中证半导体ETF联接A", "theme": "半导体", "type": "联接"},
    "008281": {"name": "国泰CES半导体芯片ETF联接A", "theme": "半导体", "type": "联接"},
    "011612": {"name": "华夏芯片ETF联接A", "theme": "半导体", "type": "联接"},
    "014178": {"name": "鹏华半导体芯片ETF联接A", "theme": "半导体", "type": "联接"},
    # 主动管理
    "011961": {"name": "广发科技先锋", "theme": "科技", "type": "混合"},
    "011613": {"name": "华夏科技创新", "theme": "科技", "type": "混合"},
    "009313": {"name": "华安科技动力", "theme": "科技", "type": "混合"},
    "005311": {"name": "万家行业优选", "theme": "科技", "type": "混合"},
    "001071": {"name": "华安媒体互联网", "theme": "科技", "type": "混合"},
    "163406": {"name": "兴全合润", "theme": "科技", "type": "混合"},
}


def get_fund_holdings(fund_code):
    """
    从天天基金抓取基金持仓（前十大重仓股）
    返回: [(股票代码, 股票名称, 占净值比例), ...]
    """
    url = (
        f"https://fundf10.eastmoney.com/FundArchivesDatas.aspx"
        f"?type=jjcc&code={fund_code}&topline=10&year=&month="
    )
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        text = resp.text
        
        # 从HTML中提取股票代码和名称
        # 格式: <a href='//quote.eastmoney.com/.../1.688041'>688041</a>
        #        <td class='tol'><a href='...'>海光信息</a>
        
        # 股票代码: 在 quote.eastmoney.com/unify/r/ 后面的6位数字
        code_pattern = re.findall(
            r"quote\.eastmoney\.com/unify/r/[\d\.]+(\d{6})'", text
        )
        
        # 股票名称: tol class 的 td 里的 a 标签文本
        name_pattern = re.findall(
            r"class='tol'><a[^>]*>([^<]+)</a>", text
        )
        
        # 占净值比例
        ratio_pattern = re.findall(
            r">([\d.]+%)</td>", text
        )
        
        # 去重保留股票代码（ETF代码159995等会混入）
        etf_codes = {'159995', '512760', '512480', '159813', '516160'}
        code_pattern = [c for c in code_pattern if c not in etf_codes]
        # 去重股票代码（每个股票出现多次）
        seen = set()
        unique_codes = []
        for c in code_pattern:
            if c not in seen:
                seen.add(c)
                unique_codes.append(c)
        code_pattern = unique_codes
        
        holdings = []
        for i in range(min(len(code_pattern), len(name_pattern))):
            holdings.append({
                "code": code_pattern[i],
                "name": name_pattern[i],
                "ratio": ratio_pattern[i] if i < len(ratio_pattern) else "",
            })
        
        return holdings
        
    except Exception as e:
        print(f"  [ERR] {fund_code}: {e}", file=sys.stderr)
        return []


def fetch_single_fund(code_info):
    """单个基金获取持仓（用于多线程）"""
    code, info = code_info
    holdings = get_fund_holdings(code)
    return code, info, holdings


def main():
    parser = argparse.ArgumentParser(description="基金持仓股交集筛选器")
    parser.add_argument("--theme", type=str, default="", help="筛选主题")
    parser.add_argument("--top", type=int, default=15, help="输出前N大交集")
    args = parser.parse_args()
    
    print("=" * 65)
    print("  半导体/科技基金 持仓股交集筛选器")
    print("=" * 65)
    print()
    
    # 筛选基金
    funds = CORE_FUNDS
    if args.theme:
        funds = {k: v for k, v in funds.items() if args.theme in v["theme"]}
    
    print(f"  分析 {len(funds)} 只基金的持仓...\n")
    
    # 展示基金列表
    for code, info in funds.items():
        print(f"  {code}  {info['name']:<30s}  [{info['theme']}]")
    print()
    
    # 多线程获取持仓
    print("  正在获取持仓数据...", flush=True)
    all_holdings = defaultdict(list)  # stock_code -> [{fund_code, fund_name, stock_name, ratio}]
    success_count = 0
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(fetch_single_fund, (code, info)): code
            for code, info in funds.items()
        }
        
        for future in as_completed(futures):
            code, info, holdings = future.result()
            if holdings:
                success_count += 1
                for h in holdings:
                    all_holdings[h["code"]].append({
                        "fund_code": code,
                        "fund_name": info["name"],
                        "stock_name": h["name"],
                        "ratio": h["ratio"],
                    })
                print(f"  ✓ {code} {info['name'][:20]} → {len(holdings)}只股票", flush=True)
            else:
                print(f"  ✗ {code} {info['name'][:20]} → 无持仓数据(可能是联接基金)", flush=True)
    
    print(f"\n  成功获取 {success_count}/{len(funds)} 只基金持仓\n")
    
    if not all_holdings:
        print("  [!] 未获取到持仓数据，天天基金接口可能需要更新")
        print("  请手动查看: https://fundf10.eastmoney.com/ccmx_159995.html")
        return
    
    # 统计交集
    stock_stats = {}
    for stock_code, fund_list in all_holdings.items():
        stock_stats[stock_code] = {
            "name": fund_list[0]["stock_name"],
            "count": len(fund_list),
            "funds": fund_list,
            "total_ratio": sum(
                float(r["ratio"].replace("%", ""))
                for r in fund_list
                if r["ratio"]
            ),
        }
    
    # 排序：优先按基金数量，其次按总占比
    sorted_stocks = sorted(
        stock_stats.items(),
        key=lambda x: (x[1]["count"], x[1]["total_ratio"]),
        reverse=True,
    )
    
    # 输出结果
    print("=" * 65)
    print(f"  持仓股交集 TOP {args.top}")
    print("=" * 65)
    print()
    print(f"  {'排名':<4s} {'代码':<8s} {'名称':<12s} {'基金数':<6s} {'总占比':<8s}  持有基金")
    print(f"  {'-'*4} {'-'*8} {'-'*12} {'-'*6} {'-'*8}  {'-'*30}")
    
    for rank, (code, info) in enumerate(sorted_stocks[:args.top], 1):
        name = info["name"]
        count = info["count"]
        ratio_str = f"{info['total_ratio']:.1f}%" if info['total_ratio'] > 0 else "N/A"
        fund_names = [f["fund_name"][:12] for f in info["funds"][:3]]
        funds_str = ", ".join(fund_names)
        if len(info["funds"]) > 3:
            funds_str += f" +{len(info['funds'])-3}"
        print(f"  {rank:<4d} {code:<8s} {name:<12s} {count:<6d} {ratio_str:<8s}  {funds_str}")
    
    print()
    print("=" * 65)
    print("  策略解读:")
    print("  · 基金数≥3 = 多只基金共同重仓 = 资金流驱动概率高")
    print("  · 关注这些基金的申购开放日 → 申购前1-2天建仓")
    print("  · 基金集中买入期(1-3天)后择机卖出")
    print("  · 净值更新日(T+1)后可以看到申购带来的持仓变化")
    print("=" * 65)


if __name__ == "__main__":
    main()
