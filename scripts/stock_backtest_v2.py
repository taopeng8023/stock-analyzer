#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票策略回测系统 v2.0 - 优化版
改进点：降低回撤、提高胜率
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import numpy as np

# ==================== 历史数据生成 ====================

def generate_historical_data(code: str, name: str, days: int = 250) -> List[Dict]:
    """生成模拟历史 K 线数据"""
    np.random.seed(42)
    data = []
    base_price = 12.0
    current_price = base_price
    
    for i in range(days):
        date = (datetime.now() - timedelta(days=days-i)).strftime('%Y-%m-%d')
        trend = np.sin(i / 20) * 0.02
        random_change = np.random.randn() * 0.03
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
            'amount': round(volume * open_price * 100, 2)
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
    exp1, exp2 = [], []
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
        dea.append(dif[i] * 2/10 + (dea[-1] * 8/10 if dea else dif[0] * 8/10))
    
    macd_bar = [(dif[i] - dea[i]) * 2 for i in range(len(dif))]
    
    # 判断 MACD 趋势（金叉/死叉）
    macd_trend = '延续'
    if len(dif) >= 2:
        if dif[-1] > dea[-1] and dif[-2] <= dea[-2]:
            macd_trend = '金叉'
        elif dif[-1] < dea[-1] and dif[-2] >= dea[-2]:
            macd_trend = '死叉'
    
    indicators['macd'] = {
        'dif': dif[-1],
        'dea': dea[-1],
        'bar': macd_bar[-1],
        'trend': macd_trend
    }
    
    # KDJ
    low_min, high_max = [], []
    for i in range(len(closes)):
        window = min(9, i+1)
        low_min.append(min(lows[max(0, i-window+1):i+1]))
        high_max.append(max(highs[max(0, i-window+1):i+1]))
    
    rsv = [(closes[i] - low_min[i]) / (high_max[i] - low_min[i]) * 100 if high_max[i] != low_min[i] else 50 
           for i in range(len(closes))]
    
    k, d = [], []
    for i in range(len(rsv)):
        if i == 0:
            k.append(rsv[0])
            d.append(rsv[0])
        else:
            k.append(rsv[i] * 2/3 + k[-1] * 1/3)
            d.append(k[-1] * 2/3 + (d[-1] * 1/3 if d else rsv[0] * 1/3))
    
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
    
    # 判断均线趋势
    ma = indicators['ma']
    if ma.get('ma5', 0) > ma.get('ma10', 0) > ma.get('ma20', 0) > ma.get('ma60', 0):
        indicators['ma_trend'] = '强势多头'
    elif ma.get('ma5', 0) > ma.get('ma10', 0) > ma.get('ma20', 0):
        indicators['ma_trend'] = '多头'
    elif ma.get('ma5', 0) < ma.get('ma10', 0) < ma.get('ma20', 0) < ma.get('ma60', 0):
        indicators['ma_trend'] = '强势空头'
    elif ma.get('ma5', 0) < ma.get('ma10', 0) < ma.get('ma20', 0):
        indicators['ma_trend'] = '空头'
    else:
        indicators['ma_trend'] = '震荡'
    
    # 成交量
    avg_volume = sum(d['volume'] for d in data[-5:]) / 5 if len(data) >= 5 else data[-1]['volume']
    indicators['volume'] = {
        'volume_ratio': data[-1]['volume'] / avg_volume if avg_volume > 0 else 1,
        'turnover_rate': 0
    }
    
    return indicators

# ==================== 综合评分系统 v2.0 ====================

