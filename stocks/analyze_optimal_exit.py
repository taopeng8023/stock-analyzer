#!/usr/bin/env python3
"""
卖出策略优化分析 - 寻找最优卖出点

基于 v3.0 基准 (MA15/MA20 金叉买入，死叉卖出)

分析内容:
1. 死叉卖出前的最高收益
2. 如果在最高点卖出能赚多少
3. 不同卖出策略对比
4. 寻找最优卖出策略

用法:
    python3 analyze_optimal_exit.py --full     # 全市场分析
    python3 analyze_optimal_exit.py --sample 500  # 抽样分析
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


class OptimalExitAnalyzer:
    """最优卖出策略分析器"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / 'cache' / 'history'
        self.results_dir = Path(__file__).parent / 'backtest_results'
        self.results_dir.mkdir(exist_ok=True)
    
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
    
    def calc_ma(self, data: List[Dict], period: int, idx: int) -> Optional[float]:
        """计算移动平均线"""
        if idx < period - 1:
            return None
        return sum(data[i].get('收盘', data[i].get('close')) for i in range(idx-period+1, idx+1)) / period
    
    def find_trades(self, data: List[Dict]) -> List[Dict]:
        """
        找出所有交易 (金叉买入，死叉卖出)
        
        Returns:
            交易列表
        """
        trades = []
        holding = False
        buy_idx = 0
        buy_price = 0
        
        close_key = '收盘' if '收盘' in data[0] else 'close'
        
        for i in range(20, len(data)):
            ma15 = self.calc_ma(data, 15, i)
            ma20 = self.calc_ma(data, 20, i)
            ma15_prev = self.calc_ma(data, 15, i-1)
            ma20_prev = self.calc_ma(data, 20, i-1)
            
            if None in (ma15, ma20, ma15_prev, ma20_prev):
                continue
            
            current_price = data[i].get(close_key, 0)
            
            if not holding:
                # 金叉买入
                if ma15_prev <= ma20_prev and ma15 > ma20:
                    holding = True
                    buy_idx = i
                    buy_price = current_price
            else:
                # 死叉卖出
                if ma15_prev >= ma20_prev and ma15 < ma20:
                    sell_price = current_price
                    
                    # 计算持有期间最高价
                    highest_price = max(data[j].get(close_key, 0) for j in range(buy_idx, i+1))
                    highest_idx = buy_idx + max(range(i - buy_idx + 1), key=lambda x: data[buy_idx + x].get(close_key, 0))
                    
                    trade = {
                        'buy_idx': buy_idx,
                        'buy_price': buy_price,
                        'buy_date': data[buy_idx].get('日期', data[buy_idx].get('day', '')),
                        'sell_idx': i,
                        'sell_price': sell_price,
                        'sell_date': data[i].get('日期', data[i].get('day', '')),
                        'death_cross_profit': ((sell_price - buy_price) / buy_price) * 100,
                        'highest_price': highest_price,
                        'highest_idx': highest_idx,
                        'highest_date': data[highest_idx].get('日期', data[highest_idx].get('day', '')),
                        'optimal_profit': ((highest_price - buy_price) / buy_price) * 100,
                        'profit_loss': ((highest_price - buy_price) / buy_price) * 100 - ((sell_price - buy_price) / buy_price) * 100,
                        'hold_days': i - buy_idx,
                    }
                    trades.append(trade)
                    
                    holding = False
        
        return trades
    
    def analyze_stock(self, data: List[Dict]) -> Dict:
        """
        分析单只股票
        
        Returns:
            分析结果
        """
        if len(data) < 200:
            return {'error': '数据不足'}
        
        trades = self.find_trades(data)
        
        if not trades:
            return {'error': '无有效交易'}
        
        # 统计
        total_death_cross_profit = sum(t['death_cross_profit'] for t in trades)
        total_optimal_profit = sum(t['optimal_profit'] for t in trades)
        total_profit_loss = sum(t['profit_loss'] for t in trades)
        
        avg_death_cross_profit = total_death_cross_profit / len(trades)
        avg_optimal_profit = total_optimal_profit / len(trades)
        avg_profit_loss = total_profit_loss / len(trades)
        
        avg_hold_days = statistics.mean(t['hold_days'] for t in trades)
        
        # 分类统计
        captured_ratio = [t['death_cross_profit'] / t['optimal_profit'] * 100 if t['optimal_profit'] > 0 else 0 for t in trades]
        avg_captured_ratio = statistics.mean(captured_ratio) if captured_ratio else 0
        
        return {
            'trade_count': len(trades),
            'avg_death_cross_profit': avg_death_cross_profit,
            'avg_optimal_profit': avg_optimal_profit,
            'avg_profit_loss': avg_profit_loss,
            'avg_hold_days': avg_hold_days,
            'avg_captured_ratio': avg_captured_ratio,
            'trades': trades,
        }
    
    def validate_all_stocks(self, sample_size: int = None) -> Dict:
        """
        全市场验证
        
        Args:
            sample_size: 抽样数量 (None=全量)
        """
        print('='*90)
        print('卖出策略优化分析 - 寻找最优卖出点')
        print('='*90)
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
            print(f'抽样分析：{sample_size} 只股票')
        else:
            print(f'全量分析：{len(stock_files)} 只股票')
        
        print()
        
        # 分析结果
        results = []
        
        start_time = time.time()
        
        for i, symbol in enumerate(stock_files):
            try:
                data = self.load_stock_data(symbol)
                if not data or len(data) < 200:
                    continue
                
                result = self.analyze_stock(data)
                if 'error' not in result:
                    results.append({'symbol': symbol, **result})
                
                # 进度
                if (i + 1) % 500 == 0:
                    elapsed = time.time() - start_time
                    print(f'进度：{i+1}/{len(stock_files)} (有效:{len(results)} 耗时:{elapsed:.1f}秒)')
                    
            except Exception as e:
                continue
        
        elapsed = time.time() - start_time
        
        # 统计分析
        print()
        print('='*90)
        print('分析结果汇总')
        print('='*90)
        print()
        
        if results:
            death_cross_profits = [r['avg_death_cross_profit'] for r in results]
            optimal_profits = [r['avg_optimal_profit'] for r in results]
            profit_losses = [r['avg_profit_loss'] for r in results]
            captured_ratios = [r['avg_captured_ratio'] for r in results]
            hold_days = [r['avg_hold_days'] for r in results]
            
            summary = {
                'stock_count': len(results),
                'total_trades': sum(r['trade_count'] for r in results),
                'avg_death_cross_profit': statistics.mean(death_cross_profits),
                'avg_optimal_profit': statistics.mean(optimal_profits),
                'avg_profit_loss': statistics.mean(profit_losses),
                'avg_captured_ratio': statistics.mean(captured_ratios),
                'avg_hold_days': statistics.mean(hold_days),
                'elapsed_time': elapsed,
                'timestamp': datetime.now().isoformat(),
            }
            
            # 打印结果
            print(f'分析股票数：{len(results)}')
            print(f'总交易数：{summary["total_trades"]}')
            print(f'总耗时：{elapsed:.1f}秒')
            print()
            print('收益对比:')
            print(f'  死叉卖出平均收益：{summary["avg_death_cross_profit"]:+.2f}%')
            print(f'  最优卖出平均收益：{summary["avg_optimal_profit"]:+.2f}%')
            print(f'  收益损失：{summary["avg_profit_loss"]:+.2f}%')
            print()
            print('效率分析:')
            print(f'  平均持仓天数：{summary["avg_hold_days"]:.1f} 天')
            print(f'  收益捕获率：{summary["avg_captured_ratio"]:.1f}%')
            print()
            print('='*90)
            
            # 保存结果
            output_file = self.results_dir / f'optimal_exit_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print(f'\n结果已保存：{output_file}')
            
            return summary
        else:
            print('❌ 无有效分析结果')
            return {}


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='卖出策略优化分析')
    parser.add_argument('--sample', type=int, help='抽样数量')
    parser.add_argument('--full', action='store_true', help='全量分析')
    
    args = parser.parse_args()
    
    analyzer = OptimalExitAnalyzer()
    
    if args.full:
        # 全量分析
        analyzer.validate_all_stocks(sample_size=None)
    elif args.sample:
        # 抽样分析
        analyzer.validate_all_stocks(sample_size=args.sample)
    else:
        # 默认抽样 1000 只
        print('使用默认抽样 1000 只股票 (使用 --full 全量分析 或 --sample 指定数量)')
        analyzer.validate_all_stocks(sample_size=1000)


if __name__ == '__main__':
    main()
