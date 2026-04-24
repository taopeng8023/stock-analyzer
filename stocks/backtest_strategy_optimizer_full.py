#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全市场策略优化回测系统
测试多种买入卖出策略，找出胜率高、收益高的最佳策略

策略类型：
1. 单均线策略（价格突破MA）
2. 双均线金叉死叉策略
3. 三均线策略
4. RSI超买超卖策略
5. MACD金叉死叉策略
6. 布林带突破策略
7. 量价突破策略
8. KDJ策略
9. 组合策略

用法：
    python backtest_strategy_optimizer_full.py --sample 500  # 抽样测试
    python backtest_strategy_optimizer_full.py --all         # 全市场测试
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
import argparse
import warnings
from pathlib import Path
import time
from typing import List, Dict, Optional, Tuple
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

warnings.filterwarnings('ignore')

# ============== 配置 ==============
CACHE_DIR = Path(__file__).parent / 'data_tushare'
RESULTS_DIR = Path(__file__).parent / 'backtest_results'
RESULTS_DIR.mkdir(exist_ok=True)

DEFAULT_INITIAL_CAPITAL = 100000
DEFAULT_FEE_RATE = 0.0003
DEFAULT_SLIPPAGE = 0.001  # 滑点


def load_stock_data(symbol: str) -> Optional[pd.DataFrame]:
    """从缓存加载股票数据"""
    filepath = CACHE_DIR / f'{symbol}.json'
    
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if data is None or len(data) == 0:
            return None
        
        if isinstance(data, dict) and 'fields' in data and 'items' in data:
            fields = data['fields']
            items = data['items']
            df = pd.DataFrame(items, columns=fields)
            
            df = df.rename(columns={
                'trade_date': 'date',
                'vol': 'volume'
            })
        else:
            df = pd.DataFrame(data)
            df = df.rename(columns={
                '日期': 'date',
                '成交量': 'volume'
            })
        
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        
        # 确保数值类型
        for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
        
    except Exception as e:
        return None


# ============== 技术指标计算 ==============

def calc_ma(series: pd.Series, period: int) -> pd.Series:
    """移动平均线"""
    return series.rolling(window=period).mean()


def calc_ema(series: pd.Series, period: int) -> pd.Series:
    """指数移动平均线"""
    return series.ewm(span=period, adjust=False).mean()