def calculate_score_v2(data: List[Dict], indicators: Dict) -> Tuple[float, Dict]:
    """计算综合评分 v2.0（优化版）"""
    if not indicators:
        return 50.0, {}
    
    latest = data[-1]
    prev = data[-2] if len(data) > 1 else data[-1]
    price_change = (latest['close'] - prev['close']) / prev['close'] * 100
    
    # 技术面（35 分）- 提高权重
    tech_score = 17.5
    
    # MACD 评分（最高 +8 分）
    if indicators['macd']['trend'] == '金叉':
        tech_score += 8
    elif indicators['macd']['trend'] == '死叉':
        tech_score -= 6
    
    # KDJ 评分（最高 +6 分）
    if indicators['kdj']['position'] == '超卖':
        tech_score += 6
    elif indicators['kdj']['k'] > 50 and indicators['kdj']['k'] < 75:
        tech_score += 3
    elif indicators['kdj']['position'] == '超买':
        tech_score -= 5
    
    # 均线趋势评分（最高 +10 分）- 新增
    ma_trend = indicators.get('ma_trend', '震荡')
    if ma_trend == '强势多头':
        tech_score += 10
    elif ma_trend == '多头':
        tech_score += 6
    elif ma_trend == '震荡':
        tech_score += 0
    elif ma_trend == '空头':
        tech_score -= 6
    elif ma_trend == '强势空头':
        tech_score -= 10
    
    # 量价配合评分（最高 +6 分）
    if indicators['volume']['volume_ratio'] > 2 and price_change > 0:
        tech_score += 6  # 放量上涨
    elif indicators['volume']['volume_ratio'] > 1.5 and price_change > 0:
        tech_score += 4
    elif indicators['volume']['volume_ratio'] > 1 and price_change > 0:
        tech_score += 2
    elif indicators['volume']['volume_ratio'] > 2 and price_change < 0:
        tech_score -= 4  # 放量下跌
    
    tech_score = max(0, min(35, tech_score))
    
    # 资金面（20 分）
    fund_score = 12.0
    if indicators['volume']['volume_ratio'] > 1.5 and price_change > 0:
        fund_score += 6
    elif indicators['volume']['volume_ratio'] > 1:
        fund_score += 3
    fund_score = max(0, min(20, fund_score))
    
    # 题材面（20 分）
    theme_score = 15.0
    
    # 基本面（15 分）
    fundamental_score = 11.0
    
    # 风险面（10 分）- 降低权重
    risk_score = 6.0
    
    total_score = tech_score + fund_score + theme_score + fundamental_score + risk_score
    
    details = {
        'tech_score': round(tech_score, 1),
        'fund_score': round(fund_score, 1),
        'theme_score': round(theme_score, 1),
        'fundamental_score': round(fundamental_score, 1),
        'risk_score': round(risk_score, 1),
        'total_score': round(total_score, 1),
        'ma_trend': ma_trend,
    }
    
    return total_score, details

# ==================== 回测引擎 v2.0 ====================

