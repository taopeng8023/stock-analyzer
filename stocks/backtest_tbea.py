#!/usr/bin/env python3
"""
特变电工 (600089) 多策略回测分析

策略列表:
1. 均线交叉 (MA5/MA20)
2. 双均线 (MA10/MA30)
3. MACD 策略
4. RSI 超买超卖策略
5. 布林带策略
6. 成交量突破策略
7. 海龟交易法则
8. 持有不动基准
"""

import json
import math

# ========== 数据加载 ==========
with open('backtest_data/tbea_kline.json') as f:
    klines = json.load(f)

# 数据处理
for k in klines:
    k['open'] = float(k['open'])
    k['close'] = float(k['close'])
    k['high'] = float(k['high'])
    k['low'] = float(k['low'])
    k['volume'] = int(k['volume'])

# 计算涨跌幅
for i in range(1, len(klines)):
    klines[i]['change'] = ((klines[i]['close'] - klines[i-1]['close']) / klines[i-1]['close']) * 100

INITIAL_CAPITAL = 100000
COMMISSION = 0.0003
SLIPPAGE = 0.001

print('='*90)
print('特变电工 (600089) - 多策略回测分析')
print('='*90)
print(f'数据范围：{klines[0]["day"]} 至 {klines[-1]["day"]} ({len(klines)} 条)')
print(f'初始资金：¥{INITIAL_CAPITAL:,.0f} | 手续费：万三 | 滑点：0.1%')
print()


# ========== 辅助函数 ==========

def calc_ma(data, period, idx):
    if idx < period - 1:
        return None
    return sum(data[i]['close'] for i in range(idx-period+1, idx+1)) / period

def calc_ema(data, period, idx):
    if idx < period - 1:
        return None
    multiplier = 2 / (period + 1)
    ema = data[idx-period+1]['close']
    for i in range(idx-period+2, idx+1):
        ema = (data[i]['close'] - ema) * multiplier + ema
    return ema

def calc_macd(data, fast=12, slow=26, signal=9, idx=None):
    if idx is None:
        idx = len(data) - 1
    if idx < slow + signal - 1:
        return None, None, None
    
    ema_fast = calc_ema(data, fast, idx)
    ema_slow = calc_ema(data, slow, idx)
    if ema_fast is None or ema_slow is None:
        return None, None, None
    
    macd_line = ema_fast - ema_slow
    
    macd_values = []
    for i in range(slow-1, idx+1):
        ef = calc_ema(data, fast, i)
        es = calc_ema(data, slow, i)
        if ef and es:
            macd_values.append(ef - es)
    
    if len(macd_values) < signal:
        return None, None, None
    
    signal_line = sum(macd_values[-signal:]) / signal
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calc_rsi(data, period=14, idx=None):
    if idx is None:
        idx = len(data) - 1
    if idx < period:
        return None
    
    gains = []
    losses = []
    for i in range(idx-period+1, idx+1):
        change = data[i]['close'] - data[i-1]['close']
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calc_bollinger(data, period=20, std_dev=2, idx=None):
    if idx is None:
        idx = len(data) - 1
    if idx < period - 1:
        return None, None, None
    
    ma = calc_ma(data, period, idx)
    prices = [data[i]['close'] for i in range(idx-period+1, idx+1)]
    variance = sum((p - ma) ** 2 for p in prices) / period
    std = math.sqrt(variance)
    
    upper = ma + (std_dev * std)
    lower = ma - (std_dev * std)
    
    return upper, ma, lower

def calc_atr(data, period=14, idx=None):
    if idx is None:
        idx = len(data) - 1
    if idx < period:
        return None
    
    tr_values = []
    for i in range(idx-period+1, idx+1):
        high = data[i]['high']
        low = data[i]['low']
        prev_close = data[i-1]['close']
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_values.append(tr)
    
    return sum(tr_values) / period


# ========== 策略执行函数 ==========

