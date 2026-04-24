#!/usr/bin/env python3
"""
选股系统 v3.2 回测 - 成交量萎缩 (<0.5 倍) 卖出

基于全市场 5493 只股票回测验证

卖出策略:
- 成交量 < 0.5 倍 20 日均量 (收益最高 +4.16%)

用法:
    python3 backtest_v32_volume_shrink.py --full     # 全市场回测
    python3 backtest_v32_volume_shrink.py --sample 500  # 抽样回测
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


class V32VolumeShrinkBacktester:
    """v3.2 成交量萎缩卖出回测器"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / 'cache' / 'history'
        self.results_dir = Path(__file__).parent / 'backtest_results'
        self.results_dir.mkdir(exist_ok=True)
        
        # 成交量萎缩阈值
        self.volume_shrink_threshold = 0.5
    
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
    
    def backtest(self, data: List[Dict]) -> Dict:
        """
        回测策略 (MA15/MA20 金叉买入，成交量萎缩<0.5 倍卖出)
        
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
        buy_date_idx = 0
        highest_price = 0
        
        close_key = '收盘' if '收盘' in data[0] else 'close'
        volume_key = '成交量' if '成交量' in data[0] else 'volume'
        
        for i in range(200, len(data)):
            current_price = data[i].get(close_key, 0)
            current_volume = data[i].get(volume_key, 0)
            
            # 计算 20 日均量
            avg_volume = sum(data[j].get(volume_key, 0) for j in range(i-20, i)) / 20
            
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
                            buy_date_idx = i
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
                
                # 卖出信号：成交量萎缩 <0.5 倍
                sell_signal = False
                sell_reason = ''
                
                if avg_volume > 0 and current_volume < avg_volume * self.volume_shrink_threshold:
                    sell_signal = True
                    sell_reason = f'成交量萎缩 ({current_volume/avg_volume:.2f}倍)'
                
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
        
        # 计算最大回撤
        peak = initial_capital
        max_drawdown = 0
        current_capital = initial_capital
        for t in trades:
            if t['type'] == '卖出' and 'shares' in t:
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
    
    def validate_all_stocks(self, sample_size: int = None) -> Dict:
        """
        全市场回测验证
        
        Args:
            sample_size: 抽样数量 (None=全量)
        """
        print('='*70)
        print('选股系统 v3.2 回测 (成交量萎缩<0.5 倍卖出)')
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
        results = []
        
        start_time = time.time()
        
        for i, symbol in enumerate(stock_files):
            try:
                data = self.load_stock_data(symbol)
                if not data or len(data) < 200:
                    continue
                
                result = self.backtest(data)
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
        print('='*70)
        print('回测结果汇总')
        print('='*70)
        print()
        
        if results:
            returns = [r['total_return'] for r in results]
            win_rates = [r['win_rate'] for r in results]
            drawdowns = [r['max_drawdown'] for r in results]
            
            summary = {
                'stock_count': len(results),
                'avg_return': statistics.mean(returns),
                'median_return': statistics.median(returns),
                'max_return': max(returns),
                'min_return': min(returns),
                'avg_win_rate': statistics.mean(win_rates),
                'avg_max_drawdown': statistics.mean(drawdowns),
                'profitable_count': len([r for r in results if r['total_return'] > 0]),
                'elapsed_time': elapsed,
                'timestamp': datetime.now().isoformat(),
                'strategy': '成交量萎缩 (<0.5 倍)',
            }
            
            # 打印结果
            print(f'回测股票数：{len(results)}')
            print(f'总耗时：{elapsed:.1f}秒')
            print()
            print(f'平均收益率：{summary["avg_return"]:+.2f}%')
            print(f'中位收益率：{summary["median_return"]:+.2f}%')
            print(f'最高收益率：{summary["max_return"]:+.2f}%')
            print(f'最低收益率：{summary["min_return"]:+.2f}%')
            print(f'平均胜率：{summary["avg_win_rate"]:.1f}%')
            print(f'平均最大回撤：{summary["avg_max_drawdown"]:.1f}%')
            print(f'盈利股票：{summary["profitable_count"]} ({summary["profitable_count"]/len(results)*100:.1f}%)')
            print()
            print('='*70)
            
            # 保存结果
            output_file = self.results_dir / f'v32_volume_shrink_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print(f'\n结果已保存：{output_file}')
            
            return summary
        else:
            print('❌ 无有效回测结果')
            return {}


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='选股系统 v3.2 回测 (成交量萎缩<0.5 倍卖出)')
    parser.add_argument('--sample', type=int, help='抽样数量')
    parser.add_argument('--full', action='store_true', help='全量回测')
    
    args = parser.parse_args()
    
    backtester = V32VolumeShrinkBacktester()
    
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
