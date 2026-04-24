#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
选股系统 V3.0 回测 - 双均线金叉 + 移动止盈
基于 V3.0 选股策略，集成移动止盈和完整回测指标

策略说明:
- 买入：MA15 金叉 MA20 + 五重过滤 (可选)
- 卖出：移动止盈 (从最高价回撤 10%) 或 死叉卖出

用法:
    python backtest_v3.py 000001.SZ --token <Tushare Token>
    python backtest_v3.py --all --sample 500  # 全市场抽样回测
"""

import pandas as pd
import numpy as np
import tushare as ts
from datetime import datetime
import argparse
import warnings
import json
from pathlib import Path
import time
from typing import List, Dict, Optional

warnings.filterwarnings('ignore')

# ============== 配置区域 ==============
TS_TOKEN = 'your_tushare_token_here'

# V3.0 默认参数
DEFAULT_SHORT_MA = 15  # V3.0 使用 MA15
DEFAULT_LONG_MA = 20   # V3.0 使用 MA20
DEFAULT_PROFIT_STOP = 0.10
DEFAULT_START_DATE = '20230101'
DEFAULT_END_DATE = '20260329'
DEFAULT_INITIAL_CAPITAL = 100000
DEFAULT_FEE_RATE = 0.0003

# 五重过滤权重
FILTER_WEIGHTS = {
    'volume': 1,      # 成交量>1.5 倍均量
    'trend': 1,       # 股价>MA200
    'rsi': 1,         # RSI 50-75
    'macd': 1,        # MACD 金叉
    'slope': 1        # 均线斜率向上
}
MIN_FILTER_SCORE = 3  # 至少 3 分 (60%)

# ======================================


class V3Strategy:
    """V3.0 选股策略"""
    
    def __init__(self, short_ma=15, long_ma=20, use_filters=True, min_score=3):
        self.short_ma = short_ma
        self.long_ma = long_ma
        self.use_filters = use_filters
        self.min_score = min_score
    
    def calc_ma(self, data, period, idx):
        """计算移动平均线"""
        if idx < period - 1:
            return None
        return data['close'].iloc[idx-period+1:idx+1].mean()
    
    def calc_ema(self, data, period, idx):
        """计算 EMA"""
        if idx < period - 1:
            return None
        multiplier = 2 / (period + 1)
        ema = data['close'].iloc[idx-period+1]
        for i in range(idx-period+2, idx+1):
            ema = (data['close'].iloc[i] - ema) * multiplier + ema
        return ema
    
    def calc_rsi(self, data, period, idx):
        """计算 RSI"""
        if idx < period:
            return None
        
        gains, losses = [], []
        for i in range(idx-period+1, idx+1):
            change = data['close'].iloc[i] - data['close'].iloc[i-1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def check_filters(self, data, idx):
        """五重过滤检查"""
        score = 0
        
        # 1. 成交量过滤 (>1.5 倍均量)
        volume = data['volume'].iloc[idx]
        avg_volume = data['volume'].iloc[idx-20:idx].mean()
        if avg_volume > 0 and volume > avg_volume * 1.5:
            score += FILTER_WEIGHTS['volume']
        
        # 2. 趋势过滤 (股价>MA200)
        ma200 = self.calc_ma(data, 200, idx)
        current_price = data['close'].iloc[idx]
        if ma200 and current_price > ma200:
            score += FILTER_WEIGHTS['trend']
        
        # 3. RSI 过滤 (50-75)
        rsi = self.calc_rsi(data, 14, idx)
        if rsi and 50 < rsi < 75:
            score += FILTER_WEIGHTS['rsi']
        
        # 4. MACD 过滤 (EMA12 > EMA26)
        ema12 = self.calc_ema(data, 12, idx)
        ema26 = self.calc_ema(data, 26, idx)
        if ema12 and ema26 and ema12 > ema26:
            score += FILTER_WEIGHTS['macd']
        
        # 5. 均线斜率 (MA15/MA20 向上)
        ma15 = self.calc_ma(data, self.short_ma, idx)
        ma20 = self.calc_ma(data, self.long_ma, idx)
        ma15_prev = self.calc_ma(data, self.short_ma, idx-3)
        ma20_prev = self.calc_ma(data, self.long_ma, idx-3)
        if ma15_prev and ma20_prev:
            if ma15 > ma15_prev and ma20 > ma20_prev:
                score += FILTER_WEIGHTS['slope']
        
        return score
    
    def signal(self, data, idx):
        """
        生成交易信号
        返回：'买入' | '卖出' | '持有'
        """
        if idx < self.long_ma + 20:  # 至少需要 200 日数据用于过滤
            return '持有'
        
        # 计算均线
        ma_short = self.calc_ma(data, self.short_ma, idx)
        ma_long = self.calc_ma(data, self.long_ma, idx)
        ma_short_prev = self.calc_ma(data, self.short_ma, idx-1)
        ma_long_prev = self.calc_ma(data, self.long_ma, idx-1)
        
        if ma_short is None or ma_long is None:
            return '持有'
        
        # 金叉：短均线上穿长均线
        if ma_short_prev <= ma_long_prev and ma_short > ma_long:
            # 检查五重过滤
            if self.use_filters:
                filter_score = self.check_filters(data, idx)
                if filter_score >= self.min_score:
                    return '买入'
            else:
                return '买入'
        
        # 死叉：短均线下穿长均线
        if ma_short_prev >= ma_long_prev and ma_short < ma_long:
            return '卖出'
        
        return '持有'


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital=DEFAULT_INITIAL_CAPITAL, fee_rate=DEFAULT_FEE_RATE):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.current_capital = initial_capital
        self.position = {}
        self.trades = []
        self.equity_curve = []
        
        # 移动止盈相关
        self.cost_price = 0
        self.highest_price = 0
        self.profit_stop_threshold = DEFAULT_PROFIT_STOP
    
    def set_profit_stop(self, threshold):
        """设置移动止盈阈值"""
        self.profit_stop_threshold = threshold
    
    def execute_buy(self, data, idx, reason='策略信号', score=0):
        """执行买入操作"""
        if self.position:
            return False
        
        price = data['close'].iloc[idx]
        date = data['date'].iloc[idx]
        code = data.get('ts_code', 'UNKNOWN')
        
        # 计算可买数量 (95% 仓位)
        available_capital = self.current_capital * 0.95
        shares = int(available_capital / price / 100) * 100
        
        if shares <= 0:
            return False
        
        amount = shares * price
        fee = amount * self.fee_rate
        
        self.current_capital -= (amount + fee)
        self.position[code] = {
            'shares': shares,
            'cost': price,
            'market_value': amount
        }
        
        self.cost_price = price
        self.highest_price = price
        
        self.trades.append({
            'date': date,
            'code': code,
            'operation': '买入',
            'price': price,
            'shares': shares,
            'amount': amount,
            'fee': fee,
            'reason': reason,
            'filter_score': score
        })
        
        return True
    
    def execute_sell(self, data, idx, reason='策略信号'):
        """执行卖出操作"""
        if not self.position:
            return False
        
        price = data['close'].iloc[idx]
        date = data['date'].iloc[idx]
        code = list(self.position.keys())[0]
        pos_info = self.position[code]
        
        shares = pos_info['shares']
        amount = shares * price
        fee = amount * self.fee_rate
        profit = amount - (shares * pos_info['cost']) - fee
        profit_rate = profit / (shares * pos_info['cost']) * 100
        
        self.current_capital += (amount - fee)
        
        self.trades.append({
            'date': date,
            'code': code,
            'operation': '卖出',
            'price': price,
            'shares': shares,
            'amount': amount,
            'fee': fee,
            'profit': profit,
            'profit_rate': profit_rate,
            'reason': reason
        })
        
        self.position = {}
        self.cost_price = 0
        self.highest_price = 0
        
        return True
    
    def check_profit_stop(self, current_price):
        """检查移动止盈条件"""
        if not self.position:
            return False
        
        if current_price > self.highest_price:
            self.highest_price = current_price
        
        drawdown = (self.highest_price - current_price) / self.highest_price
        return drawdown >= self.profit_stop_threshold
    
    def update_equity_curve(self, data, idx):
        """更新资金曲线"""
        date = data['date'].iloc[idx]
        current_price = data['close'].iloc[idx]
        
        position_value = 0
        if self.position:
            code = list(self.position.keys())[0]
            position_value = self.position[code]['shares'] * current_price
        
        total_assets = self.current_capital + position_value
        return_rate = (total_assets - self.initial_capital) / self.initial_capital
        
        self.equity_curve.append({
            'date': date,
            'total_assets': total_assets,
            'return_rate': return_rate,
            'has_position': bool(self.position)
        })
    
    def run_backtest(self, strategy, data, print_log=True):
        """运行完整回测"""
        if print_log:
            print(f"\n🚀 开始回测...")
            print(f"   策略：V3.0 选股策略 (MA{strategy.short_ma}/MA{strategy.long_ma})")
            print(f"   五重过滤：{'启用' if strategy.use_filters else '禁用'}")
            if strategy.use_filters:
                print(f"   最低分数：{strategy.min_score}分")
            print(f"   初始资金：¥{self.initial_capital:,.2f}")
            print(f"   数据范围：{data['date'].min()} ~ {data['date'].max()}")
            print(f"   数据条数：{len(data)}")
            print("-" * 70)
        
        # 重置状态
        self.current_capital = self.initial_capital
        self.position = {}
        self.trades = []
        self.equity_curve = []
        self.cost_price = 0
        self.highest_price = 0
        
        # 逐日回测
        for i in range(len(data)):
            current_price = data['close'].iloc[i]
            
            # 获取策略信号
            signal = strategy.signal(data, i)
            
            # 检查移动止盈（优先）
            if self.position and self.check_profit_stop(current_price):
                self.execute_sell(data, i, reason='移动止盈')
                if print_log:
                    trade = self.trades[-1]
                    print(f"📉 {trade['date'].strftime('%Y-%m-%d')} 移动止盈 卖出 @ ¥{trade['price']:.2f} "
                          f"盈利：¥{trade['profit']:.2f} ({trade['profit_rate']:+.2f}%)")
            
            # 执行策略信号
            elif signal == '买入' and not self.position:
                filter_score = strategy.check_filters(data, i) if strategy.use_filters else 0
                if self.execute_buy(data, i, reason='金叉信号', score=filter_score):
                    if print_log:
                        trade = self.trades[-1]
                        print(f"📈 {trade['date'].strftime('%Y-%m-%d')} 金叉买入 @ ¥{trade['price']:.2f} "
                              f"{trade['shares']}股 (过滤得分：{trade['filter_score']}分)")
            
            elif signal == '卖出' and self.position:
                self.execute_sell(data, i, reason='死叉信号')
                if print_log:
                    trade = self.trades[-1]
                    print(f"📉 {trade['date'].strftime('%Y-%m-%d')} 死叉卖出 @ ¥{trade['price']:.2f} "
                          f"盈利：¥{trade['profit']:.2f} ({trade['profit_rate']:+.2f}%)")
            
            self.update_equity_curve(data, i)
        
        # 处理剩余持仓
        if self.position:
            code = list(self.position.keys())[0]
            last_price = data['close'].iloc[-1]
            last_date = data['date'].iloc[-1]
            position_value = self.position[code]['shares'] * last_price
            unrealized_profit = position_value - (self.position[code]['shares'] * self.position[code]['cost'])
            
            if print_log:
                print(f"\n⚠️  回测结束仍有持仓")
                print(f"   最后收盘价：¥{last_price:.2f}")
                print(f"   未实现盈亏：¥{unrealized_profit:.2f}")
            
            self.trades.append({
                'date': last_date,
                'code': code,
                'operation': '持仓',
                'price': last_price,
                'shares': self.position[code]['shares'],
                'market_value': position_value,
                'unrealized_profit': unrealized_profit
            })
        
        return self.generate_report()
    
    def calculate_return_metrics(self):
        """计算收益指标"""
        if not self.equity_curve:
            return {}
        
        return_rates = [d['return_rate'] for d in self.equity_curve]
        total_return = return_rates[-1] if return_rates else 0
        trading_days = len(return_rates)
        annual_return = (1 + total_return) ** (252 / max(trading_days, 1)) - 1
        final_assets = self.equity_curve[-1]['total_assets'] if self.equity_curve else self.initial_capital
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'trading_days': trading_days,
            'final_assets': final_assets
        }
    
    def calculate_risk_metrics(self):
        """计算风险指标"""
        if len(self.equity_curve) < 2:
            return {'max_drawdown': 0, 'volatility': 0, 'sharpe_ratio': 0}
        
        return_rates = [d['return_rate'] for d in self.equity_curve]
        total_assets = [self.initial_capital * (1 + r) for r in return_rates]
        
        peak = 0
        max_drawdown = 0
        for assets in total_assets:
            if assets > peak:
                peak = assets
            drawdown = (peak - assets) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        daily_returns = np.diff(return_rates)
        volatility = np.std(daily_returns) * np.sqrt(252) if len(daily_returns) > 0 else 0
        risk_free_rate = 0.03
        sharpe_ratio = (np.mean(daily_returns) * 252 - risk_free_rate) / volatility if volatility > 0 else 0
        
        return {
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio
        }
    
    def calculate_trade_metrics(self):
        """计算交易指标"""
        buy_trades = [t for t in self.trades if t['operation'] == '买入']
        sell_trades = [t for t in self.trades if t['operation'] == '卖出']
        
        trade_count = len(sell_trades)
        profitable_trades = len([t for t in sell_trades if t['profit'] > 0])
        win_rate = profitable_trades / trade_count * 100 if trade_count > 0 else 0
        total_profit = sum([t['profit'] for t in sell_trades])
        gross_profit = sum([t['profit'] for t in sell_trades if t['profit'] > 0])
        gross_loss = abs(sum([t['profit'] for t in sell_trades if t['profit'] < 0]))
        profit_loss_ratio = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return {
            'trade_count': trade_count,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'total_profit': total_profit,
            'buy_count': len(buy_trades),
            'profitable_count': profitable_trades,
            'losing_count': trade_count - profitable_trades
        }
    
    def generate_report(self):
        """生成回测报告"""
        return_metrics = self.calculate_return_metrics()
        risk_metrics = self.calculate_risk_metrics()
        trade_metrics = self.calculate_trade_metrics()
        
        report = {
            'return_metrics': return_metrics,
            'risk_metrics': risk_metrics,
            'trade_metrics': trade_metrics,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
        
        print("\n" + "=" * 70)
        print("📊 回测报告")
        print("=" * 70)
        
        print(f"""
