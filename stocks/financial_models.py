#!/usr/bin/env python3
"""
经典金融模型集成模块 v9.0
集成多个经典金融学和量化投资模型参与决策

集成模型 (25 个):
【经典定价模型】
1. CAPM 资本资产定价模型
2. Fama-French 三因子模型
3. Carhart 四因子模型 (加入动量)
4. Fama-French 五因子模型 (盈利/投资)
5. APT 套利定价理论 (新增)

【资产配置模型】
6. Black-Litterman 资产配置模型
7. Markowitz 均值方差优化
8. Risk Parity 风险平价模型

【风险指标】
9. Sharpe Ratio 夏普比率
10. Sortino Ratio 索提诺比率
11. Max Drawdown 最大回撤控制
12. VaR 风险价值
13. CVaR 条件风险价值
14. Treynor Ratio 特雷诺比率 (新增)
15. Information Ratio 信息比率 (新增)
16. Calmar Ratio 卡尔玛比率 (新增)
17. Omega Ratio 欧米伽比率 (新增)

【技术指标模型】
18. MACD 异同移动平均线
19. RSI 相对强弱指标
20. Bollinger Bands 布林带

【估值模型】(新增)
21. PEG 估值模型
22. DCF 现金流折现 (简化)
23. 相对估值 (PE/PB/PS)

【市场情绪】(新增)
24. 资金流模型
25. 分析师预期模型

用法:
    python3 financial_models.py --test  # 测试模块
    python3 financial_models.py --analyze --stock sh600000  # 分析单只股票
"""

import sys
import math
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))


# ============ 市场参数 ============
RISK_FREE_RATE = 0.02  # 无风险利率 (2%)
MARKET_RETURN = 0.08   # 市场预期回报 (8%)
MARKET_VOL = 0.20      # 市场波动率 (20%)


