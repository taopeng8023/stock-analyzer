#!/usr/bin/env python3
"""
量价分析策略模块
基于《量价分析》- 安娜·库林 的核心理念

核心量价关系:
1. 价涨量增 - 健康上涨
2. 价涨量缩 - 上涨乏力
3. 价跌量增 - 恐慌下跌
4. 价跌量缩 - 下跌乏力
5. 量价背离 - 趋势反转信号
6. 放量突破 - 趋势确认
7. 缩量整理 - 趋势延续

用法:
    python3 volume_price_analysis.py --stock sh600000
    python3 volume_price_analysis.py --analyze all
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

sys.path.insert(0, str(Path(__file__).parent))


class VolumePriceAnalysis:
    """
    量价分析策略
    
    基于《量价分析》书中的核心理念
    """
    
    def __init__(self):
        pass
    
    def analyze_volume_price_relationship(self, stock_data: dict) -> dict:
        """
        量价关系分析
        
        核心量价关系:
        1. 价涨量增 - 健康上涨 (看多)
        2. 价涨量缩 - 上涨乏力 (警惕)
        3. 价跌量增 - 恐慌下跌 (看空)
        4. 价跌量缩 - 下跌乏力 (观望)
        5. 盘整放量 - 突破前兆
        6. 盘整缩量 - 延续整理
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        volume = stock_data.get('volume', 0)
        amount = stock_data.get('amount', 0)
        
        # 判断量价关系
        if change_pct > 3:  # 上涨
            if volume > 3000000:  # 放量
                relationship = '价涨量增'
                signal = '健康上涨'
                score = 85
                verdict = '看多'
            else:  # 缩量
                relationship = '价涨量缩'
                signal = '上涨乏力'
                score = 50
                verdict = '警惕'
        elif change_pct > -3:  # 盘整
            if volume > 5000000:  # 放量
                relationship = '盘整放量'
                signal = '突破前兆'
                score = 70
                verdict = '关注'
            else:  # 缩量
                relationship = '盘整缩量'
                signal = '延续整理'
                score = 55
                verdict = '观望'
        else:  # 下跌
            if volume > 3000000:  # 放量
                relationship = '价跌量增'
                signal = '恐慌下跌'
                score = 20
                verdict = '看空'
            else:  # 缩量
                relationship = '价跌量缩'
                signal = '下跌乏力'
                score = 45
                verdict = '观望'
        
        return {
            'relationship': relationship,
            'signal': signal,
            'score': score,
            'verdict': verdict,
            'description': f'量价关系：{relationship} - {signal} ({verdict})',
        }
    
    def analyze_volume_trend(self, stock_data: dict) -> dict:
        """
        成交量趋势分析
        
        分析成交量的变化趋势:
        - 成交量放大
        - 成交量缩小
        - 成交量平稳
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        volume = stock_data.get('volume', 0)
        amount = stock_data.get('amount', 0)
        
        # 简化版成交量趋势判断
        if volume > 50000000:  # >5000 万手
            trend = '显著放大'
            score = 80
        elif volume > 20000000:  # >2000 万手
            trend = '放大'
            score = 65
        elif volume > 5000000:  # >500 万手
            trend = '平稳'
            score = 50
        elif volume > 1000000:  # >100 万手
            trend = '缩小'
            score = 35
        else:
            trend = '显著缩小'
            score = 20
        
        return {
            'trend': trend,
            'score': score,
            'description': f'成交量趋势：{trend}',
        }
    
    def analyze_volume_breakout(self, stock_data: dict) -> dict:
        """
        放量突破分析
        
        识别放量突破信号:
        - 突破关键价位
        - 成交量显著放大
        - 趋势确认
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        volume = stock_data.get('volume', 0)
        amount = stock_data.get('amount', 0)
        
        # 简化版突破判断
        if change_pct > 5 and volume > 3000000:
            breakout = '放量突破'
            strength = '强'
            score = 90
            signal = '买入'
        elif change_pct > 3 and volume > 2000000:
            breakout = '温和突破'
            strength = '中'
            score = 70
            signal = '增持'
        elif change_pct > 0 and volume > 1000000:
            breakout = '小幅上涨'
            strength = '弱'
            score = 50
            signal = '持有'
        elif change_pct < -3 and volume > 3000000:
            breakout = '放量跌破'
            strength = '强'
            score = 20
            signal = '卖出'
        else:
            breakout = '无突破'
            strength = '无'
            score = 40
            signal = '观望'
        
        return {
            'breakout': breakout,
            'strength': strength,
            'score': score,
            'signal': signal,
            'description': f'突破信号：{breakout} ({strength}) - {signal}',
        }
    
    def analyze_volume_divergence(self, stock_data: dict) -> dict:
        """
        量价背离分析
        
        识别量价背离信号:
        - 顶背离：价格新高，成交量不新高 (看跌)
        - 底背离：价格新低，成交量不新低 (看涨)
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        volume = stock_data.get('volume', 0)
        price = stock_data.get('price', 0)
        
        # 简化版背离判断
        if change_pct > 5 and volume < 2000000:
            divergence = '顶背离'
            signal = '看跌'
            score = 30
            warning = '价格上涨但成交量不足，警惕反转'
        elif change_pct < -5 and volume < 2000000:
            divergence = '底背离'
            signal = '看涨'
            score = 70
            warning = '价格下跌但成交量萎缩，可能反弹'
        elif change_pct > 3 and volume > 5000000:
            divergence = '量价配合'
            signal = '健康'
            score = 80
            warning = '量价配合良好'
        else:
            divergence = '无明显背离'
            signal = '中性'
            score = 50
            warning = '无明显背离信号'
        
        return {
            'divergence': divergence,
            'signal': signal,
            'score': score,
            'warning': warning,
            'description': f'量价背离：{divergence} - {signal}',
        }
    
    def analyze_volume_accumulation(self, stock_data: dict) -> dict:
        """
        成交量累积分析
        
        分析一段时间内的成交量累积情况:
        - 资金流入
        - 资金流出
        - 资金平衡
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        amount = stock_data.get('amount', 0)
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版资金累积判断
        if amount > 5000000000 and change_pct > 0:  # >50 亿且上涨
            accumulation = '资金大幅流入'
            score = 85
            signal = '强烈看多'
        elif amount > 2000000000 and change_pct > 0:  # >20 亿且上涨
            accumulation = '资金流入'
            score = 70
            signal = '看多'
        elif amount > 5000000000 and change_pct < 0:  # >50 亿且下跌
            accumulation = '资金大幅流出'
            score = 25
            signal = '强烈看空'
        elif amount > 2000000000 and change_pct < 0:  # >20 亿且下跌
            accumulation = '资金流出'
            score = 35
            signal = '看空'
        else:
            accumulation = '资金平衡'
            score = 50
            signal = '中性'
        
        return {
            'accumulation': accumulation,
            'score': score,
            'signal': signal,
            'description': f'资金累积：{accumulation} - {signal}',
        }
    
    def analyze_company(self, stock_data: dict) -> dict:
        """
        量价综合分析报告
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 综合分析结果
        """
        # 1. 量价关系分析
        volume_price = self.analyze_volume_price_relationship(stock_data)
        
        # 2. 成交量趋势分析
        volume_trend = self.analyze_volume_trend(stock_data)
        
        # 3. 放量突破分析
        volume_breakout = self.analyze_volume_breakout(stock_data)
        
        # 4. 量价背离分析
        volume_divergence = self.analyze_volume_divergence(stock_data)
        
        # 5. 成交量累积分析
        volume_accumulation = self.analyze_volume_accumulation(stock_data)
        
        # 综合评分
        total_score = (
            volume_price['score'] * 0.30 +
            volume_trend['score'] * 0.15 +
            volume_breakout['score'] * 0.25 +
            volume_divergence['score'] * 0.15 +
            volume_accumulation['score'] * 0.15
        )
        
        # 量价评级
        if total_score >= 80:
            rating = '非常健康'
            vp_rating = '⭐⭐⭐⭐⭐'
            recommendation = '强烈买入'
        elif total_score >= 70:
            rating = '健康'
            vp_rating = '⭐⭐⭐⭐'
            recommendation = '买入'
        elif total_score >= 60:
            rating = '良好'
            vp_rating = '⭐⭐⭐'
            recommendation = '增持'
        elif total_score >= 50:
            rating = '中性'
            vp_rating = '⭐⭐'
            recommendation = '持有'
        elif total_score >= 40:
            rating = '偏弱'
            vp_rating = '⭐'
            recommendation = '减持'
        else:
            rating = '弱势'
            vp_rating = ''
            recommendation = '卖出'
        
        return {
            'total_score': round(total_score, 1),
            'rating': rating,
            'vp_rating': vp_rating,
            'recommendation': recommendation,
            'volume_price': volume_price,
            'volume_trend': volume_trend,
            'volume_breakout': volume_breakout,
            'volume_divergence': volume_divergence,
            'volume_accumulation': volume_accumulation,
            'analysis_time': datetime.now().isoformat(),
        }
    
    def get_decision_bonus(self, analysis_result: dict) -> float:
        """
        根据量价分析结果计算决策加分
        
        Args:
            analysis_result: 分析结果
        
        Returns:
            float: 决策加分 (0-0.3)
        """
        total_score = analysis_result.get('total_score', 0)
        
        if total_score >= 80:
            return 0.30  # 非常健康
        elif total_score >= 70:
            return 0.25  # 健康
        elif total_score >= 60:
            return 0.20  # 良好
        elif total_score >= 50:
            return 0.10  # 中性
        elif total_score >= 40:
            return 0.05  # 偏弱
        else:
            return 0.00  # 弱势


