#!/usr/bin/env python3
"""
测试东方财富 API 数据获取
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from eastmoney_api import EastMoneyAPI, get_stock_data
import json

def test_api():
    api = EastMoneyAPI()
    
    print("="*60)
    print("东方财富 API 测试")
    print("="*60)
    
    symbol = "603739"  # 蔚蓝生物
    print(f"\n测试股票：{symbol} 蔚蓝生物\n")
    
    # 1. 实时行情
    print("【1. 实时行情】")
    quote = api.get_realtime_quote(symbol)
    if "error" not in quote:
        print(f"  名称：{quote.get('名称')}")
        print(f"  最新价：{quote.get('最新价')}")
        print(f"  涨跌幅：{quote.get('涨跌幅')}%")
        print(f"  成交量：{quote.get('成交量')}")
        print(f"  总市值：{quote.get('总市值', 0)/100000000:.2f}亿")
    else:
        print(f"  失败：{quote.get('error')}")
    print()
    
    # 2. K 线数据
    print("【2. K 线数据】")
    kline = api.get_kline_data(symbol, period='day', count=5)
    if not kline.empty:
        for _, row in kline.iterrows():
            print(f"  {row['日期']} 开{row['开盘']} 收{row['收盘']} 高{row['最高']} 低{row['最低']}")
    else:
        print("  无数据")
    print()
    
    # 3. 资金流向
    print("【3. 资金流向】")
    flow = api.get_money_flow(symbol)
    if flow:
        print(f"  日期：{flow.get('日期')}")
        print(f"  主力净流入：{flow.get('主力净流入', 0)/10000:.2f}万")
        print(f"  超大单：{flow.get('超大单净流入', 0)/10000:.2f}万")
        print(f"  大单：{flow.get('大单净流入', 0)/10000:.2f}万")
    else:
        print("  无数据")
    print()
    
    # 4. 所属板块
    print("【4. 所属板块】")
    blocks = api.get_concept_blocks(symbol)
    if blocks:
        for block in blocks[:5]:
            print(f"  • {block.get('板块', 'N/A')}")
    else:
        print("  无数据")
    print()
    
    # 5. 最新公告
    print("【5. 最新公告】")
    notices = api.get_notices(symbol, count=3)
    if notices:
        for notice in notices:
            print(f"  {notice.get('日期')} - {notice.get('标题')[:40]}")
    else:
        print("  无数据")
    print()
    
    # 6. 机构研报
    print("【6. 机构研报】")
    reports = api.get_research_reports(symbol, count=3)
    if reports:
        for report in reports:
            print(f"  {report.get('日期')} {report.get('机构')} [{report.get('评级')}]")
            print(f"    {report.get('标题')[:50]}")
    else:
        print("  无数据")
    print()
    
    print("="*60)
    print("测试完成!")
    print("="*60)


if __name__ == "__main__":
    try:
        test_api()
    except Exception as e:
        print(f"测试失败：{e}")
        import traceback
        traceback.print_exc()