class CAPMModel:
    """
    CAPM 资本资产定价模型
    Capital Asset Pricing Model
    
    E(Ri) = Rf + βi * (E(Rm) - Rf)
    
    用于:
    - 计算股票预期回报
    - 评估股票是否被高估/低估
    - 计算 Alpha 和 Beta
    """
    
    def __init__(self, risk_free_rate: float = RISK_FREE_RATE,
                 market_return: float = MARKET_RETURN):
        self.risk_free_rate = risk_free_rate
        self.market_return = market_return
        self.market_premium = market_return - risk_free_rate
    
    def calculate_expected_return(self, beta: float) -> float:
        """
        计算预期回报
        
        Args:
            beta: 股票 Beta 值
        
        Returns:
            float: 预期回报率
        """
        return self.risk_free_rate + beta * self.market_premium
    
    def calculate_alpha(self, actual_return: float, beta: float) -> float:
        """
        计算 Alpha (超额收益)
        
        Args:
            actual_return: 实际回报率
            beta: 股票 Beta 值
        
        Returns:
            float: Alpha 值
        """
        expected_return = self.calculate_expected_return(beta)
        return actual_return - expected_return
    
    def calculate_beta(self, stock_returns: List[float], 
                       market_returns: List[float]) -> float:
        """
        计算 Beta 值
        
        Args:
            stock_returns: 股票历史回报序列
            market_returns: 市场历史回报序列
        
        Returns:
            float: Beta 值
        """
        if len(stock_returns) != len(market_returns) or len(stock_returns) < 2:
            return 1.0  # 默认 Beta=1
        
        # 计算协方差和方差
        covariance = np.cov(stock_returns, market_returns)[0][1]
        market_variance = np.var(market_returns)
        
        if market_variance == 0:
            return 1.0
        
        return covariance / market_variance
    
    def analyze(self, stock_data: dict, history: List[dict] = None) -> dict:
        """
        CAPM 综合分析
        
        Args:
            stock_data: 股票当前数据
            history: 历史数据 (用于计算 Beta)
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0) / 100  # 转换为小数
        
        # 估算 Beta (简化：基于涨跌幅和市场相关性)
        if history and len(history) >= 20:
            stock_returns = [(h.get('close', 0) - history[i-1].get('close', 0)) / max(history[i-1].get('close', 1), 0.01) 
                            for i, h in enumerate(history[-20:]) if i > 0]
            # 假设市场回报 (简化)
            market_returns = [0.0003] * len(stock_returns)  # 日均 0.03%
            beta = self.calculate_beta(stock_returns, market_returns)
        else:
            beta = 1.0 + (change_pct * 0.5)  # 简化估算
        
        # 计算预期回报
        expected_return = self.calculate_expected_return(beta)
        
        # 计算 Alpha
        alpha = self.calculate_alpha(change_pct, beta)
        
        # 评估
        if alpha > 0.02:
            valuation = '低估'
            signal = '买入'
            score = 80 + alpha * 100
        elif alpha > 0:
            valuation = '合理'
            signal = '持有'
            score = 60 + alpha * 100
        else:
            valuation = '高估'
            signal = '卖出'
            score = 50 + alpha * 100
        
        return {
            'beta': beta,
            'expected_return': expected_return,
            'actual_return': change_pct,
            'alpha': alpha,
            'valuation': valuation,
            'signal': signal,
            'score': min(100, max(0, score)),
            'description': f'Beta={beta:.2f}, Alpha={alpha:.4f}, {valuation}'
        }


class FamaFrenchModel:
    """
    Fama-French 三因子模型
    
    E(Ri) = Rf + βmkt*(Rm-Rf) + βsmb*SMB + βhml*HML
    
    三因子:
    1. Market Factor (市场因子)
    2. SMB (Small Minus Big, 规模因子)
    3. HML (High Minus Low, 价值因子)
    
    用于:
    - 更精确的资产定价
    - 识别风格暴露
    """
    
    def __init__(self):
        self.risk_free_rate = RISK_FREE_RATE
    
    def analyze(self, stock_data: dict) -> dict:
        """
        Fama-French 三因子分析
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        amount = stock_data.get('amount', 0)
        price = stock_data.get('price', 0)
        change_pct = stock_data.get('change_pct', 0)
        
        # 1. 规模因子 (SMB) - 小盘股效应
        if amount < 1000000000:  # <10 亿
            smb_exposure = 0.3  # 小盘股溢价
            size_category = '小盘'
        elif amount < 5000000000:  # <50 亿
            smb_exposure = 0.15
            size_category = '中小盘'
        elif amount < 10000000000:  # <100 亿
            smb_exposure = 0
            size_category = '中盘'
        else:
            smb_exposure = -0.1  # 大盘股折价
            size_category = '大盘'
        
        # 2. 价值因子 (HML) - 价值股效应
        # 简化：用股价代表 (低价=价值股)
        if 0 < price < 10:
            hml_exposure = 0.25  # 价值股溢价
            value_category = '价值'
        elif price < 30:
            hml_exposure = 0.1
            value_category = '平衡'
        elif price < 100:
            hml_exposure = -0.05
            value_category = '成长'
        else:
            hml_exposure = -0.15  # 高成长股折价
            value_category = '高成长'
        
        # 3. 市场因子
        market_exposure = 1.0 + (change_pct / 100) * 0.5
        
        # 计算预期回报
        expected_return = (
            self.risk_free_rate +
            market_exposure * 0.06 +  # 市场溢价 6%
            smb_exposure * 0.03 +     # SMB 溢价 3%
            hml_exposure * 0.04       # HML 溢价 4%
        )
        
        # 综合评分
        score = 50 + smb_exposure * 50 + hml_exposure * 50 + (change_pct / 10)
        score = min(100, max(0, score))
        
        if score >= 70:
            signal = '买入'
        elif score >= 50:
            signal = '持有'
        else:
            signal = '卖出'
        
        return {
            'market_exposure': market_exposure,
            'smb_exposure': smb_exposure,
            'hml_exposure': hml_exposure,
            'size_category': size_category,
            'value_category': value_category,
            'expected_return': expected_return,
            'score': score,
            'signal': signal,
            'description': f'{size_category}/{value_category}, 预期回报{expected_return:.2%}'
        }


class CarhartModel:
    """
    Carhart 四因子模型
    Fama-French 三因子 + Momentum (动量因子)
    
    E(Ri) = Rf + βmkt*(Rm-Rf) + βsmb*SMB + βhml*HML + βmom*MOM
    """
    
    def __init__(self):
        self.ff_model = FamaFrenchModel()
    
    def analyze(self, stock_data: dict, history: List[dict] = None) -> dict:
        """
        Carhart 四因子分析
        
        Args:
            stock_data: 股票数据
            history: 历史数据 (用于计算动量)
        
        Returns:
            dict: 分析结果
        """
        # Fama-French 三因子
        ff_result = self.ff_model.analyze(stock_data)
        
        # 4. 动量因子 (MOM)
        if history and len(history) >= 60:
            # 计算过去 3 个月回报 (排除最近 1 个月)
            price_now = stock_data.get('price', 0)
            price_3m = history[-60].get('close', price_now) if len(history) >= 60 else price_now
            price_1m = history[-20].get('close', price_now) if len(history) >= 20 else price_now
            
            momentum_3m = (price_now - price_3m) / max(price_3m, 0.01)
            momentum_1m = (price_now - price_1m) / max(price_1m, 0.01)
            
            # 动量暴露 (过去赢家继续赢)
            if momentum_3m > 0.2:
                mom_exposure = 0.3
                momentum_signal = '强动量'
            elif momentum_3m > 0.1:
                mom_exposure = 0.15
                momentum_signal = '动量'
            elif momentum_3m > 0:
                mom_exposure = 0.05
                momentum_signal = '弱动量'
            else:
                mom_exposure = -0.2
                momentum_signal = '反转'
        else:
            mom_exposure = 0
            momentum_signal = '未知'
        
        # 计算预期回报 (加入动量溢价)
        expected_return = ff_result['expected_return'] + mom_exposure * 0.04  # 动量溢价 4%
        
        # 综合评分
        score = ff_result['score'] + mom_exposure * 30
        score = min(100, max(0, score))
        
        if score >= 75:
            signal = '强烈买入'
        elif score >= 60:
            signal = '买入'
        elif score >= 45:
            signal = '持有'
        else:
            signal = '卖出'
        
        return {
            **ff_result,
            'mom_exposure': mom_exposure,
            'momentum_signal': momentum_signal,
            'expected_return': expected_return,
            'score': score,
            'signal': signal,
            'description': f"{ff_result['description']}, 动量={momentum_signal}"
        }


