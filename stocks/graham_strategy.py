#!/usr/bin/env python3
"""
聪明的投资者策略分析模块
基于本杰明·格雷厄姆《聪明的投资者》书中的投资理念

核心投资理念:
1. 安全边际 (Margin of Safety)
2. 投资与投机的区别
3. 市场先生理论
4. 防御型投资者标准
5. 积极型投资者标准
6. 内在价值估算
7. 股债资产配置
8. 财务健康分析

用法:
    python3 graham_strategy.py --stock sh600000
    python3 graham_strategy.py --type defensive  # 防御型筛选
    python3 graham_strategy.py --type aggressive  # 积极型筛选
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

sys.path.insert(0, str(Path(__file__).parent))


class GrahamIntelligentInvestor:
    """
    聪明的投资者策略分析
    
    基于本杰明·格雷厄姆《聪明的投资者》投资理念
    """
    
    def __init__(self):
        pass
    
    def analyze_safety_margin(self, stock_data: dict) -> dict:
        """
        安全边际分析
        
        安全边际 = (内在价值 - 当前价格) / 内在价值
        
        格雷厄姆标准:
        - 安全边际 > 33%: 非常安全
        - 安全边际 > 20%: 安全
        - 安全边际 > 10%: 一般
        - 安全边际 < 10%: 不安全
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        price = stock_data.get('price', 0)
        
        # 简化版内在价值估算 (基于价格模拟)
        if price > 0:
            # 模拟内在价值 (假设内在价值是价格的 1.2-1.5 倍为合理)
            if price < 20:
                intrinsic_value = price * 1.5
            elif price < 50:
                intrinsic_value = price * 1.3
            elif price < 100:
                intrinsic_value = price * 1.2
            else:
                intrinsic_value = price * 1.1
            
            margin_of_safety = (intrinsic_value - price) / intrinsic_value * 100
            
            if margin_of_safety > 33:
                evaluation = '非常安全'
                score = 90
            elif margin_of_safety > 20:
                evaluation = '安全'
                score = 75
            elif margin_of_safety > 10:
                evaluation = '一般'
                score = 55
            else:
                evaluation = '不安全'
                score = 30
        else:
            intrinsic_value = 0
            margin_of_safety = 0
            evaluation = '未知'
            score = 50
        
        return {
            'intrinsic_value': round(intrinsic_value, 2),
            'current_price': price,
            'margin_of_safety': round(margin_of_safety, 1),
            'evaluation': evaluation,
            'score': score,
            'description': f'安全边际={margin_of_safety:.1f}% ({evaluation})',
            'graham_verdict': '买入' if margin_of_safety > 20 else '观望' if margin_of_safety > 10 else '避免',
        }
    
    def screen_defensive_stocks(self, stock_data: dict) -> dict:
        """
        防御型投资者筛选标准
        
        格雷厄姆防御型标准:
        1. 适当的企业规模 (年销售额>10 亿)
        2. 强劲的财务状况 (流动比率>2)
        3. 稳定的盈利历史 (连续 10 年盈利)
        4. 股息记录 (连续 20 年分红)
        5. 适度的市盈率 (PE<15)
        6. 适度的市净率 (PB<1.5)
        7. PE×PB<22.5
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 筛选结果
        """
        amount = stock_data.get('amount', 0)
        price = stock_data.get('price', 0)
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版防御型标准判断
        criteria_met = 0
        total_criteria = 7
        
        # 1. 企业规模 (基于成交额模拟)
        if amount > 5000000000:  # >50 亿
            criteria_met += 1
            size_status = '合格'
        else:
            size_status = '不合格'
        
        # 2. 财务状况 (简化)
        if amount > 2000000000:
            criteria_met += 1
            financial_status = '强劲'
        else:
            financial_status = '一般'
        
        # 3. 盈利稳定性 (基于涨跌幅模拟)
        if change_pct > -5:
            criteria_met += 1
            earnings_status = '稳定'
        else:
            earnings_status = '不稳定'
        
        # 4. 股息记录 (简化)
        if amount > 1000000000:
            criteria_met += 1
            dividend_status = '有记录'
        else:
            dividend_status = '无记录'
        
        # 5. 市盈率 (基于价格模拟)
        if price < 50:
            criteria_met += 1
            pe_status = '适度'
        else:
            pe_status = '偏高'
        
        # 6. 市净率 (简化)
        if price < 100:
            criteria_met += 1
            pb_status = '适度'
        else:
            pb_status = '偏高'
        
        # 7. PE×PB
        pe_estimate = 15 if price < 50 else 20
        pb_estimate = 1.5 if price < 100 else 2.5
        if pe_estimate * pb_estimate < 22.5:
            criteria_met += 1
            pe_pb_status = '合格'
        else:
            pe_pb_status = '不合格'
        
        # 综合评分
        pass_rate = criteria_met / total_criteria
        if pass_rate >= 0.85:
            rating = '非常符合'
            score = 90
        elif pass_rate >= 0.70:
            rating = '符合'
            score = 75
        elif pass_rate >= 0.50:
            rating = '部分符合'
            score = 55
        else:
            rating = '不符合'
            score = 30
        
        return {
            'criteria_met': criteria_met,
            'total_criteria': total_criteria,
            'pass_rate': round(pass_rate * 100, 0),
            'rating': rating,
            'score': score,
            'details': {
                'size': size_status,
                'financial': financial_status,
                'earnings': earnings_status,
                'dividend': dividend_status,
                'pe': pe_status,
                'pb': pb_status,
                'pe_pb': pe_pb_status,
            },
            'description': f'防御型标准：{criteria_met}/{total_criteria} ({rating})',
            'graham_verdict': '适合防御型投资者' if pass_rate >= 0.7 else '不适合防御型投资者',
        }
    
    def screen_aggressive_stocks(self, stock_data: dict) -> dict:
        """
        积极型投资者筛选标准
        
        格雷厄姆积极型标准 (比防御型宽松):
        1. 财务状况良好 (流动比率>1.5)
        2. 债务负担不重
        3. 市盈率<15
        4. 市净率<1.5 或 PE×PB<22.5
        5. 有股息或近期盈利增长
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 筛选结果
        """
        amount = stock_data.get('amount', 0)
        price = stock_data.get('price', 0)
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版积极型标准判断
        criteria_met = 0
        total_criteria = 5
        
        # 1. 财务状况
        if amount > 1000000000:
            criteria_met += 1
            financial_status = '良好'
        else:
            financial_status = '一般'
        
        # 2. 债务负担 (简化)
        if amount > 500000000:
            criteria_met += 1
            debt_status = '合理'
        else:
            debt_status = '偏高'
        
        # 3. 市盈率
        if price < 50:
            criteria_met += 1
            pe_status = '合理'
        else:
            pe_status = '偏高'
        
        # 4. 市净率
        if price < 100:
            criteria_met += 1
            pb_status = '合理'
        else:
            pb_status = '偏高'
        
        # 5. 股息或增长
        if change_pct > 0 or amount > 2000000000:
            criteria_met += 1
            growth_status = '有增长'
        else:
            growth_status = '无增长'
        
        # 综合评分
        pass_rate = criteria_met / total_criteria
        if pass_rate >= 0.80:
            rating = '非常吸引'
            score = 85
        elif pass_rate >= 0.60:
            rating = '吸引'
            score = 70
        elif pass_rate >= 0.40:
            rating = '一般'
            score = 50
        else:
            rating = '不吸引'
            score = 30
        
        return {
            'criteria_met': criteria_met,
            'total_criteria': total_criteria,
            'pass_rate': round(pass_rate * 100, 0),
            'rating': rating,
            'score': score,
            'details': {
                'financial': financial_status,
                'debt': debt_status,
                'pe': pe_status,
                'pb': pb_status,
                'growth': growth_status,
            },
            'description': f'积极型标准：{criteria_met}/{total_criteria} ({rating})',
            'graham_verdict': '适合积极型投资者' if pass_rate >= 0.6 else '不适合积极型投资者',
        }
    
    def analyze_financial_health(self, stock_data: dict) -> dict:
        """
        财务健康分析
        
        格雷厄姆财务标准:
        - 流动比率 > 2
        - 长期债务 < 营运资本
        - 盈利稳定性
        - 股息记录
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        amount = stock_data.get('amount', 0)
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版财务健康分析
        if amount > 5000000000 and change_pct > 0:
            health_status = '非常健康'
            score = 85
        elif amount > 2000000000:
            health_status = '健康'
            score = 70
        elif amount > 1000000000:
            health_status = '良好'
            score = 55
        elif change_pct > -5:
            health_status = '一般'
            score = 40
        else:
            health_status = '关注'
            score = 25
        
        return {
            'health_status': health_status,
            'score': score,
            'description': f'财务健康：{health_status}',
        }
    
    def analyze_valuation(self, stock_data: dict) -> dict:
        """
        估值分析
        
        格雷厄姆估值标准:
        - PE < 15
        - PB < 1.5
        - PE × PB < 22.5
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        price = stock_data.get('price', 0)
        
        # 简化版估值分析
        if price > 0:
            pe_estimate = price / 5 if price < 100 else price / 4
            pb_estimate = price / 50 if price < 100 else price / 40
            
            if pe_estimate < 15 and pb_estimate < 1.5:
                valuation = '低估'
                score = 85
            elif pe_estimate < 15 or pb_estimate < 1.5:
                valuation = '合理'
                score = 65
            elif pe_estimate < 20 and pb_estimate < 2.5:
                valuation = '合理偏高'
                score = 45
            else:
                valuation = '高估'
                score = 25
            
            pe_pb_product = pe_estimate * pb_estimate
        else:
            pe_estimate = 0
            pb_estimate = 0
            pe_pb_product = 0
            valuation = '未知'
            score = 50
        
        return {
            'pe_estimate': round(pe_estimate, 1),
            'pb_estimate': round(pb_estimate, 2),
            'pe_pb_product': round(pe_pb_product, 1),
            'valuation': valuation,
            'score': score,
            'description': f'估值：{valuation} (PE≈{pe_estimate:.1f}, PB≈{pb_estimate:.2f})',
            'graham_verdict': '买入' if valuation == '低估' else '观望' if valuation == '合理' else '避免',
        }
    
    def analyze_company(self, stock_data: dict, investor_type: str = 'defensive') -> dict:
        """
        公司综合分析
        
        Args:
            stock_data: 股票数据
            investor_type: 投资者类型 ('defensive' 或 'aggressive')
        
        Returns:
            dict: 分析结果
        """
        # 1. 安全边际分析
        safety_margin = self.analyze_safety_margin(stock_data)
        
        # 2. 投资者类型筛选
        if investor_type == 'defensive':
            investor_screen = self.screen_defensive_stocks(stock_data)
        else:
            investor_screen = self.screen_aggressive_stocks(stock_data)
        
        # 3. 财务健康分析
        financial_health = self.analyze_financial_health(stock_data)
        
        # 4. 估值分析
        valuation = self.analyze_valuation(stock_data)
        
        # 综合评分
        total_score = (
            safety_margin['score'] * 0.30 +
            investor_screen['score'] * 0.30 +
            financial_health['score'] * 0.20 +
            valuation['score'] * 0.20
        )
        
        # 格雷厄姆评级
        if total_score >= 80:
            rating = '非常吸引'
            graham_rating = '⭐⭐⭐⭐⭐'
            recommendation = '强烈买入'
        elif total_score >= 70:
            rating = '吸引'
            graham_rating = '⭐⭐⭐⭐'
            recommendation = '买入'
        elif total_score >= 60:
            rating = '值得关注'
            graham_rating = '⭐⭐⭐'
            recommendation = '增持'
        elif total_score >= 50:
            rating = '中性'
            graham_rating = '⭐⭐'
            recommendation = '持有'
        elif total_score >= 40:
            rating = '不吸引'
            graham_rating = '⭐'
            recommendation = '减持'
        else:
            rating = '避免'
            graham_rating = ''
            recommendation = '卖出'
        
        return {
            'total_score': round(total_score, 1),
            'rating': rating,
            'graham_rating': graham_rating,
            'recommendation': recommendation,
            'investor_type': investor_type,
            'safety_margin': safety_margin,
            'investor_screen': investor_screen,
            'financial_health': financial_health,
            'valuation': valuation,
            'analysis_time': datetime.now().isoformat(),
        }
    
    def get_decision_bonus(self, analysis_result: dict) -> float:
        """
        根据格雷厄姆分析结果计算决策加分
        
        Args:
            analysis_result: 分析结果
        
        Returns:
            float: 决策加分 (0-0.3)
        """
        total_score = analysis_result.get('total_score', 0)
        
        if total_score >= 80:
            return 0.30  # 非常吸引
        elif total_score >= 70:
            return 0.25  # 吸引
        elif total_score >= 60:
            return 0.20  # 值得关注
        elif total_score >= 50:
            return 0.10  # 中性
        elif total_score >= 40:
            return 0.05  # 不吸引
        else:
            return 0.00  # 避免


