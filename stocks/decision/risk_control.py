#!/usr/bin/env python3
"""
风险控制模块 - v1.0

功能:
- ST 股票过滤
- 高位股风险提示
- 流动性风险评估
- 估值风险评估
- 涨跌幅异常检测

用法:
    from decision.risk_control import RiskControlModule
    
    risk = RiskControlModule()
    result = risk.check(stock_data)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime


@dataclass
class RiskCheckResult:
    """风险检查结果"""
    passed: bool                    # 是否通过
    risk_level: str                 # 风险等级：low/medium/high
    risk_score: int                 # 风险评分（0-100）
    risk_factors: List[str]         # 风险因素列表
    suggestions: List[str]          # 建议
    check_time: str                 # 检查时间


class RiskControlModule:
    """风险控制模块"""
    
    # 风险阈值配置
    THRESHOLDS = {
        'high_position_pct': 50,      # 高位股阈值（年内涨幅>50%）
        'low_turnover': 100000000,    # 低流动性阈值（1 亿）
        'high_pe': 100,               # 高估值阈值
        'abnormal_change_pct': 20,    # 涨跌幅异常阈值
    }
    
    def check(self, stock: Dict, fundamental_data: Optional[Dict] = None) -> RiskCheckResult:
        """
        风险控制检查
        
        Args:
            stock: 股票数据（包含 code, name, change_pct, turnover 等）
            fundamental_data: 基本面数据（可选，包含 pe_ratio 等）
        
        Returns:
            RiskCheckResult: 风险检查结果
        """
        risk_factors = []
        risk_score = 0
        
        # 1. ST 股票检查
        is_st, score = self._check_st(stock)
        if is_st:
            risk_factors.append('ST 股票')
            risk_score += score
        
        # 2. 高位股检查
        is_high_position, score = self._check_high_position(stock)
        if is_high_position:
            risk_factors.append('高位股')
            risk_score += score
        
        # 3. 流动性检查
        is_low_liquidity, score = self._check_liquidity(stock)
        if is_low_liquidity:
            risk_factors.append('流动性差')
            risk_score += score
        
        # 4. 估值检查
        if fundamental_data:
            is_high_valuation, score = self._check_valuation(fundamental_data)
            if is_high_valuation:
                risk_factors.append('高估值')
                risk_score += score
            
            is_loss, score = self._check_loss(fundamental_data)
            if is_loss:
                risk_factors.append('亏损股')
                risk_score += score
        
        # 5. 涨跌幅异常检查
        is_abnormal, score = self._check_abnormal_change(stock)
        if is_abnormal:
            risk_factors.append('涨跌幅异常')
            risk_score += score
        
        # 确定风险等级
        risk_level, passed, suggestions = self._determine_risk_level(risk_score, risk_factors)
        
        return RiskCheckResult(
            passed=passed,
            risk_level=risk_level,
            risk_score=risk_score,
            risk_factors=risk_factors,
            suggestions=suggestions,
            check_time=datetime.now().isoformat()
        )
    
    def _check_st(self, stock: Dict) -> Tuple[bool, int]:
        """检查 ST 股票"""
        name = stock.get('name', '')
        if 'ST' in name or '*' in name:
            return True, 30
        return False, 0
    
    def _check_high_position(self, stock: Dict) -> Tuple[bool, int]:
        """检查高位股（年内涨幅）"""
        change_pct = stock.get('change_pct', 0)
        
        # 如果 change_pct 是年内涨幅
        if change_pct > self.THRESHOLDS['high_position_pct']:
            return True, 20
        
        # 如果是当日涨幅，检查是否连续大涨
        if change_pct > 15:  # 当日涨幅>15%
            return True, 15
        
        return False, 0
    
    def _check_liquidity(self, stock: Dict) -> Tuple[bool, int]:
        """检查流动性"""
        turnover = stock.get('turnover', 0)  # 成交额（元）
        
        if turnover < self.THRESHOLDS['low_turnover']:
            return True, 20
        
        return False, 0
    
    def _check_valuation(self, fundamental_data: Dict) -> Tuple[bool, int]:
        """检查估值"""
        pe_ratio = fundamental_data.get('pe_ratio', 0)
        pb_ratio = fundamental_data.get('pb_ratio', 0)
        
        # PE 过高
        if pe_ratio > self.THRESHOLDS['high_pe']:
            return True, 15
        
        # PB 过高
        if pb_ratio > 10:
            return True, 10
        
        return False, 0
    
    def _check_loss(self, fundamental_data: Dict) -> Tuple[bool, int]:
        """检查亏损"""
        pe_ratio = fundamental_data.get('pe_ratio', 0)
        roe = fundamental_data.get('roe', 0)
        
        # PE 为负（亏损）
        if pe_ratio < 0:
            return True, 20
        
        # ROE 为负
        if roe < 0:
            return True, 15
        
        return False, 0
    
    def _check_abnormal_change(self, stock: Dict) -> Tuple[bool, int]:
        """检查涨跌幅异常"""
        change_pct = abs(stock.get('change_pct', 0))
        
        if change_pct > self.THRESHOLDS['abnormal_change_pct']:
            return True, 15
        
        return False, 0
    
    def _determine_risk_level(self, risk_score: int, risk_factors: List[str]) -> Tuple[str, bool, List[str]]:
        """
        确定风险等级
        
        Returns:
            (risk_level, passed, suggestions)
        """
        if risk_score >= 50:
            return 'high', False, ['避免参与']
        elif risk_score >= 30:
            return 'medium', True, ['轻仓参与', '设置严格止损']
        else:
            return 'low', True, ['正常参与']
    
    def get_risk_summary(self, stocks: List[Dict]) -> Dict:
        """
        获取批量股票的风险汇总
        
        Args:
            stocks: 股票列表
        
        Returns:
            Dict: 风险汇总统计
        """
        total = len(stocks)
        high_risk = 0
        medium_risk = 0
        low_risk = 0
        passed = 0
        
        for stock in stocks:
            result = self.check(stock)
            
            if result.risk_level == 'high':
                high_risk += 1
            elif result.risk_level == 'medium':
                medium_risk += 1
            else:
                low_risk += 1
            
            if result.passed:
                passed += 1
        
        return {
            'total': total,
            'high_risk': high_risk,
            'medium_risk': medium_risk,
            'low_risk': low_risk,
            'passed': passed,
            'pass_rate': passed / total * 100 if total > 0 else 0
        }


# 测试
if __name__ == '__main__':
    risk = RiskControlModule()
    
    # 测试数据
    test_stocks = [
        {
            'code': '600519',
            'name': '贵州茅台',
            'change_pct': 2.5,
            'turnover': 5000000000,
        },
        {
            'code': '000001',
            'name': '*ST 平安',
            'change_pct': -5.0,
            'turnover': 100000000,
        },
        {
            'code': '300750',
            'name': '宁德时代',
            'change_pct': 55.0,  # 高位股
            'turnover': 3000000000,
        },
    ]
    
    print("="*80)
    print("🛡️ 风险控制模块测试")
    print("="*80)
    
    for stock in test_stocks:
        result = risk.check(stock)
        print(f"\n{stock['code']} {stock['name']}:")
        print(f"  风险等级：{result.risk_level}")
        print(f"  风险评分：{result.risk_score}")
        print(f"  通过：{result.passed}")
        if result.risk_factors:
            print(f"  风险因素：{', '.join(result.risk_factors)}")
        print(f"  建议：{', '.join(result.suggestions)}")
    
    # 汇总统计
    print("\n" + "="*80)
    print("📊 风险汇总")
    print("="*80)
    summary = risk.get_risk_summary(test_stocks)
    print(f"总股票数：{summary['total']}")
    print(f"高风险：{summary['high_risk']}")
    print(f"中风险：{summary['medium_risk']}")
    print(f"低风险：{summary['low_risk']}")
    print(f"通过率：{summary['pass_rate']:.1f}%")