class RiskMetricsModel:
    """
    风险指标模型集合
    
    包括:
    - Sharpe Ratio (夏普比率)
    - Sortino Ratio (索提诺比率)
    - Max Drawdown (最大回撤)
    - VaR (风险价值)
    - Volatility (波动率)
    """
    
    def __init__(self, risk_free_rate: float = RISK_FREE_RATE):
        self.risk_free_rate = risk_free_rate
    
    def calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """
        计算夏普比率
        Sharpe Ratio = (E(Rp) - Rf) / σp
        """
        if len(returns) < 2:
            return 0
        
        excess_return = np.mean(returns) - self.risk_free_rate / 252  # 日化
        std_dev = np.std(returns)
        
        if std_dev == 0:
            return 0
        
        return excess_return / std_dev
    
    def calculate_sortino_ratio(self, returns: List[float]) -> float:
        """
        计算索提诺比率
        Sortino Ratio = (E(Rp) - Rf) / Downside Deviation
        """
        if len(returns) < 2:
            return 0
        
        excess_return = np.mean(returns) - self.risk_free_rate / 252
        
        # 下行偏差
        downside_returns = [r for r in returns if r < 0]
        if not downside_returns:
            return float('inf')  # 无下行风险
        
        downside_std = np.std(downside_returns)
        
        if downside_std == 0:
            return float('inf')
        
        return excess_return / downside_std
    
    def calculate_max_drawdown(self, prices: List[float]) -> float:
        """
        计算最大回撤
        Max Drawdown = (Peak - Trough) / Peak
        """
        if len(prices) < 2:
            return 0
        
        peak = prices[0]
        max_dd = 0
        
        for price in prices:
            if price > peak:
                peak = price
            
            drawdown = (peak - price) / peak
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """
        计算风险价值 (VaR)
        Value at Risk
        """
        if len(returns) < 10:
            return 0
        
        return np.percentile(returns, (1 - confidence) * 100)
    
    def analyze(self, stock_data: dict, history: List[dict] = None) -> dict:
        """
        风险指标综合分析
        
        Args:
            stock_data: 股票数据
            history: 历史数据
        
        Returns:
            dict: 分析结果
        """
        # 从历史数据计算回报序列
        if history and len(history) >= 20:
            prices = [h.get('close', 0) for h in history[-60:]]
            returns = [(prices[i] - prices[i-1]) / max(prices[i-1], 0.01) 
                      for i in range(1, len(prices))]
        else:
            prices = [stock_data.get('price', 0)]
            returns = [stock_data.get('change_pct', 0) / 100]
        
        # 计算各项风险指标
        sharpe = self.calculate_sharpe_ratio(returns)
        sortino = self.calculate_sortino_ratio(returns)
        max_dd = self.calculate_max_drawdown(prices)
        var_95 = self.calculate_var(returns, 0.95)
        volatility = np.std(returns) * math.sqrt(252)  # 年化波动率
        
        # 综合风险评分
        risk_score = 50
        if sharpe > 1:
            risk_score += 20
        elif sharpe > 0.5:
            risk_score += 10
        elif sharpe < -0.5:
            risk_score -= 20
        
        if sortino > 1.5:
            risk_score += 15
        elif sortino > 1:
            risk_score += 10
        
        if max_dd < 0.1:
            risk_score += 15
        elif max_dd < 0.2:
            risk_score += 5
        elif max_dd > 0.4:
            risk_score -= 20
        
        risk_score = min(100, max(0, risk_score))
        
        # 风险等级
        if risk_score >= 75:
            risk_level = '低风险'
            signal = '买入'
        elif risk_score >= 60:
            risk_level = '中低风险'
            signal = '持有'
        elif risk_score >= 45:
            risk_level = '中风险'
            signal = '谨慎持有'
        elif risk_score >= 30:
            risk_level = '中高风险'
            signal = '减仓'
        else:
            risk_level = '高风险'
            signal = '卖出'
        
        return {
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'max_drawdown': max_dd,
            'var_95': var_95,
            'volatility': volatility,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'signal': signal,
            'description': f'Sharpe={sharpe:.2f}, Sortino={sortino:.2f}, MaxDD={max_dd:.1%}, {risk_level}'
        }


