#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票策略回测系统 v5.0 - 真实数据版
【重要】所有数据来自东方财富 API，禁止使用模拟数据
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import requests

# ==================== 真实数据获取 ====================

def get_real_kline_data(code: str, days: int = 250) -> Optional[List[Dict]]:
    """
    获取真实 K 线数据（东方财富 API）
    【重要】真实数据，禁止模拟
    """
    print(f"📡 正在获取 {code} 的真实 K 线数据...")
    
    # 转换证券 ID
    if code.startswith('6') or code.startswith('9'):
        secid = f'1.{code}'
    else:
        secid = f'0.{code}'
    
    # 计算日期范围
    end_date = datetime.now()
    beg_date = datetime(end_date.year - 1, end_date.month, end_date.day)
    
    url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
    params = {
        'secid': secid,
        'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'klt': '101',
        'fqt': '1',
        'beg': beg_date.strftime('%Y%m%d'),
        'end': end_date.strftime('%Y%m%d'),
        'lmt': '1000000'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'http://quote.eastmoney.com/',
        'Connection': 'keep-alive'
    }
    
    # 重试机制
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            
            data = resp.json()
            
            if data.get('rc') != 0 or not data.get('data'):
                print(f"⚠️ API 返回错误，重试 {attempt+1}/3")
                time.sleep(2)
                continue
            
            klines = data['data'].get('klines', [])
            if not klines:
                print(f"⚠️ 无 K 线数据，重试 {attempt+1}/3")
                time.sleep(2)
                continue
            
            # 解析数据
            parsed_data = []
            for line in klines:
                fields = line.split(',')
                if len(fields) >= 11:
                    parsed_data.append({
                        'date': fields[0],
                        'open': float(fields[1]),
                        'close': float(fields[2]),
                        'high': float(fields[3]),
                        'low': float(fields[4]),
                        'volume': int(fields[5]),
                        'amount': float(fields[6]),
                        'amplitude': float(fields[7]),
                        'change_pct': float(fields[8]),
                        'change': float(fields[9]),
                        'turnover': float(fields[10])
                    })
            
            print(f"✅ 成功获取 {len(parsed_data)} 条真实数据")
            if parsed_data:
                print(f"   数据范围：{parsed_data[0]['date']} 至 {parsed_data[-1]['date']}")
                print(f"   最新收盘价：{parsed_data[-1]['close']:.2f}元")
            
            return parsed_data
            
        except Exception as e:
            print(f"⚠️ 请求失败 (尝试 {attempt+1}/3): {e}")
            if attempt < 2:
                time.sleep(3)
    
    print(f"❌ 无法获取真实数据，已重试 3 次")
    return None

def get_real_fund_flow(code: str) -> Optional[Dict]:
    """
    获取真实资金流数据（东方财富 API）
    """
    print(f"💰 正在获取 {code} 的资金流数据...")
    
    try:
        if code.startswith('6') or code.startswith('9'):
            secid = f'1.{code}'
        else:
            secid = f'0.{code}'
        
        url = 'https://push2.eastmoney.com/api/qt/stock/fflow/daykline/get'
        params = {
            'lmt': 0,
            'klt': 1,
            'fields1': 'f1,f2,f3,f7',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65',
            'ut': 'b2884a393a59ad64002292a3e90d46a5',
            'secid': secid
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://quote.eastmoney.com/'
        }
        
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        
        data = resp.json()
        
        if data.get('rc') != 0 or not data.get('data'):
            print(f"⚠️ 资金流数据获取失败，使用默认值")
            return {'main_net_inflow': 0, 'main_ratio': 0, 'super_ratio': 0}
        
        klines = data['data'].get('klines', [])
        if not klines:
            return {'main_net_inflow': 0, 'main_ratio': 0, 'super_ratio': 0}
        
        # 解析最新一天数据
        latest = klines[-1].split(',')
        
        fund_flow = {
            'main_net_inflow': float(latest[1]) / 10000,  # 万元
            'main_ratio': float(latest[6]),
            'super_ratio': float(latest[10]),
            'large_ratio': float(latest[9]),
            'medium_ratio': float(latest[8]),
            'small_ratio': float(latest[7])
        }
        
        print(f"✅ 主力净流入：{fund_flow['main_net_inflow']:,.0f}万 ({fund_flow['main_ratio']:.2f}%)")
        
        return fund_flow
        
    except Exception as e:
        print(f"⚠️ 资金流获取失败：{e}")
        return {'main_net_inflow': 0, 'main_ratio': 0, 'super_ratio': 0}

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
        'turnover_rate': data[-1].get('turnover', 0)
    }
    
    return indicators

# ==================== 综合评分 ====================

