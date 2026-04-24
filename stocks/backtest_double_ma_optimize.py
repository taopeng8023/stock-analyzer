#!/usr/bin/env python3
"""
双均线金叉 + 移动止盈 策略优化回测

测试不同双均线配置:
- MA3/MA10 (激进)
- MA5/MA15 (较激进)
- MA5/MA20 (标准)
- MA8/MA20 (较保守)
- MA10/MA30 (保守)
- MA15/MA30 (更保守)
- MA20/MA60 (很保守)

卖出信号:
- 移动止盈 (0%, 5%, 10%, 15%, 20%)
- 或 双均线死叉

用法:
    python3 backtest_double_ma_optimize.py --full     # 全市场回测
    python3 backtest_double_ma_optimize.py --sample 500  # 抽样回测
"""

import json
import sys
import time
import statistics
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))


class DoubleMAOptimizeBacktester:
    """双均线配置优化回测器"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / 'cache' / 'history'
        self.results_dir = Path(__file__).parent / 'backtest_results'
        self.results_dir.mkdir(exist_ok=True)
        
        # 测试的双均线配置 (短，长)
        self.test_configs = [
            (3, 10),     # 激进
            (5, 15),     # 较激进
            (5, 20),     # 标准 (v3.3 默认)
            (8, 20),     # 较保守
            (10, 30),    # 保守
            (15, 30),    # 更保守
            (20, 60),    # 很保守
        ]
        
        # 测试的移动止盈比例
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
    
    def backtest(self, data: List[Dict], ma_config: Tuple[int, int], trailing_stop_ratio: float) -> Dict:
        """
        回测双均线金叉 + 移动止盈策略
        
        Args:
            data: 股票数据
            ma_config: 双均线配置 (短，长)
            trailing_stop_ratio: 移动止盈比例
        
        Returns:
            回测结果
        """
        ma_short, ma_long = ma_config
        
        if len(data) < ma_long + 10:
            return {'error': '数据不足'}
        
        initial_capital = 100000
        capital = initial_capital
        shares = 0
        trades = []
        holding = False
        buy_price = 0
        highest_price = 0
        
        close_key = '收盘' if '收盘' in data[0] else 'close'
        
        for i in range(ma_long, len(data)):
            current_price = data[i].get(close_key, 0)
            
            # 计算双均线
            ma_s = self.calc_ma(data, ma_short, i)
            ma_l = self.calc_ma(data, ma_long, i)
            ma_s_prev = self.calc_ma(data, ma_short, i-1)
            ma_l_prev = self.calc_ma(data, ma_long, i-1)
            
            if None in (ma_s, ma_l, ma_s_prev, ma_l_prev):
                continue
            
            if not holding:
                # 双均线金叉买入
                if ma_s_prev <= ma_l_prev and ma_s > ma_l:
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
                            'config': f'{ma_short}/{ma_long}',
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
                    if ma_s_prev >= ma_l_prev and ma_s < ma_l:
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
        print('='*110)
        print('双均线金叉配置优化回测')
        print('='*110)
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
        
        config_names = {
            (3, 10): '3/10 (激进)',
            (5, 15): '5/15 (较激进)',
            (5, 20): '5/20 (标准)',
            (8, 20): '8/20 (较保守)',
            (10, 30): '10/30 (保守)',
            (15, 30): '15/30 (更保守)',
            (20, 60): '20/60 (很保守)',
        }
        print(f'测试配置：{[config_names[c] for c in self.test_configs]}')
        print(f'测试移动止盈：{[f"{int(r*100)}%" for r in self.test_ratios]}')
        print()
        
        # 回测结果 (按配置 + 比例分组)
        config_results = {config: {ratio: [] for ratio in self.test_ratios} for config in self.test_configs}
        
        start_time = time.time()
        
        for i, symbol in enumerate(stock_files):
            try:
                data = self.load_stock_data(symbol)
                if not data or len(data) < 70:  # 至少需要 60+10 天数据
                    continue
                
                # 对每个配置和比例进行回测
                for config in self.test_configs:
                    for ratio in self.test_ratios:
                        result = self.backtest(data, config, ratio)
                        if 'error' not in result:
                            config_results[config][ratio].append({
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
        print('='*110)
        print('回测结果汇总 (按双均线配置和移动止盈比例)')
        print('='*110)
        print()
        
        summary = {
            'configs': {},
            'elapsed_time': elapsed,
            'timestamp': datetime.now().isoformat(),
        }
        
        print(f'{"配置":<18} {"止盈":>8} {"股票数":>10} {"交易数":>10} {"平均收益":>12} {"胜率":>10} {"持仓天":>10}')
        print('-'*110)
        
        for config in self.test_configs:
            config_name = config_names.get(config, f'{config[0]}/{config[1]}')
            summary['configs'][config_name] = {'ratios': {}}
            
            for ratio in self.test_ratios:
                results = config_results[config][ratio]
                if not results:
                    continue
                
                stock_count = len(set(r['symbol'] for r in results))
                total_trades = sum(r['trade_count'] for r in results)
                total_return = sum(r['total_return'] for r in results)
                avg_return = total_return / stock_count if stock_count > 0 else 0
                avg_win_rate = statistics.mean(r['win_rate'] for r in results)
                avg_hold_days = statistics.mean(r['avg_hold_days'] for r in results)
                profitable_count = len([r for r in results if r['total_return'] > 0])
                
                summary['configs'][config_name]['ratios'][f'{int(ratio*100)}%'] = {
                    'stock_count': stock_count,
                    'total_trades': total_trades,
                    'avg_return': avg_return,
                    'avg_win_rate': avg_win_rate,
                    'avg_hold_days': avg_hold_days,
                    'profitable_count': profitable_count,
                }
                
                ratio_str = f'{int(ratio*100)}%'
                print(f'{config_name:<18} {ratio_str:>8} {stock_count:>10} {total_trades:>10} {avg_return:>+11.2f}% {avg_win_rate:>9.1f}% {avg_hold_days:>10.1f}')
            
            print()
        
        print(f'总耗时：{elapsed:.1f}秒')
        print('='*110)
        
        # 找出最佳配置和比例
        best_config = None
        best_ratio = None
        best_return = -999
        
        for config_name, config_data in summary['configs'].items():
            for ratio_str, ratio_data in config_data['ratios'].items():
                if ratio_data['avg_return'] > best_return:
                    best_return = ratio_data['avg_return']
                    best_config = config_name
                    best_ratio = ratio_str
        
        if best_config:
            print()
            print(f'🏆 最佳配置：{best_config} + 移动止盈{best_ratio}')
            best_data = summary['configs'][best_config]['ratios'][best_ratio]
            print(f'   平均收益：{best_data["avg_return"]:+.2f}%')
            print(f'   胜率：{best_data["avg_win_rate"]:.1f}%')
            print(f'   平均持仓：{best_data["avg_hold_days"]:.1f} 天')
        
        # 保存结果
        output_file = self.results_dir / f'double_ma_optimize_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f'\n结果已保存：{output_file}')
        
        return summary


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='双均线金叉配置优化回测')
    parser.add_argument('--sample', type=int, help='抽样数量')
    parser.add_argument('--full', action='store_true', help='全量回测')
    
    args = parser.parse_args()
    
    backtester = DoubleMAOptimizeBacktester()
    
    if args.full:
        # 全量回测
        backtester.validate_all_stocks(sample_size=None)
    elif args.sample:
        # 抽样回测
        backtester.validate_all_stocks(sample_size=args.sample)
    else:
        # 默认抽样 500 只
        print('使用默认抽样 500 只股票 (使用 --full 全量回测 或 --sample 指定数量)')
        backtester.validate_all_stocks(sample_size=500)


if __name__ == '__main__':
    main()