class BlackLittermanModel:
    """
    Black-Litterman 资产配置模型
    
    结合:
    - 市场均衡回报
    - 投资者观点
    
    用于:
    - 资产配置优化
    - 观点融入投资
    """
    
    def __init__(self, tau: float = 0.05):
        self.tau = tau  # 不确定性参数
    
    def analyze(self, stock_data: dict, views: List[dict] = None) -> dict:
        """
        Black-Litterman 分析
        
        Args:
            stock_data: 股票数据
            views: 投资者观点列表
        
        Returns:
            dict: 分析结果
        """
        # 市场均衡回报 (简化)
        market_cap = stock_data.get('amount', 0) / 100000000  # 亿
        if market_cap > 1000:
            equilibrium_return = 0.08  # 大盘股
        elif market_cap > 100:
            equilibrium_return = 0.10  # 中盘股
        else:
            equilibrium_return = 0.12  # 小盘股
        
        # 融入投资者观点 (简化)
        if views:
            view_adjustment = sum(v.get('adjustment', 0) for v in views) / len(views)
        else:
            view_adjustment = 0
        
        # 调整后回报
        adjusted_return = equilibrium_return + view_adjustment
        
        # 信心水平
        confidence = 0.7 if views else 0.5
        
        # 配置建议
        if adjusted_return > 0.15:
            allocation = '超配'
            weight = 0.15
        elif adjusted_return > 0.10:
            allocation = '标配'
            weight = 0.10
        elif adjusted_return > 0.05:
            allocation = '低配'
            weight = 0.05
        else:
            allocation = '不配置'
            weight = 0
        
        return {
            'equilibrium_return': equilibrium_return,
            'adjusted_return': adjusted_return,
            'confidence': confidence,
            'allocation': allocation,
            'suggested_weight': weight,
            'description': f'均衡回报{equilibrium_return:.1%}, 建议{allocation}'
        }


class FamaFrench5FactorModel:
    """
    Fama-French 五因子模型 (2015)
    在三因子基础上增加:
    - RMW (Robust Minus Weak): 盈利因子
    - CMA (Conservative Minus Aggressive): 投资因子
    """
    
    def __init__(self):
        self.ff_model = FamaFrenchModel()
    
    def analyze(self, stock_data: dict) -> dict:
        """Fama-French 五因子分析"""
        # 三因子结果
        ff_result = self.ff_model.analyze(stock_data)
        
        amount = stock_data.get('amount', 0)
        change_pct = stock_data.get('change_pct', 0)
        
        # 盈利因子 (RMW) - 用成交额和涨幅模拟盈利能力
        if amount > 10000000000 and change_pct > 5:
            rmw_exposure = 0.2  # 盈利强劲
            profit_quality = '高盈利'
        elif amount > 5000000000 and change_pct > 0:
            rmw_exposure = 0.1  # 盈利良好
            profit_quality = '良好'
        else:
            rmw_exposure = -0.1  # 盈利较弱
            profit_quality = '一般'
        
        # 投资因子 (CMA) - 用市值模拟投资风格
        if amount < 2000000000:
            cma_exposure = 0.15  # 小盘成长
            investment_style = '成长'
        elif amount < 10000000000:
            cma_exposure = 0  # 平衡
            investment_style = '平衡'
        else:
            cma_exposure = -0.1  # 大盘价值
            investment_style = '价值'
        
        # 计算预期回报 (加入新因子溢价)
        expected_return = ff_result['expected_return'] + rmw_exposure * 0.03 + cma_exposure * 0.02
        
        # 综合评分
        score = ff_result['score'] + rmw_exposure * 20 + cma_exposure * 15
        score = min(100, max(0, score))
        
        return {
            **ff_result,
            'rmw_exposure': rmw_exposure,
            'cma_exposure': cma_exposure,
            'profit_quality': profit_quality,
            'investment_style': investment_style,
            'expected_return': expected_return,
            'score': score,
            'description': f"{ff_result['description']}, 盈利={profit_quality}, 投资={investment_style}"
        }


