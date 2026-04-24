#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✅ 东方财富个股资金流 API 数据获取脚本（优化版）

【状态】: ✅ 已优化
【用途】: 根据 API 接口字段自动映射，获取 4 种排行数据
【用法】: python3 fetch_capital_flow_api.py [days] [count]
  - days: 0=今日，3=3 日，5=5 日，10=10 日（默认 0）
  - count: 获取条数（默认 100）

【输出】:
  - JSON: /home/admin/.openclaw/workspace/data_files/个股资金流/YYYY-MM-DD/capital_flow_[today|3d|5d|10d]_YYYYMMDD_HHMMSS.json
  - CSV: /home/admin/.openclaw/workspace/data_files/个股资金流/YYYY-MM-DD/capital_flow_[today|3d|5d|10d]_YYYYMMDD_HHMMSS.csv

【测试】: 2026-03-14 测试通过
"""

import json
import csv
import os
import sys
import subprocess
from datetime import datetime

# ==================== 配置 ====================
BASE_OUTPUT_DIR = "/home/admin/.openclaw/workspace/data_files/个股资金流"
API_URL = "https://push2.eastmoney.com/api/qt/clist/get"

# API 字段到中文表头的映射
FIELD_MAPPING = {
    # 基础字段
    "f12": "代码",
    "f14": "名称",
    "f2": "最新价",
    "f3": "涨跌幅",
    
    # 今日排行字段
    "f62": "今日主力净流入 - 净额",
    "f184": "今日主力净流入 - 净占比",
    "f66": "今日超大单净流入 - 净额",
    "f67": "今日超大单净流入 - 净占比",
    "f68": "今日大单净流入 - 净额",
    "f69": "今日大单净流入 - 净占比",
    "f70": "今日中单净流入 - 净额",
    "f71": "今日中单净流入 - 净占比",
    "f72": "今日小单净流入 - 净额",
    "f73": "今日小单净流入 - 净占比",
    
    # 3 日排行字段
    "f262": "3 日主力净流入 - 净额",
    "f263": "3 日主力净流入 - 净占比",
    "f266": "3 日超大单净流入 - 净额",
    "f267": "3 日超大单净流入 - 净占比",
    "f268": "3 日大单净流入 - 净额",
    "f269": "3 日大单净流入 - 净占比",
    "f270": "3 日中单净流入 - 净额",
    "f271": "3 日中单净流入 - 净占比",
    "f272": "3 日小单净流入 - 净额",
    "f273": "3 日小单净流入 - 净占比",
    
    # 5 日排行字段
    "f362": "5 日主力净流入 - 净额",
    "f363": "5 日主力净流入 - 净占比",
    "f366": "5 日超大单净流入 - 净额",
    "f367": "5 日超大单净流入 - 净占比",
    "f368": "5 日大单净流入 - 净额",
    "f369": "5 日大单净流入 - 净占比",
    "f370": "5 日中单净流入 - 净额",
    "f371": "5 日中单净流入 - 净占比",
    "f372": "5 日小单净流入 - 净额",
    "f373": "5 日小单净流入 - 净占比",
    
    # 10 日排行字段
    "f462": "10 日主力净流入 - 净额",
    "f463": "10 日主力净流入 - 净占比",
    "f466": "10 日超大单净流入 - 净额",
    "f467": "10 日超大单净流入 - 净占比",
    "f468": "10 日大单净流入 - 净额",
    "f469": "10 日大单净流入 - 净占比",
    "f470": "10 日中单净流入 - 净额",
    "f471": "10 日中单净流入 - 净占比",
    "f472": "10 日小单净流入 - 净额",
    "f473": "10 日小单净流入 - 净占比",
}

# 排行类型配置
RANK_CONFIG = {
    "0": {"name": "今日", "suffix": "today", "sort_field": "f62", "fields": "f12,f14,f2,f3,f62,f184,f66,f67,f68,f69,f70,f71,f72,f73"},
    "3": {"name": "3 日", "suffix": "3d", "sort_field": "f262", "fields": "f12,f14,f2,f3,f262,f263,f266,f267,f268,f269,f270,f271,f272,f273"},
    "5": {"name": "5 日", "suffix": "5d", "sort_field": "f362", "fields": "f12,f14,f2,f3,f362,f363,f366,f367,f368,f369,f370,f371,f372,f373"},
    "10": {"name": "10 日", "suffix": "10d", "sort_field": "f462", "fields": "f12,f14,f2,f3,f462,f463,f466,f467,f468,f469,f470,f471,f472,f473"},
}


# ==================== 工具函数 ====================

def format_value(value, field_name=""):
    """格式化 API 返回的数值"""
    if value is None or value == "" or value == "-":
        return "0"
    
    try:
        val = float(value)
        
        # 根据字段类型格式化
        if "净占比" in field_name or "涨跌幅" in field_name:
            # 百分比字段
            if abs(val) >= 1:
                return f"{val:.2f}%"
            else:
                return f"{val*100:.2f}%"
        elif "净额" in field_name or "流入" in field_name:
            # 金额字段
            if abs(val) >= 100000000:
                return f"{val/100000000:.2f}亿"
            elif abs(val) >= 10000:
                return f"{val/10000:.2f}万"
            else:
                return f"{val:.2f}"
        else:
            # 其他字段（价格等）
            return f"{val:.2f}"
    except:
        return str(value)


def get_api_url(days="0", count=100):
    """构建 API URL"""
    config = RANK_CONFIG.get(str(days), RANK_CONFIG["0"])
    
    params = {
        "pn": 1,
        "pz": min(count, 500),
        "po": 1,
        "np": 1,
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": 2,
        "invt": 2,
        "wbp2u": "|0|0|0|web",
        "fid": config["sort_field"],
        "fs": "m:0+t:6,m:0+t:80,m:1+t:2",
        "fields": config["fields"]
    }
    
    param_str = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{API_URL}?{param_str}"


def fetch_data_via_curl(days="0", count=100):
    """使用 curl 获取 API 数据"""
    url = get_api_url(days, count)
    rank_name = RANK_CONFIG.get(str(days), RANK_CONFIG["0"])["name"]
    
    print(f"正在获取{rank_name}排行前{count}名数据...")
    
    cmd = [
        "curl", "-s", "-L",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-H", "Accept: application/json, text/javascript, */*; q=0.01",
        "-H", "Referer: https://data.eastmoney.com/zjlx/detail.html",
        "--compressed",
        "--max-time", "60",
        "--retry", "3",
        url
    ]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=90)
        
        if result.returncode != 0:
            print(f"  ✗ 请求失败：{result.stderr}")
            return None
        
        data = json.loads(result.stdout)
        
        if data.get("rc") == 0:
            stocks = data.get("data", {}).get("diff", [])
            total = data.get("data", {}).get("total", 0)
            print(f"  ✓ 成功获取 {len(stocks)} 条数据（市场总股票数：{total}）")
            return stocks[:count]
        else:
            print(f"  ✗ API 错误：{data}")
            return None
            
    except subprocess.TimeoutExpired:
        print("  ✗ 请求超时")
        return None
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON 解析失败：{e}")
        return None


# ==================== 数据处理 ====================

def process_api_data(raw_stocks, days="0"):
    """处理 API 返回的原始数据"""
    config = RANK_CONFIG.get(str(days), RANK_CONFIG["0"])
    rank_name = config["name"]
    
    processed = []
    for i, stock in enumerate(raw_stocks, 1):
        item = {"排名": i}
        
        # 遍历 API 字段，自动映射到中文名称
        for api_field, value in stock.items():
            if api_field in FIELD_MAPPING:
                chinese_name = FIELD_MAPPING[api_field]
                item[chinese_name] = format_value(value, chinese_name)
        
        # 添加排行类型
        item["排行类型"] = rank_name
        processed.append(item)
    
    return processed


# ==================== 数据保存 ====================

def save_data(stocks, days, timestamp):
    """保存数据到文件"""
    config = RANK_CONFIG.get(str(days), RANK_CONFIG["0"])
    rank_name = config["name"]
    suffix = config["suffix"]
    
    # 创建日期目录
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join(BASE_OUTPUT_DIR, today)
    os.makedirs(output_dir, exist_ok=True)
    
    json_file = f"capital_flow_{suffix}_{timestamp}.json"
    csv_file = f"capital_flow_{suffix}_{timestamp}.csv"
    
    # 保存 JSON
    json_path = os.path.join(output_dir, json_file)
    output = {
        "获取时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "排行类型": rank_name,
        "数据条数": len(stocks),
        "数据来源": "东方财富网 - 个股资金流",
        "数据网址": "https://data.eastmoney.com/zjlx/detail.html",
        "字段映射": FIELD_MAPPING,
        "数据": stocks
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  ✓ JSON: {json_path}")
    
    # 保存 CSV
    csv_path = os.path.join(output_dir, csv_file)
    
    # 根据排行类型生成表头
    if rank_name == "今日":
        headers = ["排名", "代码", "名称", "最新价", "今日涨跌幅",
                   "今日主力净流入 - 净额", "今日主力净流入 - 净占比",
                   "今日超大单净流入 - 净额", "今日超大单净流入 - 净占比",
                   "今日大单净流入 - 净额", "今日大单净流入 - 净占比",
                   "今日中单净流入 - 净额", "今日中单净流入 - 净占比",
                   "今日小单净流入 - 净额", "今日小单净流入 - 净占比"]
    else:
        headers = ["排名", "代码", "名称", "最新价", f"{rank_name}涨跌幅",
                   f"{rank_name}主力净流入 - 净额", f"{rank_name}主力净流入 - 净占比",
                   f"{rank_name}超大单净流入 - 净额", f"{rank_name}超大单净流入 - 净占比",
                   f"{rank_name}大单净流入 - 净额", f"{rank_name}大单净流入 - 净占比",
                   f"{rank_name}中单净流入 - 净额", f"{rank_name}中单净流入 - 净占比",
                   f"{rank_name}小单净流入 - 净额", f"{rank_name}小单净流入 - 净占比"]
    
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for stock in stocks:
            row = [stock.get(h, "") for h in headers]
            writer.writerow(row)
    print(f"  ✓ CSV: {csv_path}")
    
    return json_path, csv_path


# ==================== 摘要打印 ====================

def print_summary(stocks, days):
    """打印数据摘要"""
    config = RANK_CONFIG.get(str(days), RANK_CONFIG["0"])
    rank_name = config["name"]
    
    print()
    print("="*80)
    print(f"📊 东方财富{rank_name}排行个股资金流数据 - 获取完成")
    print("="*80)
    print(f"获取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"排行类型：{rank_name}")
    print(f"数据条数：{len(stocks)}")
    print(f"输出目录：{BASE_OUTPUT_DIR}/{datetime.now().strftime('%Y-%m-%d')}")
    print()
    
    if stocks:
        print(f"🔥 {rank_name}排行前 10 名主力净流入:")
        print("-"*80)
        print(f"{'排名':<4} {'代码':<8} {'名称':<10} {'最新价':<8} {rank_name+'涨跌':<10} {'主力净流入':<12} {'净占比':<10}")
        print("-"*80)
        
        for stock in stocks[:10]:
            code = stock.get('代码', 'N/A')
            name = stock.get('名称', 'N/A')
            price = stock.get('最新价', 'N/A')
            change = stock.get(f'{rank_name}涨跌幅', 'N/A')
            inflow = stock.get(f'{rank_name}主力净流入 - 净额', 'N/A')
            ratio = stock.get(f'{rank_name}主力净流入 - 净占比', 'N/A')
            print(f"{stock.get('排名', 'N/A'):<4} {code:<8} {name:<10} {price:<8} {change:<10} {inflow:<12} {ratio:<10}")
        
        print("-"*80)
    
    print("="*80)


# ==================== 主函数 ====================

def main():
    # 解析参数
    days = sys.argv[1] if len(sys.argv) > 1 else "0"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    if days not in ["0", "3", "5", "10"]:
        print("错误：days 参数必须是 0, 3, 5, 或 10")
        print("用法：python3 fetch_capital_flow_api.py [days] [count]")
        print("  days: 0=今日，3=3 日，5=5 日，10=10 日（默认 0）")
        print("  count: 获取条数（默认 100）")
        sys.exit(1)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print()
    print("="*80)
    print("东方财富个股资金流 API 数据获取脚本（优化版）")
    print("="*80)
    print()
    
    # 获取数据
    raw_stocks = fetch_data_via_curl(days, count)
    
    if not raw_stocks:
        print()
        print("❌ 获取数据失败")
        print()
        print("可能原因:")
        print("  1. 网络连接问题")
        print("  2. API 端点变更")
        print("  3. 请求频率限制")
        print()
        sys.exit(1)
    
    # 处理数据
    print()
    print("正在处理数据...")
    processed_stocks = process_api_data(raw_stocks, days)
    print(f"  ✓ 处理完成 {len(processed_stocks)} 条数据")
    
    # 保存数据
    print()
    print("正在保存数据...")
    save_data(processed_stocks, days, timestamp)
    
    # 打印摘要
    print_summary(processed_stocks, days)
    
    print()
    print("✅ 全部完成!")
    print()


if __name__ == "__main__":
    main()
