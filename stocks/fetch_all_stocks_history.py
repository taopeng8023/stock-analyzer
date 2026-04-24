#!/usr/bin/env python3
"""
全市场历史数据批量获取脚本
使用 Tushare 获取 2023-2024 年历史数据，追加到现有数据中

鹏总专用 - 2026 年 4 月 7 日
"""

import tushare as ts
import pandas as pd
import os
import time
from datetime import datetime
from pathlib import Path

# ==================== 配置区域 ====================
TS_TOKEN = 'a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4'
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
START_DATE = '20230101'  # 开始日期
END_DATE = '20241231'    # 结束日期
DELAY = 1.0  # 请求间隔（秒）- 避免频率限制
# ================================================

# 初始化 Tushare
ts.set_token(TS_TOKEN)
pro = ts.pro_api()

# 创建数据目录
DATA_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("📊 全市场历史数据批量获取")
print("=" * 70)
print(f"数据目录：{DATA_DIR}")
print(f"日期范围：{START_DATE} 至 {END_DATE}")
print(f"请求间隔：{DELAY}秒")
print("=" * 70)

# 获取股票列表
print("\n📋 获取股票列表...")
df_stocks = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,market')
print(f"✅ 全市场共 {len(df_stocks)} 只股票")

# 统计
total = len(df_stocks)
success = 0
skip = 0
fail = 0

results = []

# 批量获取
for i, row in df_stocks.iterrows():
    ts_code = row['ts_code']
    name = row['name']
    market = row['market']
    
    # 文件名
    file_name = f"{ts_code.replace('.', '_')}.csv"
    file_path = DATA_DIR / file_name
    
    print(f"\n[{i+1}/{total}] {ts_code} {name} ({market})...", end=' ')
    
    try:
        # 检查是否已存在
        if file_path.exists():
            # 读取现有数据
            existing_df = pd.read_csv(file_path)
            
            # 检查日期范围
            if 'trade_date' in existing_df.columns:
                existing_dates = pd.to_datetime(existing_df['trade_date'].astype(str))
                start_in_range = (existing_dates >= pd.to_datetime(START_DATE)).any()
                end_in_range = (existing_dates <= pd.to_datetime(END_DATE)).any()
                
                if start_in_range and end_in_range and len(existing_df) > 200:
                    print("⏭️  数据已存在，跳过")
                    skip += 1
                    results.append({'ts_code': ts_code, 'name': name, 'status': 'skipped', 'records': len(existing_df)})
                    continue
        
        # 获取数据
        df = pro.daily(ts_code=ts_code, start_date=START_DATE, end_date=END_DATE)
        
        if df is not None and not df.empty:
            # 如果文件已存在，合并数据
            if file_path.exists():
                existing_df = pd.read_csv(file_path)
                combined = pd.concat([existing_df, df], ignore_index=True)
                combined = combined.drop_duplicates(subset=['trade_date'], keep='last')
                combined = combined.sort_values('trade_date').reset_index(drop=True)
                df = combined
                print(f"📊 合并后 {len(df)} 条", end=' ')
            
            # 保存数据
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"✅ {len(df)}条")
            success += 1
            results.append({'ts_code': ts_code, 'name': name, 'status': 'success', 'records': len(df)})
        else:
            print("❌ 无数据")
            fail += 1
            results.append({'ts_code': ts_code, 'name': name, 'status': 'no_data', 'records': 0})
        
        # 延迟
        if (i+1) % 10 == 0:
            time.sleep(DELAY)
        
    except Exception as e:
        print(f"❌ 错误：{e}")
        fail += 1
        results.append({'ts_code': ts_code, 'name': name, 'status': 'error', 'error': str(e)})
    
    # 每 100 只股票打印进度
    if (i+1) % 100 == 0:
        print(f"\n📊 进度：{i+1}/{total} ({(i+1)/total*100:.1f}%)  成功：{success}  跳过：{skip}  失败：{fail}")

# 最终统计
print("\n" + "=" * 70)
print("📊 数据获取完成")
print("=" * 70)
print(f"总计：{total} 只股票")
print(f"成功：{success} 只")
print(f"跳过：{skip} 只 (数据已存在)")
print(f"失败：{fail} 只")
print("=" * 70)

# 保存报告
report_path = DATA_DIR / 'fetch_report.json'
import json
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump({
        'fetch_time': datetime.now().isoformat(),
        'start_date': START_DATE,
        'end_date': END_DATE,
        'summary': {
            'total': total,
            'success': success,
            'skip': skip,
            'failed': fail
        },
        'details': results
    }, f, indent=2, ensure_ascii=False)

print(f"\n💾 报告已保存至：{report_path}")
print(f"\n💾 数据目录：{DATA_DIR}")
