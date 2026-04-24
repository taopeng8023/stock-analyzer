#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终极策略优化回测系统
针对A股2022-2024熊市环境，测试多种防守型策略组合

核心优化方向：
1. 趋势过滤 - 只在上升趋势中买入
2. 多种止盈止损参数组合
3. 仓位管理 - 不是满仓而是分批建仓
4. 信号过滤 - 减少假信号
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

warnings.filterwarnings('ignore')

CACHE_DIR = Path(__file__).parent / 'data_tushare'
RESULTS_DIR = Path(__file__).parent / 'backtest_results'
RESULTS_DIR.mkdir(exist_ok=True)


def load_stock_data(symbol: str) -> Optional[pd.DataFrame]:
    """加载股票数据"""
    filepath = CACHE_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and 'fields' in data and 'items' in data:
            df = pd.DataFrame(data['items'], columns=data['fields'])
            df = df.rename(columns={'trade_date': 'date', 'vol': 'volume'})
        else:
            return None
        
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    except:
        return None


# ============== 技术指标 ==============

def calc_ma(data, period):
    return data['close'].rolling(window=period).mean()

def calc_ema(data, period):
    return data['close'].ewm(span=period, adjust=False).mean()

def calc_rsi(data, period=14):
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_macd(data, fast=12, slow=26, signal=9):
    ema_f = calc_ema(data, fast)
    ema_s = calc_ema(data, slow)
    dif = ema_f - ema_s
    dea = dif.ewm(span=signal, adjust=False).mean()
    return dif, dea, (dif - dea) * 2