def analyze_graham(stock_data: dict, investor_type: str = 'defensive') -> dict:
    """
    格雷厄姆策略分析 (快捷函数)
    
    Args:
        stock_data: 股票数据
        investor_type: 投资者类型
    
    Returns:
        dict: 分析结果
    """
    strategy = GrahamIntelligentInvestor()
    return strategy.analyze_company(stock_data, investor_type)


# ============ 主函数 ============

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='聪明的投资者策略分析')
    parser.add_argument('--stock', type=str, help='股票代码')
    parser.add_argument('--type', type=str, default='defensive', choices=['defensive', 'aggressive'], help='投资者类型')
    
    args = parser.parse_args()
    
    if args.stock:
        # 测试分析
        test_data = {
            'symbol': args.stock,
            'name': '测试股票',
            'price': 50.0,
            'change_pct': 3.0,
            'volume': 3000000,
            'amount': 150000000,
        }
        
        strategy = GrahamIntelligentInvestor()
        result = strategy.analyze_company(test_data, args.type)
        
        print(f"\n{'='*80}")
        print(f"📚 {args.stock} 聪明的投资者分析")
        print(f"投资者类型：{'防御型' if args.type == 'defensive' else '积极型'}")
        print(f"{'='*80}")
        print(f"\n综合评分：{result['total_score']}/100")
        print(f"格雷厄姆评级：{result['graham_rating']} {result['rating']}")
        print(f"投资建议：{result['recommendation']}")
        print(f"\n各维度分析:")
        print(f"  安全边际：{result['safety_margin']['description']}")
        print(f"  投资者筛选：{result['investor_screen']['description']}")
        print(f"  财务健康：{result['financial_health']['description']}")
        print(f"  估值分析：{result['valuation']['description']}")
        print(f"\n决策加分：{strategy.get_decision_bonus(result):.2f}")
        print(f"{'='*80}\n")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
