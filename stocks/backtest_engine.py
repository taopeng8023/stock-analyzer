#!/usr/bin/env python3
"""
鹏总选股系统 - 策略回测引擎 v1.0
支持多种策略回测、收益统计、风险评估

鹏总专用 - 2026 年 3 月 26 日
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import urllib.request
import urllib.error


class BacktestEngine:
    """策略回测引擎"""
    
    def __init__(self, initial_capital: float = 1000000.0):
        """
        初始化回测引擎
        
        参数:
            initial_capital: 初始资金 (默认 100 万)
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}  # 持仓
        self.trades = []  # 交易记录
        self.daily_values = []  # 每日净值
        self.output_dir = "/home/admin/.openclaw/workspace/stocks/backtest_results/"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def reset(self):
        """重置回测状态"""
        self.capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.daily_values = []
    
    def buy(self, stock_code: str, stock_name: str, price: float, shares: int, date: str, reason: str = ""):
        """买入"""
        cost = price * shares
        commission = max(5, cost * 0.0003)  # 万三佣金，最低 5 元
        
        if cost + commission > self.capital:
            return False
        
        self.capital -= (cost + commission)
        
        if stock_code in self.positions:
            self.positions[stock_code]['shares'] += shares
            self.positions[stock_code]['avg_price'] = (
                (self.positions[stock_code]['avg_price'] * self.positions[stock_code]['shares'] + cost) /
                (self.positions[stock_code]['shares'] + shares)
            )
        else:
            self.positions[stock_code] = {
                'code': stock_code,
                'name': stock_name,
                'shares': shares,
                'avg_price': price,
                'buy_date': date,
            }
        
        self.trades.append({
            'date': date,
            'type': 'BUY',
            'code': stock_code,
            'name': stock_name,
            'price': price,
            'shares': shares,
            'cost': cost + commission,
            'reason': reason,
        })
        
        return True
    
    def sell(self, stock_code: str, price: float, shares: int, date: str, reason: str = ""):
        """卖出"""
        if stock_code not in self.positions:
            return False
        
        pos = self.positions[stock_code]
        if shares > pos['shares']:
            shares = pos['shares']
        
        revenue = price * shares
        commission = max(5, revenue * 0.0003)
        stamp_duty = revenue * 0.001  # 千一印花税
        
        self.capital += (revenue - commission - stamp_duty)
        
        self.positions[stock_code]['shares'] -= shares
        
        if self.positions[stock_code]['shares'] <= 0:
            del self.positions[stock_code]
        
        self.trades.append({
            'date': date,
            'type': 'SELL',
            'code': stock_code,
            'name': pos['name'],
            'price': price,
            'shares': shares,
            'revenue': revenue - commission - stamp_duty,
            'profit': (price - pos['avg_price']) * shares - commission - stamp_duty,
            'reason': reason,
        })
        
        return True
    
    def update_daily_value(self, date: str, prices: dict):
        """更新每日净值"""
        total_value = self.capital
        
        for code, pos in self.positions.items():
            if code in prices:
                total_value += pos['shares'] * prices[code]
        
        self.daily_values.append({
            'date': date,
            'value': total_value,
            'capital': self.capital,
            'position_value': total_value - self.capital,
        })
    
    def calculate_metrics(self) -> dict:
        """计算回测指标"""
        if not self.daily_values:
            return {}
        
        # 总收益
        final_value = self.daily_values[-1]['value']
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        # 年化收益
        days = (datetime.strptime(self.daily_values[-1]['date'], '%Y-%m-%d') - 
                datetime.strptime(self.daily_values[0]['date'], '%Y-%m-%d')).days
        annual_return = ((final_value / self.initial_capital) ** (365 / max(days, 1)) - 1) * 100
        
        # 最大回撤
        max_value = 0
        max_drawdown = 0
        for dv in self.daily_values:
            if dv['value'] > max_value:
                max_value = dv['value']
            drawdown = (max_value - dv['value']) / max_value * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 胜率
        profitable_trades = sum(1 for t in self.trades if t['type'] == 'SELL' and t.get('profit', 0) > 0)
        total_trades = sum(1 for t in self.trades if t['type'] == 'SELL')
        win_rate = profitable_trades / max(total_trades, 1) * 100
        
        # 夏普比率 (简化版)
        if len(self.daily_values) > 1:
            daily_returns = []
            for i in range(1, len(self.daily_values)):
                ret = (self.daily_values[i]['value'] - self.daily_values[i-1]['value']) / self.daily_values[i-1]['value']
                daily_returns.append(ret)
            
            if daily_returns:
                avg_return = sum(daily_returns) / len(daily_returns)
                std_return = (sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns)) ** 0.5
                sharpe = (avg_return * 252) / (std_return * (252 ** 0.5)) if std_return > 0 else 0
            else:
                sharpe = 0
        else:
            sharpe = 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe,
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'trading_days': days,
        }
    
    def generate_report(self, output_file: str = None) -> str:
        """生成回测报告"""
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"{self.output_dir}/backtest_report_{timestamp}.json"
        
        metrics = self.calculate_metrics()
        
        report = {
            'backtest_info': {
                'initial_capital': self.initial_capital,
                'start_date': self.daily_values[0]['date'] if self.daily_values else 'N/A',
                'end_date': self.daily_values[-1]['date'] if self.daily_values else 'N/A',
                'trading_days': len(self.daily_values),
            },
            'performance_metrics': metrics,
            'trades': self.trades,
            'daily_values': self.daily_values,
            'current_positions': list(self.positions.values()),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return output_file
    
    def print_report(self):
        """打印回测报告"""
        metrics = self.calculate_metrics()
        
        print("\n" + "="*80)
        print("  鹏总选股系统 - 策略回测报告")
        print("="*80)
        print(f"\n📊 基本信息")
        print(f"   初始资金：¥{self.initial_capital:,.2f}")
        print(f"   最终净值：¥{metrics.get('final_value', 0):,.2f}")
        print(f"   交易天数：{metrics.get('trading_days', 0)}")
        
        print(f"\n💰 收益指标")
        print(f"   总收益率：{metrics.get('total_return', 0):+.2f}%")
        print(f"   年化收益：{metrics.get('annual_return', 0):+.2f}%")
        print(f"   最大回撤：{metrics.get('max_drawdown', 0):.2f}%")
        
        print(f"\n📈 风险指标")
        print(f"   夏普比率：{metrics.get('sharpe_ratio', 0):.2f}")
        print(f"   胜率：{metrics.get('win_rate', 0):.1f}%")
        
        print(f"\n📋 交易统计")
        print(f"   总交易数：{metrics.get('total_trades', 0)}")
        print(f"   盈利交易：{metrics.get('profitable_trades', 0)}")
        
        print(f"\n💼 当前持仓")
        if self.positions:
            for code, pos in self.positions.items():
                print(f"   {pos['name']}({code}): {pos['shares']}股，成本¥{pos['avg_price']:.2f}")
        else:
            print("   无持仓")
        
        print(f"\n{'='*80}")
        print(f"  报告已保存：{self.output_dir}")
        print(f"{'='*80}\n")


class SimpleBacktestStrategy:
    """简单回测策略示例"""
    
    def __init__(self, engine: BacktestEngine):
        self.engine = engine
    
    def run(self, stock_data: list, signal_threshold: float = 70.0):
        """
        运行回测
        
        参数:
            stock_data: 股票数据列表，包含每日的评分、价格等
            signal_threshold: 买入信号阈值 (综合评分)
        """
        for day_data in stock_data:
            date = day_data.get('date', '')
            price = day_data.get('price', 0)
            score = day_data.get('total_score', 0)
            code = day_data.get('code', '')
            name = day_data.get('name', '')
            
            # 买入信号：评分超过阈值
            if score >= signal_threshold and code not in self.engine.positions:
                shares = int(self.engine.capital * 0.3 / price)  # 30% 仓位
                if shares > 0:
                    self.engine.buy(code, name, price, shares, date, f"评分{score}")
            
            # 卖出信号：持有 10 天后卖出
            for code in list(self.engine.positions.keys()):
                pos = self.engine.positions[code]
                buy_date = datetime.strptime(pos['buy_date'], '%Y-%m-%d')
                current_date = datetime.strptime(date, '%Y-%m-%d')
                
                if (current_date - buy_date).days >= 10:
                    self.engine.sell(code, price, pos['shares'], date, "持有 10 天")
            
            # 更新净值
            self.engine.update_daily_value(date, {code: price})
        
        # 清仓
        for code, pos in self.engine.positions.items():
            self.engine.sell(code, price, pos['shares'], date, "回测结束清仓")


if __name__ == "__main__":
    # 测试回测
    engine = BacktestEngine(initial_capital=1000000)
    strategy = SimpleBacktestStrategy(engine)
    
    # 生成测试数据
    import random
    test_data = []
    base_price = 32.0
    base_date = datetime(2026, 1, 1)
    
    for i in range(60):
        date = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
        price = base_price * (1 + random.uniform(-0.05, 0.05))
        score = random.randint(60, 85)
        
        test_data.append({
            'date': date,
            'code': '601899',
            'name': '紫金矿业',
            'price': price,
            'total_score': score,
        })
    
    print("\n🚀 开始回测...\n")
    strategy.run(test_data, signal_threshold=75)
    engine.print_report()
    
    # 保存报告
    output_file = engine.generate_report()
    print(f"📁 详细报告：{output_file}\n")