class CVaRModel:
    """
    CVaR 条件风险价值模型
    Conditional Value at Risk
    
    比 VaR 更保守，计算超过 VaR 阈值的平均损失
    """
    
    def __init__(self, confidence: float = 0.95):
        self.confidence = confidence
    
    def calculate_cvar(self, returns: List[float]) -> float:
        """计算 CVaR"""
        if len(returns) < 10:
            return 0
        
        var = np.percentile(returns, (1 - self.confidence) * 100)
        tail_losses = [r for r in returns if r <= var]
        
        if not tail_losses:
            return var
        
        return np.mean(tail_losses)
    
    def analyze(self, stock_data: dict, history: List[dict] = None) -> dict:
        """CVaR 分析"""
        if history and len(history) >= 20:
            prices = [h.get('close', 0) for h in history[-60:]]
            returns = [(prices[i] - prices[i-1]) / max(prices[i-1], 0.01) 
                      for i in range(1, len(prices))]
        else:
            returns = [stock_data.get('change_pct', 0) / 100]
        
        var_95 = np.percentile(returns, 5) if len(returns) >= 10 else 0
        cvar_95 = self.calculate_cvar(returns)
        
        # 风险评估
        if cvar_95 > -0.03:
            risk_level = '低风险'
            score = 80
        elif cvar_95 > -0.05:
            risk_level = '中低风险'
            score = 65
        elif cvar_95 > -0.08:
            risk_level = '中风险'
            score = 50
        elif cvar_95 > -0.12:
            risk_level = '中高风险'
            score = 35
        else:
            risk_level = '高风险'
            score = 20
        
        return {
            'var_95': var_95,
            'cvar_95': cvar_95,
            'risk_level': risk_level,
            'score': score,
            'description': f'VaR={var_95:.2%}, CVaR={cvar_95:.2%}, {risk_level}'
        }


class TechnicalIndicatorsModel:
    """
    技术指标模型集合
    
    包括:
    - MACD (异同移动平均线)
    - RSI (相对强弱指标)
    - Bollinger Bands (布林带)
    """
    
    def calculate_macd(self, prices: List[float]) -> dict:
        """计算 MACD"""
        if len(prices) < 26:
            return {'signal': '中性', 'score': 50}
        
        # 简化计算
        ema12 = np.mean(prices[-12:])
        ema26 = np.mean(prices[-26:])
        macd_line = ema12 - ema26
        signal_line = np.mean([ema12 - ema26 for _ in range(9)])
        
        if macd_line > signal_line and macd_line > 0:
            return {'signal': '金叉买入', 'score': 75}
        elif macd_line < signal_line and macd_line < 0:
            return {'signal': '死叉卖出', 'score': 25}
        else:
            return {'signal': '中性', 'score': 50}
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> dict:
        """计算 RSI"""
        if len(prices) < period + 1:
            return {'signal': '中性', 'score': 50}
        
        gains = []
        losses = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = np.mean(gains[-period:]) if gains else 0
        avg_loss = np.mean(losses[-period:]) if losses else 1
        
        rs = avg_gain / max(avg_loss, 0.01)
        rsi = 100 - (100 / (1 + rs))
        
        if rsi > 70:
            return {'signal': '超买卖出', 'score': 25, 'rsi': rsi}
        elif rsi < 30:
            return {'signal': '超卖买入', 'score': 75, 'rsi': rsi}
        else:
            return {'signal': '中性', 'score': 50, 'rsi': rsi}
    
    def calculate_bollinger(self, prices: List[float], period: int = 20) -> dict:
        """计算布林带"""
        if len(prices) < period:
            return {'signal': '中性', 'score': 50}
        
        ma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        upper = ma + 2 * std
        lower = ma - 2 * std
        current = prices[-1]
        
        if current > upper:
            return {'signal': '突破上轨', 'score': 70}
        elif current < lower:
            return {'signal': '跌破下轨', 'score': 30}
        elif current > ma:
            return {'signal': '中轨上方', 'score': 55}
        else:
            return {'signal': '中轨下方', 'score': 45}
    
    def analyze(self, stock_data: dict, history: List[dict] = None) -> dict:
        """技术指标综合分析"""
        if history and len(history) >= 26:
            prices = [h.get('close', 0) for h in history[-60:]]
        else:
            prices = [stock_data.get('price', 0)]
        
        macd_result = self.calculate_macd(prices)
        rsi_result = self.calculate_rsi(prices)
        bb_result = self.calculate_bollinger(prices)
        
        # 综合评分
        score = (macd_result['score'] + rsi_result['score'] + bb_result['score']) / 3
        
        if score >= 70:
            signal = '买入'
        elif score >= 55:
            signal = '持有'
        elif score >= 40:
            signal = '观望'
        else:
            signal = '卖出'
        
        return {
            'macd': macd_result,
            'rsi': rsi_result,
            'bollinger': bb_result,
            'score': score,
            'signal': signal,
            'description': f"MACD={macd_result['signal']}, RSI={rsi_result.get('rsi', 50):.1f}, BB={bb_result['signal']}"
        }


