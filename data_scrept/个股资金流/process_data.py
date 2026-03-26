#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✅ 可用脚本 - 处理东方财富资金流数据

【状态】: ✅ 已测试可用
【用途】: 将 JSON 数据转换为标准格式并保存（按日期分类存储）
【用法】: python3 process_data.py [input.json] [count]
【输出】:
  - JSON: /home/admin/.openclaw/workspace/data_files/个股资金流/YYYY-MM-DD/capital_flow_[today|3d|5d|10d]_YYYYMMDD_HHMMSS.json
  - CSV: /home/admin/.openclaw/workspace/data_files/个股资金流/YYYY-MM-DD/capital_flow_[today|3d|5d|10d]_YYYYMMDD_HHMMSS.csv

【示例】:
  python3 process_data.py /path/to/data.json 100
  echo '<JSON>' | python3 process_data.py -

【测试】: 2026-03-14 测试通过
"""

import json
import csv
import os
import sys
from datetime import datetime

# 基础输出目录
BASE_OUTPUT_DIR = "/home/admin/.openclaw/workspace/data_files/个股资金流"


def format_money(value):
    """格式化金额"""
    if value is None:
        return "0"
    try:
        return str(value)
    except:
        return "0"


def save_data(stocks, timestamp, rank_type="今日"):
    """保存数据（按日期分类存储）"""
    # 获取今天日期作为子目录名
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join(BASE_OUTPUT_DIR, today)
    
    # 创建目录（如果不存在）
    os.makedirs(output_dir, exist_ok=True)
    
    suffix = {"今日":"today","3 日":"3d","5 日":"5d","10 日":"10d"}.get(rank_type, "today")
    json_file = f"capital_flow_{suffix}_{timestamp}.json"
    csv_file = f"capital_flow_{suffix}_{timestamp}.csv"
    
    # JSON
    json_path = os.path.join(output_dir, json_file)
    output = {
        "获取时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "排行类型": rank_type,
        "数据条数": len(stocks),
        "数据来源": "东方财富网 - 个股资金流",
        "数据网址": "https://data.eastmoney.com/zjlx/detail.html",
        "数据": stocks
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  ✓ JSON: {json_path}")
    
    # CSV - 根据排行类型使用不同的表头
    csv_path = os.path.join(output_dir, csv_file)
    
    # 3 日排行专用表头（与东方财富网页面一致）
    if rank_type == "3 日":
        headers = ["序号","代码","名称","相关","最新价","3 日涨跌幅",
                   "3 日主力净流入 - 净额","3 日主力净流入 - 净占比",
                   "3 日超大单净流入 - 净额","3 日超大单净流入 - 净占比",
                   "3 日大单净流入","3 日中单净流入","3 日小单净流入"]
    # 5 日排行专用表头（与东方财富网页面一致）
    elif rank_type == "5 日":
        headers = ["序号","代码","名称","相关","最新价","5 日涨跌幅",
                   "5 日主力净流入 - 净额","5 日主力净流入 - 净占比",
                   "5 日超大单净流入 - 净额","5 日超大单净流入 - 净占比",
                   "5 日大单净流入 - 净额","5 日大单净流入 - 净占比",
                   "5 日中单净流入 - 净额","5 日中单净流入 - 净占比",
                   "5 日小单净流入 - 净额","5 日小单净流入 - 净占比"]
    # 10 日排行专用表头（与东方财富网页面一致）
    elif rank_type == "10 日":
        headers = ["序号","代码","名称","相关","最新价","10 日涨跌幅",
                   "10 日主力净流入 - 净额","10 日主力净流入 - 净占比",
                   "10 日超大单净流入 - 净额","10 日超大单净流入 - 净占比",
                   "10 日大单净流入 - 净额","10 日大单净流入 - 净占比",
                   "10 日中单净流入 - 净额","10 日中单净流入 - 净占比",
                   "10 日小单净流入 - 净额","10 日小单净流入 - 净占比"]
    else:
        headers = ["排名","股票代码","股票名称","最新价","涨跌幅",
                   "主力净流入","主力净占比","排行类型",
                   "超大单净流入","大单净流入","中单净流入","小单净流入"]
    
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for item in stocks:
            if rank_type == "3 日":
                # 3 日排行数据格式
                row = [
                    item.get("排名", ""),
                    item.get("code", item.get("股票代码", "")),
                    item.get("name", item.get("股票名称", "")),
                    "详情 数据 股吧",
                    item.get("price", item.get("最新价", "")),
                    item.get("changePct", item.get("涨跌幅", "")),
                    item.get("mainInflow", item.get("主力净流入", "")),
                    item.get("mainRatio", item.get("主力净占比", "")),
                    item.get("superInflow", item.get("超大单净流入", "")),
                    item.get("superRatio", item.get("超大单净占比", "")),
                    item.get("bigInflow", item.get("大单净流入", "")),
                    item.get("midInflow", item.get("中单净流入", "")),
                    item.get("smallInflow", item.get("小单净流入", ""))
                ]
            elif rank_type == "5 日" or rank_type == "10 日":
                # 5 日/10 日排行数据格式（与图片一致）
                row = [
                    item.get("排名", ""),
                    item.get("code", item.get("股票代码", "")),
                    item.get("name", item.get("股票名称", "")),
                    "详情 数据 股吧",
                    item.get("price", item.get("最新价", "")),
                    item.get("changePct", item.get("涨跌幅", "")),
                    item.get("mainInflow", item.get("主力净流入", "")),
                    item.get("mainRatio", item.get("主力净占比", "")),
                    item.get("superInflow", item.get("超大单净流入", "")),
                    item.get("superRatio", item.get("超大单净占比", "")),
                    item.get("bigInflow", item.get("大单净流入", "")),
                    item.get("bigRatio", item.get("大单净占比", "")),
                    item.get("midInflow", item.get("中单净流入", "")),
                    item.get("midRatio", item.get("中单净占比", "")),
                    item.get("smallInflow", item.get("小单净流入", "")),
                    item.get("smallRatio", item.get("小单净占比", ""))
                ]
            else:
                row = [item.get(h, "") for h in headers]
            writer.writerow(row)
    print(f"  ✓ CSV: {csv_path}")
    
    return json_path, csv_path


def main():
    if len(sys.argv) < 2:
        print("用法：python3 process_data.py <input.json> [count]")
        print()
        print("示例:")
        print("  python3 process_data.py /path/to/data.json 100")
        print()
        print("或者从标准输入读取:")
        print("  echo '<JSON>' | python3 process_data.py -")
        sys.exit(1)
    
    input_file = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print()
    print("="*70)
    print("东方财富资金流数据处理")
    print("="*70)
    
    # 读取数据
    if input_file == "-":
        print("从标准输入读取...")
        raw_data = json.load(sys.stdin)
    else:
        print(f"读取文件：{input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    
    # 确定排行类型
    rank_type = raw_data.get("排行类型", "今日")
    
    # 处理数据
    if "数据" in raw_data:
        stocks = raw_data["数据"][:count]
    elif "data" in raw_data:
        stocks = raw_data["data"][:count]
    else:
        stocks = [raw_data] if isinstance(raw_data, dict) else raw_data[:count]
    
    print(f"处理数据（最多 {count} 条）...")
    print(f"排行类型：{rank_type}")
    print(f"成功处理 {len(stocks)} 条数据")
    print()
    
    # 保存数据
    print("保存数据...")
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join(BASE_OUTPUT_DIR, today)
    save_data(stocks, timestamp, rank_type)
    
    # 打印摘要
    print()
    print("="*70)
    print("✅ 处理完成!")
    print("="*70)
    print(f"排行类型：{rank_type}")
    print(f"数据条数：{len(stocks)}")
    print(f"输出目录：{output_dir}")
    
    if stocks:
        print()
        print(f"前 5 名{rank_type}主力净流入:")
        for i, stock in enumerate(stocks[:5], 1):
            name = stock.get('股票名称', stock.get('name', 'N/A'))
            code = stock.get('股票代码', stock.get('code', 'N/A'))
            inflow = stock.get('主力净流入', '0')
            print(f"  {i}. {name}({code}) 主力净流入：{inflow}")
    
    print("="*70)


if __name__ == "__main__":
    main()
