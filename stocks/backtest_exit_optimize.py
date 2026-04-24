#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
止盈止损参数优化回测
测试不同止盈/止损组合的效果
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path
import time
from typing import List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')

CACHE_DIR = Path(__file__).parent / 'data_tushare'
RESULTS_DIR = Path(__file__).parent / 'backtest_results'

# 止盈止损组合
EXIT_COMBOS = [
    {'profit_target': 0.05, 'stop_loss': None, 'name': '止盈 5%'},
    {'profit_target': 0.10, 'stop_loss': None, 'name': '止盈 10%'},
    {'profit_target': 0.15, 'stop_loss': None, 'name': '止盈 15%'},
    {'profit_target': 0.20, 'stop_loss': None, 'name': '止盈 20%'},
    {'profit_target': 0.10, 'stop_loss': 0.05, 'name': '止盈 10%+ 止损 5%'},
    {'profit_target': 0.10, 'stop_loss': 0.10, 'name': '止盈 10%+ 止损 10%'},
    {'profit_target': 0.15, 'stop_loss': 0.05, 'name': '止盈 15%+ 止损 5%'},
    {'profit_target': 0.15, 'stop_loss': 0.10, 'name': '止盈 15%+ 止损 10%'},
    {'profit_target': None, 'stop_loss': 0.10, 'name': '移动止盈 10%'},
    {'profit_target': None, 'stop_loss': 0.15, 'name': '移动止盈 15%'},
]

MA_SHORT, MA_LONG = 15, 20
DEFAULT_INITIAL_CAPITAL = 100000
DEFAULT_FEE_RATE = 0.0003


def load_stock_data(symbol: str) -> Optional[pd.DataFrame]:
    filepath = CACHE_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not data:
            return None
        df = pd.DataFrame(data)
        df = df.rename(columns={
            '日期': 'date', '开盘': 'open', '收盘': 'close',
            '最高': 'high', '最低': 'low', '成交量': 'volume'
        })
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        return df
    except:
        return None


class ExitOptimizeBacktester:
    def __init__(self, initial_capital=DEFAULT_INITIAL_CAPITAL, fee_rate=DEFAULT_FEE_RATE):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
    
    def calc_ma(self, data, period, idx):
        if idx < period - 1:
            return None
        return float(data['close'].iloc[idx-period+1:idx+1].mean())
    
    def run_backtest(self, data, exit_combo, print_log=False):
        profit_target = exit_combo.get('profit_target')
        stop_loss = exit_combo.get('stop_loss')
        is_trailing = profit_target is None and stop_loss is not None
        
        current_capital = self.initial_capital
        position = 0
        buy_price = 0
        highest_price = 0
        
        trades = []
        
        for i in range(MA_LONG + 20, len(data)):
            current_price = float(data['close'].iloc[i])
            current_date = data['date'].iloc[i]
            
            ma_short = self.calc_ma(data, MA_SHORT, i)
            ma_long = self.calc_ma(data, MA_LONG, i)
            ma_short_prev = self.calc_ma(data, MA_SHORT, i-1)
            ma_long_prev = self.calc_ma(data, MA_LONG, i-1)
            
            if position == 0:
                if ma_short_prev and ma_long_prev and ma_short_prev <= ma_long_prev and ma_short > ma_long:
                    shares = int(current_capital * 0.95 / current_price / 100) * 100
                    if shares > 0:
                        cost = shares * current_price * (1 + self.fee_rate)
                        current_capital -= cost
                        position = shares
                        buy_price = current_price
                        highest_price = current_price
                        trades.append({'date': current_date, 'type': '买入', 'price': current_price})
            
            elif position > 0:
                if current_price > highest_price:
                    highest_price = current_price
                
                profit = (current_price - buy_price) / buy_price
                trailing_stop_profit = (highest_price - buy_price) / buy_price
                
                should_sell = False
                sell_reason = ''
                
                # 固定止盈
                if profit_target and profit >= profit_target:
                    should_sell = True
                    sell_reason = f'止盈{profit_target*100:.0f}%'
                
                # 固定止损
                if not should_sell and stop_loss and not is_trailing:
                    if profit <= -stop_loss:
                        should_sell = True
                        sell_reason = f'止损{stop_loss*100:.0f}%'
                
                # 移动止盈
                if not should_sell and is_trailing:
                    trailing_drawdown = (highest_price - current_price) / highest_price
                    if trailing_drawdown >= stop_loss:
                        should_sell = True
                        sell_reason = f'移动止盈{stop_loss*100:.0f}%'
                
                # 死叉卖出
                if not should_sell and ma_short_prev and ma_long_prev:
                    if ma_short < ma_long:
                        should_sell = True
                        sell_reason = '死叉'
                
                if should_sell:
                    revenue = position * current_price * (1 - self.fee_rate)
                    current_capital += revenue
                    profit = (current_price - buy_price) / buy_price
                    trades.append({'date': current_date, 'type': '卖出', 'price': current_price, 
                                  'profit': profit, 'reason': sell_reason})
                    position = 0
                    buy_price = 0
                    highest_price = 0
        
        final_value = current_capital
        if position > 0:
            final_value += position * float(data['close'].iloc[-1])
        
        total_return = (final_value - self.initial_capital) / self.initial_capital
        
        sell_trades = [t for t in trades if t['type'] == '卖出']
        trade_count = len(sell_trades)
        profitable_trades = len([t for t in sell_trades if t['profit'] > 0])
        win_rate = profitable_trades / trade_count * 100 if trade_count > 0 else 0
        
        return {
            'total_return': total_return,
            'trade_count': trade_count,
            'win_rate': win_rate,
            'final_value': final_value
        }


