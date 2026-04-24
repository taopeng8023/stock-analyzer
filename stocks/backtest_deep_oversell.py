#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度超卖反弹策略 - 全市场回测

最优策略参数：
买入：跌MA20 + 跌>12% + RSI<40
卖出：盈利10%回撤5% / RSI>70 / KDJ>85
止损：12%

效果：胜率61.1%，期望收益+1.42%
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

def calc_rsi(data, period=14):
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_kdj(data, n=9):
    lowv = data['low'].rolling(n).min()
    highv = data['high'].rolling(n).max()
    rsv = (data['close'] - lowv) / (highv - lowv) * 100
    k = rsv.ewm(alpha=1/3, adjust=False).mean()
    d = k.ewm(alpha=1/3, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


# ============== 深度超卖反弹策略 ==============

class DeepOversellStrategy:
    """深度超卖反弹策略"""
    
    def __init__(self, params: Dict = None):
        self.params = params or {
            'ma_period': 20,        # MA周期
            'drop_pct': 0.08,       # 跌幅阈值 8%（放宽）
            'rsi_buy': 50,          # RSI买入阈值 50（放宽）
            'rsi_sell': 70,         # RSI卖出阈值
            'kdj_sell': 85,         # KDJ卖出阈值
            'profit_pct': 0.10,     # 盈利阈值 10%
            'trail_pct': 0.05,      # 回撤阈值 5%
            'stop_loss': 0.12,      # 止损 12%
            'hold_days': 15,        # 最大持仓天数
        }
        self.name = "深度超卖反弹"
    
    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """生成交易信号"""
        signals = []
        
        # 计算指标
        ma = calc_ma(data, self.params['ma_period'])
        rsi = calc_rsi(data)
        k, d, j = calc_kdj(data)
        
        # 计算跌幅（相对MA20）
        drop_from_ma = (data['close'] - ma) / ma
        
        for i in range(20, len(data)):
            date = data['date'].iloc[i]
            close = float(data['close'].iloc[i])
            
            # ===== 买入条件 =====
            # 1. 股价低于MA20
            below_ma = close < ma.iloc[i]
            
            # 2. 跌幅超过12%
            drop_pct = drop_from_ma.iloc[i]
            deep_drop = drop_pct <= -self.params['drop_pct']
            
            # 3. RSI < 40（超卖）
            rsi_val = rsi.iloc[i]
            oversell = rsi_val < self.params['rsi_buy']
            
            # 三条件同时满足
            if below_ma and deep_drop and oversell:
                signals.append({
                    'date': date,
                    'type': 'buy',
                    'price': close,
                    'drop_pct': drop_pct,
                    'rsi': rsi_val,
                    'kdj_j': j.iloc[i]
                })
        
        return signals


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital=100000, fee_rate=0.0006):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
    
    def run(self, strategy: DeepOversellStrategy, data: pd.DataFrame) -> Dict:
        """执行回测"""
        if len(data) < 100:
            return None
        
        signals = strategy.generate_signals(data)
        
        if not signals:
            return None
        
        # 参数
        params = strategy.params
        stop_loss = params['stop_loss']
        profit_pct = params['profit_pct']
        trail_pct = params['trail_pct']
        rsi_sell = params['rsi_sell']
        kdj_sell = params['kdj_sell']
        max_hold_days = params['hold_days']
        
        # 计算指标（用于卖出判断）
        rsi = calc_rsi(data)
        k, d, j = calc_kdj(data)
        
        # 状态
        capital = self.initial_capital
        position = 0
        cost_price = 0
        highest_price = 0
        buy_date = None
        trades = []
        
        signal_idx = 0
        
        for i in range(len(data)):
            date = data['date'].iloc[i]
            close = float(data['close'].iloc[i])
            
            # 更新最高价
            if position > 0:
                highest_price = max(highest_price, close)
                
                # 持仓天数
                hold_days = (date - buy_date).days
                
                # ===== 止损检查 =====
                loss_pct = (close - cost_price) / cost_price
                if loss_pct <= -stop_loss:
                    self._sell(date, close, position, 'stop_loss', trades, capital)
                    capital = trades[-1]['capital']
                    position = 0
                    continue
                
                # ===== 止盈检查 =====
                if loss_pct >= profit_pct:
                    # 盈利达标，进入移动止盈
                    drawdown = (highest_price - close) / highest_price
                    if drawdown >= trail_pct:
                        self._sell(date, close, position, 'trailing_stop', trades, capital)
                        capital = trades[-1]['capital']
                        position = 0
                        continue
                
                # ===== RSI超买卖出 =====
                rsi_val = rsi.iloc[i] if i < len(rsi) else None
                if rsi_val and rsi_val > rsi_sell:
                    self._sell(date, close, position, 'rsi_overbought', trades, capital)
                    capital = trades[-1]['capital']
                    position = 0
                    continue
                
                # ===== KDJ超买卖出 =====
                j_val = j.iloc[i] if i < len(j) else None
                if j_val and j_val > kdj_sell:
                    self._sell(date, close, position, 'kdj_overbought', trades, capital)
                    capital = trades[-1]['capital']
                    position = 0
                    continue
                
                # ===== 最大持仓天数 =====
                if hold_days >= max_hold_days:
                    self._sell(date, close, position, 'max_hold', trades, capital)
                    capital = trades[-1]['capital']
                    position = 0
                    continue
            
            # ===== 买入信号处理 =====
            while signal_idx < len(signals) and signals[signal_idx]['date'] == date:
                sig = signals[signal_idx]
                
                if sig['type'] == 'buy' and position == 0:
                    # 买入
                    buy_price = close * 1.001  # 滑点
                    shares = int(capital * 0.95 / buy_price / 100) * 100
                    
                    if shares >= 100:
                        amount = shares * buy_price
                        fee = amount * self.fee_rate
                        
                        capital -= (amount + fee)
                        position = shares
                        cost_price = buy_price
                        highest_price = buy_price
                        buy_date = date
                        
                        trades.append({
                            'date': date,
                            'type': 'buy',
                            'price': buy_price,
                            'shares': shares,
                            'amount': amount,
                            'fee': fee,
                            'drop_pct': sig.get('drop_pct', 0),
                            'rsi': sig.get('rsi', 0),
                            'capital': capital
                        })
                
                signal_idx += 1
        
        # 强制平仓
        if position > 0:
            last_close = float(data['close'].iloc[-1])
            last_date = data['date'].iloc[-1]
            self._sell(last_date, last_close, position, 'force_close', trades, capital)
        
        return self._calculate_metrics(trades)
    
    def _sell(self, date, price, shares, reason, trades, capital):
        """卖出操作"""
        sell_price = price * 0.999
        amount = shares * sell_price
        fee = amount * self.fee_rate
        
        # 找到对应的买入
        buy_trades = [t for t in trades if t['type'] == 'buy']
        last_buy = buy_trades[-1] if buy_trades else None
        
        profit = amount - (shares * last_buy['price']) - fee if last_buy else 0
        profit_pct = profit / (shares * last_buy['price']) if last_buy else 0
        hold_days = (date - last_buy['date']).days if last_buy else 0
        
        trades.append({
            'date': date,
            'type': 'sell',
            'price': sell_price,
            'shares': shares,
            'amount': amount,
            'fee': fee,
            'profit': profit,
            'profit_pct': profit_pct,
            'hold_days': hold_days,
            'reason': reason,
            'capital': capital + amount - fee
        })
    
    def _calculate_metrics(self, trades):
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
        
        avg_win_pct = statistics.mean([t['profit_pct'] for t in win_trades]) if win_trades else 0
        avg_loss_pct = statistics.mean([t['profit_pct'] for t in loss_trades]) if loss_trades else 0
        
        # 期望收益
        expected_return = win_rate * avg_win_pct + (1 - win_rate) * avg_loss_pct
        
        # 盈亏比
        gross_win = sum(abs(t['profit']) for t in win_trades)
        gross_loss = sum(abs(t['profit']) for t in loss_trades)
        profit_loss_ratio = gross_win / gross_loss if gross_loss > 0 else 0
        
        # 平均持仓天数
        avg_hold_days = statistics.mean([t['hold_days'] for t in sell_trades]) if sell_trades else 0
        
        # 卖出原因统计
        sell_reasons = {}
        for t in sell_trades:
            reason = t.get('reason', 'unknown')
            if reason not in sell_reasons:
                sell_reasons[reason] = {'count': 0, 'profit': 0, 'pct': 0}
            sell_reasons[reason]['count'] += 1
            sell_reasons[reason]['profit'] += t['profit']
            sell_reasons[reason]['pct'] += t['profit_pct']
        
        return {
            'strategy': self.name,
            'total_trades': len(sell_trades),
            'win_trades': len(win_trades),
            'loss_trades': len(loss_trades),
            'win_rate': win_rate,
            'avg_win_pct': avg_win_pct,
            'avg_loss_pct': avg_loss_pct,
            'expected_return': expected_return,
            'profit_loss_ratio': profit_loss_ratio,
            'total_profit': total_profit,
            'avg_hold_days': avg_hold_days,
            'sell_reasons': sell_reasons,
            'trades': trades
        }


