#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 Tushare 历史数据完整性
找出数据不完整的股票（缺少 2025-03-27 至 2026-03-27 范围的数据）
"""

import json
import os
from pathlib import Path
from datetime import datetime

DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')

# 目标日期范围
TARGET_START = '20250327'
TARGET_END = '20260327'

# 最少交易日天数（一年约 240-250 个交易日）
MIN_TRADING_DAYS = 200


def check_stock_data(filepath):
    """检查单只股票数据完整性"""
    stock_code = filepath.stem
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            return {
                'code': stock_code,
                'status': 'empty',
                'records': 0,
                'start_date': None,
                'end_date': None,
                'issue': '数据为空'
            }
        
        dates = [d['日期'] for d in data]
        start_date = min(dates)
        end_date = max(dates)
        records = len(data)
        
        issues = []
        
        # 检查开始日期
        if start_date > TARGET_START:
            issues.append(f'缺少开始数据 (从{start_date}开始，需要从{TARGET_START}开始)')
        
        # 检查结束日期
        if end_date < TARGET_END:
            issues.append(f'缺少结束数据 (到{end_date}结束，需要到{TARGET_END}结束)')
        
        # 检查数据条数
        if records < MIN_TRADING_DAYS:
            issues.append(f'数据条数不足 ({records}条，需要至少{MIN_TRADING_DAYS}条)')
        
        status = 'complete' if not issues else 'incomplete'
        
        return {
            'code': stock_code,
            'status': status,
            'records': records,
            'start_date': start_date,
            'end_date': end_date,
            'issue': '; '.join(issues) if issues else None
        }
    
    except Exception as e:
        return {
            'code': stock_code,
            'status': 'error',
            'records': 0,
            'start_date': None,
            'end_date': None,
            'issue': str(e)
        }


def main():
    print("=" * 70)
    print("📊 Tushare 历史数据完整性检查")
    print("=" * 70)
    print(f"目标日期范围：{TARGET_START} ~ {TARGET_END}")
    print(f"数据目录：{DATA_DIR}")
    print(f"最少交易日要求：{MIN_TRADING_DAYS} 天")
    print("=" * 70)
    
    # 获取所有数据文件
    json_files = list(DATA_DIR.glob('*.json'))
    total_files = len(json_files)
    
    print(f"\n发现 {total_files} 只股票数据文件\n")
    
    # 检查结果分类
    complete = []
    incomplete = []
    empty = []
    errors = []
    
    # 逐个检查
    for i, filepath in enumerate(json_files, 1):
        result = check_stock_data(filepath)
        
        if result['status'] == 'complete':
            complete.append(result)
        elif result['status'] == 'incomplete':
            incomplete.append(result)
        elif result['status'] == 'empty':
            empty.append(result)
        elif result['status'] == 'error':
            errors.append(result)
        
        # 进度显示
        if i % 500 == 0:
            print(f"已检查 {i}/{total_files}...")
    
    # 打印统计
    print("\n" + "=" * 70)
    print("📊 检查结果统计")
    print("=" * 70)
    print(f"完整数据：{len(complete)} 只")
    print(f"不完整数据：{len(incomplete)} 只")
    print(f"空数据：{len(empty)} 只")
    print(f"读取错误：{len(errors)} 只")
    print(f"总计：{total_files} 只")
    print("=" * 70)
    
    # 打印不完整的股票详情
    if incomplete:
        print("\n⚠️  数据不完整的股票:")
        print("-" * 70)
        print(f"{'代码':<10} {'记录数':<8} {'开始日期':<12} {'结束日期':<12} 问题")
        print("-" * 70)
        
        for r in sorted(incomplete, key=lambda x: x['records']):
            print(f"{r['code']:<10} {r['records']:<8} {r['start_date'] or 'N/A':<12} {r['end_date'] or 'N/A':<12} {r['issue']}")
        
        print("-" * 70)
        
        # 保存不完整股票列表
        incomplete_list = [r['code'] for r in incomplete]
        incomplete_file = DATA_DIR.parent / 'incomplete_stocks.txt'
        with open(incomplete_file, 'w') as f:
            for code in incomplete_list:
                f.write(f"{code}\n")
        print(f"\n💾 不完整股票列表已保存至：{incomplete_file}")
    
    # 打印空数据或错误的股票
    if empty:
        print("\n⚠️  空数据文件:")
        for r in empty:
            print(f"  - {r['code']}")
    
    if errors:
        print("\n❌ 读取错误的文件:")
        for r in errors:
            print(f"  - {r['code']}: {r['issue']}")
    
    # 保存检查报告
    report = {
        'check_time': datetime.now().isoformat(),
        'target_range': {'start': TARGET_START, 'end': TARGET_END},
        'summary': {
            'total': total_files,
            'complete': len(complete),
            'incomplete': len(incomplete),
            'empty': len(empty),
            'errors': len(errors)
        },
        'incomplete_stocks': incomplete,
        'empty_stocks': empty,
        'error_stocks': errors
    }
    
    report_file = DATA_DIR.parent / 'data_completeness_report.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 完整检查报告已保存至：{report_file}")
    
    return incomplete


if __name__ == '__main__':
    main()