def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI指标"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calc_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """MACD指标"""
    ema_fast = calc_ema(close, fast)
    ema_slow = calc_ema(close, slow)
    dif = ema_fast - ema_slow
    dea = calc_ema(dif, signal)
    macd = (dif - dea) * 2
    return dif, dea, macd


def calc_kdj(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """KDJ指标"""
    llv = low.rolling(window=n).min()
    hhv = high.rolling(window=n).max()
    rsv = (close - llv) / (hhv - llv) * 100
    k = rsv.ewm(alpha=1/m1, adjust=False).mean()
    d = k.ewm(alpha=1/m2, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


def calc_bollinger(close: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """布林带"""
    mid = calc_ma(close, period)
    std = close.rolling(window=period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return upper, mid, lower


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """ATR真实波幅"""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


# ============== 策略定义 ==============

class Strategy:
    """策略基类"""
    def __init__(self, name: str):
        self.name = name
        self.signals = []
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """生成信号：1=买入，-1=卖出，0=持有"""
        raise NotImplementedError


class SingleMAStrategy(Strategy):
    """单均线策略：价格突破MA买入，跌破MA卖出"""
    def __init__(self, period: int = 20):
        super().__init__(f'MA{period}')
        self.period = period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        ma = calc_ma(data['close'], self.period)
        signals = pd.Series(0, index=data.index)
        
        # 价格突破MA买入
        signals[(data['close'] > ma) & (data['close'].shift(1) <= ma.shift(1))] = 1
        # 价格跌破MA卖出
        signals[(data['close'] < ma) & (data['close'].shift(1) >= ma.shift(1))] = -1
        
        return signals


class DoubleMAStrategy(Strategy):
    """双均线策略：金叉买入，死叉卖出"""
    def __init__(self, fast: int = 5, slow: int = 20):
        super().__init__(f'MA{fast}/MA{slow}')
        self.fast = fast
        self.slow = slow
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        ma_fast = calc_ma(data['close'], self.fast)
        ma_slow = calc_ma(data['close'], self.slow)
        signals = pd.Series(0, index=data.index)
        
        # 金叉
        signals[(ma_fast > ma_slow) & (ma_fast.shift(1) <= ma_slow.shift(1))] = 1
        # 死叉
        signals[(ma_fast < ma_slow) & (ma_fast.shift(1) >= ma_slow.shift(1))] = -1
        
        return signals


class TripleMAStrategy(Strategy):
    """三均线策略：短中长期均线共振"""
    def __init__(self, short: int = 5, mid: int = 10, long: int = 20):
        super().__init__(f'MA{short}/MA{mid}/MA{long}')
        self.short = short
        self.mid = mid
        self.long = long
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        ma_short = calc_ma(data['close'], self.short)
        ma_mid = calc_ma(data['close'], self.mid)
        ma_long = calc_ma(data['close'], self.long)
        signals = pd.Series(0, index=data.index)
        
        # 多头排列买入：短>中>长 且 中>长上穿
        bullish = (ma_short > ma_mid) & (ma_mid > ma_long)
        golden_cross = (ma_mid > ma_long) & (ma_mid.shift(1) <= ma_long.shift(1))
        signals[bullish & golden_cross] = 1
        
        # 空头排列卖出
        bearish = (ma_short < ma_mid) & (ma_mid < ma_long)
        death_cross = (ma_mid < ma_long) & (ma_mid.shift(1) >= ma_long.shift(1))
        signals[bearish & death_cross] = -1
        
        return signals


class RSIStrategy(Strategy):
    """RSI策略：超卖买入，超买卖出"""
    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        super().__init__(f'RSI{period}')
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        rsi = calc_rsi(data['close'], self.period)
        signals = pd.Series(0, index=data.index)
        
        # RSI超卖回升买入
        signals[(rsi > self.oversold) & (rsi.shift(1) <= self.oversold)] = 1
        # RSI超买回落卖出
        signals[(rsi < self.overbought) & (rsi.shift(1) >= self.overbought)] = -1
        
        return signals


class MACDStrategy(Strategy):
    """MACD策略：金叉买入，死叉卖出"""
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__(f'MACD({fast},{slow},{signal})')
        self.fast = fast
        self.slow = slow
        self.signal = signal
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        dif, dea, macd = calc_macd(data['close'], self.fast, self.slow, self.signal)
        signals = pd.Series(0, index=data.index)
        
        # MACD金叉
        signals[(dif > dea) & (dif.shift(1) <= dea.shift(1))] = 1
        # MACD死叉
        signals[(dif < dea) & (dif.shift(1) >= dea.shift(1))] = -1
        
        return signals


class BollingerStrategy(Strategy):
    """布林带策略：下轨买入，上轨卖出"""
    def __init__(self, period: int = 20, std_dev: float = 2):
        super().__init__(f'BOLL({period},{std_dev})')
        self.period = period
        self.std_dev = std_dev
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        upper, mid, lower = calc_bollinger(data['close'], self.period, self.std_dev)
        signals = pd.Series(0, index=data.index)
        
        # 触及下轨买入
        signals[(data['close'] <= lower) & (data['close'].shift(1) > lower.shift(1))] = 1
        # 触及上轨卖出
        signals[(data['close'] >= upper) & (data['close'].shift(1) < upper.shift(1))] = -1
        
        return signals


class VolumeBreakoutStrategy(Strategy):
    """量价突破策略：放量突破前高买入"""
    def __init__(self, lookback: int = 20, volume_mult: float = 2.0):
        super().__init__(f'VolBreak({lookback},{volume_mult})')
        self.lookback = lookback
        self.volume_mult = volume_mult
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)
        
        high_roll = data['high'].rolling(window=self.lookback).max().shift(1)
        vol_roll = data['volume'].rolling(window=self.lookback).mean().shift(1)
        
        # 放量突破前高买入
        breakout = (data['close'] > high_roll) & (data['volume'] > vol_roll * self.volume_mult)
        signals[breakout] = 1
        
        # 跌破前低卖出
        low_roll = data['low'].rolling(window=self.lookback).min().shift(1)
        breakdown = data['close'] < low_roll
        signals[breakdown] = -1
        
        return signals


class KDJStrategy(Strategy):
    """KDJ策略：金叉买入，死叉卖出"""
    def __init__(self, n: int = 9, m1: int = 3, m2: int = 3):
        super().__init__(f'KDJ({n},{m1},{m2})')
        self.n = n
        self.m1 = m1
        self.m2 = m2
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        k, d, j = calc_kdj(data['high'], data['low'], data['close'], self.n, self.m1, self.m2)
        signals = pd.Series(0, index=data.index)
        
        # K线上穿D线买入
        signals[(k > d) & (k.shift(1) <= d.shift(1))] = 1
        # K线下穿D线卖出
        signals[(k < d) & (k.shift(1) >= d.shift(1))] = -1
        
        return signals


class CompositeStrategy(Strategy):
    """组合策略：多信号融合"""
    def __init__(self, strategies: List[Strategy], min_signals: int = 2):
        super().__init__(f'Composite({len(strategies)})')
        self.strategies = strategies
        self.min_signals = min_signals
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        # 收集所有策略信号
        all_signals = []
        for s in self.strategies:
            all_signals.append(s.generate_signals(data))
        
        # 汇总信号
        buy_count = sum([sig == 1 for sig in all_signals])
        sell_count = sum([sig == -1 for sig in all_signals])
        
        signals = pd.Series(0, index=data.index)
        
        # 至少min_signals个策略同时发出买入信号
        signals[buy_count >= self.min_signals] = 1
        signals[sell_count >= self.min_signals] = -1
        
        return signals


# ============== 回测引擎 ==============

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital=DEFAULT_INITIAL_CAPITAL, fee_rate=DEFAULT_FEE_RATE, 
                 slippage=DEFAULT_SLIPPAGE, trailing_stop=None, take_profit=None, stop_loss=None):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.trailing_stop = trailing_stop  # 移动止盈比例
        self.take_profit = take_profit      # 固定止盈比例
        self.stop_loss = stop_loss          # 固定止损比例
    
    def run(self, strategy: Strategy, data: pd.DataFrame) -> Dict:
        """执行回测"""
        if len(data) < 50:
            return None
        
        # 生成信号
        signals = strategy.generate_signals(data)
        
        # 初始化
        capital = self.initial_capital
        position = 0  # 持仓数量
        cost_price = 0
        highest_price = 0
        trades = []
        equity_curve = []
        
        for i in range(len(data)):
            date = data['date'].iloc[i]
            close = float(data['close'].iloc[i])
            signal = signals.iloc[i]
            
            # 更新最高价（用于移动止盈）
            if position > 0:
                highest_price = max(highest_price, close)
            
            # 移动止盈检查
            if position > 0 and self.trailing_stop:
                drawdown = (highest_price - close) / highest_price
                if drawdown >= self.trailing_stop:
                    # 卖出
                    sell_price = close * (1 - self.slippage)
                    sell_amount = position * sell_price
                    fee = sell_amount * self.fee_rate
                    profit = sell_amount - (position * cost_price) - fee
                    
                    trades.append({
                        'date': date,
                        'type': 'sell',
                        'price': sell_price,
                        'shares': position,
                        'profit': profit,
                        'reason': 'trailing_stop'
                    })
                    
                    capital = sell_amount - fee
                    position = 0
                    cost_price = 0
                    highest_price = 0
                    continue
            
            # 固定止盈止损检查
            if position > 0 and (self.take_profit or self.stop_loss):
                profit_pct = (close - cost_price) / cost_price
                
                if self.take_profit and profit_pct >= self.take_profit:
                    # 止盈卖出
                    sell_price = close * (1 - self.slippage)
                    sell_amount = position * sell_price
                    fee = sell_amount * self.fee_rate
                    profit = sell_amount - (position * cost_price) - fee
                    
                    trades.append({
                        'date': date,
                        'type': 'sell',
                        'price': sell_price,
                        'shares': position,
                        'profit': profit,
                        'reason': 'take_profit'
                    })
                    
                    capital = sell_amount - fee
                    position = 0
                    cost_price = 0
                    continue
                
                if self.stop_loss and profit_pct <= -self.stop_loss:
                    # 止损卖出
                    sell_price = close * (1 - self.slippage)
                    sell_amount = position * sell_price
                    fee = sell_amount * self.fee_rate
                    profit = sell_amount - (position * cost_price) - fee
                    
                    trades.append({
                        'date': date,
                        'type': 'sell',
                        'price': sell_price,
                        'shares': position,
                        'profit': profit,
                        'reason': 'stop_loss'
                    })
                    
                    capital = sell_amount - fee
                    position = 0
                    cost_price = 0
                    continue
            
            # 处理信号
            if signal == 1 and position == 0:  # 买入
                buy_price = close * (1 + self.slippage)
                max_shares = int((capital * 0.95) / buy_price / 100) * 100  # 满仓买入
                if max_shares >= 100:
                    buy_amount = max_shares * buy_price
                    fee = buy_amount * self.fee_rate
                    
                    if capital >= buy_amount + fee:
                        capital -= (buy_amount + fee)
                        position = max_shares
                        cost_price = buy_price
                        highest_price = buy_price
                        
                        trades.append({
                            'date': date,
                            'type': 'buy',
                            'price': buy_price,
                            'shares': max_shares,
                            'reason': 'signal'
                        })
            
            elif signal == -1 and position > 0:  # 卖出
                sell_price = close * (1 - self.slippage)
                sell_amount = position * sell_price
                fee = sell_amount * self.fee_rate
                profit = sell_amount - (position * cost_price) - fee
                
                trades.append({
                    'date': date,
                    'type': 'sell',
                    'price': sell_price,
                    'shares': position,
                    'profit': profit,
                    'reason': 'signal'
                })
                
                capital = sell_amount - fee
                position = 0
                cost_price = 0
                highest_price = 0
            
            # 记录权益
            total_value = capital + (position * close if position > 0 else 0)
            equity_curve.append({
                'date': date,
                'value': total_value,
                'return': (total_value - self.initial_capital) / self.initial_capital
            })
        
        # 强制平仓
        if position > 0:
            last_price = float(data['close'].iloc[-1])
            last_date = data['date'].iloc[-1]
            sell_amount = position * last_price
            fee = sell_amount * self.fee_rate
            profit = sell_amount - (position * cost_price) - fee
            capital = sell_amount - fee
            
            trades.append({
                'date': last_date,
                'type': 'sell',
                'price': last_price,
                'shares': position,
                'profit': profit,
                'reason': 'force_close'
            })
        
        # 计算统计指标
        return self._calculate_metrics(trades, equity_curve)
    
    def _calculate_metrics(self, trades: List[Dict], equity_curve: List[Dict]) -> Dict:
        """计算回测指标"""
        if not trades or not equity_curve:
            return None
        
        # 过滤卖出交易
        sell_trades = [t for t in trades if t['type'] == 'sell']
        
        if not sell_trades:
            return None
        
        # 基本统计
        total_profit = sum([t['profit'] for t in sell_trades])
        profit_trades = [t for t in sell_trades if t['profit'] > 0]
        loss_trades = [t for t in sell_trades if t['profit'] <= 0]
        
        win_count = len(profit_trades)
        loss_count = len(loss_trades)
        total_trades = len(sell_trades)
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        # 盈亏比
        gross_profit = sum([t['profit'] for t in profit_trades]) if profit_trades else 0
        gross_loss = abs(sum([t['profit'] for t in loss_trades])) if loss_trades else 1
        profit_loss_ratio = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # 收益率
        final_value = equity_curve[-1]['value'] if equity_curve else self.initial_capital
        total_return = (final_value - self.initial_capital) / self.initial_capital
        
        # 年化收益
        if len(equity_curve) > 1:
            days = (equity_curve[-1]['date'] - equity_curve[0]['date']).days
            annual_return = (1 + total_return) ** (365 / max(days, 1)) - 1 if days > 0 else 0
        else:
            annual_return = 0
        
        # 最大回撤
        max_drawdown = 0
        peak = 0
        for eq in equity_curve:
            if eq['value'] > peak:
                peak = eq['value']
            drawdown = (peak - eq['value']) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        # 夏普比率
        if len(equity_curve) > 1:
            returns = [equity_curve[i]['return'] - equity_curve[i-1]['return'] 
                      for i in range(1, len(equity_curve))]
            if returns and np.std(returns) > 0:
                sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
            else:
                sharpe = 0
        else:
            sharpe = 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe,
            'total_profit': total_profit,
            'final_value': final_value
        }


# ============== 参数优化 ==============

def optimize_double_ma(data: pd.DataFrame) -> Dict:
    """优化双均线参数"""
    best_result = None
    best_params = None
    best_score = -float('inf')
    
    for fast in [5, 7, 10, 15, 20]:
        for slow in [20, 30, 40, 50, 60]:
            if fast >= slow:
                continue
            
            strategy = DoubleMAStrategy(fast, slow)
            engine = BacktestEngine(trailing_stop=0.10)
            result = engine.run(strategy, data)
            
            if result and result['total_trades'] >= 3:
                # 综合评分：胜率*权重 + 收益*权重 - 回撤*权重
                score = (result['win_rate'] * 0.3 + 
                        min(result['annual_return'], 1) * 0.5 - 
                        result['max_drawdown'] * 0.2)
                
                if score > best_score:
                    best_score = score
                    best_params = {'fast': fast, 'slow': slow}
                    best_result = result
    
    return {'params': best_params, 'result': best_result, 'score': best_score}


def optimize_single_ma(data: pd.DataFrame) -> Dict:
    """优化单均线参数"""
    best_result = None
    best_params = None
    best_score = -float('inf')
    
    for period in [10, 15, 20, 30, 40, 50, 60]:
        strategy = SingleMAStrategy(period)
        engine = BacktestEngine(trailing_stop=0.10)
        result = engine.run(strategy, data)
        
        if result and result['total_trades'] >= 3:
            score = (result['win_rate'] * 0.3 + 
                    min(result['annual_return'], 1) * 0.5 - 
                    result['max_drawdown'] * 0.2)
            
            if score > best_score:
                best_score = score
                best_params = {'period': period}
                best_result = result
    
    return {'params': best_params, 'result': best_result, 'score': best_score}


def optimize_rsi(data: pd.DataFrame) -> Dict:
    """优化RSI参数"""
    best_result = None
    best_params = None
    best_score = -float('inf')
    
    for period in [6, 9, 14, 21]:
        for oversold in [20, 25, 30, 35]:
            for overbought in [65, 70, 75, 80]:
                if oversold >= overbought:
                    continue
                
                strategy = RSIStrategy(period, oversold, overbought)
                engine = BacktestEngine(trailing_stop=0.10)
                result = engine.run(strategy, data)
                
                if result and result['total_trades'] >= 3:
                    score = (result['win_rate'] * 0.3 + 
                            min(result['annual_return'], 1) * 0.5 - 
                            result['max_drawdown'] * 0.2)
                    
                    if score > best_score:
                        best_score = score
                        best_params = {'period': period, 'oversold': oversold, 'overbought': overbought}
                        best_result = result
    
    return {'params': best_params, 'result': best_result, 'score': best_score}


def optimize_macd(data: pd.DataFrame) -> Dict:
    """优化MACD参数"""
    best_result = None
    best_params = None
    best_score = -float('inf')
    
    # 经典参数组合
    param_combos = [
        (12, 26, 9),   # 经典
        (6, 13, 5),    # 快速
        (8, 17, 9),    # 中速
        (19, 39, 9),   # 慢速
        (5, 34, 5),    # 短线
    ]
    
    for fast, slow, signal in param_combos:
        strategy = MACDStrategy(fast, slow, signal)
        engine = BacktestEngine(trailing_stop=0.10)
        result = engine.run(strategy, data)
        
        if result and result['total_trades'] >= 3:
            score = (result['win_rate'] * 0.3 + 
                    min(result['annual_return'], 1) * 0.5 - 
                    result['max_drawdown'] * 0.2)
            
            if score > best_score:
                best_score = score
                best_params = {'fast': fast, 'slow': slow, 'signal': signal}
                best_result = result
    
    return {'params': best_params, 'result': best_result, 'score': best_score}


def optimize_bollinger(data: pd.DataFrame) -> Dict:
    """优化布林带参数"""
    best_result = None
    best_params = None
    best_score = -float('inf')
    
    for period in [10, 15, 20, 25]:
        for std_dev in [1.5, 2.0, 2.5]:
            strategy = BollingerStrategy(period, std_dev)
            engine = BacktestEngine(trailing_stop=0.10)
            result = engine.run(strategy, data)
            
            if result and result['total_trades'] >= 3:
                score = (result['win_rate'] * 0.3 + 
                        min(result['annual_return'], 1) * 0.5 - 
                        result['max_drawdown'] * 0.2)
                
                if score > best_score:
                    best_score = score
                    best_params = {'period': period, 'std_dev': std_dev}
                    best_result = result
    
    return {'params': best_params, 'result': best_result, 'score': best_score}


def test_all_strategies(data: pd.DataFrame, trailing_stop: float = 0.10) -> List[Dict]:
    """测试所有策略类型"""
    results = []
    
    # 预定义策略列表
    strategies = [
        ('MA5/MA20', DoubleMAStrategy(5, 20)),
        ('MA10/MA20', DoubleMAStrategy(10, 20)),
        ('MA15/MA20', DoubleMAStrategy(15, 20)),
        ('MA5/MA30', DoubleMAStrategy(5, 30)),
        ('MA10/MA30', DoubleMAStrategy(10, 30)),
        ('MA15/MA30', DoubleMAStrategy(15, 30)),
        ('RSI(14,30,70)', RSIStrategy(14, 30, 70)),
        ('RSI(14,25,75)', RSIStrategy(14, 25, 75)),
        ('RSI(9,30,70)', RSIStrategy(9, 30, 70)),
        ('MACD经典', MACDStrategy(12, 26, 9)),
        ('MACD快速', MACDStrategy(6, 13, 5)),
        ('BOLL(20,2)', BollingerStrategy(20, 2.0)),
        ('BOLL(20,2.5)', BollingerStrategy(20, 2.5)),
        ('KDJ(9,3,3)', KDJStrategy(9, 3, 3)),
        ('量价突破', VolumeBreakoutStrategy(20, 2.0)),
    ]
    
    engine = BacktestEngine(trailing_stop=trailing_stop)
    
    for name, strategy in strategies:
        result = engine.run(strategy, data)
        if result:
            results.append({
                'strategy': name,
                **result
            })
    
    return results


def backtest_single_stock(symbol: str, args) -> Dict:
    """回测单只股票的所有策略"""
    data = load_stock_data(symbol)
    if data is None or len(data) < 100:
        return None
    
    # 测试所有策略
    results = test_all_strategies(data, trailing_stop=args.trailing_stop)
    
    if not results:
        return None
    
    # 按综合评分排序
    for r in results:
        r['score'] = (r['win_rate'] * 0.3 + 
                     min(max(r['annual_return'], -1), 1) * 0.5 - 
                     r['max_drawdown'] * 0.2)
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        'symbol': symbol,
        'best_strategy': results[0] if results else None,
        'all_results': results,
        'data_range': f"{data['date'].min().strftime('%Y-%m-%d')} ~ {data['date'].max().strftime('%Y-%m-%d')}",
        'data_count': len(data)
    }


def backtest_all_stocks(args):
    """全市场回测"""
    print('='*70)
    print('全市场策略优化回测')
    print('='*70)
    print()
    
    # 获取股票列表
    stock_files = [f.stem for f in CACHE_DIR.glob('*.json') if f.is_file()]
    
    # 去重（同一股票可能有多种格式）
    stock_codes = list(set(stock_files))
    
    if args.sample and len(stock_codes) > args.sample:
        import random
        random.seed(42)  # 固定种子，可复现
        stock_codes = random.sample(stock_codes, args.sample)
        print(f'📊 抽样回测：{args.sample} 只股票')
    else:
        print(f'📊 全量回测：{len(stock_codes)} 只股票')
    
    print(f'📊 移动止盈：{args.trailing_stop*100:.0f}%')
    print(f'📊 初始资金：¥{args.capital:,.0f}')
    print()
    
    # 收集所有策略结果
    strategy_stats = {}
    all_results = []
    
    start_time = time.time()
    
    for i, symbol in enumerate(stock_codes):
        try:
            result = backtest_single_stock(symbol, args)
            if result and result['best_strategy']:
                all_results.append({
                    'symbol': symbol,
                    'best_strategy': result['best_strategy']['strategy'],
                    'win_rate': result['best_strategy']['win_rate'],
                    'annual_return': result['best_strategy']['annual_return'],
                    'max_drawdown': result['best_strategy']['max_drawdown'],
                    'total_trades': result['best_strategy']['total_trades'],
                    'sharpe_ratio': result['best_strategy']['sharpe_ratio'],
                    'score': result['best_strategy']['score']
                })
                
                # 统计每个策略
                for r in result['all_results']:
                    name = r['strategy']
                    if name not in strategy_stats:
                        strategy_stats[name] = {
                            'count': 0,
                            'win_rates': [],
                            'annual_returns': [],
                            'max_drawdowns': [],
                            'total_trades': [],
                            'sharpe_ratios': []
                        }
                    strategy_stats[name]['count'] += 1
                    strategy_stats[name]['win_rates'].append(r['win_rate'])
                    strategy_stats[name]['annual_returns'].append(r['annual_return'])
                    strategy_stats[name]['max_drawdowns'].append(r['max_drawdown'])
                    strategy_stats[name]['total_trades'].append(r['total_trades'])
                    strategy_stats[name]['sharpe_ratios'].append(r['sharpe_ratio'])
            
            # 进度
            if (i + 1) % 200 == 0:
                elapsed = time.time() - start_time
                speed = (i + 1) / elapsed
                remaining = (len(stock_codes) - i - 1) / speed if speed > 0 else 0
                print(f"⏳ 进度：{i+1}/{len(stock_codes)} ({(i+1)/len(stock_codes)*100:.1f}%) "
                      f"速度：{speed:.1f}只/秒 剩余：{remaining:.0f}秒")
        
        except Exception as e:
            pass
    
    elapsed = time.time() - start_time
    
    # 汇总结果
    print("\n" + "="*70)
    print("📊 策略排名（按平均综合评分）")
    print("="*70)
    
    strategy_summary = []
    for name, stats in strategy_stats.items():
        if stats['count'] < 10:  # 过滤样本太少的
            continue
        
        avg_win_rate = statistics.mean(stats['win_rates'])
        avg_return = statistics.mean(stats['annual_returns'])
        avg_drawdown = statistics.mean(stats['max_drawdowns'])
        avg_trades = statistics.mean(stats['total_trades'])
        avg_sharpe = statistics.mean([s for s in stats['sharpe_ratios'] if not np.isnan(s)])
        
        # 综合评分
        composite_score = (avg_win_rate * 0.3 + 
                          min(max(avg_return, -1), 1) * 0.5 - 
                          avg_drawdown * 0.2)
        
        strategy_summary.append({
            'strategy': name,
            'count': stats['count'],
            'avg_win_rate': avg_win_rate,
            'avg_return': avg_return,
            'avg_drawdown': avg_drawdown,
            'avg_trades': avg_trades,
            'avg_sharpe': avg_sharpe,
            'composite_score': composite_score
        })
    
    # 排序
    strategy_summary.sort(key=lambda x: x['composite_score'], reverse=True)
    
    # 打印结果
    print("\n| 排名 | 策略名称 | 覆盖股票 | 平均胜率 | 平均年化 | 平均回撤 | 综合评分 |")
    print("|------|---------|---------|---------|---------|---------|---------|")
    
    for i, s in enumerate(strategy_summary[:20], 1):
        print(f"| {i:2d} | {s['strategy']:12s} | {s['count']:6d} | {s['avg_win_rate']*100:6.2f}% | "
              f"{s['avg_return']*100:+7.2f}% | {s['avg_drawdown']*100:6.2f}% | {s['composite_score']:+7.3f} |")
    
    # 保存结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 保存策略汇总
    summary_df = pd.DataFrame(strategy_summary)
    summary_file = RESULTS_DIR / f'strategy_summary_{timestamp}.csv'
    summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 策略汇总已保存至：{summary_file}")
    
    # 保存详细结果
    details_df = pd.DataFrame(all_results)
    details_file = RESULTS_DIR / f'stock_details_{timestamp}.csv'
    details_df.to_csv(details_file, index=False, encoding='utf-8-sig')
    print(f"💾 股票详情已保存至：{details_file}")
    
    # 找出最佳策略组合
    print("\n" + "="*70)
    print("🏆 最佳策略推荐")
    print("="*70)
    
    if strategy_summary:
        best = strategy_summary[0]
        print(f"""
