#!/usr/bin/env python3
"""
智能止盈止损计算器 - v1.0

功能:
- 基于 ATR 波动率计算
- 基于支撑/阻力位计算
- 基于评分计算（降级方案）
- 盈亏比优化

用法:
    from decision.stop_loss_calculator import SmartStopLossCalculator
    
    calc = SmartStopLossCalculator()
    result = calc.calculate(stock_data, atr=50, support=1700, resistance=1900)
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from datetime import datetime


@dataclass
class StopLossResult:
    """止盈止损计算结果"""
    stop_profit: float                # 止盈价
    stop_loss: float                  # 止损价
    method: str                       # 计算方法：atr/support_resistance/score
    risk_reward_ratio: float          # 盈亏比
    confidence: str                   # 置信度：high/medium/low


class SmartStopLossCalculator:
    """智能止盈止损计算器"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        'atr_multiplier_stop_loss': 2.0,    # ATR 止损倍数
        'atr_multiplier_stop_profit': 4.0,  # ATR 止盈倍数（盈亏比 2:1）
        'support_buffer': 0.02,             # 支撑位缓冲 2%
        'resistance_buffer': 0.02,          # 阻力位缓冲 2%
        
        # 评分法配置
        'score_high_stop_profit': 1.50,     # 高评分止盈 +50%
        'score_high_stop_loss': 0.78,       # 高评分止损 -22%
        'score_medium_stop_profit': 1.40,   # 中评分止盈 +40%
        'score_medium_stop_loss': 0.85,     # 中评分止损 -15%
        'score_low_stop_profit': 1.33,      # 低评分止盈 +33%
        'score_low_stop_loss': 0.87,        # 低评分止损 -13%
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化计算器
        
        Args:
            config: 配置字典（可选）
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
    
    def calculate(self, stock: Dict, 
                  atr: Optional[float] = None,
                  support_level: Optional[float] = None,
                  resistance_level: Optional[float] = None,
                  score: int = 75,
                  holding_period: str = 'short',
                  volatility_adjustment: bool = True) -> StopLossResult:
        """
        计算智能止盈止损
        
        Args:
            stock: 股票数据（包含 price 等）
            atr: 平均真实波幅（可选）
            support_level: 支撑位（可选）
            resistance_level: 阻力位（可选）
            score: 综合评分（0-100，用于降级方案）
            holding_period: 持仓周期（short/medium/long）
            volatility_adjustment: 是否波动率调整
        
        Returns:
            StopLossResult: 计算结果
        """
        price = stock.get('price', 0)
        if price <= 0:
            raise ValueError("股票价格必须大于 0")
        
        # 方法 1: 基于 ATR（优先）
        if atr and atr > 0:
            stop_loss, stop_profit, method = self._calculate_by_atr(price, atr, volatility_adjustment)
        
        # 方法 2: 基于支撑/阻力位
        elif support_level and resistance_level:
            stop_loss, stop_profit, method = self._calculate_by_support_resistance(
                price, support_level, resistance_level
            )
        
        # 方法 3: 基于评分（降级方案）
        else:
            stop_loss, stop_profit, method = self._calculate_by_score(price, score)
        
        # 根据持仓周期调整
        stop_loss, stop_profit = self._adjust_by_holding_period(
            stop_loss, stop_profit, price, holding_period
        )
        
        # 计算盈亏比
        risk_reward_ratio = self._calculate_risk_reward_ratio(price, stop_profit, stop_loss)
        
        # 确定置信度
        confidence = self._determine_confidence(method, atr, support_level)
        
        return StopLossResult(
            stop_profit=round(stop_profit, 2),
            stop_loss=round(stop_loss, 2),
            method=method,
            risk_reward_ratio=round(risk_reward_ratio, 2),
            confidence=confidence
        )
    
    def _calculate_by_atr(self, price: float, atr: float, 
                          volatility_adjustment: bool) -> Tuple[float, float, str]:
        """
        基于 ATR 计算止盈止损
        
        Args:
            price: 当前价格
            atr: 平均真实波幅
            volatility_adjustment: 是否波动率调整
        
        Returns:
            (stop_loss, stop_profit, method)
        """
        # ATR 倍数
        atr_mult_sl = self.config['atr_multiplier_stop_loss']
        atr_mult_sp = self.config['atr_multiplier_stop_profit']
        
        # 波动率调整（高波动率时放宽止损）
        if volatility_adjustment:
            atr_ratio = atr / price  # ATR 占比
            if atr_ratio > 0.05:  # ATR>5%，高波动
                atr_mult_sl *= 1.2  # 放宽 20%
                atr_mult_sp *= 1.2
        
        stop_loss = price - (atr * atr_mult_sl)
        stop_profit = price + (atr * atr_mult_sp)
        
        # 确保止损不超过 -50%
        stop_loss = max(stop_loss, price * 0.5)
        
        return stop_loss, stop_profit, 'atr_based'
    
    def _calculate_by_support_resistance(self, price: float, 
                                         support_level: float, 
                                         resistance_level: float) -> Tuple[float, float, str]:
        """
        基于支撑/阻力位计算
        
        Args:
            price: 当前价格
            support_level: 支撑位
            resistance_level: 阻力位
        
        Returns:
            (stop_loss, stop_profit, method)
        """
        # 支撑位下方 2% 为止损
        stop_loss = support_level * (1 - self.config['support_buffer'])
        
        # 阻力位上方 2% 为止盈
        stop_profit = resistance_level * (1 + self.config['resistance_buffer'])
        
        # 确保合理的止损范围
        if stop_loss > price:
            stop_loss = price * 0.95  # 最多 -5%
        
        if stop_profit < price:
            stop_profit = price * 1.05  # 最少 +5%
        
        return stop_loss, stop_profit, 'support_resistance'
    
    def _calculate_by_score(self, price: float, score: int) -> Tuple[float, float, str]:
        """
        基于评分计算（降级方案）
        
        Args:
            price: 当前价格
            score: 综合评分（0-100）
        
        Returns:
            (stop_loss, stop_profit, method)
        """
        if score >= 90:
            stop_profit = price * self.config['score_high_stop_profit']
            stop_loss = price * self.config['score_high_stop_loss']
        elif score >= 80:
            stop_profit = price * self.config['score_medium_stop_profit']
            stop_loss = price * self.config['score_medium_stop_loss']
        else:
            stop_profit = price * self.config['score_low_stop_profit']
            stop_loss = price * self.config['score_low_stop_loss']
        
        return stop_loss, stop_profit, 'score_based'
    
    def _adjust_by_holding_period(self, stop_loss: float, stop_profit: float,
                                  price: float, holding_period: str) -> Tuple[float, float]:
        """
        根据持仓周期调整
        
        Args:
            stop_loss: 止损价
            stop_profit: 止盈价
            price: 当前价格
            holding_period: 持仓周期
        
        Returns:
            (adjusted_stop_loss, adjusted_stop_profit)
        """
        if holding_period == 'long':
            # 长线：提高止盈，放宽止损
            stop_profit = stop_profit * 1.2  # +20%
            stop_loss = stop_loss * 0.95     # -5%
        elif holding_period == 'medium':
            # 中线：适度调整
            stop_profit = stop_profit * 1.1  # +10%
            stop_loss = stop_loss * 0.975    # -2.5%
        # short: 不调整
        
        return stop_loss, stop_profit
    
    def _calculate_risk_reward_ratio(self, price: float, 
                                     stop_profit: float, 
                                     stop_loss: float) -> float:
        """
        计算盈亏比
        
        Args:
            price: 当前价格
            stop_profit: 止盈价
            stop_loss: 止损价
        
        Returns:
            盈亏比
        """
        potential_profit = stop_profit - price
        potential_loss = price - stop_loss
        
        if potential_loss <= 0:
            return 0
        
        return potential_profit / potential_loss
    
    def _determine_confidence(self, method: str, 
                              atr: Optional[float], 
                              support_level: Optional[float]) -> str:
        """
        确定置信度
        
        Args:
            method: 计算方法
            atr: ATR 值
            support_level: 支撑位
        
        Returns:
            置信度：high/medium/low
        """
        if method == 'atr_based' and atr:
            return 'high'
        elif method == 'support_resistance' and support_level:
            return 'high'
        elif method == 'score_based':
            return 'medium'
        else:
            return 'low'
    
    def get_optimal_position_size(self, capital: float, 
                                  entry_price: float, 
                                  stop_loss: float, 
                                  risk_per_trade: float = 0.02) -> int:
        """
        计算最优仓位
        
        Args:
            capital: 总资金
            entry_price: 入场价
            stop_loss: 止损价
            risk_per_trade: 单笔风险（默认 2%）
        
        Returns:
            建议仓位（股数）
        """
        risk_amount = capital * risk_per_trade
        risk_per_share = entry_price - stop_loss
        
        if risk_per_share <= 0:
            return 0
        
        shares = risk_amount / risk_per_share
        return int(shares)