def calculate_score(data: List[Dict], indicators: Dict, fund_flow: Dict = None) -> Tuple[float, Dict]:
    """计算综合评分"""
    if not indicators or len(data) < 1:
        return 50.0, {}
    
    latest = data[-1]
    prev = data[-2] if len(data) > 1 else data[-1]
    price_change = (latest['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
    
    # 技术面（35 分）
    tech_score = 17.5
    
    macd_trend = indicators.get('macd', {}).get('trend', '延续')
    if macd_trend == '金叉':
        tech_score += 8
    elif macd_trend == '死叉':
        tech_score -= 6
    
    kdj_pos = indicators.get('kdj', {}).get('position', '中性')
    kdj_k = indicators.get('kdj', {}).get('k', 50)
    if kdj_pos == '超卖':
        tech_score += 6
    elif 50 < kdj_k < 75:
        tech_score += 3
    elif kdj_pos == '超买':
        tech_score -= 5
    
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
    
    # 资金面（20 分）
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
    
    theme_score = 14.0
    fundamental_score = 10.0
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

# ==================== 回测引擎 ====================

class BacktestEngine:
    """回测引擎"""
    
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
            self.cost_basis = cost / shares
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

# ==================== 交易策略 ====================

def trading_strategy(score: float, indicators: Dict, prev_score: float = 0,
                     hold_days: int = 0, current_return: float = 0,
                     peak_return: float = 0) -> str:
    """交易策略"""
    ma_trend = indicators.get('ma_trend', '震荡')
    
    if score >= 75 and prev_score < 75 and ma_trend != '强势空头':
        return 'buy'
    
    if score < 50:
        return 'sell'
    
    if hold_days >= 7 and score < 60:
        return 'sell'
    
    if peak_return > 0.08 and current_return < peak_return - 0.05:
        return 'sell'
    
    if ma_trend == '强势空头' and hold_days > 0:
        return 'sell'
    
    return 'hold'

# ==================== 回测主函数 ====================

def run_backtest_real(code: str, name: str, days: int = 250) -> Optional[Dict]:
    """运行回测（真实数据版）"""
    print("=" * 90)
    print(" " * 25 + "股票策略回测系统 v5.0（真实数据版）")
    print("=" * 90)
    print(f"\n📊 回测标的：{name} ({code})")
    print(f"📅 回测周期：{days} 交易日")
    print(f"💰 初始资金：100,000 元")
    print(f"⚠️  【重要】所有数据来自东方财富 API，禁止使用模拟数据")
    print("-" * 90)
    
    # 【关键】获取真实 K 线数据
    data = get_real_kline_data(code, days)
    
    if not data or len(data) < 60:
        print(f"\n❌ 错误：无法获取足够的真实数据")
        return None
    
    # 获取资金流数据
    fund_flow = get_real_fund_flow(code)
    
    # 初始化回测引擎
    engine = BacktestEngine(initial_capital=100000)
    
    # 回测参数
    take_profit = 0.15
    stop_loss = 0.06
    trailing_stop_start = 0.08
    trailing_stop_pct = 0.05
    
    hold_days = 0
    buy_price = 0
    prev_score = 50
    peak_return = 0
    
    print(f"\n📊 开始回测...")
    print("-" * 90)
    
    for i in range(60, len(data)):
        day_data = data[:i+1]
        current = day_data[-1]
        
        indicators = calculate_indicators(day_data)
        score, score_details = calculate_score(day_data, indicators, fund_flow)
        
        current_return = (current['close'] - buy_price) / buy_price if buy_price > 0 else 0
        peak_return = max(peak_return, current_return)
        
        signal = trading_strategy(score, indicators, prev_score, hold_days, current_return, peak_return)
        
        if signal == 'buy' and engine.position == 0:
            shares = engine.get_position_size(current['close'], score)
            if shares > 0:
                engine.buy(current['date'], current['close'], shares, f"评分={score:.1f}")
                buy_price = current['close']
                hold_days = 0
                peak_return = 0
                print(f"📈 [{current['date']}] 买入 {shares}股 @ {current['close']:.2f}元 (评分={score:.1f})")
        
        elif signal == 'sell' and engine.position > 0:
            reason = f"评分={score:.1f}"
            if current_return > take_profit:
                reason += " 止盈"
            elif current_return < -stop_loss:
                reason += " 止损"
            
            engine.sell(current['date'], current['close'], reason=reason)
            profit_pct = (current['close'] - buy_price) / buy_price * 100
            print(f"📉 [{current['date']}] 卖出 @ {current['close']:.2f}元 收益率={profit_pct:.1f}% ({reason})")
            hold_days = 0
            buy_price = 0
            peak_return = 0
        
        elif engine.position > 0:
            hold_days += 1
            
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
        
        prev_score = score
    
    if engine.position > 0:
        engine.sell(data[-1]['date'], data[-1]['close'], reason="回测结束")
        print(f"📉 [{data[-1]['date']}] 回测结束强制平仓 @ {data[-1]['close']:.2f}元")
    
    # 计算结果
    total_trades = len([t for t in engine.trades if t['type'] == '卖出'])
    profitable_trades = len([t for t in engine.trades if t['type'] == '卖出' and t.get('profit', 0) > 0])
    win_rate = profitable_trades / total_trades * 100 if total_trades > 0 else 0
    
    total_profit = sum([t.get('profit', 0) for t in engine.trades if t['type'] == '卖出'])
    avg_profit = total_profit / total_trades if total_trades > 0 else 0
    
    final_value = engine.initial_capital + total_profit
    total_return = (final_value - engine.initial_capital) / engine.initial_capital * 100
    
    # 输出报告
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
    
    result = {
        'code': code,
        'name': name,
        'version': 'v5.0-real-api',
        'data_source': 'eastmoney-api',
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
    
    # 保存结果
    output_dir = '/home/admin/.openclaw/workspace/data/backtest'
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/backtest_real_api_{code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 回测报告已保存：{output_file}")
    print("✅ 【重要】本回测基于东方财富 API 真实数据")
    
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
        print(f"\n{'股票':<12} {'收益率':<10} {'胜率':<8} {'交易次数':<10} {'最大回撤':<10} {'年化':<10}")
        print("-" * 90)
        for r in sorted(results, key=lambda x: x['total_return'], reverse=True):
            print(f"{r['code']:<8} {r['total_return']:>8.2f}% {r['win_rate']:>7.1f}% {r['total_trades']:>10} {r['max_drawdown']:>9.2f}% {r['annual_return']:>9.2f}%")
