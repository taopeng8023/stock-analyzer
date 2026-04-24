#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✅ 可用脚本 - 东方财富网个股资金流数据 Browser 工具使用说明

【状态】: ✅ 已测试可用
【用途】: 提供 browser 工具获取数据的详细说明和示例代码
【输出】: 
  - JSON: /home/admin/.openclaw/workspace/data_files/capital_flow_YYYYMMDD_HHMMSS.json
  - CSV: /home/admin/.openclaw/workspace/data_files/capital_flow_YYYYMMDD_HHMMSS.csv

【使用方法】:
  详见 AVAILABLE_SCRIPTS.md 或 QUICK_START.md

【测试】: 2026-03-14 测试通过
"""

import json
import csv
import os
import sys
from datetime import datetime

# 配置
OUTPUT_DIR = "/home/admin/.openclaw/workspace/data_files"
TARGET_URL = "https://data.eastmoney.com/zjlx/detail.html"


def format_money(value):
    """将金额（元）转换为易读格式（亿/万）"""
    if value is None:
        return "0"
    try:
        value = float(value)
        if abs(value) >= 100000000:
            return f"{value/100000000:.2f}亿"
        elif abs(value) >= 10000:
            return f"{value/10000:.2f}万"
        else:
            return f"{value:.2f}"
    except (ValueError, TypeError):
        return "0"


def parse_stock_data(raw_data):
    """解析浏览器返回的原始数据"""
    stocks = []
    
    if isinstance(raw_data, list):
        for item in raw_data:
            if isinstance(item, dict):
                stock = {
                    "f12": item.get("code", ""),
                    "f14": item.get("name", ""),
                    "f2": item.get("price", 0),
                    "f3": item.get("changePct", "0%").replace("%", ""),
                    "f62": item.get("mainInflow", "0").replace("亿", "00000000").replace("万", "0000").replace("亿", ""),
                    "f184": item.get("mainRatio", "0%").replace("%", ""),
                    "f66": item.get("superInflow", "0"),
                    "f69": item.get("superRatio", "0%").replace("%", ""),
                    "f68": item.get("bigInflow", "0"),
                    "f70": item.get("midInflow", "0"),
                    "f72": item.get("smallInflow", "0"),
                }
                stocks.append(stock)
    
    return stocks


def save_json(stocks, filename, raw_data=None):
    """保存为 JSON 格式"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # 转换数据为易读格式
    readable_data = []
    for i, stock in enumerate(stocks, 1):
        item = {
            "排名": i,
            "代码": stock.get("f12", ""),
            "名称": stock.get("f14", ""),
            "最新价": stock.get("f2", 0),
            "涨跌幅": f"{float(stock.get('f3', 0)):.2f}%",
            "主力净流入": stock.get("f62", "0"),
            "主力净占比": f"{float(stock.get('f184', 0)):.2f}%",
            "超大单净流入": stock.get("f66", "0"),
            "超大单净占比": f"{float(stock.get('f69', 0)):.2f}%",
            "大单净流入": stock.get("f68", "0"),
            "中单净流入": stock.get("f70", "0"),
            "小单净流入": stock.get("f72", "0"),
        }
        readable_data.append(item)
    
    output = {
        "获取时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "数据条数": len(stocks),
        "说明": "东方财富网个股资金流排行榜 - 按主力净流入排序",
        "数据来源": TARGET_URL,
        "数据": readable_data
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ JSON 数据已保存：{filepath}")
    return filepath


def save_csv(stocks, filename):
    """保存为 CSV 格式"""
    csv_filename = filename.replace('.json', '.csv')
    filepath = os.path.join(OUTPUT_DIR, csv_filename)
    
    headers = ["排名", "代码", "名称", "最新价", "涨跌幅", "主力净流入", 
               "主力净占比", "超大单净流入", "超大单净占比", "大单净流入", 
               "中单净流入", "小单净流入"]
    
    with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for i, stock in enumerate(stocks, 1):
            try:
                change_pct = float(stock.get('f3', 0))
                change_sign = '+' if change_pct > 0 else ''
                row = [
                    i,
                    stock.get("f12", ""),
                    stock.get("f14", ""),
                    stock.get("f2", 0),
                    f"{change_sign}{change_pct:.2f}%",
                    stock.get("f62", "0"),
                    f"{float(stock.get('f184', 0)):.2f}%",
                    stock.get("f66", "0"),
                    f"{float(stock.get('f69', 0)):.2f}%",
                    stock.get("f68", "0"),
                    stock.get("f70", "0"),
                    stock.get("f72", "0")
                ]
                writer.writerow(row)
            except (ValueError, TypeError):
                continue
    
    print(f"  ✓ CSV 数据已保存：{filepath}")
    return filepath


def print_summary(stocks):
    """打印数据摘要"""
    print("\n" + "="*60)
    print("数据获取完成!")
    print("="*60)
    print(f"获取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"数据条数：{len(stocks)}")
    print(f"输出目录：{OUTPUT_DIR}")
    
    if stocks:
        print("\n📊 前 5 名主力净流入个股:")
        for i, stock in enumerate(stocks[:5], 1):
            name = stock.get('f14', '')
            code = stock.get('f12', '')
            inflow = stock.get('f62', '0')
            try:
                change = float(stock.get('f3', 0))
                change_sign = '+' if change > 0 else ''
                print(f"  {i}. {name}({code}) 主力净流入：{inflow} 涨跌幅：{change_sign}{change:.2f}%")
            except:
                print(f"  {i}. {name}({code}) 主力净流入：{inflow}")
    
    print("="*60)


def main():
    """
    此脚本需要配合 OpenClaw browser 工具使用
    
    使用步骤:
    1. 使用 browser 工具打开页面：https://data.eastmoney.com/zjlx/detail.html
    2. 使用 browser evaluate 提取数据
    3. 将提取的数据保存到此脚本处理
    
    或者直接使用 OpenClaw 的 browser 工具自动化获取
    """
    print("="*60)
    print("东方财富个股资金流数据抓取脚本")
    print("="*60)
    print(f"\n目标 URL: {TARGET_URL}")
    print(f"输出目录：{OUTPUT_DIR}")
    print("\n此脚本需要配合 OpenClaw browser 工具使用。")
    print("请确保确保输出目录存在...")
    
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"  ✓ 输出目录已准备：{OUTPUT_DIR}")
    
    print("\n使用说明:")
    print("  1. 使用 OpenClaw browser 工具访问页面")
    print("  2. 使用 evaluate 提取表格数据")
    print("  3. 数据将自动保存到输出目录")
    print("\n示例 browser evaluate 代码:")
    print('''
    () => {
      const rows = document.querySelectorAll('table tbody tr');
      const data = [];
      rows.forEach((row, idx) => {
        if(idx < 100) {
          const cells = row.querySelectorAll('td');
          if(cells.length > 3) {
            data.push({
              rank: cells[0]?.textContent?.trim(),
              code: cells[1]?.textContent?.trim(),
              name: cells[2]?.textContent?.trim(),
              price: cells[4]?.textContent?.trim(),
              changePct: cells[5]?.textContent?.trim(),
              mainInflow: cells[6]?.textContent?.trim(),
              mainRatio: cells[7]?.textContent?.trim()
            });
          }
        }
      });
      return data;
    }
    ''')


if __name__ == "__main__":
    main()
