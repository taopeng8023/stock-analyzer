#!/usr/bin/env python3
"""
使用Tushare API更新今日行情数据到历史文件
2026-04-15 凯文记录：使用现有Tushare脚本补充数据
"""
import requests
import json
import os
from datetime import datetime

# Tushare配置
TOKEN = 'a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4'
api_url = 'http://api.tushare.pro'
DATA_DIR = '/home/admin/.openclaw/workspace/stocks/data_history_2022_2026'

print("="*80)
print("Tushare更新今日行情数据")
print("="*80)
print(f"开始时间: {datetime.now()}")

# 获取今日行情
print("\n获取20260415行情数据...")

payload = {
    'api_name': 'daily',
    'token': TOKEN,
    'params': {'trade_date': '20260415'},
    'fields': 'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
}

resp = requests.post(api_url, json=payload, timeout=30)
result = resp.json()

if result.get('code') != 0:
    print(f"API错误: {result.get('msg')}")
    exit(1)

data = result.get('data')
if not data or 'items' not in data:
    print("无数据返回")
    exit(1)

items = data['items']
fields = data.get('fields', [])
print(f"获取到 {len(items)} 条数据")
print(f"字段: {fields}")

print(f"示例数据:")
print(f"  {items[0]}")

# 更新历史文件
print("\n更新历史数据文件...")
updated = 0
skipped = 0

for item in items:
    # 解析数据项
    ts_code = item[0]           # ts_code
    trade_date = item[1]        # trade_date
    open_p = item[2]            # open
    high = item[3]              # high
    low = item[4]               # low
    close = item[5]             # close
    pre_close = item[6]         # pre_close
    change = item[7]            # change
    pct_chg = item[8]           # pct_chg
    vol = item[9]               # vol
    amount = item[10]           # amount
    
    code = ts_code.split('.')[0]  # 去掉市场后缀
    
    file_path = os.path.join(DATA_DIR, f"{code}.json")
    
    if not os.path.exists(file_path):
        skipped += 1
        continue
    
    try:
        with open(file_path, 'r') as f:
            hist = json.load(f)
        
        if 'items' not in hist:
            skipped += 1
            continue
        
        # 检查是否已有今日数据
        dates = [item[1] for item in hist['items']]
        
        if trade_date in dates:
            skipped += 1
            continue
        
        # 构建新数据项 (与原格式一致)
        new_item = [
            ts_code,                    # ts_code
            trade_date,                 # trade_date
            open_p,                     # open
            high,                       # high
            low,                        # low
            close,                      # close
            pre_close,                  # pre_close
            change,                     # change
            pct_chg,                    # pct_chg
            vol,                        # vol
            amount,                     # amount
        ]
        
        hist['items'].append(new_item)
        
        # 更新元数据
        hist['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        hist['record_count'] = len(hist['items'])
        
        # 保存
        with open(file_path, 'w') as f:
            json.dump(hist, f)
        
        updated += 1
        
        if updated <= 10:
            print(f"  ✅ {code}: ¥{close:.2f} ({pct_chg:.2f}%)")
        
    except Exception as e:
        skipped += 1

print(f"\n更新统计:")
print(f"  成功更新: {updated}股")
print(f"  跳过: {skipped}股")

# 验证持仓股票
print("\n验证持仓股票数据:")
holdings = ['002709', '600089', '603739', '600163']

for code in holdings:
    file_path = os.path.join(DATA_DIR, f"{code}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            hist = json.load(f)
        
        if 'items' in hist:
            latest = hist['items'][-1]
            print(f"  {code}: 最新日期={latest[1]}, 收盘={latest[5]}")

print(f"\n完成时间: {datetime.now()}")

# 记录操作
print("\n💡 操作记录:")
print("  脚本位置: /home/admin/.openclaw/workspace/stocks/")
print("  数据源: Tushare API")
print("  Token: a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4")
print("  API接口: http://api.tushare.pro")
print("  接口名称: daily (日线行情)")