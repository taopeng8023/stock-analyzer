#!/usr/bin/env python3
"""
立讯精密 (002475) K 线数据回测分析

策略：
1. 均线交叉策略 (MA5/MA20)
2. 突破策略 (20 日新高)
3. RSI 超卖策略
"""

import json
import sys
from datetime import datetime

# 加载 K 线数据
with open('backtest_data/luxshare_kline.json') as f:
    klines = json.load(f)

# 数据处理
for k in klines:
    k['open'] = float(k['open'])
    k['close'] = float(k['close'])
    k['high'] = float(k['high'])
    k['low'] = float(k['low'])
    k['volume'] = int(k['volume'])
    k['change'] = float(k.get('change', 0))

print('='*80)
print('立讯精密 (002475) - 策略回测分析')
print('='*80)
print(f'数据范围：{klines[0]["day"]} 至 {klines[-1]["day"]} ({len(klines)} 条)')
print()

# ========== 策略 1: 均线交叉 (MA5/MA20) ==========
print('-'*80)
print('【策略 1】均线交叉策略 (MA5 上穿 MA20 买入，下穿卖出)')
print('-'*80)

def calc_ma(data, period, idx):
    if idx < period - 1:
        return None
    return sum(data[i]['close'] for i in range(idx-period+1, idx+1)) / period

initial_capital = 100000
capital = initial_capital
shares = 0
trades = []
holding = False
buy_price = 0

for i in range(20, len(klines)):
    ma5 = calc_ma(klines, 5, i)
    ma20 = calc_ma(klines, 20, i)
    ma5_prev = calc_ma(klines, 5, i-1)
    ma20_prev = calc_ma(klines, 20, i-1)
    
    if ma5 is None or ma20 is None:
        continue
    
    # 金叉买入
    if not holding and ma5_prev <= ma20_prev and ma5 > ma20:
        shares = int(capital * 0.95 / klines[i]['close'] / 100) * 100
        if shares > 0:
            cost = shares * klines[i]['close']
            capital -= cost
            holding = True
            buy_price = klines[i]['close']
            trades.append({
                'date': klines[i]['day'],
                'type': '买入',
                'price': buy_price,
                'shares': shares,
                'ma5': ma5,
                'ma20': ma20
            })
    
    # 死叉卖出
    elif holding and ma5_prev >= ma20_prev and ma5 < ma20:
        revenue = shares * klines[i]['close']
        capital += revenue
        profit = (klines[i]['close'] - buy_price) / buy_price * 100
        trades.append({
            'date': klines[i]['day'],
            'type': '卖出',
            'price': klines[i]['close'],
            'shares': shares,
            'profit': profit,
            'ma5': ma5,
            'ma20': ma20
        })
        shares = 0
        holding = False

# 如果还持有，按最后价格计算
if holding:
    final_value = capital + shares * klines[-1]['close']
else:
    final_value = capital

total_return = ((final_value / initial_capital) - 1) * 100

print(f'初始资金：¥{initial_capital:,.0f}')
print(f'最终资产：¥{final_value:,.0f}')
print(f'总收益率：{total_return:+.2f}%')
print(f'交易次数：{len(trades)} 次')
print(f'持仓状态：{"持有中" if holding else "空仓"}')

# 计算胜率
buy_trades = [t for t in trades if t['type'] == '买入']
sell_trades = [t for t in trades if t['type'] == '卖出']
winning_trades = [t for t in sell_trades if t.get('profit', 0) > 0]

if sell_trades:
    win_rate = len(winning_trades) / len(sell_trades) * 100
    avg_profit = sum(t.get('profit', 0) for t in sell_trades) / len(sell_trades)
    print(f'胜率：{win_rate:.1f}% ({len(winning_trades)}/{len(sell_trades)})')
    print(f'平均盈亏：{avg_profit:+.2f}%')

print()
print('交易记录:')
for t in trades[-10:]:
    if t['type'] == '买入':
        print(f"  {t['date']} 买入 ¥{t['price']:.2f} × {t['shares']} 股 (MA5={t['ma5']:.2f}, MA20={t['ma20']:.2f})")
    else:
        print(f"  {t['date']} 卖出 ¥{t['price']:.2f} × {t['shares']} 股 盈亏{t.get('profit', 0):+.2f}%")

