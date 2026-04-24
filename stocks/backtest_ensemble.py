#!/usr/bin/env python3
"""
三重确认策略回测脚本
回测周期：2022-2026
买入条件：RSI<45 + 跌幅>10%
卖出条件：持有 15 天
统计：胜率、平均收益、期望收益
"""
import json
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 配置
HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
OUTPUT_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/backtest_reports")

# 回测参数
RSI_THRESHOLD = 45  # RSI < 45
DROP_THRESHOLD = 10  # 跌幅 > 10%
HOLD_DAYS = 15  # 持有天数
START_DATE = "20220101"  # 回测开始日期
END_DATE = "20261231"  # 回测结束日期

class EnsembleBacktest:
    """三重确认策略回测器"""
    
    def __init__(self):
        self.trades = []
        self.daily_returns = []
    
    def calculate_rsi(self, closes, period=14):
        """计算 RSI 指标"""
        if len(closes) < period + 1:
            return 50
        
        deltas = [closes[i] - closes[i-1] for i in range(len(closes)-period, len(closes))]
        gains = sum(d for d in deltas if d > 0)
        losses = sum(-d for d in deltas if d < 0)
        
        if losses == 0:
            return 100
        
        rs = gains / (losses + 0.001)
        rsi = 100 - 100 / (1 + rs)
        return rsi
    
    def calculate_drop(self, closes, period=20):
        """计算近期最大跌幅"""
        if len(closes) < period:
            return 0
        
        recent = closes[-period:]
        high = max(recent)
        current = closes[-1]
        
        drop = (high - current) / high * 100
        return drop
    
    def check_buy_signal(self, closes):
        """检查买入信号"""
        if len(closes) < 60:
            return False
        
        rsi = self.calculate_rsi(closes)
        drop = self.calculate_drop(closes)
        
        return rsi < RSI_THRESHOLD and drop > DROP_THRESHOLD
    
    def backtest_stock(self, code):
        """回测单只股票"""
        try:
            with open(HISTORY_DIR / f"{code}.json") as f:
                raw = json.load(f)
            
            items, fields = raw['items'], raw['fields']
            if len(items) < 100:
                return []
            
            # 解析数据
            data = []
            for item in items:
                d = dict(zip(fields, item))
                trade_date = str(d.get('trade_date', ''))
                
                # 过滤日期范围
                if trade_date < START_DATE or trade_date > END_DATE:
                    continue
                
                c = float(d.get('close', 0))
                if c > 0:
                    data.append({
                        'date': trade_date,
                        'close': c,
                        'open': float(d.get('open', c)),
                    })
            
            if len(data) < 100:
                return []
            
            closes = [d['close'] for d in data]
            dates = [d['date'] for d in data]
            
            trades = []
            position = None
            
            # 遍历每个交易日
            for i in range(60, len(data) - HOLD_DAYS):
                # 检查是否有持仓
                if position is not None:
                    # 检查是否到达卖出日
                    if i >= position['buy_idx'] + HOLD_DAYS:
                        sell_price = closes[i]
                        buy_price = position['buy_price']
                        return_pct = (sell_price - buy_price) / buy_price * 100
                        
                        trades.append({
                            'code': code,
                            'buy_date': dates[position['buy_idx']],
                            'sell_date': dates[i],
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'return_pct': return_pct,
                            'hold_days': i - position['buy_idx']
                        })
                        position = None
                
                # 如果没有持仓，检查买入信号
                if position is None:
                    historical_closes = closes[:i+1]
                    if self.check_buy_signal(historical_closes):
                        position = {
                            'buy_idx': i,
                            'buy_price': closes[i],
                            'buy_date': dates[i]
                        }
            
            # 处理最后的持仓（如果还有）
            if position is not None and len(data) - position['buy_idx'] >= HOLD_DAYS:
                sell_idx = min(position['buy_idx'] + HOLD_DAYS, len(data) - 1)
                sell_price = closes[sell_idx]
                buy_price = position['buy_price']
                return_pct = (sell_price - buy_price) / buy_price * 100
                
                trades.append({
                    'code': code,
                    'buy_date': dates[position['buy_idx']],
                    'sell_date': dates[sell_idx],
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'return_pct': return_pct,
                    'hold_days': sell_idx - position['buy_idx']
                })
            
            return trades
            
        except Exception as e:
            print(f"回测股票 {code} 失败：{e}", flush=True)
            return []
    
    def run(self):
        """执行回测"""
        print(f"\n{'='*60}", flush=True)
        print(f"三重确认策略回测", flush=True)
        print(f"{'='*60}", flush=True)
        print(f"回测参数:", flush=True)
        print(f"  - 回测周期：{START_DATE} ~ {END_DATE}", flush=True)
        print(f"  - 买入条件：RSI < {RSI_THRESHOLD} AND 跌幅 > {DROP_THRESHOLD}%", flush=True)
        print(f"  - 卖出条件：持有 {HOLD_DAYS} 天", flush=True)
        print(f"{'='*60}\n", flush=True)
        
        # 获取所有股票文件
        stock_files = list(HISTORY_DIR.glob("*.json"))
        total_stocks = len(stock_files)
        print(f"回测股票数量：{total_stocks}", flush=True)
        
        # 回测所有股票
        all_trades = []
        for idx, stock_file in enumerate(stock_files):
            code = stock_file.stem
            trades = self.backtest_stock(code)
            all_trades.extend(trades)
            
            if (idx + 1) % 500 == 0:
                print(f"已回测：{idx + 1}/{total_stocks} (交易数：{len(all_trades)})", flush=True)
        
        print(f"\n完成回测：{len(all_trades)} 笔交易\n", flush=True)
        
        self.trades = all_trades
        
        # 计算统计指标
        stats = self.calculate_stats()
        
        # 输出结果
        self.print_results(stats)
        
        # 保存结果
        self.save_results(stats)
        
        return stats
    
    def calculate_stats(self):
        """计算统计指标"""
        if not self.trades:
            return None
        
        returns = [t['return_pct'] for t in self.trades]
        
        # 基本统计
        total_trades = len(returns)
        winning_trades = sum(1 for r in returns if r > 0)
        losing_trades = sum(1 for r in returns if r <= 0)
        
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        avg_return = np.mean(returns)
        median_return = np.median(returns)
        std_return = np.std(returns)
        
        # 收益分布
        avg_win = np.mean([r for r in returns if r > 0]) if winning_trades > 0 else 0
        avg_loss = np.mean([r for r in returns if r <= 0]) if losing_trades > 0 else 0
        
        # 盈亏比
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        # 期望收益
        expected_return = (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss)
        
        # 最大收益和最大损失
        max_win = max(returns)
        max_loss = min(returns)
        
        # 连续统计
        returns_array = np.array(returns)
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'median_return': median_return,
            'std_return': std_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'expected_return': expected_return,
            'max_win': max_win,
            'max_loss': max_loss,
            'total_return': sum(returns),
        }
    
    def print_results(self, stats):
        """打印回测结果"""
        if not stats:
            print("无交易数据", flush=True)
            return
        
        print(f"{'='*60}", flush=True)
        print(f"回测结果统计", flush=True)
        print(f"{'='*60}", flush=True)
        print(f"交易统计:", flush=True)
        print(f"  - 总交易次数：{stats['total_trades']}", flush=True)
        print(f"  - 盈利交易：{stats['winning_trades']}", flush=True)
        print(f"  - 亏损交易：{stats['losing_trades']}", flush=True)
        print(f"\n收益统计:", flush=True)
        print(f"  - 胜率：{stats['win_rate']:.2f}%", flush=True)
        print(f"  - 平均收益：{stats['avg_return']:.2f}%", flush=True)
        print(f"  - 中位收益：{stats['median_return']:.2f}%", flush=True)
        print(f"  - 收益标准差：{stats['std_return']:.2f}%", flush=True)
        print(f"\n盈亏分析:", flush=True)
        print(f"  - 平均盈利：{stats['avg_win']:.2f}%", flush=True)
        print(f"  - 平均亏损：{stats['avg_loss']:.2f}%", flush=True)
        print(f"  - 盈亏比：{stats['profit_factor']:.2f}", flush=True)
        print(f"  - 期望收益：{stats['expected_return']:.2f}%", flush=True)
        print(f"\n极值:", flush=True)
        print(f"  - 最大单笔盈利：{stats['max_win']:.2f}%", flush=True)
        print(f"  - 最大单笔亏损：{stats['max_loss']:.2f}%", flush=True)
        print(f"  - 累计收益：{stats['total_return']:.2f}%", flush=True)
        print(f"{'='*60}\n", flush=True)
    
    def save_results(self, stats):
        """保存回测结果"""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存统计结果
        stats_file = OUTPUT_DIR / f"ensemble_backtest_stats_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"统计结果已保存：{stats_file}", flush=True)
        
        # 保存交易明细
        trades_file = OUTPUT_DIR / f"ensemble_backtest_trades_{timestamp}.json"
        with open(trades_file, 'w', encoding='utf-8') as f:
            json.dump(self.trades, f, ensure_ascii=False, indent=2)
        print(f"交易明细已保存：{trades_file}", flush=True)
        
        # 保存文本报告
        report_file = OUTPUT_DIR / f"ensemble_backtest_report_{timestamp}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"三重确认策略回测报告\n")
            f.write(f"{'='*60}\n\n")
            f.write(f"回测周期：{START_DATE} ~ {END_DATE}\n")
            f.write(f"买入条件：RSI < {RSI_THRESHOLD} AND 跌幅 > {DROP_THRESHOLD}%\n")
            f.write(f"卖出条件：持有 {HOLD_DAYS} 天\n\n")
            f.write(f"交易统计:\n")
            f.write(f"  总交易次数：{stats['total_trades']}\n")
            f.write(f"  盈利交易：{stats['winning_trades']}\n")
            f.write(f"  亏损交易：{stats['losing_trades']}\n\n")
            f.write(f"收益统计:\n")
            f.write(f"  胜率：{stats['win_rate']:.2f}%\n")
            f.write(f"  平均收益：{stats['avg_return']:.2f}%\n")
            f.write(f"  中位收益：{stats['median_return']:.2f}%\n")
            f.write(f"  期望收益：{stats['expected_return']:.2f}%\n\n")
            f.write(f"盈亏分析:\n")
            f.write(f"  平均盈利：{stats['avg_win']:.2f}%\n")
            f.write(f"  平均亏损：{stats['avg_loss']:.2f}%\n")
            f.write(f"  盈亏比：{stats['profit_factor']:.2f}\n\n")
            f.write(f"极值:\n")
            f.write(f"  最大单笔盈利：{stats['max_win']:.2f}%\n")
            f.write(f"  最大单笔亏损：{stats['max_loss']:.2f}%\n")
            f.write(f"  累计收益：{stats['total_return']:.2f}%\n")
        print(f"文本报告已保存：{report_file}", flush=True)


def main():
    backtest = EnsembleBacktest()
    stats = backtest.run()
    
    return stats


if __name__ == "__main__":
    main()
