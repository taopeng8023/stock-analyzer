#!/usr/bin/env python3
"""
海龟交易法则模块
基于《海龟交易法则》- 柯蒂斯·费思

核心系统:
1. 市场选择
2. 头寸规模 (N 值/ATR)
3. 入场信号 (突破)
4. 止损策略
5. 加仓策略
6. 退出策略

用法:
    python3 turtle_trading.py --stock sh600000
    python3 turtle_trading.py --analyze all
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

sys.path.insert(0, str(Path(__file__).parent))


class TurtleTradingStrategy:
    """
    海龟交易策略
    
    基于柯蒂斯·费思《海龟交易法则》
    """
    
    def __init__(self):
        pass
    
    def calculate_position_size(self, stock_data: dict, capital: float = 1000000) -> dict:
        """
        头寸规模计算
        
        基于 N 值 (ATR) 计算仓位:
        - 1 单位 = 1% 账户风险 / N 值
        - 最大持仓：4 单位
        
        Args:
            stock_data: 股票数据
            capital: 账户资金 (默认 100 万)
        
        Returns:
            dict: 头寸规模结果
        """
        price = stock_data.get('price', 0)
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版 N 值计算 (基于波动率模拟)
        if abs(change_pct) > 7:
            n_value = price * 0.05  # 高波动
        elif abs(change_pct) > 3:
            n_value = price * 0.03  # 中等波动
        else:
            n_value = price * 0.02  # 低波动
        
        # 计算单位仓位
        risk_per_unit = capital * 0.01  # 1% 风险
        units = risk_per_unit / n_value if n_value > 0 else 0
        
        # 限制最大 4 单位
        units = min(units, 4)
        
        # 计算股数
        shares = int(units * (capital / price)) if price > 0 else 0
        
        return {
            'n_value': round(n_value, 2),
            'units': round(units, 1),
            'shares': shares,
            'position_value': round(shares * price, 0),
            'risk_percent': round(units * 1, 1),  # 每单位 1% 风险
            'description': f'头寸规模：{units:.1f}单位 ({shares}股)',
        }
    
    def analyze_entry_signal(self, stock_data: dict) -> dict:
        """
        入场信号分析
        
        海龟入场规则:
        - 系统 1: 突破 20 日高点
        - 系统 2: 突破 55 日高点
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 入场信号结果
        """
        change_pct = stock_data.get('change_pct', 0)
        price = stock_data.get('price', 0)
        
        # 简化版突破判断
        if change_pct > 7:
            entry_signal = '系统 1 突破 (20 日)'
            signal_strength = '强'
            action = '买入 1 单位'
            score = 85
        elif change_pct > 3:
            entry_signal = '潜在突破'
            signal_strength = '中'
            action = '准备买入'
            score = 65
        elif change_pct > 0:
            entry_signal = '无突破'
            signal_strength = '弱'
            action = '观望'
            score = 40
        elif change_pct < -3:
            entry_signal = '向下突破'
            signal_strength = '中'
            action = '卖出/做空'
            score = 25
        else:
            entry_signal = '无信号'
            signal_strength = '无'
            action = '空仓'
            score = 30
        
        return {
            'entry_signal': entry_signal,
            'signal_strength': signal_strength,
            'action': action,
            'score': score,
            'description': f'入场信号：{entry_signal} - {action}',
        }
    
    def analyze_stop_loss(self, stock_data: dict) -> dict:
        """
        止损策略分析
        
        海龟止损规则:
        - 止损价 = 入场价 - 2N
        - 每单位风险 1%
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 止损策略结果
        """
        price = stock_data.get('price', 0)
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版 N 值
        if abs(change_pct) > 7:
            n_value = price * 0.05
        elif abs(change_pct) > 3:
            n_value = price * 0.03
        else:
            n_value = price * 0.02
        
        # 计算止损价
        stop_loss_price = price - 2 * n_value
        stop_loss_percent = (price - stop_loss_price) / price * 100
        
        # 判断止损状态
        if change_pct < -5:
            stop_status = '接近止损'
            urgency = '高'
            score = 30
        elif change_pct < 0:
            stop_status = '安全'
            urgency = '低'
            score = 70
        else:
            stop_status = '盈利中'
            urgency = '无'
            score = 85
        
        return {
            'stop_loss_price': round(stop_loss_price, 2),
            'stop_loss_percent': round(stop_loss_percent, 2),
            'n_value': round(n_value, 2),
            'stop_status': stop_status,
            'urgency': urgency,
            'score': score,
            'description': f'止损价：¥{stop_loss_price:.2f} (-{stop_loss_percent:.1f}%)',
        }
    
    def analyze_add_position(self, stock_data: dict) -> dict:
        """
        加仓策略分析
        
        海龟加仓规则:
        - 每上涨 1N 加仓 1 单位
        - 最多加仓至 4 单位
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 加仓策略结果
        """
        change_pct = stock_data.get('change_pct', 0)
        price = stock_data.get('price', 0)
        
        # 简化版 N 值
        if abs(change_pct) > 7:
            n_value = price * 0.05
        elif abs(change_pct) > 3:
            n_value = price * 0.03
        else:
            n_value = price * 0.02
        
        # 判断加仓时机
        if change_pct > 10:
            add_signal = '加仓 1 单位'
            current_units = 2
            max_units = 4
            score = 80
        elif change_pct > 5:
            add_signal = '准备加仓'
            current_units = 1
            max_units = 4
            score = 60
        elif change_pct > 0:
            add_signal = '持有'
            current_units = 1
            max_units = 4
            score = 50
        else:
            add_signal = '不加仓'
            current_units = 0
            max_units = 4
            score = 30
        
        return {
            'add_signal': add_signal,
            'current_units': current_units,
            'max_units': max_units,
            'n_value': round(n_value, 2),
            'score': score,
            'description': f'加仓信号：{add_signal} (当前{current_units}单位，最大{max_units}单位)',
        }
    
    def analyze_exit_signal(self, stock_data: dict) -> dict:
        """
        退出信号分析
        
        海龟退出规则:
        - 系统 1: 跌破 10 日低点
        - 系统 2: 跌破 20 日低点
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 退出信号结果
        """
        change_pct = stock_data.get('change_pct', 0)
        
        # 判断退出信号
        if change_pct < -7:
            exit_signal = '系统 1 退出 (10 日低点)'
            action = '全部卖出'
            urgency = '紧急'
            score = 20
        elif change_pct < -3:
            exit_signal = '潜在退出信号'
            action = '准备卖出'
            urgency = '中等'
            score = 35
        elif change_pct < 0:
            exit_signal = '无退出信号'
            action = '持有'
            urgency = '低'
            score = 60
        else:
            exit_signal = '无退出信号'
            action = '继续持有'
            urgency = '无'
            score = 80
        
        return {
            'exit_signal': exit_signal,
            'action': action,
            'urgency': urgency,
            'score': score,
            'description': f'退出信号：{exit_signal} - {action}',
        }
    
    def analyze_risk_management(self, stock_data: dict, capital: float = 1000000) -> dict:
        """
        风险管理分析
        
        海龟风控规则:
        - 单笔风险<2%
        - 总风险<6%
        - 相关性控制
        
        Args:
            stock_data: 股票数据
            capital: 账户资金
        
        Returns:
            dict: 风险管理结果
        """
        position_size = self.calculate_position_size(stock_data, capital)
        
        units = position_size.get('units', 0)
        risk_percent = position_size.get('risk_percent', 0)
        
        # 风险评估
        if risk_percent > 6:
            risk_level = '高风险'
            action = '减仓'
            score = 25
        elif risk_percent > 4:
            risk_level = '中高风险'
            action = '控制仓位'
            score = 50
        elif risk_percent > 2:
            risk_level = '中等风险'
            action = '可接受'
            score = 70
        else:
            risk_level = '低风险'
            action = '安全'
            score = 85
        
        return {
            'risk_level': risk_level,
            'risk_percent': risk_percent,
            'action': action,
            'score': score,
            'description': f'风险等级：{risk_level} ({risk_percent:.1f}%)',
        }
    
    def analyze_company(self, stock_data: dict, capital: float = 1000000) -> dict:
        """
        海龟交易综合分析
        
        Args:
            stock_data: 股票数据
            capital: 账户资金
        
        Returns:
            dict: 综合分析结果
        """
        # 分析各维度
        position_size = self.calculate_position_size(stock_data, capital)
        entry_signal = self.analyze_entry_signal(stock_data)
        stop_loss = self.analyze_stop_loss(stock_data)
        add_position = self.analyze_add_position(stock_data)
        exit_signal = self.analyze_exit_signal(stock_data)
        risk_management = self.analyze_risk_management(stock_data, capital)
        
        # 综合评分
        total_score = (
            position_size['score'] * 0.15 +
            entry_signal['score'] * 0.20 +
            stop_loss['score'] * 0.20 +
            add_position['score'] * 0.15 +
            exit_signal['score'] * 0.15 +
            risk_management['score'] * 0.15
        )
        
        # 海龟评级
        if total_score >= 80:
            rating = '强烈买入信号'
            turtle_rating = '⭐⭐⭐⭐⭐'
            recommendation = '买入 1-2 单位'
        elif total_score >= 70:
            rating = '买入信号'
            turtle_rating = '⭐⭐⭐⭐'
            recommendation = '买入 1 单位'
        elif total_score >= 60:
            rating = '观望信号'
            turtle_rating = '⭐⭐⭐'
            recommendation = '观望'
        elif total_score >= 50:
            rating = '中性信号'
            turtle_rating = '⭐⭐'
            recommendation = '持有'
        elif total_score >= 40:
            rating = '卖出信号'
            turtle_rating = '⭐'
            recommendation = '减仓'
        else:
            rating = '强烈卖出信号'
            turtle_rating = ''
            recommendation = '清仓'
        
        return {
            'total_score': round(total_score, 1),
            'rating': rating,
            'turtle_rating': turtle_rating,
            'recommendation': recommendation,
            'position_size': position_size,
            'entry_signal': entry_signal,
            'stop_loss': stop_loss,
            'add_position': add_position,
            'exit_signal': exit_signal,
            'risk_management': risk_management,
            'analysis_time': datetime.now().isoformat(),
        }
    
    def get_decision_bonus(self, analysis_result: dict) -> float:
        """
        根据海龟交易分析结果计算决策加分
        
        Args:
            analysis_result: 分析结果
        
        Returns:
            float: 决策加分 (0-0.3)
        """
        total_score = analysis_result.get('total_score', 0)
        
        if total_score >= 80:
            return 0.30  # 强烈买入
        elif total_score >= 70:
            return 0.25  # 买入
        elif total_score >= 60:
            return 0.20  # 观望
        elif total_score >= 50:
            return 0.10  # 中性
        elif total_score >= 40:
            return 0.05  # 卖出
        else:
            return 0.00  # 强烈卖出


def analyze_turtle_trading(stock_data: dict, capital: float = 1000000) -> dict:
    """
    海龟交易分析 (快捷函数)
    
    Args:
        stock_data: 股票数据
        capital: 账户资金
    
    Returns:
        dict: 分析结果
    """
    strategy = TurtleTradingStrategy()
    return strategy.analyze_company(stock_data, capital)


# ============ 主函数 ============

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='海龟交易法则策略')
    parser.add_argument('--stock', type=str, help='股票代码')
    parser.add_argument('--capital', type=float, default=1000000, help='账户资金')
    parser.add_argument('--analyze', type=str, help='分析模式')
    
    args = parser.parse_args()
    
    if args.stock:
        # 测试分析
        test_data = {
            'symbol': args.stock,
            'name': '测试股票',
            'price': 50.0,
            'change_pct': 5.0,
            'volume': 3000000,
            'amount': 150000000,
        }
        
        strategy = TurtleTradingStrategy()
        result = strategy.analyze_company(test_data, args.capital)
        
        print(f"\n{'='*80}")
        print(f"🐢 {args.stock} 海龟交易分析报告")
        print(f"账户资金：¥{args.capital:,.0f}")
        print(f"{'='*80}")
        print(f"\n综合评分：{result['total_score']}/100")
        print(f"海龟评级：{result['turtle_rating']} {result['rating']}")
        print(f"操作建议：{result['recommendation']}")
        print(f"\n各维度分析:")
        print(f"  头寸规模：{result['position_size']['description']}")
        print(f"  入场信号：{result['entry_signal']['description']}")
        print(f"  止损策略：{result['stop_loss']['description']}")
        print(f"  加仓策略：{result['add_position']['description']}")
        print(f"  退出信号：{result['exit_signal']['description']}")
        print(f"  风险管理：{result['risk_management']['description']}")
        print(f"\n决策加分：{strategy.get_decision_bonus(result):.2f}")
        print(f"{'='*80}\n")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
