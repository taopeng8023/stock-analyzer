#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✅ 可用脚本 - 东方财富 3 日排行个股资金流数据获取（优化版）

【状态】: ✅ 已优化（需 browser 工具配合手动操作）
【用途】: 获取 3 日排行前 100 名个股资金流数据
【用法】: 
  python3 fetch_3day_capital_flow.py [count]
  count: 获取前 N 名（默认 100）

【输出】:
  - JSON: /home/admin/.openclaw/workspace/data_files/capital_flow_3d_YYYYMMDD_HHMMSS.json
  - CSV: /home/admin/.openclaw/workspace/data_files/capital_flow_3d_YYYYMMDD_HHMMSS.csv

【示例】:
  # 获取 3 日排行前 100 名
  python3 fetch_3day_capital_flow.py 100
  
  # 获取 3 日排行前 50 名
  python3 fetch_3day_capital_flow.py 50

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

# 3 日排行字段说明
"""
东方财富网 3 日排行数据字段:
- f12: 股票代码
- f14: 股票名称
- f2: 最新价
- f3: 3 日涨跌幅
- f262: 3 日主力净流入
- f263: 3 日主力净占比
- f66: 超大单净流入（当日）
- f68: 大单净流入（当日）
- f70: 中单净流入（当日）
- f72: 小单净流入（当日）
"""


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
        val = float(str(value).replace('%', ''))
        return f"{val:.2f}%"
    except:
        return str(value)


# ==================== 使用说明 ====================

def print_instructions(count=100):
    """打印详细操作说明"""
    print()
    print("="*70)
    print("📊 东方财富 3 日排行个股资金流数据获取指南")
    print("="*70)
    print()
    print("⚠️  重要说明:")
    print("   由于东方财富网有验证码保护，需要通过 browser 工具手动获取数据")
    print("   本脚本提供详细的操作步骤和数据处理功能")
    print()
    print("📋 操作步骤:")
    print()
    print("步骤 1: 打开东方财富网个股资金流页面")
    print("-"*70)
    print("  在浏览器中打开或使用命令:")
    print(f"  browser open {BASE_URL}")
    print()
    
    print("步骤 2: 完成验证码")
    print("-"*70)
    print("  在打开的浏览器窗口中，手动拖动滑块完成拼图验证")
    print()
    
    print("步骤 3: 切换到 3 日排行")
    print("-"*70)
    print("  在页面上方找到排行选项卡，点击【3 日排行】")
    print("  选项卡位置：今日排行 | 3 日排行 | 5 日排行 | 10 日排行")
    print()
    print("  或使用 browser 命令点击:")
    print("""
  browser act <targetId> evaluate --fn "() => {
    const tabs = document.querySelectorAll('[class*=\\'tab\\'], [role*=\\'tab\\'], .tab-link');
    tabs.forEach(tab => {
      if(tab.textContent && tab.textContent.includes('3 日')) {
        tab.click();
        console.log('已切换到 3 日排行');
      }
    });
  }"
  """)
    print()
    
    print("步骤 4: 等待数据加载")
    print("-"*70)
    print("  browser act <targetId> wait --time-ms 10000")
    print("  (等待约 10 秒，确保数据完全加载)")
    print()
    
    print("步骤 5: 滚动页面触发数据加载")
    print("-"*70)
    print("  browser act <targetId> evaluate --fn \"() => {")
    print("    window.scrollTo(0, document.body.scrollHeight);")
    print("  }\"")
    print("  browser act <targetId> wait --time-ms 5000")
    print()
    
    print("步骤 6: 提取 3 日排行数据")
    print("-"*70)
    print("  使用以下 JavaScript 代码提取数据:")
    print()
    print(f"""  browser act <targetId> evaluate --fn "() => {{
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
          changePct: cells[5]?.textContent?.trim(),  // 3 日涨跌幅
          mainInflow: cells[6]?.textContent?.trim(),  // 3 日主力净流入
          mainRatio: cells[7]?.textContent?.trim()    // 3 日主力净占比
        }});
      }}
    }});
    return JSON.stringify({{count: data.length, data: data, type: '3 日排行'}});
  }}"
  """)
    print()
    
    print("步骤 7: 保存并处理数据")
    print("-"*70)
    print("  1. 将返回的 JSON 数据保存为文件，例如：data_3d.json")
    print("  2. 使用本脚本处理:")
    print(f"     python3 fetch_3day_capital_flow.py process data_3d.json {count}")
    print()
    
    print("="*70)
    print("📝 注意事项:")
    print("="*70)
    print("  1. 3 日排行显示的是近 3 个交易日的累计资金流数据")
    print("  2. 3 日涨跌幅也是 3 日累计涨跌幅")
    print("  3. 超大单/大单/中单/小单净流入通常显示当日数据")
    print("  4. 数据仅在交易日更新，周末和节假日无新数据")
    print("  5. 建议在市场收盘后（15:30 后）获取数据")
    print("="*70)
    print()


