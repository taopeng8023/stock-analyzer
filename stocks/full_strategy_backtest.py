#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三大策略全量回测
- 缠论 + 蜡烛图
- RSI 超买超卖
- MACD

使用全量 5500+ 只股票数据
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import numpy as np

# 数据目录
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
REPORT_DIR = Path('/home/admin/.openclaw/workspace/stocks/analysis_reports')
REPORT_DIR.mkdir(exist_ok=True)


def load_stock_data(symbol):
    """加载股票数据"""
    filepath = DATA_DIR / f'{symbol}.json'
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def get_stock_list():
    """获取所有股票代码"""
    stocks = []
    for f in DATA_DIR.glob('*.json'):
        stocks.append(f.stem)
    return stocks


# ============== 技术指标计算 ==============

def calc_macd(data):
    """计算 MACD"""
    closes = [d['收盘'] for d in data]
    
    ema12 = []
    for i, close in enumerate(closes):
        if i == 0:
            ema12.append(close)
        else:
            ema12.append(close * 2/13 + ema12[-1] * 11/13)
    
    ema26 = []
    for i, close in enumerate(closes):
        if i == 0:
            ema26.append(close)
        else:
            ema26.append(close * 2/27 + ema26[-1] * 25/27)
    
    dif = [ema12[i] - ema26[i] for i in range(len(closes))]
    
    dea = []
    for i, d in enumerate(dif):
        if i == 0:
            dea.append(d)
        else:
            dea.append(d * 2/10 + dea[-1] * 8/10)
    
    return dif, dea


