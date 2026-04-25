#!/usr/bin/env python3
"""
低价优质主板股票选股脚本
========================

策略逻辑：
1. 主板股票（沪深主板）
2. 低价（<20元）
3. 主力净流入 > 1亿
4. 主力占比 > 5%（资金共识强）
5. 排除 ST、新股

数据源：东方财富 API（通过 zjlx_auto_fetcher.py 获取缓存）
"""

import json
import os
import sys
from datetime import datetime


def load_zjlx_data(data_dir='data'):
    """加载资金流数据"""
    latest_file = os.path.join(data_dir, 'zjlx_ranking_latest.json')
    
    if not os.path.exists(latest_file):
        print(f'❌ 未找到数据文件: {latest_file}')
        print('请先运行: python3 zjlx_auto_fetcher.py')
        sys.exit(1)
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    return data


def is_mainboard(code):
    """判断是否为主板股票"""
    return code.startswith(('600', '601', '603', '000', '001', '002', '003'))


def is_st_stock(name):
    """判断是否 ST 股"""
    return 'ST' in name or 'st' in name


def is_new_stock(name):
    """判断是否新股/次新股"""
    return name.startswith('N') or name.startswith('C')


def calculate_score(item):
    """计算综合评分"""
    score = 0
    
    # 主力净流入评分（0-10分）
    main_inflow = item.get('main_net_inflow', 0)
    if main_inflow > 10:
        score += 10
    elif main_inflow > 5:
        score += 7
    elif main_inflow > 3:
        score += 5
    elif main_inflow > 1:
        score += 3
    
    # 主力占比评分（0-10分）
    main_pct = item.get('main_net_pct', 0)
    if main_pct > 25:
        score += 10
    elif main_pct > 20:
        score += 8
    elif main_pct > 15:
        score += 6
    elif main_pct > 10:
        score += 4
    elif main_pct > 5:
        score += 2
    
    # 超大单 + 大单均流入（0-5分）
    super_inflow = item.get('super_large_net', 0)
    large_inflow = item.get('large_net', 0)
    if super_inflow > 0 and large_inflow > 0:
        score += 5
    elif super_inflow > 0:
        score += 2
    
    # 低价加分（0-5分）
    price = item.get('price', 0)
    if price < 5:
        score += 5
    elif price < 10:
        score += 4
    elif price < 15:
        score += 3
    elif price < 20:
        score += 2
    
    # 涨幅温和加分（0-3分）
    pct = item.get('change_pct', 0)
    if pct < 3:
        score += 3
    elif pct < 5:
        score += 2
    elif pct < 7:
        score += 1
    
    return score


def select_stocks(data_dir='data', min_price=0, max_price=20, min_main_inflow=1, min_main_pct=5, max_pct=99, sort_by='score'):
    """
    选股主函数
    
    参数：
        data_dir: 数据目录
        min_price: 最低价格
        max_price: 最高价格
        min_main_inflow: 最小主力净流入（亿）
        min_main_pct: 最小主力占比（%）
        max_pct: 最大涨幅（%，默认 99，不限制）
        sort_by: 排序方式 ('score'=综合评分, 'inflow'=主力净流入)
    
    返回：
        候选股票列表（按评分排序）
    """
    data = load_zjlx_data(data_dir)
    
    candidates = []
    for item in data['data']:
        code = item['code']
        name = item['name']
        price = item.get('price', 0)
        pct = item.get('change_pct', 0)
        
        # 筛选条件
        if not is_mainboard(code):
            continue
        if is_st_stock(name) or is_new_stock(name):
            continue
        if price < min_price or price > max_price:
            continue
        if item.get('main_net_inflow', 0) < min_main_inflow:
            continue
        if item.get('main_net_pct', 0) < min_main_pct:
            continue
        if pct >= max_pct:  # 排除涨幅>=max_pct 的股票
            continue
        
        # 计算评分
        item['score'] = calculate_score(item)
        candidates.append(item)
    
    # 排序
    if sort_by == 'inflow':
        candidates.sort(key=lambda x: x.get('main_net_inflow', 0), reverse=True)
    else:
        candidates.sort(key=lambda x: x['score'], reverse=True)
    
    return candidates, data['update_time']


def print_results(candidates, update_time):
    """打印选股结果"""
    print('=' * 70)
    print('📊 低价优质主板股票选股结果')
    print('=' * 70)
    print(f'数据时间: {update_time}')
    print(f'候选数量: {len(candidates)} 只')
    print()
    
    if not candidates:
        print('⚠️ 未找到符合条件的股票')
        return
    
    # 打印 TOP10
    top_n = min(10, len(candidates))
    print(f'=== TOP{top_n} 精选 ===')
    print()
    
    for i, item in enumerate(candidates[:top_n], 1):
        code = item['code']
        name = item['name']
        price = item.get('price', 0)
        pct = item.get('change_pct', 0)
        main_inflow = item.get('main_net_inflow', 0)
        main_pct = item.get('main_net_pct', 0)
        super_inflow = item.get('super_large_net', 0)
        large_inflow = item.get('large_net', 0)
        score = item.get('score', 0)
        
        # 星级
        stars = '⭐' * min(int(score / 2), 5)
        
        print(f'{i}. {name}({code}) {stars} (评分:{score})')
        print(f'   现价:{price}元  涨跌幅:{pct:+.2f}%  主力净流入:{main_inflow:+.2f}亿  主力占比:{main_pct:+.2f}%')
        print(f'   超大单:{super_inflow:+.2f}亿  大单:{large_inflow:+.2f}亿')
        print()
    
    # 操作建议
    print('=' * 70)
    print('💡 操作建议')
    print('=' * 70)
    
    # 首选：评分最高且涨幅<10%
    safe_candidates = [c for c in candidates[:5] if c.get('change_pct', 0) < 10]
    if safe_candidates:
        print('首选（评分高 + 涨幅温和）：')
        for item in safe_candidates[:3]:
            print(f'  ✅ {item["name"]}({item["code"]}) - 评分:{item["score"]}')
    else:
        print('⚠️ 当前无涨幅<10%的高评分股票')
    
    print()
    print('仓位建议：单只 20-30%，总仓位不超过 60%')
    print()
    print('⚠️ 免责声明：以上分析基于资金流数据，不构成投资建议。股市有风险，投资需谨慎。')


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='低价优质主板股票选股脚本')
    parser.add_argument('--data-dir', default='data', help='数据目录 (默认: data)')
    parser.add_argument('--max-price', type=float, default=20, help='最高价格 (默认: 20)')
    parser.add_argument('--min-inflow', type=float, default=1, help='最小主力净流入亿 (默认: 1)')
    parser.add_argument('--min-pct', type=float, default=5, help='最小主力占比% (默认: 5)')
    parser.add_argument('--top', type=int, default=10, help='显示 TOP N (默认: 10)')
    parser.add_argument('--max-pct', type=float, default=99, help='最大涨幅%% (默认: 99，不限制)')
    parser.add_argument('--sort-by', choices=['score', 'inflow'], default='score', help='排序方式 (默认: score)')
    
    args = parser.parse_args()
    
    # 选股
    candidates, update_time = select_stocks(
        data_dir=args.data_dir,
        max_price=args.max_price,
        min_main_inflow=args.min_inflow,
        min_main_pct=args.min_pct,
        max_pct=args.max_pct,
        sort_by=args.sort_by
    )
    
    # 打印结果
    print_results(candidates, update_time)
    
    # 返回候选列表（供其他脚本调用）
    return candidates


if __name__ == '__main__':
    main()
