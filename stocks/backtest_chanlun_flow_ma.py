#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缠论分型 + 资金流 + 均线 组合策略回测
基于 Tushare 缓存数据，回测全市场近一年行情

策略逻辑：
1. 缠论底分型形成（提前发现转折）
2. 主力资金净流入（确认资金进场）
3. MA15/20 金叉确认（趋势确认）
4. 蜡烛图形态辅助（增强信号）

卖出逻辑：
1. 缠论顶分型形成
2. 移动止盈 15%（基于回测最优）
3. 固定止损 -15%
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import warnings

warnings.filterwarnings('ignore')

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')

# ============== 策略参数 ==============
STRATEGY_CONFIG = {
    'ma_short': 15,
    'ma_long': 20,
    'fractal_window': 5,  # 分型窗口
    'volume_threshold': 1.5,  # 成交量放大倍数
    'trailing_stop': 0.15,  # 移动止盈 15%
    'fixed_stop_loss': 0.15,  # 固定止损 15%
    'fee_rate': 0.0003,  # 手续费万 3
}

# ============== 技术分析函数 ==============

def detect_fractal(data: pd.DataFrame, window: int = 5) -> Tuple[List[int], List[int]]:
    """检测缠论分型"""
    top_fractals = []
    bottom_fractals = []
    
    for i in range(window, len(data) - window):
        # 获取窗口内的最高价和最低价
        highs = data['high'].iloc[i-window:i+window+1].values
        lows = data['low'].iloc[i-window:i+window+1].values
        
        current_high = data['high'].iloc[i]
        current_low = data['low'].iloc[i]
        
        # 顶分型：中间最高，左右各 window 根 K 线都比它低
        left_highs = highs[:window]
        right_highs = highs[window+1:]
        
        if len(left_highs) > 0 and len(right_highs) > 0:
            if current_high > left_highs.max() and current_high >= right_highs.max():
                top_fractals.append(i)
        
        # 底分型：中间最低，左右各 window 根 K 线都比它高
        left_lows = lows[:window]
        right_lows = lows[window+1:]
        
        if len(left_lows) > 0 and len(right_lows) > 0:
            if current_low < left_lows.min() and current_low <= right_lows.min():
                bottom_fractals.append(i)
    
    return top_fractals, bottom_fractals


def detect_candlestick_pattern(data: pd.DataFrame, idx: int) -> Optional[Tuple[str, str, float]]:
    """检测蜡烛图形态"""
    if idx >= len(data):
        return None
    
    o = data['open'].iloc[idx]
    h = data['high'].iloc[idx]
    l = data['low'].iloc[idx]
    c = data['close'].iloc[idx]
    
    body = abs(c - o)
    total_range = h - l
    upper = h - max(o, c)
    lower = min(o, c) - l
    
    if total_range < 0.001:
        return None
    
    # 锤头线（看涨）
    if lower > body * 2 and upper < body * 0.5 and lower > total_range * 0.3:
        return ('锤头线', 'bull', 0.8)
    
    # 射击之星（看跌）
    if upper > body * 2 and lower < body * 0.5 and upper > total_range * 0.3:
        return ('射击之星', 'bear', 0.8)
    
    # 大阳线（看涨）
    if body > total_range * 0.7 and c > o:
        return ('大阳线', 'bull', 0.7)
    
    # 大阴线（看跌）
    if body > total_range * 0.7 and c < o:
        return ('大阴线', 'bear', 0.7)
    
    # 十字星（变盘信号）
    if body < total_range * 0.1:
        return ('十字星', 'neutral', 0.5)
    
    return None


def calc_ma(series: pd.Series, period: int) -> pd.Series:
    """计算移动平均线"""
    return series.rolling(window=period).mean()


def simulate_capital_flow(data: pd.DataFrame) -> pd.Series:
    """
    模拟资金流（因为没有真实资金流数据）
    基于价量关系估算：放量上涨=主力流入，放量下跌=主力流出
    """
    # 计算涨跌幅
    pct_change = data['close'].pct_change()
    
    # 计算成交量相对均量的倍数
    volume_ma20 = data['volume'].rolling(20).mean()
    volume_ratio = data['volume'] / volume_ma20
    
    # 估算资金流：涨跌幅 * 成交量比
    # 放量上涨为正，放量下跌为负
    capital_flow = pct_change * volume_ratio * 100
    
    # 计算累计资金流（5 日）
    capital_flow_5d = capital_flow.rolling(5).sum()
    
    return capital_flow_5d


# ============== 策略信号 ==============