class BacktestEngineV2:
    """回测引擎 v2.0（优化版）"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = 0
        self.cost_basis = 0
        self.trades = []
        self.consecutive_losses = 0  # 连续亏损次数
        self.peak_capital = initial_capital  # 资金峰值
        self.max_drawdown = 0  # 最大回撤
    
    def get_position_size(self, price: float, score: float) -> int:
        """动态仓位管理"""
        # 基础仓位 95%
        base_ratio = 0.95
        
        # 连续亏损后降低仓位
        if self.consecutive_losses >= 3:
            base_ratio = 0.3  # 连续亏损 3 次，降至 30% 仓位
        elif self.consecutive_losses >= 2:
            base_ratio = 0.5  # 连续亏损 2 次，降至 50% 仓位
        elif self.consecutive_losses >= 1:
            base_ratio = 0.7  # 亏损 1 次，降至 70% 仓位
        
        # 高分增加仓位
        if score >= 85:
            base_ratio = min(1.0, base_ratio + 0.1)
        
        shares = int(self.capital * base_ratio / (price * 100)) * 100
        return max(0, shares)
    
    def buy(self, date: str, price: float, shares: int, reason: str = ''):
        """买入"""
        cost = price * shares * 1.001
        if cost <= self.capital and shares > 0:
            self.capital -= cost
            self.position += shares
            self.cost_basis = cost / shares if shares > 0 else 0
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
        
        revenue = price * shares * 0.999
        profit = revenue - (self.cost_basis * shares)
        
        self.capital += revenue
        self.trades.append({
            'date': date,
            'type': '卖出',
            'price': price,
            'shares': shares,
            'revenue': revenue,
            'profit': profit,
            'reason': reason
        })
        
        # 更新连续亏损计数
        if profit < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        self.position -= shares
        if self.position == 0:
            self.cost_basis = 0
        
        # 更新最大回撤
        current_total = self.capital + self.position * price
        if current_total > self.peak_capital:
            self.peak_capital = current_total
        drawdown = (self.peak_capital - current_total) / self.peak_capital * 100
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        
        return True
    
    def get_portfolio_value(self, current_price: float) -> float:
        """获取总资产"""
        return self.capital + self.position * current_price

# ==================== 交易策略 v2.0 ====================

def trading_strategy_v2(score: float, indicators: Dict, prev_score: float = 0, 
                        hold_days: int = 0, current_return: float = 0) -> str:
    """
    交易策略 v2.0（优化版）
    改进：添加趋势过滤、追踪止损
    """
    ma_trend = indicators.get('ma_trend', '震荡')
    
    # === 买入信号 ===
    # 1. 评分 >= 75（适度提高阈值）
    # 2. 均线趋势不是强势空头（避免逆势）
    # 3. 之前评分 < 75（刚达到条件）
    # 4. 无持仓
    if score >= 75 and prev_score < 75 and ma_trend != '强势空头':
        return 'buy'
    
    # === 卖出信号 ===
    # 1. 评分 < 50（基本面恶化）
    if score < 50:
        return 'sell'
    
    # 2. 持仓超过 7 天且评分 < 60
    if hold_days >= 7 and score < 60:
        return 'sell'
    
    # 3. 追踪止损（新增）
    if hold_days > 0 and current_return > 0.05:
        # 盈利超过 5%，启动追踪止损（保护利润）
        if current_return < 0.02:  # 从高点回撤超过 3%
            return 'sell'
    
    # 4. 均线转空（新增）
    if ma_trend == '强势空头' and hold_days > 0:
        return 'sell'
    
    return 'hold'

# ==================== 回测主函数 v2.0 ====================

def run_backtest_v2(code: str, name: str, days: int = 250) -> Dict:
    """运行回测 v2.0"""
    print("=" * 80)
    print(" " * 22 + "股票策略回测系统 v2.0（优化版）")
    print("=" * 80)
    print(f"\n📊 回测标的：{name} ({code})")
    print(f"📅 回测周期：{days} 交易日")
    print(f"💰 初始资金：100,000 元")
    
    # 生成历史数据
    print("\n📈 生成历史 K 线数据...")
    data = generate_historical_data(code, name, days)
    
    # 初始化回测引擎
    engine = BacktestEngineV2(initial_capital=100000)
    
    # 回测参数（优化）
    take_profit = 0.15   # 15% 止盈（提高）
    stop_loss = 0.06     # 6% 止损（降低）
    trailing_stop_start = 0.08  # 盈利 8% 后启动追踪
    trailing_stop_pct = 0.05    # 追踪止损 5%（让利润多飞）
    
    hold_days = 0
    buy_price = 0
    prev_score = 50
    peak_return = 0
    
    print(f"\n📊 开始回测...")
    print("-" * 80)
    
    # 逐日回测
    for i in range(60, len(data)):
        day_data = data[:i+1]
        current = day_data[-1]
        
        # 计算技术指标
        indicators = calculate_indicators(day_data)
        
        # 计算综合评分
        score, score_details = calculate_score_v2(day_data, indicators)
        
        # 当前收益率
        current_return = (current['close'] - buy_price) / buy_price if buy_price > 0 else 0
        peak_return = max(peak_return, current_return)
        
        # 获取交易信号
        signal = trading_strategy_v2(score, indicators, prev_score, hold_days, current_return)
        
        # 执行交易
        if signal == 'buy' and engine.position == 0:
            # 动态仓位
            shares = engine.get_position_size(current['close'], score)
            if shares > 0:
                engine.buy(current['date'], current['close'], shares, f"评分={score:.1f} 趋势={score_details.get('ma_trend', '-')}")
                buy_price = current['close']
                hold_days = 0
                peak_return = 0
                print(f"📈 [{current['date']}] 买入 {shares}股 @ {current['close']:.2f}元 (评分={score:.1f} 趋势={score_details.get('ma_trend', '-')})")
        
        elif signal == 'sell' and engine.position > 0:
            reason = f"评分={score:.1f}"
            if current_return > take_profit:
                reason += " 止盈"
            elif current_return < -stop_loss:
                reason += " 止损"
            elif peak_return > 0.05 and current_return < peak_return - trailing_stop:
                reason += " 追踪止损"
            
            engine.sell(current['date'], current['close'], reason=reason)
            profit_pct = (current['close'] - buy_price) / buy_price * 100
            print(f"📉 [{current['date']}] 卖出 @ {current['close']:.2f}元 收益率={profit_pct:.1f}% ({reason})")
            hold_days = 0
            buy_price = 0
            peak_return = 0
        
        elif engine.position > 0:
            hold_days += 1
            
            # 检查止盈止损
            if hold_days > 0 and buy_price > 0:
                # 止盈
                if current_return > take_profit:
                    engine.sell(current['date'], current['close'], reason="止盈")
                    print(f"📉 [{current['date']}] 止盈卖出 @ {current['close']:.2f}元 收益率={current_return*100:.1f}%")
                    hold_days = 0
                    buy_price = 0
                    peak_return = 0
                # 止损
                elif current_return < -stop_loss:
                    engine.sell(current['date'], current['close'], reason="止损")
                    print(f"📉 [{current['date']}] 止损卖出 @ {current['close']:.2f}元 收益率={current_return*100:.1f}%")
                    hold_days = 0
                    buy_price = 0
                    peak_return = 0
                # 追踪止损（盈利 8% 后启动，回撤 5% 卖出）
                elif peak_return > trailing_stop_start and current_return < peak_return - trailing_stop_pct:
                    engine.sell(current['date'], current['close'], reason="追踪止损")
                    print(f"📉 [{current['date']}] 追踪止损卖出 @ {current['close']:.2f}元 收益率={current_return*100:.1f}% (峰值={peak_return*100:.1f}%)")
                    hold_days = 0
                    buy_price = 0
                    peak_return = 0
        
        prev_score = score
    
    # 强制平仓
    if engine.position > 0:
        engine.sell(data[-1]['date'], data[-1]['close'], reason="回测结束")
        print(f"📉 [{data[-1]['date']}] 回测结束强制平仓 @ {data[-1]['close']:.2f}元")
    
    # 计算回测结果
    total_trades = len([t for t in engine.trades if t['type'] == '卖出'])
    profitable_trades = len([t for t in engine.trades if t['type'] == '卖出' and t.get('profit', 0) > 0])
    win_rate = profitable_trades / total_trades * 100 if total_trades > 0 else 0
    
    total_profit = sum([t.get('profit', 0) for t in engine.trades if t['type'] == '卖出'])
    avg_profit = total_profit / total_trades if total_trades > 0 else 0
    
    # 计算平均持仓周期
    hold_period_sum = 0
    sell_trades = [t for t in engine.trades if t['type'] == '卖出']
    for j, trade in enumerate(sell_trades):
        if j > 0:
            buy_trade = engine.trades[engine.trades.index(trade) - 1]
            if buy_trade['type'] == '买入':
                hold_period_sum += 1  # 简化计算
    
    final_value = engine.initial_capital + total_profit
    total_return = (final_value - engine.initial_capital) / engine.initial_capital * 100
    
    # 输出回测报告
    print("\n" + "=" * 80)
    print(" " * 32 + "回测报告")
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
    print(f"  最大回撤：{engine.max_drawdown:.2f}%")
    print(f"  连续亏损最多：{engine.consecutive_losses} 次")
    
    print(f"\n📈 年化收益率：{total_return * 250 / days:.2f}%")
    
    # 保存结果
    result = {
        'code': code,
        'name': name,
        'version': 'v2.0',
        'period': days,
        'initial_capital': engine.initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_profit': avg_profit,
        'max_drawdown': engine.max_drawdown,
        'trades': engine.trades,
        'annual_return': total_return * 250 / days,
    }
    
    output_dir = '/home/admin/.openclaw/workspace/data/backtest'
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/backtest_v2_{code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 回测报告已保存：{output_file}")
    
    return result

if __name__ == "__main__":
    result = run_backtest_v2('002428', '云南锗业', days=250)
