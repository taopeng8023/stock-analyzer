#!/usr/bin/env python3
"""
交易心理分析模块
基于《以交易为生》- 亚历山大·埃尔德

核心系统:
1. 三重滤网交易系统
2. 交易心理分析
3. 资金管理
4. 风险控制系统

用法:
    python3 trading_psychology.py --stock sh600000
    python3 trading_psychology.py --analyze all
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

sys.path.insert(0, str(Path(__file__).parent))


class TradingPsychologyStrategy:
    """
    交易心理策略
    
    基于亚历山大·埃尔德《以交易为生》
    """
    
    def __init__(self):
        pass
    
    def analyze_triple_screen(self, stock_data: dict) -> dict:
        """
        三重滤网系统分析
        
        第一重滤网：长期趋势 (周线)
        第二重滤网：中期趋势 (日线)
        第三重滤网：短期入场 (小时线)
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 三重滤网分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        amount = stock_data.get('amount', 0)
        
        # 简化版三重滤网判断
        if change_pct > 5 and amount > 5000000000:
            screen1 = '看涨'  # 长期趋势
            screen2 = '看涨'  # 中期趋势
            screen3 = '买入信号'  # 短期入场
            alignment = '三重共振'
            score = 90
        elif change_pct > 2 and amount > 2000000000:
            screen1 = '看涨'
            screen2 = '看涨'
            screen3 = '观望'
            alignment = '双重看涨'
            score = 70
        elif change_pct > -2:
            screen1 = '盘整'
            screen2 = '盘整'
            screen3 = '观望'
            alignment = '盘整'
            score = 50
        elif change_pct > -5:
            screen1 = '看跌'
            screen2 = '看跌'
            screen3 = '观望'
            alignment = '双重看跌'
            score = 30
        else:
            screen1 = '看跌'
            screen2 = '看跌'
            screen3 = '卖出信号'
            alignment = '三重共振'
            score = 10
        
        return {
            'screen1': screen1,
            'screen2': screen2,
            'screen3': screen3,
            'alignment': alignment,
            'score': score,
            'description': f'三重滤网：{alignment} (长{screen1}/中{screen2}/短{screen3})',
        }
    
    def analyze_trading_psychology(self, stock_data: dict) -> dict:
        """
        交易心理分析
        
        埃尔德心理要点:
        - 恐惧与贪婪
        - 希望与恐惧
        - 从众心理
        - 自律性
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 交易心理分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        volume = stock_data.get('volume', 0)
        
        # 简化版心理状态判断
        if change_pct > 10 and volume > 50000000:
            psychology = '贪婪主导'
            warning = '警惕过度乐观'
            action = '保持理性，考虑减仓'
            score = 30
        elif change_pct > 5:
            psychology = '乐观情绪'
            warning = '注意风险控制'
            action = '谨慎持有'
            score = 50
        elif change_pct > -5:
            psychology = '理性状态'
            warning = '保持纪律'
            action = '按计划操作'
            score = 70
        elif change_pct > -10:
            psychology = '恐惧情绪'
            warning = '避免恐慌性卖出'
            action = '评估基本面'
            score = 50
        else:
            psychology = '恐慌主导'
            warning = '可能是买入机会'
            action = '逆向思考'
            score = 40
        
        return {
            'psychology': psychology,
            'warning': warning,
            'action': action,
            'score': score,
            'description': f'市场心理：{psychology} - {warning}',
        }
    
    def analyze_money_management(self, stock_data: dict, capital: float = 1000000) -> dict:
        """
        资金管理分析
        
        埃尔德资金管理规则:
        - 2% 规则：单笔风险<2%
        - 6% 规则：总风险<6%
        - 头寸规模计算
        
        Args:
            stock_data: 股票数据
            capital: 账户资金
        
        Returns:
            dict: 资金管理分析结果
        """
        price = stock_data.get('price', 0)
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版风险计算
        if abs(change_pct) > 7:
            risk_per_trade = capital * 0.02  # 2% 风险
            stop_distance = price * 0.05  # 5% 止损
        elif abs(change_pct) > 3:
            risk_per_trade = capital * 0.015
            stop_distance = price * 0.03
        else:
            risk_per_trade = capital * 0.01
            stop_distance = price * 0.02
        
        # 计算可买股数
        shares = int(risk_per_trade / stop_distance) if stop_distance > 0 else 0
        position_value = shares * price
        position_percent = position_value / capital * 100
        
        # 风险评估
        if position_percent > 20:
            risk_level = '高风险'
            action = '减仓'
            score = 30
        elif position_percent > 10:
            risk_level = '中等风险'
            action = '控制仓位'
            score = 60
        else:
            risk_level = '低风险'
            action = '安全'
            score = 85
        
        return {
            'risk_per_trade': round(risk_per_trade, 0),
            'stop_distance': round(stop_distance, 2),
            'shares': shares,
            'position_value': round(position_value, 0),
            'position_percent': round(position_percent, 1),
            'risk_level': risk_level,
            'action': action,
            'score': score,
            'description': f'资金管理：{risk_level} (仓位{position_percent:.1f}%)',
        }
    
    def analyze_risk_control(self, stock_data: dict) -> dict:
        """
        风险控制分析
        
        埃尔德风控规则:
        - 止损设置
        - 风险收益比
        - 仓位控制
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 风险控制分析结果
        """
        price = stock_data.get('price', 0)
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版止损计算
        if abs(change_pct) > 7:
            stop_loss = price * 0.95  # 5% 止损
            take_profit = price * 1.10  # 10% 止盈
        elif abs(change_pct) > 3:
            stop_loss = price * 0.97
            take_profit = price * 1.08
        else:
            stop_loss = price * 0.98
            take_profit = price * 1.05
        
        # 风险收益比
        risk = price - stop_loss
        reward = take_profit - price
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        # 评估
        if risk_reward_ratio >= 2:
            evaluation = '优秀'
            score = 85
        elif risk_reward_ratio >= 1.5:
            evaluation = '良好'
            score = 70
        elif risk_reward_ratio >= 1:
            evaluation = '可接受'
            score = 55
        else:
            evaluation = '不佳'
            score = 30
        
        return {
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'evaluation': evaluation,
            'score': score,
            'description': f'风险控制：{evaluation} (风险收益比 1:{risk_reward_ratio:.1f})',
        }
    
    def analyze_market_timing(self, stock_data: dict) -> dict:
        """
        市场时机分析
        
        埃尔德时机选择:
        - 趋势确认
        - 入场时机
        - 出场时机
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 市场时机分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        volume = stock_data.get('volume', 0)
        
        # 简化版时机判断
        if change_pct > 5 and volume > 3000000:
            timing = '良好入场时机'
            action = '买入'
            confidence = '高'
            score = 80
        elif change_pct > 2:
            timing = '可入场'
            action = '分批买入'
            confidence = '中'
            score = 60
        elif change_pct > -2:
            timing = '观望'
            action = '等待'
            confidence = '低'
            score = 40
        elif change_pct > -5:
            timing = '考虑出场'
            action = '减仓'
            confidence = '中'
            score = 30
        else:
            timing = '不良时机'
            action = '避免操作'
            confidence = '高'
            score = 20
        
        return {
            'timing': timing,
            'action': action,
            'confidence': confidence,
            'score': score,
            'description': f'市场时机：{timing} - {action}',
        }
    
    def analyze_company(self, stock_data: dict, capital: float = 1000000) -> dict:
        """
        交易心理综合分析
        
        Args:
            stock_data: 股票数据
            capital: 账户资金
        
        Returns:
            dict: 综合分析结果
        """
        # 分析各维度
        triple_screen = self.analyze_triple_screen(stock_data)
        psychology = self.analyze_trading_psychology(stock_data)
        money_management = self.analyze_money_management(stock_data, capital)
        risk_control = self.analyze_risk_control(stock_data)
        market_timing = self.analyze_market_timing(stock_data)
        
        # 综合评分
        total_score = (
            triple_screen['score'] * 0.25 +
            psychology['score'] * 0.15 +
            money_management['score'] * 0.20 +
            risk_control['score'] * 0.20 +
            market_timing['score'] * 0.20
        )
        
        # 埃尔德评级
        if total_score >= 80:
            rating = '强烈买入'
            elder_rating = '⭐⭐⭐⭐⭐'
            recommendation = '买入 (符合三重滤网)'
        elif total_score >= 70:
            rating = '买入'
            elder_rating = '⭐⭐⭐⭐'
            recommendation = '买入 (控制仓位)'
        elif total_score >= 60:
            rating = '观望'
            elder_rating = '⭐⭐⭐'
            recommendation = '观望等待'
        elif total_score >= 50:
            rating = '中性'
            elder_rating = '⭐⭐'
            recommendation = '持有'
        elif total_score >= 40:
            rating = '减仓'
            elder_rating = '⭐'
            recommendation = '减仓'
        else:
            rating = '卖出'
            elder_rating = ''
            recommendation = '卖出/空仓'
        
        return {
            'total_score': round(total_score, 1),
            'rating': rating,
            'elder_rating': elder_rating,
            'recommendation': recommendation,
            'triple_screen': triple_screen,
            'psychology': psychology,
            'money_management': money_management,
            'risk_control': risk_control,
            'market_timing': market_timing,
            'analysis_time': datetime.now().isoformat(),
        }
    
    def get_decision_bonus(self, analysis_result: dict) -> float:
        """
        根据交易心理分析结果计算决策加分
        
        Args:
            analysis_result: 分析结果
        
        Returns:
            float: 决策加分 (0-0.2)
        """
        total_score = analysis_result.get('total_score', 0)
        
        if total_score >= 80:
            return 0.20  # 强烈买入
        elif total_score >= 70:
            return 0.18  # 买入
        elif total_score >= 60:
            return 0.15  # 观望
        elif total_score >= 50:
            return 0.08  # 中性
        elif total_score >= 40:
            return 0.03  # 减仓
        else:
            return 0.00  # 卖出