def calc_rsi(data, period=14):
    """计算 RSI"""
    closes = [d['收盘'] for d in data]
    rsi = []
    
    for i in range(len(closes)):
        if i < period:
            rsi.append(None)
        else:
            gains = []
            losses = []
            for j in range(i-period+1, i+1):
                change = closes[j] - closes[j-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period
            
            if avg_loss == 0:
                rsi.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi.append(100 - (100 / (1 + rs)))
    
    return rsi


def detect_fractal(data, window=5):
    """检测分型"""
    top_fractals = []
    bottom_fractals = []
    
    for i in range(window, len(data) - window):
        highs = [data[i+j]['最高'] for j in range(-window, window+1)]
        lows = [data[i+j]['最低'] for j in range(-window, window+1)]
        
        if data[i]['最高'] == max(highs):
            top_fractals.append(i)
        
        if data[i]['最低'] == min(lows):
            bottom_fractals.append(i)
    
    return top_fractals, bottom_fractals


def detect_candlestick_pattern(data, i):
    """检测蜡烛图形态"""
    o = data[i]['开盘']
    h = data[i]['最高']
    l = data[i]['最低']
    c = data[i]['收盘']
    
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    
    if lower > body * 2 and upper < body * 0.5:
        return 'hammer'
    
    if upper > body * 2 and lower < body * 0.5:
        return 'shooting_star'
    
    if body > (h - l) * 0.7 and c > o:
        return 'big_bull'
    
    if body > (h - l) * 0.7 and c < o:
        return 'big_bear'
    
    return None


# ============== 策略实现 ==============

def strategy_chanlun_candle(data):
    """缠论 + 蜡烛图策略"""
    top_fractals, bottom_fractals = detect_fractal(data)
    
    trades = []
    position = 0
    buy_price = 0
    buy_date = ''
    
    for i in range(10, len(data)):
        pattern = detect_candlestick_pattern(data, i)
        
        # 买入：底分型 + 看涨蜡烛
        if position == 0 and i in bottom_fractals:
            if pattern in ['hammer', 'big_bull']:
                position = 1
                buy_price = data[i]['收盘']
                buy_date = data[i]['日期']
        
        # 卖出：顶分型 + 看跌蜡烛
        elif position == 1 and i in top_fractals:
            if pattern in ['shooting_star', 'big_bear']:
                sell_price = data[i]['收盘']
                profit = (sell_price - buy_price) / buy_price
                trades.append({
                    'buy_date': buy_date,
                    'sell_date': data[i]['日期'],
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'profit': profit
                })
                position = 0
    
    # 处理最后持仓
    if position == 1:
        sell_price = data[-1]['收盘']
        profit = (sell_price - buy_price) / buy_price
        trades.append({
            'buy_date': buy_date,
            'sell_date': data[-1]['日期'],
            'buy_price': buy_price,
            'sell_price': sell_price,
            'profit': profit
        })
    
    return trades


def strategy_rsi(data, buy_threshold=30, sell_threshold=70):
    """RSI 超买超卖策略"""
    rsi = calc_rsi(data)
    
    trades = []
    position = 0
    buy_price = 0
    buy_date = ''
    
    for i in range(20, len(data)):
        if rsi[i] is None:
            continue
        
        # 超卖买入
        if position == 0 and rsi[i] < buy_threshold:
            position = 1
            buy_price = data[i]['收盘']
            buy_date = data[i]['日期']
        
        # 超买卖出
        elif position == 1 and rsi[i] > sell_threshold:
            sell_price = data[i]['收盘']
            profit = (sell_price - buy_price) / buy_price
            trades.append({
                'buy_date': buy_date,
                'sell_date': data[i]['日期'],
                'buy_price': buy_price,
                'sell_price': sell_price,
                'profit': profit
            })
            position = 0
    
    if position == 1:
        sell_price = data[-1]['收盘']
        profit = (sell_price - buy_price) / buy_price
        trades.append({
            'buy_date': buy_date,
            'sell_date': data[-1]['日期'],
            'buy_price': buy_price,
            'sell_price': sell_price,
            'profit': profit
        })
    
    return trades


def strategy_macd(data):
    """MACD 策略"""
    dif, dea = calc_macd(data)
    
    trades = []
    position = 0
    buy_price = 0
    buy_date = ''
    
    for i in range(30, len(data)):
        # 金叉买入
        if position == 0 and dif[i-1] <= dea[i-1] and dif[i] > dea[i]:
            position = 1
            buy_price = data[i]['收盘']
            buy_date = data[i]['日期']
        
        # 死叉卖出
        elif position == 1 and dif[i-1] >= dea[i-1] and dif[i] < dea[i]:
            sell_price = data[i]['收盘']
            profit = (sell_price - buy_price) / buy_price
            trades.append({
                'buy_date': buy_date,
                'sell_date': data[i]['日期'],
                'buy_price': buy_price,
                'sell_price': sell_price,
                'profit': profit
            })
            position = 0
    
    if position == 1:
        sell_price = data[-1]['收盘']
        profit = (sell_price - buy_price) / buy_price
        trades.append({
            'buy_date': buy_date,
            'sell_date': data[-1]['日期'],
            'buy_price': buy_price,
            'sell_price': sell_price,
            'profit': profit
        })
    
    return trades


# ============== 评估函数 ==============

def evaluate_trades(trades, symbol):
    """评估交易结果"""
    if not trades:
        return None
    
    profits = [t['profit'] for t in trades]
    
    # 总收益
    total_return = 1
    for p in profits:
        total_return *= (1 + p)
    total_return -= 1
    
    # 年化收益
    n_days = 365
    annual_return = (1 + total_return) ** (1) - 1
    
    # 胜率
    wins = [p for p in profits if p > 0]
    win_rate = len(wins) / len(profits) * 100
    
    # 盈亏比
    avg_win = np.mean(wins) if wins else 0
    losses = [p for p in profits if p <= 0]
    avg_loss = abs(np.mean(losses)) if losses else 1
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
    
    # 夏普比率
    if len(profits) > 1:
        avg_return = np.mean(profits)
        std_return = np.std(profits)
        sharpe = (avg_return / std_return * np.sqrt(252)) if std_return > 0 else 0
    else:
        sharpe = 0
    
    # 最大回撤
    cumulative = [1]
    for p in profits:
        cumulative.append(cumulative[-1] * (1 + p))
    
    peak = 0
    max_dd = 0
    for v in cumulative:
        if v > peak:
            peak = v
        dd = (peak - v) / peak
        if dd > max_dd:
            max_dd = dd
    
    # 最大单笔盈利
    max_win = max(profits) if profits else 0
    max_loss = min(profits) if profits else 0
    
    return {
        'symbol': symbol,
        'total_return': total_return * 100,
        'annual_return': annual_return * 100,
        'sharpe': sharpe,
        'max_drawdown': max_dd * 100,
        'win_rate': win_rate,
        'profit_loss_ratio': profit_loss_ratio,
        'trade_count': len(trades),
        'max_win': max_win * 100,
        'max_loss': max_loss * 100,
        'trades': trades
    }


# ============== 主函数 ==============

def backtest_strategy(stocks, strategy_func, strategy_name):
    """回测单个策略"""
    print(f"\n回测策略：{strategy_name}")
    print("-" * 80)
    
    results = []
    valid_count = 0
    skip_count = 0
    
    for i, symbol in enumerate(stocks):
        data = load_stock_data(symbol)
        if not data or len(data) < 100:
            skip_count += 1
            continue
        
        trades = strategy_func(data)
        eval_result = evaluate_trades(trades, symbol)
        
        if eval_result:
            results.append(eval_result)
            valid_count += 1
        
        # 进度
        if (i + 1) % 500 == 0:
            print(f"  进度：{i+1}/{len(stocks)} (有效:{valid_count} 跳过:{skip_count})")
    
    return results


def aggregate_results(results, strategy_name):
    """汇总结果"""
    if not results:
        return None
    
    metrics = {
        'strategy': strategy_name,
        'stock_count': len(results),
        'avg_total_return': np.mean([r['total_return'] for r in results]),
        'avg_annual_return': np.mean([r['annual_return'] for r in results]),
        'avg_sharpe': np.mean([r['sharpe'] for r in results]),
        'avg_max_drawdown': np.mean([r['max_drawdown'] for r in results]),
        'avg_win_rate': np.mean([r['win_rate'] for r in results]),
        'avg_profit_loss_ratio': np.mean([r['profit_loss_ratio'] for r in results]),
        'avg_trade_count': np.mean([r['trade_count'] for r in results]),
        'median_total_return': np.median([r['total_return'] for r in results]),
        'median_sharpe': np.median([r['sharpe'] for r in results]),
    }
    
    # 找出最佳股票
    best_stock = max(results, key=lambda x: x['total_return'])
    worst_stock = min(results, key=lambda x: x['total_return'])
    
    metrics['best_stock'] = {
        'symbol': best_stock['symbol'],
        'return': best_stock['total_return']
    }
    metrics['worst_stock'] = {
        'symbol': worst_stock['symbol'],
        'return': worst_stock['total_return']
    }
    
    # 收益分布
    returns = [r['total_return'] for r in results]
    metrics['return_distribution'] = {
        'p10': np.percentile(returns, 10),
        'p25': np.percentile(returns, 25),
        'p50': np.percentile(returns, 50),
        'p75': np.percentile(returns, 75),
        'p90': np.percentile(returns, 90)
    }
    
    # 胜率分布
    win_rates = [r['win_rate'] for r in results]
    metrics['win_rate_distribution'] = {
        'p10': np.percentile(win_rates, 10),
        'p50': np.percentile(win_rates, 50),
        'p90': np.percentile(win_rates, 90)
    }
    
    return metrics


def print_report(metrics_list):
    """打印报告"""
    print("\n" + "=" * 120)
    print("三大策略全量回测对比报告")
    print("=" * 120)
    
    print(f"\n{'策略':<20} {'股票数':<10} {'总收益%':<12} {'年化%':<12} {'夏普':<10} {'回撤%':<12} {'胜率%':<10} {'盈亏比':<10}")
    print("-" * 120)
    
    for m in metrics_list:
        print(f"{m['strategy']:<20} {m['stock_count']:<10} {m['avg_total_return']:>10.2f} {m['avg_annual_return']:>10.2f} {m['avg_sharpe']:>8.2f} {m['avg_max_drawdown']:>10.2f} {m['avg_win_rate']:>8.2f} {m['avg_profit_loss_ratio']:>8.2f}")
    
    print("=" * 120)
    
    # 排名
    print("\n📊 策略排名（按夏普比率）:")
    ranked = sorted(metrics_list, key=lambda x: x['avg_sharpe'], reverse=True)
    for i, m in enumerate(ranked, 1):
        print(f"  {i}. {m['strategy']}: 夏普={m['avg_sharpe']:.2f} 年化={m['avg_annual_return']:.2f}%")
    
    print("\n📊 策略排名（按年化收益）:")
    ranked = sorted(metrics_list, key=lambda x: x['avg_annual_return'], reverse=True)
    for i, m in enumerate(ranked, 1):
        print(f"  {i}. {m['strategy']}: 年化={m['avg_annual_return']:.2f}% 夏普={m['avg_sharpe']:.2f}")
    
    # 详细统计
    print("\n" + "=" * 120)
    print("详细统计")
    print("=" * 120)
    
    for m in metrics_list:
        print(f"\n{m['strategy']}:")
        print(f"  最佳股票：{m['best_stock']['symbol']} ({m['best_stock']['return']:.2f}%)")
        print(f"  最差股票：{m['worst_stock']['symbol']} ({m['worst_stock']['return']:.2f}%)")
        print(f"  收益分布：P10={m['return_distribution']['p10']:.2f}% P50={m['return_distribution']['p50']:.2f}% P90={m['return_distribution']['p90']:.2f}%")
        print(f"  胜率分布：P10={m['win_rate_distribution']['p10']:.1f}% P50={m['win_rate_distribution']['p50']:.1f}% P90={m['win_rate_distribution']['p90']:.1f}%")
    
    print("=" * 120)


def main():
    print("=" * 120)
    print("三大策略全量回测")
    print("=" * 120)
    
    # 获取股票列表
    print("\n[1/5] 加载股票列表...")
    stocks = get_stock_list()
    print(f"   总股票数：{len(stocks)} 只")
    
    # 回测各策略
    all_results = {}
    metrics_list = []
    
    # 策略 1：缠论 + 蜡烛图
    print("\n[2/5] 回测缠论 + 蜡烛图策略...")
    results_chanlun = backtest_strategy(stocks, strategy_chanlun_candle, '缠论 + 蜡烛图')
    all_results['chanlun'] = results_chanlun
    metrics_list.append(aggregate_results(results_chanlun, '缠论 + 蜡烛图'))
    
    # 策略 2：RSI
    print("\n[3/5] 回测 RSI 超买超卖策略...")
    results_rsi = backtest_strategy(stocks, strategy_rsi, 'RSI 超买超卖')
    all_results['rsi'] = results_rsi
    metrics_list.append(aggregate_results(results_rsi, 'RSI 超买超卖'))
    
    # 策略 3：MACD
    print("\n[4/5] 回测 MACD 策略...")
    results_macd = backtest_strategy(stocks, strategy_macd, 'MACD')
    all_results['macd'] = results_macd
    metrics_list.append(aggregate_results(results_macd, 'MACD'))
    
    # 打印报告
    print("\n[5/5] 生成报告...")
    print_report(metrics_list)
    
    # 保存报告
    report = {
        'time': datetime.now().isoformat(),
        'total_stocks': len(stocks),
        'strategies': metrics_list,
        'detailed_results': {
            'chanlun': [r for r in all_results['chanlun']],
            'rsi': [r for r in all_results['rsi']],
            'macd': [r for r in all_results['macd']]
        }
    }
    
    # 保存完整报告（不含详细交易记录，避免文件过大）
    report_summary = {
        'time': datetime.now().isoformat(),
        'total_stocks': len(stocks),
        'strategies': metrics_list
    }
    
    report_file = REPORT_DIR / f'full_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 报告已保存：{report_file}")
    
    # 保存最佳股票列表
    best_stocks = {}
    for m in metrics_list:
        strategy = m['strategy']
        sorted_results = sorted(all_results[strategy.lower().replace(' ', '_').replace('+', '_')], 
                               key=lambda x: x['total_return'], reverse=True)
        best_stocks[strategy] = sorted_results[:20]  # 前 20 只
    
    best_file = REPORT_DIR / f'best_stocks_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(best_file, 'w', encoding='utf-8') as f:
        json.dump(best_stocks, f, indent=2, ensure_ascii=False)
    
    print(f"💾 最佳股票列表：{best_file}")
    
    return metrics_list


if __name__ == '__main__':
    main()