def calc_kdj(data, n=9):
    lowv = data['low'].rolling(n).min()
    highv = data['high'].rolling(n).max()
    rsv = (data['close'] - lowv) / (highv - lowv) * 100
    k = rsv.ewm(alpha=1/3, adjust=False).mean()
    d = k.ewm(alpha=1/3, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j

def calc_boll(data, period=20, std_dev=2):
    mid = calc_ma(data, period)
    std = data['close'].rolling(period).std()
    return mid + std_dev * std, mid, mid - std_dev * std

def calc_slope(data, period=5):
    """计算均线斜率"""
    ma = calc_ma(data, period)
    return (ma - ma.shift(period)) / ma.shift(period) * 100


# ============== 策略定义 ==============

class UltimateStrategy:
    """终极策略 - 多条件组合"""
    
    def __init__(self, params: Dict):
        self.params = params
        self.name = self._generate_name()
    
    def _generate_name(self):
        parts = []
        if self.params.get('use_ma_cross'):
            parts.append(f"MA{self.params['fast_ma']}/{self.params['slow_ma']}")
        if self.params.get('use_rsi'):
            parts.append(f"RSI{self.params['rsi_buy']}-{self.params['rsi_sell']}")
        if self.params.get('use_trend_filter'):
            parts.append(f"TrendMA{self.params['trend_ma']}")
        if self.params.get('use_macd_filter'):
            parts.append("MACD+")
        if self.params.get('use_volume_filter'):
            parts.append(f"Vol>{self.params['vol_mult']}x")
        parts.append(f"SL{int(self.params['stop_loss']*100)}%")
        parts.append(f"TP{int(self.params['take_profit']*100)}%")
        parts.append(f"Trail{int(self.params['trailing_stop']*100)}%")
        return ' | '.join(parts) if parts else 'Basic'
    
    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """生成交易信号"""
        signals = []
        
        # 计算指标
        ma_fast = calc_ma(data, self.params['fast_ma'])
        ma_slow = calc_ma(data, self.params['slow_ma'])
        rsi = calc_rsi(data, self.params.get('rsi_period', 14))
        macd_dif, macd_dea, macd_hist = calc_macd(data)
        k, d, j = calc_kdj(data)
        volume_ma = data['volume'].rolling(20).mean()
        
        # 趋势均线
        if self.params.get('use_trend_filter'):
            trend_ma = calc_ma(data, self.params['trend_ma'])
        else:
            trend_ma = None
        
        # 斜率
        slope_fast = calc_slope(data, self.params['fast_ma'])
        slope_slow = calc_slope(data, self.params['slow_ma'])
        
        for i in range(max(self.params['slow_ma'], 60), len(data)):
            date = data['date'].iloc[i]
            close = float(data['close'].iloc[i])
            
            # ===== 买入条件 =====
            buy_score = 0
            
            # 1. 基础条件：金叉
            if self.params.get('use_ma_cross'):
                if ma_fast.iloc[i] > ma_slow.iloc[i] and ma_fast.iloc[i-1] <= ma_slow.iloc[i-1]:
                    buy_score += 3
            
            # 2. 趋势过滤：股价在长期均线之上
            if self.params.get('use_trend_filter') and trend_ma is not None:
                if close > trend_ma.iloc[i]:
                    buy_score += 2
            
            # 3. MACD辅助：DIF>0或DIF向上
            if self.params.get('use_macd_filter'):
                if macd_dif.iloc[i] > 0 or (macd_dif.iloc[i] > macd_dif.iloc[i-3]):
                    buy_score += 1
            
            # 4. RSI不在超买区
            if self.params.get('use_rsi'):
                rsi_val = rsi.iloc[i]
                if rsi_val < self.params['rsi_buy']:
                    buy_score += 1
            
            # 5. 量价配合：成交量放大
            if self.params.get('use_volume_filter'):
                vol_ratio = data['volume'].iloc[i] / volume_ma.iloc[i]
                if vol_ratio > self.params['vol_mult']:
                    buy_score += 1
            
            # 6. 均线向上（斜率正）
            if slope_fast.iloc[i] > 0 and slope_slow.iloc[i] > 0:
                buy_score += 1
            
            # 满足买入条件
            min_buy_score = self.params.get('min_buy_score', 3)
            if buy_score >= min_buy_score:
                signals.append({
                    'date': date,
                    'type': 'buy',
                    'price': close,
                    'score': buy_score,
                    'rsi': rsi.iloc[i] if rsi.iloc[i] else None,
                    'volume_ratio': data['volume'].iloc[i] / volume_ma.iloc[i]
                })
            
            # ===== 卖出条件 =====
            # 死叉信号
            if self.params.get('use_ma_cross'):
                if ma_fast.iloc[i] < ma_slow.iloc[i] and ma_fast.iloc[i-1] >= ma_slow.iloc[i-1]:
                    signals.append({
                        'date': date,
                        'type': 'sell',
                        'price': close,
                        'reason': 'death_cross'
                    })
            
            # RSI超买卖出
            if self.params.get('use_rsi'):
                if rsi.iloc[i] > self.params['rsi_sell'] and rsi.iloc[i-1] <= self.params['rsi_sell']:
                    signals.append({
                        'date': date,
                        'type': 'sell',
                        'price': close,
                        'reason': 'rsi_overbought'
                    })
        
        return signals


class BacktestEngine:
    """增强回测引擎"""
    
    def __init__(self, initial_capital=100000, fee_rate=0.0003, slippage=0.001):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage
    
    def run(self, strategy: UltimateStrategy, data: pd.DataFrame) -> Dict:
        """执行回测"""
        if len(data) < 100:
            return None
        
        signals = strategy.generate_signals(data)
        
        if not signals:
            return None
        
        # 参数
        stop_loss = strategy.params.get('stop_loss', 0.08)
        take_profit = strategy.params.get('take_profit', 0.15)
        trailing_stop = strategy.params.get('trailing_stop', 0.05)
        position_pct = strategy.params.get('position_pct', 0.95)  # 仓位比例
        
        # 状态
        capital = self.initial_capital
        position = 0
        cost_price = 0
        highest_price = 0
        trades = []
        equity_curve = []
        
        # 按日期遍历
        signal_idx = 0
        for i in range(len(data)):
            date = data['date'].iloc[i]
            close = float(data['close'].iloc[i])
            
            # 更新最高价
            if position > 0:
                highest_price = max(highest_price, close)
            
            # 止损检查
            if position > 0 and stop_loss > 0:
                loss_pct = (close - cost_price) / cost_price
                if loss_pct <= -stop_loss:
                    self._sell(date, close, position, 'stop_loss', trades, capital)
                    capital = trades[-1]['capital']
                    position = 0
                    cost_price = 0
                    highest_price = 0
                    continue
            
            # 止盈检查
            if position > 0 and take_profit > 0:
                profit_pct = (close - cost_price) / cost_price
                if profit_pct >= take_profit:
                    self._sell(date, close, position, 'take_profit', trades, capital)
                    capital = trades[-1]['capital']
                    position = 0
                    cost_price = 0
                    continue
            
            # 移动止盈检查
            if position > 0 and trailing_stop > 0:
                drawdown = (highest_price - close) / highest_price
                if drawdown >= trailing_stop:
                    self._sell(date, close, position, 'trailing_stop', trades, capital)
                    capital = trades[-1]['capital']
                    position = 0
                    cost_price = 0
                    highest_price = 0
                    continue
            
            # 处理信号
            while signal_idx < len(signals) and signals[signal_idx]['date'] == date:
                sig = signals[signal_idx]
                
                if sig['type'] == 'buy' and position == 0:
                    # 买入
                    buy_price = close * (1 + self.slippage)
                    buy_capital = capital * position_pct
                    shares = int(buy_capital / buy_price / 100) * 100
                    
                    if shares >= 100:
                        amount = shares * buy_price
                        fee = amount * self.fee_rate
                        
                        capital -= (amount + fee)
                        position = shares
                        cost_price = buy_price
                        highest_price = buy_price
                        
                        trades.append({
                            'date': date,
                            'type': 'buy',
                            'price': buy_price,
                            'shares': shares,
                            'amount': amount,
                            'fee': fee,
                            'score': sig.get('score', 0),
                            'reason': 'signal',
                            'capital': capital
                        })
                
                elif sig['type'] == 'sell' and position > 0:
                    self._sell(date, close, position, sig.get('reason', 'signal'), trades, capital)
                    capital = trades[-1]['capital']
                    position = 0
                    cost_price = 0
                    highest_price = 0
                
                signal_idx += 1
            
            # 记录权益
            total_value = capital + (position * close if position > 0 else 0)
            equity_curve.append({
                'date': date,
                'value': total_value,
                'return': (total_value - self.initial_capital) / self.initial_capital
            })
        
        # 强制平仓
        if position > 0:
            last_close = float(data['close'].iloc[-1])
            last_date = data['date'].iloc[-1]
            self._sell(last_date, last_close, position, 'force_close', trades, capital)
        
        return self._calculate_metrics(trades, equity_curve, data)
    
    def _sell(self, date, price, shares, reason, trades, capital):
        """卖出操作"""
        sell_price = price * (1 - self.slippage)
        amount = shares * sell_price
        fee = amount * self.fee_rate
        
        last_buy = [t for t in trades if t['type'] == 'buy'][-1] if trades else None
        profit = amount - (shares * last_buy['price']) - fee if last_buy else 0
        
        trades.append({
            'date': date,
            'type': 'sell',
            'price': sell_price,
            'shares': shares,
            'amount': amount,
            'fee': fee,
            'profit': profit,
            'profit_pct': profit / (shares * last_buy['price']) if last_buy and last_buy['price'] else 0,
            'reason': reason,
            'capital': capital + amount - fee
        })
    
    def _calculate_metrics(self, trades, equity_curve, data):
        """计算回测指标"""
        if not trades:
            return None
        
        sell_trades = [t for t in trades if t['type'] == 'sell']
        if not sell_trades:
            return None
        
        # 基本统计
        total_profit = sum(t['profit'] for t in sell_trades)
        win_trades = [t for t in sell_trades if t['profit'] > 0]
        loss_trades = [t for t in sell_trades if t['profit'] <= 0]
        
        win_rate = len(win_trades) / len(sell_trades) if sell_trades else 0
        gross_profit = sum(t['profit'] for t in win_trades)
        gross_loss = abs(sum(t['profit'] for t in loss_trades))
        profit_loss_ratio = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # 收益率
        final_value = equity_curve[-1]['value']
        total_return = (final_value - self.initial_capital) / self.initial_capital
        
        days = (equity_curve[-1]['date'] - equity_curve[0]['date']).days
        annual_return = (1 + total_return) ** (365 / max(days, 1)) - 1 if days > 0 else 0
        
        # 最大回撤
        peak = 0
        max_dd = 0
        for eq in equity_curve:
            peak = max(peak, eq['value'])
            dd = (peak - eq['value']) / peak
            max_dd = max(max_dd, dd)
        
        # 夏普
        returns = [eq['return'] for eq in equity_curve]
        if len(returns) > 1:
            daily_ret = np.diff(returns)
            sharpe = np.mean(daily_ret) / np.std(daily_ret) * np.sqrt(252) if np.std(daily_ret) > 0 else 0
        else:
            sharpe = 0
        
        return {
            'strategy': 'Ultimate',
            'total_return': total_return,
            'annual_return': annual_return,
            'total_trades': len(sell_trades),
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'max_drawdown': max_dd,
            'sharpe_ratio': sharpe,
            'total_profit': total_profit,
            'avg_profit_pct': statistics.mean([t['profit_pct'] for t in sell_trades]) if sell_trades else 0,
            'avg_hold_days': statistics.mean([
                (sell_trades[i]['date'] - [t for t in trades if t['type'] == 'buy'][i]['date']).days 
                for i in range(len(sell_trades))
            ]) if len([t for t in trades if t['type'] == 'buy']) == len(sell_trades) else 0
        }


def generate_strategy_params() -> List[Dict]:
    """生成策略参数组合"""
    params_list = []
    
    # 基础参数组合
    base_configs = [
        {'fast_ma': 5, 'slow_ma': 20},
        {'fast_ma': 10, 'slow_ma': 20},
        {'fast_ma': 15, 'slow_ma': 20},
        {'fast_ma': 5, 'slow_ma': 30},
        {'fast_ma': 10, 'slow_ma': 30},
    ]
    
    # 止盈止损组合
    stop_configs = [
        {'stop_loss': 0.05, 'take_profit': 0.10, 'trailing_stop': 0.05},
        {'stop_loss': 0.08, 'take_profit': 0.15, 'trailing_stop': 0.08},
        {'stop_loss': 0.10, 'take_profit': 0.20, 'trailing_stop': 0.10},
        {'stop_loss': 0.05, 'take_profit': 0.08, 'trailing_stop': 0.03},  # 防守型
        {'stop_loss': 0.08, 'take_profit': 0.12, 'trailing_stop': 0.05},  # 平衡型
    ]
    
    # 过滤条件组合
    filter_configs = [
        {'use_trend_filter': False, 'use_macd_filter': False, 'use_volume_filter': False, 'use_rsi': False, 'min_buy_score': 3},
        {'use_trend_filter': True, 'trend_ma': 60, 'use_macd_filter': False, 'use_volume_filter': False, 'use_rsi': False, 'min_buy_score': 3},
        {'use_trend_filter': True, 'trend_ma': 60, 'use_macd_filter': True, 'use_volume_filter': False, 'use_rsi': False, 'min_buy_score': 4},
        {'use_trend_filter': True, 'trend_ma': 60, 'use_macd_filter': True, 'use_volume_filter': True, 'vol_mult': 1.5, 'use_rsi': False, 'min_buy_score': 5},
        {'use_trend_filter': True, 'trend_ma': 60, 'use_macd_filter': True, 'use_volume_filter': True, 'vol_mult': 1.5, 'use_rsi': True, 'rsi_period': 14, 'rsi_buy': 50, 'rsi_sell': 80, 'min_buy_score': 5},
        {'use_trend_filter': True, 'trend_ma': 200, 'use_macd_filter': False, 'use_volume_filter': False, 'use_rsi': False, 'min_buy_score': 3},
    ]
    
    # 组合生成
    for base in base_configs:
        for stop in stop_configs:
            for filter_cfg in filter_configs:
                params = {
                    **base,
                    **stop,
                    **filter_cfg,
                    'use_ma_cross': True,
                    'position_pct': 0.95
                }
                params_list.append(params)
    
    return params_list


def backtest_all_strategies(data: pd.DataFrame) -> List[Dict]:
    """测试所有参数组合"""
    params_list = generate_strategy_params()
    engine = BacktestEngine()
    results = []
    
    for params in params_list:
        strategy = UltimateStrategy(params)
        result = engine.run(strategy, data)
        
        if result:
            result['params'] = params
            result['strategy_name'] = strategy.name
            results.append(result)
    
    return results


def optimize_single_stock(symbol: str) -> Dict:
    """优化单只股票"""
    data = load_stock_data(symbol)
    if data is None or len(data) < 100:
        return None
    
    results = backtest_all_strategies(data)
    
    if not results:
        return None
    
    # 按综合评分排序
    for r in results:
        r['score'] = (r['win_rate'] * 0.35 + 
                     min(max(r['annual_return'], -1), 1) * 0.40 - 
                     r['max_drawdown'] * 0.15 +
                     min(r['profit_loss_ratio'], 3) * 0.10)
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        'symbol': symbol,
        'data_range': f"{data['date'].min().strftime('%Y-%m-%d')} ~ {data['date'].max().strftime('%Y-%m-%d')}",
        'best': results[0] if results else None,
        'all_results': results[:20]  # 保留前20个
    }


