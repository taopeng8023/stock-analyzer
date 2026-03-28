#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票策略回测系统 - 使用采集的缓存数据
基于凯文采集的 5493 只股票历史行情数据进行回测

功能:
- 读取本地缓存的历史数据
- 技术指标计算 (MACD/KDJ/RSI/均线)
- 综合评分系统
- 交易信号生成
- 完整回测报告

用法:
    python3 backtest_with_cache.py --code 600549 --days 250
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import numpy as np

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ==================== 数据加载 ====================

def load_cached_data(code: str, cache_dir: str = None) -> Optional[List[Dict]]:
    """
    从缓存目录加载历史数据
    
    Args:
        code: 股票代码 (6 位数字)
        cache_dir: 缓存目录路径
    
    Returns:
        历史数据列表，如果不存在则返回 None
    """
    if cache_dir is None:
        cache_dir = os.path.join(os.path.dirname(__file__), 'cache', 'history', datetime.now().strftime('%Y%m'))
    
    # 尝试当前月份
    file_path = os.path.join(cache_dir, f"{code}.json")
    
    # 保存股票代码到数据中
    stock_code = code
    
    if not os.path.exists(file_path):
        # 尝试上个月
        last_month = datetime.now().replace(day=1) - timedelta(days=1)
        cache_dir = os.path.join(os.path.dirname(__file__), 'cache', 'history', last_month.strftime('%Y%m'))
        file_path = os.path.join(cache_dir, f"{code}.json")
    
    if not os.path.exists(file_path):
        print(f"❌ 未找到 {code} 的缓存数据")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 处理不同的数据格式
        if isinstance(data, dict) and 'data' in data:
            records = data['data']
        elif isinstance(data, list):
            records = data
        else:
            print(f"⚠️ 数据格式异常：{file_path}")
            return None
        
        # 标准化字段名
        standardized = []
        for record in records:
            try:
                std = {
                    'code': stock_code,  # 添加股票代码
                    'date': record.get('日期', record.get('date', '')),
                    'open': float(record.get('开盘', record.get('open', 0))),
                    'close': float(record.get('收盘', record.get('close', 0))),
                    'high': float(record.get('最高', record.get('high', 0))),
                    'low': float(record.get('最低', record.get('low', 0))),
                    'volume': int(record.get('成交量', record.get('volume', 0))),
                    'amount': float(record.get('成交额', record.get('amount', 0))),
                    'amplitude': float(record.get('振幅', record.get('amplitude', 0))),
                    'change_pct': float(record.get('涨跌幅', record.get('change_pct', 0))),
                    'change': float(record.get('涨跌额', record.get('change', 0))),
                    'turnover': float(record.get('换手率', record.get('turnover', 0)))
                }
                standardized.append(std)
            except (ValueError, KeyError) as e:
                continue
        
        if standardized:
            print(f"✅ 成功加载 {code} 的 {len(standardized)} 条数据")
            print(f"   数据范围：{standardized[0]['date']} 至 {standardized[-1]['date']}")
            print(f"   最新收盘价：{standardized[-1]['close']:.2f}元")
        
        return standardized
        
    except Exception as e:
        print(f"❌ 加载数据失败：{e}")
        return None


def get_stock_name(code: str) -> str:
    """获取股票名称（从缓存或硬编码）"""
    # 可以尝试从其他缓存文件读取，这里简单返回代码
    return code


# ==================== 技术指标计算 ====================

def calculate_ma(prices: List[float], period: int) -> List[float]:
    """计算移动平均线"""
    result = []
    for i in range(len(prices)):
        if i < period - 1:
            result.append(None)
        else:
            avg = sum(prices[i-period+1:i+1]) / period
            result.append(avg)
    return result


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """计算指数移动平均线"""
    result = []
    multiplier = 2 / (period + 1)
    
    # 第一个 EMA 使用 SMA
    if len(prices) < period:
        return [None] * len(prices)
    
    sma = sum(prices[:period]) / period
    result.append(sma)
    
    for i in range(1, len(prices)):
        ema = (prices[i] - result[-1]) * multiplier + result[-1]
        result.append(ema)
    
    # 前面补 None
    return [None] * (period - 1) + result


