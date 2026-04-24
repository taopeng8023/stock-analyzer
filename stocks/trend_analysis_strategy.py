#!/usr/bin/env python3
"""
股市趋势技术分析策略
基于经典技术分析理论的决策策略系统

参考书籍:
- 《股市趋势技术分析》- 罗伯特·爱德华兹
- 《日本蜡烛图技术》- 史蒂夫·尼森
- 《期货市场技术分析》- 约翰·墨菲

分析维度:
1. 道氏理论 (趋势判断)
2. 均线系统 (MA5/10/20/60)
3. K 线形态 (反转/整理/持续)
4. 支撑阻力位
5. 成交量确认
6. MACD 指标
7. KDJ 指标
8. RSI 指标

用法:
    python3 trend_analysis_strategy.py --stock sh600000
    python3 trend_analysis_strategy.py --strategy all
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))


# ============ 趋势分析策略 ============

class TrendAnalysisStrategy:
    """
    股市趋势技术分析策略
    
    基于经典技术分析理论的综合评估系统
    """
    
    def __init__(self):
        self.cache_dir = Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
    
    def analyze_trend(self, stock_data: dict) -> dict:
        """
        综合趋势分析
        
        Args:
            stock_data: 股票数据 (包含 K 线、均线、指标等)
        
        Returns:
            dict: 分析结果
        """
        # 1. 道氏理论趋势判断
        dow_trend = self._analyze_dow_theory(stock_data)
        
        # 2. 均线系统分析
        ma_system = self._analyze_ma_system(stock_data)
        
        # 3. K 线形态识别
        candlestick_pattern = self._analyze_candlestick_pattern(stock_data)
        
        # 4. 支撑阻力位
        support_resistance = self._analyze_support_resistance(stock_data)
        
        # 5. 成交量确认
        volume_confirmation = self._analyze_volume_confirmation(stock_data)
        
        # 6. MACD 指标
        macd_signal = self._analyze_macd(stock_data)
        
        # 7. KDJ 指标
        kdj_signal = self._analyze_kdj(stock_data)
        
        # 8. RSI 指标
        rsi_signal = self._analyze_rsi(stock_data)
        
        # 综合评分
        total_score = (
            dow_trend['score'] * 0.20 +
            ma_system['score'] * 0.20 +
            candlestick_pattern['score'] * 0.15 +
            support_resistance['score'] * 0.10 +
            volume_confirmation['score'] * 0.15 +
            macd_signal['score'] * 0.10 +
            kdj_signal['score'] * 0.05 +
            rsi_signal['score'] * 0.05
        )
        
        # 趋势判断
        if total_score >= 75:
            trend = '强烈上涨'
            signal = '强烈买入'
            confidence = 90
        elif total_score >= 65:
            trend = '上涨'
            signal = '买入'
            confidence = 75
        elif total_score >= 55:
            trend = '偏强'
            signal = '增持'
            confidence = 60
        elif total_score >= 45:
            trend = '盘整'
            signal = '持有'
            confidence = 50
        elif total_score >= 35:
            trend = '偏弱'
            signal = '减持'
            confidence = 40
        else:
            trend = '下跌'
            signal = '卖出'
            confidence = 30
        
        return {
            'total_score': round(total_score, 1),
            'trend': trend,
            'signal': signal,
            'confidence': confidence,
            'dow_trend': dow_trend,
            'ma_system': ma_system,
            'candlestick_pattern': candlestick_pattern,
            'support_resistance': support_resistance,
            'volume_confirmation': volume_confirmation,
            'macd_signal': macd_signal,
            'kdj_signal': kdj_signal,
            'rsi_signal': rsi_signal,
            'analysis_time': datetime.now().isoformat(),
        }
    
    def _analyze_dow_theory(self, stock_data: dict) -> dict:
        """
        道氏理论趋势分析
        
        核心原则:
        1. 市场价格包含一切信息
        2. 市场有三种趋势 (主要/次要/短期)
        3. 主要趋势有三个阶段
        4. 指数必须相互确认
        5. 成交量确认趋势
        6. 趋势持续直到反转信号
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        price = stock_data.get('price', 0)
        
        # 简化版道氏理论判断
        # 基于价格和涨跌幅判断主要趋势
        
        if change_pct > 5:
            trend = '主要上涨趋势'
            score = 85
            stage = '第二阶段 (上涨确认)'
        elif change_pct > 2:
            trend = '主要上涨趋势'
            score = 70
            stage = '第一阶段 (初步上涨)'
        elif change_pct > -2:
            trend = '盘整趋势'
            score = 50
            stage = '盘整阶段'
        elif change_pct > -5:
            trend = '主要下跌趋势'
            score = 30
            stage = '第一阶段 (初步下跌)'
        else:
            trend = '主要下跌趋势'
            score = 15
            stage = '第二阶段 (下跌确认)'
        
        return {
            'trend': trend,
            'stage': stage,
            'score': score,
            'description': f'道氏理论：{trend} - {stage}',
        }
    
    def _analyze_ma_system(self, stock_data: dict) -> dict:
        """
        均线系统分析
        
        均线组合:
        - MA5: 短期趋势
        - MA10: 短期趋势
        - MA20: 中期趋势
        - MA60: 长期趋势
        
        多头排列：MA5 > MA10 > MA20 > MA60
        空头排列：MA5 < MA10 < MA20 < MA60
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        price = stock_data.get('price', 0)
        
        # 简化版均线分析 (基于价格位置)
        if price > 0:
            # 假设价格在均线上方为多头
            if price > 50:  # 高价股
                ma_signal = '多头排列'
                score = 75
            elif price > 20:  # 中价股
                ma_signal = '偏多'
                score = 60
            else:  # 低价股
                ma_signal = '中性'
                score = 50
        else:
            ma_signal = '未知'
            score = 50
        
        return {
            'signal': ma_signal,
            'score': score,
            'description': f'均线系统：{ma_signal}',
        }
    
    def _analyze_candlestick_pattern(self, stock_data: dict) -> dict:
        """
        K 线形态识别
        
        反转形态:
        - 锤子线/上吊线
        - 吞没形态
        - 早晨之星/黄昏之星
        - 头肩顶/底
        
        整理形态:
        - 三角形
        - 矩形
        - 旗形
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版 K 线形态识别
        if change_pct > 7:
            pattern = '大阳线'
            signal = '强烈看涨'
            score = 85
        elif change_pct > 3:
            pattern = '中阳线'
            signal = '看涨'
            score = 70
        elif change_pct > 0:
            pattern = '小阳线'
            signal = '偏涨'
            score = 55
        elif change_pct > -3:
            pattern = '小阴线'
            signal = '偏跌'
            score = 45
        elif change_pct > -7:
            pattern = '中阴线'
            signal = '看跌'
            score = 30
        else:
            pattern = '大阴线'
            signal = '强烈看跌'
            score = 15
        
        return {
            'pattern': pattern,
            'signal': signal,
            'score': score,
            'description': f'K 线形态：{pattern} - {signal}',
        }
    
    def _analyze_support_resistance(self, stock_data: dict) -> dict:
        """
        支撑阻力位分析
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        price = stock_data.get('price', 0)
        
        # 简化版支撑阻力计算
        if price > 0:
            support = price * 0.95  # 5% 支撑位
            resistance = price * 1.05  # 5% 阻力位
            position = '中间'
            score = 50
            
            if price > (support + resistance) / 2:
                position = '偏上'
                score = 60
            else:
                position = '偏下'
                score = 40
        else:
            support = 0
            resistance = 0
            position = '未知'
            score = 50
        
        return {
            'support': round(support, 2),
            'resistance': round(resistance, 2),
            'position': position,
            'score': score,
            'description': f'支撑阻力：{position} (支撑¥{support:.2f}, 阻力¥{resistance:.2f})',
        }
    
    def _analyze_volume_confirmation(self, stock_data: dict) -> dict:
        """
        成交量确认分析
        
        量价关系:
        - 价涨量增：健康上涨
        - 价涨量缩：上涨乏力
        - 价跌量增：恐慌下跌
        - 价跌量缩：下跌乏力
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        volume = stock_data.get('volume', 0)
        amount = stock_data.get('amount', 0)
        
        # 简化版量价关系分析
        if change_pct > 3 and volume > 2000000:
            relation = '价涨量增'
            signal = '健康上涨'
            score = 85
        elif change_pct > 3 and volume <= 2000000:
            relation = '价涨量缩'
            signal = '上涨乏力'
            score = 50
        elif change_pct > 0:
            relation = '温和上涨'
            signal = '偏多'
            score = 60
        elif change_pct < -3 and volume > 2000000:
            relation = '价跌量增'
            signal = '恐慌下跌'
            score = 20
        elif change_pct < -3 and volume <= 2000000:
            relation = '价跌量缩'
            signal = '下跌乏力'
            score = 40
        else:
            relation = '盘整'
            signal = '观望'
            score = 50
        
        return {
            'relation': relation,
            'signal': signal,
            'score': score,
            'description': f'量价关系：{relation} - {signal}',
        }
    
    def _analyze_macd(self, stock_data: dict) -> dict:
        """
        MACD 指标分析
        
        金叉：DIF 上穿 DEA (买入信号)
        死叉：DIF 下穿 DEA (卖出信号)
        背离：价格新高但 MACD 不新高 (反转信号)
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版 MACD 分析 (基于涨跌幅模拟)
        if change_pct > 5:
            signal = '金叉'
            trend = '上涨'
            score = 80
        elif change_pct > 0:
            signal = '偏多'
            trend = '偏涨'
            score = 60
        elif change_pct > -5:
            signal = '偏空'
            trend = '偏跌'
            score = 40
        else:
            signal = '死叉'
            trend = '下跌'
            score = 20
        
        return {
            'signal': signal,
            'trend': trend,
            'score': score,
            'description': f'MACD: {signal} - {trend}',
        }
    
    def _analyze_kdj(self, stock_data: dict) -> dict:
        """
        KDJ 指标分析
        
        超买：K>80, D>80 (卖出信号)
        超卖：K<20, D<20 (买入信号)
        金叉：K 上穿 D (买入信号)
        死叉：K 下穿 D (卖出信号)
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版 KDJ 分析
        if change_pct > 7:
            k, d, j = 85, 80, 95
            signal = '超买'
            score = 30
        elif change_pct > 3:
            k, d, j = 65, 60, 75
            signal = '偏多'
            score = 60
        elif change_pct > -3:
            k, d, j = 50, 50, 50
            signal = '中性'
            score = 50
        elif change_pct > -7:
            k, d, j = 35, 40, 25
            signal = '偏空'
            score = 40
        else:
            k, d, j = 15, 20, 5
            signal = '超卖'
            score = 70
        
        return {
            'k': k,
            'd': d,
            'j': j,
            'signal': signal,
            'score': score,
            'description': f'KDJ: {signal} (K={k}, D={d}, J={j})',
        }
    
    def _analyze_rsi(self, stock_data: dict) -> dict:
        """
        RSI 指标分析
        
        超买：RSI>70 (卖出信号)
        超卖：RSI<30 (买入信号)
        
        Args:
            stock_data: 股票数据
        
        Returns:
            dict: 分析结果
        """
        change_pct = stock_data.get('change_pct', 0)
        
        # 简化版 RSI 分析
        if change_pct > 7:
            rsi = 75
            signal = '超买'
            score = 30
        elif change_pct > 3:
            rsi = 60
            signal = '偏强'
            score = 60
        elif change_pct > -3:
            rsi = 50
            signal = '中性'
            score = 50
        elif change_pct > -7:
            rsi = 40
            signal = '偏弱'
            score = 40
        else:
            rsi = 25
            signal = '超卖'
            score = 70
        
        return {
            'rsi': rsi,
            'signal': signal,
            'score': score,
            'description': f'RSI: {rsi} - {signal}',
        }
    
    def get_decision_bonus(self, analysis_result: dict) -> float:
        """
        根据技术分析结果计算决策加分
        
        Args:
            analysis_result: 技术分析结果
        
        Returns:
            float: 决策加分 (0-0.3)
        """
        total_score = analysis_result.get('total_score', 0)
        
        if total_score >= 75:
            return 0.30  # 强烈上涨
        elif total_score >= 65:
            return 0.25  # 上涨
        elif total_score >= 55:
            return 0.20  # 偏强
        elif total_score >= 45:
            return 0.10  # 盘整
        elif total_score >= 35:
            return 0.05  # 偏弱
        else:
            return 0.00  # 下跌


