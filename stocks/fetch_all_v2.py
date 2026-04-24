#!/usr/bin/env python3
"""
全市场历史数据批量获取 - 腾讯财经 API 版 v2
获取 2023-2024 年历史数据

鹏总专用 - 2026 年 4 月 7 日
"""

import urllib.request
import pandas as pd
import json
import os
import time
from pathlib import Path
from datetime import datetime

# ==================== 配置区域 ====================
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
START_DATE = '2023-01-01'
END_DATE = '2024-12-31'
BATCH_SIZE = 50
DELAY = 0.1
# ================================================

DATA_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("📊 全市场历史数据批量获取 v2")
print("=" * 70)

# 读取股票列表
stock_list_file = '/home/admin/.openclaw/workspace/stocks/all_stocks_list.csv'
df_stocks = pd.read_csv(stock_list_file)
print(f"✅ 读取到 {len(df_stocks)} 只股票")

total = len(df_stocks)
success = 0
skip = 0
fail = 0

for batch_start in range(0, total, BATCH_SIZE):
    batch_end = min(batch_start + BATCH_SIZE, total)
    
    print(f"\n{'='*70}")
    print(f"批次 {batch_start//BATCH_SIZE + 1}: [{batch_start+1}-{batch_end}]")
    print(f"{'='*70}")
    
    for i in range(batch_start, batch_end):
        row = df_stocks.iloc[i]
        ts_code = row['ts_code']
        name = row['name']
        
        if ts_code.endswith('.SZ'):
            qt_code = 'sz' + ts_code.replace('.SZ', '')
        elif ts_code.endswith('.SH'):
            qt_code = 'sh' + ts_code.replace('.SH', '')
        else:
            continue
        
        file_name = f"{ts_code.replace('.', '_')}.csv"
        file_path = DATA_DIR / file_name
        
        print(f"[{i+1}/{total}] {ts_code} {name}...", end=' ')
        
        try:
            url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={qt_code},day,,,600,bfq"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode('utf-8')
                data = json.loads(content)
                
                if 'data' in data and qt_code in data['data'] and 'day' in data['data'][qt_code]:
                    klines = data['data'][qt_code]['day']
                    
                    # 处理 6 列或 7 列
                    if len(klines[0]) == 7:
                        df = pd.DataFrame(klines, columns=['date', 'open', 'close', 'high', 'low', 'volume', 'turnover'])
                    else:
                        df = pd.DataFrame(klines, columns=['date', 'open', 'close', 'high', 'low', 'volume'])
                    
                    df['ts_code'] = ts_code
                    df['date'] = pd.to_datetime(df['date'])
                    
                    # 过滤日期
                    df = df[(df['date'] >= START_DATE) & (df['date'] <= END_DATE)]
                    
                    if len(df) > 0:
                        # 合并现有数据
                        if file_path.exists():
                            existing_df = pd.read_csv(file_path)
                            if 'trade_date' in existing_df.columns:
                                existing_df['trade_date'] = pd.to_datetime(existing_df['trade_date'])
                                existing_df = existing_df.rename(columns={'trade_date': 'date'})
                            
                            combined = pd.concat([existing_df, df], ignore_index=True)
                            combined = combined.drop_duplicates(subset=['date'], keep='last')
                            combined = combined.sort_values('date').reset_index(drop=True)
                            df = combined
                            print(f"合并后{len(df)}条", end=' ')
                        
                        df.to_csv(file_path, index=False, encoding='utf-8-sig')
                        print(f"✅ {len(df)}条")
                        success += 1
                    else:
                        print("❌ 无数据")
                        fail += 1
                else:
                    print("❌ 解析失败")
                    fail += 1
            
            time.sleep(DELAY)
            
        except Exception as e:
            print(f"❌ {e}")
            fail += 1
    
    # 保存进度
    progress_file = DATA_DIR / f'progress_batch_{batch_start//BATCH_SIZE}.json'
    with open(progress_file, 'w') as f:
        json.dump({'batch': batch_start//BATCH_SIZE, 'success': success, 'fail': fail}, f)
    
    print(f"\n批次完成：成功={success} 失败={fail}")

print("\n" + "=" * 70)
print(f"完成！成功={success} 跳过={skip} 失败={fail}")
print("=" * 70)
