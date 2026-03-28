#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略参数网格搜索优化系统

通过回测结果网格搜索最优参数:
- 止盈比例 (5% - 25%)
- 止损比例 (3% - 10%)
- 买入评分阈值 (65 - 85)
- 追踪止损比例 (3% - 8%)
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Tuple
from itertools import product
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest_with_cache import load_cached_data, BacktestEngine


# ==================== 参数网格搜索 ====================

def grid_search_optimization(code: str, data: List[Dict], 
                             take_profit_range: Tuple[float, float, float] = (0.08, 0.20, 0.04),
                             stop_loss_range: Tuple[float, float, float] = (0.04, 0.10, 0.02),
                             score_threshold_range: Tuple[int, int, int] = (65, 85, 5),
                             trailing_stop_range: Tuple[float, float, float] = (0.03, 0.08, 0.02)) -> List[Dict]:
    """
    网格搜索最优参数
    
    Args:
        code: 股票代码
        data: 历史数据
        take_profit_range: (最小值，最大值，步长)
        stop_loss_range: (最小值，最大值，步长)
        score_threshold_range: (最小值，最大值，步长)
        trailing_stop_range: (最小值，最大值，步长)
    
    Returns:
        所有参数组合的回测结果
    """
    # 生成参数网格
    take_profits = np.arange(take_profit_range[0], take_profit_range[1] + 0.001, take_profit_range[2])
    stop_losses = np.arange(stop_loss_range[0], stop_loss_range[1] + 0.001, stop_loss_range[2])
    score_thresholds = range(score_threshold_range[0], score_threshold_range[1] + 1, score_threshold_range[2])
    trailing_stops = np.arange(trailing_stop_range[0], trailing_stop_range[1] + 0.001, trailing_stop_range[2])
    
    total_combinations = len(take_profits) * len(stop_losses) * len(score_thresholds) * len(trailing_stops)
    print(f"🔍 参数网格搜索")
    print(f"   止盈范围：{take_profits[0]:.0%} - {take_profits[-1]:.0%}")
    print(f"   止损范围：{stop_losses[0]:.0%} - {stop_losses[-1]:.0%}")
    print(f"   评分阈值：{score_thresholds[0]} - {score_thresholds[-1]}")
    print(f"   追踪止损：{trailing_stops[0]:.0%} - {trailing_stops[-1]:.0%}")
    print(f"   总组合数：{total_combinations}")
    print()
    
    results = []
    combo_idx = 0
    
    for tp, sl, st, ts in product(take_profits, stop_losses, score_thresholds, trailing_stops):
        combo_idx += 1
        
        # 进度显示
        if combo_idx % 50 == 0:
            print(f"  进度：{combo_idx}/{total_combinations} ({combo_idx/total_combinations*100:.1f}%)")
        
        # 运行回测
        engine = OptimizedBacktestEngine(
            initial_capital=100000,
            take_profit=tp,
            stop_loss=sl,
            score_threshold=st,
            trailing_stop=ts
        )
        
        try:
            result = engine.run(data)
            
            results.append({
                'params': {
                    'take_profit': tp,
                    'stop_loss': sl,
                    'score_threshold': st,
                    'trailing_stop': ts
                },
                'metrics': {
                    'total_return': result['total_return'],
                    'annualized_return': result['annualized_return'],
                    'sharpe_ratio': result['sharpe_ratio'],
                    'max_drawdown': result['max_drawdown'],
                    'win_rate': result['win_rate'],
                    'total_trades': result['total_trades']
                }
            })
        except Exception as e:
            continue
    
    # 按夏普比率排序
    results.sort(key=lambda x: x['metrics']['sharpe_ratio'], reverse=True)
    
    return results


