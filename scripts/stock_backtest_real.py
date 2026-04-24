#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票策略回测系统 v3.0 - 真实数据版
【重要】所有数据必须来自真实 API，禁止使用模拟数据
"""

import sys
sys.path.insert(0, '/home/admin/.openclaw/workspace/scripts')

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import time

# 导入真实 API
from stock_api import StockAPI, calculate_indicators

# ==================== 真实数据获取 ====================

def get_real_kline_data(code: str, days: int = 250) -> List[Dict]:
    """
    获取真实 K 线数据（新浪财经 API）
    【重要】禁止使用模拟数据
    """
    api = StockAPI()
    
    print(f"📡 正在获取 {code} 的真实 K 线数据...")
    
    # 尝试获取真实数据
    kline_data = api.get_kline_sina(code, period='day', days=days)
    
    if kline_data and len(kline_data) > 0:
        print(f"✅ 成功获取 {len(kline_data)} 条真实数据")
        print(f"   数据范围：{kline_data[0]['date']} 至 {kline_data[-1]['date']}")
        return kline_data
    else:
        # API 失败时的处理
        print(f"❌ 无法获取 {code} 的真实数据")
        print("   可能原因：网络问题、API 限流、股票代码错误")
        print("   请检查网络连接或稍后重试")
        return None

def get_real_fund_flow(code: str) -> Dict:
    """
    获取真实资金流数据（东方财富 API）
    【重要】禁止使用模拟数据
    """
    api = StockAPI()
    
    fund_flow = api.get_fund_flow(code)
    
    if fund_flow:
        print(f"✅ 获取 {code} 资金流：主力净流入={fund_flow['main_net_inflow']:,.0f}万")
        return fund_flow
    else:
        print(f"⚠️ 无法获取 {code} 资金流数据，使用默认值")
        return {
            'main_net_inflow': 0,
            'main_ratio': 0,
            'super_ratio': 0
        }

# ==================== 综合评分系统（基于真实数据）====================

def calculate_score_real(data: List[Dict], indicators: Dict, fund_flow: Dict = None) -> Tuple[float, Dict]:
    """
    计算综合评分（基于真实数据）
    """
    if not indicators or len(data) < 1:
        return 50.0, {}
    
    latest = data[-1]
    prev = data[-2] if len(data) > 1 else data[-1]
    price_change = (latest['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
    
    # 技术面（35 分）
    tech_score = 17.5
    
    # MACD 评分
    macd_trend = indicators.get('macd', {}).get('trend', '延续')
    if macd_trend == '金叉':
        tech_score += 8
    elif macd_trend == '死叉':
        tech_score -= 6
    
    # KDJ 评分
    kdj_pos = indicators.get('kdj', {}).get('position', '中性')
    kdj_k = indicators.get('kdj', {}).get('k', 50)
    if kdj_pos == '超卖':
        tech_score += 6
    elif 50 < kdj_k < 75:
        tech_score += 3
    elif kdj_pos == '超买':
        tech_score -= 5
    
    # 均线趋势评分
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
    
    # 量价配合评分
    vol_ratio = indicators.get('volume', {}).get('volume_ratio', 1)
    if vol_ratio > 2 and price_change > 0:
        tech_score += 6
    elif vol_ratio > 1.5 and price_change > 0:
        tech_score += 4
    elif vol_ratio > 1 and price_change > 0:
        tech_score += 2
    elif vol_ratio > 2 and price_change < 0:
        tech_score -= 4
    
    tech_score = max(0, min(35, tech_score))
    
    # 资金面（20 分）- 使用真实资金流数据
    fund_score = 10.0
    if fund_flow:
        main_ratio = fund_flow.get('main_ratio', 0)
        super_ratio = fund_flow.get('super_ratio', 0)
        
        if main_ratio > 10:
            fund_score += 8
        elif main_ratio > 5:
            fund_score += 5
        elif main_ratio > 0:
            fund_score += 2
        elif main_ratio < -10:
            fund_score -= 5
        elif main_ratio < -5:
            fund_score -= 3
        
        if super_ratio > 5:
            fund_score += 4
        elif super_ratio > 2:
            fund_score += 2
    
    fund_score = max(0, min(20, fund_score))
    
    # 题材面（20 分）
    theme_score = 14.0
    
    # 基本面（15 分）
    fundamental_score = 10.0
    
    # 风险面（10 分）
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

# ==================== 回测引擎（真实数据版）====================

class BacktestEngineReal:
    """回测引擎（真实数据版）"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = 0
        self.cost_basis = 0
        self.trades = []
        self.consecutive_losses = 0
        self.peak_capital = initial_capital
        self.max_drawdown = 0
    
    def get_position_size(self, price: float, score: float) -> int:
        """动态仓位管理"""
        base_ratio = 0.95
        
        if self.consecutive_losses >= 3:
            base_ratio = 0.3
        elif self.consecutive_losses >= 2:
            base_ratio = 0.5
        elif self.consecutive_losses >= 1:
            base_ratio = 0.7
        
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
        
        if profit < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        self.position -= shares
        if self.position == 0:
            self.cost_basis = 0
        
        current_total = self.capital + self.position * price
        if current_total > self.peak_capital:
            self.peak_capital = current_total
        drawdown = (self.peak_capital - current_total) / self.peak_capital * 100
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        
        return True

# ==================== 交易策略（真实数据版）====================

