#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
选股系统 V3.0 全市场回测 - 使用 2022-2026 完整历史数据

用法:
    python3 backtest_v3_full.py                     # 全量回测 (约 5500 只)
    python3 backtest_v3_full.py --no-filters        # 禁用五重过滤
    python3 backtest_v3_full.py --top 100           # 只回测收益前 100 的股票
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
import argparse
import warnings
from pathlib import Path
import time
from typing import List, Dict, Optional
import statistics

warnings.filterwarnings('ignore')

# ============== 配置区域 ==============
# 完整历史数据目录 (2022-2026)
CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')

# V3.0 默认参数
DEFAULT_SHORT_MA = 15
DEFAULT_LONG_MA = 20
DEFAULT_PROFIT_STOP = 0.10
DEFAULT_INITIAL_CAPITAL = 100000
DEFAULT_FEE_RATE = 0.0003

# ======================================


def load_stock_data(symbol: str) -> Optional[pd.DataFrame]:
    """从缓存加载股票数据"""
    filepath = CACHE_DIR / f'{symbol}.json'
    
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if data is None or 'items' not in data:
            return None
        
        # fields/items 格式
        fields = data['fields']
        items = data['items']
        df = pd.DataFrame(items, columns=fields)
        
        # 重命名列
        df = df.rename(columns={
            'trade_date': 'date',
            'ts_code': 'code',
            'open': 'open',
            'close': 'close',
            'high': 'high',
            'low': 'low',
            'vol': 'volume',
            'amount': 'amount'
        })
        
        # 转换日期
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        
        # 数值转换
        for col in ['open', 'close', 'high', 'low', 'volume', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 排序 (日期升序)
        df = df.sort_values('date').reset_index(drop=True)
        
        return df
        
    except Exception as e:
        return None


class V3Strategy:
    """V3.0 选股策略"""
    
    def __init__(self, short_ma=15, long_ma=20, use_filters=False):
        self.short_ma = short_ma
        self.long_ma = long_ma
        self.use_filters = use_filters
    
    def calc_ma(self, data, period, idx):
        """计算移动平均线"""
        if idx < period - 1:
            return None
        return float(data['close'].iloc[idx-period+1:idx+1].mean())
    
    def calc_ema(self, data, period, idx):
        """计算 EMA"""
        if idx < period - 1:
            return None
        multiplier = 2 / (period + 1)
        ema = float(data['close'].iloc[idx-period+1])
        for i in range(idx-period+2, idx+1):
            ema = (float(data['close'].iloc[i]) - ema) * multiplier + ema
        return float(ema)
    
    def calc_rsi(self, data, period, idx):
        """计算 RSI"""
        if idx < period:
            return None
        
        gains, losses = [], []
        for i in range(idx-period+1, idx+1):
            change = float(data['close'].iloc[i]) - float(data['close'].iloc[i-1])
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return float(100 - (100 / (1 + rs)))
    
    def check_filters(self, data, idx):
        """五重过滤检查"""
        score = 0
        
        # 1. 成交量过滤 (>1.5 倍均量)
        volume = float(data['volume'].iloc[idx])
        avg_volume = float(data['volume'].iloc[idx-20:idx].mean()) if idx >= 20 else 0
        if avg_volume > 0 and volume > avg_volume * 1.5:
            score += 1
        
        # 2. 趋势过滤 (股价>MA200)
        ma200 = self.calc_ma(data, 200, idx)
        current_price = float(data['close'].iloc[idx])
        if ma200 and current_price > ma200:
            score += 1
        
        # 3. RSI 过滤 (50-75)
        rsi = self.calc_rsi(data, 14, idx)
        if rsi and 50 < rsi < 75:
            score += 1
        
        # 4. MACD 过滤 (EMA12 > EMA26)
        ema12 = self.calc_ema(data, 12, idx)
        ema26 = self.calc_ema(data, 26, idx)
        if ema12 and ema26 and ema12 > ema26:
            score += 1
        
        # 5. 均线斜率向上
        ma15 = self.calc_ma(data, self.short_ma, idx)
        ma20 = self.calc_ma(data, self.long_ma, idx)
        ma15_prev = self.calc_ma(data, self.short_ma, idx-3)
        ma20_prev = self.calc_ma(data, self.long_ma, idx-3)
        if ma15_prev and ma20_prev and ma15 > ma15_prev and ma20 > ma20_prev:
            score += 1
        
        return score
    
    def signal(self, data, idx):
        """生成交易信号"""
        if idx < self.long_ma + 5:
            return 'hold'
        
        ma_short = self.calc_ma(data, self.short_ma, idx)
        ma_long = self.calc_ma(data, self.long_ma, idx)
        ma_short_prev = self.calc_ma(data, self.short_ma, idx-1)
        ma_long_prev = self.calc_ma(data, self.long_ma, idx-1)
        
        if ma_short is None or ma_long is None:
            return 'hold'
        
        try:
            # 金叉买入
            if float(ma_short_prev) <= float(ma_long_prev) and float(ma_short) > float(ma_long):
                if self.use_filters:
                    score = self.check_filters(data, idx)
                    if score >= 3:
                        return 'buy'
                else:
                    return 'buy'
            
            # 死叉卖出
            if float(ma_short_prev) >= float(ma_long_prev) and float(ma_short) < float(ma_long):
                return 'sell'
        except:
            pass
        
        return 'hold'


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital=DEFAULT_INITIAL_CAPITAL, fee_rate=DEFAULT_FEE_RATE, profit_stop=DEFAULT_PROFIT_STOP):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.profit_stop = profit_stop
        self.reset()
    
    def reset(self):
        self.current_capital = self.initial_capital
        self.position = None
        self.cost_price = 0
        self.highest_price = 0
        self.trades = []
        self.equity_curve = []
    
    def run(self, strategy, data):
        """运行回测"""
        self.reset()
        
        for i in range(len(data)):
            current_price = float(data['close'].iloc[i])
            signal = strategy.signal(data, i)
            
            # 移动止盈
            if self.position and current_price > self.highest_price:
                self.highest_price = current_price
            
            if self.position:
                drawdown = (self.highest_price - current_price) / self.highest_price
                if drawdown >= self.profit_stop:
                    self._sell(data, i, 'trailing_stop')
                    continue
            
            if signal == 'buy' and not self.position:
                self._buy(data, i)
            elif signal == 'sell' and self.position:
                self._sell(data, i, 'cross_dead')
            
            # 更新净值
            self._update_equity(data, i)
        
        return self._metrics()
    
    def _buy(self, data, idx):
        price = float(data['close'].iloc[idx])
        shares = int(self.current_capital * 0.95 / price / 100) * 100
        
        if shares <= 0:
            return
        
        amount = shares * price
        fee = amount * self.fee_rate
        
        self.current_capital -= (amount + fee)
        self.position = shares
        self.cost_price = price
        self.highest_price = price
        
        self.trades.append({
            'date': data['date'].iloc[idx],
            'action': 'buy',
            'price': price,
            'shares': shares,
            'fee': fee
        })
    
    def _sell(self, data, idx, reason):
        price = float(data['close'].iloc[idx])
        shares = self.position
        amount = shares * price
        fee = amount * self.fee_rate
        profit = amount - (shares * self.cost_price) - fee
        profit_rate = profit / (shares * self.cost_price)
        
        self.current_capital += (amount - fee)
        
        self.trades.append({
            'date': data['date'].iloc[idx],
            'action': 'sell',
            'price': price,
            'shares': shares,
            'fee': fee,
            'profit': profit,
            'profit_rate': profit_rate,
            'reason': reason
        })
        
        self.position = None
        self.cost_price = 0
        self.highest_price = 0
    
    def _update_equity(self, data, idx):
        price = float(data['close'].iloc[idx])
        position_value = self.position * price if self.position else 0
        total = self.current_capital + position_value
        return_rate = (total - self.initial_capital) / self.initial_capital
        
        self.equity_curve.append({
            'date': data['date'].iloc[idx],
            'total': total,
            'return_rate': return_rate
        })
    
    def _metrics(self):
        """计算指标"""
        if not self.trades:
            return None
        
        sell_trades = [t for t in self.trades if t['action'] == 'sell']
        
        if not sell_trades:
            return None
        
        total_return = self.equity_curve[-1]['return_rate'] if self.equity_curve else 0
        
        # 年化收益
        days = len(self.equity_curve)
        annual_return = (1 + total_return) ** (252 / max(days, 1)) - 1
        
        # 最大回撤
        peak = self.initial_capital
        max_dd = 0
        for e in self.equity_curve:
            total = self.initial_capital * (1 + e['return_rate'])
            if total > peak:
                peak = total
            dd = (peak - total) / peak
            if dd > max_dd:
                max_dd = dd
        
        # 胜率
        wins = len([t for t in sell_trades if t['profit'] > 0])
        win_rate = wins / len(sell_trades) * 100 if sell_trades else 0
        
        # 夏普比率
        daily_returns = [e['return_rate'] for e in self.equity_curve]
        if len(daily_returns) > 1:
            daily_diff = np.diff(daily_returns)
            vol = np.std(daily_diff) * np.sqrt(252)
            sharpe = (np.mean(daily_diff) * 252 - 0.03) / vol if vol > 0 else 0
        else:
            sharpe = 0
        
        # 盈亏比
        gross_profit = sum([t['profit'] for t in sell_trades if t['profit'] > 0])
        gross_loss = abs(sum([t['profit'] for t in sell_trades if t['profit'] < 0]))
        pl_ratio = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_dd,
            'sharpe_ratio': sharpe,
            'win_rate': win_rate,
            'trade_count': len(sell_trades),
            'pl_ratio': pl_ratio,
            'total_profit': sum([t['profit'] for t in sell_trades])
        }