def run_strategy(name, strategy_func):
    capital, shares, trades = strategy_func()
    
    if shares > 0:
        final_value = capital + shares * klines[-1]['close'] * (1 - COMMISSION)
    else:
        final_value = capital
    
    total_return = ((final_value / INITIAL_CAPITAL) - 1) * 100
    
    buy_count = len([t for t in trades if t['type'] == '买入'])
    sell_count = len([t for t in trades if t['type'] == '卖出'])
    winning_trades = len([t for t in trades if t['type'] == '卖出' and t.get('profit', 0) > 0])
    
    print(f'最终资产：¥{final_value:,.0f}')
    print(f'总收益率：{total_return:+.2f}%')
    print(f'交易次数：{len(trades)} 次 (买入{buy_count}/卖出{sell_count})')
    
    if sell_count > 0:
        win_rate = winning_trades / sell_count * 100
        avg_profit = sum(t.get('profit', 0) for t in trades if t['type'] == '卖出') / sell_count
        print(f'胜率：{win_rate:.1f}% ({winning_trades}/{sell_count})')
        print(f'平均盈亏：{avg_profit:+.2f}%')
    
    if trades:
        print('\n最近交易记录:')
        for t in trades[-6:]:
            if t['type'] == '买入':
                print(f"  {t['date']} 买入 ¥{t['price']:.2f} × {t['shares']} 股")
            else:
                print(f"  {t['date']} 卖出 ¥{t['price']:.2f} × {t['shares']} 股 盈亏{t.get('profit', 0):+.2f}%")
    
    print()
    return total_return, len(trades)


# ========== 策略 1: 均线交叉 (MA5/MA20) ==========
def strategy_ma_cross():
    capital = INITIAL_CAPITAL
    shares = 0
    trades = []
    holding = False
    buy_price = 0
    
    for i in range(20, len(klines)):
        ma5 = calc_ma(klines, 5, i)
        ma20 = calc_ma(klines, 20, i)
        ma5_prev = calc_ma(klines, 5, i-1)
        ma20_prev = calc_ma(klines, 20, i-1)
        
        if None in (ma5, ma20, ma5_prev, ma20_prev):
            continue
        
        if not holding and ma5_prev <= ma20_prev and ma5 > ma20:
            buy_price = klines[i]['close'] * (1 + SLIPPAGE)
            shares = int(capital * 0.95 / buy_price / 100) * 100
            if shares > 0:
                cost = shares * buy_price * (1 + COMMISSION)
                capital -= cost
                holding = True
                trades.append({'date': klines[i]['day'], 'type': '买入', 'price': buy_price, 'shares': shares})
        
        elif holding and ma5_prev >= ma20_prev and ma5 < ma20:
            sell_price = klines[i]['close'] * (1 - SLIPPAGE)
            revenue = shares * sell_price * (1 - COMMISSION)
            capital += revenue
            profit = ((sell_price - buy_price) / buy_price) * 100
            trades.append({'date': klines[i]['day'], 'type': '卖出', 'price': sell_price, 'shares': shares, 'profit': profit})
            shares = 0
            holding = False
    
    return capital, shares, trades


# ========== 策略 2: 双均线 (MA10/MA30) ==========
def strategy_double_ma():
    capital = INITIAL_CAPITAL
    shares = 0
    trades = []
    holding = False
    buy_price = 0
    
    for i in range(30, len(klines)):
        ma10 = calc_ma(klines, 10, i)
        ma30 = calc_ma(klines, 30, i)
        ma10_prev = calc_ma(klines, 10, i-1)
        ma30_prev = calc_ma(klines, 30, i-1)
        
        if None in (ma10, ma30, ma10_prev, ma30_prev):
            continue
        
        if not holding and ma10_prev <= ma30_prev and ma10 > ma30:
            buy_price = klines[i]['close'] * (1 + SLIPPAGE)
            shares = int(capital * 0.95 / buy_price / 100) * 100
            if shares > 0:
                cost = shares * buy_price * (1 + COMMISSION)
                capital -= cost
                holding = True
                trades.append({'date': klines[i]['day'], 'type': '买入', 'price': buy_price, 'shares': shares})
        
        elif holding and ma10_prev >= ma30_prev and ma10 < ma30:
            sell_price = klines[i]['close'] * (1 - SLIPPAGE)
            revenue = shares * sell_price * (1 - COMMISSION)
            capital += revenue
            profit = ((sell_price - buy_price) / buy_price) * 100
            trades.append({'date': klines[i]['day'], 'type': '卖出', 'price': sell_price, 'shares': shares, 'profit': profit})
            shares = 0
            holding = False
    
    return capital, shares, trades


