#!/usr/bin/env python3
"""
全市场股票历史数据批量回溯系统

功能:
- 批量回溯所有 5493 只股票
- 测试多种策略参数
- 生成回测报告
- 优化策略参数

用法:
    python3.11 batch_backtest_all.py --strategy ma_cross --days 250
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import statistics

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))


class BatchBacktester:
    """批量回溯测试器"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / 'cache' / 'history'
        self.results_dir = Path(__file__).parent / 'backtest_results'
        self.results_dir.mkdir(exist_ok=True)
        
        # 策略配置
        self.strategies = {
            'ma_cross': {
                'name': '均线交叉',
                'params': {
                    'ma_short': [5, 10, 15],
                    'ma_long': [20, 30, 60],
                }
            },
            'ma_trend': {
                'name': '均线趋势',
                'params': {
                    'ma_period': [20, 30, 60],
                    'threshold': [0.02, 0.05, 0.10],
                }
            },
        }
    
    def load_stock_data(self, symbol: str) -> Optional[List[Dict]]:
        """加载单只股票数据"""
        # 查找最新月份目录
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
        return sum(data[i]['收盘'] for i in range(idx-period+1, idx+1)) / period
    
    def backtest_ma_cross(self, data: List[Dict], ma_short: int = 5, ma_long: int = 20) -> Dict:
        """
        均线交叉策略回测
        
        Returns:
            回测结果字典
        """
        if len(data) < ma_long + 10:
            return {'error': '数据不足'}
        
        initial_capital = 100000
        capital = initial_capital
        shares = 0
        trades = []
        holding = False
        buy_price = 0
        
        for i in range(ma_long, len(data)):
            ma_s = self.calc_ma(data, ma_short, i)
            ma_l = self.calc_ma(data, ma_long, i)
            ma_s_prev = self.calc_ma(data, ma_short, i-1)
            ma_l_prev = self.calc_ma(data, ma_long, i-1)
            
            if None in (ma_s, ma_l, ma_s_prev, ma_l_prev):
                continue
            
            # 金叉买入
            if not holding and ma_s_prev <= ma_l_prev and ma_s > ma_l:
                buy_price = data[i]['收盘']
                shares = int(capital * 0.95 / buy_price / 100) * 100
                if shares > 0:
                    cost = shares * buy_price * 1.0003  # 手续费
                    capital -= cost
                    holding = True
                    trades.append({
                        'date': data[i]['日期'],
                        'type': '买入',
                        'price': buy_price,
                        'shares': shares,
                    })
            
            # 死叉卖出
            elif holding and ma_s_prev >= ma_l_prev and ma_s < ma_l:
                sell_price = data[i]['收盘']
                revenue = shares * sell_price * 0.9997  # 手续费
                capital += revenue
                profit = ((sell_price - buy_price) / buy_price) * 100
                trades.append({
                    'date': data[i]['日期'],
                    'type': '卖出',
                    'price': sell_price,
                    'shares': shares,
                    'profit': profit,
                })
                shares = 0
                holding = False
        
        # 最终资产
        if shares > 0 and len(data) > 0:
            final_value = capital + shares * data[-1]['收盘'] * 0.9997
        else:
            final_value = capital
        
        total_return = ((final_value / initial_capital) - 1) * 100
        
        # 计算胜率
        sell_trades = [t for t in trades if t['type'] == '卖出']
        winning_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
        win_rate = len(winning_trades) / len(sell_trades) * 100 if sell_trades else 0
        
        # 计算最大回撤
        peak = initial_capital
        max_drawdown = 0
        current_capital = initial_capital
        for t in trades:
            if t['type'] == '卖出':
                current_capital = current_capital + t['shares'] * t['price'] * 0.9997
                if current_capital > peak:
                    peak = current_capital
                drawdown = (peak - current_capital) / peak * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'trade_count': len(trades),
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'trades': trades,
        }
    
    def backtest_all_stocks(self, strategy: str = 'ma_cross', **params) -> Dict:
        """
        回溯所有股票
        
        Returns:
            回测结果汇总
        """
        print('='*70)
        print(f'全市场股票批量回测 - {self.strategies.get(strategy, {}).get("name", strategy)}')
        print('='*70)
        print()
        
        # 获取所有股票文件
        stock_files = []
        month_dirs = sorted([d for d in self.cache_dir.iterdir() if d.is_dir()], reverse=True)
        
        if month_dirs:
            latest_dir = month_dirs[0]
            stock_files = [f.stem for f in latest_dir.glob('*.json') if f.is_file()]
        
        print(f'找到 {len(stock_files)} 只股票')
        print()
        
        # 回测结果
        results = []
        start_time = time.time()
        
        for i, symbol in enumerate(stock_files):
            try:
                # 加载数据
                data = self.load_stock_data(symbol)
                if not data or len(data) < 60:
                    continue
                
                # 执行回测
                if strategy == 'ma_cross':
                    result = self.backtest_ma_cross(
                        data,
                        ma_short=params.get('ma_short', 5),
                        ma_long=params.get('ma_long', 20),
                    )
                else:
                    result = {'error': '未知策略'}
                
                if 'error' not in result:
                    results.append({
                        'symbol': symbol,
                        **result,
                    })
                
                # 进度
                if (i + 1) % 500 == 0:
                    elapsed = time.time() - start_time
                    print(f'进度：{i+1}/{len(stock_files)} (耗时：{elapsed:.1f}秒)')
                    
            except Exception as e:
                continue
        
        elapsed = time.time() - start_time
        
        # 统计分析
        if results:
            returns = [r['total_return'] for r in results]
            win_rates = [r['win_rate'] for r in results]
            
            stats = {
                'strategy': strategy,
                'params': params,
                'total_stocks': len(stock_files),
                'valid_stocks': len(results),
                'avg_return': statistics.mean(returns),
                'median_return': statistics.median(returns),
                'max_return': max(returns),
                'min_return': min(returns),
                'avg_win_rate': statistics.mean(win_rates),
                'profitable_stocks': len([r for r in results if r['total_return'] > 0]),
                'elapsed_time': elapsed,
                'timestamp': datetime.now().isoformat(),
            }
            
            # 最佳股票
            best_stocks = sorted(results, key=lambda x: x['total_return'], reverse=True)[:10]
            worst_stocks = sorted(results, key=lambda x: x['total_return'])[:10]
            
            stats['best_stocks'] = best_stocks
            stats['worst_stocks'] = worst_stocks
            
            # 打印结果
            print()
            print('='*70)
            print('回测结果汇总')
            print('='*70)
            print()
            print(f'回测股票数：{len(results)}/{len(stock_files)}')
            print(f'耗时：{elapsed:.1f}秒')
            print()
            print(f'平均收益率：{stats["avg_return"]:+.2f}%')
            print(f'中位收益率：{stats["median_return"]:+.2f}%')
            print(f'最高收益率：{stats["max_return"]:+.2f}%')
            print(f'最低收益率：{stats["min_return"]:+.2f}%')
            print(f'平均胜率：{stats["avg_win_rate"]:.1f}%')
            print(f'盈利股票数：{stats["profitable_stocks"]} ({stats["profitable_stocks"]/len(results)*100:.1f}%)')
            print()
            
            print('最佳股票 TOP 10:')
            for i, s in enumerate(best_stocks[:10], 1):
                print(f'  {i}. {s["symbol"]} {s["total_return"]:+.2f}% (胜率:{s["win_rate"]:.1f}%)')
            print()
            
            # 保存结果
            output_file = self.results_dir / f'backtest_{strategy}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            print(f'结果已保存：{output_file}')
            
            return stats
        else:
            print('❌ 无有效回测结果')
            return {}
    
    def optimize_strategy(self, strategy: str = 'ma_cross') -> Dict:
        """
        优化策略参数
        
        Returns:
            最优参数
        """
        print('='*70)
        print(f'策略参数优化 - {strategy}')
        print('='*70)
        print()
        
        if strategy not in self.strategies:
            print(f'未知策略：{strategy}')
            return {}
        
        strategy_config = self.strategies[strategy]
        params = strategy_config['params']
        
        # 参数网格搜索
        best_params = {}
        best_avg_return = -100
        
        if strategy == 'ma_cross':
            short_list = params['ma_short']
            long_list = params['ma_long']
            
            print(f'测试参数组合：{len(short_list)} x {len(long_list)} = {len(short_list)*len(long_list)} 种')
            print()
            
            for short in short_list:
                for long in long_list:
                    if short >= long:
                        continue
                    
                    print(f'测试 MA{short}/MA{long}...', end=' ')
                    
                    result = self.backtest_all_stocks(
                        strategy='ma_cross',
                        ma_short=short,
                        ma_long=long,
                    )
                    
                    if result and 'avg_return' in result:
                        avg_return = result['avg_return']
                        print(f'平均收益：{avg_return:+.2f}%')
                        
                        if avg_return > best_avg_return:
                            best_avg_return = avg_return
                            best_params = {'ma_short': short, 'ma_long': long}
                    else:
                        print('失败')
        
        print()
        print('='*70)
        print('最优参数')
        print('='*70)
        print(f'策略：{strategy}')
        print(f'参数：{best_params}')
        print(f'平均收益：{best_avg_return:+.2f}%')
        print('='*70)
        
        return {
            'strategy': strategy,
            'best_params': best_params,
            'best_avg_return': best_avg_return,
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='全市场股票批量回测')
    parser.add_argument('--strategy', type=str, default='ma_cross', help='回测策略')
    parser.add_argument('--optimize', action='store_true', help='优化策略参数')
    parser.add_argument('--ma-short', type=int, default=5, help='短期均线')
    parser.add_argument('--ma-long', type=int, default=20, help='长期均线')
    
    args = parser.parse_args()
    
    backtester = BatchBacktester()
    
    if args.optimize:
        # 优化策略
        backtester.optimize_strategy(args.strategy)
    else:
        # 执行回测
        backtester.backtest_all_stocks(
            strategy=args.strategy,
            ma_short=args.ma_short,
            ma_long=args.ma_long,
        )


if __name__ == '__main__':
    main()