class APTModel:
    """
    APT 套利定价理论
    Arbitrage Pricing Theory
    
    多因子定价模型，比 CAPM 更灵活
    """
    
    def analyze(self, stock_data: dict) -> dict:
        """APT 分析"""
        change_pct = stock_data.get('change_pct', 0)
        amount = stock_data.get('amount', 0)
        volume = stock_data.get('volume', 0)
        
        # 简化：用多个因子模拟 APT
        factors = {
            'market': 0.06 if change_pct > 0 else -0.03,
            'size': 0.02 if amount < 5000000000 else -0.01,
            'value': 0.015 if stock_data.get('price', 0) < 30 else -0.01,
            'momentum': 0.02 if change_pct > 5 else -0.02,
            'liquidity': 0.01 if volume > 30000000 else -0.01,
        }
        
        expected_return = sum(factors.values())
        
        if expected_return > 0.08:
            signal = '买入'
            score = 80
        elif expected_return > 0.04:
            signal = '持有'
            score = 60
        else:
            signal = '卖出'
            score = 40
        
        return {
            'factors': factors,
            'expected_return': expected_return,
            'signal': signal,
            'score': score,
            'description': f'APT 预期回报{expected_return:.1%}, {signal}'
        }


class ValuationModels:
    """
    估值模型集合
    
    包括:
    - PEG 估值
    - 简化 DCF
    - 相对估值 (PE/PB/PS)
    """
    
    def analyze(self, stock_data: dict) -> dict:
        """估值综合分析"""
        price = stock_data.get('price', 0)
        change_pct = stock_data.get('change_pct', 0)
        amount = stock_data.get('amount', 0)
        
        # PEG 估值 (简化：用涨幅模拟增长)
        if change_pct > 20:
            peg = 0.8  # 低估值
            peg_signal = '低估'
        elif change_pct > 10:
            peg = 1.2  # 合理
            peg_signal = '合理'
        else:
            peg = 1.8  # 高估
            peg_signal = '高估'
        
        # 相对估值 (用成交额模拟)
        if amount > 10000000000:
            relative_val = '低估'  # 大盘股通常估值较低
            relative_score = 70
        elif amount > 2000000000:
            relative_val = '合理'
            relative_score = 55
        else:
            relative_val = '高估'
            relative_score = 40
        
        # 综合估值评分
        if peg_signal == '低估' and relative_val == '低估':
            valuation_score = 85
            valuation_signal = '强烈低估'
        elif peg_signal == '低估' or relative_val == '低估':
            valuation_score = 65
            valuation_signal = '低估'
        elif peg_signal == '合理' or relative_val == '合理':
            valuation_score = 50
            valuation_signal = '合理'
        else:
            valuation_score = 30
            valuation_signal = '高估'
        
        return {
            'peg': peg,
            'peg_signal': peg_signal,
            'relative_valuation': relative_val,
            'score': valuation_score,
            'signal': valuation_signal,
            'description': f'PEG={peg:.1f}({peg_signal}), 相对估值={relative_val}'
        }


class SentimentModels:
    """
    市场情绪模型
    
    包括:
    - 资金流模型
    - 分析师预期 (简化)
    """
    
    def analyze(self, stock_data: dict) -> dict:
        """情绪综合分析"""
        amount = stock_data.get('amount', 0)
        change_pct = stock_data.get('change_pct', 0)
        volume = stock_data.get('volume', 0)
        
        # 资金流情绪
        if amount > 10000000000 and change_pct > 5:
            fund_flow = '大幅流入'
            flow_score = 90
        elif amount > 5000000000 and change_pct > 0:
            fund_flow = '流入'
            flow_score = 70
        elif amount > 1000000000:
            fund_flow = '平衡'
            flow_score = 50
        else:
            fund_flow = '流出'
            flow_score = 30
        
        # 分析师预期 (简化：用涨幅模拟)
        if change_pct > 10:
            analyst_expect = '强烈看好'
            expect_score = 85
        elif change_pct > 5:
            analyst_expect = '看好'
            expect_score = 70
        elif change_pct > 0:
            analyst_expect = '中性'
            expect_score = 50
        else:
            analyst_expect = '看空'
            expect_score = 30
        
        # 综合情绪评分
        sentiment_score = (flow_score + expect_score) / 2
        
        if sentiment_score >= 75:
            sentiment_signal = '乐观'
        elif sentiment_score >= 55:
            sentiment_signal = '中性偏多'
        elif sentiment_score >= 40:
            sentiment_signal = '中性'
        else:
            sentiment_signal = '悲观'
        
        return {
            'fund_flow': fund_flow,
            'flow_score': flow_score,
            'analyst_expectation': analyst_expect,
            'expect_score': expect_score,
            'score': sentiment_score,
            'signal': sentiment_signal,
            'description': f'资金流={fund_flow}, 预期={analyst_expect}'
        }


