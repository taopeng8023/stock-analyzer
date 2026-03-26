"""
基本面分析模块
分析财务数据和估值水平
"""

import pandas as pd


class FundamentalAnalyzer:
    """基本面分析器"""
    
    def __init__(self):
        pass
    
    def analyze_roe(self, roe: float) -> dict:
        """ROE 分析"""
        if roe >= 20:
            return {'score': 100, 'level': '优秀', 'comment': 'ROE 非常优秀'}
        elif roe >= 15:
            return {'score': 80, 'level': '良好', 'comment': 'ROE 良好'}
        elif roe >= 10:
            return {'score': 60, 'level': '一般', 'comment': 'ROE 一般'}
        elif roe >= 5:
            return {'score': 40, 'level': '较差', 'comment': 'ROE 较低'}
        else:
            return {'score': 20, 'level': '差', 'comment': 'ROE 很差'}
    
    def analyze_growth(self, revenue_growth: float, profit_growth: float) -> dict:
        """成长性分析"""
        avg_growth = (revenue_growth + profit_growth) / 2
        
        if avg_growth >= 30:
            return {'score': 100, 'level': '高成长', 'comment': '高速成长期'}
        elif avg_growth >= 20:
            return {'score': 80, 'level': '成长', 'comment': '稳定成长'}
        elif avg_growth >= 10:
            return {'score': 60, 'level': '稳健', 'comment': '稳健增长'}
        elif avg_growth >= 0:
            return {'score': 40, 'level': '停滞', 'comment': '增长停滞'}
        else:
            return {'score': 20, 'level': '衰退', 'comment': '业绩下滑'}
    
    def analyze_debt(self, debt_ratio: float) -> dict:
        """负债率分析"""
        if debt_ratio <= 30:
            return {'score': 100, 'level': '很低', 'comment': '财务非常安全'}
        elif debt_ratio <= 50:
            return {'score': 80, 'level': '合理', 'comment': '负债合理'}
        elif debt_ratio <= 60:
            return {'score': 60, 'level': '偏高', 'comment': '负债偏高'}
        elif debt_ratio <= 70:
            return {'score': 40, 'level': '高', 'comment': '负债较高'}
        else:
            return {'score': 20, 'level': '很高', 'comment': '财务风险高'}
    
    def analyze_pe(self, pe: float, industry_pe: float = 0) -> dict:
        """市盈率分析"""
        if pe <= 0:
            return {'score': 30, 'level': '亏损', 'comment': '公司亏损'}
        elif pe <= 15:
            return {'score': 90, 'level': '低估', 'comment': '估值较低'}
        elif pe <= 25:
            return {'score': 70, 'level': '合理', 'comment': '估值合理'}
        elif pe <= 40:
            return {'score': 50, 'level': '偏高', 'comment': '估值偏高'}
        else:
            return {'score': 30, 'level': '高估', 'comment': '估值过高'}
    
    def analyze_pb(self, pb: float) -> dict:
        """市净率分析"""
        if pb <= 1:
            return {'score': 90, 'level': '很低', 'comment': '破净或接近破净'}
        elif pb <= 2:
            return {'score': 70, 'level': '合理', 'comment': '市净率合理'}
        elif pb <= 4:
            return {'score': 50, 'level': '偏高', 'comment': '市净率偏高'}
        else:
            return {'score': 30, 'level': '很高', 'comment': '市净率过高'}
    
    def get_fundamental_score(self, financial_data: dict, market_data: dict = None) -> dict:
        """综合基本面评分"""
        if not financial_data:
            return {'score': 50, 'signals': ['财务数据不足']}
        
        score = 50
        signals = []
        
        # ROE 分析
        roe = financial_data.get('roe', 0)
        roe_result = self.analyze_roe(roe)
        score += (roe_result['score'] - 50) * 0.3
        signals.append(f"{'✓' if roe_result['score'] >= 70 else '✗'} ROE: {roe:.1f}% ({roe_result['level']})")
        
        # 成长性分析
        revenue_growth = financial_data.get('revenue_growth', 0)
        profit_growth = financial_data.get('profit_growth', 0)
        growth_result = self.analyze_growth(revenue_growth, profit_growth)
        score += (growth_result['score'] - 50) * 0.3
        signals.append(f"{'✓' if growth_result['score'] >= 70 else '✗'} 成长性：营收{revenue_growth:.1f}%, 净利{profit_growth:.1f}%")
        
        # 负债率分析
        debt_ratio = financial_data.get('debt_ratio', 0)
        debt_result = self.analyze_debt(debt_ratio)
        score += (debt_result['score'] - 50) * 0.2
        signals.append(f"{'✓' if debt_result['score'] >= 70 else '✗'} 负债率：{debt_ratio:.1f}% ({debt_result['level']})")
        
        # 估值分析
        if market_data:
            pe = market_data.get('pe_ttm', 0)
            pb = market_data.get('pb', 0)
            
            pe_result = self.analyze_pe(pe)
            score += (pe_result['score'] - 50) * 0.15
            signals.append(f"{'✓' if pe_result['score'] >= 70 else '✗'} PE(TTM): {pe:.1f} ({pe_result['level']})")
            
            pb_result = self.analyze_pb(pb)
            score += (pb_result['score'] - 50) * 0.05
            signals.append(f"~ PB: {pb:.1f} ({pb_result['level']})")
        
        # 限制分数范围
        score = max(0, min(100, score))
        
        return {
            'score': score,
            'signals': signals,
            'details': {
                'roe': roe_result,
                'growth': growth_result,
                'debt': debt_result,
            }
        }


# 测试用
if __name__ == "__main__":
    analyzer = FundamentalAnalyzer()
    
    # 测试数据
    financial = {
        'roe': 18.5,
        'revenue_growth': 15.2,
        'profit_growth': 22.3,
        'debt_ratio': 45.6,
        'gross_margin': 35.2,
        'net_margin': 12.8,
    }
    
    market = {
        'pe_ttm': 25.5,
        'pb': 3.2,
    }
    
    result = analyzer.get_fundamental_score(financial, market)
    print(f"基本面评分：{result['score']}")
    for signal in result['signals']:
        print(signal)