def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
    """计算 MACD 指标"""
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    
    # DIF = EMA12 - EMA26
    dif = []
    for i in range(len(prices)):
        if ema_fast[i] is None or ema_slow[i] is None:
            dif.append(None)
        else:
            dif.append(ema_fast[i] - ema_slow[i])
    
    # DEA = DIF 的 9 日 EMA
    dif_valid = [d for d in dif if d is not None]
    dea_raw = calculate_ema(dif_valid, signal) if dif_valid else []
    
    # 对齐 DEA
    dea = []
    dea_idx = 0
    for i in range(len(prices)):
        if dif[i] is None:
            dea.append(None)
        elif dea_idx < len(dea_raw):
            dea.append(dea_raw[dea_idx])
            dea_idx += 1
        else:
            dea.append(None)
    
    # MACD 柱 = 2 * (DIF - DEA)
    macd_bar = []
    for i in range(len(prices)):
        if dif[i] is None or dea[i] is None:
            macd_bar.append(None)
        else:
            macd_bar.append(2 * (dif[i] - dea[i]))
    
    return {
        'dif': dif,
        'dea': dea,
        'macd': macd_bar
    }


def calculate_kdj(data: List[Dict], n: int = 9) -> Dict:
    """计算 KDJ 指标"""
    k_values = []
    d_values = []
    j_values = []
    
    prev_k = 50  # 初始 K 值
    prev_d = 50  # 初始 D 值
    
    for i in range(len(data)):
        if i < n - 1:
            k_values.append(None)
            d_values.append(None)
            j_values.append(None)
            continue
        
        # 计算 N 日内的最高价和最低价
        period = data[i-n+1:i+1]
        highest = max(d['high'] for d in period)
        lowest = min(d['low'] for d in period)
        current_close = data[i]['close']
        
        if highest == lowest:
            rsv = 50
        else:
            rsv = (current_close - lowest) / (highest - lowest) * 100
        
        # K = 2/3 * prev_K + 1/3 * RSV
        k = (2/3) * prev_k + (1/3) * rsv
        # D = 2/3 * prev_D + 1/3 * K
        d = (2/3) * prev_d + (1/3) * k
        # J = 3 * K - 2 * D
        j = 3 * k - 2 * d
        
        k_values.append(k)
        d_values.append(d)
        j_values.append(j)
        
        prev_k = k
        prev_d = d
    
    return {
        'k': k_values,
        'd': d_values,
        'j': j_values
    }


