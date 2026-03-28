#!/usr/bin/env python3
"""
基于缓存数据的选股系统

功能:
- 读取已缓存的股票历史数据
- 运行选股系统分析
- 输出符合条件的股票

用法:
    python3.11 scan_from_cache.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from stock_selector_v2 import EnhancedStockSelector


def load_cached_stocks(cache_dir: str = None, limit: int = None) -> list:
    """
    从缓存加载股票数据
    
    Args:
        cache_dir: 缓存目录
        limit: 最大加载数量
    
    Returns:
        股票数据列表
    """
    if not cache_dir:
        cache_dir = Path(__file__).parent / 'cache' / 'history'
    else:
        cache_dir = Path(cache_dir)
    
    # 查找最新的月份目录
    if not cache_dir.exists():
        print(f'❌ 缓存目录不存在：{cache_dir}')
        return []
    
    month_dirs = sorted([d for d in cache_dir.iterdir() if d.is_dir()], reverse=True)
    if not month_dirs:
        print('❌ 无缓存数据')
        return []
    
    latest_dir = month_dirs[0]
    print(f'使用缓存目录：{latest_dir}')
    
    # 加载股票数据
    stock_files = list(latest_dir.glob('*.json'))
    if limit:
        stock_files = stock_files[:limit]
    
    print(f'找到 {len(stock_files)} 只股票')
    
    stocks = []
    for i, filepath in enumerate(stock_files):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            symbol = data.get('symbol', filepath.stem)
            history = data.get('data', [])
            
            if history:
                stocks.append({
                    'symbol': symbol,
                    'history': history,
                })
            
            # 进度
            if (i + 1) % 100 == 0:
                print(f'   加载进度：{i+1}/{len(stock_files)}')
                
        except Exception as e:
            continue
    
    print(f'✅ 成功加载 {len(stocks)} 只股票')
    return stocks


def analyze_stocks(stocks: list) -> list:
    """
    分析股票
    
    Args:
        stocks: 股票数据列表
    
    Returns:
        分析结果列表
    """
    selector = EnhancedStockSelector()
    results = []
    
    print()
    print('开始分析股票...')
    print()
    
    for i, stock in enumerate(stocks):
        symbol = stock['symbol']
        history = stock['history']
        
        try:
            # 检查数据是否足够
            if len(history) < 200:
                continue
            
            # 获取最新数据
            latest = history[-1]
            
            # 获取资金流数据 (模拟)
            fund_flow_data = None
            
            # 分析
            result = selector.analyze_stock(
                symbol=symbol,
                fund_flow_data=fund_flow_data
            )
            
            if result:
                results.append(result)
                
                # 显示结果
                if result['score'] >= 10:
                    print(f"✅ {symbol} {result['name']} ¥{result['price']:.2f} "
                          f"{result['change']:+.2f}% 评分:{result['score']:.1f}/20 "
                          f"{result['recommendation']}")
            
            # 进度
            if (i + 1) % 50 == 0:
                print(f'进度：{i+1}/{len(stocks)} (找到{len(results)}只)')
                
        except Exception as e:
            continue
    
    return results


def main():
    print('='*70)
    print('基于缓存数据的选股系统')
    print('='*70)
    print()
    
    # 加载缓存数据
    stocks = load_cached_stocks()
    
    if not stocks:
        print('❌ 无可用数据')
        return
    
    print()
    
    # 分析股票
    results = analyze_stocks(stocks)
    
    print()
    print('='*70)
    print(f'分析完成！找到 {len(results)} 只符合条件的股票')
    print('='*70)
    print()
    
    if results:
        # 按评分排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        print('推荐股票:')
        print()
        print(f'{"排名":>4} {"代码":<8} {"名称":<12} {"价格":>8} {"涨幅":>8} {"评分":>8} {"建议":>10}')
        print('-'*70)
        
        for i, r in enumerate(results[:20], 1):
            print(f'{i:>4} {r["symbol"]:<8} {r["name"]:<12} '
                  f'{r["price"]:>8.2f} {r["change"]:>+7.2f}% '
                  f'{r["score"]:>7.1f}/20 {r["recommendation"]:>10}')
        
        print()
        
        # 保存结果
        cache_dir = Path(__file__).parent / 'cache'
        cache_dir.mkdir(exist_ok=True)
        
        result_file = cache_dir / f'cache_scan_result_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f'✅ 结果已保存：{result_file}')
    else:
        print('❌ 未找到符合条件的股票')
        print()
        print('建议:')
        print('  1. 降低筛选条件 (修改 stock_selector_v2.py)')
        print('  2. 等待更多数据 (接口恢复后重新扫描)')
        print('  3. 检查数据质量 (确保历史数据足够)')


if __name__ == '__main__':
    main()
