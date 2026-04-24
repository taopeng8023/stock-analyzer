#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
均线+MACD 组合策略全市场回测
买入：MA 金叉 + MACD 金叉 (双重确认)
卖出：MA 死叉 或 MACD 死叉
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

MA_COMBOS = [
    {'short': 10, 'long': 20, 'name': 'MA10/20+MACD'},
    {'short': 15, 'long': 20, 'name': 'MA15/20+MACD'},
    {'short': 10, 'long': 30, 'name': 'MA10/30+MACD'},
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
            '日期': 'date', '收盘': 'close', '成交量': 'volume'
        })
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        return df
    except:
        return None


class MAMACDBacktester:
    def __init__(self, initial_capital=DEFAULT_INITIAL_CAPITAL, fee_rate=DEFAULT_FEE_RATE):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
    
    def calc_ma(self, data, period, idx):
        if idx < period - 1:
            return None
        return float(data['close'].iloc[idx-period+1:idx+1].mean())
    
    def calc_ema(self, data, period, idx):
        if idx < period - 1:
            return None
        multiplier = 2 / (period + 1)
        ema = float(data['close'].iloc[idx-period+1])
        for i in range(idx-period+2, idx+1):
            ema = (float(data['close'].iloc[i]) - ema) * multiplier + ema
        return ema
    
    def calc_macd(self, data, idx):
        if idx < 26 + 12:
            return None, None, None
        
        ema12 = self.calc_ema(data, 12, idx)
        ema26 = self.calc_ema(data, 26, idx)
        
        if ema12 is None or ema26 is None:
            return None, None, None
        
        dif = ema12 - ema26
        
        # 计算 DEA
        dif_values = []
        for i in range(idx-8, idx+1):
            d = self.calc_macd_single(data, i)
            if d[0] is not None:
                dif_values.append(d[0])
        
        if len(dif_values) < 9:
            return dif, None, None
        
        dea = sum(dif_values[-9:]) / 9
        macd = 2 * (dif - dea)
        
        return dif, dea, macd
    
    def calc_macd_single(self, data, idx):
        ema12 = self.calc_ema(data, 12, idx)
        ema26 = self.calc_ema(data, 26, idx)
        if ema12 is None or ema26 is None:
            return None, None, None
        dif = ema12 - ema26
        return dif, None, None
    
    def run_backtest(self, data, combo, print_log=False):
        short_ma, long_ma = combo['short'], combo['long']
        
        current_capital = self.initial_capital
        position = 0
        buy_price = 0
        highest_price = 0
        
        trades = []
        
        for i in range(long_ma + 60, len(data)):
            current_price = float(data['close'].iloc[i])
            current_date = data['date'].iloc[i]
            
            ma_short = self.calc_ma(data, short_ma, i)
            ma_long = self.calc_ma(data, long_ma, i)
            ma_short_prev = self.calc_ma(data, short_ma, i-1)
            ma_long_prev = self.calc_ma(data, long_ma, i-1)
            
            macd = self.calc_macd(data, i)
            macd_prev = self.calc_macd(data, i-1)
            
            if position == 0:
                # 双重确认：MA 金叉 + MACD 金叉
                ma_golden = ma_short_prev and ma_long_prev and ma_short_prev <= ma_long_prev and ma_short > ma_long
                macd_golden = False
                if macd[1] and macd_prev[1]:
                    macd_golden = macd_prev[2] < 0 and macd[2] > 0
                
                if ma_golden and macd_golden:
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
                
                drawdown = (highest_price - current_price) / highest_price
                should_sell = drawdown >= PROFIT_STOP
                
                # MA 死叉或 MACD 死叉
                if not should_sell:
                    ma_death = ma_short_prev and ma_long_prev and ma_short_prev >= ma_long_prev and ma_short < ma_long
                    macd_death = macd[1] and macd_prev[1] and macd_prev[2] > 0 and macd[2] < 0
                    if ma_death or macd_death:
                        should_sell = True
                
                if should_sell:
                    revenue = position * current_price * (1 - self.fee_rate)
                    current_capital += revenue
                    profit = (current_price - buy_price) / buy_price
                    trades.append({'date': current_date, 'type': '卖出', 'price': current_price, 'profit': profit})
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
        
        return {'total_return': total_return, 'trade_count': trade_count, 'win_rate': win_rate}


def run_full_market_backtest():
    print("="*80)
    print("均线+MACD 组合策略全市场回测")
    print("="*80)
    
    stock_files = [f.stem for f in CACHE_DIR.glob('*.json') if f.is_file()]
    print(f"测试股票：{len(stock_files)} 只")
    
    backtester = MAMACDBacktester()
    all_results = []
    
    for combo in MA_COMBOS:
        print(f"\n测试：{combo['name']}...")
        stock_results = []
        
        for i, symbol in enumerate(stock_files):
            data = load_stock_data(symbol)
            if data is None or len(data) < 200:
                continue
            
            result = backtester.run_backtest(data, combo)
            result['symbol'] = symbol
            stock_results.append(result)
            
            if (i + 1) % 1000 == 0:
                print(f"  进度：{i+1}/{len(stock_files)}")
        
        if stock_results:
            avg_return = np.mean([r['total_return'] for r in stock_results])
            avg_win_rate = np.mean([r['win_rate'] for r in stock_results])
            profitable_stocks = len([r for r in stock_results if r['total_return'] > 0])
            
            combo_result = {
                'combo': combo['name'],
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
    output_file = RESULTS_DIR / f'ma_macd_full_market_{timestamp}.csv'
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n完成：{output_file}")
    return all_results


if __name__ == '__main__':
    results = run_full_market_backtest()
