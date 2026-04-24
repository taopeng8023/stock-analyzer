#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块热点 + 资金流 + 主力 策略回测
验证策略可行性
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings
from collections import defaultdict
warnings.filterwarnings('ignore')

# 配置
HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
OUTPUT_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/backtest_results")

# 主板代码前缀
MAIN_BOARD_PREFIXES = ['600', '601', '603', '605', '000', '001', '002', '003']

# 策略参数
STRATEGY_PARAMS = {
    'money_flow_ratio_min': 1.5,  # 资金流比率
    'rsi_min': 50,
    'rsi_max': 75,
    'ret5_min': 0.03,  # 5 日涨超 3%
    'ma5_above_ma10': True,
    'hold_days': 5,  # 持有 5 天
    'stop_loss': -0.08,  # 止损 -8%
    'take_profit': 0.20,  # 止盈 +20%
    'trail_stop': 0.05,  # 止盈后回撤 5%
}

def is_main_board(code):
    """是否为主板股票"""
    for prefix in MAIN_BOARD_PREFIXES:
        if code.startswith(prefix):
            return True
    return False

def calculate_rsi(closes, period=14):
    """计算 RSI"""
    if len(closes) < period + 1:
        return 50
    
    gains = []
    losses = []
    for i in range(1, period + 1):
        delta = closes[-i] - closes[-i-1]
        if delta > 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(-delta)
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def check_signals(df):
    """检查选股信号"""
    try:
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        volumes = df['vol'].values if 'vol' in df.columns else df['amount'].values
        
        if len(closes) < 60:
            return False, None
        
        # 均线
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:])
        
        # 收益率
        ret5 = closes[-1] / closes[-6] - 1 if len(closes) >= 6 else 0
        
        # RSI
        rsi = calculate_rsi(closes)
        
        # 资金流 (简化)
        money_flows = []
        for i in range(len(closes)):
            if highs[i] > lows[i]:
                price_pos = (closes[i] - lows[i]) / (highs[i] - lows[i])
            else:
                price_pos = 0.5
            flow = volumes[i] * price_pos
            money_flows.append(flow)
        
        recent_flow = np.mean(money_flows[-5:])
        avg_flow = np.mean(money_flows[-20:])
        flow_ratio = recent_flow / avg_flow if avg_flow > 0 else 1
        
        # 检查条件
        signal = True
        reasons = []
        
        if flow_ratio < STRATEGY_PARAMS['money_flow_ratio_min']:
            signal = False
            reasons.append(f"资金流不足 ({flow_ratio:.2f})")
        
        if not (STRATEGY_PARAMS['rsi_min'] <= rsi < STRATEGY_PARAMS['rsi_max']):
            signal = False
            reasons.append(f"RSI 不符合 ({rsi:.1f})")
        
        if ret5 < STRATEGY_PARAMS['ret5_min']:
            signal = False
            reasons.append(f"5 日收益不足 ({ret5*100:.1f}%)")
        
        if STRATEGY_PARAMS['ma5_above_ma10'] and ma5 <= ma10:
            signal = False
            reasons.append("均线非多头")
        
        info = {
            'rsi': rsi,
            'ret5': ret5,
            'flow_ratio': flow_ratio,
            'ma5': ma5,
            'ma10': ma10,
            'price': closes[-1]
        }
        
        return signal, info
        
    except Exception as e:
        return False, None

