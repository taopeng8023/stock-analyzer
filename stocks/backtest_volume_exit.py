#!/usr/bin/env python3
"""
成交量卖出策略回测 - 金叉当日买入，根据成交量卖出

买入信号:
- MA15 金叉 MA20 (当日买入)

卖出信号 (测试多种成交量策略):
1. 成交量放大 (>2 倍均量) - 可能是出货
2. 成交量萎缩 (<0.5 倍均量) - 动能衰竭
3. 量价背离 (价涨量缩)
4. 死叉卖出 (基准)

用法:
    python3 backtest_volume_exit.py --full     # 全市场回测
    python3 backtest_volume_exit.py --sample 500  # 抽样回测
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


class VolumeExitBacktester:
    """成交量卖出策略回测器"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / 'cache' / 'history'
        self.results_dir = Path(__file__).parent / 'backtest_results'
        self.results_dir.mkdir(exist_ok=True)
        
        # 测试的卖出策略
        self.exit_strategies = {
            'death_cross': '死叉卖出 (基准)',
            'volume_spike': '成交量放大 (>2 倍)',
            'volume_shrink': '成交量萎缩 (<0.5 倍)',
            'price_volume_div': '量价背离',
            'combo': '组合策略 (成交量 + 死叉)',
        }
    
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
    
    def find_golden_cross(self, data: List[Dict], start_idx: int = 20) -> List[int]:
        """找出所有金叉位置"""
        golden_crosses = []
        
        for i in range(start_idx, len(data)):
            ma15 = self.calc_ma(data, 15, i)
            ma20 = self.calc_ma(data, 20, i)
            ma15_prev = self.calc_ma(data, 15, i-1)
            ma20_prev = self.calc_ma(data, 20, i-1)
            
            if None in (ma15, ma20, ma15_prev, ma20_prev):
                continue
            
            # 金叉：MA15 从下方上穿 MA20
            if ma15_prev <= ma20_prev and ma15 > ma20:
                golden_crosses.append(i)
        
        return golden_crosses
    
    def check_volume_exit(self, data: List[Dict], idx: int, strategy: str) -> bool:
        """
        检查成交量卖出信号
        
        Args:
            data: 股票数据
            idx: 当前位置
            strategy: 卖出策略
        
        Returns:
            是否卖出
        """
        if idx < 20:
            return False
        
        volume = data[idx].get('成交量', data[idx].get('volume'))
        avg_volume = sum(data[i].get('成交量', data[i].get('volume')) for i in range(idx-20, idx)) / 20
        
        if avg_volume <= 0:
            return False
        
        volume_ratio = volume / avg_volume
        
        # 1. 成交量放大 (>2 倍均量) - 可能是出货
        if strategy == 'volume_spike':
            return volume_ratio > 2.0
        
        # 2. 成交量萎缩 (<0.5 倍均量) - 动能衰竭
        elif strategy == 'volume_shrink':
            return volume_ratio < 0.5
        
        # 3. 量价背离 (价涨量缩)
        elif strategy == 'price_volume_div':
            if idx >= 1:
                prev_close = data[idx-1].get('收盘', data[idx-1].get('close'))
                curr_close = data[idx].get('收盘', data[idx].get('close'))
                price_up = curr_close > prev_close
                volume_down = volume_ratio < 0.8
                return price_up and volume_down
            return False
        
        # 4. 死叉卖出 (基准)
        elif strategy == 'death_cross':
            ma15 = self.calc_ma(data, 15, idx)
            ma20 = self.calc_ma(data, 20, idx)
            ma15_prev = self.calc_ma(data, 15, idx-1)
            ma20_prev = self.calc_ma(data, 20, idx-1)
            
            if None in (ma15, ma20, ma15_prev, ma20_prev):
                return False
            
            return ma15_prev >= ma20_prev and ma15 < ma20
        
        # 5. 组合策略 (成交量放大 or 死叉)
        elif strategy == 'combo':
            # 成交量放大
            if volume_ratio > 2.5:
                return True
            # 死叉
            ma15 = self.calc_ma(data, 15, idx)
            ma20 = self.calc_ma(data, 20, idx)
            ma15_prev = self.calc_ma(data, 15, idx-1)
            ma20_prev = self.calc_ma(data, 20, idx-1)
            
            if None not in (ma15, ma20, ma15_prev, ma20_prev):
                if ma15_prev >= ma20_prev and ma15 < ma20:
                    return True
            return False
        
        return False
    
    def backtest_with_exit(self, data: List[Dict], exit_strategy: str) -> Dict:
        """
        回测特定卖出策略
        
        Args:
            data: 股票数据
            exit_strategy: 卖出策略
        
        Returns:
            回测结果
        """
        if len(data) < 200:
            return {'error': '数据不足'}
        
        initial_capital = 100000
        total_profit = 0
        trade_count = 0
        winning_trades = 0
        losing_trades = 0
        max_profit = 0
        max_loss = 0
        profits = []
        
        close_key = '收盘' if '收盘' in data[0] else 'close'
        
        # 找出所有金叉位置
        golden_crosses = self.find_golden_cross(data)
        
        # 对每个金叉进行回测
        for gc_idx in golden_crosses:
            # 买入位置 (金叉当日)
            buy_idx = gc_idx
            buy_price = data[buy_idx].get(close_key, 0)
            
            if buy_price <= 0:
                continue
            
            # 寻找卖出信号
            sell_idx = None
            for i in range(buy_idx + 1, len(data)):
                if self.check_volume_exit(data, i, exit_strategy):
                    sell_idx = i
                    break
            
            # 如果没有卖出信号，使用最后价格
            if sell_idx is None:
                sell_idx = len(data) - 1
            
            sell_price = data[sell_idx].get(close_key, 0)
            
            # 计算收益
            profit = ((sell_price - buy_price) / buy_price) * 100
            profits.append(profit)
            
            total_profit += profit
            trade_count += 1
            
            if profit > 0:
                winning_trades += 1
            else:
                losing_trades += 1
            
            if profit > max_profit:
                max_profit = profit
            if profit < max_loss:
                max_loss = profit
        
        # 统计结果
        if trade_count == 0:
            return {'error': '无有效交易'}
        
        avg_profit = total_profit / trade_count
        win_rate = winning_trades / trade_count * 100 if trade_count > 0 else 0
        
        return {
            'trade_count': trade_count,
            'avg_profit': avg_profit,
            'win_rate': win_rate,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'total_profit': total_profit,
            'profits': profits,
        }
    
    def validate_all_stocks(self, sample_size: int = None) -> Dict:
        """
        全市场回测验证
        
        Args:
            sample_size: 抽样数量 (None=全量)
        """
        print('='*90)
        print('成交量卖出策略回测 - 全市场验证')
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
            print(f'抽样回测：{sample_size} 只股票')
        else:
            print(f'全量回测：{len(stock_files)} 只股票')
        
        print(f'测试策略：{len(self.exit_strategies)} 种')
        print()
        
        # 回测结果 (按策略分组)
        strategy_results = {strategy: [] for strategy in self.exit_strategies.keys()}
        
        start_time = time.time()
        
        for i, symbol in enumerate(stock_files):
            try:
                data = self.load_stock_data(symbol)
                if not data or len(data) < 200:
                    continue
                
                # 对每个策略进行回测
                for strategy in self.exit_strategies.keys():
                    result = self.backtest_with_exit(data, strategy)
                    if 'error' not in result:
                        strategy_results[strategy].append({
                            'symbol': symbol,
                            **result,
                        })
                
                # 进度
                if (i + 1) % 500 == 0:
                    elapsed = time.time() - start_time
                    print(f'进度：{i+1}/{len(stock_files)} (耗时:{elapsed:.1f}秒)')
                    
            except Exception as e:
                continue
        
        elapsed = time.time() - start_time
        
        # 统计分析
        print()
        print('='*90)
        print('回测结果汇总 (按卖出策略)')
        print('='*90)
        print()
        
        summary = {
            'strategies': {},
            'elapsed_time': elapsed,
            'timestamp': datetime.now().isoformat(),
        }
        
        print(f'{"策略":<25} {"股票数":>10} {"交易数":>10} {"平均收益":>12} {"胜率":>10} {"盈利比":>10}')
        print('-'*90)
        
        for strategy, name in self.exit_strategies.items():
            results = strategy_results[strategy]
            if not results:
                continue
            
            stock_count = len(set(r['symbol'] for r in results))
            total_trades = sum(r['trade_count'] for r in results)
            total_profit = sum(r['total_profit'] for r in results)
            avg_profit = total_profit / total_trades if total_trades > 0 else 0
            total_winning = sum(r['winning_trades'] for r in results)
            win_rate = total_winning / total_trades * 100 if total_trades > 0 else 0
            profitable_stocks = len(set(r['symbol'] for r in results if r['total_profit'] > 0))
            profitable_ratio = profitable_stocks / stock_count * 100 if stock_count > 0 else 0
            
            summary['strategies'][strategy] = {
                'name': name,
                'stock_count': stock_count,
                'total_trades': total_trades,
                'avg_profit': avg_profit,
                'win_rate': win_rate,
                'profitable_ratio': profitable_ratio,
                'total_profit': total_profit,
            }
            
            print(f'{name:<25} {stock_count:>10} {total_trades:>10} {avg_profit:>+11.2f}% {win_rate:>9.1f}% {profitable_ratio:>9.1f}%')
        
        print()
        print(f'总耗时：{elapsed:.1f}秒')
        print('='*90)
        
        # 找出最佳策略
        if summary['strategies']:
            best_strategy = max(summary['strategies'].keys(), key=lambda s: summary['strategies'][s]['avg_profit'])
            print()
            print(f'🏆 最佳策略：{summary["strategies"][best_strategy]["name"]}')
            print(f'   平均收益：{summary["strategies"][best_strategy]["avg_profit"]:+.2f}%')
            print(f'   胜率：{summary["strategies"][best_strategy]["win_rate"]:.1f}%')
            print(f'   盈利股票比：{summary["strategies"][best_strategy]["profitable_ratio"]:.1f}%')
        
        # 保存结果
        output_file = self.results_dir / f'volume_exit_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f'\n结果已保存：{output_file}')
        
        return summary


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='成交量卖出策略回测')
    parser.add_argument('--sample', type=int, help='抽样数量')
    parser.add_argument('--full', action='store_true', help='全量回测')
    
    args = parser.parse_args()
    
    backtester = VolumeExitBacktester()
    
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