def full_market_backtest(sample: int = None):
    """全市场回测"""
    print('='*70)
    print('终极策略优化回测 - 全市场')
    print('='*70)
    
    stock_files = list(set([f.stem for f in CACHE_DIR.glob('*.json')]))
    
    if sample:
        import random
        random.seed(42)
        stock_files = random.sample(stock_files, min(sample, len(stock_files)))
        print(f'📊 抽样回测：{sample} 只股票')
    else:
        print(f'📊 全量回测：{len(stock_files)} 只股票')
    
    print()
    
    all_best = []
    strategy_stats = {}
    start_time = time.time()
    
    for i, symbol in enumerate(stock_files):
        try:
            result = optimize_single_stock(symbol)
            
            if result and result['best']:
                all_best.append({
                    'symbol': symbol,
                    'strategy': result['best']['strategy_name'],
                    'win_rate': result['best']['win_rate'],
                    'annual_return': result['best']['annual_return'],
                    'max_drawdown': result['best']['max_drawdown'],
                    'total_trades': result['best']['total_trades'],
                    'sharpe': result['best']['sharpe_ratio'],
                    'profit_loss_ratio': result['best']['profit_loss_ratio'],
                    'score': result['best']['score']
                })
                
                # 统计策略参数效果
                key = result['best']['strategy_name']
                if key not in strategy_stats:
                    strategy_stats[key] = []
                strategy_stats[key].append(result['best'])
            
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                speed = (i + 1) / elapsed
                print(f"⏳ {i+1}/{len(stock_files)} ({(i+1)/len(stock_files)*100:.1f}%) 速度:{speed:.1f}只/秒")
        
        except Exception as e:
            pass
    
    elapsed = time.time() - start_time
    
    # 汇总
    print("\n" + "="*70)
    print("📊 策略排名（按平均综合评分）")
    print("="*70)
    
    summary = []
    for name, stats in strategy_stats.items():
        if len(stats) < 5:
            continue
        
        avg_win = statistics.mean([s['win_rate'] for s in stats])
        avg_return = statistics.mean([s['annual_return'] for s in stats])
        avg_dd = statistics.mean([s['max_drawdown'] for s in stats])
        avg_trades = statistics.mean([s['total_trades'] for s in stats])
        avg_sharpe = statistics.mean([s['sharpe'] for s in stats])
        avg_pl_ratio = statistics.mean([s['profit_loss_ratio'] for s in stats])
        
        score = (avg_win * 0.35 + min(max(avg_return, -1), 1) * 0.40 - avg_dd * 0.15 + min(avg_pl_ratio, 3) * 0.10)
        
        summary.append({
            'strategy': name,
            'count': len(stats),
            'avg_win_rate': avg_win,
            'avg_return': avg_return,
            'avg_drawdown': avg_dd,
            'avg_trades': avg_trades,
            'avg_sharpe': avg_sharpe,
            'avg_pl_ratio': avg_pl_ratio,
            'score': score
        })
    
    summary.sort(key=lambda x: x['score'], reverse=True)
    
    # 打印
    print("\n| 排名 | 策略参数组合 | 覆盖股票 | 平均胜率 | 平均年化 | 平均回撤 | 综合评分 |")
    print("|------|-------------|---------|---------|---------|---------|---------|")
    
    for i, s in enumerate(summary[:30], 1):
        print(f"| {i:2d} | {s['strategy'][:35]} | {s['count']:5d} | {s['avg_win_rate']*100:5.1f}% | "
              f"{s['avg_return']*100:+5.1f}% | {s['avg_drawdown']*100:5.1f}% | {s['score']:+5.3f} |")
    
    # 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(RESULTS_DIR / f'ultimate_strategy_summary_{timestamp}.csv', 
                      index=False, encoding='utf-8-sig')
    
    best_df = pd.DataFrame(all_best)
    best_df.to_csv(RESULTS_DIR / f'ultimate_best_by_stock_{timestamp}.csv',
                   index=False, encoding='utf-8-sig')
    
    print(f"\n💾 结果已保存至 backtest_results/")
    
    # 推荐最佳
    print("\n" + "="*70)
    print("🏆 最佳策略推荐")
    print("="*70)
    
    if summary:
        best = summary[0]
        print(f"""
策略配置：{best['strategy']}
覆盖股票：{best['count']} 只
平均胜率：{best['avg_win_rate']*100:.1f}%
平均年化：{best['avg_return']*100:+.1f}%
平均回撤：{best['avg_drawdown']*100:.1f}%
平均交易：{best['avg_trades']:.1f} 次
综合评分：{best['score']:+.3f}

⏱️ 耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)
""")
    
    return summary