def generate_signal(data: pd.DataFrame, idx: int) -> Tuple[str, int, Dict]:
    """
    生成交易信号
    
    Returns:
        (signal_type, signal_strength, info_dict)
    """
    if idx < 50:  # 需要足够历史数据
        return ('hold', 0, {})
    
    # 计算均线
    ma15 = calc_ma(data['close'], 15).iloc[idx]
    ma20 = calc_ma(data['close'], 20).iloc[idx]
    ma15_prev = calc_ma(data['close'], 15).iloc[idx-1]
    ma20_prev = calc_ma(data['close'], 20).iloc[idx-1]
    
    # 检测分型（使用最近 20 天数据）
    recent_data = data.iloc[max(0, idx-30):idx+1].reset_index(drop=True)
    top_fractals, bottom_fractals = detect_fractal(recent_data, STRATEGY_CONFIG['fractal_window'])
    
    # 调整分型索引到原数据
    offset = max(0, idx-30)
    bottom_fractals = [b + offset for b in bottom_fractals]
    top_fractals = [t + offset for t in top_fractals]
    
    # 检测蜡烛图
    candle_pattern = detect_candlestick_pattern(data, idx)
    
    # 模拟资金流
    capital_flow = simulate_capital_flow(data)
    flow_5d = capital_flow.iloc[idx]
    
    # 成交量比
    volume_ma20 = data['volume'].rolling(20).mean()
    volume_ratio = data['volume'].iloc[idx] / volume_ma20.iloc[idx] if volume_ma20.iloc[idx] > 0 else 0
    
    info = {
        'ma15': ma15,
        'ma20': ma20,
        'ma_diff_pct': (ma15 - ma20) / ma20 * 100 if pd.notna(ma20) and ma20 > 0 else 0,
        'bottom_fractal': idx in bottom_fractals,
        'top_fractal': idx in top_fractals,
        'candle_pattern': candle_pattern,
        'capital_flow_5d': flow_5d,
        'volume_ratio': volume_ratio,
    }
    
    # 买入信号评分
    buy_score = 0
    
    # 1. 缠论底分型（3 分）
    if idx in bottom_fractals:
        buy_score += 3
    
    # 2. 资金流为正（2 分）
    if pd.notna(flow_5d) and flow_5d > 0:
        buy_score += 2
    
    # 3. 均线金叉（3 分）
    if pd.notna(ma15) and pd.notna(ma20) and ma15 > ma20:
        buy_score += 3
        # 刚金叉额外加 1 分
        if ma15_prev <= ma20_prev:
            buy_score += 1
    
    # 4. 成交量放大（1 分）
    if volume_ratio > STRATEGY_CONFIG['volume_threshold']:
        buy_score += 1
    
    # 5. 看涨蜡烛图（1 分）
    if candle_pattern and candle_pattern[1] == 'bull':
        buy_score += 1
    
    # 卖出信号评分
    sell_score = 0
    
    # 1. 缠论顶分型（3 分）
    if idx in top_fractals:
        sell_score += 3
    
    # 2. 资金流转负（2 分）
    if pd.notna(flow_5d) and flow_5d < 0:
        sell_score += 2
    
    # 3. 均线死叉（3 分）
    if pd.notna(ma15) and pd.notna(ma20) and ma15 < ma20:
        sell_score += 3
    
    # 4. 看跌蜡烛图（1 分）
    if candle_pattern and candle_pattern[1] == 'bear':
        sell_score += 1
    
    # 生成信号
    if buy_score >= 6:  # 买入阈值
        return ('buy', buy_score, info)
    elif sell_score >= 5:  # 卖出阈值
        return ('sell', sell_score, info)
    else:
        return ('hold', 0, info)


