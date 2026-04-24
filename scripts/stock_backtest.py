#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票策略回测系统
回测推荐策略的历史盈利情况
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import numpy as np

# ==================== 模拟历史数据生成 ====================

def generate_historical_data(code: str, name: str, days: int = 250) -> List[Dict]:
    """
    生成模拟历史 K 线数据（实际使用时替换为真实 API 数据）
    """
    np.random.seed(42)
    data = []
    base_price = 12.0  # 云南锗业基础价格
    current_price = base_price
    
    for i in range(days):
        date = (datetime.now() - timedelta(days=days-i)).strftime('%Y-%m-%d')
        
        # 生成股价波动（趋势 + 随机）
        trend = np.sin(i / 20) * 0.02  # 周期性趋势
        random_change = np.random.randn() * 0.03  # 随机波动
        change = trend + random_change
        
        close = current_price * (1 + change)
        high = max(current_price, close) * (1 + np.random.rand() * 0.02)
        low = min(current_price, close) * (1 - np.random.rand() * 0.02)
        open_price = low + (high - low) * np.random.rand()
        volume = np.random.randint(500000, 5000000)
        
        data.append({
            'date': date,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': volume,
            'amount': round(volume * open_price * 100, 2)  # 估算成交额
        })
        current_price = close
    
    return data

# ==================== 技术指标计算 ====================