# ==================== 数据处理 ====================

def process_3day_data(input_file, count=100):
    """处理 3 日排行数据"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print()
    print("="*70)
    print("📊 处理 3 日排行数据")
    print("="*70)
    print(f"读取文件：{input_file}")
    
    # 读取数据
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # 提取数据
    if "数据" in raw_data:
        stocks = raw_data["数据"][:count]
    elif "data" in raw_data:
        stocks = raw_data["data"][:count]
    else:
        stocks = [raw_data] if isinstance(raw_data, dict) else raw_data[:count]
    
    print(f"处理数据（最多 {count} 条）...")
    print(f"成功处理 {len(stocks)} 条数据")
    print()
    
    # 保存 JSON
    json_file = f"capital_flow_3d_{timestamp}.json"
    json_path = os.path.join(OUTPUT_DIR, json_file)
    
    output = {
        "获取时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "排行类型": "3 日",
        "数据条数": len(stocks),
        "数据来源": "东方财富网 - 个股资金流",
        "数据网址": BASE_URL,
        "排序方式": "3 日主力净流入降序",
        "字段说明": {
            "排名": "3 日排行名次",
            "股票代码": "6 位股票代码",
            "股票名称": "股票简称",
            "最新价": "当前股价",
            "涨跌幅": "3 日累计涨跌幅",
            "主力净流入": "3 日主力净流入金额",
            "主力净占比": "3 日主力净流入占成交额比例"
        },
        "数据": stocks
    }
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  ✓ JSON: {json_path}")
    
    # 保存 CSV
    csv_file = f"capital_flow_3d_{timestamp}.csv"
    csv_path = os.path.join(OUTPUT_DIR, csv_file)
    
    headers = ["排名","股票代码","股票名称","最新价","涨跌幅",
               "主力净流入","主力净占比","排行类型",
               "超大单净流入","大单净流入","中单净流入","小单净流入"]
    
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for stock in stocks:
            row = [
                stock.get("排名", ""),
                stock.get("code", stock.get("股票代码", "")),
                stock.get("name", stock.get("股票名称", "")),
                stock.get("price", stock.get("最新价", "")),
                stock.get("changePct", stock.get("涨跌幅", "")),
                stock.get("mainInflow", stock.get("主力净流入", "")),
                stock.get("mainRatio", stock.get("主力净占比", "")),
                "3 日",
                stock.get("superInflow", stock.get("超大单净流入", "")),
                stock.get("bigInflow", stock.get("大单净流入", "")),
                stock.get("midInflow", stock.get("中单净流入", "")),
                stock.get("smallInflow", stock.get("小单净流入", ""))
            ]
            writer.writerow(row)
    print(f"  ✓ CSV: {csv_path}")
    
    # 打印摘要
    print()
    print("="*70)
    print("✅ 3 日排行数据处理完成!")
    print("="*70)
    print(f"排行类型：3 日")
    print(f"数据条数：{len(stocks)}")
    print(f"输出目录：{OUTPUT_DIR}")
    
    if stocks:
        print()
        print("🔥 3 日排行前 5 名主力净流入:")
        print("-"*70)
        print(f"{'排名':<4} {'代码':<8} {'名称':<10} {'3 日涨跌':<10} {'主力净流入':<12}")
        print("-"*70)
        for stock in stocks[:5]:
            code = stock.get('code', stock.get('股票代码', 'N/A'))
            name = stock.get('name', stock.get('股票名称', 'N/A'))
            change = stock.get('changePct', stock.get('涨跌幅', 'N/A'))
            inflow = stock.get('mainInflow', stock.get('主力净流入', 'N/A'))
            print(f"{stock.get('排名', 'N/A'):<4} {code:<8} {name:<10} {change:<10} {inflow:<12}")
        print("-"*70)
    
    print("="*70)
    print()
    
    return json_path, csv_path


# ==================== 主函数 ====================

def main():
    # 检查参数
    if len(sys.argv) < 2:
        print_instructions(100)
        return
    
    if sys.argv[1] == "process" and len(sys.argv) >= 3:
        # 处理已有数据文件
        input_file = sys.argv[2]
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 100
        
        if not os.path.exists(input_file):
            print(f"错误：文件不存在：{input_file}")
            sys.exit(1)
        
        process_3day_data(input_file, count)
    else:
        # 显示使用说明
        try:
            count = int(sys.argv[1])
        except ValueError:
            count = 100
        
        print_instructions(count)


if __name__ == "__main__":
    main()