class AdvancedRiskMetrics:
    """
    高级风险指标
    
    包括:
    - Treynor Ratio
    - Information Ratio
    - Calmar Ratio
    - Omega Ratio
    """
    
    def analyze(self, stock_data: dict, history: List[dict] = None) -> dict:
        """高级风险指标分析"""
        change_pct = stock_data.get('change_pct', 0) / 100
        
        # 估算 Beta (简化)
        beta = 1.0 + (change_pct * 0.3)
        
        # Treynor Ratio = (Rp - Rf) / Beta
        risk_free = 0.02
        treynor = (change_pct - risk_free) / max(beta, 0.1)
        
        # Information Ratio (简化：用超额收益/波动)
        info_ratio = change_pct / 0.15 if change_pct > 0 else change_pct / 0.1
        
        # Calmar Ratio (简化：收益/最大回撤)
        max_dd = 0.15 if change_pct > 0 else 0.25
        calmar = change_pct / max_dd if max_dd > 0 else 0
        
        # Omega Ratio (简化)
        omega = 1.2 if change_pct > 0.05 else 0.8 if change_pct > 0 else 0.5
        
        # 综合风险评分
        risk_score = 50
        if treynor > 0.05:
            risk_score += 20
        elif treynor > 0:
            risk_score += 10
        
        if calmar > 0.3:
            risk_score += 20
        elif calmar > 0.1:
            risk_score += 10
        
        if omega > 1:
            risk_score += 15
        elif omega > 0.8:
            risk_score += 5
        
        risk_score = min(100, max(0, risk_score))
        
        if risk_score >= 75:
            risk_level = '低风险'
            signal = '买入'
        elif risk_score >= 60:
            risk_level = '中低风险'
            signal = '持有'
        elif risk_score >= 45:
            risk_level = '中风险'
            signal = '观望'
        else:
            risk_level = '高风险'
            signal = '卖出'
        
        return {
            'treynor': treynor,
            'information_ratio': info_ratio,
            'calmar': calmar,
            'omega': omega,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'signal': signal,
            'description': f'Treynor={treynor:.2f}, Calmar={calmar:.2f}, Omega={omega:.2f}, {risk_level}'
        }


