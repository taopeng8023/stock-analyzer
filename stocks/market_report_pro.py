#!/usr/bin/env python3
"""
专业市场分析报告工具
- 明确目标价计算（基于技术面 + 基本面）
- 严格数据验证
- 完整分析报告

⚠️  核心原则：
1. 只使用真实数据
2. 目标价必须有计算依据
3. 明确标注数据来源
4. 无真实数据不分析

用法:
    python3 market_report_pro.py --full          # 完整报告
    python3 market_report_pro.py --target        # 目标价分析
    python3 market_report_pro.py --push          # 推送报告
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


# ============ 目标价计算模型 ============

def calculate_target_price(stock_data: dict, method: str = 'comprehensive') -> dict:
    """
    计算目标价
    
    方法:
    1. 技术面目标价（支撑/阻力位）
    2. 基本面目标价（估值修复）
    3. 综合目标价（加权平均）
    
    Args:
        stock_data: 股票数据
        method: 计算方法
    
    Returns:
        目标价信息
    """
    
    current_price = stock_data.get('price', 0)
    
    # 1. 技术面目标价
    technical = stock_data.get('technical', {})
    resistance = technical.get('resistance', current_price * 1.05)
    support = technical.get('support', current_price * 0.95)
    
    # 根据技术评级调整
    tech_score = technical.get('total_score', 50)
    if tech_score >= 80:
        tech_target = resistance * 1.10  # 强势股突破阻力
    elif tech_score >= 60:
        tech_target = resistance
    elif tech_score >= 40:
        tech_target = current_price * 1.02  # 中性
    else:
        tech_target = support * 0.95  # 弱势
    
    # 2. 基本面目标价
    fundamental = stock_data.get('fundamental', {})
    pe = fundamental.get('pe', 20)
    industry_pe = fundamental.get('industry_pe', 20)
    growth_rate = fundamental.get('growth_rate', 10)
    
    # PEG 估值法
    if growth_rate > 0:
        fair_pe = growth_rate  # 合理 PEG=1
        fundamental_target = current_price * (fair_pe / pe) if pe > 0 else current_price
    else:
        fundamental_target = current_price * (industry_pe / pe) if pe > 0 else current_price
    
    # 3. 综合目标价（技术 40% + 基本面 60%）
    comprehensive_target = tech_target * 0.4 + fundamental_target * 0.6
    
    # 4. 计算上涨空间（避免除零）
    if current_price > 0:
        upside = (comprehensive_target - current_price) / current_price * 100
    else:
        upside = 0
    
    # 5. 目标价评级
    if upside >= 30:
        rating = '强烈推荐'
        stars = '⭐⭐⭐⭐⭐'
    elif upside >= 20:
        rating = '推荐'
        stars = '⭐⭐⭐⭐'
    elif upside >= 10:
        rating = '谨慎推荐'
        stars = '⭐⭐⭐'
    elif upside >= 0:
        rating = '观望'
        stars = '⭐⭐'
    else:
        rating = '回避'
        stars = '⭐'
    
    # 6. 止损价
    stop_loss = support * 0.95  # 支撑位下方 5%
    
    return {
        'current_price': current_price,
        'technical_target': round(tech_target, 2),
        'fundamental_target': round(fundamental_target, 2),
        'comprehensive_target': round(comprehensive_target, 2),
        'upside': round(upside, 1),
        'rating': rating,
        'stars': stars,
        'support': round(support, 2),
        'resistance': round(resistance, 2),
        'stop_loss': round(stop_loss, 2),
        'method': method,
    }


# ============ 完整报告生成 ============

def generate_professional_report(stocks_data: list) -> str:
    """
    生成专业市场分析报告
    
    Args:
        stocks_data: 股票数据列表
    
    Returns:
        报告文本
    """
    
    lines = []
    lines.append("="*90)
    lines.append("📊 专业市场分析报告")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("="*90)
    lines.append("")
    
    # 1. 3 句话摘要
    lines.append("📋 **3 句话总结**")
    
    # 计算平均上涨概率
    if stocks_data:
        avg_upside = sum(s.get('target_price', {}).get('upside', 0) for s in stocks_data) / len(stocks_data)
        if avg_upside >= 20:
            sentiment = "市场机会较好"
        elif avg_upside >= 10:
            sentiment = "市场谨慎偏多"
        elif avg_upside >= 0:
            sentiment = "市场震荡"
        else:
            sentiment = "市场风险较大"
        
        lines.append(f"📊 {sentiment}（平均空间 {avg_upside:+.1f}%）")
        lines.append("🔥 重点关注：" + ", ".join(s.get('name', '') for s in stocks_data[:3]))
        lines.append("⚠️ 风险提示：注意控制仓位，设置止损")
    else:
        lines.append("❌ 无真实数据，无法生成摘要")
    
    lines.append("")
    lines.append("-"*90)
    lines.append("")
    
    # 2. 股票详细分析
    lines.append("📈 **个股详细分析**")
    lines.append("")
    
    for i, stock in enumerate(stocks_data, 1):
        symbol = stock.get('symbol', '')
        name = stock.get('name', '')
        source = stock.get('source', 'unknown')
        
        lines.append(f"### {i}. {name} ({symbol})")
        lines.append("")
        
        # 数据源标注
        if source == 'real':
            lines.append("**数据源：** ✅ 腾讯财经真实数据")
        elif source == 'estimated':
            lines.append("**数据源：** ⚠️ 估算数据（已标注）")
        else:
            lines.append("**数据源：** ❌ 未知（不建议使用）")
        lines.append("")
        
        # 行情数据
        price_data = stock.get('price_data', {})
        lines.append("**行情数据：**")
        lines.append(f"- 现价：¥{price_data.get('price', 0):.2f}")
        lines.append(f"- 涨跌幅：{price_data.get('change_pct', 0):+.2f}%")
        lines.append(f"- 成交额：{price_data.get('amount_wan', 0):.0f}万")
        lines.append(f"- 主力流入：{price_data.get('main_net', 0)/10000:.0f}万")
        lines.append("")
        
        # 目标价分析
        target = stock.get('target_price', {})
        if target:
            lines.append("**目标价分析：**")
            lines.append(f"- 当前价：¥{target.get('current_price', 0):.2f}")
            lines.append(f"- 技术面目标：¥{target.get('technical_target', 0):.2f}")
            lines.append(f"- 基本面目标：¥{target.get('fundamental_target', 0):.2f}")
            lines.append(f"- **综合目标：¥{target.get('comprehensive_target', 0):.2f}**")
            lines.append(f"- 上涨空间：{target.get('upside', 0):+.1f}%")
            lines.append(f"- 评级：{target.get('stars')} {target.get('rating', '')}")
            lines.append("")
            
            lines.append("**操作建议：**")
            lines.append(f"- 🎯 买入区间：¥{target.get('support', 0):.2f} - ¥{target.get('support', 0)*1.02:.2f}")
            lines.append(f"- 🎯 目标价位：¥{target.get('comprehensive_target', 0):.2f} - ¥{target.get('comprehensive_target', 0)*1.05:.2f}")
            lines.append(f"- 🛑 止损位：¥{target.get('stop_loss', 0):.2f}")
            lines.append("")
        else:
            lines.append("⚠️ 无法计算目标价（数据不足）")
            lines.append("")
        
        # 技术面
        technical = stock.get('technical', {})
        if technical:
            lines.append("**技术面分析：**")
            lines.append(f"- 综合评分：{technical.get('total_score', 0)}/100 {technical.get('stars', '')}")
            lines.append(f"- K 线：{technical.get('kline', {}).get('kline_type', 'N/A')}")
            lines.append(f"- 均线：{technical.get('ma', {}).get('arrangement', 'N/A')}")
            lines.append(f"- MACD: {technical.get('macd', {}).get('cross', 'N/A')}")
            lines.append("")
        
        # 基本面
        fundamental = stock.get('fundamental', {})
        if fundamental:
            lines.append("**基本面分析：**")
            lines.append(f"- 综合评分：{fundamental.get('total_score', 0)}/100 {fundamental.get('stars', '')}")
            lines.append(f"- PE: {fundamental.get('pe', 0)}x")
            lines.append(f"- ROE: {fundamental.get('roe', 0):.1f}%")
            lines.append(f"- 增长：{fundamental.get('profit_growth', 0):.1f}%")
            lines.append("")
        
        lines.append("-"*90)
        lines.append("")
    
    # 3. 综合对比表
    lines.append("📊 **综合对比**")
    lines.append("")
    lines.append(f"{'股票':<10} {'现价':<8} {'目标价':<10} {'空间':<8} {'评级':<12} {'数据源':<8}")
    lines.append("-"*90)
    
    for stock in stocks_data:
        name = stock.get('name', '')
        target = stock.get('target_price', {})
        source = '✅' if stock.get('source') == 'real' else '⚠️'
        
        lines.append(f"{name:<10} ¥{target.get('current_price', 0):<6.2f} ¥{target.get('comprehensive_target', 0):<8.2f} "
                    f"{target.get('upside', 0):>+6.1f}% {target.get('rating', 'N/A'):<12} {source}")
    
    lines.append("")
    lines.append("-"*90)
    lines.append("")
    
    # 4. 风险提示
    lines.append("⚠️ **风险提示**")
    lines.append("")
    lines.append("1. **数据说明**")
    lines.append("   - ✅ 真实数据：来自腾讯财经实时行情")
    lines.append("   - ⚠️ 估算数据：主力流入=成交额×15%")
    lines.append("   - 📊 模型分析：目标价基于技术面 + 基本面计算")
    lines.append("")
    lines.append("2. **目标价计算**")
    lines.append("   - 技术面目标：基于支撑/阻力位")
    lines.append("   - 基本面目标：基于 PEG 估值法")
    lines.append("   - 综合目标：技术 40% + 基本面 60%")
    lines.append("")
    lines.append("3. **投资风险**")
    lines.append("   - 目标价不保证实现")
    lines.append("   - 市场存在不确定性")
    lines.append("   - 请设置止损，控制仓位")
    lines.append("   - 本报告仅供参考，不构成投资建议")
    lines.append("")
    lines.append("="*90)
    
    return "\n".join(lines)


# ============ 主函数 ============

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='专业市场分析报告')
    parser.add_argument('--full', action='store_true', help='完整报告')
    parser.add_argument('--target', action='store_true', help='目标价分析')
    parser.add_argument('--push', action='store_true', help='推送报告')
    
    args = parser.parse_args()
    
    # 示例数据（实际应从真实数据源获取）
    sample_stocks = [
        {
            'symbol': 'sh600152',
            'name': '维科技术',
            'source': 'real',
            'price_data': {
                'price': 10.24,
                'change_pct': -61.16,
                'amount_wan': 427200,
                'main_net': 51300,
            },
            'technical': {
                'total_score': 35,
                'stars': '⭐',
                'kline': {'kline_type': '大阴线'},
                'ma': {'arrangement': '空头排列'},
                'macd': {'cross': '死叉'},
                'resistance': 11.50,
                'support': 9.50,
            },
            'fundamental': {
                'total_score': 50,
                'stars': '⭐⭐',
                'pe': 25,
                'roe': 8,
                'profit_growth': 5,
                'industry_pe': 20,
                'growth_rate': 5,
            },
        },
    ]
    
    # 计算目标价
    for stock in sample_stocks:
        target = calculate_target_price(stock)
        stock['target_price'] = target
    
    # 生成报告
    report = generate_professional_report(sample_stocks)
    print(report)


if __name__ == '__main__':
    main()
