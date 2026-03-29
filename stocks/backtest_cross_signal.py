#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双均线 + 成交量信号交叉组合回测系统
使用 Tushare 缓存数据，测试多种均线买入信号与成交量卖出信号的组合

买入信号 (双均线金叉):
- MA5/MA20, MA10/MA20, MA10/MA30, MA15/MA20, MA15/MA30, MA20/MA30, MA20/MA60, MA30/MA60

卖出信号 (成交量):
- 缩量止盈：成交量<20 日均量×0.8 且盈利>5%
- 放量滞涨：成交量>20 日均量×2 且涨幅<1%
- 天量见顶：成交量>60 日均量×3
- 量价背离：价格上涨但成交量下降
- 固定止盈：盈利>10% 卖出
- 死叉卖出：双均线死叉
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path
import time
from typing import List, Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# ============== 配置区域 ==============
CACHE_DIR = Path(__file__).parent / 'data_tushare'
RESULTS_DIR = Path(__file__).parent / 'backtest_results'

# 均线组合配置
MA_COMBINATIONS = [
    {'short': 5, 'long': 20, 'name': 'MA5/MA20'},
    {'short': 10, 'long': 20, 'name': 'MA10/MA20'},
    {'short': 10, 'long': 30, 'name': 'MA10/MA30'},
    {'short': 15, 'long': 20, 'name': 'MA15/MA20'},
    {'short': 15, 'long': 30, 'name': 'MA15/MA30'},
    {'short': 20, 'long': 30, 'name': 'MA20/MA30'},
    {'short': 20, 'long': 60, 'name': 'MA20/MA60'},
    {'short': 30, 'long': 60, 'name': 'MA30/MA60'},
]

# 成交量卖出信号配置
VOLUME_EXIT_SIGNALS = [
    {'name': '缩量止盈', 'type': 'shrink_profit', 'params': {'volume_ratio': 0.8, 'min_profit': 0.05}},
    {'name': '放量滞涨', 'type': 'volume_stagnation', 'params': {'volume_ratio': 2.0, 'max_gain': 0.01}},
    {'name': '天量见顶', 'type': 'huge_volume', 'params': {'volume_ratio': 3.0, 'ma_period': 60}},
    {'name': '量价背离', 'type': 'divergence', 'params': {'lookback': 5}},
    {'name': '固定止盈 10%', 'type': 'fixed_profit', 'params': {'profit_target': 0.10}},
    {'name': '固定止盈 15%', 'type': 'fixed_profit', 'params': {'profit_target': 0.15}},
    {'name': '死叉卖出', 'type': 'death_cross', 'params': {}},
]

# 回测参数
DEFAULT_INITIAL_CAPITAL = 100000
DEFAULT_FEE_RATE = 0.0003
SAMPLE_SIZE = 100  # 抽样数量 (加快速度)

# ======================================


def load_stock_data(symbol: str) -> Optional[pd.DataFrame]:
    """从缓存加载股票数据"""
    filepath = CACHE_DIR / f'{symbol}.json'
    
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data or len(data) == 0:
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
        
        return df
        
    except Exception as e:
        return None