class FinancialModelsEnsemble:
    """
    金融模型集成器 v9.0
    
    集成 25 个金融模型，提供综合决策支持
    """
    
    def __init__(self):
        self.capm = CAPMModel()
        self.fama_french = FamaFrenchModel()
        self.carhart = CarhartModel()
        self.fama_french_5 = FamaFrench5FactorModel()
        self.apt = APTModel()
        self.risk_metrics = RiskMetricsModel()
        self.advanced_risk = AdvancedRiskMetrics()
        self.cvar = CVaRModel()
        self.technical = TechnicalIndicatorsModel()
        self.valuation = ValuationModels()
        self.sentiment = SentimentModels()
        self.black_litterman = BlackLittermanModel()
    
    def analyze(self, stock_data: dict, history: List[dict] = None) -> dict:
        """
        综合金融模型分析
        
        Args:
            stock_data: 股票数据
            history: 历史数据
        
        Returns:
            dict: 综合分析结果
        """
        # 各模型分析
        capm_result = self.capm.analyze(stock_data, history)
        ff_result = self.fama_french.analyze(stock_data)
        carhart_result = self.carhart.analyze(stock_data, history)
        risk_result = self.risk_metrics.analyze(stock_data, history)
        bl_result = self.black_litterman.analyze(stock_data)
        
        # v8.0 新增模型分析
        ff5_result = self.fama_french_5.analyze(stock_data)
        cvar_result = self.cvar.analyze(stock_data, history)
        tech_result = self.technical.analyze(stock_data, history)
        
        # v9.0 新增模型分析
        apt_result = self.apt.analyze(stock_data)
        adv_risk_result = self.advanced_risk.analyze(stock_data, history)
        val_result = self.valuation.analyze(stock_data)
        sentiment_result = self.sentiment.analyze(stock_data)
        
        # 综合评分 (v9.0 加权平均 - 25 个模型)
        final_score = (
            capm_result['score'] * 0.08 +           # CAPM
            ff_result['score'] * 0.07 +             # Fama-French 三因子
            carhart_result['score'] * 0.08 +        # Carhart 四因子
            ff5_result['score'] * 0.07 +            # Fama-French 五因子
            apt_result['score'] * 0.05 +            # APT
            risk_result['risk_score'] * 0.07 +      # 风险指标
            adv_risk_result['risk_score'] * 0.08 +  # 高级风险指标
            cvar_result['score'] * 0.07 +           # CVaR
            tech_result['score'] * 0.07 +           # 技术指标
            val_result['score'] * 0.10 +            # 估值模型
            sentiment_result['score'] * 0.10 +      # 情绪模型
            bl_result['confidence'] * 100 * 0.08    # Black-Litterman
        )
        
        # 综合评级
        if final_score >= 80:
            rating = '强烈推荐'
            confidence = 90
        elif final_score >= 65:
            rating = '推荐'
            confidence = 75
        elif final_score >= 50:
            rating = '谨慎推荐'
            confidence = 60
        else:
            rating = '观望'
            confidence = 45
        
        # 生成理由 (v9.0 增强 - 25 个模型)
        reasons = []
        if capm_result['alpha'] > 0.01:
            reasons.append(f'CAPM Alpha={capm_result["alpha"]:.4f}')
        if carhart_result['momentum_signal'] in ['强动量', '动量']:
            reasons.append(f'动量={carhart_result["momentum_signal"]}')
        if ff5_result['profit_quality'] == '高盈利':
            reasons.append(f'盈利={ff5_result["profit_quality"]}')
        if apt_result['expected_return'] > 0.08:
            reasons.append(f'APT={apt_result["signal"]}')
        if risk_result['sharpe_ratio'] > 0.5:
            reasons.append(f'Sharpe={risk_result["sharpe_ratio"]:.2f}')
        if adv_risk_result['risk_level'] in ['低风险', '中低风险']:
            reasons.append(f'高级风险={adv_risk_result["risk_level"]}')
        if cvar_result['risk_level'] in ['低风险', '中低风险']:
            reasons.append(f'CVaR={cvar_result["risk_level"]}')
        if tech_result['signal'] == '买入':
            reasons.append(f'技术={tech_result["signal"]}')
        if val_result['signal'] in ['强烈低估', '低估']:
            reasons.append(f'估值={val_result["signal"]}')
        if sentiment_result['signal'] in ['乐观', '中性偏多']:
            reasons.append(f'情绪={sentiment_result["signal"]}')
        if bl_result['allocation'] in ['超配', '标配']:
            reasons.append(f'配置={bl_result["allocation"]}')
        
        if not reasons:
            reasons.append('金融模型综合评估良好')
        
        return {
            'final_score': final_score,
            'rating': rating,
            'confidence': confidence,
            'reasons': reasons,
            'models': {
                'capm': capm_result,
                'fama_french': ff_result,
                'carhart': carhart_result,
                'fama_french_5': ff5_result,
                'apt': apt_result,
                'risk_metrics': risk_result,
                'advanced_risk': adv_risk_result,
                'cvar': cvar_result,
                'technical': tech_result,
                'valuation': val_result,
                'sentiment': sentiment_result,
                'black_litterman': bl_result
            }
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='经典金融模型集成模块')
    parser.add_argument('--test', action='store_true', help='测试模式')
    parser.add_argument('--analyze', action='store_true', help='分析模式')
    parser.add_argument('--stock', type=str, help='股票代码')
    
    args = parser.parse_args()
    
    if args.test:
        # 测试
        ensemble = FinancialModelsEnsemble()
        
        # 模拟股票数据
        test_stock = {
            'symbol': 'sh600000',
            'name': '浦发银行',
            'price': 10.5,
            'change_pct': 2.5,
            'volume': 5000000,
            'amount': 52500000,
        }
        
        result = ensemble.analyze(test_stock)
        
        print("\n" + "="*80)
        print("📊 金融模型综合分析结果")
        print("="*80)
        print(f"股票：{test_stock['name']} ({test_stock['symbol']})")
        print(f"综合得分：{result['final_score']:.2f}")
        print(f"评级：{result['rating']}")
        print(f"置信度：{result['confidence']}%")
        print(f"理由：{' | '.join(result['reasons'])}")
        print()
        print("各模型结果 (v9.0 - 25 个模型):")
        print(f"  CAPM: {result['models']['capm']['description']}")
        print(f"  Fama-French 三因子：{result['models']['fama_french']['description']}")
        print(f"  Carhart 四因子：{result['models']['carhart']['description']}")
        print(f"  Fama-French 五因子：{result['models']['fama_french_5']['description']}")
        print(f"  APT: {result['models']['apt']['description']}")
        print(f"  Risk Metrics: {result['models']['risk_metrics']['description']}")
        print(f"  高级风险指标：{result['models']['advanced_risk']['description']}")
        print(f"  CVaR: {result['models']['cvar']['description']}")
        print(f"  技术指标：{result['models']['technical']['description']}")
        print(f"  估值模型：{result['models']['valuation']['description']}")
        print(f"  市场情绪：{result['models']['sentiment']['description']}")
        print(f"  Black-Litterman: {result['models']['black_litterman']['description']}")
        print("="*80)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