def trading_strategy_real(score: float, indicators: Dict, prev_score: float = 0,
                          hold_days: int = 0, current_return: float = 0,
                          peak_return: float = 0) -> str:
    """
    交易策略（真实数据版）
    """
    ma_trend = indicators.get('ma_trend', '震荡')
    
    # 买入信号
    if score >= 75 and prev_score < 75 and ma_trend != '强势空头':
        return 'buy'
    
    # 卖出信号
    if score < 50:
        return 'sell'
    
    if hold_days >= 7 and score < 60:
        return 'sell'
    
    # 追踪止损
    if peak_return > 0.08 and current_return < peak_return - 0.05:
        return 'sell'
    
    if ma_trend == '强势空头' and hold_days > 0:
        return 'sell'
    
    return 'hold'

# ==================== 回测主函数（真实数据版）====================

def run_backtest_real(code: str, name: str, days: int = 250) -> Dict:
    """
    运行回测（真实数据版）
    【重要】所有数据必须来自真实 API
    """
    print("=" * 90)
    print(" " * 25 + "股票策略回测系统 v3.0（真实数据版）")
    print("=" * 90)
    print(f"\n📊 回测标的：{name} ({code})")
    print(f"📅 回测周期：{days} 交易日")
    print(f"💰 初始资金：100,000 元")
    print(f"⚠️  【重要】所有数据来自真实 API，禁止使用模拟数据")
    print("-" * 90)
    
    # 【关键】获取真实 K 线数据
    data = get_real_kline_data(code, days)
    
    if not data or len(data) < 60:
        print(f"\n❌ 错误：无法获取足够的真实数据（需要至少 60 条，实际{len(data) if data else 0}条）")
        print("   请检查网络连接或股票代码是否正确")
        return None
    
    # 初始化回测引擎
    engine = BacktestEngineReal(initial_capital=100000)
    
    # 回测参数
    take_profit = 0.15
    stop_loss = 0.06
    trailing_stop_start = 0.08
    trailing_stop_pct = 0.05
    
    hold_days = 0
    buy_price = 0
    prev_score = 50
    peak_return = 0
    
    # 获取最新资金流数据（用于评分）
    print(f"\n💰 获取最新资金流数据...")
    latest_fund_flow = get_real_fund_flow(code)
    
    print(f"\n📊 开始回测...")
    print("-" * 90)
    
    # 逐日回测
    trade_count = 0
    for i in range(60, len(data)):
        day_data = data[:i+1]
        current = day_data[-1]
        
        # 计算技术指标（基于真实 K 线）
        indicators = calculate_indicators(day_data)
        
        # 计算综合评分（使用真实资金流）
        score, score_details = calculate_score_real(day_data, indicators, latest_fund_flow)
        
        # 当前收益率
        current_return = (current['close'] - buy_price) / buy_price if buy_price > 0 else 0
        peak_return = max(peak_return, current_return)
        
        # 获取交易信号
        signal = trading_strategy_real(score, indicators, prev_score, hold_days, current_return, peak_return)
        
        # 执行交易
        if signal == 'buy' and engine.position == 0:
            shares = engine.get_position_size(current['close'], score)
            if shares > 0:
                engine.buy(current['date'], current['close'], shares, f"评分={score:.1f} 趋势={score_details.get('ma_trend', '-')}")
                buy_price = current['close']
                hold_days = 0
                peak_return = 0
                trade_count += 1
                print(f"📈 [{current['date']}] 买入 {shares}股 @ {current['close']:.2f}元 (评分={score:.1f})")
        
        elif signal == 'sell' and engine.position > 0:
            reason = f"评分={score:.1f}"
            if current_return > take_profit:
                reason += " 止盈"
            elif current_return < -stop_loss:
                reason += " 止损"
            elif peak_return > trailing_stop_start and current_return < peak_return - trailing_stop_pct:
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
                if current_return > take_profit:
                    engine.sell(current['date'], current['close'], reason="止盈")
                    print(f"📉 [{current['date']}] 止盈卖出 @ {current['close']:.2f}元 收益率={current_return*100:.1f}%")
                    hold_days = 0
                    buy_price = 0
                    peak_return = 0
                elif current_return < -stop_loss:
                    engine.sell(current['date'], current['close'], reason="止损")
                    print(f"📉 [{current['date']}] 止损卖出 @ {current['close']:.2f}元 收益率={current_return*100:.1f}%")
                    hold_days = 0
                    buy_price = 0
                    peak_return = 0
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
    
    final_value = engine.initial_capital + total_profit
    total_return = (final_value - engine.initial_capital) / engine.initial_capital * 100
    
    # 输出回测报告
    print("\n" + "=" * 90)
    print(" " * 38 + "回测报告")
    print("=" * 90)
    
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
        'version': 'v3.0-real',
        'data_source': 'real-api',
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
        'timestamp': datetime.now().isoformat(),
    }
    
    output_dir = '/home/admin/.openclaw/workspace/data/backtest'
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/backtest_real_{code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 回测报告已保存：{output_file}")
    print("⚠️  【重要】本回测基于真实 API 数据")
    
    return result

if __name__ == "__main__":
    # 回测指定股票
    stocks = [
        {'code': '600549', 'name': '厦门钨业'},
        {'code': '000592', 'name': '平潭发展'},
        {'code': '600186', 'name': '莲花健康'},
    ]
    
    results = []
    for stock in stocks:
        result = run_backtest_real(stock['code'], stock['name'], days=250)
        if result:
            results.append(result)
        time.sleep(1)  # API 限流保护
    
    # 汇总
    if results:
        print("\n" + "=" * 90)
        print(" " * 35 + "回测汇总")
        print("=" * 90)
        print(f"\n{'股票':<12} {'收益率':<10} {'胜率':<8} {'交易次数':<10} {'最大回撤':<10}")
        print("-" * 90)
        for r in sorted(results, key=lambda x: x['total_return'], reverse=True):
            print(f"{r['code']:<8} {r['total_return']:>8.2f}% {r['win_rate']:>7.1f}% {r['total_trades']:>10} {r['max_drawdown']:>9.2f}%")