def analyze_volume_price(stock_data: dict) -> dict:
    """
    量价分析 (快捷函数)
    
    Args:
        stock_data: 股票数据
    
    Returns:
        dict: 分析结果
    """
    strategy = VolumePriceAnalysis()
    return strategy.analyze_company(stock_data)


# ============ 主函数 ============

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='量价分析策略')
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
            'volume': 5000000,
            'amount': 250000000,
        }
        
        strategy = VolumePriceAnalysis()
        result = strategy.analyze_company(test_data)
        
        print(f"\n{'='*80}")
        print(f"📊 {args.stock} 量价分析报告")
        print(f"{'='*80}")
        print(f"\n综合评分：{result['total_score']}/100")
        print(f"量价评级：{result['vp_rating']} {result['rating']}")
        print(f"投资建议：{result['recommendation']}")
        print(f"\n各维度分析:")
        print(f"  量价关系：{result['volume_price']['description']}")
        print(f"  成交量趋势：{result['volume_trend']['description']}")
        print(f"  突破信号：{result['volume_breakout']['description']}")
        print(f"  量价背离：{result['volume_divergence']['description']}")
        print(f"  资金累积：{result['volume_accumulation']['description']}")
        print(f"\n决策加分：{strategy.get_decision_bonus(result):.2f}")
        print(f"{'='*80}\n")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
