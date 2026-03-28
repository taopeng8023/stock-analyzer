#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据质量检查脚本

功能:
- 检查数据完整性
- 检测异常数据
- 验证数据连续性
- 生成质量报告

用法:
    python3 data_quality_check.py
    python3 data_quality_check.py --fix  # 自动修复
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import numpy as np


def load_stock_data(code: str, cache_dir: str) -> Optional[List[Dict]]:
    """加载股票数据"""
    file_path = os.path.join(cache_dir, f"{code}.json")
    
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict) and 'data' in data:
        return data['data']
    elif isinstance(data, list):
        return data
    
    return None


def check_data_completeness(data: List[Dict]) -> Dict:
    """检查数据完整性"""
    issues = []
    
    if not data:
        return {'valid': False, 'issues': ['数据为空'], 'score': 0}
    
    # 检查必需字段
    required_fields = ['date', 'open', 'close', 'high', 'low', 'volume']
    for record in data:
        for field in required_fields:
            if field not in record:
                issues.append(f"缺少字段：{field}")
    
    # 检查数据量
    if len(data) < 60:
        issues.append(f"数据量不足：{len(data)} 条 (最少 60 条)")
    
    # 检查日期连续性
    dates = [d['date'] for d in data]
    gaps = check_date_gaps(dates)
    if gaps:
        issues.extend([f"日期不连续：{g}" for g in gaps[:5]])  # 最多显示 5 个
    
    # 检查价格合理性
    price_issues = check_price_validity(data)
    issues.extend(price_issues[:5])
    
    # 计算质量分数
    score = 100
    score -= len(issues) * 10
    score = max(0, score)
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'score': score,
        'records': len(data)
    }


def check_date_gaps(dates: List[str]) -> List[str]:
    """检查日期间隙"""
    gaps = []
    
    for i in range(1, len(dates)):
        try:
            prev = datetime.strptime(dates[i-1], '%Y-%m-%d')
            curr = datetime.strptime(dates[i], '%Y-%m-%d')
            
            diff = (curr - prev).days
            
            # 跳过周末（允许 3 天间隔）
            if diff > 3:
                gaps.append(f"{dates[i-1]} 至 {dates[i]} 间隔{diff}天")
        except:
            continue
    
    return gaps


def check_price_validity(data: List[Dict]) -> List[str]:
    """检查价格合理性"""
    issues = []
    
    for i, record in enumerate(data):
        try:
            open_p = record.get('open', 0)
            close_p = record.get('close', 0)
            high_p = record.get('high', 0)
            low_p = record.get('low', 0)
            
            # 检查高低点包含关系
            if high_p < max(open_p, close_p):
                issues.append(f"记录{i}: 最高价{high_p} < max(开盘{open_p}, 收盘{close_p})")
            
            if low_p > min(open_p, close_p):
                issues.append(f"记录{i}: 最低价{low_p} > min(开盘{open_p}, 收盘{close_p})")
            
            # 检查价格是否为 0 或负数
            if close_p <= 0:
                issues.append(f"记录{i}: 收盘价{close_p} <= 0")
            
            # 检查涨跌幅是否异常 (>20%)
            if i > 0:
                prev_close = data[i-1].get('close', close_p)
                if prev_close > 0:
                    change = abs(close_p - prev_close) / prev_close * 100
                    if change > 20:
                        issues.append(f"记录{i}: 涨跌幅{change:.1f}% > 20%")
        
        except Exception as e:
            issues.append(f"记录{i}: 解析错误 - {e}")
    
    return issues


def check_volume_validity(data: List[Dict]) -> List[str]:
    """检查成交量合理性"""
    issues = []
    
    volumes = [d.get('volume', 0) for d in data]
    
    if not volumes:
        return ['无成交量数据']
    
    avg_vol = np.mean(volumes)
    
    for i, vol in enumerate(volumes):
        # 检查成交量是否为 0
        if vol == 0:
            issues.append(f"记录{i}: 成交量为 0")
        
        # 检查成交量是否异常（超过平均值 10 倍）
        if vol > avg_vol * 10:
            issues.append(f"记录{i}: 成交量{vol} > 平均{avg_vol:.0f} * 10")
    
    return issues


