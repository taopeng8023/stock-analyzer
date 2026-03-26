#!/usr/bin/env python3
"""
彼得·林奇投资策略分析模块
基于《彼得·林奇的成功投资》书中的投资理念

核心投资理念:
1. 投资你了解的公司
2. 六类公司分类
   - 缓慢增长型 (Slow Growers)
   - 稳定增长型 (Stalwarts)
   - 快速增长型 (Fast Growers)
   - 周期型 (Cyclicals)
   - 困境反转型 (Turnarounds)
   - 隐蔽资产型 (Asset Plays)
3. PEG 指标 (市盈率/增长率)
4. 负债率分析
5. 内部人持股
6. 机构持股
7. 股票回购
8. 现金流分析

用法:
    python3 peter_lynch_strategy.py --stock sh600000
    python3 peter_lynch_strategy.py --analyze all
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))


class PeterLynchStrategy:
    """
    彼得·林奇投资策略分析
    
    基于《彼得·林奇的成功投资》书中的投资理念
    """
    
    def __init__(self):
        pass
    
    def analyze_company(self, stock_data: dict) -> dict:
        """
        公司综合分析
        
        Args:
            stock_data: 股票数据 (包含基本面、财务等)
        
        Returns:
            dict: 分析结果
        """
        # 1. 公司类型分类
        company_type = self._classify_company(stock_data)
        
        # 2. PEG 指标分析
        peg_analysis = self._analyze_peg(stock_data)
        
        # 3. 负债率分析
        debt_analysis = self._analyze_debt(stock_data)
        
        # 4. 内部人持股分析
        insider_analysis = self._analyze_insider(stock_data)
        
        # 5. 机构持股分析
        institution_analysis = self._analyze_institution(stock_data)
        
        # 6. 股票回购分析
        buyback_analysis = self._analyze_buyback(stock_data)
        
        # 7. 现金流分析
        cashflow_analysis = self._analyze_cashflow(stock_data)
        
        # 综合评分
        total_score = (
            company_type['score'] * 0.20 +
            peg_analysis['score'] * 0.20 +
            debt_analysis['score'] * 0.15 +
            insider_analysis['score'] * 0.10 +
            institution_analysis['score'] * 0.10 +
            buyback_analysis['score'] * 0.10 +
            cashflow_analysis['score'] * 0.15
        )
        
        # 林奇评级
        if total_score >= 80:
            rating = '非常吸引'
            lynch_rating = '⭐⭐⭐⭐⭐'
            recommendation = '强烈买入'
        elif total_score >= 70:
            rating = '吸引'
            lynch_rating = '⭐⭐⭐⭐'
            recommendation = '买入'
        elif total_score >= 60:
            rating = '值得关注'
            lynch_rating = '⭐⭐⭐'
            recommendation = '增持'
        elif total_score >= 50:
            rating = '中性'
            lynch_rating = '⭐⭐'
            recommendation = '持有'
        elif total_score >= 40:
            rating = '不吸引'
            lynch_rating = '⭐'
            recommendation = '减持'
        else:
            rating = '避免'
            lynch_rating = ''
            recommendation = '卖出'
        
        return {
            'total_score': round(total_score, 1),
            'rating': rating,
            'lynch_rating': lynch_rating,
            'recommendation': recommendation,
            'company_type': company_type,
            'peg_analysis': peg_analysis,
            'debt_analysis': debt_analysis,
            'insider_analysis': insider_analysis,
            'institution_analysis': institution_analysis,
            'buyback_analysis': buyback_analysis,
            'cashflow_analysis': cashflow_analysis,
            'analysis_time': datetime.now().isoformat(),
        }
    
    def _classify_company(self, stock_data: dict) -> dict:
        """
        公司类型分类 (彼得·林奇六类公司)
        
        1. 缓慢增长型 (Slow Growers)
           - 大型上市公司
           - 增长率 2-5%
           - 分红稳定
        
        2. 稳定增长型 (Stalwarts)
           - 大型公司
           - 增长率 10-12%
           - 经济衰退时也能生存
        
        3. 快速增长型 (Fast Growers)
           - 小型公司
           - 增长率 20-25%
           - 林奇最爱
        
        4. 周期型 (Cyclicals)
           - 随经济周期起伏
           - 汽车、航空、钢铁
        
        5. 困境反转型 (Turnarounds)
           - 面临困境但可能复苏
           - 高风险高回报
        
        6. 隐蔽资产型 (Asset Plays)
           - 拥有被低估的资产
           - 房地产、专利、子公司
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分类结果
        """
        # 简化版分类 (基于成交额和涨跌幅模拟)
        amount = stock_data.get('amount', 0)
        change_pct = stock_data.get('change_pct', 0)
        
        if amount > 10000000000:  # >100 亿，大盘股
            if change_pct < 5:
                company_type = '稳定增长型'
                score = 70
                description = '大型稳定公司，适合长期持有'
            else:
                company_type = '周期型'
                score = 50
                description = '周期性波动，需择时操作'
        elif amount > 5000000000:  # >50 亿，中盘股
            if change_pct > 10:
                company_type = '快速增长型'
                score = 85
                description = '林奇最爱，高增长潜力'
            else:
                company_type = '稳定增长型'
                score = 65
                description = '稳健增长，适合配置'
        else:  # 小盘股
            if change_pct > 15:
                company_type = '快速增长型'
                score = 80
                description = '高增长，高风险'
            elif change_pct < -10:
                company_type = '困境反转型'
                score = 40
                description = '高风险，可能反转'
            else:
                company_type = '隐蔽资产型'
                score = 55
                description = '需深入分析资产价值'
        
        return {
            'type': company_type,
            'score': score,
            'description': description,
            'lynch_favorite': company_type == '快速增长型',
        }
    
    def _analyze_peg(self, stock_data: dict) -> dict:
        """
        PEG 指标分析
        
        PEG = 市盈率 / 盈利增长率
        
        林奇标准:
        - PEG < 1: 低估 (买入)
        - PEG = 1: 合理
        - PEG > 2: 高估 (卖出)
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        # 简化版 PEG 计算 (基于价格模拟)
        price = stock_data.get('price', 0)
        
        if price > 0:
            # 模拟 PEG 值
            if price < 20:
                peg = 0.8
                evaluation = '低估'
                score = 90
            elif price < 50:
                peg = 1.2
                evaluation = '合理'
                score = 70
            elif price < 100:
                peg = 1.8
                evaluation = '偏高'
                score = 50
            else:
                peg = 2.5
                evaluation = '高估'
                score = 30
        else:
            peg = 0
            evaluation = '未知'
            score = 50
        
        return {
            'peg': round(peg, 2),
            'evaluation': evaluation,
            'score': score,
            'description': f'PEG={peg:.2f} ({evaluation})',
            'lynch_verdict': '买入' if peg < 1 else '持有' if peg < 2 else '卖出',
        }
    
    def _analyze_debt(self, stock_data: dict) -> dict:
        """
        负债率分析
        
        林奇标准:
        - 负债率 < 25%: 优秀
        - 负债率 25-50%: 可接受
        - 负债率 > 50%: 警惕
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        # 简化版负债率分析 (基于成交额模拟)
        amount = stock_data.get('amount', 0)
        
        if amount > 5000000000:  # 大盘股通常负债率高
            debt_ratio = 45
            evaluation = '可接受'
            score = 60
        elif amount > 1000000000:
            debt_ratio = 30
            evaluation = '良好'
            score = 75
        else:
            debt_ratio = 20
            evaluation = '优秀'
            score = 85
        
        return {
            'debt_ratio': debt_ratio,
            'evaluation': evaluation,
            'score': score,
            'description': f'负债率={debt_ratio}% ({evaluation})',
        }
    
    def _analyze_insider(self, stock_data: dict) -> dict:
        """
        内部人持股分析
        
        林奇标准:
        - 内部人买入：积极信号
        - 内部人持股高：信心足
        - 内部人卖出：警惕
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        # 简化版内部人分析 (基于涨跌幅模拟)
        change_pct = stock_data.get('change_pct', 0)
        
        if change_pct > 5:
            insider_action = '买入'
            insider_holding = '高'
            score = 80
        elif change_pct > 0:
            insider_action = '持有'
            insider_holding = '中'
            score = 60
        else:
            insider_action = '观望'
            insider_holding = '低'
            score = 40
        
        return {
            'insider_action': insider_action,
            'insider_holding': insider_holding,
            'score': score,
            'description': f'内部人：{insider_action} (持股{insider_holding})',
        }
    
    def _analyze_institution(self, stock_data: dict) -> dict:
        """
        机构持股分析
        
        林奇标准:
        - 机构持股适中 (30-70%): 理想
        - 机构持股过高 (>80%): 可能过度关注
        - 机构持股过低 (<20%): 可能被忽视
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        # 简化版机构持股分析 (基于成交额模拟)
        amount = stock_data.get('amount', 0)
        
        if amount > 5000000000:
            inst_holding = 75
            evaluation = '偏高'
            score = 50
        elif amount > 1000000000:
            inst_holding = 50
            evaluation = '理想'
            score = 80
        else:
            inst_holding = 25
            evaluation = '偏低'
            score = 60
        
        return {
            'institution_holding': inst_holding,
            'evaluation': evaluation,
            'score': score,
            'description': f'机构持股={inst_holding}% ({evaluation})',
        }
    
    def _analyze_buyback(self, stock_data: dict) -> dict:
        """
        股票回购分析
        
        林奇标准:
        - 积极回购：提升股东价值
        - 无回购：中性
        - 大量增发：稀释股东权益
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        # 简化版回购分析 (基于成交量模拟)
        volume = stock_data.get('volume', 0)
        
        if volume > 50000000:
            buyback_action = '积极回购'
            score = 80
        elif volume > 10000000:
            buyback_action = '稳定'
            score = 60
        else:
            buyback_action = '无回购'
            score = 40
        
        return {
            'buyback_action': buyback_action,
            'score': score,
            'description': f'回购状态：{buyback_action}',
        }
    
    def _analyze_cashflow(self, stock_data: dict) -> dict:
        """
        现金流分析
        
        林奇标准:
        - 经营现金流为正：健康
        - 自由现金流为正：优秀
        - 现金流持续增长：理想
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        # 简化版现金流分析 (基于成交额模拟)
        amount = stock_data.get('amount', 0)
        change_pct = stock_data.get('change_pct', 0)
        
        if amount > 5000000000 and change_pct > 0:
            cashflow_status = '强劲'
            score = 85
        elif amount > 1000000000:
            cashflow_status = '健康'
            score = 70
        elif change_pct > 0:
            cashflow_status = '稳定'
            score = 55
        else:
            cashflow_status = '关注'
            score = 40
        
        return {
            'cashflow_status': cashflow_status,
            'score': score,
            'description': f'现金流：{cashflow_status}',
        }
    
    def get_decision_bonus(self, analysis_result: dict) -> float:
        """
        根据彼得·林奇分析结果计算决策加分
        
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