📈 策略名称：{best['strategy']}
📊 覆盖股票：{best['count']} 只
✅ 平均胜率：{best['avg_win_rate']*100:.2f}%
💰 平均年化：{best['avg_return']*100:+.2f}%
⚠️  平均回撤：{best['avg_drawdown']*100:.2f}%
📈 平均交易：{best['avg_trades']:.1f} 次
🎯 综合评分：{best['composite_score']:+.3f}

⏱️ 回测耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)
""")
    
    return strategy_summary


def main():
    parser = argparse.ArgumentParser(description='全市场策略优化回测系统')
    parser.add_argument('--sample', type=int, default=None, help='抽样数量')
    parser.add_argument('--all', action='store_true', help='全市场回测')
    parser.add_argument('--symbol', type=str, default=None, help='单只股票回测')
    parser.add_argument('--capital', type=float, default=DEFAULT_INITIAL_CAPITAL, help='初始资金')
    parser.add_argument('--trailing-stop', type=float, default=0.10, help='移动止盈比例')
    
    args = parser.parse_args()
    
    # 检查数据
    if not CACHE_DIR.exists():
        print(f"❌ 缓存目录不存在：{CACHE_DIR}")
        return
    
    stock_count = len(list(CACHE_DIR.glob('*.json')))
    if stock_count == 0:
        print("❌ 缓存目录中没有数据文件")
        return
    
    print(f"✅ 缓存数据目录：{CACHE_DIR}")
    print(f"✅ 缓存股票数量：{stock_count} 个文件")
    
    if args.symbol:
        # 单只股票回测
        result = backtest_single_stock(args.symbol, args)
        if result:
            print(f"\n{'='*70}")
            print(f"📊 {args.symbol} 策略回测结果")
            print(f"{'='*70}")
            print(f"数据范围：{result['data_range']}")
            print(f"数据条数：{result['data_count']}")
            print("\n| 排名 | 策略 | 胜率 | 年化收益 | 最大回撤 | 交易次数 | 夏普比率 |")
            print("|------|------|------|---------|---------|---------|---------|")
            for i, r in enumerate(result['all_results'][:10], 1):
                print(f"| {i:2d} | {r['strategy']:12s} | {r['win_rate']*100:5.1f}% | "
                      f"{r['annual_return']*100:+6.2f}% | {r['max_drawdown']*100:5.2f}% | "
                      f"{r['total_trades']:5d} | {r['sharpe_ratio']:+6.2f} |")
    elif args.all or args.sample:
        # 全市场回测
        backtest_all_stocks(args)
    else:
        print("❌ 请指定回测模式：")
        print("  --symbol 000001  # 单只股票回测")
        print("  --sample 500      # 抽样回测")
        print("  --all             # 全市场回测")


if __name__ == '__main__':
    main()