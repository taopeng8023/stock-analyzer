#!/usr/bin/env python3
"""
增强标签生成模块 - v1.0

功能:
- 成交额标签
- 涨跌幅标签
- 行业标签
- 技术形态标签
- 风险标签
- 概念标签

用法:
    from decision.tag_generator import EnhancedTagGenerator
    
    gen = EnhancedTagGenerator()
    tags = gen.generate(stock_data, fundamental_data, technical_data)
"""

from typing import Dict, List, Optional
from datetime import datetime


class EnhancedTagGenerator:
    """增强标签生成器"""
    
    # 标签配置
    TURNOVER_THRESHOLDS = {
        'high': 5000000000,      # 50 亿 - 资金关注度高
        'medium': 1000000000,    # 10 亿 - 成交活跃
        'low': 100000000,        # 1 亿 - 流动性好
    }
    
    CHANGE_THRESHOLDS = {
        'surge': 10,             # >10% - 强势涨停
        'rise': 2,               # 2-10% - 温和上涨
        'small_rise': 0,         # 0-2% - 小幅上涨
        'small_fall': 0,         # 0 to -2% - 小幅下跌
        'fall': -5,              # -5% to -10% - 温和下跌
        'plunge': -10,           # <-10% - 大幅下跌
    }
    
    def generate(self, stock: Dict, 
                 fundamental_data: Optional[Dict] = None,
                 technical_data: Optional[Dict] = None) -> List[str]:
        """
        生成增强标签
        
        Args:
            stock: 股票数据
            fundamental_data: 基本面数据（可选）
            technical_data: 技术面数据（可选）
        
        Returns:
            List[str]: 标签列表
        """
        tags = []
        
        # 1. 成交额标签
        tags.extend(self._generate_turnover_tags(stock))
        
        # 2. 涨跌幅标签
        tags.extend(self._generate_change_tags(stock))
        
        # 3. 行业标签
        if fundamental_data:
            tags.extend(self._generate_industry_tags(fundamental_data))
        
        # 4. 技术形态标签
        if technical_data:
            tags.extend(self._generate_technical_tags(technical_data))
        
        # 5. 风险标签
        tags.extend(self._generate_risk_tags(stock, fundamental_data))
        
        return tags
    
    def _generate_turnover_tags(self, stock: Dict) -> List[str]:
        """生成成交额标签"""
        tags = []
        turnover = stock.get('turnover', 0)
        
        if turnover >= self.TURNOVER_THRESHOLDS['high']:
            tags.append('💰 资金关注度高')
        elif turnover >= self.TURNOVER_THRESHOLDS['medium']:
            tags.append('📊 成交活跃')
        elif turnover >= self.TURNOVER_THRESHOLDS['low']:
            tags.append('💧 流动性好')
        else:
            tags.append('⚠️ 成交清淡')
        
        return tags
    
    def _generate_change_tags(self, stock: Dict) -> List[str]:
        """生成涨跌幅标签"""
        tags = []
        change_pct = stock.get('change_pct', 0)
        
        if change_pct >= self.CHANGE_THRESHOLDS['surge']:
            tags.append('🚀 强势涨停')
        elif change_pct >= self.CHANGE_THRESHOLDS['rise']:
            tags.append('📈 温和上涨')
        elif change_pct >= self.CHANGE_THRESHOLDS['small_rise']:
            tags.append('↗️ 小幅上涨')
        elif change_pct >= self.CHANGE_THRESHOLDS['small_fall']:
            tags.append('↘️ 小幅下跌')
        elif change_pct >= self.CHANGE_THRESHOLDS['fall']:
            tags.append('📉 温和下跌')
        else:
            tags.append('🔻 大幅下跌')
        
        return tags
    
    def _generate_industry_tags(self, fundamental_data: Dict) -> List[str]:
        """生成行业标签"""
        tags = []
        
        industry = fundamental_data.get('industry', '')
        if industry:
            tags.append(f'🏭 {industry}')
        
        # 热门行业标签
        hot_industries = {
            '半导体': '🔥 半导体',
            '新能源': '⚡ 新能源',
            '白酒': '🍶 白酒',
            '医药': '💊 医药',
            '芯片': '💾 芯片',
            '人工智能': '🤖 AI',
            '5G': '📡 5G',
        }
        
        for keyword, tag in hot_industries.items():
            if keyword in industry:
                tags.append(tag)
                break
        
        return tags
    
    def _generate_technical_tags(self, technical_data: Dict) -> List[str]:
        """生成技术形态标签"""
        tags = []
        
        # 均线形态
        ma5 = technical_data.get('ma5', 0)
        ma20 = technical_data.get('ma20', 0)
        ma60 = technical_data.get('ma60', 0)
        
        if ma5 > ma20 > ma60:
            tags.append('📈 多头排列')
        elif ma5 < ma20 < ma60:
            tags.append('📉 空头排列')
        
        # MACD
        if technical_data.get('macd_golden_cross'):
            tags.append('✨ MACD 金叉')
        elif technical_data.get('macd_dead_cross'):
            tags.append('❌ MACD 死叉')
        
        # RSI
        rsi = technical_data.get('rsi', 50)
        if rsi > 80:
            tags.append('🔥 超买')
        elif rsi < 20:
            tags.append('❄️ 超卖')
        
        # 布林带
        bb_position = technical_data.get('bb_position', 0.5)
        if bb_position > 0.9:
            tags.append('📊 突破上轨')
        elif bb_position < 0.1:
            tags.append('📊 跌破下轨')
        
        # 成交量
        volume_ratio = technical_data.get('volume_ratio', 1)
        if volume_ratio > 2:
            tags.append('📊 放量')
        elif volume_ratio < 0.5:
            tags.append('📊 缩量')
        
        return tags
    
    def _generate_risk_tags(self, stock: Dict, 
                            fundamental_data: Optional[Dict] = None) -> List[str]:
        """生成风险标签"""
        tags = []
        
        # ST 风险
        name = stock.get('name', '')
        if 'ST' in name or '*' in name:
            tags.append('⚠️ ST 股票')
        
        # 高位风险
        change_pct = stock.get('change_pct', 0)
        if change_pct > 50:
            tags.append('⚠️ 高位股')
        elif change_pct > 30:
            tags.append('⚠️ 涨幅较大')
        
        # 流动性风险
        turnover = stock.get('turnover', 0)
        if turnover < 100000000:
            tags.append('⚠️ 流动性差')
        
        # 高估值风险
        if fundamental_data:
            pe = fundamental_data.get('pe_ratio', 0)
            if pe > 100:
                tags.append('⚠️ 高估值')
            elif pe < 0:
                tags.append('⚠️ 亏损股')
            
            pb = fundamental_data.get('pb_ratio', 0)
            if pb > 10:
                tags.append('⚠️ 高 PB')
        
        return tags
    
    def format_tags(self, tags: List[str], max_tags: int = 5, 
                    separator: str = ' | ') -> str:
        """
        格式化标签为字符串
        
        Args:
            tags: 标签列表
            max_tags: 最大标签数
            separator: 分隔符
        
        Returns:
            str: 格式化后的标签字符串
        """
        if not tags:
            return ''
        
        # 限制标签数量
        limited_tags = tags[:max_tags]
        
        return separator.join(limited_tags)


