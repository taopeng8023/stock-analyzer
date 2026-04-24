#!/usr/bin/env python3
"""
同花顺资金流数据（直接 API 调用）
使用标准库 requests，无需安装额外依赖

⚠️  仅用于个人研究学习

用法:
    python3 ths_direct.py --top 10
"""

import requests
import json
from datetime import datetime


def get_ths_moneyflow(top_n: int = 10):
    """
    获取同花顺个股资金流排行
    
    通过模拟浏览器请求获取真实数据
    """
    print(f"[同花顺] 获取个股资金流排行...")
    
    # 同花顺资金流 API（模拟）
    url = "http://data.10jqka.com.cn/rank/zjlx/field/zljc/order/desc/page/1/ajax/1/free/1/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'http://data.10jqka.com.cn/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            # 解析 HTML
            html = resp.text
            
            # 尝试提取数据
            import re
            
            # 查找数据行
            pattern = r'<td[^>]*>(\d+)</td>.*?<td[^>]*>(\d{6})</td>.*?<td[^>]*]>([^<]+)</td>.*?<td[^>]*]>([^<]+)</td>.*?<td[^>]*]>([^<]+)</td>.*?<td[^>]*]>([^<]+)</td>'
            
            matches = re.findall(pattern, html, re.DOTALL)
            
            if matches:
                print(f"✅ 获取到 {len(matches)} 条数据")
                
                stocks = []
                for match in matches[:top_n]:
                    stock = {
                        'rank': match[0],
                        'code': match[1],
                        'name': match[2].strip(),
                        'price': match[3],
                        'change_pct': match[4],
                        'main_net': match[5],
                    }
                    stocks.append(stock)
                
                return stocks
        
        print(f"❌ 请求失败：状态码 {resp.status_code}")
        return None
        
    except Exception as e:
        print(f"❌ 获取失败：{e}")
        return None


def print_ranking(stocks, title: str = "资金流排行"):
    """打印排行数据"""
    if not stocks:
        print("无数据")
        return
    
    print(f"\n{'='*80}")
    print(f"💰 {title}")
    print(f"数据源：同花顺 (真实数据)")
    print(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*80}")
    
    print(f"\n{'排名':<4} {'代码':<8} {'名称':<10} {'主力净流入':<12} {'涨跌幅':<8} {'价格':<8}")
    print(f"{'-'*80}")
    
    for s in stocks:
        print(f"{s['rank']:<4} {s['code']:<8} {s['name']:<10} {s['main_net']:<12} {s['change_pct']:<8} {s['price']:<8}")
    
    print(f"{'='*80}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='同花顺资金流数据（直接 API）')
    parser.add_argument('--top', type=int, default=10, help='前 N 只股票')
    
    args = parser.parse_args()
    
    stocks = get_ths_moneyflow(top_n=args.top)
    
    if stocks:
        print_ranking(stocks, title=f"个股资金流排行 Top{args.top}")
    else:
        print("\n❌ 无法获取同花顺数据")
        print("\n💡 建议:")
        print("  1. 使用腾讯财经估算：python3 fund_flow.py --top 10")
        print("  2. 等待 Tushare 审批通过")
        print("  3. 升级 Python 到 3.8+ 后安装 AKShare")


if __name__ == '__main__':
    main()
