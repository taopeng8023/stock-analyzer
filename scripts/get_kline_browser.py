#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过浏览器自动化获取股票 K 线数据
【真实数据方案】
"""

import json
import os
from datetime import datetime

def save_kline_data(code: str, name: str, kline_data: list):
    """保存 K 线数据到本地"""
    os.makedirs('/home/admin/.openclaw/workspace/data/kline', exist_ok=True)
    
    # 保存为 JSON
    data = {
        'code': code,
        'name': name,
        'timestamp': datetime.now().isoformat(),
        'klines': kline_data
    }
    
    with open(f'/home/admin/.openclaw/workspace/data/kline/{code}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 数据已保存：/home/admin/.openclaw/workspace/data/kline/{code}.json")
    return data

def main():
    """
    说明：
    由于网络限制，无法直接访问东方财富 API
    请使用以下手动步骤获取真实数据：
    
    1. 访问东方财富 K 线页面
    2. 复制数据
    3. 保存为 JSON
    """
    
    print("=" * 70)
    print(" " * 20 + "股票 K 线数据获取指南")
    print("=" * 70)
    
    stocks = [
        {'code': '600549', 'name': '厦门钨业'},
        {'code': '000592', 'name': '平潭发展'},
        {'code': '600186', 'name': '莲花健康'},
    ]
    
    print("\n📋 由于网络限制，请按以下步骤获取真实数据：\n")
    
    for stock in stocks:
        code = stock['code']
        name = stock['name']
        
        print(f"【{name} ({code})】")
        print(f"  1. 访问：https://quote.eastmoney.com/unify/cr/1.{code}")
        print(f"  2. 点击'历史交易'标签")
        print(f"  3. 选择时间范围（建议 1 年以上）")
        print(f"  4. 点击'导出'按钮，下载 CSV")
        print(f"  5. 保存到：/home/admin/.openclaw/workspace/data/kline/{code}.csv")
        print()
    
    print("=" * 70)
    print("💡 或者使用浏览器自动化工具：")
    print("=" * 70)
    print("""
# 使用 browser 工具打开页面
browser open https://quote.eastmoney.com/unify/cr/1.600549
browser snapshot --loadState networkidle

# 然后从 snapshot 中提取数据
""")
    
    print("=" * 70)
    print("📁 数据格式要求：")
    print("=" * 70)
    print("""
CSV 文件应包含以下列：
日期，开盘，收盘，最高，最低，成交量，成交额

示例：
2025-01-02,18.60,18.28,18.82,18.11,117015,222558490.00
2025-01-03,18.29,18.31,18.87,18.25,134379,257187295.00
""")

if __name__ == "__main__":
    main()