def analyze_trading_psychology(stock_data: dict, capital: float = 1000000) -> dict:
    """
    交易心理分析 (快捷函数)
    
    Args:
        stock_data: 股票数据
        capital: 账户资金
    
    Returns:
        dict: 分析结果
    """
    strategy = TradingPsychologyStrategy()
    return strategy.analyze_company(stock_data, capital)


# ============ 主函数 ============

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='交易心理分析策略')
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
        
        strategy = TradingPsychologyStrategy()
        result = strategy.analyze_company(test_data, args.capital)
        
        print(f"\n{'='*80}")
        print(f"🧠 {args.stock} 交易心理分析报告")
        print(f"账户资金：¥{args.capital:,.0f}")
        print(f"{'='*80}")
        print(f"\n综合评分：{result['total_score']}/100")
        print(f"埃尔德评级：{result['elder_rating']} {result['rating']}")
        print(f"操作建议：{result['recommendation']}")
        print(f"\n各维度分析:")
        print(f"  三重滤网：{result['triple_screen']['description']}")
        print(f"  交易心理：{result['psychology']['description']}")
        print(f"  资金管理：{result['money_management']['description']}")
        print(f"  风险控制：{result['risk_control']['description']}")
        print(f"  市场时机：{result['market_timing']['description']}")
        print(f"\n决策加分：{strategy.get_decision_bonus(result):.2f}")
        print(f"{'='*80}\n")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