def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """计算 RSI 指标"""
    rsi_values = []
    
    for i in range(len(prices)):
        if i < period:
            rsi_values.append(None)
            continue
        
        # 计算涨跌幅
        gains = []
        losses = []
        
        for j in range(i-period+1, i+1):
            change = prices[j] - prices[j-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        rsi_values.append(rsi)
    
    return rsi_values


# ==================== 综合评分系统 ====================

def calculate_score(data: List[Dict], idx: int) -> Tuple[float, Dict]:
    """
    计算综合评分 (100 分制)
    
    评分维度:
    - 技术面 (40 分): MACD, KDJ, RSI, 均线
    - 资金面 (25 分): 成交量，成交额
    - 趋势面 (20 分): 价格趋势
    - 风险面 (15 分): 波动性
    
    Returns:
        (总分，各维度得分详情)
    """
    if idx < 50:  # 数据不足
        return 0, {}
    
    scores = {}
    
    # 提取价格数据
    closes = [d['close'] for d in data[:idx+1]]
    highs = [d['high'] for d in data[:idx+1]]
    lows = [d['low'] for d in data[:idx+1]]
    volumes = [d['volume'] for d in data[:idx+1]]
    amounts = [d['amount'] for d in data[:idx+1]]
    
    # === 技术面评分 (40 分) ===
    tech_score = 0
    
    # MACD 评分 (10 分)
    macd = calculate_macd(closes)
    if macd['macd'][idx] is not None:
        if macd['macd'][idx] > 0:
            tech_score += 7
            if macd['dif'][idx] > macd['dea'][idx]:  # 金叉
                tech_score += 3
        elif macd['macd'][idx] > -5:
            tech_score += 3
    
    # KDJ 评分 (10 分)
    kdj = calculate_kdj(data[:idx+1])
    if kdj['k'][idx] is not None:
        k = kdj['k'][idx]
        d = kdj['d'][idx]
        if 20 <= k <= 80:
            tech_score += 5
            if k > d:  # 金叉
                tech_score += 5
        elif k < 20:  # 超卖
            tech_score += 7
        elif k > 80:  # 超买
            tech_score += 2
    
    # RSI 评分 (10 分)
    rsi = calculate_rsi(closes)
    if rsi[idx] is not None:
        rsi_val = rsi[idx]
        if 40 <= rsi_val <= 60:
            tech_score += 6
        elif 30 <= rsi_val < 40 or 60 < rsi_val <= 70:
            tech_score += 4
        elif rsi_val < 30:  # 超卖
            tech_score += 8
        elif rsi_val > 70:  # 超买
            tech_score += 2
    
    # 均线评分 (10 分)
    ma5 = calculate_ma(closes, 5)[idx]
    ma20 = calculate_ma(closes, 20)[idx]
    ma60 = calculate_ma(closes, 60)[idx] if idx >= 59 else None
    
    if ma5 and ma20:
        if ma5 > ma20:
            tech_score += 5
            if ma60 and ma5 > ma60 and ma20 > ma60:  # 多头排列
                tech_score += 5
            else:
                tech_score += 3
        else:
            tech_score += 2
    
    scores['技术面'] = min(tech_score, 40)
    
    # === 资金面评分 (25 分) ===
    money_score = 0
    
    # 成交量评分 (15 分)
    if idx >= 20:
        avg_volume = sum(volumes[idx-20:idx]) / 20
        current_volume = volumes[idx]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        if volume_ratio > 2:
            money_score += 15
        elif volume_ratio > 1.5:
            money_score += 12
        elif volume_ratio > 1:
            money_score += 8
        else:
            money_score += 4
    
    # 成交额评分 (10 分)
    if idx >= 20:
        avg_amount = sum(amounts[idx-20:idx]) / 20
        current_amount = amounts[idx]
        
        if current_amount > 1e9:  # 10 亿以上
            money_score += 10
        elif current_amount > 5e8:  # 5 亿以上
            money_score += 8
        elif current_amount > 1e8:  # 1 亿以上
            money_score += 6
        elif current_amount > 5e7:  # 5000 万以上
            money_score += 4
        else:
            money_score += 2
    
    scores['资金面'] = min(money_score, 25)
    
    # === 趋势面评分 (20 分) ===
    trend_score = 0
    
    # 短期趋势 (10 分)
    if idx >= 5:
        short_trend = (closes[idx] - closes[idx-5]) / closes[idx-5] * 100
        if short_trend > 5:
            trend_score += 10
        elif short_trend > 0:
            trend_score += 7
        elif short_trend > -5:
            trend_score += 4
        else:
            trend_score += 2
    
    # 中期趋势 (10 分)
    if idx >= 20:
        mid_trend = (closes[idx] - closes[idx-20]) / closes[idx-20] * 100
        if mid_trend > 10:
            trend_score += 10
        elif mid_trend > 5:
            trend_score += 7
        elif mid_trend > 0:
            trend_score += 5
        elif mid_trend > -10:
            trend_score += 3
        else:
            trend_score += 1
    
    scores['趋势面'] = min(trend_score, 20)
    
    # === 风险面评分 (15 分) ===
    risk_score = 15  # 基础分
    
    # 波动性扣分
    if idx >= 20:
        returns = [(closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(idx-19, idx+1)]
        volatility = np.std(returns)
        
        if volatility > 5:
            risk_score -= 8
        elif volatility > 3:
            risk_score -= 5
        elif volatility > 2:
            risk_score -= 2
    
    # 连续下跌扣分
    consecutive_down = 0
    for i in range(idx, max(0, idx-10), -1):
        if data[i]['change_pct'] < 0:
            consecutive_down += 1
        else:
            break
    
    if consecutive_down >= 5:
        risk_score -= 5
    elif consecutive_down >= 3:
        risk_score -= 2
    
    scores['风险面'] = max(risk_score, 0)
    
    # === 总分 ===
    total_score = sum(scores.values())
    
    return total_score, scores


# ==================== 交易策略 ====================

def trading_strategy(score: float, scores_detail: Dict, data: List[Dict], idx: int, 
                     position: Optional[Dict] = None) -> str:
    """
    交易策略
    
    Returns:
        'buy': 买入信号
        'sell': 卖出信号
        'hold': 持有/观望
    """
    current_price = data[idx]['close']
    
    # 如果有持仓，检查卖出条件
    if position:
        cost_price = position['cost_price']
        hold_days = position['hold_days']
        
        # 止盈 (15%)
        if current_price >= cost_price * 1.15:
            return 'sell'
        
        # 止损 (6%)
        if current_price <= cost_price * 0.94:
            return 'sell'
        
        # 追踪止损 (盈利 8% 后回撤 5%)
        if current_price >= cost_price * 1.08:
            peak_price = max(position.get('peak_price', cost_price), current_price)
            if current_price <= peak_price * 0.95:
                return 'sell'
        
        # 评分过低卖出
        if score < 50:
            return 'sell'
        
        # 持仓超过 7 天且评分低
        if hold_days >= 7 and score < 60:
            return 'sell'
        
        return 'hold'
    
    # 无持仓，检查买入条件
    if score >= 75:
        return 'buy'
    elif score >= 70 and scores_detail.get('技术面', 0) >= 30:
        return 'buy'
    
    return 'hold'


# ==================== 回测引擎 ====================

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 100000,
                 commission_rate: float = 0.0003,
                 slippage_rate: float = 0.001):
        """
        初始化回测引擎
        
        Args:
            initial_capital: 初始资金 (默认 10 万)
            commission_rate: 手续费率 (万分之三)
            slippage_rate: 滑点率 (千分之一)
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        
        self.capital = initial_capital
        self.position = None  # 当前持仓
        self.trades = []  # 交易记录
        self.equity_curve = [initial_capital]  # 资金曲线
        self.daily_returns = []  # 日收益
    
    def run(self, data: List[Dict], start_idx: int = 0, end_idx: int = None) -> Dict:
        """
        运行回测
        
        Args:
            data: 历史数据
            start_idx: 开始索引
            end_idx: 结束索引
        
        Returns:
            回测结果字典
        """
        if end_idx is None:
            end_idx = len(data)
        
        # 重置状态
        self.capital = self.initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = [self.initial_capital]
        self.daily_returns = []
        
        prev_equity = self.initial_capital
        
        for i in range(start_idx, end_idx):
            # 计算评分
            score, scores_detail = calculate_score(data, i)
            
            # 生成交易信号
            signal = trading_strategy(score, scores_detail, data, i, self.position)
            
            # 执行交易
            if signal == 'buy' and not self.position:
                # 买入
                price = data[i]['close']
                # 考虑滑点
                buy_price = price * (1 + self.slippage_rate)
                # 计算可买股数 (100 的整数倍)
                available = self.capital * 0.95 / buy_price  # 留 5% 现金
                shares = int(available // 100) * 100
                
                if shares >= 100:
                    cost = shares * buy_price
                    commission = cost * self.commission_rate
                    total_cost = cost + commission
                    
                    if total_cost <= self.capital:
                        self.capital -= total_cost
                        self.position = {
                            'code': data[i].get('code', 'UNKNOWN'),
                            'shares': shares,
                            'cost_price': buy_price,
                            'peak_price': buy_price,
                            'hold_days': 0
                        }
                        
                        self.trades.append({
                            'date': data[i]['date'],
                            'type': 'buy',
                            'price': buy_price,
                            'shares': shares,
                            'amount': cost,
                            'commission': commission,
                            'score': score
                        })
            
            elif signal == 'sell' and self.position:
                # 卖出
                price = data[i]['close']
                # 考虑滑点
                sell_price = price * (1 - self.slippage_rate)
                
                shares = self.position['shares']
                revenue = shares * sell_price
                commission = revenue * self.commission_rate
                net_revenue = revenue - commission
                
                self.capital += net_revenue
                
                # 记录交易
                profit = net_revenue - (self.position['shares'] * self.position['cost_price'] + 
                                        self.position['shares'] * self.position['cost_price'] * self.commission_rate)
                profit_pct = profit / (self.position['shares'] * self.position['cost_price']) * 100
                
                self.trades.append({
                    'date': data[i]['date'],
                    'type': 'sell',
                    'price': sell_price,
                    'shares': shares,
                    'amount': revenue,
                    'commission': commission,
                    'profit': profit,
                    'profit_pct': profit_pct,
                    'score': score
                })
                
                self.position = None
            
            # 更新持仓天数
            if self.position:
                self.position['hold_days'] += 1
                # 更新最高价
                if data[i]['close'] > self.position['peak_price']:
                    self.position['peak_price'] = data[i]['close']
            
            # 计算当日权益
            if self.position:
                equity = self.capital + self.position['shares'] * data[i]['close']
            else:
                equity = self.capital
            
            self.equity_curve.append(equity)
            
            # 计算日收益
            daily_return = (equity - prev_equity) / prev_equity * 100
            self.daily_returns.append(daily_return)
            prev_equity = equity
        
        # 生成回测结果
        return self._generate_result(data, start_idx, end_idx)
    
    def _generate_result(self, data: List[Dict], start_idx: int, end_idx: int) -> Dict:
        """生成回测结果报告"""
        final_equity = self.equity_curve[-1]
        total_return = (final_equity - self.initial_capital) / self.initial_capital * 100
        
        # 交易统计
        buy_trades = [t for t in self.trades if t['type'] == 'buy']
        sell_trades = [t for t in self.trades if t['type'] == 'sell']
        
        winning_trades = len([t for t in sell_trades if t.get('profit', 0) > 0])
        losing_trades = len([t for t in sell_trades if t.get('profit', 0) <= 0])
        
        win_rate = winning_trades / len(sell_trades) * 100 if sell_trades else 0
        
        # 风险指标
        if len(self.daily_returns) > 1:
            volatility = np.std(self.daily_returns)
            avg_return = np.mean(self.daily_returns)
            
            # 夏普比率 (假设无风险利率为 3%)
            risk_free_rate = 3 / 252  # 日化
            sharpe = (avg_return - risk_free_rate) / volatility * np.sqrt(252) if volatility > 0 else 0
            
            # 最大回撤
            peak = self.equity_curve[0]
            max_drawdown = 0
            for equity in self.equity_curve:
                if equity > peak:
                    peak = equity
                drawdown = (peak - equity) / peak * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        else:
            volatility = 0
            sharpe = 0
            max_drawdown = 0
        
        # 年化收益率
        days = end_idx - start_idx
        annualized_return = ((1 + total_return/100) ** (252/days) - 1) * 100 if days > 0 else 0
        
        return {
            'code': data[0].get('code', 'UNKNOWN') if data else 'UNKNOWN',
            'start_date': data[start_idx]['date'] if start_idx < len(data) else 'N/A',
            'end_date': data[end_idx-1]['date'] if end_idx <= len(data) else 'N/A',
            'initial_capital': self.initial_capital,
            'final_capital': final_equity,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility * 100,  # 转为百分比
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe,
            'total_trades': len(buy_trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'daily_returns': self.daily_returns
        }


def print_report(result: Dict):
    """打印回测报告"""
    print("\n" + "="*80)
    print("📊 股票策略回测报告".center(80))
    print("="*80)
    
    print(f"\n📈 回测标的：{result['code']}")
    print(f"📅 回测区间：{result['start_date']} 至 {result['end_date']}")
    print(f"💰 初始资金：¥{result['initial_capital']:,.0f}")
    print(f"💰 最终资金：¥{result['final_capital']:,.0f}")
    
    print("\n" + "-"*80)
    print("📈 收益指标")
    print("-"*80)
    print(f"  总收益率：    {result['total_return']:+.2f}%")
    print(f"  年化收益率：  {result['annualized_return']:+.2f}%")
    
    print("\n" + "-"*80)
    print("⚠️ 风险指标")
    print("-"*80)
    print(f"  波动率：      {result['volatility']:.2f}%")
    print(f"  最大回撤：    {result['max_drawdown']:.2f}%")
    print(f"  夏普比率：    {result['sharpe_ratio']:.2f}")
    
    print("\n" + "-"*80)
    print("💰 交易统计")
    print("-"*80)
    print(f"  总交易次数：  {result['total_trades']} 次")
    print(f"  盈利次数：    {result['winning_trades']} 次")
    print(f"  亏损次数：    {result['losing_trades']} 次")
    print(f"  胜率：        {result['win_rate']:.2f}%")
    
    # 打印交易记录
    if result['trades']:
        print("\n" + "-"*80)
        print("📝 交易记录")
        print("-"*80)
        print(f"{'日期':<12} {'类型':<6} {'价格':>10} {'股数':>10} {'金额':>15} {'评分':>8}")
        print("-"*80)
        
        for trade in result['trades']:
            trade_type = '买入' if trade['type'] == 'buy' else '卖出'
            amount_str = f"¥{trade['amount']:,.0f}"
            
            if trade['type'] == 'sell' and 'profit_pct' in trade:
                profit_str = f"({'+' if trade['profit'] > 0 else ''}{trade['profit_pct']:.1f}%)"
                print(f"{trade['date']:<12} {trade_type:<6} {trade['price']:>10.2f} {trade['shares']:>10} {amount_str:>15} {trade['score']:>8.1f} {profit_str}")
            else:
                print(f"{trade['date']:<12} {trade_type:<6} {trade['price']:>10.2f} {trade['shares']:>10} {amount_str:>15} {trade['score']:>8.1f}")
    
    print("\n" + "="*80)
    
    # 评级
    if result['sharpe_ratio'] >= 2:
        rating = '🏆 优秀'
    elif result['sharpe_ratio'] >= 1:
        rating = '✅ 良好'
    elif result['sharpe_ratio'] >= 0:
        rating = '⚠️ 一般'
    else:
        rating = '❌ 较差'
    
    print(f"综合评级：{rating}")
    print("="*80 + "\n")


def save_report(result: Dict, output_dir: str = None):
    """保存回测报告到文件"""
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), 'backtest_results')
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成文件名
    code = result['code']
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"backtest_{code}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    # 简化结果 (移除大数组)
    simplified = result.copy()
    simplified['equity_curve'] = result['equity_curve'][::10]  # 降采样
    simplified['daily_returns'] = result['daily_returns'][::10]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(simplified, f, ensure_ascii=False, indent=2)
    
    print(f"📁 报告已保存：{filepath}")


# ==================== 主程序 ====================

def main():
    parser = argparse.ArgumentParser(description='股票策略回测系统 - 使用采集的缓存数据')
    parser.add_argument('--code', type=str, required=True, help='股票代码 (6 位数字)')
    parser.add_argument('--days', type=int, default=250, help='回测天数 (默认 250)')
    parser.add_argument('--capital', type=float, default=100000, help='初始资金 (默认 100000)')
    parser.add_argument('--save', action='store_true', help='保存报告到文件')
    
    args = parser.parse_args()
    
    print("="*80)
    print("🚀 股票策略回测系统 v1.0 - 缓存数据版".center(80))
    print("="*80)
    print(f"作者：凯文")
    print(f"数据源：本地缓存 (5493 只股票)")
    print("="*80 + "\n")
    
    # 加载数据
    data = load_cached_data(args.code)
    
    if not data or len(data) < args.days:
        print(f"❌ 数据不足，需要至少 {args.days} 条，实际 {len(data) if data else 0} 条")
        return
    
    # 截取指定天数的数据
    data = data[-args.days:]
    
    # 运行回测
    engine = BacktestEngine(initial_capital=args.capital)
    result = engine.run(data)
    
    # 打印报告
    print_report(result)
    
    # 保存报告
    if args.save:
        save_report(result)


if __name__ == '__main__':
    from datetime import timedelta
    main()
