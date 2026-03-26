#!/usr/bin/env python3
"""
回测引擎 - v1.0

功能:
- 历史回测
- 策略评估
- 绩效指标计算
- 盈亏分析

用法:
    from backtest.engine import BacktestEngine
    
    engine = BacktestEngine(initial_capital=1000000)
    result = engine.run_backtest(strategy, start_date, end_date)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import json


@dataclass
class Trade:
    """交易记录"""
    code: str                       # 股票代码
    direction: str                  # 买卖方向：buy/sell
    price: float                    # 成交价格
    shares: int                     # 成交股数
    amount: float                   # 成交金额
    timestamp: str                  # 时间戳
    commission: float = 0.0003      # 手续费率（万分之三）
    slippage: float = 0.001         # 滑点（千分之一）
    
    @property
    def cost(self) -> float:
        """交易成本"""
        return self.amount * (self.commission + self.slippage)
    
    @property
    def net_amount(self) -> float:
        """净成交金额"""
        if self.direction == 'buy':
            return self.amount + self.cost
        else:
            return self.amount - self.cost


@dataclass
class Position:
    """持仓记录"""
    code: str                       # 股票代码
    shares: int                     # 持仓股数
    avg_cost: float                 # 平均成本
    current_price: float = 0.0      # 当前价格
    
    @property
    def market_value(self) -> float:
        """市值"""
        return self.shares * self.current_price
    
    @property
    def cost_basis(self) -> float:
        """成本"""
        return self.shares * self.avg_cost
    
    @property
    def profit_loss(self) -> float:
        """盈亏"""
        return self.market_value - self.cost_basis
    
    @property
    def profit_loss_pct(self) -> float:
        """盈亏比例"""
        if self.cost_basis == 0:
            return 0
        return self.profit_loss / self.cost_basis * 100


@dataclass
class BacktestResult:
    """回测结果"""
    # 基本信息
    start_date: str                 # 开始日期
    end_date: str                   # 结束日期
    initial_capital: float          # 初始资金
    final_capital: float            # 最终资金
    
    # 收益指标
    total_return: float             # 总收益率 (%)
    annualized_return: float        # 年化收益率 (%)
    
    # 风险指标
    volatility: float               # 波动率 (%)
    max_drawdown: float             # 最大回撤 (%)
    sharpe_ratio: float             # 夏普比率
    sortino_ratio: float            # 索提诺比率
    
    # 交易统计
    total_trades: int               # 总交易次数
    winning_trades: int             # 盈利交易次数
    losing_trades: int              # 亏损交易次数
    win_rate: float                 # 胜率 (%)
    avg_profit: float               # 平均盈利 (%)
    avg_loss: float                 # 平均亏损 (%)
    profit_factor: float            # 盈利因子
    
    # 其他
    trades: List[Trade] = field(default_factory=list)  # 交易记录
    daily_returns: List[float] = field(default_factory=list)  # 每日收益
    equity_curve: List[float] = field(default_factory=list)  # 资金曲线
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'total_return': self.total_return,
            'annualized_return': self.annualized_return,
            'volatility': self.volatility,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'avg_profit': self.avg_profit,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
        }
    
    def summary(self) -> str:
        """回测结果摘要"""
        lines = [
            "="*80,
            "📊 回测结果摘要",
            "="*80,
            f"回测区间：{self.start_date} 至 {self.end_date}",
            f"初始资金：¥{self.initial_capital:,.0f}",
            f"最终资金：¥{self.final_capital:,.0f}",
            "",
            "📈 收益指标:",
            f"  总收益率：{self.total_return:+.2f}%",
            f"  年化收益率：{self.annualized_return:+.2f}%",
            "",
            "⚠️ 风险指标:",
            f"  波动率：{self.volatility:.2f}%",
            f"  最大回撤：{self.max_drawdown:.2f}%",
            f"  夏普比率：{self.sharpe_ratio:.2f}",
            f"  索提诺比率：{self.sortino_ratio:.2f}",
            "",
            "💰 交易统计:",
            f"  总交易次数：{self.total_trades}",
            f"  胜率：{self.win_rate:.2f}%",
            f"  平均盈利：{self.avg_profit:+.2f}%",
            f"  平均亏损：{self.avg_loss:+.2f}%",
            f"  盈利因子：{self.profit_factor:.2f}",
            "="*80,
        ]
        return "\n".join(lines)


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 1000000,
                 commission_rate: float = 0.0003,
                 slippage_rate: float = 0.001):
        """
        初始化回测引擎
        
        Args:
            initial_capital: 初始资金
            commission_rate: 手续费率
            slippage_rate: 滑点率
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        
        self.capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = [initial_capital]
        self.daily_returns: List[float] = []
    
    def run_backtest(self, strategy: Callable, 
                     data: List[Dict],
                     start_date: str,
                     end_date: str) -> BacktestResult:
        """
        运行回测
        
        Args:
            strategy: 策略函数，输入数据，输出交易信号
            data: 历史数据列表
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            BacktestResult: 回测结果
        """
        # 重置状态
        self.capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = [self.initial_capital]
        self.daily_returns = []
        
        # 过滤数据
        filtered_data = [
            d for d in data
            if start_date <= d.get('date', '') <= end_date
        ]
        
        if not filtered_data:
            raise ValueError("回测区间内无数据")
        
        # 运行回测
        prev_equity = self.initial_capital
        
        for day_data in filtered_data:
            date = day_data.get('date', '')
            
            # 执行策略
            signals = strategy(day_data)
            
            # 执行交易
            self._execute_signals(signals, day_data)
            
            # 更新持仓价格
            self._update_positions(day_data)
            
            # 计算当日权益
            equity = self.capital + sum(
                p.market_value for p in self.positions.values()
            )
            
            # 记录资金曲线
            self.equity_curve.append(equity)
            
            # 计算日收益
            daily_return = (equity - prev_equity) / prev_equity * 100
            self.daily_returns.append(daily_return)
            prev_equity = equity
        
        # 计算回测结果
        return self._calculate_result(start_date, end_date)
    
    def _execute_signals(self, signals: List[Dict], day_data: Dict):
        """
        执行交易信号
        
        Args:
            signals: 交易信号列表
            day_data: 当日数据
        """
        for signal in signals:
            code = signal.get('code', '')
            action = signal.get('action', '')  # buy/sell
            shares = signal.get('shares', 0)
            price = signal.get('price', day_data.get('close', 0))
            
            if action == 'buy' and shares > 0:
                self._buy(code, shares, price)
            elif action == 'sell' and shares > 0:
                self._sell(code, shares, price)
    
    def _buy(self, code: str, shares: int, price: float):
        """买入"""
        amount = shares * price
        cost = amount * (self.commission_rate + self.slippage_rate)
        total_cost = amount + cost
        
        # 检查资金是否足够
        if total_cost > self.capital:
            # 调整购买数量
            shares = int(self.capital / (price * (1 + self.commission_rate + self.slippage_rate)))
            if shares <= 0:
                return
            amount = shares * price
            cost = amount * (self.commission_rate + self.slippage_rate)
            total_cost = amount + cost
        
        # 更新资金
        self.capital -= total_cost
        
        # 更新持仓
        if code in self.positions:
            pos = self.positions[code]
            total_shares = pos.shares + shares
            total_cost = pos.cost_basis + amount + cost
            pos.avg_cost = total_cost / total_shares
            pos.shares = total_shares
        else:
            self.positions[code] = Position(
                code=code,
                shares=shares,
                avg_cost=(amount + cost) / shares
            )
        
        # 记录交易
        self.trades.append(Trade(
            code=code,
            direction='buy',
            price=price,
            shares=shares,
            amount=amount,
            timestamp=datetime.now().isoformat()
        ))
    
    def _sell(self, code: str, shares: int, price: float):
        """卖出"""
        if code not in self.positions:
            return
        
        pos = self.positions[code]
        shares = min(shares, pos.shares)  # 不能卖出超过持仓
        
        if shares <= 0:
            return
        
        amount = shares * price
        cost = amount * (self.commission_rate + self.slippage_rate)
        net_amount = amount - cost
        
        # 更新资金
        self.capital += net_amount
        
        # 更新持仓
        pos.shares -= shares
        if pos.shares == 0:
            del self.positions[code]
        
        # 记录交易
        self.trades.append(Trade(
            code=code,
            direction='sell',
            price=price,
            shares=shares,
            amount=amount,
            timestamp=datetime.now().isoformat()
        ))
    
    def _update_positions(self, day_data: Dict):
        """更新持仓价格"""
        for code, pos in self.positions.items():
            # 从当日数据中获取最新价格
            if code in day_data:
                pos.current_price = day_data[code].get('close', pos.current_price)
    
    def _calculate_result(self, start_date: str, end_date: str) -> BacktestResult:
        """计算回测结果"""
        final_capital = self.equity_curve[-1] if self.equity_curve else self.initial_capital
        
        # 总收益率
        total_return = (final_capital - self.initial_capital) / self.initial_capital * 100
        
        # 年化收益率
        days = (datetime.strptime(end_date, '%Y-%m-%d') - 
                datetime.strptime(start_date, '%Y-%m-%d')).days
        years = days / 365.25
        if years > 0:
            annualized_return = ((final_capital / self.initial_capital) ** (1 / years) - 1) * 100
        else:
            annualized_return = 0
        
        # 波动率
        if self.daily_returns:
            import statistics
            volatility = statistics.stdev(self.daily_returns) * (252 ** 0.5)  # 年化
        else:
            volatility = 0
        
        # 最大回撤
        max_drawdown = self._calculate_max_drawdown()
        
        # 夏普比率
        if volatility > 0:
            sharpe_ratio = (annualized_return - 3.0) / volatility  # 假设无风险利率 3%
        else:
            sharpe_ratio = 0
        
        # 索提诺比率
        downside_returns = [r for r in self.daily_returns if r < 0]
        if downside_returns:
            import statistics
            downside_deviation = statistics.stdev(downside_returns) * (252 ** 0.5)
            sortino_ratio = (annualized_return - 3.0) / downside_deviation if downside_deviation > 0 else 0
        else:
            sortino_ratio = 0
        
        # 交易统计
        total_trades = len(self.trades)
        
        # 计算盈亏
        trade_profits = []
        for i in range(0, len(self.trades), 2):
            if i + 1 < len(self.trades):
                buy_trade = self.trades[i]
                sell_trade = self.trades[i + 1]
                if buy_trade.code == sell_trade.code:
                    profit = (sell_trade.price - buy_trade.price) / buy_trade.price * 100
                    trade_profits.append(profit)
        
        winning_trades = sum(1 for p in trade_profits if p > 0)
        losing_trades = sum(1 for p in trade_profits if p < 0)
        win_rate = winning_trades / len(trade_profits) * 100 if trade_profits else 0
        
        avg_profit = sum(p for p in trade_profits if p > 0) / winning_trades if winning_trades > 0 else 0
        avg_loss = sum(p for p in trade_profits if p < 0) / losing_trades if losing_trades > 0 else 0
        
        total_profit = sum(p for p in trade_profits if p > 0)
        total_loss = abs(sum(p for p in trade_profits if p < 0))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            trades=self.trades,
            daily_returns=self.daily_returns,
            equity_curve=self.equity_curve
        )
    
    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if not self.equity_curve:
            return 0
        
        peak = self.equity_curve[0]
        max_dd = 0
        
        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def get_positions(self) -> Dict[str, Position]:
        """获取当前持仓"""
        return self.positions
    
    def get_trades(self) -> List[Trade]:
        """获取交易记录"""
        return self.trades


