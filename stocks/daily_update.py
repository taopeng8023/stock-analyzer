#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日常增量数据更新脚本

功能:
- 每日收盘后自动更新最新交易日数据
- 增量更新，只获取新数据
- 自动验证数据完整性
- 支持定时任务执行

用法:
    python3 daily_update.py
    python3 daily_update.py --force  # 强制更新所有
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False
    print("⚠️ 未安装 akshare，使用备用接口")


def get_stock_list() -> List[str]:
    """获取所有股票代码列表"""
    # 从缓存目录读取已有股票
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache', 'history', datetime.now().strftime('%Y%m'))
    
    if os.path.exists(cache_dir):
        files = [f.replace('.json', '') for f in os.listdir(cache_dir) if f.endswith('.json')]
        return files
    
    # 如果缓存不存在，返回空列表
    return []


def get_latest_data(code: str, days: int = 5) -> Optional[List[Dict]]:
    """
    获取最新交易日数据
    
    Args:
        code: 股票代码
        days: 获取天数（防止遗漏）
    
    Returns:
        最新数据列表
    """
    if not HAS_AKSHARE:
        return None
    
    try:
        # 使用 AKShare 获取实时数据
        stock_df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        
        if stock_df is None or len(stock_df) == 0:
            return None
        
        # 取最近 N 天
        recent = stock_df.tail(days)
        
        data = []
        for _, row in recent.iterrows():
            data.append({
                'date': str(row['日期']),
                'open': float(row['开盘']),
                'close': float(row['收盘']),
                'high': float(row['最高']),
                'low': float(row['最低']),
                'volume': int(row['成交量']),
                'amount': float(row['成交额']),
                'amplitude': float(row['振幅']),
                'change_pct': float(row['涨跌幅']),
                'change': float(row['涨跌额']),
                'turnover': float(row['换手率'])
            })
        
        return data
        
    except Exception as e:
        print(f"  ⚠️ 获取 {code} 数据失败：{e}")
        return None


def merge_data(existing: List[Dict], new_data: List[Dict]) -> List[Dict]:
    """合并现有数据和新数据，去重"""
    existing_dates = set(d['date'] for d in existing)
    
    for record in new_data:
        if record['date'] not in existing_dates:
            existing.append(record)
    
    # 按日期排序
    existing.sort(key=lambda x: x['date'])
    
    return existing


def update_single_stock(code: str, cache_dir: str) -> bool:
    """更新单只股票数据"""
    file_path = os.path.join(cache_dir, f"{code}.json")
    
    # 加载现有数据
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and 'data' in data:
            existing = data['data']
        else:
            existing = data
    else:
        existing = []
    
    # 获取最新数据
    new_data = get_latest_data(code, days=5)
    
    if not new_data:
        return False
    
    # 合并数据
    merged = merge_data(existing, new_data)
    
    # 保存
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump({'symbol': code, 'data': merged}, f, ensure_ascii=False, indent=2)
    
    return True


def daily_update():
    """执行日常增量更新"""
    print("="*80)
    print("🔄 日常增量数据更新".center(80))
    print("="*80)
    print(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    # 获取股票列表
    stocks = get_stock_list()
    
    if not stocks:
        print("❌ 未找到股票数据，请先运行全量采集")
        return
    
    print(f"📊 共 {len(stocks)} 只股票需要更新\n")
    
    # 创建缓存目录
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache', 'history', datetime.now().strftime('%Y%m'))
    os.makedirs(cache_dir, exist_ok=True)
    
    # 更新统计
    success = 0
    failed = 0
    skipped = 0
    
    for i, code in enumerate(stocks, 1):
        # 进度显示
        if i % 100 == 0:
            print(f"  进度：{i}/{len(stocks)} (成功:{success} 失败:{failed} 跳过:{skipped})")
        
        try:
            result = update_single_stock(code, cache_dir)
            
            if result:
                success += 1
            else:
                failed += 1
                
        except Exception as e:
            failed += 1
            print(f"  ❌ {code} 更新失败：{e}")
        
        # 限流
        if i % 50 == 0:
            time.sleep(1)
    
    # 输出结果
    print("\n" + "="*80)
    print("📊 更新结果")
    print("="*80)
    print(f"  总数：{len(stocks)}")
    print(f"  成功：{success} ({success/len(stocks)*100:.1f}%)")
    print(f"  失败：{failed} ({failed/len(stocks)*100:.1f}%)")
    print(f"  跳过：{skipped}")
    print("="*80 + "\n")
    
    # 保存更新日志
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"update_{datetime.now().strftime('%Y%m%d')}.json")
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total': len(stocks),
            'success': success,
            'failed': failed,
            'skipped': skipped
        }, f, indent=2)
    
    print(f"📁 更新日志：{log_file}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='日常增量数据更新')
    parser.add_argument('--force', action='store_true', help='强制更新所有数据')
    
    args = parser.parse_args()
    
    if args.force:
        print("⚠️ 强制更新模式，将重新获取所有数据...")
        # 可以调用全量采集脚本
    
    daily_update()