# ============== 回测引擎 ==============

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = None  # {'shares': x, 'cost': y, 'code': z}
        self.trades = []
        self.equity_curve = []
        self.highest_price = 0  # 用于移动止盈
    
    def execute_buy(self, data: pd.DataFrame, idx: int, signal_strength: int, info: Dict):
        """执行买入"""
        if self.position:
            return False
        
        price = data['close'].iloc[idx]
        date = data['date'].iloc[idx]
        
        # 计算可买股数（95% 仓位）
        available_capital = self.capital * 0.95
        shares = int(available_capital / price / 100) * 100
        
        if shares <= 0:
            return False
        
        amount = shares * price
        fee = amount * STRATEGY_CONFIG['fee_rate']
        
        self.capital -= (amount + fee)
        self.position = {
            'shares': shares,
            'cost': price,
            'code': data.get('ts_code', ['UNKNOWN'])[0] if isinstance(data.get('ts_code'), list) else 'UNKNOWN',
            'buy_date': date,
            'buy_idx': idx
        }
        self.highest_price = price
        
        self.trades.append({
            'type': 'buy',
            'date': date,
            'price': price,
            'shares': shares,
            'amount': amount,
            'fee': fee,
            'signal_strength': signal_strength,
            'info': info
        })
        
        return True
    
    def execute_sell(self, data: pd.DataFrame, idx: int, reason: str, signal_strength: int = 0):
        """执行卖出"""
        if not self.position:
            return False
        
        price = data['close'].iloc[idx]
        date = data['date'].iloc[idx]
        shares = self.position['shares']
        cost = self.position['cost']
        
        amount = shares * price
        fee = amount * STRATEGY_CONFIG['fee_rate']
        
        profit = (price - cost) / cost * 100
        profit_amount = amount - (shares * cost) - fee
        
        self.capital += (amount - fee)
        
        self.trades.append({
            'type': 'sell',
            'date': date,
            'price': price,
            'shares': shares,
            'amount': amount,
            'fee': fee,
            'profit_pct': profit,
            'profit_amount': profit_amount,
            'reason': reason,
            'signal_strength': signal_strength,
            'cost': cost,
            'hold_days': (date - self.position['buy_date']).days
        })
        
        self.position = None
        self.highest_price = 0
        
        return True
    
    def check_stop_conditions(self, data: pd.DataFrame, idx: int) -> Optional[str]:
        """检查止损止盈条件"""
        if not self.position:
            return None
        
        current_price = data['close'].iloc[idx]
        cost = self.position['cost']
        
        # 更新最高价
        if current_price > self.highest_price:
            self.highest_price = current_price
        
        # 1. 移动止盈
        if self.highest_price > cost * 1.05:  # 有过盈利才启用移动止盈
            trailing_stop_price = self.highest_price * (1 - STRATEGY_CONFIG['trailing_stop'])
            if current_price <= trailing_stop_price:
                return f'移动止盈 (最高{self.highest_price:.2f}, 回撤{STRATEGY_CONFIG["trailing_stop"]*100}%)'
        
        # 2. 固定止损
        if current_price <= cost * (1 - STRATEGY_CONFIG['fixed_stop_loss']):
            return f'固定止损 (-{STRATEGY_CONFIG["fixed_stop_loss"]*100}%)'
        
        return None
    
    def run(self, data: pd.DataFrame) -> Dict:
        """运行回测"""
        print(f"  开始回测... 数据长度：{len(data)}")
        
        for idx in range(len(data)):
            date = data['date'].iloc[idx]
            current_price = data['close'].iloc[idx]
            
            # 检查止损止盈
            stop_reason = self.check_stop_conditions(data, idx)
            if stop_reason:
                self.execute_sell(data, idx, stop_reason)
            
            # 生成信号
            signal, strength, info = generate_signal(data, idx)
            
            # 执行交易
            if signal == 'buy':
                self.execute_buy(data, idx, strength, info)
            elif signal == 'sell' and self.position:
                self.execute_sell(data, idx, f'卖出信号 (强度{strength})', strength)
            
            # 记录权益
            if self.position:
                equity = self.capital + self.position['shares'] * current_price
            else:
                equity = self.capital
            
            self.equity_curve.append({
                'date': date,
                'equity': equity,
                'price': current_price
            })
        
        # 清空持仓
        if self.position:
            last_idx = len(data) - 1
            self.execute_sell(data, last_idx, '回测结束')
        
        # 计算统计
        return self.calculate_stats()
    
    def calculate_stats(self) -> Dict:
        """计算回测统计"""
        if not self.trades:
            return {'error': '无交易记录'}
        
        # 分离买卖记录
        buys = [t for t in self.trades if t['type'] == 'buy']
        sells = [t for t in self.trades if t['type'] == 'sell']
        
        # 计算收益
        total_profit = sum(t.get('profit_amount', 0) for t in sells)
        total_profit_pct = (self.capital - self.initial_capital) / self.initial_capital * 100
        
        # 胜率
        profitable_trades = [t for t in sells if t.get('profit_pct', 0) > 0]
        win_rate = len(profitable_trades) / len(sells) * 100 if sells else 0
        
        # 平均盈亏
        avg_profit = np.mean([t.get('profit_pct', 0) for t in sells]) if sells else 0
        avg_win = np.mean([t.get('profit_pct', 0) for t in profitable_trades]) if profitable_trades else 0
        avg_loss = np.mean([t.get('profit_pct', 0) for t in sells if t.get('profit_pct', 0) <= 0]) if len(sells) > len(profitable_trades) else 0
        
        # 最大回撤
        equity_series = [e['equity'] for e in self.equity_curve]
        peak = equity_series[0]
        max_drawdown = 0
        for equity in equity_series:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 交易频率
        total_days = (self.equity_curve[-1]['date'] - self.equity_curve[0]['date']).days if self.equity_curve else 0
        trades_per_year = len(sells) / (total_days / 365) if total_days > 0 else 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_profit_pct': total_profit_pct,
            'total_trades': len(sells),
            'win_rate': win_rate,
            'avg_profit_pct': avg_profit,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'max_drawdown': max_drawdown,
            'trades_per_year': trades_per_year,
            'profitable_trades': len(profitable_trades),
            'losing_trades': len(sells) - len(profitable_trades)
        }