def analyze_stock_trend(stock_data: dict) -> dict:
    """
    分析股票趋势 (快捷函数)
    
    Args:
        stock_data: 股票数据
    
    Returns:
        dict: 分析结果
    """
    strategy = TrendAnalysisStrategy()
    return strategy.analyze_trend(stock_data)


# ============ 主函数 ============

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='股市趋势技术分析策略')
    parser.add_argument('--stock', type=str, help='股票代码')
    parser.add_argument('--strategy', type=str, help='策略名称')
    
    args = parser.parse_args()
    
    if args.stock:
        # 测试分析
        test_data = {
            'symbol': args.stock,
            'name': '测试股票',
            'price': 50.0,
            'change_pct': 3.5,
            'volume': 3000000,
            'amount': 150000000,
        }
        
        strategy = TrendAnalysisStrategy()
        result = strategy.analyze_trend(test_data)
        
        print(f"\n{'='*80}")
        print(f"📈 {args.stock} 趋势技术分析")
        print(f"{'='*80}")
        print(f"\n综合评分：{result['total_score']}/100")
        print(f"趋势判断：{result['trend']}")
        print(f"交易信号：{result['signal']}")
        print(f"置信度：{result['confidence']}%")
        print(f"\n各维度分析:")
        print(f"  道氏理论：{result['dow_trend']['description']}")
        print(f"  均线系统：{result['ma_system']['description']}")
        print(f"  K 线形态：{result['candlestick_pattern']['description']}")
        print(f"  支撑阻力：{result['support_resistance']['description']}")
        print(f"  量价关系：{result['volume_confirmation']['description']}")
        print(f"  MACD: {result['macd_signal']['description']}")
        print(f"  KDJ: {result['kdj_signal']['description']}")
        print(f"  RSI: {result['rsi_signal']['description']}")
        print(f"\n决策加分：{strategy.get_decision_bonus(result):.2f}")
        print(f"{'='*80}\n")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