📈 收益统计
   初始资金：    ¥{self.initial_capital:>12,.2f}
   最终价值：    ¥{return_metrics.get('final_assets', 0):>12,.2f}
   总盈利：      ¥{trade_metrics.get('total_profit', 0):>12,.2f}
   总收益率：    {return_metrics.get('total_return', 0)*100:>12.2f}%
   年化收益：    {return_metrics.get('annual_return', 0)*100:>12.2f}%

📊 交易统计
   总交易次数：  {trade_metrics.get('trade_count', 0):>12} 次
   盈利次数：    {trade_metrics.get('profitable_count', 0):>12} 次
   亏损次数：    {trade_metrics.get('losing_count', 0):>12} 次
   胜率：        {trade_metrics.get('win_rate', 0):>12.2f}%
   盈亏比：      {trade_metrics.get('profit_loss_ratio', 0):>12.2f}

⚠️  风险指标
   最大回撤：    {risk_metrics.get('max_drawdown', 0)*100:>12.2f}%
   波动率：      {risk_metrics.get('volatility', 0)*100:>12.2f}%
   夏普比率：    {risk_metrics.get('sharpe_ratio', 0):>12.2f}
""")
        
        print("=" * 70)
        
        return report
    
    def export_trades(self, filename):
        """导出交易记录"""
        if self.trades:
            df = pd.DataFrame(self.trades)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n💾 交易记录已保存至：{filename}")
    
    def export_equity_curve(self, filename):
        """导出资金曲线"""
        if self.equity_curve:
            df = pd.DataFrame(self.equity_curve)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"💾 资金曲线已保存至：{filename}")


def fetch_data(stock_code, start_date, end_date):
    """获取历史行情数据"""
    print(f"📊 正在获取 {stock_code} 的历史行情...")
    
    try:
        ts.set_token(TS_TOKEN)
        pro = ts.pro_api()
        
        df = pro.daily(ts_code=stock_code, start_date=start_date, end_date=end_date)
        
        if df.empty:
            print(f"❌ 未获取到 {stock_code} 的数据")
            return None
        
        df = df.sort_values('trade_date').reset_index(drop=True)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df = df.rename(columns={'trade_date': 'date'})
        
        print(f"✅ 获取到 {len(df)} 条数据 ({df['date'].min()} ~ {df['date'].max()})")
        return df
        
    except Exception as e:
        print(f"❌ 获取数据失败：{e}")
        print("💡 请确保已设置正确的 Tushare Token")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='选股系统 V3.0 回测 - 双均线金叉 + 移动止盈',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单只股票回测
  python backtest_v3.py 000001.SZ --token <你的 Tushare Token>
  
  # 禁用五重过滤 (简单策略)
  python backtest_v3.py 000001.SZ --no-filters --token <Token>
  
  # 自定义参数
  python backtest_v3.py 600519.SH --short-ma 10 --long-ma 30 --profit-stop 0.15
  
  # 导出交易记录
  python backtest_v3.py 000001.SZ --export --token <Token>
        """
    )
    
    parser.add_argument('stock_code', nargs='?', help='股票代码 (如：000001.SZ, 600519.SH)')
    parser.add_argument('--short-ma', type=int, default=DEFAULT_SHORT_MA,
                       help=f'短期均线周期 (默认：{DEFAULT_SHORT_MA})')
    parser.add_argument('--long-ma', type=int, default=DEFAULT_LONG_MA,
                       help=f'长期均线周期 (默认：{DEFAULT_LONG_MA})')
    parser.add_argument('--profit-stop', type=float, default=DEFAULT_PROFIT_STOP,
                       help=f'移动止盈阈值 (默认：{DEFAULT_PROFIT_STOP})')
    parser.add_argument('--start-date', type=str, default=DEFAULT_START_DATE,
                       help=f'开始日期 (默认：{DEFAULT_START_DATE})')
    parser.add_argument('--end-date', type=str, default=DEFAULT_END_DATE,
                       help=f'结束日期 (默认：{DEFAULT_END_DATE})')
    parser.add_argument('--capital', type=float, default=DEFAULT_INITIAL_CAPITAL,
                       help=f'初始资金 (默认：{DEFAULT_INITIAL_CAPITAL})')
    parser.add_argument('--fee-rate', type=float, default=DEFAULT_FEE_RATE,
                       help=f'手续费率 (默认：{DEFAULT_FEE_RATE})')
    parser.add_argument('--token', type=str, default=None,
                       help='Tushare Token')
    parser.add_argument('--no-filters', action='store_true',
                       help='禁用五重过滤 (仅使用金叉信号)')
    parser.add_argument('--min-score', type=int, default=MIN_FILTER_SCORE,
                       help=f'最低过滤分数 (默认：{MIN_FILTER_SCORE})')
    parser.add_argument('--no-log', action='store_true',
                       help='不打印交易日志')
    parser.add_argument('--export', action='store_true',
                       help='导出交易记录和资金曲线')
    
    args = parser.parse_args()
    
    global TS_TOKEN
    if args.token:
        TS_TOKEN = args.token
    
    if TS_TOKEN == 'your_tushare_token_here':
        print("❌ 错误：未设置 Tushare Token")
        print("💡 请在脚本中设置 TS_TOKEN 或使用 --token 参数")
        print("💡 获取 Token: https://tushare.pro/user/token")
        return
    
    if not args.stock_code:
        print("❌ 错误：请提供股票代码")
        print("💡 用法：python backtest_v3.py 000001.SZ --token <Token>")
        return
    
    df = fetch_data(args.stock_code, args.start_date, args.end_date)
    if df is None:
        return
    
    strategy = V3Strategy(
        short_ma=args.short_ma,
        long_ma=args.long_ma,
        use_filters=not args.no_filters,
        min_score=args.min_score
    )
    
    engine = BacktestEngine(initial_capital=args.capital, fee_rate=args.fee_rate)
    engine.set_profit_stop(args.profit_stop)
    
    report = engine.run_backtest(strategy, df, print_log=not args.no_log)
    
    if args.export:
        engine.export_trades(f"backtest_v3_{args.stock_code.replace('.', '_')}_trades.csv")
        engine.export_equity_curve(f"backtest_v3_{args.stock_code.replace('.', '_')}_curve.csv")


if __name__ == '__main__':
    main()