# ============== 主函数 ==============

def backtest_single_stock(symbol: str) -> Optional[Dict]:
    """回测单只股票"""
    filepath = CACHE_DIR / f'{symbol}.json'
    
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data or len(data) < 100:
            return None
        
        df = pd.DataFrame(data)
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount'
        })
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        
        # 运行回测
        engine = BacktestEngine(initial_capital=100000)
        stats = engine.run(df)
        
        if 'error' in stats:
            return None
        
        stats['symbol'] = symbol
        stats['data_days'] = len(df)
        
        return stats
    
    except Exception as e:
        return None


def backtest_market():
    """回测全市场"""
    print("=" * 80)
    print("🔬 缠论分型 + 资金流 + 均线 组合策略回测")
    print(f"📅 回测时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"📊 数据源：Tushare 缓存")
    print("=" * 80)
    
    print(f"\n📋 策略参数:")
    for key, value in STRATEGY_CONFIG.items():
        print(f"   {key}: {value}")
    
    stock_files = list(CACHE_DIR.glob('*.json'))
    total = len(stock_files)
    
    print(f"\n🔍 开始回测 {total} 只股票...\n")
    
    results = []
    
    for i, filepath in enumerate(stock_files):
        symbol = filepath.stem
        
        # 进度显示
        if (i + 1) % 500 == 0:
            print(f"  进度：{i+1}/{total} ({(i+1)/total*100:.1f}%)")
        
        stats = backtest_single_stock(symbol)
        if stats:
            results.append(stats)
    
    print(f"\n✅ 回测完成，有效结果：{len(results)}只股票\n")
    
    # 统计分析
    if results:
        analyze_results(results)
    
    return results


def analyze_results(results: List[Dict]):
    """分析回测结果"""
    print("=" * 80)
    print("📊 回测结果统计")
    print("=" * 80)
    
    # 平均收益
    avg_profit = np.mean([r['total_profit_pct'] for r in results])
    median_profit = np.median([r['total_profit_pct'] for r in results])
    
    # 胜率统计
    avg_win_rate = np.mean([r['win_rate'] for r in results])
    
    # 盈利股票比例
    profitable_stocks = [r for r in results if r['total_profit_pct'] > 0]
    profitable_ratio = len(profitable_stocks) / len(results) * 100
    
    # 收益分布
    top_10 = sorted(results, key=lambda x: x['total_profit_pct'], reverse=True)[:10]
    bottom_10 = sorted(results, key=lambda x: x['total_profit_pct'])[:10]
    
    print(f"\n📈 整体表现:")
    print(f"   回测股票数：{len(results)}")
    print(f"   平均收益：{avg_profit:.2f}%")
    print(f"   中位收益：{median_profit:.2f}%")
    print(f"   平均胜率：{avg_win_rate:.1f}%")
    print(f"   盈利股票：{len(profitable_stocks)}/{len(results)} ({profitable_ratio:.1f}%)")
    
    # 最大回撤统计
    avg_max_dd = np.mean([r['max_drawdown'] for r in results])
    print(f"   平均最大回撤：{avg_max_dd:.2f}%")
    
    # 交易频率
    avg_trades = np.mean([r['total_trades'] for r in results])
    print(f"   平均交易次数：{avg_trades:.1f}次/年")
    
    print(f"\n🏆 TOP 10 最佳股票:")
    for i, r in enumerate(top_10, 1):
        print(f"   {i}. {r['symbol']}: {r['total_profit_pct']:+.2f}% (胜率{r['win_rate']:.1f}%, 交易{r['total_trades']}次)")
    
    print(f"\n🔴 TOP 10 最差股票:")
    for i, r in enumerate(bottom_10, 1):
        print(f"   {i}. {r['symbol']}: {r['total_profit_pct']:+.2f}% (胜率{r['win_rate']:.1f}%, 交易{r['total_trades']}次)")
    
    # 收益分布
    print(f"\n📊 收益分布:")
    ranges = [
        ('>50%', [r for r in results if r['total_profit_pct'] > 50]),
        ('20-50%', [r for r in results if 20 < r['total_profit_pct'] <= 50]),
        ('0-20%', [r for r in results if 0 < r['total_profit_pct'] <= 20]),
        ('-20-0%', [r for r in results if -20 < r['total_profit_pct'] <= 0]),
        ('<-20%', [r for r in results if r['total_profit_pct'] <= -20]),
    ]
    
    for range_name, stocks in ranges:
        ratio = len(stocks) / len(results) * 100
        print(f"   {range_name}: {len(stocks)}只 ({ratio:.1f}%)")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    results = backtest_market()
