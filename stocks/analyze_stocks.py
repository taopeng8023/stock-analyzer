#!/usr/bin/env python3
"""
分析指定股票列表 - 使用腾讯数据源

用法:
    python3 analyze_stocks.py --codes 300308,300274,601012
"""

import sys
import json
import requests
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))


def get_stock_data(codes: list) -> list:
    """从腾讯获取股票数据"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    # 格式化代码
    formatted_codes = []
    for code in codes:
        code = code.strip()
        if code.startswith('6') or code.startswith('000') or code.startswith('001') or code.startswith('002'):
            formatted_codes.append(f"sh{code}" if code.startswith('6') else f"sz{code}")
        elif code.startswith('300') or code.startswith('301'):
            formatted_codes.append(f"sz{code}")
        elif code.startswith('688'):
            formatted_codes.append(f"sh{code}")
        else:
            formatted_codes.append(code)
    
    results = []
    
    # 分批获取
    for i in range(0, len(formatted_codes), 60):
        batch = formatted_codes[i:i+60]
        symbol_list = ','.join(batch)
        url = f"https://qt.gtimg.cn/q={symbol_list}"
        
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'gbk'
            
            for line in resp.text.split('\n'):
                match = re.search(r'v_(\w+)="([^"]+)"', line)
                if match:
                    fields = match.group(2).split('~')
                    if len(fields) >= 40:
                        symbol = match.group(1)
                        stock = {
                            'symbol': symbol,
                            'name': fields[1] if len(fields) > 1 else '',
                            'price': float(fields[3]) if len(fields) > 3 and fields[3] else 0,
                            'change_pct': float(fields[32]) if len(fields) > 32 and fields[32] else 0,
                            'volume': int(float(fields[36])) if len(fields) > 36 and fields[36] else 0,
                            'amount': 0,
                        }
                        
                        # 成交额解析
                        if len(fields) > 35 and '/' in fields[35]:
                            parts = fields[35].split('/')
                            if len(parts) >= 3:
                                stock['amount'] = float(parts[2])
                        
                        # 板块标识
                        if symbol.startswith('sh60') or symbol.startswith('sz000') or symbol.startswith('sz001') or symbol.startswith('sz002'):
                            stock['board'] = '主板'
                        elif symbol.startswith('sz300') or symbol.startswith('sz301'):
                            stock['board'] = '创业板'
                        elif symbol.startswith('sh688'):
                            stock['board'] = '科创板'
                        else:
                            stock['board'] = '其他'
                        
                        results.append(stock)
            
        except Exception as e:
            print(f"⚠️  获取失败：{e}")
    
    return results


def analyze_stocks(codes: list):
    """分析指定股票"""
    
    print(f"\n{'='*100}")
    print(f"📊 股票分析报告")
    print(f"{'='*100}")
    print(f"分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"股票数量：{len(codes)} 只")
    print(f"{'='*100}\n")
    
    # 获取实时数据
    print("[1/3] 获取实时行情...")
    stocks = get_stock_data(codes)
    
    if not stocks:
        print("❌ 无法获取数据")
        return
    
    print(f"✅ 获取到 {len(stocks)} 只股票数据\n")
    
    # 分类统计
    main_board = [s for s in stocks if s['board'] == '主板']
    cyb = [s for s in stocks if s['board'] == '创业板']
    kcb = [s for s in stocks if s['board'] == '科创板']
    
    print(f"[2/3] 股票分类:")
    print(f"   主板：{len(main_board)} 只")
    print(f"   创业板：{len(cyb)} 只")
    print(f"   科创板：{len(kcb)} 只")
    print()
    
    # 按涨幅排序
    stocks.sort(key=lambda x: x.get('change_pct', 0), reverse=True)
    
    print(f"[3/3] 个股详情 (按涨幅排序):\n")
    print(f"{'='*110}")
    print(f"{'排名':<4} {'代码':<10} {'名称':<10} {'股价':>8} {'涨跌':>10} {'成交':>10} {'板块':<8}")
    print(f"{'-'*110}")
    
    for i, s in enumerate(stocks, 1):
        symbol = s.get('symbol', '')
        name = s.get('name', '')
        price = s.get('price', 0)
        change_pct = s.get('change_pct', 0)
        amount = s.get('amount', 0)
        board = s.get('board', '')
        
        # 成交额格式
        if amount >= 100000000:
            amount_str = f"{amount/100000000:.2f}亿"
        else:
            amount_str = f"{amount/10000:.0f}万"
        
        change_sign = '+' if change_pct >= 0 else ''
        
        print(f"{i:<4} {symbol:<10} {name:<10} ¥{price:>5.2f} {change_sign}{change_pct:>7.2f}% {amount_str:>8} {board:<8}")
    
    print(f"{'='*110}")
    
    # 统计
    gainers = [s for s in stocks if s.get('change_pct', 0) > 3]
    losers = [s for s in stocks if s.get('change_pct', 0) < -3]
    flat = [s for s in stocks if -3 <= s.get('change_pct', 0) <= 3]
    
    print(f"\n📊 涨跌统计:")
    print(f"   大涨 (>3%): {len(gainers)} 只")
    print(f"   震荡 (±3%): {len(flat)} 只")
    print(f"   大跌 (<-3%): {len(losers)} 只")
    
    if gainers:
        print(f"\n📈 领涨股 Top5:")
        for s in gainers[:5]:
            print(f"   {s.get('name', '')} ({s.get('symbol', '')}) +{s.get('change_pct', 0):.2f}%")
    
    if losers:
        print(f"\n📉 领跌股 Top5:")
        for s in losers[:5]:
            print(f"   {s.get('name', '')} ({s.get('symbol', '')}) {s.get('change_pct', 0):.2f}%")
    
    # 主板股票分析 (符合工作流筛选条件)
    if main_board:
        main_board.sort(key=lambda x: x.get('change_pct', 0), reverse=True)
        print(f"\n{'='*100}")
        print(f"🎯 主板股票分析 (符合工作流筛选条件)")
        print(f"{'='*100}")
        
        # 按成交额排序
        main_board_by_amount = sorted(main_board, key=lambda x: x.get('amount', 0), reverse=True)
        
        print(f"\n按成交额排序 Top10:")
        print(f"{'排名':<4} {'代码':<10} {'名称':<10} {'股价':>8} {'涨跌':>10} {'成交':>10}")
        print(f"{'-'*70}")
        for i, s in enumerate(main_board_by_amount[:10], 1):
            amount = s.get('amount', 0)
            amount_str = f"{amount/100000000:.2f}亿" if amount >= 100000000 else f"{amount/10000:.0f}万"
            change_sign = '+' if s.get('change_pct', 0) >= 0 else ''
            print(f"{i:<4} {s.get('symbol',''):<10} {s.get('name',''):<10} ¥{s.get('price',0):>5.2f} {change_sign}{s.get('change_pct',0):>7.2f}% {amount_str:>8}")
    
    # 保存结果
    result_file = Path(__file__).parent / 'cache' / f'analyze_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
    result_file.parent.mkdir(exist_ok=True)
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'time': datetime.now().isoformat(),
            'count': len(stocks),
            'main_board': len(main_board),
            'cyb': len(cyb),
            'kcb': len(kcb),
            'stocks': stocks
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 结果已保存：{result_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='分析指定股票')
    parser.add_argument('--codes', type=str, required=True, help='股票代码列表，逗号分隔')
    
    args = parser.parse_args()
    
    codes = [c.strip() for c in args.codes.split(',')]
    analyze_stocks(codes)


if __name__ == '__main__':
    main()
