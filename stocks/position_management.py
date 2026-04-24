#!/usr/bin/env python3
"""
资金管理策略模块

基于《专业投机原理》- 维克多·斯波朗迪

核心原理:
1. 风险/回报比至少 1:3
2. 单笔交易风险不超过总资金 2%
3. 根据市场状况调整仓位
4. 止损是交易的保险
5. 盈利后增加仓位，亏损后减少仓位

用法:
    from position_management import PositionManager
    manager = PositionManager()
    position = manager.calculate_position(capital, stock_data)
"""

from typing import List, Dict, Optional
import math


class PositionManager:
    """资金管理器"""
    
    # 风险参数
    MAX_RISK_PER_TRADE = 0.02  # 单笔最大风险 2%
    MAX_POSITION_SIZE = 0.20   # 单只股票最大仓位 20%
    MIN_RISK_REWARD = 3.0      # 最小风险回报比 1:3
    
    def __init__(self, total_capital: float = 100000):
        self.total_capital = total_capital
        self.current_positions = 0
        self.total_risk = 0
    
    def calculate_position(self, stock_data: Dict, 
                          entry_price: float,
                          stop_loss: float,
                          target_price: float) -> Dict:
        """
        计算建议仓位
        
        Args:
            stock_data: 股票数据 (包含波动率等)
            entry_price: 入场价
            stop_loss: 止损价
            target_price: 目标价
        
        Returns:
            {
                'shares': int,  # 股数
                'position_size': float,  # 仓位金额
                'position_pct': float,  # 仓位占比
                'risk_amount': float,  # 风险金额
                'risk_pct': float,  # 风险占比
                'reward_ratio': float,  # 风险回报比
                'recommendation': str,  # 建议
            }
        """
        # 1. 计算每股风险
        risk_per_share = entry_price - stop_loss
        
        if risk_per_share <= 0:
            return {
                'error': '止损价高于入场价',
                'recommendation': '调整止损位',
            }
        
        # 2. 计算风险回报比
        reward_per_share = target_price - entry_price
        risk_reward_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0
        
        # 确保风险回报比合理
        if risk_reward_ratio < 0:
            risk_reward_ratio = 0
        
        if risk_reward_ratio < self.MIN_RISK_REWARD:
            return {
                'error': f'风险回报比{risk_reward_ratio:.2f}低于{self.MIN_RISK_REWARD}',
                'recommendation': '寻找更好的入场点',
            }
        
        # 3. 计算最大可承受风险金额
        max_risk_amount = self.total_capital * self.MAX_RISK_PER_TRADE
        
        # 4. 计算可买股数
        shares = int(max_risk_amount / risk_per_share)
        
        # 5. 计算仓位金额
        position_size = shares * entry_price
        
        # 6. 检查是否超过最大仓位
        max_position = self.total_capital * self.MAX_POSITION_SIZE
        if position_size > max_position:
            shares = int(max_position / entry_price)
            position_size = shares * entry_price
            risk_amount = shares * risk_per_share
        else:
            risk_amount = shares * risk_per_share
        
        # 7. 计算仓位占比
        position_pct = position_size / self.total_capital
        
        # 8. 计算实际风险占比
        risk_pct = risk_amount / self.total_capital
        
        # 9. 综合建议
        recommendation = self._get_recommendation(
            risk_reward_ratio, risk_pct, position_pct, stock_data
        )
        
        return {
            'shares': shares,
            'position_size': round(position_size, 2),
            'position_pct': round(position_pct * 100, 2),
            'risk_amount': round(risk_amount, 2),
            'risk_pct': round(risk_pct * 100, 2),
            'reward_ratio': round(risk_reward_ratio, 2),
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target_price': target_price,
            'recommendation': recommendation,
        }
    
    def _get_recommendation(self, risk_reward: float, risk_pct: float, 
                           position_pct: float, stock_data: Dict) -> str:
        """获取综合建议"""
        # 检查波动率
        volatility = stock_data.get('volatility', 0.03)  # 默认 3%
        
        # 风险回报比评分
        if risk_reward >= 5:
            rr_score = '优秀'
        elif risk_reward >= 3:
            rr_score = '良好'
        elif risk_reward >= 2:
            rr_score = '一般'
        else:
            rr_score = '较差'
        
        # 仓位评分
        if position_pct <= 10:
            pos_score = '保守'
        elif position_pct <= 20:
            pos_score = '适中'
        else:
            pos_score = '激进'
        
        # 波动率评分
        if volatility < 0.02:
            vol_score = '低波动'
        elif volatility < 0.05:
            vol_score = '中等波动'
        else:
            vol_score = '高波动'
        
        # 综合建议
        if risk_reward >= 3 and position_pct <= 20 and volatility < 0.05:
            return f'✅ 建议买入 (风险回报{rr_score}, 仓位{pos_score}, {vol_score})'
        elif risk_reward >= 2:
            return f'⚠️ 谨慎买入 (风险回报{rr_score}, 建议降低仓位)'
        else:
            return f'❌ 不建议买入 (风险回报{rr_score})'
    
    def calculate_pyramiding(self, current_position: Dict, 
                            current_price: float,
                            new_entry: bool = True) -> Dict:
        """
        计算加仓/减仓策略
        
        原理:
        - 盈利后加仓 (金字塔式)
        - 亏损后减仓
        
        Args:
            current_position: 当前持仓信息
            current_price: 当前价格
            new_entry: 是否新入场
        
        Returns:
            {
                'action': str,  # add/reduce/hold
                'shares': int,  # 调整股数
                'reason': str,  # 理由
            }
        """
        entry_price = current_position.get('entry_price', 0)
        current_shares = current_position.get('shares', 0)
        stop_loss = current_position.get('stop_loss', 0)
        
        if entry_price == 0 or current_shares == 0:
            return {'action': 'hold', 'shares': 0, 'reason': '无持仓'}
        
        # 计算盈亏比例
        profit_pct = (current_price - entry_price) / entry_price
        
        # 江恩/斯波朗迪加仓规则
        if profit_pct >= 0.10 and new_entry:
            # 盈利 10% 以上，可加仓 50%
            add_shares = int(current_shares * 0.5)
            new_stop = entry_price * 1.05  # 上移止损到成本价上方 5%
            
            return {
                'action': 'add',
                'shares': add_shares,
                'new_stop_loss': round(new_stop, 2),
                'reason': f'盈利{profit_pct*100:.1f}%, 金字塔加仓',
            }
        elif profit_pct >= 0.20 and new_entry:
            # 盈利 20% 以上，可加仓 30%
            add_shares = int(current_shares * 0.3)
            new_stop = entry_price * 1.10  # 上移止损到成本价上方 10%
            
            return {
                'action': 'add',
                'shares': add_shares,
                'new_stop_loss': round(new_stop, 2),
                'reason': f'盈利{profit_pct*100:.1f}%, 继续加仓',
            }
        elif profit_pct <= -0.05:
            # 亏损 5% 以上，减仓 50%
            reduce_shares = int(current_shares * 0.5)
            
            return {
                'action': 'reduce',
                'shares': reduce_shares,
                'reason': f'亏损{profit_pct*100:.1f}%, 减仓止损',
            }
        elif profit_pct <= -0.10:
            # 亏损 10% 以上，清仓
            return {
                'action': 'exit',
                'shares': current_shares,
                'reason': f'亏损{profit_pct*100:.1f}%, 止损离场',
            }
        else:
            return {
                'action': 'hold',
                'shares': 0,
                'reason': f'盈利{profit_pct*100:.1f}%, 保持持仓',
            }
    
    def calculate_trailing_stop(self, entry_price: float, 
                               current_price: float,
                               high_since_entry: float,
                               method: str = 'percent') -> float:
        """
        计算移动止损
        
        方法:
        - percent: 固定百分比回撤
        - atr: ATR 倍数
        - gann: 江恩百分比
        
        Args:
            entry_price: 入场价
            current_price: 当前价
            high_since_entry: 入场以来最高价
            method: 计算方法
        
        Returns:
            float: 移动止损价
        """
        if method == 'percent':
            # 固定百分比回撤 (5-10%)
            if current_price > entry_price * 1.20:
                # 盈利 20% 以上，回撤 10% 止损
                stop = high_since_entry * 0.90
            elif current_price > entry_price * 1.10:
                # 盈利 10% 以上，回撤 7% 止损
                stop = high_since_entry * 0.93
            else:
                # 盈利不足 10%, 回撤 5% 止损
                stop = high_since_entry * 0.95
            
            # 确保止损不低于成本价
            stop = max(stop, entry_price * 1.02)
            
            return round(stop, 2)
        
        elif method == 'gann':
            # 江恩百分比回撤
            gann_levels = [0.125, 0.25, 0.375, 0.5]
            
            profit = high_since_entry - entry_price
            
            # 根据盈利幅度选择江恩回撤位
            if profit > entry_price * 0.30:
                stop = high_since_entry - profit * 0.375  # 3/8 回撤
            elif profit > entry_price * 0.20:
                stop = high_since_entry - profit * 0.25   # 1/4 回撤
            elif profit > entry_price * 0.10:
                stop = high_since_entry - profit * 0.125  # 1/8 回撤
            else:
                stop = entry_price * 1.02  # 保本止损
            
            return round(stop, 2)
        
        else:
            # 默认：成本价上方 2%
            return round(entry_price * 1.02, 2)
    
    def portfolio_risk_check(self, positions: List[Dict]) -> Dict:
        """
        检查整体组合风险
        
        Args:
            positions: 所有持仓列表
        
        Returns:
            {
                'total_risk': float,  # 总风险金额
                'total_risk_pct': float,  # 总风险占比
                'position_count': int,  # 持仓数量
                'recommendation': str,  # 建议
                'risk_level': str,  # 风险等级
            }
        """
        total_risk = 0
        total_value = 0
        
        for pos in positions:
            entry = pos.get('entry_price', 0)
            current = pos.get('current_price', 0)
            shares = pos.get('shares', 0)
            stop = pos.get('stop_loss', entry * 0.90)
            
            # 计算当前风险
            risk_per_share = current - stop
            position_risk = risk_per_share * shares
            total_risk += position_risk
            
            total_value += current * shares
        
        total_risk_pct = total_risk / self.total_capital if self.total_capital > 0 else 0
        
        # 风险等级判断
        if total_risk_pct < 0.05:
            risk_level = '低风险'
            recommendation = '✅ 风险可控，可适当增加仓位'
        elif total_risk_pct < 0.10:
            risk_level = '中等风险'
            recommendation = '⚠️ 风险适中，保持当前仓位'
        elif total_risk_pct < 0.15:
            risk_level = '高风险'
            recommendation = '⚠️ 风险较高，建议减仓'
        else:
            risk_level = '极高风险'
            recommendation = '❌ 风险过高，立即减仓'
        
        return {
            'total_risk': round(total_risk, 2),
            'total_risk_pct': round(total_risk_pct * 100, 2),
            'position_count': len(positions),
            'total_value': round(total_value, 2),
            'recommendation': recommendation,
            'risk_level': risk_level,
        }


# 集成到评分系统
def position_management_score(position_data: Dict) -> float:
    """
    资金管理评分 (0-10 分)
    
    基于风险回报比、仓位合理性评分
    """
    reward_ratio = position_data.get('reward_ratio', 0)
    risk_pct = position_data.get('risk_pct', 0)
    position_pct = position_data.get('position_pct', 0)
    
    score = 5.0
    
    # 风险回报比评分
    if reward_ratio >= 5:
        score += 3
    elif reward_ratio >= 3:
        score += 2
    elif reward_ratio >= 2:
        score += 1
    else:
        score -= 2
    
    # 仓位合理性评分
    if risk_pct <= 2 and position_pct <= 20:
        score += 2
    elif risk_pct <= 3 and position_pct <= 25:
        score += 1
    elif risk_pct > 5 or position_pct > 30:
        score -= 2
    
    return min(max(score, 0), 10)


if __name__ == '__main__':
    print('资金管理模块 - 测试')
    print('='*60)
    
    manager = PositionManager(total_capital=100000)
    
    # 测试仓位计算
    result = manager.calculate_position(
        stock_data={'volatility': 0.03},
        entry_price=50.0,
        stop_loss=47.5,
        target_price=60.0
    )
    
    print(f'仓位计算结果：{result}')