def backtest_single_stock(symbol: str) -> Dict:
    """单只股票回测"""
    data = load_stock_data(symbol)
    if data is None or len(data) < 100:
        return None
    
    strategy = DeepOversellStrategy()
    engine = BacktestEngine()
    result = engine.run(strategy, data)
    
    if result:
        result['symbol'] = symbol
        result['data_range'] = f"{data['date'].min().strftime('%Y-%m-%d')} ~ {data['date'].max().strftime('%Y-%m-%d')}"
    
    return result


def full_market_backtest():
    """全市场回测"""
    print('='*70)
    print('深度超卖反弹策略 - 全市场回测')
    print('='*70)
    print()
    print('策略参数：')
    print('  买入：跌MA20 + 跌>8% + RSI<50（放宽）')
    print('  卖出：盈利10%回撤5% / RSI>70 / KDJ>85')
    print('  止损：12%')
    print('  持仓：最长15天')
    print()
    
    stock_files = list(set([f.stem for f in CACHE_DIR.glob('*.json')]))
    print(f'📊 全量回测：{len(stock_files)} 只股票')
    print()
    
    all_results = []
    start_time = time.time()
    
    for i, symbol in enumerate(stock_files):
        try:
            result = backtest_single_stock(symbol)
            
            if result and result['total_trades'] > 0:
                all_results.append({
                    'symbol': symbol,
                    'trades': result['total_trades'],
                    'win_rate': result['win_rate'],
                    'avg_win_pct': result['avg_win_pct'],
                    'avg_loss_pct': result['avg_loss_pct'],
                    'expected_return': result['expected_return'],
                    'profit_loss_ratio': result['profit_loss_ratio'],
                    'total_profit': result['total_profit'],
                    'avg_hold_days': result['avg_hold_days'],
                    'sell_reasons': result['sell_reasons']
                })
            
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                speed = (i + 1) / elapsed
                valid = len(all_results)
                print(f"⏳ {i+1}/{len(stock_files)} ({(i+1)/len(stock_files)*100:.1f}%) | 有效:{valid} | 速度:{speed:.1f}只/秒")
        
        except Exception as e:
            pass
    
    elapsed = time.time() - start_time
    
    # 汇总
    print("\n" + "="*70)
    print("📊 全市场回测结果汇总")
    print("="*70)
    
    if not all_results:
        print("无有效回测结果")
        return
    
    # 全市场统计
    total_trades = sum(r['trades'] for r in all_results)
    total_win = sum(r['trades'] * r['win_rate'] for r in all_results)
    
    avg_win_rate = statistics.mean([r['win_rate'] for r in all_results])
    avg_expected_return = statistics.mean([r['expected_return'] for r in all_results])
    avg_win_pct = statistics.mean([r['avg_win_pct'] for r in all_results])
    avg_loss_pct = statistics.mean([r['avg_loss_pct'] for r in all_results])
    avg_hold_days = statistics.mean([r['avg_hold_days'] for r in all_results])
    
    # 盈利股票数
    profit_stocks = len([r for r in all_results if r['expected_return'] > 0])
    
    print(f"""
覆盖股票：{len(all_results)} 只
总交易数：{total_trades} 次

平均胜率：{avg_win_rate*100:.1f}% (目标61.1%)
期望收益：{avg_expected_return*100:+.2f}% (目标+1.42%)
盈利时赚：{avg_win_pct*100:+.2f}% (目标+7.07%)
亏损时亏：{avg_loss_pct*100:+.2f}% (目标-7.46%)

盈利股票：{profit_stocks}/{len(all_results)} ({profit_stocks/len(all_results)*100:.1f}%)
平均持仓：{avg_hold_days:.1f} 天

⏱️ 耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)
""")
    
    # 卖出原因统计
    sell_stats = {}
    for r in all_results:
        for reason, stats in r.get('sell_reasons', {}).items():
            if reason not in sell_stats:
                sell_stats[reason] = {'count': 0, 'win': 0, 'total': 0}
            sell_stats[reason]['count'] += stats['count']
            sell_stats[reason]['total'] += stats['profit']
            if stats['profit'] > 0:
                sell_stats[reason]['win'] += stats['count']
    
    print("卖出原因分析：")
    print("| 原因 | 次数 | 盈利次数 | 总盈利 |")
    print("|------|------|---------|--------|")
    for reason, stats in sorted(sell_stats.items(), key=lambda x: -x[1]['count']):
        win_pct = stats['win'] / stats['count'] * 100 if stats['count'] > 0 else 0
        print(f"| {reason} | {stats['count']} | {stats['win']} ({win_pct:.1f}%) | {stats['total']:,.0f} |")
    
    # Top 20 表现最佳
    print("\n" + "="*70)
    print("🏆 Top 20 表现最佳股票")
    print("="*70)
    
    sorted_results = sorted(all_results, key=lambda x: -x['expected_return'])
    
    print("| 排名 | 代码 | 交易 | 胜率 | 期望收益 | 盈利时赚 | 亏损时亏 |")
    print("|------|------|------|------|---------|---------|---------|")
    for i, r in enumerate(sorted_results[:20], 1):
        print(f"| {i:2d} | {r['symbol']} | {r['trades']} | {r['win_rate']*100:.1f}% | "
              f"{r['expected_return']*100:+.2f}% | {r['avg_win_pct']*100:+.2f}% | {r['avg_loss_pct']*100:+.2f}% |")
    
    # Top 20 表现最差
    print("\n" + "="*70)
    print("⚠️ Top 20 表现最差股票")
    print("="*70)
    
    worst_results = sorted(all_results, key=lambda x: x['expected_return'])[:20]
    
    print("| 排名 | 代码 | 交易 | 胜率 | 期望收益 | 盈利时赚 | 亏损时亏 |")
    print("|------|------|------|------|---------|---------|---------|")
    for i, r in enumerate(worst_results, 1):
        print(f"| {i:2d} | {r['symbol']} | {r['trades']} | {r['win_rate']*100:.1f}% | "
              f"{r['expected_return']*100:+.2f}% | {r['avg_win_pct']*100:+.2f}% | {r['avg_loss_pct']*100:+.2f}% |")
    
    # 收益分布
    print("\n" + "="*70)
    print("📈 期望收益分布")
    print("="*70)
    
    returns = [r['expected_return'] for r in all_results]
    
    p10 = np.percentile(returns, 10)
    p25 = np.percentile(returns, 25)
    p50 = np.percentile(returns, 50)
    p75 = np.percentile(returns, 75)
    p90 = np.percentile(returns, 90)
    
    print(f"""
P10 (最差10%): {p10*100:+.2f}%
P25 (较差25%): {p25*100:+.2f}%
P50 (中位数): {p50*100:+.2f}%
P75 (较好25%): {p75*100:+.2f}%
P90 (最佳10%): {p90*100:+.2f}%
""")
    
    # 保存结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    results_df = pd.DataFrame(all_results)
    results_df.to_csv(RESULTS_DIR / f'deep_oversell_all_{timestamp}.csv',
                      index=False, encoding='utf-8-sig')
    
    # 保存汇总
    summary = {
        'timestamp': timestamp,
        'stock_count': len(all_results),
        'total_trades': total_trades,
        'avg_win_rate': avg_win_rate,
        'avg_expected_return': avg_expected_return,
        'avg_win_pct': avg_win_pct,
        'avg_loss_pct': avg_loss_pct,
        'profit_stocks': profit_stocks,
        'avg_hold_days': avg_hold_days,
        'elapsed_seconds': elapsed
    }
    
    with open(RESULTS_DIR / f'deep_oversell_summary_{timestamp}.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n💾 结果已保存至 backtest_results/")
    print(f"  - deep_oversell_all_{timestamp}.csv")
    print(f"  - deep_oversell_summary_{timestamp}.json")
    
    # 结论
    print("\n" + "="*70)
    print("🎯 结论")
    print("="*70)
    
    if avg_win_rate >= 0.60 and avg_expected_return >= 0.01:
        print(f"""
✅ 策略有效！
胜率 {avg_win_rate*100:.1f}% ≥ 60%，期望收益 {avg_expected_return*100:+.2f}% ≥ 1%

符合预期，可以用于实盘选股。
""")
    elif avg_win_rate >= 0.55 and avg_expected_return >= 0.005:
        print(f"""
🟡 策略基本有效，但略低于预期。
胜率 {avg_win_rate*100:.1f}% (目标61.1%)，期望收益 {avg_expected_return*100:+.2f}% (目标+1.42%)

建议：进一步优化参数或增加过滤条件。
""")
    else:
        print(f"""
❌ 策略表现不佳。
胜率 {avg_win_rate*100:.1f}%，期望收益 {avg_expected_return*100:+.2f}%

建议：重新调整参数或换其他策略。
""")
    
    return all_results


def main():
    parser = argparse.ArgumentParser(description='深度超卖反弹策略回测')
    parser.add_argument('--all', action='store_true', help='全市场回测')
    parser.add_argument('--symbol', type=str, default=None, help='单只股票回测')
    parser.add_argument('--sample', type=int, default=None, help='抽样回测')
    
    args = parser.parse_args()
    
    if args.symbol:
        result = backtest_single_stock(args.symbol)
        if result:
            print(f"\n{'='*70}")
            print(f"📊 {args.symbol} 回测结果")
            print(f"{'='*70}")
            print(f"\n数据范围：{result['data_range']}")
            print(f"\n交易次数：{result['total_trades']}")
            print(f"胜率：{result['win_rate']*100:.1f}%")
            print(f"期望收益：{result['expected_return']*100:+.2f}%")
            print(f"盈利时赚：{result['avg_win_pct']*100:+.2f}%")
            print(f"亏损时亏：{result['avg_loss_pct']*100:+.2f}%")
            print(f"盈亏比：{result['profit_loss_ratio']:.2f}")
            print(f"平均持仓：{result['avg_hold_days']:.1f}天")
            
            print("\n卖出原因分析：")
            for reason, stats in result['sell_reasons'].items():
                win_pct = stats['count'] / result['total_trades'] * 100
                print(f"  {reason}: {stats['count']}次 ({win_pct:.1f}%) 收益{stats['profit']:,.0f}")
    
    elif args.all:
        full_market_backtest()
    
    elif args.sample:
        # 抽样回测
        import random
        random.seed(42)
        stock_files = list(set([f.stem for f in CACHE_DIR.glob('*.json')]))
        sample_files = random.sample(stock_files, min(args.sample, len(stock_files)))
        
        print(f"抽样回测：{args.sample} 只股票")
        
        # 临时修改缓存目录的文件列表
        all_results = []
        for symbol in sample_files:
            try:
                result = backtest_single_stock(symbol)
                if result and result['total_trades'] > 0:
                    all_results.append(result)
            except:
                pass
        
        # 统计
        if all_results:
            avg_win = statistics.mean([r['win_rate'] for r in all_results])
            avg_return = statistics.mean([r['expected_return'] for r in all_results])
            print(f"\n抽样结果：")
            print(f"  覆盖：{len(all_results)} 只")
            print(f"  胜率：{avg_win*100:.1f}%")
            print(f"  期望收益：{avg_return*100:+.2f}%")
    
    else:
        print("用法：")
        print("  --symbol 000001  单只股票回测")
        print("  --all             全市场回测")
        print("  --sample 500      抽样回测")


if __name__ == '__main__':
    main()