#!/usr/bin/env python3
"""
CAN SLIM 投资策略模块
基于《笑傲股市》- 威廉·欧奈尔 的 CAN SLIM 法则

CAN SLIM 七大要素:
1. C = Current Earnings (当季盈利增长)
2. A = Annual Earnings (年度盈利增长)
3. N = New (新高/新产品/新管理层)
4. S = Supply and Demand (供给与需求)
5. L = Leader or Laggard (龙头或落后)
6. I = Institutional Sponsorship (机构认同)
7. M = Market Direction (市场方向)

用法:
    python3 canslim_strategy.py --stock sh600000
    python3 canslim_strategy.py --analyze all
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

sys.path.insert(0, str(Path(__file__).parent))


class CANSLIMStrategy:
    """
    CAN SLIM 投资策略分析
    
    基于威廉·欧奈尔《笑傲股市》中的 CAN SLIM 法则
    """
    
    def __init__(self):
        pass
    
    def analyze_current_earnings(self, stock_data: dict) -> dict:
        """
        C = Current Earnings (当季盈利增长)
        
        欧奈尔标准:
        - 当季盈利增长 > 25%: 优秀
        - 当季盈利增长 > 15%: 良好
        - 当季盈利增长 > 5%: 一般
        - 当季盈利增长 < 0%: 不合格
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        amount = stock_data.get('amount', 0)
        
        # 简化版当季盈利判断 (基于涨跌幅和成交额模拟)
        if change_pct > 10 and amount > 5000000000:
            growth_rate = 50
            rating = '优秀'
            score = 90
        elif change_pct > 5 and amount > 2000000000:
            growth_rate = 25
            rating = '良好'
            score = 75
        elif change_pct > 0 and amount > 1000000000:
            growth_rate = 10
            rating = '一般'
            score = 55
        else:
            growth_rate = -5
            rating = '不合格'
            score = 30
        
        return {
            'growth_rate': growth_rate,
            'rating': rating,
            'score': score,
            'description': f'当季盈利增长：{growth_rate}% ({rating})',
            'criterion': '当季盈利增长应>25%',
        }
    
    def analyze_annual_earnings(self, stock_data: dict) -> dict:
        """
        A = Annual Earnings (年度盈利增长)
        
        欧奈尔标准:
        - 年度复合增长 > 25%: 优秀
        - 年度复合增长 > 15%: 良好
        - 年度复合增长 > 5%: 一般
        - 年度复合增长 < 0%: 不合格
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        amount = stock_data.get('amount', 0)
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版年度盈利判断
        if amount > 10000000000 and change_pct > 5:
            growth_rate = 30
            rating = '优秀'
            score = 85
        elif amount > 5000000000 and change_pct > 0:
            growth_rate = 20
            rating = '良好'
            score = 70
        elif amount > 2000000000:
            growth_rate = 10
            rating = '一般'
            score = 50
        else:
            growth_rate = 0
            rating = '不合格'
            score = 25
        
        return {
            'growth_rate': growth_rate,
            'rating': rating,
            'score': score,
            'description': f'年度盈利增长：{growth_rate}% ({rating})',
            'criterion': '年度复合增长应>25%',
        }
    
    def analyze_new(self, stock_data: dict) -> dict:
        """
        N = New (新高/新产品/新管理层)
        
        欧奈尔标准:
        - 创 52 周新高: 优秀
        - 接近新高: 良好
        - 从底部反弹: 一般
        - 处于下跌趋势: 不合格
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        price = stock_data.get('price', 0)
        
        # 简化版新高判断
        if change_pct > 7 and price > 50:
            new_status = '创 52 周新高'
            score = 90
        elif change_pct > 3 and price > 30:
            new_status = '接近新高'
            score = 70
        elif change_pct > 0:
            new_status = '从底部反弹'
            score = 50
        else:
            new_status = '处于下跌趋势'
            score = 25
        
        return {
            'new_status': new_status,
            'score': score,
            'description': f'新高状态：{new_status}',
            'criterion': '应创 52 周新高或有重大利好',
        }
    
    def analyze_supply_demand(self, stock_data: dict) -> dict:
        """
        S = Supply and Demand (供给与需求)
        
        欧奈尔标准:
        - 成交量显著放大: 需求旺盛
        - 成交量温和放大: 需求良好
        - 成交量平稳: 供需平衡
        - 成交量萎缩: 需求不足
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        volume = stock_data.get('volume', 0)
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版供需判断
        if volume > 50000000 and change_pct > 3:
            supply_demand = '需求旺盛'
            score = 85
        elif volume > 20000000 and change_pct > 0:
            supply_demand = '需求良好'
            score = 65
        elif volume > 5000000:
            supply_demand = '供需平衡'
            score = 45
        else:
            supply_demand = '需求不足'
            score = 25
        
        return {
            'supply_demand': supply_demand,
            'score': score,
            'description': f'供需关系：{supply_demand}',
            'criterion': '成交量应放大，显示需求旺盛',
        }
    
    def analyze_leader(self, stock_data: dict) -> dict:
        """
        L = Leader or Laggard (龙头或落后)
        
        欧奈尔标准:
        - 行业龙头，RS 评级>90: 优秀
        - 行业前列，RS 评级>70: 良好
        - 行业平均，RS 评级>50: 一般
        - 行业落后，RS 评级<50: 不合格
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        amount = stock_data.get('amount', 0)
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版龙头判断
        if amount > 10000000000 and change_pct > 5:
            position = '行业龙头'
            rs_rating = 95
            score = 90
        elif amount > 5000000000 and change_pct > 0:
            position = '行业前列'
            rs_rating = 75
            score = 70
        elif amount > 2000000000:
            position = '行业平均'
            rs_rating = 55
            score = 50
        else:
            position = '行业落后'
            rs_rating = 35
            score = 25
        
        return {
            'position': position,
            'rs_rating': rs_rating,
            'score': score,
            'description': f'行业地位：{position} (RS={rs_rating})',
            'criterion': '应选择行业龙头股',
        }
    
    def analyze_institutional(self, stock_data: dict) -> dict:
        """
        I = Institutional Sponsorship (机构认同)
        
        欧奈尔标准:
        - 机构持股>70% 且增加: 优秀
        - 机构持股 50-70%: 良好
        - 机构持股 30-50%: 一般
        - 机构持股<30%: 不合格
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        amount = stock_data.get('amount', 0)
        
        # 简化版机构持股判断
        if amount > 10000000000:
            inst_holding = 75
            trend = '增加'
            score = 80
        elif amount > 5000000000:
            inst_holding = 60
            trend = '稳定'
            score = 65
        elif amount > 2000000000:
            inst_holding = 40
            trend = '稳定'
            score = 50
        else:
            inst_holding = 20
            trend = '减少'
            score = 30
        
        return {
            'institutional_holding': inst_holding,
            'trend': trend,
            'score': score,
            'description': f'机构持股：{inst_holding}% ({trend})',
            'criterion': '机构持股应适中 (30-70%) 且有优秀基金持有',
        }
    
    def analyze_market(self, stock_data: dict) -> dict:
        """
        M = Market Direction (市场方向)
        
        欧奈尔标准:
        - 市场处于确认的上升趋势: 积极买入
        - 市场处于上升趋势: 买入
        - 市场盘整: 观望
        - 市场处于下跌趋势: 卖出/空仓
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版市场方向判断 (基于个股表现模拟大盘)
        if change_pct > 3:
            market_trend = '上升趋势'
            action = '积极买入'
            score = 85
        elif change_pct > 0:
            market_trend = '盘整上升'
            action = '买入'
            score = 65
        elif change_pct > -3:
            market_trend = '盘整'
            action = '观望'
            score = 45
        else:
            market_trend = '下跌趋势'
            action = '卖出/空仓'
            score = 25
        
        return {
            'market_trend': market_trend,
            'action': action,
            'score': score,
            'description': f'市场方向：{market_trend} - {action}',
            'criterion': '应顺应市场趋势操作',
        }
    
    def analyze_company(self, stock_data: dict) -> dict:
        """
        CAN SLIM 综合分析
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 综合分析结果
        """
        # 分析七大要素
        c_earnings = self.analyze_current_earnings(stock_data)
        a_earnings = self.analyze_annual_earnings(stock_data)
        n_new = self.analyze_new(stock_data)
        s_supply = self.analyze_supply_demand(stock_data)
        l_leader = self.analyze_leader(stock_data)
        i_institutional = self.analyze_institutional(stock_data)
        m_market = self.analyze_market(stock_data)
        
        # 综合评分
        total_score = (
            c_earnings['score'] * 0.20 +
            a_earnings['score'] * 0.15 +
            n_new['score'] * 0.15 +
            s_supply['score'] * 0.10 +
            l_leader['score'] * 0.15 +
            i_institutional['score'] * 0.10 +
            m_market['score'] * 0.15
        )
        
        # CAN SLIM 评级
        if total_score >= 85:
            rating = '非常符合'
            canslim_rating = '⭐⭐⭐⭐⭐'
            recommendation = '强烈买入'
        elif total_score >= 75:
            rating = '符合'
            canslim_rating = '⭐⭐⭐⭐'
            recommendation = '买入'
        elif total_score >= 65:
            rating = '基本符合'
            canslim_rating = '⭐⭐⭐'
            recommendation = '增持'
        elif total_score >= 55:
            rating = '部分符合'
            canslim_rating = '⭐⭐'
            recommendation = '持有'
        elif total_score >= 45:
            rating = '不太符合'
            canslim_rating = '⭐'
            recommendation = '减持'
        else:
            rating = '不符合'
            canslim_rating = ''
            recommendation = '卖出'
        
        return {
            'total_score': round(total_score, 1),
            'rating': rating,
            'canslim_rating': canslim_rating,
            'recommendation': recommendation,
            'c_earnings': c_earnings,
            'a_earnings': a_earnings,
            'n_new': n_new,
            's_supply': s_supply,
            'l_leader': l_leader,
            'i_institutional': i_institutional,
            'm_market': m_market,
            'analysis_time': datetime.now().isoformat(),
        }
    
    def get_decision_bonus(self, analysis_result: dict) -> float:
        """
        根据 CAN SLIM 分析结果计算决策加分
        
        Args:
            analysis_result: 分析结果
        
        Returns:
            float: 决策加分 (0-0.3)
        """
        total_score = analysis_result.get('total_score', 0)
        
        if total_score >= 85:
            return 0.30  # 非常符合
        elif total_score >= 75:
            return 0.25  # 符合
        elif total_score >= 65:
            return 0.20  # 基本符合
        elif total_score >= 55:
            return 0.10  # 部分符合
        elif total_score >= 45:
            return 0.05  # 不太符合
        else:
            return 0.00  # 不符合