def simulate_trade(df, buy_idx, hold_days, stop_loss, take_profit, trail_stop):
    """模拟单笔交易"""
    try:
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        
        if buy_idx + 1 >= len(closes):
            return None
        
        buy_price = closes[buy_idx]
        peak_price = buy_price
        
        best_sell_idx = None
        best_sell_price = None
        sell_reason = "到期卖出"
        
        for i in range(1, min(hold_days + 1, len(closes) - buy_idx)):
            sell_idx = buy_idx + i
            sell_price = closes[sell_idx]
            
            # 跟踪最高价
            if sell_price > peak_price:
                peak_price = sell_price
            
            # 计算当前收益
            current_return = (sell_price - buy_price) / buy_price
            
            # 止损检查
            if current_return <= stop_loss:
                return {
                    'sell_price': sell_price,
                    'return': current_return,
                    'hold_days': i,
                    'reason': "止损"
                }
            
            # 止盈检查
            if current_return >= take_profit:
                # 启动回撤止盈
                trail_price = peak_price * (1 - trail_stop)
                if sell_price <= trail_price:
                    return {
                        'sell_price': sell_price,
                        'return': current_return,
                        'hold_days': i,
                        'reason': "止盈"
                    }
            
            # 记录最佳卖点 (用于到期卖出)
            if best_sell_idx is None or sell_price > best_sell_price:
                best_sell_idx = sell_idx
                best_sell_price = sell_price
        
        # 到期卖出
        final_return = (best_sell_price - buy_price) / buy_price if best_sell_price else 0
        return {
            'sell_price': best_sell_price,
            'return': final_return,
            'hold_days': hold_days,
            'reason': sell_reason
        }
        
    except Exception as e:
        return None