# 测试
if __name__ == '__main__':
    calc = SmartStopLossCalculator()
    
    # 测试数据
    test_stock = {
        'code': '600519',
        'name': '贵州茅台',
        'price': 1800.00,
    }
    
    print("="*80)
    print("🎯 智能止盈止损计算器测试")
    print("="*80)
    
    # 测试 1: ATR 法
    print("\n[测试 1] ATR 法")
    result = calc.calculate(test_stock, atr=50)
    print(f"  入场价：¥{test_stock['price']:.2f}")
    print(f"  止盈价：¥{result.stop_profit:.2f} (+{(result.stop_profit/test_stock['price']-1)*100:.1f}%)")
    print(f"  止损价：¥{result.stop_loss:.2f} ({(result.stop_loss/test_stock['price']-1)*100:.1f}%)")
    print(f"  方法：{result.method}")
    print(f"  盈亏比：{result.risk_reward_ratio}:1")
    print(f"  置信度：{result.confidence}")
    
    # 测试 2: 支撑阻力法
    print("\n[测试 2] 支撑阻力法")
    result = calc.calculate(test_stock, support_level=1700, resistance_level=1900)
    print(f"  入场价：¥{test_stock['price']:.2f}")
    print(f"  止盈价：¥{result.stop_profit:.2f} (+{(result.stop_profit/test_stock['price']-1)*100:.1f}%)")
    print(f"  止损价：¥{result.stop_loss:.2f} ({(result.stop_loss/test_stock['price']-1)*100:.1f}%)")
    print(f"  方法：{result.method}")
    print(f"  盈亏比：{result.risk_reward_ratio}:1")
    print(f"  置信度：{result.confidence}")
    
    # 测试 3: 评分法
    print("\n[测试 3] 评分法")
    result = calc.calculate(test_stock, score=85)
    print(f"  入场价：¥{test_stock['price']:.2f}")
    print(f"  止盈价：¥{result.stop_profit:.2f} (+{(result.stop_profit/test_stock['price']-1)*100:.1f}%)")
    print(f"  止损价：¥{result.stop_loss:.2f} ({(result.stop_loss/test_stock['price']-1)*100:.1f}%)")
    print(f"  方法：{result.method}")
    print(f"  盈亏比：{result.risk_reward_ratio}:1")
    print(f"  置信度：{result.confidence}")
    
    # 测试 4: 持仓周期调整
    print("\n[测试 4] 持仓周期调整")
    for period in ['short', 'medium', 'long']:
        result = calc.calculate(test_stock, atr=50, holding_period=period)
        print(f"  {period}: 止盈¥{result.stop_profit:.2f} 止损¥{result.stop_loss:.2f} 盈亏比{result.risk_reward_ratio}:1")
    
    # 测试 5: 仓位计算
    print("\n[测试 5] 最优仓位计算")
    capital = 1000000  # 100 万
    entry = 1800
    stop_loss = 1700
    shares = calc.get_optimal_position_size(capital, entry, stop_loss)
    print(f"  总资金：¥{capital:,.0f}")
    print(f"  入场价：¥{entry}")
    print(f"  止损价：¥{stop_loss}")
    print(f"  建议仓位：{shares} 股")
    print(f"  仓位金额：¥{shares * entry:,.0f}")
    print(f"  仓位占比：{shares * entry / capital * 100:.1f}%")