class CrossSignalBacktester:
    """交叉信号回测器"""
    
    def __init__(self, initial_capital=DEFAULT_INITIAL_CAPITAL, fee_rate=DEFAULT_FEE_RATE):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
    
    def calc_ma(self, data, period, idx):
        """计算移动平均线"""
        if idx < period - 1:
            return None
        return float(data['close'].iloc[idx-period+1:idx+1].mean())
    
    def check_ma_golden_cross(self, data, idx, short_ma, long_ma):
        """检查均线金叉信号"""
        if idx < long_ma:
            return False
        
        ma_short = self.calc_ma(data, short_ma, idx)
        ma_long = self.calc_ma(data, long_ma, idx)
        ma_short_prev = self.calc_ma(data, short_ma, idx-1)
        ma_long_prev = self.calc_ma(data, long_ma, idx-1)
        
        if ma_short is None or ma_long is None or ma_short_prev is None or ma_long_prev is None:
            return False
        
        return ma_short_prev <= ma_long_prev and ma_short > ma_long
    
    def check_ma_death_cross(self, data, idx, short_ma, long_ma):
        """检查均线死叉信号"""
        if idx < long_ma:
            return False
        
        ma_short = self.calc_ma(data, short_ma, idx)
        ma_long = self.calc_ma(data, long_ma, idx)
        ma_short_prev = self.calc_ma(data, short_ma, idx-1)
        ma_long_prev = self.calc_ma(data, long_ma, idx-1)
        
        if ma_short is None or ma_long is None or ma_short_prev is None or ma_long_prev is None:
            return False
        
        return ma_short_prev >= ma_long_prev and ma_short < ma_long
    
    def check_volume_exit(self, data, idx, exit_signal, buy_price, current_price):
        """检查成交量卖出信号"""
        if idx < 20:
            return False
        
        signal_type = exit_signal['type']
        params = exit_signal['params']
        
        current_volume = float(data['volume'].iloc[idx])
        avg_volume_20 = float(data['volume'].iloc[idx-20:idx].mean())
        
        # 计算盈利
        profit = (current_price - buy_price) / buy_price
        
        # 1. 缩量止盈
        if signal_type == 'shrink_profit':
            if current_volume < avg_volume_20 * params['volume_ratio'] and profit > params['min_profit']:
                return True
        
        # 2. 放量滞涨
        elif signal_type == 'volume_stagnation':
            daily_gain = (current_price - float(data['close'].iloc[idx-1])) / float(data['close'].iloc[idx-1])
            if current_volume > avg_volume_20 * params['volume_ratio'] and daily_gain < params['max_gain']:
                return True
        
        # 3. 天量见顶
        elif signal_type == 'huge_volume':
            ma_period = params.get('ma_period', 60)
            if idx >= ma_period:
                avg_volume_60 = float(data['volume'].iloc[idx-ma_period:idx].mean())
                if current_volume > avg_volume_60 * params['volume_ratio']:
                    return True
        
        # 4. 量价背离
        elif signal_type == 'divergence':
            lookback = params.get('lookback', 5)
            if idx >= lookback:
                price_trend = data['close'].iloc[idx] > data['close'].iloc[idx-lookback]
                volume_trend = data['volume'].iloc[idx] < data['volume'].iloc[idx-lookback]
                if price_trend and volume_trend and profit > 0.05:
                    return True
        
        # 5. 固定止盈
        elif signal_type == 'fixed_profit':
            if profit >= params['profit_target']:
                return True
        
        # 6. 死叉卖出
        elif signal_type == 'death_cross':
            # 需要使用当前回测的均线组合，这里简化处理
            pass
        
        return False
    
    def run_backtest(self, data, ma_combo, exit_signal, print_log=False):
        """运行单次回测"""
        short_ma = ma_combo['short']
        long_ma = ma_combo['long']
        
        initial_capital = self.initial_capital
        current_capital = initial_capital
        position = 0
        buy_price = 0
        buy_date_idx = 0
        
        trades = []
        equity_curve = []
        
        for i in range(long_ma + 20, len(data)):
            current_price = float(data['close'].iloc[i])
            current_date = data['date'].iloc[i]
            
            # 无持仓时检查买入信号
            if position == 0:
                if self.check_ma_golden_cross(data, i, short_ma, long_ma):
                    shares = int(current_capital * 0.95 / current_price / 100) * 100
                    if shares > 0:
                        cost = shares * current_price * (1 + self.fee_rate)
                        current_capital -= cost
                        position = shares
                        buy_price = current_price
                        buy_date_idx = i
                        
                        trades.append({
                            'date': current_date,
                            'type': '买入',
                            'price': current_price,
                            'shares': shares,
                            'ma_combo': ma_combo['name'],
                            'exit_signal': exit_signal['name']
                        })
            
            # 有持仓时检查卖出信号
            elif position > 0:
                should_sell = False
                sell_reason = ''
                
                # 检查成交量卖出信号
                if self.check_volume_exit(data, i, exit_signal, buy_price, current_price):
                    should_sell = True
                    sell_reason = exit_signal['name']
                
                # 检查死叉卖出
                if exit_signal['type'] == 'death_cross':
                    if self.check_ma_death_cross(data, i, short_ma, long_ma):
                        should_sell = True
                        sell_reason = '死叉卖出'
                
                if should_sell:
                    revenue = position * current_price * (1 - self.fee_rate)
                    current_capital += revenue
                    profit = (current_price - buy_price) / buy_price
                    profit_amount = revenue - (position * buy_price * (1 + self.fee_rate))
                    
                    trades.append({
                        'date': current_date,
                        'type': '卖出',
                        'price': current_price,
                        'shares': position,
                        'profit': profit,
                        'profit_amount': profit_amount,
                        'reason': sell_reason,
                        'ma_combo': ma_combo['name'],
                        'exit_signal': exit_signal['name']
                    })
                    
                    position = 0
                    buy_price = 0
            
            # 更新资金曲线
            total_assets = current_capital
            if position > 0:
                total_assets += position * current_price
            
            return_rate = (total_assets - initial_capital) / initial_capital
            equity_curve.append({
                'date': current_date,
                'total_assets': total_assets,
                'return_rate': return_rate,
                'has_position': position > 0
            })
        
        # 处理剩余持仓
        if position > 0:
            last_price = float(data['close'].iloc[-1])
            last_date = data['date'].iloc[-1]
            market_value = position * last_price
            unrealized_profit = (last_price - buy_price) / buy_price
            
            trades.append({
                'date': last_date,
                'type': '持仓',
                'price': last_price,
                'shares': position,
                'market_value': market_value,
                'unrealized_profit': unrealized_profit,
                'ma_combo': ma_combo['name'],
                'exit_signal': exit_signal['name']
            })
        
        # 计算回测指标
        final_value = current_capital
        if position > 0:
            final_value += position * float(data['close'].iloc[-1])
        
        total_return = (final_value - initial_capital) / initial_capital
        
        # 交易统计
        sell_trades = [t for t in trades if t['type'] == '卖出']
        trade_count = len(sell_trades)
        profitable_trades = len([t for t in sell_trades if t['profit'] > 0])
        win_rate = profitable_trades / trade_count * 100 if trade_count > 0 else 0
        
        # 计算最大回撤
        return_rates = [e['return_rate'] for e in equity_curve]
        peak = 0
        max_drawdown = 0
        for r in return_rates:
            assets = initial_capital * (1 + r)
            if assets > peak:
                peak = assets
            drawdown = (peak - assets) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return {
            'ma_combo': ma_combo['name'],
            'exit_signal': exit_signal['name'],
            'total_return': total_return,
            'trade_count': trade_count,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'final_value': final_value,
            'trades': trades
        }