# ========== 策略 2: 20 日突破策略 ==========
print()
print('-'*80)
print('【策略 2】20 日突破策略 (突破 20 日新高买入，跌破 10 日新低卖出)')
print('-'*80)

capital = initial_capital
shares = 0
holding = False
buy_price = 0
trades2 = []

for i in range(20, len(klines)):
    high_20 = max(klines[j]['high'] for j in range(i-20, i+1))
    low_10 = min(klines[j]['low'] for j in range(i-10, i+1))
    
    # 突破买入
    if not holding and klines[i]['close'] >= high_20:
        shares = int(capital * 0.95 / klines[i]['close'] / 100) * 100
        if shares > 0:
            cost = shares * klines[i]['close']
            capital -= cost
            holding = True
            buy_price = klines[i]['close']
            trades2.append({
                'date': klines[i]['day'],
                'type': '买入',
                'price': buy_price,
                'shares': shares,
                'signal': f'突破 20 日高点{high_20:.2f}'
            })
    
    # 跌破卖出
    elif holding and klines[i]['close'] <= low_10:
        revenue = shares * klines[i]['close']
        capital += revenue
        profit = (klines[i]['close'] - buy_price) / buy_price * 100
        trades2.append({
            'date': klines[i]['day'],
            'type': '卖出',
            'price': klines[i]['close'],
            'shares': shares,
            'profit': profit,
            'signal': f'跌破 10 日低点{low_10:.2f}'
        })
        shares = 0
        holding = False

if holding:
    final_value2 = capital + shares * klines[-1]['close']
else:
    final_value2 = capital

total_return2 = ((final_value2 / initial_capital) - 1) * 100

print(f'初始资金：¥{initial_capital:,.0f}')
print(f'最终资产：¥{final_value2:,.0f}')
print(f'总收益率：{total_return2:+.2f}%')
print(f'交易次数：{len(trades2)} 次')

sell_trades2 = [t for t in trades2 if t['type'] == '卖出']
winning_trades2 = [t for t in sell_trades2 if t.get('profit', 0) > 0]
if sell_trades2:
    win_rate2 = len(winning_trades2) / len(sell_trades2) * 100
    avg_profit2 = sum(t.get('profit', 0) for t in sell_trades2) / len(sell_trades2)
    print(f'胜率：{win_rate2:.1f}%')
    print(f'平均盈亏：{avg_profit2:+.2f}%')

# ========== 策略 3: 持有不动 ==========
print()
print('-'*80)
print('【基准】持有不动策略')
print('-'*80)
buy_and_hold_return = ((klines[-1]['close'] / klines[0]['close']) - 1) * 100
print(f'买入价格：¥{klines[0]["close"]:.2f} ({klines[0]["day"]})')
print(f'卖出价格：¥{klines[-1]["close"]:.2f} ({klines[-1]["day"]})')
print(f'总收益率：{buy_and_hold_return:+.2f}%')

# ========== 对比总结 ==========
print()
print('='*80)
print('【策略对比】')
print('='*80)
print(f'{"策略":<20} {"收益率":>12} {"交易次数":>12} {"胜率":>10}')
print('-'*80)
print(f'{"均线交叉策略":<20} {total_return:>11.2f}% {len(trades):>12} {"-":>10}')
print(f'{"20 日突破策略":<20} {total_return2:>11.2f}% {len(trades2):>12} {"-":>10}')
print(f'{"持有不动基准":<20} {buy_and_hold_return:>11.2f}% {"-":>12} {"-":>10}')
print('='*80)

# 最佳策略
strategies = [
    ('均线交叉策略', total_return),
    ('20 日突破策略', total_return2),
    ('持有不动基准', buy_and_hold_return)
]
best = max(strategies, key=lambda x: x[1])
print(f'\n🏆 最佳策略：{best[0]} (收益率 {best[1]:+.2f}%)')
print('='*80)
