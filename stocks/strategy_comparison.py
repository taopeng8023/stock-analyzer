#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
四大选股策略抽样回测对比分析

方案一：技术指标策略（均线/MACD/RSI）
方案二：因子分析策略（多因子组合）
方案三：缠论 + 蜡烛图策略
方案四：机器学习策略（简化版）

抽样：从 5500 只股票中随机抽取 200 只
回测期：2025-03-27 ~ 2026-03-27
"""

import json
import random
import sys
from pathlib import Path
from datetime import datetime
import numpy as np

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

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


def sample_stocks(n=200):
    """随机抽样股票"""
    all_stocks = get_stock_list()
    # 确保数据完整
    valid_stocks = []
    for s in all_stocks:
        data = load_stock_data(s)
        if data and len(data) >= 200:
            valid_stocks.append(s)
    
    print(f"有效股票数：{len(valid_stocks)}")
    return random.sample(valid_stocks, min(n, len(valid_stocks)))


# ============== 方案一：技术指标策略 ==============

def calc_ma(data, period):
    """计算移动平均线"""
    closes = [d['收盘'] for d in data]
    ma = []
    for i in range(len(closes)):
        if i < period - 1:
            ma.append(None)
        else:
            ma.append(sum(closes[i-period+1:i+1]) / period)
    return ma


def calc_macd(data):
    """计算 MACD"""
    closes = [d['收盘'] for d in data]
    
    # EMA12
    ema12 = []
    for i, close in enumerate(closes):
        if i == 0:
            ema12.append(close)
        else:
            ema12.append(close * 2/13 + ema12[-1] * 11/13)
    
    # EMA26
    ema26 = []
    for i, close in enumerate(closes):
        if i == 0:
            ema26.append(close)
        else:
            ema26.append(close * 2/27 + ema26[-1] * 25/27)
    
    # DIF
    dif = [ema12[i] - ema26[i] for i in range(len(closes))]
    
    # DEA (DIF 的 9 日 EMA)
    dea = []
    for i, d in enumerate(dif):
        if i == 0:
            dea.append(d)
        else:
            dea.append(d * 2/10 + dea[-1] * 8/10)
    
    # MACD 柱
    macd_bar = [(dif[i] - dea[i]) * 2 for i in range(len(closes))]
    
    return dif, dea, macd_bar


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


def strategy_ma_cross(data):
    """
    方案一：双均线策略
    买入：MA5 上穿 MA20
    卖出：MA5 下穿 MA20
    """
    ma5 = calc_ma(data, 5)
    ma20 = calc_ma(data, 20)
    
    signals = []
    position = 0
    buy_price = 0
    trades = []
    
    for i in range(20, len(data)):
        if ma5[i] is None or ma20[i] is None:
            continue
        
        # 金叉买入
        if position == 0 and ma5[i-1] <= ma20[i-1] and ma5[i] > ma20[i]:
            position = 1
            buy_price = data[i]['收盘']
            signals.append({'date': data[i]['日期'], 'action': 'buy', 'price': buy_price})
        
        # 死叉卖出
        elif position == 1 and ma5[i-1] >= ma20[i-1] and ma5[i] < ma20[i]:
            sell_price = data[i]['收盘']
            profit = (sell_price - buy_price) / buy_price
            trades.append(profit)
            signals.append({'date': data[i]['日期'], 'action': 'sell', 'price': sell_price, 'profit': profit})
            position = 0
    
    # 处理最后持仓
    if position == 1:
        sell_price = data[-1]['收盘']
        profit = (sell_price - buy_price) / buy_price
        trades.append(profit)
    
    return trades, signals


def strategy_macd(data):
    """
    方案一：MACD 策略
    买入：MACD 金叉（DIF 上穿 DEA）
    卖出：MACD 死叉（DIF 下穿 DEA）
    """
    dif, dea, macd_bar = calc_macd(data)
    
    trades = []
    position = 0
    buy_price = 0
    
    for i in range(30, len(data)):
        # 金叉买入
        if position == 0 and dif[i-1] <= dea[i-1] and dif[i] > dea[i]:
            position = 1
            buy_price = data[i]['收盘']
        
        # 死叉卖出
        elif position == 1 and dif[i-1] >= dea[i-1] and dif[i] < dea[i]:
            sell_price = data[i]['收盘']
            profit = (sell_price - buy_price) / buy_price
            trades.append(profit)
            position = 0
    
    if position == 1:
        sell_price = data[-1]['收盘']
        profit = (sell_price - buy_price) / buy_price
        trades.append(profit)
    
    return trades


def strategy_rsi(data):
    """
    方案一：RSI 策略
    买入：RSI < 30 (超卖)
    卖出：RSI > 70 (超买)
    """
    rsi = calc_rsi(data)
    
    trades = []
    position = 0
    buy_price = 0
    
    for i in range(20, len(data)):
        if rsi[i] is None:
            continue
        
        # 超卖买入
        if position == 0 and rsi[i] < 30:
            position = 1
            buy_price = data[i]['收盘']
        
        # 超买卖出
        elif position == 1 and rsi[i] > 70:
            sell_price = data[i]['收盘']
            profit = (sell_price - buy_price) / buy_price
            trades.append(profit)
            position = 0
    
    if position == 1:
        sell_price = data[-1]['收盘']
        profit = (sell_price - buy_price) / buy_price
        trades.append(profit)
    
    return trades


# ============== 方案二：多因子策略 ==============

def strategy_multi_factor(data):
    """
    方案二：多因子策略
    因子：MA20 趋势 + 成交量 + 动量
    买入：MA20 向上 + 成交量放大 + 近期动量强
    卖出：MA20 向下 + 成交量萎缩
    """
    ma20 = calc_ma(data, 20)
    ma60 = calc_ma(data, 60)
    
    trades = []
    position = 0
    buy_price = 0
    
    for i in range(60, len(data)):
        if ma20[i] is None or ma60[i] is None:
            continue
        
        # 计算成交量均线
        vol_ma20 = sum([d['成交量'] for d in data[i-20:i]]) / 20
        
        # 买入条件：MA20>MA60 + 成交量放大 + 价格上涨
        if position == 0:
            if (ma20[i] > ma60[i] and 
                data[i]['成交量'] > vol_ma20 * 1.5 and
                data[i]['收盘'] > data[i-5]['收盘'] * 1.02):
                position = 1
                buy_price = data[i]['收盘']
        
        # 卖出条件：MA20<MA60 或 亏损>10%
        elif position == 1:
            sell_price = data[i]['收盘']
            if ma20[i] < ma60[i] or (sell_price - buy_price) / buy_price < -0.10:
                profit = (sell_price - buy_price) / buy_price
                trades.append(profit)
                position = 0
    
    if position == 1:
        sell_price = data[-1]['收盘']
        profit = (sell_price - buy_price) / buy_price
        trades.append(profit)
    
    return trades


# ============== 方案三：缠论 + 蜡烛图策略 ==============

def detect_fractal(data, window=5):
    """检测分型（简化版）"""
    top_fractals = []
    bottom_fractals = []
    
    for i in range(window, len(data) - window):
        highs = [data[i+j]['最高'] for j in range(-window, window+1)]
        lows = [data[i+j]['最低'] for j in range(-window, window+1)]
        
        # 顶分型
        if data[i]['最高'] == max(highs):
            top_fractals.append(i)
        
        # 底分型
        if data[i]['最低'] == min(lows):
            bottom_fractals.append(i)
    
    return top_fractals, bottom_fractals


def detect_candlestick_pattern(data, i):
    """检测蜡烛图形态（简化版）"""
    o = data[i]['开盘']
    h = data[i]['最高']
    l = data[i]['最低']
    c = data[i]['收盘']
    
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    
    # 锤头线
    if lower > body * 2 and upper < body * 0.5:
        return 'hammer'
    
    # 射击之星
    if upper > body * 2 and lower < body * 0.5:
        return 'shooting_star'
    
    # 大阳线
    if body > (h - l) * 0.7 and c > o:
        return 'big_bull'
    
    # 大阴线
    if body > (h - l) * 0.7 and c < o:
        return 'big_bear'
    
    return None


def strategy_chanlun_candle(data):
    """
    方案三：缠论 + 蜡烛图策略
    买入：底分型 + 锤头线/大阳线
    卖出：顶分型 + 射击之星/大阴线
    """
    top_fractals, bottom_fractals = detect_fractal(data)
    
    trades = []
    position = 0
    buy_price = 0
    
    for i in range(10, len(data)):
        pattern = detect_candlestick_pattern(data, i)
        
        # 买入：底分型 + 看涨蜡烛
        if position == 0 and i in bottom_fractals:
            if pattern in ['hammer', 'big_bull']:
                position = 1
                buy_price = data[i]['收盘']
        
        # 卖出：顶分型 + 看跌蜡烛
        elif position == 1 and i in top_fractals:
            if pattern in ['shooting_star', 'big_bear']:
                sell_price = data[i]['收盘']
                profit = (sell_price - buy_price) / buy_price
                trades.append(profit)
                position = 0
    
    if position == 1:
        sell_price = data[-1]['收盘']
        profit = (sell_price - buy_price) / buy_price
        trades.append(profit)
    
    return trades


# ============== 方案四：简化机器学习策略 ==============

def strategy_ml_simple(data):
    """
    方案四：简化机器学习策略
    使用规则模拟 ML 预测：
    - 特征：MA5/MA20 比值、RSI、成交量变化、动量
    - 规则：基于历史数据训练的简化规则
    """
    ma5 = calc_ma(data, 5)
    ma20 = calc_ma(data, 20)
    rsi = calc_rsi(data)
    
    trades = []
    position = 0
    buy_price = 0
    
    for i in range(30, len(data)):
        if ma5[i] is None or ma20[i] is None or rsi[i] is None:
            continue
        
        # 计算特征
        ma_ratio = ma5[i] / ma20[i] if ma20[i] > 0 else 1
        vol_change = data[i]['成交量'] / sum([data[i-j]['成交量'] for j in range(1, 6)]) * 5 if i >= 5 else 1
        momentum = (data[i]['收盘'] - data[i-10]['收盘']) / data[i-10]['收盘'] if i >= 10 else 0
        
        # 简化"ML"规则（模拟训练后的决策边界）
        score = 0
        if ma_ratio > 1.02: score += 1
        if rsi[i] < 40: score += 1
        if vol_change > 1.2: score += 1
        if momentum > 0.05: score += 1
        
        # 买入：得分>=3
        if position == 0 and score >= 3:
            position = 1
            buy_price = data[i]['收盘']
        
        # 卖出：得分<=1 或 止损
        elif position == 1:
            sell_price = data[i]['收盘']
            current_score = 0
            if ma_ratio > 1.02: current_score += 1
            if rsi[i] < 40: current_score += 1
            
            if current_score <= 1 or (sell_price - buy_price) / buy_price < -0.08:
                profit = (sell_price - buy_price) / buy_price
                trades.append(profit)
                position = 0
    
    if position == 1:
        sell_price = data[-1]['收盘']
        profit = (sell_price - buy_price) / buy_price
        trades.append(profit)
    
    return trades


# ============== 回测评估 ==============

def evaluate_trades(trades, initial_capital=100000):
    """评估交易结果"""
    if not trades:
        return {
            'total_return': 0,
            'annual_return': 0,
            'sharpe': 0,
            'max_drawdown': 0,
            'win_rate': 0,
            'trade_count': 0
        }
    
    # 提取利润值（处理字典和嵌套）
    profits = []
    for t in trades:
        if isinstance(t, dict):
            if 'profit' in t:
                profits.append(t['profit'])
        elif isinstance(t, list):
            profits.extend(t)
        elif isinstance(t, (int, float)):
            profits.append(t)
    
    if not profits:
        return {
            'total_return': 0,
            'annual_return': 0,
            'sharpe': 0,
            'max_drawdown': 0,
            'win_rate': 0,
            'trade_count': 0
        }
    
    trades = profits
    
    # 总收益
    total_return = 1
    for t in trades:
        total_return *= (1 + t)
    total_return -= 1
    
    # 年化收益（假设 252 个交易日）
    n_trades = len(trades)
    avg_hold_days = 252 / max(n_trades, 1)
    annual_return = (1 + total_return) ** (252 / avg_hold_days / max(n_trades, 1)) - 1
    
    # 胜率
    wins = [t for t in trades if t > 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    
    # 夏普比率（简化）
    if len(trades) > 1:
        avg_return = np.mean(trades)
        std_return = np.std(trades)
        sharpe = (avg_return / std_return * np.sqrt(252)) if std_return > 0 else 0
    else:
        sharpe = 0
    
    # 最大回撤（简化）
    cumulative = [1]
    for t in trades:
        cumulative.append(cumulative[-1] * (1 + t))
    
    peak = 0
    max_dd = 0
    for v in cumulative:
        if v > peak:
            peak = v
        dd = (peak - v) / peak
        if dd > max_dd:
            max_dd = dd
    
    return {
        'total_return': total_return * 100,
        'annual_return': annual_return * 100,
        'sharpe': sharpe,
        'max_drawdown': max_dd * 100,
        'win_rate': win_rate,
        'trade_count': n_trades
    }


def backtest_all_strategies(stocks):
    """对所有股票进行回测"""
    results = {
        'ma_cross': [],
        'macd': [],
        'rsi': [],
        'multi_factor': [],
        'chanlun_candle': [],
        'ml_simple': []
    }
    
    for i, symbol in enumerate(stocks):
        data = load_stock_data(symbol)
        if not data or len(data) < 100:
            continue
        
        # 方案一：技术指标
        trades_result = strategy_ma_cross(data)
        trades = trades_result[0] if isinstance(trades_result, tuple) else trades_result
        results['ma_cross'].append(evaluate_trades(trades))
        
        trades = strategy_macd(data)
        results['macd'].append(evaluate_trades(trades))
        
        trades = strategy_rsi(data)
        results['rsi'].append(evaluate_trades(trades))
        
        # 方案二：多因子
        trades = strategy_multi_factor(data)
        results['multi_factor'].append(evaluate_trades(trades))
        
        # 方案三：缠论 + 蜡烛图
        trades = strategy_chanlun_candle(data)
        results['chanlun_candle'].append(evaluate_trades(trades))
        
        # 方案四：简化 ML
        trades = strategy_ml_simple(data)
        results['ml_simple'].append(evaluate_trades(trades))
        
        if (i + 1) % 20 == 0:
            print(f"  已回测：{i+1}/{len(stocks)}")
    
    return results


def aggregate_results(results):
    """汇总结果"""
    summary = {}
    
    for strategy, evals in results.items():
        valid_evals = [e for e in evals if e['trade_count'] > 0]
        
        if valid_evals:
            summary[strategy] = {
                'avg_total_return': np.mean([e['total_return'] for e in valid_evals]),
                'avg_annual_return': np.mean([e['annual_return'] for e in valid_evals]),
                'avg_sharpe': np.mean([e['sharpe'] for e in valid_evals]),
                'avg_max_drawdown': np.mean([e['max_drawdown'] for e in valid_evals]),
                'avg_win_rate': np.mean([e['win_rate'] for e in valid_evals]),
                'avg_trade_count': np.mean([e['trade_count'] for e in valid_evals]),
                'stock_count': len(valid_evals)
            }
        else:
            summary[strategy] = {
                'avg_total_return': 0,
                'avg_annual_return': 0,
                'avg_sharpe': 0,
                'avg_max_drawdown': 0,
                'avg_win_rate': 0,
                'avg_trade_count': 0,
                'stock_count': 0
            }
    
    return summary


def print_report(summary):
    """打印报告"""
    print("\n" + "=" * 100)
    print("四大选股策略回测对比分析报告")
    print("=" * 100)
    
    print(f"\n{'策略':<20} {'总收益%':<12} {'年化%':<12} {'夏普':<10} {'回撤%':<12} {'胜率%':<10} {'交易次数':<10}")
    print("-" * 100)
    
    strategy_names = {
        'ma_cross': '均线交叉',
        'macd': 'MACD',
        'rsi': 'RSI 超买超卖',
        'multi_factor': '多因子',
        'chanlun_candle': '缠论 + 蜡烛图',
        'ml_simple': '简化 ML'
    }
    
    for strategy, name in strategy_names.items():
        s = summary[strategy]
        print(f"{name:<20} {s['avg_total_return']:>10.2f} {s['avg_annual_return']:>10.2f} {s['avg_sharpe']:>8.2f} {s['avg_max_drawdown']:>10.2f} {s['avg_win_rate']:>8.2f} {s['avg_trade_count']:>8.1f}")
    
    print("=" * 100)
    
    # 排名
    print("\n📊 策略排名（按夏普比率）:")
    ranked = sorted(summary.items(), key=lambda x: x[1]['avg_sharpe'], reverse=True)
    for i, (strategy, s) in enumerate(ranked, 1):
        print(f"  {i}. {strategy_names[strategy]}: 夏普={s['avg_sharpe']:.2f}")
    
    print("\n📊 策略排名（按年化收益）:")
    ranked = sorted(summary.items(), key=lambda x: x[1]['avg_annual_return'], reverse=True)
    for i, (strategy, s) in enumerate(ranked, 1):
        print(f"  {i}. {strategy_names[strategy]}: 年化={s['avg_annual_return']:.2f}%")
    
    print("=" * 100)


def main():
    print("=" * 100)
    print("四大选股策略抽样回测对比分析")
    print("=" * 100)
    
    # 抽样
    print("\n[1/4] 抽样股票...")
    stocks = sample_stocks(200)
    print(f"   抽样数量：{len(stocks)} 只")
    
    # 回测
    print("\n[2/4] 开始回测...")
    results = backtest_all_strategies(stocks)
    
    # 汇总
    print("\n[3/4] 汇总结果...")
    summary = aggregate_results(results)
    
    # 报告
    print("\n[4/4] 生成报告...\n")
    print_report(summary)
    
    # 保存报告
    report = {
        'time': datetime.now().isoformat(),
        'sample_size': len(stocks),
        'strategies': summary
    }
    
    report_file = REPORT_DIR / f'strategy_comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 报告已保存：{report_file}")
    
    return summary


if __name__ == '__main__':
    main()