class OptimizedBacktestEngine:
    """优化版回测引擎 (支持参数配置)"""
    
    def __init__(self, initial_capital: float = 100000,
                 take_profit: float = 0.15,
                 stop_loss: float = 0.06,
                 score_threshold: int = 75,
                 trailing_stop: float = 0.05,
                 trailing_start: float = 0.08,
                 commission_rate: float = 0.0003,
                 slippage_rate: float = 0.001):
        self.initial_capital = initial_capital
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.score_threshold = score_threshold
        self.trailing_stop = trailing_stop
        self.trailing_start = trailing_start
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        
        self.capital = initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = [initial_capital]
        self.daily_returns = []
    
    def run(self, data: List[Dict]) -> Dict:
        """运行回测"""
        self.capital = self.initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = [self.initial_capital]
        self.daily_returns = []
        
        prev_equity = self.initial_capital
        
        for i in range(60, len(data)):
            # 计算评分
            score, _ = self._calculate_score(data, i)
            
            # 生成交易信号
            signal = self._trading_strategy(score, data, i)
            
            # 执行交易
            if signal == 'buy' and not self.position:
                self._execute_buy(data[i])
            elif signal == 'sell' and self.position:
                self._execute_sell(data[i])
            
            # 更新持仓
            if self.position:
                self.position['hold_days'] += 1
                if data[i]['close'] > self.position['peak_price']:
                    self.position['peak_price'] = data[i]['close']
            
            # 计算权益
            equity = self._calculate_equity(data[i])
            self.equity_curve.append(equity)
            
            daily_return = (equity - prev_equity) / prev_equity * 100
            self.daily_returns.append(daily_return)
            prev_equity = equity
        
        return self._generate_result(data)
    
    def _calculate_score(self, data: List[Dict], idx: int) -> Tuple[float, Dict]:
        """简化评分计算"""
        if idx < 50:
            return 0, {}
        
        scores = {}
        closes = [d['close'] for d in data[:idx+1]]
        volumes = [d['volume'] for d in data[:idx+1]]
        
        # 技术面 (40 分)
        tech_score = 0
        ma5 = self._calculate_ma(closes, 5)[idx]
        ma20 = self._calculate_ma(closes, 20)[idx]
        
        if ma5 and ma20 and ma5 > ma20:
            tech_score += 20
        
        # 动量
        if idx >= 10:
            momentum = (closes[idx] - closes[idx-10]) / closes[idx-10] * 100
            if momentum > 5:
                tech_score += 20
            elif momentum > 0:
                tech_score += 10
        
        scores['技术面'] = min(tech_score, 40)
        
        # 资金面 (25 分)
        money_score = 0
        if idx >= 20:
            avg_vol = sum(volumes[idx-20:idx]) / 20
            if volumes[idx] > avg_vol * 1.3:
                money_score += 25
            elif volumes[idx] > avg_vol:
                money_score += 15
        
        scores['资金面'] = money_score
        
        # 趋势面 (20 分)
        trend_score = 0
        if idx >= 20:
            trend = (closes[idx] - closes[idx-20]) / closes[idx-20] * 100
            if trend > 10:
                trend_score += 20
            elif trend > 5:
                trend_score += 15
            elif trend > 0:
                trend_score += 10
        
        scores['趋势面'] = trend_score
        
        # 风险面 (15 分)
        scores['风险面'] = 15
        
        total = sum(scores.values())
        return total, scores
    
    def _calculate_ma(self, prices: List[float], period: int) -> List[float]:
        result = []
        for i in range(len(prices)):
            if i < period - 1:
                result.append(None)
            else:
                result.append(sum(prices[i-period+1:i+1]) / period)
        return result
    
    def _trading_strategy(self, score: float, data: List[Dict], idx: int) -> str:
        """交易策略"""
        current_price = data[idx]['close']
        
        if self.position:
            cost_price = self.position['cost_price']
            
            # 止盈
            if current_price >= cost_price * (1 + self.take_profit):
                return 'sell'
            
            # 止损
            if current_price <= cost_price * (1 - self.stop_loss):
                return 'sell'
            
            # 追踪止损
            if current_price >= cost_price * (1 + self.trailing_start):
                peak = max(self.position.get('peak_price', cost_price), current_price)
                if current_price <= peak * (1 - self.trailing_stop):
                    return 'sell'
            
            # 评分过低
            if score < 50:
                return 'sell'
            
            return 'hold'
        
        # 买入
        if score >= self.score_threshold:
            return 'buy'
        
        return 'hold'
    
    def _execute_buy(self, bar: Dict):
        """执行买入"""
        price = bar['close'] * (1 + self.slippage_rate)
        available = self.capital * 0.95 / price
        shares = int(available // 100) * 100
        
        if shares >= 100:
            cost = shares * price
            commission = cost * self.commission_rate
            total = cost + commission
            
            if total <= self.capital:
                self.capital -= total
                self.position = {
                    'shares': shares,
                    'cost_price': price,
                    'peak_price': price,
                    'hold_days': 0
                }
                
                self.trades.append({
                    'date': bar['date'],
                    'type': 'buy',
                    'price': price,
                    'shares': shares
                })
    
    def _execute_sell(self, bar: Dict):
        """执行卖出"""
        price = bar['close'] * (1 - self.slippage_rate)
        shares = self.position['shares']
        revenue = shares * price
        commission = revenue * self.commission_rate
        net = revenue - commission
        
        profit = net - (shares * self.position['cost_price'] + shares * self.position['cost_price'] * self.commission_rate)
        profit_pct = profit / (shares * self.position['cost_price']) * 100
        
        self.capital += net
        
        self.trades.append({
            'date': bar['date'],
            'type': 'sell',
            'price': price,
            'shares': shares,
            'profit': profit,
            'profit_pct': profit_pct
        })
        
        self.position = None
    
    def _calculate_equity(self, bar: Dict) -> float:
        """计算权益"""
        if self.position:
            return self.capital + self.position['shares'] * bar['close']
        return self.capital
    
    def _generate_result(self, data: List[Dict]) -> Dict:
        """生成回测结果"""
        final_equity = self.equity_curve[-1]
        total_return = (final_equity - self.initial_capital) / self.initial_capital * 100
        
        sell_trades = [t for t in self.trades if t['type'] == 'sell']
        winning = len([t for t in sell_trades if t.get('profit', 0) > 0])
        losing = len([t for t in sell_trades if t.get('profit', 0) <= 0])
        win_rate = winning / len(sell_trades) * 100 if sell_trades else 0
        
        if len(self.daily_returns) > 1:
            volatility = np.std(self.daily_returns)
            avg_return = np.mean(self.daily_returns)
            sharpe = (avg_return * 252) / (volatility * np.sqrt(252)) if volatility > 0 else 0
            
            peak = self.equity_curve[0]
            max_dd = 0
            for eq in self.equity_curve:
                if eq > peak:
                    peak = eq
                dd = (peak - eq) / peak * 100
                if dd > max_dd:
                    max_dd = dd
        else:
            volatility = 0
            sharpe = 0
            max_dd = 0
        
        days = len(data) - 60
        annualized = ((1 + total_return/100) ** (252/days) - 1) * 100 if days > 0 else 0
        
        buy_trades = [t for t in self.trades if t['type'] == 'buy']
        
        return {
            'total_return': total_return,
            'annualized_return': annualized,
            'volatility': volatility * 100,
            'max_drawdown': max_dd,
            'sharpe_ratio': sharpe,
            'total_trades': len(buy_trades),
            'winning_trades': winning,
            'losing_trades': losing,
            'win_rate': win_rate
        }


# ==================== 结果分析 ====================

def analyze_optimization_results(results: List[Dict]) -> Dict:
    """分析优化结果"""
    if not results:
        return {}
    
    # 按不同指标排序
    by_sharpe = sorted(results, key=lambda x: x['metrics']['sharpe_ratio'], reverse=True)
    by_return = sorted(results, key=lambda x: x['metrics']['total_return'], reverse=True)
    by_drawdown = sorted(results, key=lambda x: x['metrics']['max_drawdown'])
    
    # 参数统计分析
    top_10 = by_sharpe[:10]
    
    # 最优参数范围
    tp_values = [r['params']['take_profit'] for r in top_10]
    sl_values = [r['params']['stop_loss'] for r in top_10]
    st_values = [r['params']['score_threshold'] for r in top_10]
    ts_values = [r['params']['trailing_stop'] for r in top_10]
    
    return {
        'best_by_sharpe': by_sharpe[0],
        'best_by_return': by_return[0],
        'best_by_drawdown': by_drawdown[0],
        'top_10_avg': {
            'sharpe': np.mean([r['metrics']['sharpe_ratio'] for r in top_10]),
            'return': np.mean([r['metrics']['total_return'] for r in top_10]),
            'drawdown': np.mean([r['metrics']['max_drawdown'] for r in top_10]),
            'win_rate': np.mean([r['metrics']['win_rate'] for r in top_10])
        },
        'optimal_ranges': {
            'take_profit': f"{min(tp_values):.0%} - {max(tp_values):.0%} (平均{np.mean(tp_values):.0%})",
            'stop_loss': f"{min(sl_values):.0%} - {max(sl_values):.0%} (平均{np.mean(sl_values):.0%})",
            'score_threshold': f"{min(st_values)} - {max(st_values)} (平均{np.mean(st_values):.0f})",
            'trailing_stop': f"{min(ts_values):.0%} - {max(ts_values):.0%} (平均{np.mean(ts_values):.0%})"
        }
    }


def print_optimization_report(results: List[Dict], analysis: Dict):
    """打印优化报告"""
    print("\n" + "="*100)
    print("📊 策略参数优化报告".center(100))
    print("="*100)
    
    # 最优组合 (夏普比率)
    print("\n🏆 最优参数组合 (按夏普比率)")
    print("-"*100)
    best = analysis['best_by_sharpe']
    p = best['params']
    m = best['metrics']
    print(f"  止盈：{p['take_profit']:.0%}  止损：{p['stop_loss']:.0%}  评分阈值：{p['score_threshold']}  追踪止损：{p['trailing_stop']:.0%}")
    print(f"  收益率：{m['total_return']:+.2f}%  年化：{m['annualized_return']:+.2f}%")
    print(f"  夏普比率：{m['sharpe_ratio']:.2f}  最大回撤：{m['max_drawdown']:.2f}%  胜率：{m['win_rate']:.1f}%")
    
    # 最高收益组合
    print("\n💰 最优参数组合 (按收益率)")
    print("-"*100)
    best_ret = analysis['best_by_return']
    p = best_ret['params']
    m = best_ret['metrics']
    print(f"  止盈：{p['take_profit']:.0%}  止损：{p['stop_loss']:.0%}  评分阈值：{p['score_threshold']}  追踪止损：{p['trailing_stop']:.0%}")
    print(f"  收益率：{m['total_return']:+.2f}%  年化：{m['annualized_return']:+.2f}%")
    print(f"  夏普比率：{m['sharpe_ratio']:.2f}  最大回撤：{m['max_drawdown']:.2f}%  胜率：{m['win_rate']:.1f}%")
    
    # 最小回撤组合
    print("\n🛡️ 最优参数组合 (按最小回撤)")
    print("-"*100)
    best_dd = analysis['best_by_drawdown']
    p = best_dd['params']
    m = best_dd['metrics']
    print(f"  止盈：{p['take_profit']:.0%}  止损：{p['stop_loss']:.0%}  评分阈值：{p['score_threshold']}  追踪止损：{p['trailing_stop']:.0%}")
    print(f"  收益率：{m['total_return']:+.2f}%  年化：{m['annualized_return']:+.2f}%")
    print(f"  夏普比率：{m['sharpe_ratio']:.2f}  最大回撤：{m['max_drawdown']:.2f}%  胜率：{m['win_rate']:.1f}%")
    
    # Top 10 平均
    print("\n📈 Top 10 参数组合平均表现")
    print("-"*100)
    avg = analysis['top_10_avg']
    print(f"  平均夏普比率：{avg['sharpe']:.2f}")
    print(f"  平均收益率：{avg['return']:+.2f}%")
    print(f"  平均最大回撤：{avg['drawdown']:.2f}%")
    print(f"  平均胜率：{avg['win_rate']:.1f}%")
    
    # 最优参数范围
    print("\n🎯 推荐参数范围")
    print("-"*100)
    ranges = analysis['optimal_ranges']
    print(f"  止盈比例：{ranges['take_profit']}")
    print(f"  止损比例：{ranges['stop_loss']}")
    print(f"  评分阈值：{ranges['score_threshold']}")
    print(f"  追踪止损：{ranges['trailing_stop']}")
    
    print("\n" + "="*100 + "\n")


# ==================== 主程序 ====================

def main():
    import argparse
    from datetime import timedelta
    
    parser = argparse.ArgumentParser(description='策略参数网格搜索优化')
    parser.add_argument('--code', type=str, default='603301', help='股票代码 (默认 603301)')
    parser.add_argument('--days', type=int, default=200, help='回测天数 (默认 200)')
    parser.add_argument('--quick', action='store_true', help='快速模式 (减少参数组合)')
    parser.add_argument('--save', action='store_true', help='保存结果到文件')
    
    args = parser.parse_args()
    
    print("="*100)
    print("🚀 策略参数网格搜索优化系统".center(100))
    print("="*100)
    print(f"作者：凯文")
    print("="*100 + "\n")
    
    # 加载数据
    data = load_cached_data(args.code)
    
    if not data or len(data) < args.days:
        print(f"❌ 数据不足")
        return
    
    data = data[-args.days:]
    
    # 设置参数范围
    if args.quick:
        print("⚡ 快速模式...\n")
        tp_range = (0.10, 0.20, 0.05)
        sl_range = (0.05, 0.08, 0.02)
        st_range = (70, 80, 5)
        ts_range = (0.04, 0.06, 0.02)
    else:
        tp_range = (0.08, 0.20, 0.04)
        sl_range = (0.04, 0.10, 0.02)
        st_range = (65, 85, 5)
        ts_range = (0.03, 0.08, 0.02)
    
    # 网格搜索
    results = grid_search_optimization(
        code=args.code,
        data=data,
        take_profit_range=tp_range,
        stop_loss_range=sl_range,
        score_threshold_range=st_range,
        trailing_stop_range=ts_range
    )
    
    # 分析结果
    analysis = analyze_optimization_results(results)
    
    # 打印报告
    print_optimization_report(results, analysis)
    
    # 保存结果
    if args.save:
        output_dir = os.path.join(os.path.dirname(__file__), 'optimization_results')
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(output_dir, f'optimization_{args.code}_{timestamp}.json')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'code': args.code,
                'timestamp': timestamp,
                'total_combinations': len(results),
                'analysis': analysis,
                'top_20_results': results[:20]
            }, f, ensure_ascii=False, indent=2)
        
        print(f"📁 结果已保存：{filepath}")


if __name__ == '__main__':
    main()