def backtest_strategy():
    """回测策略"""
    print(f"\n{'='*80}")
    print("🔬 板块热点 + 资金流 + 主力 策略回测")
    print(f"{'='*80}")
    
    print(f"\n📋 策略参数:")
    for key, value in STRATEGY_PARAMS.items():
        print(f"  • {key}: {value}")
    
    # 加载股票列表
    stock_list_path = HISTORY_DIR / "stock_list.json"
    with open(stock_list_path, 'r') as f:
        stock_list = json.load(f)
    
    print(f"\n📊 扫描全市场：{len(stock_list)} 只股票")
    
    # 统计
    total_trades = 0
    winning_trades = 0
    losing_trades = 0
    total_return = 0
    returns = []
    hold_days_list = []
    sell_reasons = defaultdict(int)
    monthly_returns = defaultdict(list)
    
    # 遍历股票
    valid_stocks = 0
    for i, stock in enumerate(stock_list):
        code = stock.get('ts_code', '')
        if '.' in code:
            code = code.split('.')[0]
        
        # 过滤主板
        if not is_main_board(code):
            continue
        
        data_path = HISTORY_DIR / f"{code}.json"
        if not data_path.exists():
            continue
        
        try:
            with open(data_path, 'r') as f:
                data = json.load(f)
            
            if not data.get('items'):
                continue
            
            df = pd.DataFrame(data['items'], columns=data['fields'])
            df = df.drop_duplicates(subset=['trade_date'], keep='last').reset_index(drop=True)
            
            if len(df) < 100:  # 至少 100 天数据
                continue
            
            valid_stocks += 1
            
            # 遍历每个交易日
            for idx in range(60, len(df) - STRATEGY_PARAMS['hold_days'] - 5):
                df_window = df.iloc[:idx+1].reset_index(drop=True)
                
                # 检查信号
                signal, info = check_signals(df_window)
                if not signal:
                    continue
                
                # 模拟交易
                trade_result = simulate_trade(
                    df, idx,
                    STRATEGY_PARAMS['hold_days'],
                    STRATEGY_PARAMS['stop_loss'],
                    STRATEGY_PARAMS['take_profit'],
                    STRATEGY_PARAMS['trail_stop']
                )
                
                if trade_result is None:
                    continue
                
                total_trades += 1
                trade_return = trade_result['return']
                returns.append(trade_return)
                hold_days_list.append(trade_result['hold_days'])
                sell_reasons[trade_result['reason']] += 1
                
                if trade_return > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
                
                total_return += trade_return
                
                # 月度统计
                trade_date = df.iloc[idx]['trade_date'] if 'trade_date' in df.columns else str(idx)
                if len(trade_date) >= 7:
                    month = str(trade_date)[:6]  # YYYYMM
                    monthly_returns[month].append(trade_return)
            
            if (i + 1) % 500 == 0:
                print(f"进度：{i+1}/{len(stock_list)} (有效：{valid_stocks}, 交易：{total_trades})")
                
        except Exception as e:
            continue
    
    # 计算统计指标
    print(f"\n{'='*80}")
    print("📊 回测结果")
    print(f"{'='*80}")
    
    if total_trades == 0:
        print("\n❌ 没有产生交易信号")
        return
    
    returns = np.array(returns)
    
    # 基础统计
    win_rate = winning_trades / total_trades * 100
    avg_return = np.mean(returns) * 100
    total_return_pct = total_return * 100
    
    # 盈亏比
    avg_win = np.mean(returns[returns > 0]) * 100 if winning_trades > 0 else 0
    avg_loss = np.mean(returns[returns <= 0]) * 100 if losing_trades > 0 else 0
    profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    
    # 夏普比率 (简化)
    std_return = np.std(returns)
    sharpe = (avg_return / std_return) if std_return > 0 else 0
    
    # 最大回撤
    cumulative = np.cumsum(returns)
    peak = np.maximum.accumulate(cumulative)
    max_drawdown = np.min(cumulative - peak) * 100
    
    # 月度收益
    monthly_avg = {k: np.mean(v) * 100 for k, v in monthly_returns.items()}
    best_month = max(monthly_avg.items(), key=lambda x: x[1]) if monthly_avg else ("N/A", 0)
    worst_month = min(monthly_avg.items(), key=lambda x: x[1]) if monthly_avg else ("N/A", 0)
    
    print(f"\n📈 交易统计")
    print(f"  回测股票：{valid_stocks} 只")
    print(f"  总交易数：{total_trades} 次")
    print(f"  盈利交易：{winning_trades} 次 ({win_rate:.1f}%)")
    print(f"  亏损交易：{losing_trades} 次 ({100-win_rate:.1f}%)")
    
    print(f"\n💰 收益统计")
    print(f"  总收益：{total_return_pct:+.2f}%")
    print(f"  平均收益：{avg_return:+.2f}% / 次")
    print(f"  盈利时赚：{avg_win:+.2f}%")
    print(f"  亏损时亏：{avg_loss:.2f}%")
    print(f"  盈亏比：{profit_loss_ratio:.2f}:1")
    
    print(f"\n📊 风险指标")
    print(f"  夏普比率：{sharpe:.2f}")
    print(f"  最大回撤：{max_drawdown:.2f}%")
    print(f"  收益标准差：{std_return*100:.2f}%")
    
    print(f"\n📅 持有期统计")
    avg_hold = np.mean(hold_days_list)
    print(f"  平均持有：{avg_hold:.1f} 天")
    
    print(f"\n💡 卖出原因")
    for reason, count in sorted(sell_reasons.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {reason}: {count} 次 ({count/total_trades*100:.1f}%)")
    
    print(f"\n📊 月度表现")
    print(f"  最佳月份：{best_month[0]} ({best_month[1]:+.2f}%)")
    print(f"  最差月份：{worst_month[0]} ({worst_month[1]:+.2f}%)")
    
    # 收益分布
    print(f"\n📈 收益分布")
    percentiles = np.percentile(returns * 100, [10, 25, 50, 75, 90])
    print(f"  P10: {percentiles[0]:+.2f}%")
    print(f"  P25: {percentiles[1]:+.2f}%")
    print(f"  P50: {percentiles[2]:+.2f}%")
    print(f"  P75: {percentiles[3]:+.2f}%")
    print(f"  P90: {percentiles[4]:+.2f}%")
    
    # 策略可行性评估
    print(f"\n{'='*80}")
    print("🎯 策略可行性评估")
    print(f"{'='*80}")
    
    score = 0
    max_score = 100
    
    # 胜率评分 (30 分)
    if win_rate >= 70:
        score += 30
        win_eval = "优秀 ✅"
    elif win_rate >= 60:
        score += 20
        win_eval = "良好 ✅"
    elif win_rate >= 50:
        score += 10
        win_eval = "一般 ⚠️"
    else:
        win_eval = "较差 ❌"
    
    # 盈亏比评分 (25 分)
    if profit_loss_ratio >= 2.0:
        score += 25
        pl_eval = "优秀 ✅"
    elif profit_loss_ratio >= 1.5:
        score += 18
        pl_eval = "良好 ✅"
    elif profit_loss_ratio >= 1.0:
        score += 10
        pl_eval = "一般 ⚠️"
    else:
        pl_eval = "较差 ❌"
    
    # 夏普比率评分 (20 分)
    if sharpe >= 1.5:
        score += 20
        sharpe_eval = "优秀 ✅"
    elif sharpe >= 1.0:
        score += 15
        sharpe_eval = "良好 ✅"
    elif sharpe >= 0.5:
        score += 8
        sharpe_eval = "一般 ⚠️"
    else:
        sharpe_eval = "较差 ❌"
    
    # 最大回撤评分 (15 分)
    if max_drawdown > -20:
        score += 15
        dd_eval = "优秀 ✅"
    elif max_drawdown > -30:
        score += 10
        dd_eval = "良好 ✅"
    elif max_drawdown > -40:
        score += 5
        dd_eval = "一般 ⚠️"
    else:
        dd_eval = "较差 ❌"
    
    # 总收益评分 (10 分)
    if total_return_pct >= 50:
        score += 10
        total_eval = "优秀 ✅"
    elif total_return_pct >= 20:
        score += 7
        total_eval = "良好 ✅"
    elif total_return_pct >= 0:
        score += 4
        total_eval = "一般 ⚠️"
    else:
        total_eval = "较差 ❌"
    
    print(f"\n  胜率：{win_rate:.1f}% [{win_eval}] (30 分)")
    print(f"  盈亏比：{profit_loss_ratio:.2f}:1 [{pl_eval}] (25 分)")
    print(f"  夏普比率：{sharpe:.2f} [{sharpe_eval}] (20 分)")
    print(f"  最大回撤：{max_drawdown:.2f}% [{dd_eval}] (15 分)")
    print(f"  总收益：{total_return_pct:+.2f}% [{total_eval}] (10 分)")
    
    print(f"\n{'='*80}")
    print(f"🏆 综合评分：{score}/100")
    print(f"{'='*80}")
    
    if score >= 80:
        conclusion = "⭐⭐⭐⭐⭐ 强烈推荐 - 策略高度可行！"
    elif score >= 70:
        conclusion = "⭐⭐⭐⭐ 推荐 - 策略可行，可以实盘"
    elif score >= 60:
        conclusion = "⭐⭐⭐ 观望 - 策略一般，需要优化"
    elif score >= 50:
        conclusion = "⭐⭐ 谨慎 - 策略较弱，谨慎使用"
    else:
        conclusion = "⭐ 不推荐 - 策略不可行"
    
    print(f"\n💡 结论：{conclusion}")
    
    print(f"\n📝 改进建议:")
    if win_rate < 60:
        print("  • 胜率偏低，建议增加过滤条件 (如板块强度、主力排名)")
    if profit_loss_ratio < 1.5:
        print("  • 盈亏比偏低，建议优化止盈止损策略")
    if sharpe < 1.0:
        print("  • 夏普比率低，收益波动大，建议分散投资")
    if max_drawdown < -30:
        print("  • 回撤过大，建议降低仓位或增加止损")
    if total_return_pct < 20:
        print("  • 总收益偏低，建议优化选股条件")
    
    # 保存结果
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    result_path = OUTPUT_DIR / f"sector_moneyflow_backtest_{timestamp}.json"
    
    result_data = {
        'timestamp': timestamp,
        'strategy': 'sector_hotspot_moneyflow_mainforce',
        'params': STRATEGY_PARAMS,
        'stats': {
            'total_trades': int(total_trades),
            'winning_trades': int(winning_trades),
            'losing_trades': int(losing_trades),
            'win_rate': float(win_rate),
            'total_return': float(total_return_pct),
            'avg_return': float(avg_return),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_loss_ratio': float(profit_loss_ratio),
            'sharpe': float(sharpe),
            'max_drawdown': float(max_drawdown),
            'avg_hold_days': float(avg_hold),
            'score': score
        },
        'sell_reasons': dict(sell_reasons),
        'monthly_returns': monthly_avg,
        'percentiles': percentiles.tolist()
    }
    
    with open(result_path, 'w') as f:
        json.dump(result_data, f, indent=2)
    
    print(f"\n💾 结果保存：{result_path}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    backtest_strategy()
