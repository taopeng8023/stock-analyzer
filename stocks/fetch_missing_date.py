#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充缺失的历史数据
专门补充 2025-03-27 这一天的数据
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime

# Tushare Token
TS_TOKEN = os.environ.get('TS_TOKEN', '')

DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')

# 需要补充的日期
MISSING_DATE = '20250327'


def get_stock_list():
    """获取所有股票代码列表"""
    # 从已存在的数据文件中获取股票代码
    stock_files = list(DATA_DIR.glob('*.json'))
    return [f.stem for f in stock_files]


def fetch_single_day_data(stock_code, trade_date):
    """获取单只股票单日的数据"""
    if not TS_TOKEN:
        print(f"❌ 未设置 TS_TOKEN 环境变量")
        return None
    
    try:
        import tushare as ts
        ts.set_token(TS_TOKEN)
        pro = ts.pro_api()
        
        # 获取日线数据
        df = pro.daily(ts_code=stock_code, start_date=trade_date, end_date=trade_date)
        
        if df.empty:
            return None
        
        row = df.iloc[0]
        
        # 转换为标准格式
        data = {
            '日期': trade_date,
            '开盘': float(row['open']),
            '收盘': float(row['close']),
            '最高': float(row['high']),
            '最低': float(row['low']),
            '成交量': float(row['vol']),
            '成交额': float(row['amount']),
            '涨跌幅': float(row['pct_chg']) if 'pct_chg' in row else 0.0
        }
        
        return data
        
    except Exception as e:
        print(f"   获取失败：{e}")
        return None


def merge_data(filepath, new_data):
    """将新数据合并到现有文件中"""
    try:
        # 读取现有数据
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查是否已存在该日期
        existing_dates = [d['日期'] for d in data]
        if new_data['日期'] in existing_dates:
            print(f"   ⏭️  数据已存在，跳过")
            return False
        
        # 插入到正确位置（按日期排序）
        data.append(new_data)
        data.sort(key=lambda x: x['日期'])
        
        # 保存
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
        
    except Exception as e:
        print(f"   合并失败：{e}")
        return False


def main():
    print("=" * 70)
    print("📊 补充缺失的历史数据")
    print("=" * 70)
    print(f"缺失日期：{MISSING_DATE}")
    print(f"数据目录：{DATA_DIR}")
    print("=" * 70)
    
    if not TS_TOKEN:
        print("\n❌ 错误：未设置 TS_TOKEN 环境变量")
        print("💡 请运行：export TS_TOKEN='your_token'")
        return
    
    # 获取所有股票代码
    stock_codes = get_stock_list()
    total = len(stock_codes)
    
    print(f"\n发现 {total} 只股票需要补充数据\n")
    
    # 统计
    success = 0
    skip = 0
    fail = 0
    
    import tushare as ts
    ts.set_token(TS_TOKEN)
    pro = ts.pro_api()
    
    for i, stock_code in enumerate(stock_codes, 1):
        print(f"[{i}/{total}] {stock_code}...", end=" ")
        
        filepath = DATA_DIR / f"{stock_code}.json"
        
        if not filepath.exists():
            print("❌ 文件不存在")
            fail += 1
            continue
        
        # 尝试获取单日数据
        new_data = fetch_single_day_data(stock_code, MISSING_DATE)
        
        if new_data is None:
            print("⚠️ 无数据")
            skip += 1
            continue
        
        # 合并数据
        if merge_data(filepath, new_data):
            print(f"✅ 补充成功 ({new_data['开盘']:.2f}→{new_data['收盘']:.2f})")
            success += 1
        else:
            print("⏭️ 已存在")
            skip += 1
        
        # 限流（Tushare 有频率限制）
        if i % 100 == 0:
            print(f"\n💤 休息 2 秒...")
            time.sleep(2)
        else:
            time.sleep(0.1)
    
    # 打印统计
    print("\n" + "=" * 70)
    print("📊 补充完成")
    print("=" * 70)
    print(f"   成功：{success} 只")
    print(f"   跳过：{skip} 只")
    print(f"   失败：{fail} 只")
    print(f"   总计：{total} 只")
    print("=" * 70)


if __name__ == '__main__':
    main()
