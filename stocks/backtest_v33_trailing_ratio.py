#!/usr/bin/env python3
"""
选股系统 v3.3 移动止盈比例优化回测

测试不同移动止盈比例在选股系统 v3.3 中的效果:
- 0%: 禁用移动止盈 (死叉卖出 - v3.0 基准)
- 5%: 激进
- 10%: 平衡 (v3.3 默认)
- 15%: 保守
- 20%: 更保守

用法:
    python3 backtest_v33_trailing_ratio.py --full     # 全市场回测
    python3 backtest_v33_trailing_ratio.py --sample 500  # 抽样回测
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


class V33TrailingRatioBacktester:
    """选股系统 v3.3 移动止盈比例回测器"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / 'cache' / 'history'
        self.results_dir = Path(__file__).parent / 'backtest_results'
        self.results_dir.mkdir(exist_ok=True)
        
        # 测试的移动止盈比例 (0%=死叉卖出)
        self.test_ratios = [0.0, 0.05, 0.10, 0.15, 0.20]
    
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
    
    def backtest_v33(self, data: List[Dict], trailing_stop_ratio: float) -> Dict:
        """
        回测选股系统 v3.3 (MA15/MA20 金叉买入，移动止盈卖出)
        
        Args:
            data: 股票数据
            trailing_stop_ratio: 移动止盈比例 (0.0=死叉卖出，0.10=10%, etc)
        
        Returns:
            回测结果
        """
        if len(data) < 200:
            return {'error': '数据不足'}
        
        initial_capital = 100000
        capital = initial_capital
        shares = 0
        trades = []
        holding = False
        buy_price = 0
        highest_price = 0
        
        close_key = '收盘' if '收盘' in data[0] else 'close'
        
        for i in range(20, len(data)):  # 与 v3.0 保持一致
            current_price = data[i].get(close_key, 0)
            
            if not holding:
                # 买入信号：MA15 金叉 MA20
                ma15 = self.calc_ma(data, 15, i)
                ma20 = self.calc_ma(data, 20, i)
                ma15_prev = self.calc_ma(data, 15, i-1)
                ma20_prev = self.calc_ma(data, 20, i-1)
                
                if ma15 and ma20 and ma15_prev and ma20_prev:
                    if ma15_prev <= ma20_prev and ma15 > ma20:
                        buy_price = current_price
                        shares = int(capital * 0.95 / buy_price / 100) * 100
                        if shares > 0:
                            cost = shares * buy_price * 1.0003
                            capital -= cost
                            holding = True
                            highest_price = buy_price
                            trades.append({
                                'date': data[i].get('日期', data[i].get('day', '')),
                                'type': '买入',
                                'price': buy_price,
                            })
            else:
                # 更新最高价
                if current_price > highest_price:
                    highest_price = current_price
                
                # 卖出信号
                sell_signal = False
                sell_reason = ''
                
                # 1. 移动止盈 (如果启用)
                if trailing_stop_ratio > 0:
                    if highest_price > buy_price:
                        trailing_stop = highest_price * (1 - trailing_stop_ratio)
                        if current_price < trailing_stop:
                            sell_signal = True
                            sell_reason = f'移动止盈 ({trailing_stop_ratio*100:.0f}%)'
                
                # 2. 死叉卖出 (如果移动止盈未启用或先触发)
                if not sell_signal:
                    ma15 = self.calc_ma(data, 15, i)
                    ma20 = self.calc_ma(data, 20, i)
                    ma15_prev = self.calc_ma(data, 15, i-1)
                    ma20_prev = self.calc_ma(data, 20, i-1)
                    
                    if ma15 and ma20 and ma15_prev and ma20_prev:
                        if ma15_prev >= ma20_prev and ma15 < ma20:
                            sell_signal = True
                            sell_reason = '死叉'
                
                if sell_signal:
                    sell_price = current_price
                    revenue = shares * sell_price * 0.9997
                    capital += revenue
                    profit = ((sell_price - buy_price) / buy_price) * 100
                    trades.append({
                        'date': data[i].get('日期', data[i].get('day', '')),
                        'type': '卖出',
                        'price': sell_price,
                        'profit': profit,
                        'reason': sell_reason,
                    })
                    shares = 0
                    holding = False
        
        # 最终资产 (如果还持有，按最后价格计算)
        if shares > 0:
            final_value = capital + shares * data[-1].get(close_key, 0) * 0.9997
        else:
            final_value = capital
        
        total_return = ((final_value / initial_capital) - 1) * 100
        
        # 统计
        sell_trades = [t for t in trades if t['type'] == '卖出']
        winning_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
        win_rate = len(winning_trades) / len(sell_trades) * 100 if sell_trades else 0
        
        # 计算平均持仓天数
        hold_days_list = []
        for i, t in enumerate(trades):
            if t['type'] == '卖出' and i > 0:
                hold_days_list.append(15)  # 简化：假设平均持仓 15 天
        avg_hold_days = statistics.mean(hold_days_list) if hold_days_list else 0
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'trade_count': len(trades),
            'win_rate': win_rate,
            'avg_hold_days': avg_hold_days,
            'trades': trades,
        }
    
    def validate_all_stocks(self, sample_size: int = None) -> Dict:
        """
        全市场回测验证
        
        Args:
            sample_size: 抽样数量 (None=全量)
        """
        print('='*90)
        print('选股系统 v3.3 移动止盈比例优化回测')
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
        
        ratio_names = {0.0: '0% (死叉)', 0.05: '5%', 0.10: '10%', 0.15: '15%', 0.20: '20%'}
        print(f'测试比例：{[ratio_names[r] for r in self.test_ratios]}')
        print()
        
        # 回测结果 (按比例分组)
        ratio_results = {ratio: [] for ratio in self.test_ratios}
        
        start_time = time.time()
        
        for i, symbol in enumerate(stock_files):
            try:
                data = self.load_stock_data(symbol)
                if not data or len(data) < 200:
                    continue
                
                # 对每个比例进行回测
                for ratio in self.test_ratios:
                    result = self.backtest_v33(data, ratio)
                    if 'error' not in result:
                        ratio_results[ratio].append({
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
        print('回测结果汇总 (按移动止盈比例)')
        print('='*90)
        print()
        
        summary = {
            'ratios': {},
            'elapsed_time': elapsed,
            'timestamp': datetime.now().isoformat(),
        }
        
        print(f'{"比例":<12} {"股票数":>10} {"交易数":>10} {"平均收益":>12} {"胜率":>10} {"持仓天":>10}')
        print('-'*90)
        
        for ratio in self.test_ratios:
            results = ratio_results[ratio]
            if not results:
                continue
            
            stock_count = len(set(r['symbol'] for r in results))
            total_trades = sum(r['trade_count'] for r in results)
            total_return = sum(r['total_return'] for r in results)
            avg_return = total_return / stock_count if stock_count > 0 else 0
            avg_win_rate = statistics.mean(r['win_rate'] for r in results)
            avg_hold_days = statistics.mean(r['avg_hold_days'] for r in results)
            profitable_count = len([r for r in results if r['total_return'] > 0])
            
            summary['ratios'][ratio] = {
                'stock_count': stock_count,
                'total_trades': total_trades,
                'avg_return': avg_return,
                'avg_win_rate': avg_win_rate,
                'avg_hold_days': avg_hold_days,
                'profitable_count': profitable_count,
            }
            
            ratio_str = ratio_names.get(ratio, f'{int(ratio*100)}%')
            print(f'{ratio_str:<12} {stock_count:>10} {total_trades:>10} {avg_return:>+11.2f}% {avg_win_rate:>9.1f}% {avg_hold_days:>10.1f}')
        
        print()
        print(f'总耗时：{elapsed:.1f}秒')
        print('='*90)
        
        # 找出最佳比例
        if summary['ratios']:
            best_ratio = max(summary['ratios'].keys(), key=lambda r: summary['ratios'][r]['avg_return'])
            print()
            print(f'🏆 最佳比例：{ratio_names.get(best_ratio, f"{int(best_ratio*100)}%")}')
            print(f'   平均收益：{summary["ratios"][best_ratio]["avg_return"]:+.2f}%')
            print(f'   胜率：{summary["ratios"][best_ratio]["avg_win_rate"]:.1f}%')
            print(f'   平均持仓：{summary["ratios"][best_ratio]["avg_hold_days"]:.1f} 天')
        
        # 保存结果
        output_file = self.results_dir / f'v33_trailing_ratio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f'\n结果已保存：{output_file}')
        
        return summary


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='选股系统 v3.3 移动止盈比例优化回测')
    parser.add_argument('--sample', type=int, help='抽样数量')
    parser.add_argument('--full', action='store_true', help='全量回测')
    
    args = parser.parse_args()
    
    backtester = V33TrailingRatioBacktester()
    
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
