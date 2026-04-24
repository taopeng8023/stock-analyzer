#!/usr/bin/env python3
"""
选股系统 v4.0 全市场回测验证

基于 5493 只股票全市场回测，验证优化效果

对比:
- v3.0 (MA15/MA20 基础版)
- v4.0 (MA15/MA20 优化版)

用法:
    python3 backtest_v4_validation.py
"""

import json
import sys
import time
import statistics
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from stock_selector_v4 import OptimizedStockSelector


class V4Backtester:
    """v4.0 回测验证器"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / 'cache' / 'history'
        self.results_dir = Path(__file__).parent / 'backtest_results'
        self.results_dir.mkdir(exist_ok=True)
        
        self.selector = OptimizedStockSelector()
    
    def load_stock_data(self, symbol: str) -> Optional[List[Dict]]:
        """加载单只股票数据"""
        month_dirs = sorted([d for d in self.cache_dir.iterdir() if d.is_dir()], reverse=True)
        
        for month_dir in month_dirs:
            filepath = month_dir / f'{symbol}.json'
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    return data.get('data', [])
                except:
                    continue
        return None
    
    def backtest_v3_baseline(self, data: List[Dict]) -> Dict:
        """
        v3.0 基础版回测 (MA15/MA20 无优化)
        
        仅使用基础金叉死叉，无止损无过滤
        """
        if len(data) < 200:
            return {'error': '数据不足'}
        
        initial_capital = 100000
        capital = initial_capital
        shares = 0
        trades = []
        holding = False
        buy_price = 0
        
        close_key = 'close' if 'close' in data[0] else '收盘'
        
        for i in range(20, len(data)):
            ma15 = self.selector.calc_ma(data, 15, i)
            ma20 = self.selector.calc_ma(data, 20, i)
            ma15_prev = self.selector.calc_ma(data, 15, i-1)
            ma20_prev = self.selector.calc_ma(data, 20, i-1)
            
            if None in (ma15, ma20, ma15_prev, ma20_prev):
                continue
            
            # 基础金叉买入
            if not holding and ma15_prev <= ma20_prev and ma15 > ma20:
                buy_price = data[i].get(close_key, 0)
                shares = int(capital * 0.95 / buy_price / 100) * 100
                if shares > 0:
                    cost = shares * buy_price * 1.0003
                    capital -= cost
                    holding = True
                    trades.append({'date': data[i].get('日期', ''), 'type': '买入', 'price': buy_price})
            
            # 基础死叉卖出
            elif holding and ma15_prev >= ma20_prev and ma15 < ma20:
                sell_price = data[i].get(close_key, 0)
                revenue = shares * sell_price * 0.9997
                capital += revenue
                profit = ((sell_price - buy_price) / buy_price) * 100
                trades.append({'date': data[i].get('日期', ''), 'type': '卖出', 'price': sell_price, 'profit': profit})
                shares = 0
                holding = False
        
        # 最终资产
        if shares > 0:
            final_value = capital + shares * data[-1].get(close_key, 0) * 0.9997
        else:
            final_value = capital
        
        total_return = ((final_value / initial_capital) - 1) * 100
        
        # 统计
        sell_trades = [t for t in trades if t['type'] == '卖出']
        winning_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
        win_rate = len(winning_trades) / len(sell_trades) * 100 if sell_trades else 0
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'trade_count': len(trades),
            'win_rate': win_rate,
            'trades': trades,
        }
    
    def backtest_v4_optimized(self, data: List[Dict]) -> Dict:
        """
        v4.0 优化版回测
        
        包含:
        - 风险过滤
        - 成交量确认
        - 多因子确认
        - 止损止盈
        """
        return self.selector.backtest_optimized(data)
    
    def validate_all_stocks(self, sample_size: int = None) -> Dict:
        """
        全市场回测验证
        
        Args:
            sample_size: 抽样数量 (None=全量)
        """
        print('='*70)
        print('选股系统 v4.0 全市场回测验证')
        print('='*70)
        print()
        
        # 获取股票列表
        stock_files = []
        month_dirs = sorted([d for d in self.cache_dir.iterdir() if d.is_dir()], reverse=True)
        
        if month_dirs:
            latest_dir = month_dirs[0]
            stock_files = [f.stem for f in latest_dir.glob('*.json') if f.is_file()]
        
        # 抽样
        if sample_size and len(stock_files) > sample_size:
            import random
            stock_files = random.sample(stock_files, sample_size)
            print(f'抽样回测：{sample_size} 只股票')
        else:
            print(f'全量回测：{len(stock_files)} 只股票')
        
        print()
        
        # 回测结果
        v3_results = []
        v4_results = []
        
        start_time = time.time()
        
        for i, symbol in enumerate(stock_files):
            try:
                data = self.load_stock_data(symbol)
                if not data or len(data) < 200:
                    continue
                
                # v3.0 回测
                v3_result = self.backtest_v3_baseline(data)
                if 'error' not in v3_result:
                    v3_results.append({'symbol': symbol, **v3_result})
                
                # v4.0 回测
                v4_result = self.backtest_v4_optimized(data)
                if 'error' not in v4_result:
                    v4_results.append({'symbol': symbol, **v4_result})
                
                # 进度
                if (i + 1) % 500 == 0:
                    elapsed = time.time() - start_time
                    print(f'进度：{i+1}/{len(stock_files)} (v3 有效:{len(v3_results)} v4 有效:{len(v4_results)} 耗时:{elapsed:.1f}秒)')
                    
            except Exception as e:
                continue
        
        elapsed = time.time() - start_time
        
        # 统计分析
        print()
        print('='*70)
        print('回测结果对比')
        print('='*70)
        print()
        
        summary = self.compare_results(v3_results, v4_results)
        
        # 打印对比
        print(f'{"指标":<20} {"v3.0 基础版":>15} {"v4.0 优化版":>15} {"提升":>10}')
        print('-'*70)
        
        for metric in ['avg_return', 'median_return', 'win_rate', 'profitable_count']:
            v3_val = summary['v3'].get(metric, 0)
            v4_val = summary['v4'].get(metric, 0)
            
            if metric == 'avg_return' or metric == 'median_return':
                print(f"{metric:<20} {v3_val:>+14.2f}% {v4_val:>+14.2f}% {((v4_val/v3_val)-1)*100:>+9.1f}%")
            elif metric == 'win_rate':
                print(f"{metric:<20} {v3_val:>+13.1f}% {v4_val:>+13.1f}% {v4_val-v3_val:>+9.1f}%")
            elif metric == 'profitable_count':
                print(f"{metric:<20} {v3_val:>+14} {v4_val:>+14} {v4_val-v3_val:>+10}")
        
        print()
        print(f'回测股票数：{len(v3_results)} (v3) / {len(v4_results)} (v4)')
        print(f'总耗时：{elapsed:.1f}秒')
        print('='*70)
        
        # 保存结果
        output_file = self.results_dir / f'v4_validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f'\n结果已保存：{output_file}')
        
        return summary
    
    def compare_results(self, v3_results: List[Dict], v4_results: List[Dict]) -> Dict:
        """对比 v3 和 v4 结果"""
        summary = {
            'v3': {},
            'v4': {},
            'timestamp': datetime.now().isoformat(),
        }
        
        # v3 统计
        if v3_results:
            returns = [r['total_return'] for r in v3_results]
            win_rates = [r['win_rate'] for r in v3_results]
            summary['v3'] = {
                'stock_count': len(v3_results),
                'avg_return': statistics.mean(returns),
                'median_return': statistics.median(returns),
                'max_return': max(returns),
                'min_return': min(returns),
                'avg_win_rate': statistics.mean(win_rates),
                'profitable_count': len([r for r in v3_results if r['total_return'] > 0]),
            }
        
        # v4 统计
        if v4_results:
            returns = [r['total_return'] for r in v4_results]
            win_rates = [r['win_rate'] for r in v4_results]
            summary['v4'] = {
                'stock_count': len(v4_results),
                'avg_return': statistics.mean(returns),
                'median_return': statistics.median(returns),
                'max_return': max(returns),
                'min_return': min(returns),
                'avg_win_rate': statistics.mean(win_rates),
                'profitable_count': len([r for r in v4_results if r['total_return'] > 0]),
            }
        
        return summary


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='选股系统 v4.0 全市场回测验证')
    parser.add_argument('--sample', type=int, help='抽样数量 (默认全量)')
    parser.add_argument('--full', action='store_true', help='全量回测')
    
    args = parser.parse_args()
    
    backtester = V4Backtester()
    
    if args.full:
        # 全量回测
        backtester.validate_all_stocks(sample_size=None)
    elif args.sample:
        # 抽样回测
        backtester.validate_all_stocks(sample_size=args.sample)
    else:
        # 默认抽样 1000 只
        print('使用默认抽样 1000 只股票 (使用 --full 全量回测 或 --sample 指定数量)')
        backtester.validate_all_stocks(sample_size=1000)


if __name__ == '__main__':
    main()