def backtest_all(args):
    """全市场回测"""
    print('=' * 80)
    print('📊 选股系统 V3.0 全市场回测 (2022-2026 数据)')
    print('=' * 80)
    
    # 获取股票列表
    stock_files = [f.stem for f in CACHE_DIR.glob('*.json') if f.name != 'stock_list.json']
    
    print(f'数据目录：{CACHE_DIR}')
    print(f'股票总数：{len(stock_files)} 只')
    print(f'策略：MA{args.short_ma}/MA{args.long_ma} + 移动止盈 {args.profit_stop*100:.0f}%')
    print(f'五重过滤：{"启用" if args.use_filters else "禁用"}')
    print()
    
    results = []
    start_time = time.time()
    
    for i, symbol in enumerate(stock_files):
        try:
            data = load_stock_data(symbol)
            
            if data is None or len(data) < args.long_ma + 10:
                continue
            
            strategy = V3Strategy(
                short_ma=args.short_ma,
                long_ma=args.long_ma,
                use_filters=args.use_filters
            )
            
            engine = BacktestEngine(
                initial_capital=args.capital,
                fee_rate=args.fee_rate,
                profit_stop=args.profit_stop
            )
            
            metrics = engine.run(strategy, data)
            
            if metrics:
                results.append({
                    'symbol': symbol,
                    **metrics,
                    'data_count': len(data)
                })
            
            # 进度
            if (i + 1) % 500 == 0 or (i + 1) == len(stock_files):
                elapsed = time.time() - start_time
                speed = (i + 1) / elapsed if elapsed > 0 else 0
                remaining = (len(stock_files) - i - 1) / speed if speed > 0 else 0
                print(f"[{(i+1)/len(stock_files)*100:.1f}%] {i+1}/{len(stock_files)} "
                      f"完成：{len(results)} 只 | "
                      f"速度：{speed:.1f}只/秒 | "
                      f"剩余：{remaining:.0f}秒")
        
        except Exception as e:
            continue
    
    elapsed = time.time() - start_time
    
    # 统计
    if results:
        print()
        print('=' * 80)
        print('📊 全市场回测统计')
        print('=' * 80)
        
        returns = [r['total_return'] for r in results]
        annuals = [r['annual_return'] for r in results]
        win_rates = [r['win_rate'] for r in results]
        sharpe = [r['sharpe_ratio'] for r in results]
        max_dds = [r['max_drawdown'] for r in results]
        
        profitable = len([r for r in returns if r > 0])
        total = len(results)
        
        # TOP 10
        sorted_results = sorted(results, key=lambda x: x['total_return'], reverse=True)
        top10 = sorted_results[:10]
        
        print(f"""
📈 总体统计
   回测股票：    {total} 只
   盈利股票：    {profitable} 只 ({profitable/total*100:.1f}%)
   
📊 收益分布
   平均收益：    {statistics.mean(returns)*100:.2f}%
   中位收益：    {statistics.median(returns)*100:.2f}%
   最高收益：    {max(returns)*100:.2f}%
   最低收益：    {min(returns)*100:.2f}%
   
   平均年化：    {statistics.mean(annuals)*100:.2f}%
   
⚠️  风险指标
   平均最大回撤：{statistics.mean(max_dds)*100:.2f}%
   平均夏普比率：{statistics.mean(sharpe):.2f}
   
🎯 交易统计
   平均胜率：    {statistics.mean(win_rates):.2f}%
   平均交易次数：{statistics.mean([r['trade_count'] for r in results]):.1f} 次

⏱️  回测耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)
""")
        
        print('🏆 TOP 10 收益股票')
        print('-' * 80)
        print(f"{'排名':<6}{'股票':<10}{'总收益':<12}{'年化':<12}{'胜率':<12}{'夏普':<12}{'回撤':<12}")
        print('-' * 80)
        
        for rank, r in enumerate(top10, 1):
            print(f"{rank:<6}{r['symbol']:<10}"
                  f"{r['total_return']*100:>10.2f}%"
                  f"{r['annual_return']*100:>10.2f}%"
                  f"{r['win_rate']:>10.2f}%"
                  f"{r['sharpe_ratio']:>10.2f}"
                  f"{r['max_drawdown']*100:>10.2f}%")
        
        # 收益分布
        print()
        print('📊 收益分布')
        print('-' * 80)
        
        bins = [-50, -20, -10, 0, 10, 20, 50, 100, 500]
        labels = ['<-50%', '-50~-20%', '-20~-10%', '-10~0%', '0~10%', '10~20%', '20~50%', '50~100%', '>100%']
        
        for i, (low, high) in enumerate(zip(bins[:-1], bins[1:])):
            count = len([r for r in returns if low <= r*100 < high])
            pct = count / total * 100
            bar = '█' * int(pct / 2)
            print(f"{labels[i]:<12} {count:>5} 只 ({pct:>5.1f}%) {bar}")
        
        # 保存结果
        results_df = pd.DataFrame(results)
        output_dir = Path('/home/admin/.openclaw/workspace/stocks/backtest_results')
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'backtest_full_{timestamp}.csv'
        results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print()
        print(f'💾 详细结果已保存至：{output_file}')
        
        return results
    
    return None


def main():
    parser = argparse.ArgumentParser(description='选股系统 V3.0 全市场回测')
    
    parser.add_argument('--short-ma', type=int, default=DEFAULT_SHORT_MA,
                        help=f'短期均线 (默认：{DEFAULT_SHORT_MA})')
    parser.add_argument('--long-ma', type=int, default=DEFAULT_LONG_MA,
                        help=f'长期均线 (默认：{DEFAULT_LONG_MA})')
    parser.add_argument('--profit-stop', type=float, default=DEFAULT_PROFIT_STOP,
                        help=f'移动止盈 (默认：{DEFAULT_PROFIT_STOP})')
    parser.add_argument('--capital', type=float, default=DEFAULT_INITIAL_CAPITAL,
                        help=f'初始资金 (默认：{DEFAULT_INITIAL_CAPITAL})')
    parser.add_argument('--fee-rate', type=float, default=DEFAULT_FEE_RATE,
                        help=f'手续费率 (默认：{DEFAULT_FEE_RATE})')
    parser.add_argument('--use-filters', action='store_true',
                        help='启用五重过滤 (默认禁用)')
    
    args = parser.parse_args()
    
    backtest_all(args)


if __name__ == '__main__':
    main()