def run_cross_backtest(sample_size=SAMPLE_SIZE):
    """运行交叉组合回测"""
    print("="*80)
    print("双均线 + 成交量信号交叉组合回测")
    print("="*80)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"均线组合数：{len(MA_COMBINATIONS)}")
    print(f"成交量信号数：{len(VOLUME_EXIT_SIGNALS)}")
    print(f"总组合数：{len(MA_COMBINATIONS) * len(VOLUME_EXIT_SIGNALS)}")
    print(f"抽样数量：{sample_size} 只股票")
    print("="*80)
    
    # 获取股票列表
    stock_files = [f.stem for f in CACHE_DIR.glob('*.json') if f.is_file()]
    
    if sample_size and len(stock_files) > sample_size:
        import random
        stock_files = random.sample(stock_files, sample_size)
        print(f"抽样回测：{sample_size} 只股票")
    else:
        print(f"全量回测：{len(stock_files)} 只股票")
    
    # 创建回测器
    backtester = CrossSignalBacktester()
    
    # 存储所有组合结果
    all_results = []
    
    total_combinations = len(MA_COMBINATIONS) * len(VOLUME_EXIT_SIGNALS)
    combo_idx = 0
    
    for ma_combo in MA_COMBINATIONS:
        for exit_signal in VOLUME_EXIT_SIGNALS:
            combo_idx += 1
            print(f"\n[{combo_idx}/{total_combinations}] 测试 {ma_combo['name']} + {exit_signal['name']}")
            
            stock_results = []
            
            for symbol in stock_files:
                data = load_stock_data(symbol)
                if data is None or len(data) < 100:
                    continue
                
                result = backtester.run_backtest(data, ma_combo, exit_signal)
                result['symbol'] = symbol
                stock_results.append(result)
            
            # 统计该组合的表现
            if stock_results:
                avg_return = np.mean([r['total_return'] for r in stock_results])
                avg_win_rate = np.mean([r['win_rate'] for r in stock_results])
                avg_drawdown = np.mean([r['max_drawdown'] for r in stock_results])
                avg_trades = np.mean([r['trade_count'] for r in stock_results])
                profitable_stocks = len([r for r in stock_results if r['total_return'] > 0])
                
                combo_result = {
                    'ma_combo': ma_combo['name'],
                    'exit_signal': exit_signal['name'],
                    'avg_return': avg_return,
                    'avg_win_rate': avg_win_rate,
                    'avg_drawdown': avg_drawdown,
                    'avg_trades': avg_trades,
                    'profitable_stocks': profitable_stocks,
                    'total_stocks': len(stock_results),
                    'profit_ratio': profitable_stocks / len(stock_results) * 100
                }
                
                all_results.append(combo_result)
                print(f"  平均收益：{avg_return*100:.2f}% | 胜率：{avg_win_rate:.1f}% | 回撤：{avg_drawdown*100:.2f}%")
    
    # 生成报告
    print("\n" + "="*80)
    print("生成对比报告...")
    
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 保存详细结果
    results_df = pd.DataFrame(all_results)
    output_file = RESULTS_DIR / f'cross_signal_backtest_{timestamp}.csv'
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"详细结果已保存至：{output_file}")
    
    # 生成 Markdown 报告
    generate_markdown_report(all_results, timestamp)
    
    print(f"\n完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    return all_results


def generate_markdown_report(results, timestamp):
    """生成 Markdown 格式报告"""
    df = pd.DataFrame(results)
    
    # 按平均收益排序
    df_sorted = df.sort_values('avg_return', ascending=False)
    
    report = f"""# 双均线 + 成交量信号交叉组合回测报告

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**数据源**: Tushare 缓存数据  
**抽样数量**: {SAMPLE_SIZE} 只股票  
**回测组合**: {len(MA_COMBINATIONS)} 种均线 × {len(VOLUME_EXIT_SIGNALS)} 种成交量信号 = {len(MA_COMBINATIONS) * len(VOLUME_EXIT_SIGNALS)} 种组合

---

## 📊 买入信号 (双均线金叉)

| 编号 | 组合 | 说明 |
|------|------|------|
"""
    
    for i, ma in enumerate(MA_COMBINATIONS, 1):
        report += f"| {i} | {ma['name']} | MA{ma['short']}上穿 MA{ma['long']} |\n"
    
    report += f"""
## 📉 卖出信号 (成交量)

| 编号 | 信号 | 说明 |
|------|------|------|
"""
    
    for i, sig in enumerate(VOLUME_EXIT_SIGNALS, 1):
        desc = {
            'shrink_profit': f"成交量<20 日均量×{sig['params'].get('volume_ratio', 0.8)} 且盈利>{sig['params'].get('min_profit', 0.05)*100:.0f}%",
            'volume_stagnation': f"成交量>20 日均量×{sig['params'].get('volume_ratio', 2.0)} 且涨幅<{sig['params'].get('max_gain', 0.01)*100:.1f}%",
            'huge_volume': f"成交量>60 日均量×{sig['params'].get('volume_ratio', 3.0)}",
            'divergence': f"价格上涨但成交量下降 (回溯{sig['params'].get('lookback', 5)}日)",
            'fixed_profit': f"盈利>{sig['params'].get('profit_target', 0.10)*100:.0f}% 止盈",
            'death_cross': "双均线死叉"
        }
        report += f"| {i} | {sig['name']} | {desc.get(sig['type'], '')} |\n"
    
    report += f"""
---

## 🏆 Top 20 最佳组合 (按平均收益排序)

| 排名 | 均线组合 | 成交量信号 | 平均收益 | 盈利面 | 胜率 | 回撤 | 交易次数 |
|------|----------|------------|----------|--------|------|------|----------|
"""
    
    for i, (_, row) in enumerate(df_sorted.head(20).iterrows(), 1):
        report += f"| {i} | {row['ma_combo']} | {row['exit_signal']} | **{row['avg_return']*100:.2f}%** | {row['profit_ratio']:.1f}% | {row['avg_win_rate']:.1f}% | {row['avg_drawdown']*100:.2f}% | {row['avg_trades']:.1f}次 |\n"
    
    report += f"""
---

## 📈 均线组合表现对比 (按平均收益排序)

"""
    
    ma_summary = df.groupby('ma_combo').agg({
        'avg_return': 'mean',
        'profit_ratio': 'mean',
        'avg_win_rate': 'mean',
        'avg_drawdown': 'mean',
        'avg_trades': 'mean'
    }).round(4).sort_values('avg_return', ascending=False)
    
    report += """| 均线组合 | 平均收益 | 盈利面 | 平均胜率 | 平均回撤 | 平均交易次数 |
|----------|----------|--------|----------|----------|--------------|
"""
    
    for ma_combo, row in ma_summary.iterrows():
        report += f"| {ma_combo} | **{row['avg_return']*100:.2f}%** | {row['profit_ratio']*100:.1f}% | {row['avg_win_rate']:.1f}% | {row['avg_drawdown']*100:.2f}% | {row['avg_trades']:.1f}次 |\n"
    
    report += f"""
---

## 📉 成交量信号表现对比 (按平均收益排序)

"""
    
    exit_summary = df.groupby('exit_signal').agg({
        'avg_return': 'mean',
        'profit_ratio': 'mean',
        'avg_win_rate': 'mean',
        'avg_drawdown': 'mean',
        'avg_trades': 'mean'
    }).round(4).sort_values('avg_return', ascending=False)
    
    report += """| 成交量信号 | 平均收益 | 盈利面 | 平均胜率 | 平均回撤 | 平均交易次数 |
|------------|----------|--------|----------|----------|--------------|
"""
    
    for sig, row in exit_summary.iterrows():
        report += f"| {sig} | **{row['avg_return']*100:.2f}%** | {row['profit_ratio']*100:.1f}% | {row['avg_win_rate']:.1f}% | {row['avg_drawdown']*100:.2f}% | {row['avg_trades']:.1f}次 |\n"
    
    report += f"""
---

## 💡 推荐配置

### 🥇 激进型 (追求高收益)

| 组件 | 推荐 |
|------|------|
| **均线组合** | {df_sorted.iloc[0]['ma_combo']} |
| **成交量信号** | {df_sorted.iloc[0]['exit_signal']} |
| **预期收益** | **{df_sorted.iloc[0]['avg_return']*100:.2f}%** |
| **盈利面** | {df_sorted.iloc[0]['profit_ratio']:.1f}% |
| **风险** | 回撤较大，适合风险承受能力强的投资者 |

### ⚖️ 稳健型 (平衡收益与风险)

"""
    
    # 选择夏普比率较高的组合 (收益/回撤)
    df_sorted['sharpe'] = df_sorted['avg_return'] / df_sorted['avg_drawdown'].replace(0, 0.01)
    stable = df_sorted.sort_values('sharpe', ascending=False).iloc[0]
    
    report += f"""| 组件 | 推荐 |
|------|------|
| **均线组合** | {stable['ma_combo']} |
| **成交量信号** | {stable['exit_signal']} |
| **预期收益** | **{stable['avg_return']*100:.2f}%** |
| **盈利面** | {stable['profit_ratio']:.1f}% |
| **特点** | 收益回撤比最优，适合稳健投资者 |

### 🛡️ 保守型 (追求高盈利面)

"""
    
    conservative = df_sorted.sort_values('profit_ratio', ascending=False).iloc[0]
    
    report += f"""| 组件 | 推荐 |
|------|------|
| **均线组合** | {conservative['ma_combo']} |
| **成交量信号** | {conservative['exit_signal']} |
| **预期收益** | **{conservative['avg_return']*100:.2f}%** |
| **盈利面** | {conservative['profit_ratio']:.1f}% |
| **特点** | 盈利股票比例最高，适合保守投资者 |

---

## 📊 交叉组合热力图数据

**使用说明**: 根据下表选择适合您的组合

| 均线\\成交量 | """ + " | ".join([s['name'] for s in VOLUME_EXIT_SIGNALS]) + """ |
|----------|""" + "|".join(["---" for _ in VOLUME_EXIT_SIGNALS]) + """|
"""
    
    for ma in MA_COMBINATIONS:
        row_data = []
        for sig in VOLUME_EXIT_SIGNALS:
            match = df[(df['ma_combo'] == ma['name']) & (df['exit_signal'] == sig['name'])]
            if len(match) > 0:
                ret = match.iloc[0]['avg_return'] * 100
                row_data.append(f"{ret:.2f}%")
            else:
                row_data.append("-")
        report += f"| {ma['name']} | " + " | ".join(row_data) + " |\n"
    
    report += f"""
---

## ⚠️ 注意事项

1. **数据周期** - 本次回测使用约 1 年数据 (2025-03~2026-03)
2. **抽样误差** - 抽样{SAMPLE_SIZE}只股票，可能存在抽样误差
3. **交易成本** - 已包含万分之三手续费
4. **市场环境** - 不同市场环境下最优组合可能变化
5. **建议** - 根据自身风险偏好选择合适的组合

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    # 保存报告
    report_file = RESULTS_DIR / f'CROSS_SIGNAL_REPORT_{timestamp}.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Markdown 报告已保存至：{report_file}")


if __name__ == '__main__':
    results = run_cross_backtest()
    print(f"\n✅ 回测完成！共测试 {len(results)} 种组合")
