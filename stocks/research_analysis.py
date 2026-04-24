#!/usr/bin/env python3
"""
股票研究分析示例
用于学习数据分析、量化策略回测

⚠️  仅用于个人研究学习，不得用于真实交易

用法:
    python3 research_analysis.py --demo    # 演示分析
    python3 research_analysis.py --code 600000.SH  # 分析指定股票
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from research_db import ResearchDatabase
from datetime import datetime


class StockAnalyzer:
    """股票分析器"""
    
    def __init__(self, db: ResearchDatabase):
        self.db = db
    
    def analyze_trend(self, ts_code: str, days: int = 60):
        """
        趋势分析
        
        Args:
            ts_code: 股票代码
            days: 分析天数
        """
        df = self.db.query_daily(ts_code, limit=days)
        
        if df.empty:
            print(f"❌ 无 {ts_code} 数据")
            return
        
        # 反转日期顺序（从旧到新）
        df = df.iloc[::-1].reset_index(drop=True)
        
        print(f"\n{'='*70}")
        print(f"📈 {ts_code} 趋势分析")
        print(f"{'='*70}")
        
        # 计算涨跌幅
        df['pct_change'] = df['close'].pct_change() * 100
        
        # 计算均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        
        # 统计信息
        total_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
        volatility = df['pct_change'].std()
        max_drawdown = ((df['close'] - df['close'].cummax()) / df['close'].cummax()).min() * 100
        
        print(f"\n基本统计:")
        print(f"  期间：{df['trade_date'].iloc[0]} ~ {df['trade_date'].iloc[-1]}")
        print(f"  起始价：¥{df['close'].iloc[0]:.2f}")
        print(f"  结束价：¥{df['close'].iloc[-1]:.2f}")
        print(f"  总收益：{total_return:+.2f}%")
        print(f"  波动率：{volatility:.2f}%")
        print(f"  最大回撤：{max_drawdown:.2f}%")
        
        # 均线信号
        current_price = df['close'].iloc[-1]
        ma5 = df['ma5'].iloc[-1]
        ma20 = df['ma20'].iloc[-1]
        
        print(f"\n均线分析:")
        print(f"  当前价格：¥{current_price:.2f}")
        print(f"  MA5: ¥{ma5:.2f} {'↑' if current_price > ma5 else '↓'}")
        print(f"  MA20: ¥{ma20:.2f} {'↑' if current_price > ma20 else '↓'}")
        
        # 金叉死叉
        if len(df) >= 20:
            recent = df.tail(5)
            above_ma20 = (recent['close'] > recent['ma20']).sum()
            print(f"  近 5 日站上 MA20: {above_ma20}/5 天")
        
        print(f"{'='*70}")
    
    def analyze_moneyflow(self, ts_code: str, days: int = 30):
        """
        资金流分析
        
        Args:
            ts_code: 股票代码
            days: 分析天数
        """
        flow_df = self.db.query_moneyflow(ts_code, limit=days)
        
        if flow_df.empty:
            print(f"❌ 无 {ts_code} 资金流数据")
            return
        
        print(f"\n{'='*70}")
        print(f"💰 {ts_code} 资金流分析")
        print(f"{'='*70}")
        
        # 统计
        total_net = flow_df['net_mf_amount'].sum()
        avg_net = flow_df['net_mf_amount'].mean()
        positive_days = (flow_df['net_mf_amount'] > 0).sum()
        
        print(f"\n资金流统计:")
        print(f"  期间：{flow_df['trade_date'].iloc[-1]} ~ {flow_df['trade_date'].iloc[0]}")
        print(f"  累计净流入：{total_net:.2f}万")
        print(f"  日均净流入：{avg_net:.2f}万")
        print(f"  净流入天数：{positive_days}/{len(flow_df)}")
        print(f"  净流入占比：{positive_days/len(flow_df)*100:.1f}%")
        
        # 特大单分析
        if 'buy_elg_amount' in flow_df.columns:
            total_buy_elg = flow_df['buy_elg_amount'].sum()
            total_sell_elg = flow_df['sell_elg_amount'].sum()
            net_elg = total_buy_elg - total_sell_elg
            
            print(f"\n特大单分析:")
            print(f"  特大单买入：{total_buy_elg:.2f}万")
            print(f"  特大单卖出：{total_sell_elg:.2f}万")
            print(f"  特大单净额：{net_elg:.2f}万")
        
        # 近期趋势
        recent_5d = flow_df.head(5)['net_mf_amount'].sum()
        recent_10d = flow_df.head(10)['net_mf_amount'].sum()
        
        print(f"\n近期趋势:")
        print(f"  近 5 日净流入：{recent_5d:.2f}万")
        print(f"  近 10 日净流入：{recent_10d:.2f}万")
        
        print(f"{'='*70}")
    
    def backtest_ma_strategy(self, ts_code: str, days: int = 250):
        """
        简单均线策略回测
        
        策略：
        - 买入：价格上穿 MA20
        - 卖出：价格下穿 MA20
        
        Args:
            ts_code: 股票代码
            days: 回测天数
        """
        df = self.db.query_daily(ts_code, limit=days)
        
        if df.empty or len(df) < 60:
            print(f"❌ 数据不足，无法回测")
            return
        
        # 反转日期
        df = df.iloc[::-1].reset_index(drop=True)
        
        print(f"\n{'='*70}")
        print(f"🧪 MA20 策略回测 ({ts_code})")
        print(f"{'='*70}")
        print(f"策略：价格上穿 MA20 买入，下穿 MA20 卖出")
        print(f"回测期间：{df['trade_date'].iloc[0]} ~ {df['trade_date'].iloc[-1]}")
        
        # 计算 MA20
        df['ma20'] = df['close'].rolling(20).mean()
        
        # 生成信号
        df['signal'] = 0
        for i in range(21, len(df)):
            if df['close'].iloc[i-1] < df['ma20'].iloc[i-1] and \
               df['close'].iloc[i] > df['ma20'].iloc[i]:
                df.loc[df.index[i], 'signal'] = 1  # 买入
            elif df['close'].iloc[i-1] > df['ma20'].iloc[i-1] and \
                 df['close'].iloc[i] < df['ma20'].iloc[i]:
                df.loc[df.index[i], 'signal'] = -1  # 卖出
        
        # 计算收益
        position = 0
        profit = 0
        trades = []
        
        for i in range(1, len(df)):
            if df['signal'].iloc[i] == 1 and position == 0:
                # 买入
                position = df['close'].iloc[i]
                trades.append(('买入', df['trade_date'].iloc[i], position))
            elif df['signal'].iloc[i] == -1 and position > 0:
                # 卖出
                profit += df['close'].iloc[i] - position
                trades.append(('卖出', df['trade_date'].iloc[i], df['close'].iloc[i]))
                position = 0
        
        # 如果仍持有，按最新价计算
        if position > 0:
            profit += df['close'].iloc[-1] - position
            trades.append(('当前持有', df['trade_date'].iloc[-1], df['close'].iloc[-1]))
        
        # 买入持有收益
        buy_hold_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
        
        # 策略收益
        strategy_return = (profit / df['close'].iloc[0]) * 100
        
        print(f"\n回测结果:")
        print(f"  交易次数：{len(trades)}")
        print(f"  策略收益：{strategy_return:+.2f}%")
        print(f"  买入持有：{buy_hold_return:+.2f}%")
        print(f"  超额收益：{strategy_return - buy_hold_return:+.2f}%")
        
        # 显示交易记录
        if trades:
            print(f"\n交易记录:")
            for trade in trades[:10]:  # 显示前 10 笔
                print(f"  {trade[0]}: {trade[1]} @ ¥{trade[2]:.2f}")
        
        print(f"{'='*70}")
        print(f"⚠️  回测说明:")
        print(f"  - 未考虑交易成本")
        print(f"  - 假设理想成交")
        print(f"  - 历史业绩不代表未来")
        print(f"  - 仅用于学习，不得用于真实交易")
        print(f"{'='*70}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='股票研究分析')
    parser.add_argument('--demo', action='store_true', help='演示分析')
    parser.add_argument('--code', type=str, help='分析指定股票')
    parser.add_argument('--days', type=int, default=60, help='分析天数')
    
    args = parser.parse_args()
    
    db = ResearchDatabase()
    analyzer = StockAnalyzer(db)
    
    if args.demo:
        # 演示分析
        print("\n🎓 研究分析演示")
        print("="*70)
        
        # 检查是否有数据
        stats = db.get_stats()
        if stats['daily_bar_count'] == 0:
            print("\n⚠️  数据库为空，先生成示例数据:")
            print("   python3 research_import.py --sample --days 250")
            return
        
        # 获取一只股票
        stock_df = db.query_stock_list()
        if stock_df.empty:
            print("❌ 无股票数据")
            return
        
        ts_code = stock_df.iloc[0]['ts_code']
        print(f"\n分析股票：{ts_code}")
        
        # 趋势分析
        analyzer.analyze_trend(ts_code, days=args.days)
        
        # 资金流分析
        analyzer.analyze_moneyflow(ts_code, days=min(30, args.days))
        
        # 策略回测
        analyzer.backtest_ma_strategy(ts_code, days=250)
        
        return
    
    if args.code:
        ts_code = args.code.upper()
        if not ts_code.endswith('.SH') and not ts_code.endswith('.SZ'):
            ts_code += '.SH' if ts_code.startswith('6') else '.SZ'
        
        analyzer.analyze_trend(ts_code, days=args.days)
        analyzer.analyze_moneyflow(ts_code, days=min(30, args.days))
        analyzer.backtest_ma_strategy(ts_code, days=250)
        return
    
    # 默认帮助
    parser.print_help()


if __name__ == '__main__':
    main()
