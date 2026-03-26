#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✅ 东方财富个股资金流 API 字段映射演示脚本

【状态】: ✅ 演示版本（使用模拟数据）
【用途】: 展示 API 字段到中文表头的自动映射关系
【用法】: python3 api_field_mapping_demo.py

【说明】: 由于网络限制，使用模拟数据演示字段映射逻辑
         实际使用时可替换为真实的 API 请求
"""

import json
import csv
import os
from datetime import datetime

# ==================== 配置 ====================
BASE_OUTPUT_DIR = "/home/admin/.openclaw/workspace/data_files/个股资金流"

# API 字段到中文表头的完整映射（根据东方财富 API 文档）
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
    "0": {"name": "今日", "suffix": "today", "sort_field": "f62"},
    "3": {"name": "3 日", "suffix": "3d", "sort_field": "f262"},
    "5": {"name": "5 日", "suffix": "5d", "sort_field": "f362"},
    "10": {"name": "10 日", "suffix": "10d", "sort_field": "f462"},
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
            return f"{val:.2f}%"
        elif "净额" in field_name or "流入" in field_name:
            if abs(val) >= 100000000:
                return f"{val/100000000:.2f}亿"
            elif abs(val) >= 10000:
                return f"{val/10000:.2f}万"
            else:
                return f"{val:.2f}"
        else:
            return f"{val:.2f}"
    except:
        return str(value)


def map_api_fields(raw_stock, rank_name="今日"):
    """将 API 字段映射到中文名称"""
    item = {}
    
    # 遍历 API 字段，自动映射
    for api_field, value in raw_stock.items():
        if api_field in FIELD_MAPPING:
            chinese_name = FIELD_MAPPING[api_field]
            item[chinese_name] = format_value(value, chinese_name)
    
    item["排行类型"] = rank_name
    return item


# ==================== 生成模拟数据 ====================

def generate_mock_data(rank_type="0", count=100):
    """生成模拟的 API 返回数据"""
    config = RANK_CONFIG.get(rank_type, RANK_CONFIG["0"])
    rank_name = config["name"]
    sort_field = config["sort_field"]
    
    # 真实股票数据（前 20 名）
    real_stocks = [
        {"f12": "601669", "f14": "中国电建", "f2": 7.19, "f3": 9.94, "f62": 2061000000, "f184": 16.13, "f66": 3311000000, "f67": 25.92, "f68": -1251000000, "f69": -9.79, "f70": -1173000000, "f71": -9.18, "f72": -887000000, "f73": -6.94},
        {"f12": "300502", "f14": "新易盛", "f2": 394.03, "f3": 4.03, "f62": 1604000000, "f184": 10.08, "f66": 1228000000, "f67": 7.72, "f68": 376000000, "f69": 2.36, "f70": -904000000, "f71": -5.68, "f72": -701000000, "f73": -4.40},
        {"f12": "601611", "f14": "中国核建", "f2": 19.21, "f3": 10.02, "f62": 1317000000, "f184": 23.00, "f66": 1444000000, "f67": 25.23, "f68": -128000000, "f69": -2.23, "f70": -582000000, "f71": -10.16, "f72": -735000000, "f73": -12.83},
        {"f12": "002463", "f14": "沪电股份", "f2": 81.18, "f3": 6.34, "f62": 1116000000, "f184": 10.71, "f66": 1185000000, "f67": 11.38, "f68": -69155800, "f69": -0.66, "f70": -407000000, "f71": -3.91, "f72": -709000000, "f73": -6.81},
        {"f12": "002165", "f14": "红宝丽", "f2": 12.76, "f3": 10.00, "f62": 1014000000, "f184": 42.57, "f66": 1058000000, "f67": 44.40, "f68": -43605000, "f69": -1.83, "f70": -395000000, "f71": -16.59, "f72": -619000000, "f73": -25.97},
    ]
    
    stocks = []
    for i in range(count):
        if i < len(real_stocks):
            # 使用真实数据
            stock = real_stocks[i].copy()
        else:
            # 生成模拟数据
            stock = {
                "f12": f"{600000+i:06d}",
                "f14": f"股票{i+1}",
                "f2": 10 + i * 0.5,
                "f3": 5 + i * 0.1,
                sort_field: (20 - i * 0.2) * 100000000,
            }
            # 添加其他字段
            for field in FIELD_MAPPING.keys():
                if field not in stock:
                    if "净占比" in FIELD_MAPPING[field]:
                        stock[field] = 10 - i * 0.1
                    elif "净额" in FIELD_MAPPING[field] or "流入" in FIELD_MAPPING[field]:
                        stock[field] = (10 - i * 0.1) * 100000000 * (1 if i % 2 == 0 else -1)
                    else:
                        stock[field] = 10 + i * 0.5
        
        stocks.append(stock)
    
    return stocks


# ==================== 数据保存 ====================

def save_data(stocks, rank_type, timestamp):
    """保存数据到文件"""
    config = RANK_CONFIG.get(rank_type, RANK_CONFIG["0"])
    rank_name = config["name"]
    suffix = config["suffix"]
    
    # 创建日期目录
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join(BASE_OUTPUT_DIR, today)
    os.makedirs(output_dir, exist_ok=True)
    
    json_file = f"capital_flow_{suffix}_demo_{timestamp}.json"
    csv_file = f"capital_flow_{suffix}_demo_{timestamp}.csv"
    
    # 处理数据 - 字段映射
    processed = []
    for i, stock in enumerate(stocks, 1):
        item = map_api_fields(stock, rank_name)
        item["排名"] = i
        processed.insert(0, item) if i == 1 else processed.append(item)
    
    # 保存 JSON
    json_path = os.path.join(output_dir, json_file)
    output = {
        "获取时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "排行类型": rank_name,
        "数据条数": len(processed),
        "数据来源": "东方财富网 - 个股资金流（演示）",
        "数据网址": "https://data.eastmoney.com/zjlx/detail.html",
        "字段映射说明": FIELD_MAPPING,
        "数据": processed
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  ✓ JSON: {json_path}")
    
    # 保存 CSV
    csv_path = os.path.join(output_dir, csv_file)
    
    # 生成表头
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
        for stock in processed:
            row = [stock.get(h, "") for h in headers]
            writer.writerow(row)
    print(f"  ✓ CSV: {csv_path}")
    
    return processed


# ==================== 主函数 ====================

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print()
    print("="*80)
    print("东方财富个股资金流 API 字段映射演示")
    print("="*80)
    print()
    print("📋 API 字段映射说明:")
    print("-"*80)
    print(f"{'API 字段':<10} {'中文名称':<30} {'说明':<40}")
    print("-"*80)
    
    for api_field, chinese_name in list(FIELD_MAPPING.items())[:15]:
        desc = "基础字段" if api_field in ["f12", "f14", "f2", "f3"] else "资金流字段"
        print(f"{api_field:<10} {chinese_name:<30} {desc:<40}")
    
    print("-"*80)
    print(f"共 {len(FIELD_MAPPING)} 个字段映射")
    print()
    
    # 生成 4 种排行数据
    for days in ["0", "3", "5", "10"]:
        config = RANK_CONFIG[days]
        rank_name = config["name"]
        
        print(f"正在生成{rank_name}排行数据...")
        mock_data = generate_mock_data(days, 100)
        processed = save_data(mock_data, days, timestamp)
        
        print(f"  ✓ {rank_name}排行前 5 名:")
        for stock in processed[:5]:
            code = stock.get('代码', 'N/A')
            name = stock.get('名称', 'N/A')
            inflow = stock.get(f'{rank_name}主力净流入 - 净额', 'N/A')
            print(f"    {stock.get('排名')}. {name}({code}) 主力净流入：{inflow}")
        print()
    
    print("="*80)
    print("✅ 演示完成！")
    print("="*80)
    print()
    print("📁 输出目录:")
    print(f"   {BASE_OUTPUT_DIR}/{datetime.now().strftime('%Y-%m-%d')}/")
    print()
    print("📝 说明:")
    print("   由于网络限制，本脚本使用模拟数据演示字段映射逻辑")
    print("   实际使用时，可将 generate_mock_data() 替换为真实的 API 请求")
    print("   API 地址：https://push2.eastmoney.com/api/qt/clist/get")
    print()


if __name__ == "__main__":
    main()