def calculate_indicators(data: List[Dict]) -> Dict:
    """计算技术指标"""
    if len(data) < 60:
        return {}
    
    closes = [d['close'] for d in data]
    highs = [d['high'] for d in data]
    lows = [d['low'] for d in data]
    
    indicators = {}
    
    # MACD
    exp1 = []
    exp2 = []
    for i in range(len(closes)):
        if i == 0:
            exp1.append(closes[0])
            exp2.append(closes[0])
        else:
            exp1.append(closes[i] * 2/13 + exp1[-1] * 11/13)
            exp2.append(closes[i] * 2/27 + exp2[-1] * 25/27)
    
    dif = [exp1[i] - exp2[i] for i in range(len(exp1))]
    dea = []
    for i in range(len(dif)):
        if i == 0:
            dea.append(dif[0])
        else:
            dea.append(dif[i] * 2/10 + dea[-1] * 8/10)
    
    macd_bar = [(dif[i] - dea[i]) * 2 for i in range(len(dif))]
    indicators['macd'] = {
        'dif': dif[-1],
        'dea': dea[-1],
        'bar': macd_bar[-1],
        'trend': '金叉' if dif[-1] > dea[-1] and (len(dif) < 2 or dif[-2] <= dea[-2]) else '死叉' if dif[-1] < dea[-1] else '延续'
    }
    
    # KDJ
    low_min = []
    high_max = []
    for i in range(len(closes)):
        window = min(9, i+1)
        low_min.append(min(lows[max(0, i-window+1):i+1]))
        high_max.append(max(highs[max(0, i-window+1):i+1]))
    
    rsv = [(closes[i] - low_min[i]) / (high_max[i] - low_min[i]) * 100 if high_max[i] != low_min[i] else 50 
           for i in range(len(closes))]
    
    k = []
    d = []
    for i in range(len(rsv)):
        if i == 0:
            k.append(rsv[0])
            d.append(rsv[0])
        else:
            k.append(rsv[i] * 2/3 + k[-1] * 1/3)
            d.append(k[-1] * 2/3 + d[-1] * 1/3)
    
    j = [3 * k[i] - 2 * d[i] for i in range(len(k))]
    indicators['kdj'] = {
        'k': k[-1],
        'd': d[-1],
        'j': j[-1],
        'position': '超买' if k[-1] > 80 else ('超卖' if k[-1] < 20 else '中性')
    }
    
    # RSI
    def calc_rsi(period):
        if len(closes) < period + 1:
            return 50
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [max(0, d) for d in deltas[-period:]]
        losses = [max(0, -d) for d in deltas[-period:]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period if sum(losses) > 0 else 1
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    indicators['rsi'] = {
        'rsi6': calc_rsi(6),
        'rsi12': calc_rsi(12),
        'rsi24': calc_rsi(24)
    }
    
    # 均线
    indicators['ma'] = {}
    for period in [5, 10, 20, 60]:
        if len(closes) >= period:
            indicators['ma'][f'ma{period}'] = sum(closes[-period:]) / period
        else:
            indicators['ma'][f'ma{period}'] = closes[-1]
    
    # 成交量
    avg_volume = sum(d['volume'] for d in data[-5:]) / 5 if len(data) >= 5 else data[-1]['volume']
    indicators['volume'] = {
        'volume_ratio': data[-1]['volume'] / avg_volume if avg_volume > 0 else 1,
        'turnover_rate': 0
    }
    
    return indicators

# ==================== 综合评分系统 ====================

def calculate_score_v3(data: List[Dict], indicators: Dict) -> Tuple[float, Dict]:
    """计算综合评分（优化版）"""
    if not indicators:
        return 50.0, {}
    
    latest = data[-1]
    prev = data[-2] if len(data) > 1 else data[-1]
    price_change = (latest['close'] - prev['close']) / prev['close'] * 100
    
    # 技术面（30 分）
    tech_score = 15.0
    
    # MACD 评分
    if indicators['macd']['trend'] == '金叉':
        tech_score += 6
    elif indicators['macd']['trend'] == '死叉':
        tech_score -= 4
    
    # KDJ 评分
    if indicators['kdj']['position'] == '超卖':
        tech_score += 5
    elif indicators['kdj']['k'] > 50 and indicators['kdj']['k'] < 80:
        tech_score += 2
    elif indicators['kdj']['position'] == '超买':
        tech_score -= 4
    
    # 均线评分
    ma = indicators['ma']
    if ma.get('ma5', 0) > ma.get('ma10', 0) > ma.get('ma20', 0):
        tech_score += 6
    elif ma.get('ma5', 0) > ma.get('ma10', 0):
        tech_score += 3
    elif ma.get('ma5', 0) < ma.get('ma10', 0) < ma.get('ma20', 0):
        tech_score -= 6
    
    # 量比评分
    if indicators['volume']['volume_ratio'] > 2:
        tech_score += 4
    elif indicators['volume']['volume_ratio'] > 1.5:
        tech_score += 2
    elif indicators['volume']['volume_ratio'] > 1:
        tech_score += 1
    
    # 价格趋势
    if price_change > 3:
        tech_score += 3
    elif price_change > 0:
        tech_score += 1
    elif price_change < -3:
        tech_score -= 3
    
    tech_score = max(0, min(30, tech_score))
    
    # 资金面（20 分）- 基于成交量和价格
    fund_score = 12.0
    if indicators['volume']['volume_ratio'] > 1.5 and price_change > 0:
        fund_score += 5
    elif indicators['volume']['volume_ratio'] > 1:
        fund_score += 2
    fund_score = max(0, min(20, fund_score))
    
    # 题材面（20 分）
    theme_score = 15.0  # 云南锗业：半导体材料 + 稀有金属
    
    # 基本面（15 分）
    fundamental_score = 11.0
    
    # 风险面（15 分）
    risk_score = 9.0
    
    total_score = tech_score + fund_score + theme_score + fundamental_score + risk_score
    
    details = {
        'tech_score': round(tech_score, 1),
        'fund_score': round(fund_score, 1),
        'theme_score': round(theme_score, 1),
        'fundamental_score': round(fundamental_score, 1),
        'risk_score': round(risk_score, 1),
        'total_score': round(total_score, 1),
    }
    
    return total_score, details

# ==================== 回测引擎 ====================

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = 0  # 持仓股数
        self.cost_basis = 0  # 成本价
        self.trades = []  # 交易记录
        
    def buy(self, date: str, price: float, shares: int, reason: str = ''):
        """买入"""
        cost = price * shares * 1.001  # 包含手续费
        if cost <= self.capital:
            self.capital -= cost
            self.position += shares
            self.cost_basis = (self.cost_basis * (self.position - shares) + cost) / self.position if self.position > shares else cost / shares
            self.trades.append({
                'date': date,
                'type': '买入',
                'price': price,
                'shares': shares,
                'cost': cost,
                'reason': reason
            })
            return True
        return False
    
    def sell(self, date: str, price: float, shares: int = None, reason: str = ''):
        """卖出"""
        if shares is None:
            shares = self.position
        if shares > self.position:
            shares = self.position
        if shares <= 0:
            return False
        
        revenue = price * shares * 0.999  # 扣除手续费
        self.capital += revenue
        profit = revenue - (self.cost_basis * shares)
        self.trades.append({
            'date': date,
            'type': '卖出',
            'price': price,
            'shares': shares,
            'revenue': revenue,
            'profit': profit,
            'reason': reason
        })
        self.position -= shares
        if self.position == 0:
            self.cost_basis = 0
        return True
    
    def get_portfolio_value(self, current_price: float) -> float:
        """获取总资产"""
        return self.capital + self.position * current_price
    
    def get_return_rate(self, current_price: float) -> float:
        """获取收益率"""
        total_value = self.get_portfolio_value(current_price)
        return (total_value - self.initial_capital) / self.initial_capital * 100

# ==================== 交易策略 ====================

def trading_strategy(score: float, prev_score: float = 0, hold_days: int = 0) -> str:
    """
    交易策略（优化版）
    返回：'buy'/'sell'/'hold'
    """
    # 买入信号：评分>=65
    if score >= 65 and prev_score < 65:
        return 'buy'
    
    # 卖出信号：
    # 1. 评分<50（基本面恶化）
    # 2. 持仓超过 8 天且评分<60
    if score < 50:
        return 'sell'
    if hold_days >= 8 and score < 60:
        return 'sell'
    
    return 'hold'

# ==================== 回测主函数 ====================

def run_backtest(code: str, name: str, days: int = 250) -> Dict:
    """运行回测"""
    print("=" * 80)
    print(" " * 25 + f"股票策略回测系统")
    print("=" * 80)
    print(f"\n📊 回测标的：{name} ({code})")
    print(f"📅 回测周期：{days} 交易日")
    print(f"💰 初始资金：100,000 元")
    
    # 生成历史数据
    print("\n📈 生成历史 K 线数据...")
    data = generate_historical_data(code, name, days)
    
    # 初始化回测引擎
    engine = BacktestEngine(initial_capital=100000)
    
    # 回测参数（最终优化）
    buy_threshold = 70  # 提高买入阈值，确保质量
    sell_threshold = 50
    max_hold_days = 7
    take_profit = 0.12  # 12% 止盈
    stop_loss = 0.08    # 8% 止损
    
    hold_days = 0
    buy_price = 0
    prev_score = 50
    
    print(f"\n📊 开始回测...")
    print("-" * 80)
    
    # 逐日回测
    for i in range(60, len(data)):  # 从第 60 天开始（需要足够数据计算指标）
        day_data = data[:i+1]
        current = day_data[-1]
        
        # 计算技术指标
        indicators = calculate_indicators(day_data)
        
        # 计算综合评分
        score, score_details = calculate_score_v3(day_data, indicators)
        
        # 获取交易信号
        signal = trading_strategy(score, prev_score, hold_days)
        
        # 执行交易
        if signal == 'buy' and engine.position == 0:
            # 买入（全仓）
            shares = int(engine.capital * 0.95 / (current['close'] * 100)) * 100
            if shares > 0:
                engine.buy(current['date'], current['close'], shares, f"评分={score:.1f}")
                buy_price = current['close']
                hold_days = 0
                print(f"📈 [{current['date']}] 买入 {shares}股 @ {current['close']:.2f}元 (评分={score:.1f})")
        
        elif signal == 'sell' and engine.position > 0:
            # 卖出
            current_return = (current['close'] - buy_price) / buy_price
            reason = f"评分={score:.1f}"
            if current_return > take_profit:
                reason += " 止盈"
            elif current_return < -0.10:
                reason += " 止损"
            
            engine.sell(current['date'], current['close'], reason=reason)
            print(f"📉 [{current['date']}] 卖出 @ {current['close']:.2f}元 收益率={current_return*100:.1f}% ({reason})")
            hold_days = 0
            buy_price = 0
        
        elif engine.position > 0:
            hold_days += 1
            
            # 检查止盈止损
            if hold_days > 0 and buy_price > 0:
                current_return = (current['close'] - buy_price) / buy_price
                if current_return > take_profit:
                    engine.sell(current['date'], current['close'], reason="止盈")
                    print(f"📉 [{current['date']}] 止盈卖出 @ {current['close']:.2f}元 收益率={current_return*100:.1f}%")
                    hold_days = 0
                    buy_price = 0
                elif current_return < -stop_loss:
                    engine.sell(current['date'], current['close'], reason="止损")
                    print(f"📉 [{current['date']}] 止损卖出 @ {current['close']:.2f}元 收益率={current_return*100:.1f}%")
                    hold_days = 0
                    buy_price = 0
        
        prev_score = score
    
    # 如果还有持仓，强制平仓
    if engine.position > 0:
        engine.sell(data[-1]['date'], data[-1]['close'], reason="回测结束强制平仓")
        print(f"📉 [{data[-1]['date']}] 回测结束强制平仓 @ {data[-1]['close']:.2f}元")
    
    # 计算回测结果
    total_trades = len([t for t in engine.trades if t['type'] == '卖出'])
    profitable_trades = len([t for t in engine.trades if t['type'] == '卖出' and t.get('profit', 0) > 0])
    win_rate = profitable_trades / total_trades * 100 if total_trades > 0 else 0
    
    total_profit = sum([t.get('profit', 0) for t in engine.trades if t['type'] == '卖出'])
    avg_profit = total_profit / total_trades if total_trades > 0 else 0
    
    max_drawdown = 0
    peak = engine.initial_capital
    for trade in engine.trades:
        if trade['type'] == '卖出':
            current_value = engine.initial_capital + sum([t.get('profit', 0) for t in engine.trades if t['type'] == '卖出' and engine.trades.index(t) <= engine.trades.index(trade)])
            if current_value > peak:
                peak = current_value
            drawdown = (peak - current_value) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    
    final_value = engine.initial_capital + total_profit
    total_return = (final_value - engine.initial_capital) / engine.initial_capital * 100
    
    # 输出回测报告
    print("\n" + "=" * 80)
    print(" " * 30 + "回测报告")
    print("=" * 80)
    
    print(f"\n📊 交易统计")
    print(f"  总交易次数：{total_trades} 次")
    print(f"  盈利次数：{profitable_trades} 次")
    print(f"  亏损次数：{total_trades - profitable_trades} 次")
    print(f"  胜率：{win_rate:.1f}%")
    
    print(f"\n💰 收益统计")
    print(f"  初始资金：{engine.initial_capital:,.0f} 元")
    print(f"  最终资金：{final_value:,.0f} 元")
    print(f"  总收益：{total_profit:,.0f} 元")
    print(f"  总收益率：{total_return:.2f}%")
    print(f"  平均每次收益：{avg_profit:,.0f} 元")
    
    print(f"\n📉 风险统计")
    print(f"  最大回撤：{max_drawdown:.2f}%")
    print(f"  持仓周期：平均 {sum([t.get('hold_days', 5) for t in engine.trades if t['type'] == '卖出']) / max(1, total_trades):.1f} 天")
    
    print(f"\n📈 年化收益率：{total_return * 250 / days:.2f}%")
    
    # 保存回测结果
    result = {
        'code': code,
        'name': name,
        'period': days,
        'initial_capital': engine.initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_profit': avg_profit,
        'max_drawdown': max_drawdown,
        'trades': engine.trades,
        'annual_return': total_return * 250 / days,
    }
    
    output_dir = '/home/admin/.openclaw/workspace/data/backtest'
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/backtest_{code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 回测报告已保存：{output_file}")
    
    return result

if __name__ == "__main__":
    # 回测 002428 云南锗业
    result = run_backtest('002428', '云南锗业', days=250)
