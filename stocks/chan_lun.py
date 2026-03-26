#!/usr/bin/env python3
"""
缠论分析模块
基于《缠中说禅》A 股技术分析体系

核心理论:
1. 分型 (顶分型/底分型)
2. 笔 (上升笔/下降笔)
3. 线段 (上升线段/下降线段)
4. 中枢 (价格震荡区间)
5. 背驰 (趋势力度衰减)
6. 买卖点 (三类买卖点)

用法:
    python3 chan_lun.py --stock sh600000
    python3 chan_lun.py --analyze all
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

sys.path.insert(0, str(Path(__file__).parent))


class ChanLunAnalysis:
    """
    缠论分析
    
    基于缠中说禅的 A 股技术分析体系
    """
    
    def __init__(self):
        pass
    
    def analyze_fenxing(self, stock_data: dict) -> dict:
        """
        分型分析
        
        顶分型：三根 K 线，中间最高
        底分型：三根 K 线，中间最低
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        price = stock_data.get('price', 0)
        
        # 简化版分型判断
        if change_pct > 5:
            fenxing = '顶分型形成中'
            signal = '警惕回调'
            score = 40
        elif change_pct > 2:
            fenxing = '上升 K 线'
            signal = '延续上涨'
            score = 65
        elif change_pct > -2:
            fenxing = '整理 K 线'
            signal = '观望'
            score = 50
        elif change_pct > -5:
            fenxing = '下降 K 线'
            signal = '延续下跌'
            score = 35
        else:
            fenxing = '底分型形成中'
            signal = '关注反弹'
            score = 60
        
        return {
            'fenxing': fenxing,
            'signal': signal,
            'score': score,
            'description': f'分型状态：{fenxing} - {signal}',
        }
    
    def analyze_bi(self, stock_data: dict) -> dict:
        """
        笔分析
        
        上升笔：从底分型到顶分型
        下降笔：从顶分型到底分型
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        amount = stock_data.get('amount', 0)
        
        # 简化版笔判断
        if change_pct > 7 and amount > 5000000000:
            bi_type = '强势上升笔'
            status = '延续中'
            score = 85
        elif change_pct > 3:
            bi_type = '上升笔'
            status = '延续中'
            score = 70
        elif change_pct > -3:
            bi_type = '整理笔'
            status = '震荡中'
            score = 50
        elif change_pct > -7:
            bi_type = '下降笔'
            status = '延续中'
            score = 30
        else:
            bi_type = '强势下降笔'
            status = '延续中'
            score = 15
        
        return {
            'bi_type': bi_type,
            'status': status,
            'score': score,
            'description': f'笔状态：{bi_type} ({status})',
        }
    
    def analyze_xianduan(self, stock_data: dict) -> dict:
        """
        线段分析
        
        上升线段：连续上升笔
        下降线段：连续下降笔
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        amount = stock_data.get('amount', 0)
        
        # 简化版线段判断
        if change_pct > 10 and amount > 10000000000:
            xianduan = '强势上升线段'
            direction = '向上'
            score = 90
        elif change_pct > 5 and amount > 5000000000:
            xianduan = '上升线段'
            direction = '向上'
            score = 75
        elif change_pct > -5:
            xianduan = '整理线段'
            direction = '水平'
            score = 50
        elif change_pct > -10:
            xianduan = '下降线段'
            direction = '向下'
            score = 25
        else:
            xianduan = '强势下降线段'
            direction = '向下'
            score = 10
        
        return {
            'xianduan': xianduan,
            'direction': direction,
            'score': score,
            'description': f'线段状态：{xianduan} ({direction})',
        }
    
    def analyze_zhongshu(self, stock_data: dict) -> dict:
        """
        中枢分析
        
        中枢：至少三段重叠的价格区间
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        price = stock_data.get('price', 0)
        change_pct = stock_data.get('change_pct', 0)
        amount = stock_data.get('amount', 0)
        
        # 简化版中枢判断
        if abs(change_pct) < 3 and amount > 2000000000:
            zhongshu = '中枢形成中'
            position = '中枢内'
            score = 55
        elif change_pct > 5:
            zhongshu = '离开中枢'
            position = '中枢上方'
            score = 75
        elif change_pct > 0:
            zhongshu = '接近中枢上沿'
            position = '中枢上方'
            score = 60
        elif change_pct < -5:
            zhongshu = '跌破中枢'
            position = '中枢下方'
            score = 25
        else:
            zhongshu = '接近中枢下沿'
            position = '中枢下方'
            score = 40
        
        return {
            'zhongshu': zhongshu,
            'position': position,
            'score': score,
            'description': f'中枢状态：{zhongshu} ({position})',
        }
    
    def analyze_beichi(self, stock_data: dict) -> dict:
        """
        背驰分析
        
        背驰：趋势力度衰减，反转信号
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        volume = stock_data.get('volume', 0)
        
        # 简化版背驰判断
        if change_pct > 7 and volume < 2000000:
            beichi = '顶背驰'
            signal = '看跌'
            score = 30
            warning = '价格上涨但成交量不足，警惕顶背驰'
        elif change_pct < -7 and volume < 2000000:
            beichi = '底背驰'
            signal = '看涨'
            score = 70
            warning = '价格下跌但成交量萎缩，可能底背驰'
        elif change_pct > 3 and volume > 5000000:
            beichi = '无背驰'
            signal = '健康'
            score = 80
            warning = '量价配合良好，无背驰'
        else:
            beichi = '无明显背驰'
            signal = '中性'
            score = 50
            warning = '无明显背驰信号'
        
        return {
            'beichi': beichi,
            'signal': signal,
            'score': score,
            'warning': warning,
            'description': f'背驰状态：{beichi} - {signal}',
        }
    
    def analyze_maidian(self, stock_data: dict) -> dict:
        """
        买卖点分析
        
        第一类买卖点：趋势背驰点
        第二类买卖点：第一次回抽/反弹
        第三类买卖点：中枢突破后回踩
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        price = stock_data.get('price', 0)
        
        # 简化版买卖点判断
        if change_pct < -10:
            maidian = '第一类买点附近'
            action = '关注买入'
            score = 75
        elif change_pct < -5:
            maidian = '潜在买点'
            action = '观望'
            score = 55
        elif change_pct > 10:
            maidian = '第一类卖点附近'
            action = '关注卖出'
            score = 30
        elif change_pct > 5:
            maidian = '潜在卖点'
            action = '减仓'
            score = 40
        else:
            maidian = '无明确买卖点'
            action = '持有/观望'
            score = 50
        
        return {
            'maidian': maidian,
            'action': action,
            'score': score,
            'description': f'买卖点：{maidian} - {action}',
        }
    
    def analyze_company(self, stock_data: dict) -> dict:
        """
        缠论综合分析
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 综合分析结果
        """
        # 分析各维度
        fenxing = self.analyze_fenxing(stock_data)
        bi = self.analyze_bi(stock_data)
        xianduan = self.analyze_xianduan(stock_data)
        zhongshu = self.analyze_zhongshu(stock_data)
        beichi = self.analyze_beichi(stock_data)
        maidian = self.analyze_maidian(stock_data)
        
        # 综合评分
        total_score = (
            fenxing['score'] * 0.15 +
            bi['score'] * 0.20 +
            xianduan['score'] * 0.20 +
            zhongshu['score'] * 0.15 +
            beichi['score'] * 0.15 +
            maidian['score'] * 0.15
        )
        
        # 缠论评级
        if total_score >= 80:
            rating = '强烈看多'
            chan_rating = '⭐⭐⭐⭐⭐'
            recommendation = '买入'
        elif total_score >= 70:
            rating = '看多'
            chan_rating = '⭐⭐⭐⭐'
            recommendation = '增持'
        elif total_score >= 60:
            rating = '偏多'
            chan_rating = '⭐⭐⭐'
            recommendation = '持有'
        elif total_score >= 50:
            rating = '中性'
            chan_rating = '⭐⭐'
            recommendation = '观望'
        elif total_score >= 40:
            rating = '偏空'
            chan_rating = '⭐'
            recommendation = '减仓'
        else:
            rating = '看空'
            chan_rating = ''
            recommendation = '卖出'
        
        return {
            'total_score': round(total_score, 1),
            'rating': rating,
            'chan_rating': chan_rating,
            'recommendation': recommendation,
            'fenxing': fenxing,
            'bi': bi,
            'xianduan': xianduan,
            'zhongshu': zhongshu,
            'beichi': beichi,
            'maidian': maidian,
            'analysis_time': datetime.now().isoformat(),
        }
    
    def get_decision_bonus(self, analysis_result: dict) -> float:
        """
        根据缠论分析结果计算决策加分
        
        Args:
            analysis_result: 分析结果
        
        Returns:
            float: 决策加分 (0-0.3)
        """
        total_score = analysis_result.get('total_score', 0)
        
        if total_score >= 80:
            return 0.30  # 强烈看多
        elif total_score >= 70:
            return 0.25  # 看多
        elif total_score >= 60:
            return 0.20  # 偏多
        elif total_score >= 50:
            return 0.10  # 中性
        elif total_score >= 40:
            return 0.05  # 偏空
        else:
            return 0.00  # 看空


def analyze_chan_lun(stock_data: dict) -> dict:
    """
    缠论分析 (快捷函数)
    
    Args:
        stock_data: 股票数据
    
    Returns:
        dict: 分析结果
    """
    strategy = ChanLunAnalysis()
    return strategy.analyze_company(stock_data)


# ============ 主函数 ============

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='缠论分析策略')
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
        
        strategy = ChanLunAnalysis()
        result = strategy.analyze_company(test_data)
        
        print(f"\n{'='*80}")
        print(f"📚 {args.stock} 缠论分析报告")
        print(f"{'='*80}")
        print(f"\n综合评分：{result['total_score']}/100")
        print(f"缠论评级：{result['chan_rating']} {result['rating']}")
        print(f"操作建议：{result['recommendation']}")
        print(f"\n各维度分析:")
        print(f"  分型：{result['fenxing']['description']}")
        print(f"  笔：{result['bi']['description']}")
        print(f"  线段：{result['xianduan']['description']}")
        print(f"  中枢：{result['zhongshu']['description']}")
        print(f"  背驰：{result['beichi']['description']}")
        print(f"  买卖点：{result['maidian']['description']}")
        print(f"\n决策加分：{strategy.get_decision_bonus(result):.2f}")
        print(f"{'='*80}\n")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