# ========== 策略 3: MACD 策略 ==========
def strategy_macd():
    capital = INITIAL_CAPITAL
    shares = 0
    trades = []
    holding = False
    buy_price = 0
    
    for i in range(35, len(klines)):
        macd, signal, hist = calc_macd(klines, idx=i)
        macd_prev, signal_prev, hist_prev = calc_macd(klines, idx=i-1)
        
        if None in (macd, signal, macd_prev, signal_prev):
            continue
        
        if not holding and macd_prev <= signal_prev and macd > signal:
            buy_price = klines[i]['close'] * (1 + SLIPPAGE)
            shares = int(capital * 0.95 / buy_price / 100) * 100
            if shares > 0:
                cost = shares * buy_price * (1 + COMMISSION)
                capital -= cost
                holding = True
                trades.append({'date': klines[i]['day'], 'type': '买入', 'price': buy_price, 'shares': shares})
        
        elif holding and macd_prev >= signal_prev and macd < signal:
            sell_price = klines[i]['close'] * (1 - SLIPPAGE)
            revenue = shares * sell_price * (1 - COMMISSION)
            capital += revenue
            profit = ((sell_price - buy_price) / buy_price) * 100
            trades.append({'date': klines[i]['day'], 'type': '卖出', 'price': sell_price, 'shares': shares, 'profit': profit})
            shares = 0
            holding = False
    
    return capital, shares, trades


# ========== 策略 4: RSI 超买超卖策略 ==========
def strategy_rsi():
    capital = INITIAL_CAPITAL
    shares = 0
    trades = []
    holding = False
    buy_price = 0
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    
    for i in range(15, len(klines)):
        rsi = calc_rsi(klines, 14, i)
        
        if rsi is None:
            continue
        
        if not holding and rsi < RSI_OVERSOLD:
            buy_price = klines[i]['close'] * (1 + SLIPPAGE)
            shares = int(capital * 0.95 / buy_price / 100) * 100
            if shares > 0:
                cost = shares * buy_price * (1 + COMMISSION)
                capital -= cost
                holding = True
                trades.append({'date': klines[i]['day'], 'type': '买入', 'price': buy_price, 'shares': shares})
        
        elif holding and rsi > RSI_OVERBOUGHT:
            sell_price = klines[i]['close'] * (1 - SLIPPAGE)
            revenue = shares * sell_price * (1 - COMMISSION)
            capital += revenue
            profit = ((sell_price - buy_price) / buy_price) * 100
            trades.append({'date': klines[i]['day'], 'type': '卖出', 'price': sell_price, 'shares': shares, 'profit': profit})
            shares = 0
            holding = False
    
    return capital, shares, trades


# ========== 策略 5: 布林带策略 ==========
def strategy_bollinger():
    capital = INITIAL_CAPITAL
    shares = 0
    trades = []
    holding = False
    buy_price = 0
    
    for i in range(20, len(klines)):
        upper, middle, lower = calc_bollinger(klines, 20, 2, i)
        
        if None in (upper, middle, lower):
            continue
        
        close = klines[i]['close']
        
        if not holding and close <= lower:
            buy_price = klines[i]['close'] * (1 + SLIPPAGE)
            shares = int(capital * 0.95 / buy_price / 100) * 100
            if shares > 0:
                cost = shares * buy_price * (1 + COMMISSION)
                capital -= cost
                holding = True
                trades.append({'date': klines[i]['day'], 'type': '买入', 'price': buy_price, 'shares': shares})
        
        elif holding and close >= upper:
            sell_price = klines[i]['close'] * (1 - SLIPPAGE)
            revenue = shares * sell_price * (1 - COMMISSION)
            capital += revenue
            profit = ((sell_price - buy_price) / buy_price) * 100
            trades.append({'date': klines[i]['day'], 'type': '卖出', 'price': sell_price, 'shares': shares, 'profit': profit})
            shares = 0
            holding = False
    
    return capital, shares, trades


# ========== 策略 6: 成交量突破策略 ==========
def strategy_volume_break():
    capital = INITIAL_CAPITAL
    shares = 0
    trades = []
    holding = False
    buy_price = 0
    
    for i in range(20, len(klines)):
        avg_volume = sum(klines[j]['volume'] for j in range(i-20, i)) / 20
        curr_volume = klines[i]['volume']
        volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 0
        change = klines[i]['change']
        
        if not holding and volume_ratio > 2.0 and change > 3.0:
            buy_price = klines[i]['close'] * (1 + SLIPPAGE)
            shares = int(capital * 0.95 / buy_price / 100) * 100
            if shares > 0:
                cost = shares * buy_price * (1 + COMMISSION)
                capital -= cost
                holding = True
                trades.append({'date': klines[i]['day'], 'type': '买入', 'price': buy_price, 'shares': shares})
        
        elif holding and change < -5.0:
            sell_price = klines[i]['close'] * (1 - SLIPPAGE)
            revenue = shares * sell_price * (1 - COMMISSION)
            capital += revenue
            profit = ((sell_price - buy_price) / buy_price) * 100
            trades.append({'date': klines[i]['day'], 'type': '卖出', 'price': sell_price, 'shares': shares, 'profit': profit})
            shares = 0
            holding = False
    
    return capital, shares, trades


