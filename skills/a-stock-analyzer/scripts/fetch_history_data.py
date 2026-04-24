#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史行情数据获取脚本
使用 Tushare 获取 A 股历史交易数据，补充缺失数据

数据范围：2026-03-27 往前一年 (2025-03-27 至 2026-03-27)
"""

import pandas as pd
import numpy as np
import tushare as ts
from datetime import datetime, timedelta
import argparse
import os
import json
import time
from pathlib import Path

# ============== 配置区域 ==============
# Tushare Token (从环境变量或配置文件读取)
TS_TOKEN = os.environ.get('TS_TOKEN', 'your_tushare_token_here')

# 数据保存目录
DATA_DIR = Path('/home/admin/.openclaw/workspace/skills/a-stock-analyzer/data')

# 默认回测参数
DEFAULT_END_DATE = '20260327'
DEFAULT_START_DATE = '20250327'  # 往前一年

# A 股主要股票代码列表 (可根据需要扩展)
STOCK_CODES = [
    # 上证指数成分股 (部分代表)
    '600519.SH',  # 贵州茅台
    '601318.SH',  # 中国平安
    '600036.SH',  # 招商银行
    '601888.SH',  # 中国中免
    '600276.SH',  # 恒瑞医药
    '601398.SH',  # 工商银行
    '600900.SH',  # 长江电力
    '601166.SH',  # 兴业银行
    '600585.SH',  # 海螺水泥
    '601012.SH',  # 隆基绿能
    
    # 深证成指成分股 (部分代表)
    '000001.SZ',  # 平安银行
    '000002.SZ',  # 万科 A
    '000333.SZ',  # 美的集团
    '000651.SZ',  # 格力电器
    '000725.SZ',  # 京东方 A
    '000858.SZ',  # 五粮液
    '002001.SZ',  # 新和成
    '002007.SZ',  # 华兰生物
    '002027.SZ',  # 分众传媒
    '002049.SZ',  # 紫光国微
    
    # 创业板 (部分代表)
    '300059.SZ',  # 东方财富
    '300750.SZ',  # 宁德时代
    '300014.SZ',  # 亿纬锂能
    '300012.SZ',  # 华测检测
    '300122.SZ',  # 智飞生物
    '300142.SZ',  # 沃森生物
    '300347.SZ',  # 泰格医药
    '300413.SZ',  # 芒果超媒
    '300498.SZ',  # 温氏股份
    '300760.SZ',  # 迈瑞医疗
]

# ======================================


def load_existing_data(stock_code):
    """加载已存在的数据文件"""
    file_path = DATA_DIR / f"{stock_code.replace('.', '_')}.csv"
    
    if file_path.exists():
        try:
            df = pd.read_csv(file_path, parse_dates=['date'])
            return df
        except Exception as e:
            print(f"⚠️  读取 {stock_code} 现有数据失败：{e}")
            return None
    
    return None


def get_missing_date_range(existing_df, start_date, end_date):
    """计算缺失的日期范围"""
    if existing_df is None or existing_df.empty:
        return start_date, end_date
    
    # 将日期转换为字符串格式进行比较
    existing_dates = set(existing_df['date'].dt.strftime('%Y%m%d'))
    
    # 生成完整日期范围 (只考虑交易日，由 Tushare 返回)
    start_dt = datetime.strptime(start_date, '%Y%m%d')
    end_dt = datetime.strptime(end_date, '%Y%m%d')
    
    # 找出最早和最晚的日期
    min_existing = existing_df['date'].min().strftime('%Y%m%d')
    max_existing = existing_df['date'].max().strftime('%Y%m%d')
    
    # 需要补充的数据范围
    need_start = start_date
    need_end = end_date
    
    # 如果已有数据覆盖了部分范围，只需要补充缺失的部分
    if min_existing <= start_date and max_existing >= end_date:
        # 数据已完整
        return None, None
    
    print(f"   现有数据范围：{min_existing} ~ {max_existing}")
    print(f"   需要数据范围：{start_date} ~ {end_date}")
    
    return start_date, end_date


def fetch_daily_data(stock_code, start_date, end_date, pro=None):
    """获取单只股票的历史行情数据"""
    try:
        if pro is None:
            ts.set_token(TS_TOKEN)
            pro = ts.pro_api()
        
        print(f"   正在获取 {stock_code} ({start_date} ~ {end_date})...")
        
        df = pro.daily(ts_code=stock_code, 
                      start_date=start_date, 
                      end_date=end_date)
        
        if df.empty:
            print(f"   ⚠️  未获取到 {stock_code} 的数据")
            return None
        
        # 数据清洗
        df = df.sort_values('trade_date').reset_index(drop=True)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df = df.rename(columns={'trade_date': 'date'})
        
        # 确保必要的列存在
        required_cols = ['ts_code', 'date', 'open', 'high', 'low', 'close', 'vol', 'amount']
        for col in required_cols:
            if col not in df.columns:
                print(f"   ⚠️  缺少列：{col}")
                return None
        
        print(f"   ✅ 获取到 {len(df)} 条数据 ({df['date'].min().strftime('%Y-%m-%d')} ~ {df['date'].max().strftime('%Y-%m-%d')})")
        return df
        
    except Exception as e:
        print(f"   ❌ 获取 {stock_code} 数据失败：{e}")
        return None


def merge_data(existing_df, new_df, stock_code):
    """合并现有数据和新数据，去重"""
    if existing_df is None or existing_df.empty:
        return new_df
    
    if new_df is None or new_df.empty:
        return existing_df
    
    # 合并数据
    combined = pd.concat([existing_df, new_df], ignore_index=True)
    
    # 去重 (基于日期)
    combined = combined.drop_duplicates(subset=['date'], keep='last')
    
    # 按日期排序
    combined = combined.sort_values('date').reset_index(drop=True)
    
    print(f"   📊 合并后数据量：{len(combined)} 条")
    return combined


def save_data(df, stock_code):
    """保存数据到 CSV 文件"""
    # 创建数据目录
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    file_path = DATA_DIR / f"{stock_code.replace('.', '_')}.csv"
    
    try:
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        print(f"   💾 数据已保存至：{file_path}")
        return True
    except Exception as e:
        print(f"   ❌ 保存数据失败：{e}")
        return False


def fetch_all_stocks(start_date=DEFAULT_START_DATE, end_date=DEFAULT_END_DATE, 
                     stock_codes=None, delay=0.5):
    """批量获取所有股票的历史数据"""
    
    if stock_codes is None:
        stock_codes = STOCK_CODES
    
    print("=" * 70)
    print("📊 A 股历史行情数据获取")
    print("=" * 70)
    print(f"   数据范围：{start_date} ~ {end_date}")
    print(f"   股票数量：{len(stock_codes)}")
    print(f"   数据目录：{DATA_DIR}")
    print("=" * 70)
    
    # 初始化 Tushare
    if TS_TOKEN == 'your_tushare_token_here':
        print("\n❌ 错误：未设置 Tushare Token")
        print("💡 请设置环境变量 TS_TOKEN 或在脚本中配置")
        print("💡 获取 Token: https://tushare.pro/user/token")
        return
    
    ts.set_token(TS_TOKEN)
    pro = ts.pro_api()
    
    # 统计信息
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    results = []
    
    for i, stock_code in enumerate(stock_codes, 1):
        print(f"\n[{i}/{len(stock_codes)}] 处理 {stock_code}...")
        
        # 加载现有数据
        existing_df = load_existing_data(stock_code)
        
        # 检查是否需要获取新数据
        if existing_df is not None and not existing_df.empty:
            existing_dates = set(existing_df['date'].dt.strftime('%Y%m%d'))
            
            # 检查是否已覆盖目标日期范围
            start_in_range = any(d >= start_date for d in existing_dates)
            end_in_range = any(d <= end_date for d in existing_dates)
            
            if start_in_range and end_in_range and len(existing_df) > 200:  # 约一年的交易日
                print(f"   ⏭️  数据已完整，跳过")
                skip_count += 1
                results.append({
                    'stock_code': stock_code,
                    'status': 'skipped',
                    'records': len(existing_df)
                })
                continue
        
        # 获取新数据
        new_df = fetch_daily_data(stock_code, start_date, end_date, pro)
        
        if new_df is not None:
            # 合并数据
            merged_df = merge_data(existing_df, new_df, stock_code)
            
            # 保存数据
            if save_data(merged_df, stock_code):
                success_count += 1
                results.append({
                    'stock_code': stock_code,
                    'status': 'success',
                    'records': len(merged_df)
                })
            else:
                fail_count += 1
                results.append({
                    'stock_code': stock_code,
                    'status': 'save_failed',
                    'records': 0
                })
        else:
            fail_count += 1
            results.append({
                'stock_code': stock_code,
                'status': 'fetch_failed',
                'records': 0
            })
        
        # 避免请求过快
        if i < len(stock_codes):
            time.sleep(delay)
    
    # 打印统计报告
    print("\n" + "=" * 70)
    print("📊 数据获取完成")
    print("=" * 70)
    print(f"   成功：{success_count} 只")
    print(f"   跳过：{skip_count} 只 (数据已完整)")
    print(f"   失败：{fail_count} 只")
    print(f"   总计：{len(stock_codes)} 只")
    print("=" * 70)
    
    # 保存获取报告
    report_path = DATA_DIR / 'fetch_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            'fetch_time': datetime.now().isoformat(),
            'start_date': start_date,
            'end_date': end_date,
            'summary': {
                'success': success_count,
                'skipped': skip_count,
                'failed': fail_count,
                'total': len(stock_codes)
            },
            'details': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 获取报告已保存至：{report_path}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='A 股历史行情数据获取脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 获取默认股票列表的数据 (2025-03-27 ~ 2026-03-27)
  python fetch_history_data.py
  
  # 获取单只股票的数据
  python fetch_history_data.py --stock 000001.SZ
  
  # 自定义日期范围
  python fetch_history_data.py --start 20240101 --end 20260327
  
  # 从文件读取股票列表
  python fetch_history_data.py --stock-list stocks.txt
        """
    )
    
    parser.add_argument('--stock', type=str, default=None,
                       help='单只股票代码 (如：000001.SZ)')
    parser.add_argument('--stock-list', type=str, default=None,
                       help='股票列表文件路径 (每行一个代码)')
    parser.add_argument('--start', type=str, default=DEFAULT_START_DATE,
                       help=f'开始日期 (默认：{DEFAULT_START_DATE})')
    parser.add_argument('--end', type=str, default=DEFAULT_END_DATE,
                       help=f'结束日期 (默认：{DEFAULT_END_DATE})')
    parser.add_argument('--delay', type=float, default=0.5,
                       help='请求间隔秒数 (默认：0.5)')
    parser.add_argument('--token', type=str, default=None,
                       help='Tushare Token (覆盖环境变量)')
    
    args = parser.parse_args()
    
    # 设置 Token
    global TS_TOKEN
    if args.token:
        TS_TOKEN = args.token
    
    # 确定股票列表
    stock_codes = None
    if args.stock:
        stock_codes = [args.stock]
    elif args.stock_list:
        with open(args.stock_list, 'r') as f:
            stock_codes = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    # 获取数据
    fetch_all_stocks(
        start_date=args.start,
        end_date=args.end,
        stock_codes=stock_codes,
        delay=args.delay
    )


if __name__ == '__main__':
    main()
