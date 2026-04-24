#!/usr/bin/env python3
"""
全市场历史数据批量获取 - 腾讯财经 API 版
获取 2023-2024 年历史数据，追加到现有数据中

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
START_DATE = '20230101'  # 开始日期
END_DATE = '20241231'    # 结束日期
BATCH_SIZE = 100  # 每批处理数量
DELAY = 0.05  # 请求间隔（秒）
# ================================================

# 创建数据目录
DATA_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("📊 全市场历史数据批量获取 - 腾讯财经 API")
print("=" * 70)
print(f"数据目录：{DATA_DIR}")
print(f"日期范围：{START_DATE} 至 {END_DATE}")
print(f"每批数量：{BATCH_SIZE}")
print("=" * 70)

# 读取股票列表
stock_list_file = '/home/admin/.openclaw/workspace/stocks/all_stocks_list.csv'
if os.path.exists(stock_list_file):
    df_stocks = pd.read_csv(stock_list_file)
    print(f"\n✅ 读取到 {len(df_stocks)} 只股票")
else:
    print("❌ 股票列表文件不存在")
    exit(1)

# 统计
total = len(df_stocks)
success = 0
skip = 0
fail = 0

results = []

# 批量获取
for batch_start in range(0, total, BATCH_SIZE):
    batch_end = min(batch_start + BATCH_SIZE, total)
    batch_stocks = df_stocks.iloc[batch_start:batch_end]
    
    print(f"\n{'='*70}")
    print(f"📦 处理批次 {batch_start//BATCH_SIZE + 1}: [{batch_start+1}-{batch_end}] / {total}")
    print(f"{'='*70}")
    
    for i, row in batch_stocks.iterrows():
        ts_code = row['ts_code']
        name = row['name']
        market = row['market']
        
        # 转换为腾讯格式 (sz000001, sh600519)
        if ts_code.endswith('.SZ'):
            qt_code = 'sz' + ts_code.replace('.SZ', '')
        elif ts_code.endswith('.SH'):
            qt_code = 'sh' + ts_code.replace('.SH', '')
        elif ts_code.endswith('.BJ'):
            continue  # 跳过北交所
        else:
            continue
        
        file_name = f"{ts_code.replace('.', '_')}.csv"
        file_path = DATA_DIR / file_name
        
        print(f"[{i+1}/{total}] {ts_code} {name}...", end=' ')
        
        try:
            # 检查是否已存在
            if file_path.exists():
                existing_df = pd.read_csv(file_path)
                if 'trade_date' in existing_df.columns or 'date' in existing_df.columns:
                    date_col = 'trade_date' if 'trade_date' in existing_df.columns else 'date'
                    existing_dates = pd.to_datetime(existing_df[date_col].astype(str))
                    
                    start_in_range = (existing_dates >= pd.to_datetime(START_DATE)).any()
                    end_in_range = (existing_dates <= pd.to_datetime(END_DATE)).any()
                    
                    if start_in_range and end_in_range and len(existing_df) > 400:
                        print("⏭️  数据已存在")
                        skip += 1
                        results.append({'ts_code': ts_code, 'name': name, 'status': 'skipped', 'records': len(existing_df)})
                        continue
            
            # 腾讯财经 API - 获取历史 K 线
            url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={qt_code},day,,,600,bfq"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode('utf-8')
                data = json.loads(content)
                
                if 'data' in data and qt_code in data['data'] and 'day' in data['data'][qt_code]:
                    klines = data['data'][qt_code]['day']
                    
                    # 转换为 DataFrame (处理 6 列或 7 列)
                    if len(klines[0]) == 7:
                        df = pd.DataFrame(klines, columns=['date', 'open', 'close', 'high', 'low', 'volume', 'turnover'])
                    else:
                        df = pd.DataFrame(klines, columns=['date', 'open', 'close', 'high', 'low', 'volume'])
                    df['ts_code'] = ts_code
                    
                    # 过滤日期范围
                    df['date'] = pd.to_datetime(df['date'])
                    df = df[(df['date'] >= pd.to_datetime(START_DATE)) & (df['date'] <= pd.to_datetime(END_DATE))]
                    
                    if len(df) > 0:
                        # 如果文件存在，合并
                        if file_path.exists():
                            existing_df = pd.read_csv(file_path)
                            if 'trade_date' in existing_df.columns:
                                existing_df['trade_date'] = pd.to_datetime(existing_df['trade_date'])
                            
                            combined = pd.concat([existing_df, df], ignore_index=True)
                            date_col = 'trade_date' if 'trade_date' in combined.columns else 'date'
                            combined = combined.drop_duplicates(subset=[date_col], keep='last')
                            combined = combined.sort_values(date_col).reset_index(drop=True)
                            df = combined
                        
                        df.to_csv(file_path, index=False, encoding='utf-8-sig')
                        print(f"✅ {len(df)}条")
                        success += 1
                        results.append({'ts_code': ts_code, 'name': name, 'status': 'success', 'records': len(df)})
                    else:
                        print("❌ 日期范围内无数据")
                        fail += 1
                        results.append({'ts_code': ts_code, 'name': name, 'status': 'no_data', 'records': 0})
                else:
                    print("❌ 数据格式错误")
                    fail += 1
                    results.append({'ts_code': ts_code, 'name': name, 'status': 'parse_error', 'records': 0})
            
            # 延迟
            time.sleep(DELAY)
            
        except Exception as e:
            print(f"❌ {e}")
            fail += 1
            results.append({'ts_code': ts_code, 'name': name, 'status': 'error', 'error': str(e)})
    
    # 批次统计
    print(f"\n📊 批次完成：成功={success} 跳过={skip} 失败={fail}")
    
    # 保存进度
    progress_file = DATA_DIR / f'fetch_progress_batch_{batch_start//BATCH_SIZE}.json'
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump({
            'batch': batch_start//BATCH_SIZE,
            'processed': batch_end,
            'total': total,
            'summary': {'success': success, 'skip': skip, 'failed': fail},
            'details': results
        }, f, indent=2, ensure_ascii=False)

# 最终统计
print("\n" + "=" * 70)
print("📊 数据获取完成")
print("=" * 70)
print(f"总计：{total} 只股票")
print(f"成功：{success} 只")
print(f"跳过：{skip} 只")
print(f"失败：{fail} 只")
print("=" * 70)

# 保存总报告
report_path = DATA_DIR / 'fetch_report_final.json'
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
print(f"💾 数据目录：{DATA_DIR}")
print(f"📁 文件数量：{len(list(DATA_DIR.glob('*.csv')))}")