def main():
    parser = argparse.ArgumentParser(description='终极策略优化回测')
    parser.add_argument('--sample', type=int, default=None, help='抽样数量')
    parser.add_argument('--all', action='store_true', help='全市场回测')
    parser.add_argument('--symbol', type=str, default=None, help='单只股票')
    
    args = parser.parse_args()
    
    if args.symbol:
        result = optimize_single_stock(args.symbol)
        if result:
            print(f"\n{'='*70}")
            print(f"📊 {args.symbol} 最佳策略")
            print(f"{'='*70}")
            print(f"数据范围：{result['data_range']}")
            
            if result['best']:
                b = result['best']
                print(f"\n最佳策略：{b['strategy_name']}")
                print(f"胜率：{b['win_rate']*100:.1f}%")
                print(f"年化：{b['annual_return']*100:+.1f}%")
                print(f"回撤：{b['max_drawdown']*100:.1f}%")
                print(f"交易：{b['total_trades']} 次")
                print(f"盈亏比：{b['profit_loss_ratio']:.2f}")
                print(f"夏普：{b['sharpe_ratio']:+.2f}")
                
                print("\n| 排名 | 策略 | 胜率 | 年化 | 回撤 | 交易 | 评分 |")
                print("|------|------|------|------|------|------|------|")
                for i, r in enumerate(result['all_results'][:10], 1):
                    print(f"| {i:2d} | {r['strategy_name'][:25]} | {r['win_rate']*100:4.1f}% | "
                          f"{r['annual_return']*100:+4.1f}% | {r['max_drawdown']*100:4.1f}% | "
                          f"{r['total_trades']:3d} | {r['score']:+5.3f} |")
    
    elif args.all or args.sample:
        full_market_backtest(args.sample)
    
    else:
        print("用法：")
        print("  --symbol 000001  单只股票优化")
        print("  --sample 500      抽样回测")
        print("  --all             全市场回测")


if __name__ == '__main__':
    main()