# ========== 策略 7: 海龟交易法则 ==========
def strategy_turtle():
    capital = INITIAL_CAPITAL
    shares = 0
    trades = []
    holding = False
    buy_price = 0
    N = 20
    
    for i in range(N, len(klines)):
        high_N = max(klines[j]['high'] for j in range(i-N, i))
        low_N = min(klines[j]['low'] for j in range(i-N, i))
        atr = calc_atr(klines, 14, i)
        
        if atr is None or atr == 0:
            continue
        
        close = klines[i]['close']
        
        if not holding and close > high_N:
            entry_price = close * (1 + SLIPPAGE)
            risk_per_trade = capital * 0.01
            units = int(risk_per_trade / (atr * 100))
            units = max(units, 1) * 100
            shares = units
            cost = shares * entry_price * (1 + COMMISSION)
            if cost <= capital * 0.95:
                capital -= cost
                holding = True
                buy_price = entry_price
                trades.append({'date': klines[i]['day'], 'type': '买入', 'price': entry_price, 'shares': shares})
        
        elif holding and close < low_N:
            sell_price = close * (1 - SLIPPAGE)
            revenue = shares * sell_price * (1 - COMMISSION)
            capital += revenue
            profit = ((sell_price - buy_price) / buy_price) * 100
            trades.append({'date': klines[i]['day'], 'type': '卖出', 'price': sell_price, 'shares': shares, 'profit': profit})
            shares = 0
            holding = False
    
    return capital, shares, trades


# ========== 策略 8: 持有不动基准 ==========
def strategy_buy_hold():
    buy_price = klines[0]['close']
    sell_price = klines[-1]['close']
    shares = int(INITIAL_CAPITAL * 0.95 / buy_price / 100) * 100
    cost = shares * buy_price * (1 + COMMISSION)
    final_value = shares * sell_price * (1 - COMMISSION)
    total_return = ((final_value / (INITIAL_CAPITAL)) - 1) * 100
    return total_return, 1


# ========== 执行所有策略 ==========
results = []

results.append(('均线交叉 (MA5/MA20)', *run_strategy('均线交叉策略 (MA5/MA20)', strategy_ma_cross)))
results.append(('双均线 (MA10/MA30)', *run_strategy('双均线策略 (MA10/MA30)', strategy_double_ma)))
results.append(('MACD 策略', *run_strategy('MACD 策略 (12/26/9)', strategy_macd)))
results.append(('RSI 超买超卖', *run_strategy('RSI 策略 (14 日，30/70)', strategy_rsi)))
results.append(('布林带策略', *run_strategy('布林带策略 (20 日，2 标准差)', strategy_bollinger)))
results.append(('成交量突破', *run_strategy('成交量突破策略', strategy_volume_break)))
results.append(('海龟交易法则', *run_strategy('海龟交易法则 (N=20)', strategy_turtle)))

bh_return, bh_trades = strategy_buy_hold()
print('-'*90)
print('【基准】持有不动策略')
print('-'*90)
print(f'买入价格：¥{klines[0]["close"]:.2f} ({klines[0]["day"]})')
print(f'当前价格：¥{klines[-1]["close"]:.2f} ({klines[-1]["day"]})')
print(f'总收益率：{bh_return:+.2f}%')
print()
results.append(('持有不动基准', bh_return, bh_trades))

# ========== 汇总对比 ==========
print('='*90)
print('【策略汇总对比】')
print('='*90)
print(f'{"策略名称":<20} {"收益率":>12} {"交易次数":>12} {"排名":>8}')
print('-'*90)

sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
for rank, (name, return_val, trades) in enumerate(sorted_results, 1):
    rank_str = f'#{rank}'
    if rank == 1:
        rank_str = '🥇 #1'
    elif rank == 2:
        rank_str = '🥈 #2'
    elif rank == 3:
        rank_str = '🥉 #3'
    print(f'{name:<20} {return_val:>+11.2f}% {trades:>12} {rank_str:>8}')

print('='*90)

best = sorted_results[0]
print(f'\n🏆 最佳策略：{best[0]} (收益率 {best[1]:+.2f}%)')

print('\n⚠️ 风险提示:')
print('  - 历史回测不代表未来表现')
print('  - 未考虑极端行情和黑天鹅事件')
print('  - 实际交易需考虑流动性限制')
print('  - 建议多策略组合分散风险')
print('='*90)