def run_exit_optimization():
    print("="*80)
    print("止盈止损参数优化回测")
    print("="*80)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试组合：{len(EXIT_COMBOS)} 种止盈止损组合")
    print(f"抽样股票：500 只")
    print("="*80)
    
    import random
    stock_files = [f.stem for f in CACHE_DIR.glob('*.json') if f.is_file()]
    stock_files = random.sample(stock_files, min(500, len(stock_files)))
    print(f"抽样：{len(stock_files)} 只股票")
    
    backtester = ExitOptimizeBacktester()
    all_results = []
    
    for exit_combo in EXIT_COMBOS:
        print(f"\n测试：{exit_combo['name']}...")
        
        stock_results = []
        for symbol in stock_files:
            data = load_stock_data(symbol)
            if data is None or len(data) < 200:
                continue
            
            result = backtester.run_backtest(data, exit_combo)
            result['symbol'] = symbol
            stock_results.append(result)
        
        if stock_results:
            avg_return = np.mean([r['total_return'] for r in stock_results])
            avg_win_rate = np.mean([r['win_rate'] for r in stock_results])
            profitable_stocks = len([r for r in stock_results if r['total_return'] > 0])
            
            combo_result = {
                'exit_combo': exit_combo['name'],
                'profit_target': exit_combo.get('profit_target'),
                'stop_loss': exit_combo.get('stop_loss'),
                'avg_return': avg_return,
                'win_rate': avg_win_rate,
                'profitable_stocks': profitable_stocks,
                'total_stocks': len(stock_results),
                'profit_ratio': profitable_stocks / len(stock_results) * 100
            }
            
            all_results.append(combo_result)
            print(f"  平均收益：{avg_return*100:.2f}% | 盈利面：{profitable_stocks/len(stock_results)*100:.1f}%")
    
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    results_df = pd.DataFrame(all_results)
    results_df = results_df.sort_values('avg_return', ascending=False)
    output_file = RESULTS_DIR / f'exit_optimization_{timestamp}.csv'
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n{'='*80}")
    print(f"完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"结果已保存：{output_file}")
    print("="*80)
    
    return all_results


if __name__ == '__main__':
    results = run_exit_optimization()