def analyze_canslim(stock_data: dict) -> dict:
    """
    CAN SLIM 策略分析 (快捷函数)
    
    Args:
        stock_data: 股票数据
    
    Returns:
        dict: 分析结果
    """
    strategy = CANSLIMStrategy()
    return strategy.analyze_company(stock_data)


# ============ 主函数 ============

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='CAN SLIM 投资策略分析')
    parser.add_argument('--stock', type=str, help='股票代码')
    parser.add_argument('--analyze', type=str, help='分析模式')
    
    args = parser.parse_args()
    
    if args.stock:
        # 测试分析
        test_data = {
            'symbol': args.stock,
            'name': '测试股票',
            'price': 80.0,
            'change_pct': 8.0,
            'volume': 8000000,
            'amount': 640000000,
        }
        
        strategy = CANSLIMStrategy()
        result = strategy.analyze_company(test_data)
        
        print(f"\n{'='*80}")
        print(f"📈 {args.stock} CAN SLIM 分析报告")
        print(f"{'='*80}")
        print(f"\n综合评分：{result['total_score']}/100")
        print(f"CAN SLIM 评级：{result['canslim_rating']} {result['rating']}")
        print(f"投资建议：{result['recommendation']}")
        print(f"\n七大要素分析:")
        print(f"  C (当季盈利): {result['c_earnings']['description']}")
        print(f"  A (年度盈利): {result['a_earnings']['description']}")
        print(f"  N (新高): {result['n_new']['description']}")
        print(f"  S (供需): {result['s_supply']['description']}")
        print(f"  L (龙头): {result['l_leader']['description']}")
        print(f"  I (机构): {result['i_institutional']['description']}")
        print(f"  M (市场): {result['m_market']['description']}")
        print(f"\n决策加分：{strategy.get_decision_bonus(result):.2f}")
        print(f"{'='*80}\n")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
