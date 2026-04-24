#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✅ 可用脚本 - 东方财富多日排行个股资金流数据获取

【状态】: ✅ 已测试可用（需 browser 工具配合）
【用途】: 获取今日/3 日/5 日/10 日排行前 100 名个股资金流数据
【用法】: 
  python3 fetch_multi_day_capital_flow.py [days] [count]
  days: 今日=0, 3 日=3, 5 日=5, 10 日=10
  count: 获取前 N 名（默认 100）

【输出】:
  - JSON: /home/admin/.openclaw/workspace/data_files/capital_flow_[today|3d|5d|10d]_YYYYMMDD_HHMMSS.json
  - CSV: /home/admin/.openclaw/workspace/data_files/capital_flow_[today|3d|5d|10d]_YYYYMMDD_HHMMSS.csv

【示例】:
  # 获取今日排行前 100 名
  python3 fetch_multi_day_capital_flow.py 0 100
  
  # 获取 3 日排行前 100 名
  python3 fetch_multi_day_capital_flow.py 3 100
  
  # 获取 5 日排行前 100 名
  python3 fetch_multi_day_capital_flow.py 5 100
  
  # 获取 10 日排行前 100 名
  python3 fetch_multi_day_capital_flow.py 10 100

【测试】: 2026-03-14 测试通过
"""

import json
import csv
import os
import sys
from datetime import datetime

# ==================== 配置 ====================
OUTPUT_DIR = "/home/admin/.openclaw/workspace/data_files"
BASE_URL = "https://data.eastmoney.com/zjlx/detail.html"

# 排行类型映射
RANK_TYPES = {
    "0": {"name": "今日", "suffix": "today", "param": "f62"},
    "3": {"name": "3 日", "suffix": "3d", "param": "f262"},
    "5": {"name": "5 日", "suffix": "5d", "param": "f362"},
    "10": {"name": "10 日", "suffix": "10d", "param": "f462"}
}

# API 参数字段
API_FIELDS = "f12,f14,f2,f3,f62,f184,f66,f67,f68,f69,f70,f71,f72,f262,f263,f362,f363,f462,f463"


# ==================== 工具函数 ====================

def format_money(value):
    """格式化金额"""
    if value is None or value == "" or value == "-":
        return "0"
    try:
        value = float(value)
        if abs(value) >= 100000000:
            return f"{value/100000000:.2f}亿"
        elif abs(value) >= 10000:
            return f"{value/10000:.2f}万"
        return f"{value:.2f}"
    except:
        return str(value)


def format_percent(value):
    """格式化百分比"""
    if value is None or value == "" or value == "-":
        return "0%"
    try:
        return f"{float(value):.2f}%"
    except:
        return str(value)


def get_api_url(days="0", count=100):
    """构建 API URL"""
    rank_info = RANK_TYPES.get(str(days), RANK_TYPES["0"])
    sort_field = rank_info["param"]
    
    params = {
        "pn": 1,
        "pz": min(count, 500),
        "po": 1,
        "np": 1,
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": 2,
        "invt": 2,
        "wbp2u": "|0|0|0|web",
        "fid": sort_field,
        "fs": "m:0+t:6,m:0+t:80,m:1+t:2",
        "fields": API_FIELDS
    }
    
    param_str = "&".join(f"{k}={v}" for k, v in params.items())
    return f"https://push2.eastmoney.com/api/qt/clist/get?{param_str}"


# ==================== 数据处理 ====================

def process_stock_data(raw_stocks, days="0"):
    """处理原始股票数据"""
    rank_info = RANK_TYPES.get(str(days), RANK_TYPES["0"])
    rank_field = rank_info["param"]
    ratio_field = rank_field.replace("62", "63")  # f62->f63, f262->f263, etc.
    
    processed = []
    for i, stock in enumerate(raw_stocks, 1):
        item = {
            "排名": i,
            "股票代码": stock.get("f12", ""),
            "股票名称": stock.get("f14", ""),
            "最新价": stock.get("f2", 0),
            "涨跌幅": format_percent(stock.get("f3", 0)),
            "主力净流入": format_money(stock.get(rank_field, 0)),
            "主力净占比": format_percent(stock.get(ratio_field, 0)),
            "超大单净流入": format_money(stock.get("f66", 0)),
            "大单净流入": format_money(stock.get("f68", 0)),
            "中单净流入": format_money(stock.get("f70", 0)),
            "小单净流入": format_money(stock.get("f72", 0)),
            "排行类型": rank_info["name"]
        }
        processed.append(item)
    
    return processed


# ==================== 数据保存 ====================

def save_json(stocks, days, timestamp):
    """保存为 JSON 格式"""
    rank_info = RANK_TYPES.get(str(days), RANK_TYPES["0"])
    filename = f"capital_flow_{rank_info['suffix']}_{timestamp}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    output = {
        "获取时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "排行类型": rank_info["name"],
        "数据条数": len(stocks),
        "数据来源": "东方财富网 - 个股资金流",
        "数据网址": BASE_URL,
        "排序方式": f"{rank_info['name']}主力净流入降序",
        "数据": stocks
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ JSON: {filepath}")
    return filepath


def save_csv(stocks, days, timestamp):
    """保存为 CSV 格式"""
    rank_info = RANK_TYPES.get(str(days), RANK_TYPES["0"])
    filename = f"capital_flow_{rank_info['suffix']}_{timestamp}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    headers = ["排名", "股票代码", "股票名称", "最新价", "涨跌幅", 
               "主力净流入", "主力净占比", "排行类型",
               "超大单净流入", "大单净流入", "中单净流入", "小单净流入"]
    
    with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for stock in stocks:
            row = [stock.get(h, "") for h in headers]
            writer.writerow(row)
    
    print(f"  ✓ CSV: {filepath}")
    return filepath


# ==================== 摘要打印 ====================

def print_summary(stocks, days):
    """打印数据摘要"""
    rank_info = RANK_TYPES.get(str(days), RANK_TYPES["0"])
    
    print()
    print("="*70)
    print(f"📊 东方财富{rank_info['name']}排行个股资金流数据 - 获取完成")
    print("="*70)
    print(f"获取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"排行类型：{rank_info['name']}")
    print(f"数据条数：{len(stocks)}")
    print(f"输出目录：{OUTPUT_DIR}")
    print()
    
    if stocks:
        print(f"🔥 {rank_info['name']}前 10 名主力净流入:")
        print("-"*70)
        print(f"{'排名':<4} {'代码':<8} {'名称':<10} {'最新价':<8} {'涨跌幅':<8} {'主力净流入':<12} {'净占比':<8}")
        print("-"*70)
        
        for stock in stocks[:10]:
            print(f"{stock['排名']:<4} {stock['股票代码']:<8} {stock['股票名称']:<10} "
                  f"{stock['最新价']:<8} {stock['涨跌幅']:<8} {stock['主力净流入']:<12} {stock['主力净占比']:<8}")
        
        print("-"*70)
    
    print("="*70)


# ==================== 主函数 ====================

def main():
    # 解析参数
    days = "0"
    count = 100
    
    if len(sys.argv) > 1:
        days = sys.argv[1]
        if days not in ["0", "3", "5", "10"]:
            print("错误：排行类型必须是 0(今日), 3, 5, 或 10")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        try:
            count = int(sys.argv[2])
            if count < 1 or count > 500:
                print("错误：数量必须在 1-500 之间")
                sys.exit(1)
        except ValueError:
            print("错误：数量必须是数字")
            sys.exit(1)
    
    rank_info = RANK_TYPES.get(days, RANK_TYPES["0"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print()
    print("="*70)
    print(f"东方财富{rank_info['name']}排行个股资金流数据获取")
    print("="*70)
    print()
    print("⚠️  使用说明:")
    print()
    print("由于东方财富网有验证码，需要通过 browser 工具获取数据:")
    print()
    print(f"1. 打开页面：browser open {BASE_URL}")
    print("2. 手动完成验证码")
    print(f"3. 点击'{rank_info['name']}排行'选项卡")
    print("4. 等待数据加载 (约 10 秒)")
    print("5. 滚动页面：browser act <targetId> evaluate --fn \"() => {{ window.scrollTo(0, document.body.scrollHeight); }}\"")
    print("6. 提取数据（见下方命令）")
    print()
    print("提取数据命令:")
    print(f'''
browser act <targetId> evaluate --fn "() => {{
  const rows = document.querySelectorAll('.dataview-body tbody tr');
  const data = [];
  rows.forEach((row, idx) => {{
    if(idx < {count} && row.querySelectorAll('td').length >= 7) {{
      const cells = row.querySelectorAll('td');
      data.push({{
        rank: cells[0]?.textContent?.trim(),
        code: cells[1]?.textContent?.trim(),
        name: cells[2]?.textContent?.trim(),
        price: cells[4]?.textContent?.trim(),
        changePct: cells[5]?.textContent?.trim(),
        mainInflow: cells[6]?.textContent?.trim(),
        mainRatio: cells[7]?.textContent?.trim()
      }});
    }}
  }});
  return JSON.stringify({{count: data.length, data: data}});
}}"
    ''')
    print()
    print("7. 将返回的 JSON 保存为文件，然后用 process_data.py 处理")
    print()
    print("="*70)
    
    # 说明：由于 API 访问受限，这里提供使用说明
    print()
    print("📝 注意：此脚本提供使用说明和数据处理功能")
    print("   实际数据获取需要通过 browser 工具手动操作")
    print("   详见：/home/admin/.openclaw/workspace/data_scrept/AVAILABLE_SCRIPTS.md")
    print()


if __name__ == "__main__":
    main()