# 测试
if __name__ == '__main__':
    print("="*80)
    print("🔧 回测引擎测试")
    print("="*80)
    
    # 创建回测引擎
    engine = BacktestEngine(initial_capital=1000000)
    
    # 简单策略：买入持有
    def simple_strategy(day_data):
        signals = []
        date = day_data.get('date', '')
        
        # 第一天买入
        if date == '2026-01-01':
            for code, data in day_data.items():
                if code != 'date':
                    signals.append({
                        'code': code,
                        'action': 'buy',
                        'shares': 100,
                        'price': data.get('close', 0)
                    })
        
        return signals
    
    # 模拟数据
    import random
    data = []
    codes = ['600519', '000858', '600036']
    
    for i in range(60):
        date = (datetime(2026, 1, 1) + timedelta(days=i)).strftime('%Y-%m-%d')
        day_data = {'date': date}
        
        for code in codes:
            base_price = {'600519': 1800, '000858': 150, '600036': 35}[code]
            price = base_price * (1 + random.uniform(-0.02, 0.02) * (i / 30))
            day_data[code] = {'close': price}
        
        data.append(day_data)
    
    # 运行回测
    result = engine.run_backtest(
        strategy=simple_strategy,
        data=data,
        start_date='2026-01-01',
        end_date='2026-03-01'
    )
    
    # 输出结果
    print(result.summary())
    
    print(f"\n交易记录：{len(result.trades)} 笔")
    print(f"资金曲线：{len(result.equity_curve)} 个点")
    print(f"日收益序列：{len(result.daily_returns)} 个点")
