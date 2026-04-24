#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三均线策略全市场回测
买入：MA5 > MA10 > MA20 (多头排列)
卖出：MA5 < MA10 (短期死叉) 或 移动止盈 10%
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

# 三均线组合配置
TRIPLE_MA_COMBOS = [
    {'ma1': 5, 'ma2': 10, 'ma3': 20, 'name': 'MA5/10/20'},
    {'ma1': 5, 'ma2': 10, 'ma3': 30, 'name': 'MA5/10/30'},
    {'ma1': 5, 'ma2': 20, 'ma3': 30, 'name': 'MA5/20/30'},
    {'ma1': 10, 'ma2': 20, 'ma3': 30, 'name': 'MA10/20/30'},
    {'ma1': 10, 'ma2': 20, 'ma3': 60, 'name': 'MA10/20/60'},
]

DEFAULT_INITIAL_CAPITAL = 100000
DEFAULT_FEE_RATE = 0.0003
PROFIT_STOP = 0.10


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
            '最高': 'high', '最低': 'low', '成交量': 'volume', '成交额': 'amount'
        })
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        return df
    except:
        return None


class TripleMABacktester:
    def __init__(self, initial_capital=DEFAULT_INITIAL_CAPITAL, fee_rate=DEFAULT_FEE_RATE):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
    
    def calc_ma(self, data, period, idx):
        if idx < period - 1:
            return None
        return float(data['close'].iloc[idx-period+1:idx+1].mean())
    
    def run_backtest(self, data, combo, print_log=False):
        ma1, ma2, ma3 = combo['ma1'], combo['ma2'], combo['ma3']
        
        current_capital = self.initial_capital
        position = 0
        buy_price = 0
        highest_price = 0
        
        trades = []
        equity_curve = []
        
        for i in range(ma3 + 20, len(data)):
            current_price = float(data['close'].iloc[i])
            current_date = data['date'].iloc[i]
            
            ma1_val = self.calc_ma(data, ma1, i)
            ma2_val = self.calc_ma(data, ma2, i)
            ma3_val = self.calc_ma(data, ma3, i)
            
            ma1_prev = self.calc_ma(data, ma1, i-1)
            ma2_prev = self.calc_ma(data, ma2, i-1)
            
            if position == 0:
                # 买入：三均线多头排列 (MA1>MA2>MA3)
                if ma1_val > ma2_val > ma3_val:
                    shares = int(current_capital * 0.95 / current_price / 100) * 100
                    if shares > 0:
                        cost = shares * current_price * (1 + self.fee_rate)
                        current_capital -= cost
                        position = shares
                        buy_price = current_price
                        highest_price = current_price
                        
                        trades.append({'date': current_date, 'type': '买入', 'price': current_price, 'shares': shares})
            
            elif position > 0:
                # 更新最高价
                if current_price > highest_price:
                    highest_price = current_price
                
                # 移动止盈
                drawdown = (highest_price - current_price) / highest_price
                should_sell = drawdown >= PROFIT_STOP
                
                # 死叉卖出：MA1 < MA2
                if not should_sell and ma1_prev and ma2_prev:
                    if ma1_val < ma2_val:
                        should_sell = True
                
                if should_sell:
                    revenue = position * current_price * (1 - self.fee_rate)
                    current_capital += revenue
                    profit = (current_price - buy_price) / buy_price
                    
                    trades.append({'date': current_date, 'type': '卖出', 'price': current_price, 
                                  'shares': position, 'profit': profit})
                    
                    position = 0
                    buy_price = 0
                    highest_price = 0
            
            total_assets = current_capital + (position * current_price if position > 0 else 0)
            return_rate = (total_assets - self.initial_capital) / self.initial_capital
            equity_curve.append({'date': current_date, 'total_assets': total_assets, 'return_rate': return_rate})
        
        final_value = current_capital
        if position > 0:
            final_value += position * float(data['close'].iloc[-1])
        
        total_return = (final_value - self.initial_capital) / self.initial_capital
        
        sell_trades = [t for t in trades if t['type'] == '卖出']
        trade_count = len(sell_trades)
        profitable_trades = len([t for t in sell_trades if t['profit'] > 0])
        win_rate = profitable_trades / trade_count * 100 if trade_count > 0 else 0
        
        return_rates = [e['return_rate'] for e in equity_curve]
        peak = 0
        max_drawdown = 0
        for r in return_rates:
            assets = self.initial_capital * (1 + r)
            if assets > peak:
                peak = assets
            drawdown = (peak - assets) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return {
            'total_return': total_return,
            'trade_count': trade_count,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'final_value': final_value
        }


def run_full_market_backtest():
    print("="*80)
    print("三均线策略全市场回测")
    print("="*80)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试组合：{len(TRIPLE_MA_COMBOS)} 种三均线组合")
    print(f"全市场股票：3620 只")
    print("="*80)
    
    stock_files = [f.stem for f in CACHE_DIR.glob('*.json') if f.is_file()]
    print(f"找到 {len(stock_files)} 只股票")
    
    backtester = TripleMABacktester()
    all_results = []
    
    for combo in TRIPLE_MA_COMBOS:
        print(f"\n{'='*80}")
        print(f"测试组合：{combo['name']} (MA{combo['ma1']}/MA{combo['ma2']}/MA{combo['ma3']})")
        print(f"{'='*80}")
        
        stock_results = []
        
        for i, symbol in enumerate(stock_files):
            data = load_stock_data(symbol)
            if data is None or len(data) < 200:
                continue
            
            result = backtester.run_backtest(data, combo)
            result['symbol'] = symbol
            stock_results.append(result)
            
            if (i + 1) % 1000 == 0:
                print(f"进度：{i+1}/{len(stock_files)} ({(i+1)/len(stock_files)*100:.1f}%)")
        
        if stock_results:
            avg_return = np.mean([r['total_return'] for r in stock_results])
            avg_win_rate = np.mean([r['win_rate'] for r in stock_results])
            avg_drawdown = np.mean([r['max_drawdown'] for r in stock_results])
            avg_trades = np.mean([r['trade_count'] for r in stock_results])
            profitable_stocks = len([r for r in stock_results if r['total_return'] > 0])
            
            combo_result = {
                'combo': combo['name'],
                'ma1': combo['ma1'],
                'ma2': combo['ma2'],
                'ma3': combo['ma3'],
                'avg_return': avg_return,
                'win_rate': avg_win_rate,
                'max_drawdown': avg_drawdown,
                'avg_trades': avg_trades,
                'profitable_stocks': profitable_stocks,
                'total_stocks': len(stock_results),
                'profit_ratio': profitable_stocks / len(stock_results) * 100
            }
            
            all_results.append(combo_result)
            
            print(f"\n结果:")
            print(f"  平均收益：{avg_return*100:.2f}%")
            print(f"  盈利股票：{profitable_stocks}/{len(stock_results)} ({profitable_stocks/len(stock_results)*100:.1f}%)")
            print(f"  平均胜率：{avg_win_rate:.1f}%")
            print(f"  平均回撤：{avg_drawdown*100:.2f}%")
    
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    results_df = pd.DataFrame(all_results)
    results_df = results_df.sort_values('avg_return', ascending=False)
    output_file = RESULTS_DIR / f'triple_ma_full_market_{timestamp}.csv'
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n{'='*80}")
    print(f"完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"结果已保存：{output_file}")
    print("="*80)
    
    return all_results


if __name__ == '__main__':
    results = run_full_market_backtest()
