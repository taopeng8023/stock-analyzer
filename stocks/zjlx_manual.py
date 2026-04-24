#!/usr/bin/env python3
"""
手动获取资金流数据 - 使用已有数据或提示用户手动输入
"""
import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data")

print("="*70)
print("资金流数据获取方案")
print("="*70)

print("\n问题：东方财富API今日被限流")
print("\n替代方案：")

# 方案1：使用昨日数据
zjlx_yesterday = DATA_DIR / "zjlx_top50_20260415.json"

if zjlx_yesterday.exists():
    with open(zjlx_yesterday) as f:
        raw = json.load(f)
    
    print("\n方案1 - 使用昨日(2026-04-15)数据:")
    print(f"  文件: {zjlx_yesterday.name}")
    print(f"  数据条数: {len(raw) if isinstance(raw, list) else 'N/A'}")
    
    if isinstance(raw, list) and len(raw) > 0:
        print("\n  TOP10预览:")
        for item in raw[:10]:
            print(f"    {item.get('序号', '?')}. {item.get('代码', '?')} {item.get('名称', '?')}")
            print(f"       主力流入: {item.get('主力净流入', '?')}")

# 方案2：提示手动获取
print("\n方案2 - 手动获取今日数据:")
print("  1. 打开浏览器访问: https://data.eastmoney.com/zjlx/zjlx_list.html")
print("  2. 选择'主力净流入'排序")
print("  3. 复制TOP20数据给我")
print("  4. 我会帮你保存和分析")

# 方案3：等待明日自动获取
print("\n方案3 - 等待明日:")
print("  明日API限制可能解除")
print("  定时任务会自动获取")

print("\n建议使用方案2手动获取今日最新数据")
print("\n完成:", datetime.now())