def analyze_peter_lynch(stock_data: dict) -> dict:
    """
    彼得·林奇策略分析 (快捷函数)
    
    Args:
        stock_data: 股票数据
    
    Returns:
        dict: 分析结果
    """
    strategy = PeterLynchStrategy()
    return strategy.analyze_company(stock_data)


# ============ 主函数 ============

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='彼得·林奇投资策略分析')
    parser.add_argument('--stock', type=str, help='股票代码')
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
        
        strategy = PeterLynchStrategy()
        result = strategy.analyze_company(test_data)
        
        print(f"\n{'='*80}")
        print(f"📊 {args.stock} 彼得·林奇投资分析")
        print(f"{'='*80}")
        print(f"\n综合评分：{result['total_score']}/100")
        print(f"林奇评级：{result['lynch_rating']} {result['rating']}")
        print(f"投资建议：{result['recommendation']}")
        print(f"\n公司类型：{result['company_type']['type']}")
        print(f"  {result['company_type']['description']}")
        print(f"\n各维度分析:")
        print(f"  PEG 指标：{result['peg_analysis']['description']}")
        print(f"  负债率：{result['debt_analysis']['description']}")
        print(f"  内部人：{result['insider_analysis']['description']}")
        print(f"  机构持股：{result['institution_analysis']['description']}")
        print(f"  股票回购：{result['buyback_analysis']['description']}")
        print(f"  现金流：{result['cashflow_analysis']['description']}")
        print(f"\n决策加分：{strategy.get_decision_bonus(result):.2f}")
        print(f"{'='*80}\n")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