# 测试
if __name__ == '__main__':
    gen = EnhancedTagGenerator()
    
    # 测试数据
    test_stock = {
        'code': '600519',
        'name': '贵州茅台',
        'change_pct': 2.5,
        'turnover': 5000000000,
    }
    
    test_fundamental = {
        'industry': '白酒',
        'pe_ratio': 35.5,
        'pb_ratio': 8.2,
        'roe': 25.3,
    }
    
    test_technical = {
        'ma5': 1800,
        'ma20': 1750,
        'ma60': 1700,
        'macd_golden_cross': True,
        'rsi': 65,
        'bb_position': 0.7,
        'volume_ratio': 1.5,
    }
    
    print("="*80)
    print("🏷️ 增强标签生成器测试")
    print("="*80)
    
    # 生成标签
    tags = gen.generate(test_stock, test_fundamental, test_technical)
    
    print(f"\n{test_stock['code']} {test_stock['name']}:")
    print(f"\n生成的标签:")
    for tag in tags:
        print(f"  {tag}")
    
    print(f"\n格式化标签:")
    formatted = gen.format_tags(tags, max_tags=5)
    print(f"  {formatted}")
    
    # 测试风险标签
    print("\n" + "="*80)
    print("🏷️ 风险标签测试")
    print("="*80)
    
    risk_stocks = [
        {'code': '000001', 'name': '*ST 平安', 'change_pct': 55, 'turnover': 50000000},
        {'code': '300750', 'name': '宁德时代', 'change_pct': 35, 'turnover': 3000000000},
    ]
    
    for stock in risk_stocks:
        tags = gen._generate_risk_tags(stock)
        print(f"\n{stock['code']} {stock['name']}:")
        for tag in tags:
            print(f"  {tag}")