def batch_quality_check(cache_dir: str = None) -> Dict:
    """批量质量检查"""
    if cache_dir is None:
        cache_dir = os.path.join(os.path.dirname(__file__), 'cache', 'history', datetime.now().strftime('%Y%m'))
    
    if not os.path.exists(cache_dir):
        return {'error': '缓存目录不存在'}
    
    files = [f.replace('.json', '') for f in os.listdir(cache_dir) if f.endswith('.json')]
    
    print(f"🔍 开始检查 {len(files)} 只股票数据质量...\n")
    
    results = {
        'total': len(files),
        'excellent': 0,  # 90-100 分
        'good': 0,       # 70-89 分
        'fair': 0,       # 50-69 分
        'poor': 0,       # <50 分
        'issues_summary': {},
        'problem_stocks': []
    }
    
    for i, code in enumerate(files, 1):
        # 进度显示
        if i % 500 == 0:
            print(f"  已检查 {i}/{len(files)} 只...")
        
        data = load_stock_data(code, cache_dir)
        
        if not data:
            results['poor'] += 1
            results['problem_stocks'].append({'code': code, 'issue': '数据加载失败'})
            continue
        
        # 完整性检查
        completeness = check_data_completeness(data)
        
        # 成交量检查
        volume_issues = check_volume_validity(data)
        completeness['issues'].extend(volume_issues[:3])
        
        # 评级
        score = completeness['score']
        if score >= 90:
            results['excellent'] += 1
        elif score >= 70:
            results['good'] += 1
        elif score >= 50:
            results['fair'] += 1
        else:
            results['poor'] += 1
            results['problem_stocks'].append({
                'code': code,
                'score': score,
                'issues': completeness['issues'][:3]
            })
        
        # 汇总问题类型
        for issue in completeness['issues']:
            issue_type = issue.split(':')[0] if ':' in issue else issue
            results['issues_summary'][issue_type] = results['issues_summary'].get(issue_type, 0) + 1
    
    return results


def print_quality_report(results: Dict):
    """打印质量报告"""
    print("\n" + "="*80)
    print("📊 数据质量检查报告".center(80))
    print("="*80)
    
    print(f"\n总股票数：{results['total']}")
    
    print("\n质量分布:")
    print(f"  🟢 优秀 (90-100 分): {results['excellent']} ({results['excellent']/results['total']*100:.1f}%)")
    print(f"  🟡 良好 (70-89 分):  {results['good']} ({results['good']/results['total']*100:.1f}%)")
    print(f"  🟠 一般 (50-69 分):  {results['fair']} ({results['fair']/results['total']*100:.1f}%)")
    print(f"  🔴 较差 (<50 分):   {results['poor']} ({results['poor']/results['total']*100:.1f}%)")
    
    if results['issues_summary']:
        print("\n常见问题:")
        for issue, count in sorted(results['issues_summary'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {issue}: {count} 次")
    
    if results['problem_stocks']:
        print(f"\n⚠️ 问题股票 (共{len(results['problem_stocks'])}只):")
        for stock in results['problem_stocks'][:10]:
            print(f"  {stock['code']}: 分数{stock.get('score', 'N/A')}, 问题：{stock.get('issues', ['未知'])}")
    
    print("\n" + "="*80 + "\n")


def fix_data_issues(code: str, cache_dir: str) -> bool:
    """尝试修复数据问题"""
    data = load_stock_data(code, cache_dir)
    
    if not data:
        return False
    
    # 按日期排序
    data.sort(key=lambda x: x.get('date', ''))
    
    # 移除重复日期
    seen_dates = set()
    unique_data = []
    for record in data:
        date = record.get('date')
        if date not in seen_dates:
            seen_dates.add(date)
            unique_data.append(record)
    
    # 保存修复后的数据
    file_path = os.path.join(cache_dir, f"{code}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump({'symbol': code, 'data': unique_data}, f, ensure_ascii=False, indent=2)
    
    return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='数据质量检查')
    parser.add_argument('--code', type=str, help='检查单只股票')
    parser.add_argument('--fix', action='store_true', help='自动修复问题')
    parser.add_argument('--report', action='store_true', help='生成详细报告')
    
    args = parser.parse_args()
    
    print("="*80)
    print("🔍 数据质量检查系统".center(80))
    print("="*80)
    print(f"作者：凯文")
    print("="*80 + "\n")
    
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache', 'history', datetime.now().strftime('%Y%m'))
    
    if args.code:
        # 检查单只股票
        data = load_stock_data(args.code, cache_dir)
        
        if not data:
            print(f"❌ 无法加载 {args.code} 的数据")
            return
        
        result = check_data_completeness(data)
        
        print(f"📊 {args.code} 数据质量检查")
        print(f"  数据量：{result['records']} 条")
        print(f"  质量分数：{result['score']}/100")
        print(f"  状态：{'✅ 通过' if result['valid'] else '❌ 存在问题'}")
        
        if result['issues']:
            print("\n  问题列表:")
            for issue in result['issues'][:10]:
                print(f"    - {issue}")
        
        if args.fix and not result['valid']:
            print("\n🔧 正在修复...")
            if fix_data_issues(args.code, cache_dir):
                print("✅ 修复完成")
            else:
                print("❌ 修复失败")
    
    else:
        # 批量检查
        results = batch_quality_check(cache_dir)
        print_quality_report(results)
        
        # 保存报告
        if args.report:
            report_dir = os.path.join(os.path.dirname(__file__), 'quality_reports')
            os.makedirs(report_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = os.path.join(report_dir, f'quality_{timestamp}.json')
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"📁 报告已保存：{filepath}")


if __name__ == '__main__':
    main()
