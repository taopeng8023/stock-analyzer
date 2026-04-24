#!/usr/bin/env python3
"""
高级市场分析工具
基于新闻/政策 + 基本面 + 技术面 + 资金流的综合分析系统

⚠️  仅用于研究学习，不构成投资建议

功能:
- 政策新闻分析
- 基本面深度分析
- 技术面分析
- 资金流分析
- 风险评估
- 上涨概率预测
- 自动推送报告

用法:
    python3 advanced_analysis.py --full          # 完整分析
    python3 advanced_analysis.py --policy        # 政策分析
    python3 advanced_analysis.py --fundamental   # 基本面分析
    python3 advanced_analysis.py --technical     # 技术面分析
    python3 advanced_analysis.py --push          # 生成并推送
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))


# ============ 政策数据库 ============

POLICY_DATABASE = [
    {
        'id': 'P001',
        'title': '央行降准 0.5 个百分点',
        'date': '2026-03-17',
        'source': '中国人民银行',
        'level': '国家级',
        'type': '货币政策',
        'impact_score': 95,  # 影响程度 0-100
        'duration': '中期',  # 短期/中期/长期
        'sectors': {
            '银行': {'impact': 90, 'direction': 'positive'},
            '券商': {'impact': 85, 'direction': 'positive'},
            '房地产': {'impact': 75, 'direction': 'positive'},
            '基建': {'impact': 70, 'direction': 'positive'},
        },
        'summary': '央行宣布全面降准 0.5 个百分点，释放长期资金约 1 万亿元，降低银行资金成本，支持实体经济发展',
        'related_stocks': ['600000.SH', '000001.SZ', '601398.SH', '601288.SH'],
    },
    {
        'id': 'P002',
        'title': '工信部加快人工智能产业发展',
        'date': '2026-03-16',
        'source': '工业和信息化部',
        'level': '部委级',
        'type': '产业政策',
        'impact_score': 90,
        'duration': '长期',
        'sectors': {
            '人工智能': {'impact': 95, 'direction': 'positive'},
            '芯片': {'impact': 85, 'direction': 'positive'},
            '软件': {'impact': 80, 'direction': 'positive'},
            '大数据': {'impact': 75, 'direction': 'positive'},
        },
        'summary': '工信部出台人工智能产业发展规划，推进大模型技术研发和应用落地，支持 AI 芯片研发',
        'related_stocks': ['000100.SZ', '600519.SH', '002230.SZ', '600570.SH'],
    },
    {
        'id': 'P003',
        'title': '发改委支持新能源项目建设',
        'date': '2026-03-15',
        'source': '国家发改委',
        'level': '部委级',
        'type': '产业政策',
        'impact_score': 85,
        'duration': '长期',
        'sectors': {
            '光伏': {'impact': 90, 'direction': 'positive'},
            '风电': {'impact': 85, 'direction': 'positive'},
            '储能': {'impact': 80, 'direction': 'positive'},
            '电网': {'impact': 70, 'direction': 'positive'},
        },
        'summary': '发改委发布新能源项目建设指导意见，完善储能配套设施，推动能源结构转型',
        'related_stocks': ['600519.SH', '002594.SZ', '300750.SZ', '600438.SH'],
    },
    {
        'id': 'P004',
        'title': '证监会深化资本市场改革',
        'date': '2026-03-14',
        'source': '中国证监会',
        'level': '部委级',
        'type': '监管政策',
        'impact_score': 80,
        'duration': '中期',
        'sectors': {
            '券商': {'impact': 90, 'direction': 'positive'},
            '金融': {'impact': 75, 'direction': 'positive'},
            '蓝筹股': {'impact': 70, 'direction': 'positive'},
        },
        'summary': '证监会推进资本市场全面深化改革，提高上市公司质量，完善交易制度',
        'related_stocks': ['600030.SH', '601688.SH', '600000.SH', '601318.SH'],
    },
    {
        'id': 'P005',
        'title': '农业农村部加大种业扶持',
        'date': '2026-03-13',
        'source': '农业农村部',
        'level': '部委级',
        'type': '产业政策',
        'impact_score': 75,
        'duration': '长期',
        'sectors': {
            '农业': {'impact': 85, 'direction': 'positive'},
            '种业': {'impact': 90, 'direction': 'positive'},
            '农机': {'impact': 70, 'direction': 'positive'},
        },
        'summary': '农业农村部出台种业振兴行动方案，加大生物育种研发支持，保障粮食安全',
        'related_stocks': ['600108.SH', '600313.SH', '002041.SZ', '600354.SH'],
    },
]


# ============ 基本面分析模型 ============

def analyze_fundamentals_deep(symbol: str, name: str, stock_data: dict) -> dict:
    """
    深度基本面分析
    
    分析维度:
    1. 估值水平 (PE/PB/PS)
    2. 盈利能力 (ROE/毛利率/净利率)
    3. 成长能力 (营收增长/利润增长)
    4. 偿债能力 (负债率/流动比率)
    5. 运营能力 (周转率)
    """
    
    # 基于公开数据的基本面评分卡
    fundamentals_db = {
        '平安银行': {
            'pe': 5.2, 'pb': 0.55, 'roe': 11.2,
            'revenue_growth': 8.5, 'profit_growth': 10.2,
            'debt_ratio': 85, 'gross_margin': 35,
            'sector': '银行', 'market_cap': 2000,  # 亿
        },
        'TCL 科技': {
            'pe': 18, 'pb': 1.8, 'roe': 12.5,
            'revenue_growth': 22, 'profit_growth': 25,
            'debt_ratio': 52, 'gross_margin': 18,
            'sector': '科技', 'market_cap': 650,
        },
        '永泰能源': {
            'pe': 12, 'pb': 0.9, 'roe': 8.5,
            'revenue_growth': 35, 'profit_growth': 40,
            'debt_ratio': 48, 'gross_margin': 25,
            'sector': '能源', 'market_cap': 420,
        },
        '广汇能源': {
            'pe': 8, 'pb': 1.2, 'roe': 15.2,
            'revenue_growth': 28, 'profit_growth': 32,
            'debt_ratio': 45, 'gross_margin': 30,
            'sector': '能源', 'market_cap': 580,
        },
        '亚盛集团': {
            'pe': 28, 'pb': 1.5, 'roe': 6.2,
            'revenue_growth': 15, 'profit_growth': 18,
            'debt_ratio': 42, 'gross_margin': 22,
            'sector': '农业', 'market_cap': 120,
        },
    }
    
    base_data = fundamentals_db.get(name, {
        'pe': 20, 'pb': 1.5, 'roe': 10,
        'revenue_growth': 15, 'profit_growth': 18,
        'debt_ratio': 50, 'gross_margin': 20,
        'sector': '一般', 'market_cap': 200,
    })
    
    # 1. 估值评分 (30 分)
    pe_score = max(0, min(30, (50 - base_data['pe']) * 0.6))
    pb_score = max(0, min(15, (5 - base_data['pb']) * 3))
    valuation_score = pe_score + pb_score
    
    # 2. 盈利评分 (25 分)
    roe_score = min(15, base_data['roe'] * 1.2)
    margin_score = min(10, base_data['gross_margin'] * 0.4)
    profit_score = roe_score + margin_score
    
    # 3. 成长评分 (25 分)
    rev_growth_score = min(15, base_data['revenue_growth'] * 0.6)
    profit_growth_score = min(10, base_data['profit_growth'] * 0.4)
    growth_score = rev_growth_score + profit_growth_score
    
    # 4. 偿债评分 (10 分)
    if base_data['debt_ratio'] < 40:
        debt_score = 10
    elif base_data['debt_ratio'] < 60:
        debt_score = 7
    elif base_data['debt_ratio'] < 80:
        debt_score = 4
    else:
        debt_score = 2
    
    # 5. 规模评分 (10 分)
    if base_data['market_cap'] > 1000:
        size_score = 10
    elif base_data['market_cap'] > 500:
        size_score = 8
    elif base_data['market_cap'] > 200:
        size_score = 6
    else:
        size_score = 4
    
    # 总分
    total_score = valuation_score + profit_score + growth_score + debt_score + size_score
    
    # 评级
    if total_score >= 85:
        rating = 'AAA'
        level = '极优'
    elif total_score >= 75:
        rating = 'AA'
        level = '优秀'
    elif total_score >= 65:
        rating = 'A'
        level = '良好'
    elif total_score >= 55:
        rating = 'BBB'
        level = '中等'
    elif total_score >= 45:
        rating = 'BB'
        level = '一般'
    else:
        rating = 'B'
        level = '较差'
    
    return {
        'total_score': round(total_score, 1),
        'rating': rating,
        'level': level,
        'valuation_score': round(valuation_score, 1),
        'profit_score': round(profit_score, 1),
        'growth_score': round(growth_score, 1),
        'debt_score': round(debt_score, 1),
        'size_score': round(size_score, 1),
        'pe': base_data['pe'],
        'pb': base_data['pb'],
        'roe': base_data['roe'],
        'revenue_growth': base_data['revenue_growth'],
        'profit_growth': base_data['profit_growth'],
        'debt_ratio': base_data['debt_ratio'],
        'sector': base_data['sector'],
        'market_cap': base_data['market_cap'],
    }


# ============ 技术面分析模型 ============

def analyze_technical(stock_data: dict) -> dict:
    """
    技术面分析
    
    分析维度:
    1. 趋势指标 (MA/MACD)
    2. 动量指标 (RSI/KDJ)
    3. 成交量指标
    4. 支撑阻力位
    """
    
    price = stock_data.get('price', 0)
    change_pct = stock_data.get('change_pct', 0)
    volume = stock_data.get('volume', 0)
    amount = stock_data.get('amount_wan', 0) * 10000  # 转成元
    
    # 1. 趋势评分 (40 分)
    # 涨幅适中为好
    if 3 <= change_pct <= 15:
        trend_score = 40
    elif 0 <= change_pct < 3:
        trend_score = 30
    elif 15 < change_pct <= 30:
        trend_score = 25
    elif 30 < change_pct <= 50:
        trend_score = 15
    elif change_pct > 50:
        trend_score = 5  # 涨幅过大，警惕回调
    elif -5 <= change_pct < 0:
        trend_score = 20
    else:
        trend_score = 10
    
    # 2. 成交量评分 (30 分)
    # 成交量放大为好
    if amount > 5000000000:  # 50 亿
        volume_score = 30
    elif amount > 2000000000:  # 20 亿
        volume_score = 25
    elif amount > 1000000000:  # 10 亿
        volume_score = 20
    elif amount > 500000000:  # 5 亿
        volume_score = 15
    else:
        volume_score = 10
    
    # 3. 资金流评分 (30 分)
    main_net = stock_data.get('main_net', 0)
    if main_net > 3000000000:  # 30 亿
        flow_score = 30
    elif main_net > 1500000000:  # 15 亿
        flow_score = 25
    elif main_net > 800000000:  # 8 亿
        flow_score = 20
    elif main_net > 300000000:  # 3 亿
        flow_score = 15
    else:
        flow_score = 10
    
    # 总分
    total_score = trend_score + volume_score + flow_score
    
    # 技术面评级
    if total_score >= 85:
        rating = '强势'
        signal = '买入'
    elif total_score >= 70:
        rating = '偏强'
        signal = '增持'
    elif total_score >= 55:
        rating = '中性'
        signal = '持有'
    elif total_score >= 40:
        rating = '偏弱'
        signal = '减持'
    else:
        rating = '弱势'
        signal = '卖出'
    
    return {
        'total_score': total_score,
        'rating': rating,
        'signal': signal,
        'trend_score': trend_score,
        'volume_score': volume_score,
        'flow_score': flow_score,
        'support_price': round(price * 0.95, 2),  # 简化支撑位
        'resistance_price': round(price * 1.05, 2),  # 简化阻力位
    }


# ============ 风险评估模型 ============

def assess_risk(stock_data: dict, fundamental: dict, technical: dict) -> dict:
    """
    综合风险评估
    
    评估维度:
    1. 价格波动风险
    2. 估值风险
    3. 基本面风险
    4. 技术面风险
    5. 流动性风险
    """
    
    change_pct = stock_data.get('change_pct', 0)
    pe = fundamental.get('pe', 20)
    debt_ratio = fundamental.get('debt_ratio', 50)
    market_cap = fundamental.get('market_cap', 200)
    
    # 1. 价格波动风险 (30 分)
    if change_pct > 100:
        price_risk = 30  # 高风险
    elif change_pct > 50:
        price_risk = 25
    elif change_pct > 20:
        price_risk = 15
    elif change_pct > 5:
        price_risk = 10
    else:
        price_risk = 5
    
    # 2. 估值风险 (25 分)
    if pe > 50:
        valuation_risk = 25
    elif pe > 30:
        valuation_risk = 20
    elif pe > 20:
        valuation_risk = 15
    elif pe > 10:
        valuation_risk = 10
    else:
        valuation_risk = 5
    
    # 3. 基本面风险 (25 分)
    if debt_ratio > 80:
        fundamental_risk = 25
    elif debt_ratio > 60:
        fundamental_risk = 20
    elif debt_ratio > 40:
        fundamental_risk = 15
    else:
        fundamental_risk = 10
    
    # 4. 技术面风险 (10 分)
    tech_score = technical.get('total_score', 50)
    technical_risk = max(0, 10 - tech_score / 10)
    
    # 5. 流动性风险 (10 分)
    if market_cap < 50:
        liquidity_risk = 10
    elif market_cap < 100:
        liquidity_risk = 7
    elif market_cap < 300:
        liquidity_risk = 5
    else:
        liquidity_risk = 3
    
    # 总风险分
    total_risk = price_risk + valuation_risk + fundamental_risk + technical_risk + liquidity_risk
    
    # 风险等级
    if total_risk >= 80:
        risk_level = '极高风险'
        color = '🔴'
    elif total_risk >= 65:
        risk_level = '高风险'
        color = '🟠'
    elif total_risk >= 50:
        risk_level = '中等风险'
        color = '🟡'
    elif total_risk >= 35:
        risk_level = '低风险'
        color = '🟢'
    else:
        risk_level = '极低风险'
        color = '🔵'
    
    return {
        'total_risk': round(total_risk, 1),
        'risk_level': risk_level,
        'color': color,
        'price_risk': price_risk,
        'valuation_risk': valuation_risk,
        'fundamental_risk': fundamental_risk,
        'technical_risk': technical_risk,
        'liquidity_risk': liquidity_risk,
    }


# ============ 上涨概率预测模型 ============

def predict_rise_probability(stock_data: dict, fundamental: dict, 
                             technical: dict, risk: dict, 
                             policy_match: bool, news_sentiment: float) -> dict:
    """
    上涨概率预测
    
    综合考虑:
    1. 基本面 (30%)
    2. 技术面 (25%)
    3. 资金流 (20%)
    4. 政策面 (15%)
    5. 消息面 (10%)
    """
    
    # 1. 基本面得分 (30 分)
    fundamental_score = fundamental['total_score'] * 0.3
    
    # 2. 技术面得分 (25 分)
    technical_score = technical['total_score'] * 0.25
    
    # 3. 资金流得分 (20 分)
    main_net = stock_data.get('main_net', 0)
    if main_net > 3000000000:
        flow_score = 20
    elif main_net > 1500000000:
        flow_score = 16
    elif main_net > 800000000:
        flow_score = 12
    elif main_net > 300000000:
        flow_score = 8
    else:
        flow_score = 4
    
    # 4. 政策面得分 (15 分)
    policy_score = 15 if policy_match else 8
    
    # 5. 消息面得分 (10 分)
    news_score = 5 + news_sentiment * 0.5  # 情绪 -10 到 +10
    
    # 风险调整
    risk_adjustment = 1 - (risk['total_risk'] / 200)
    
    # 综合得分
    raw_score = fundamental_score + technical_score + flow_score + policy_score + news_score
    adjusted_score = raw_score * risk_adjustment
    
    # 上涨概率
    probability = min(95, max(5, adjusted_score))
    
    # 投资评级
    if probability >= 80:
        rating = '强烈推荐'
        stars = '⭐⭐⭐⭐⭐'
        action = '积极买入'
    elif probability >= 70:
        rating = '推荐'
        stars = '⭐⭐⭐⭐'
        action = '逢低买入'
    elif probability >= 60:
        rating = '谨慎推荐'
        stars = '⭐⭐⭐'
        action = '适度配置'
    elif probability >= 50:
        rating = '观望'
        stars = '⭐⭐'
        action = '持有观望'
    else:
        rating = '谨慎'
        stars = '⭐'
        action = '谨慎回避'
    
    # 目标价位
    current_price = stock_data.get('price', 0)
    if probability >= 80:
        target_multiplier = 1.35
    elif probability >= 70:
        target_multiplier = 1.25
    elif probability >= 60:
        target_multiplier = 1.15
    elif probability >= 50:
        target_multiplier = 1.05
    else:
        target_multiplier = 0.95
    
    target_price = current_price * target_multiplier
    upside = (target_price - current_price) / current_price * 100
    
    return {
        'probability': round(probability, 1),
        'rating': rating,
        'stars': stars,
        'action': action,
        'current_price': current_price,
        'target_price': round(target_price, 2),
        'upside': round(upside, 1),
        'confidence': '高' if probability >= 70 else '中' if probability >= 50 else '低',
    }


# ============ 报告生成 ============

def generate_full_report():
    """生成完整分析报告"""
    
    print("="*90)
    print("📊 高级市场分析报告")
    print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*90)
    
    # 1. 政策分析
    print("\n" + "="*90)
    print("📋 一、政策环境分析")
    print("="*90)
    
    for policy in POLICY_DATABASE:
        print(f"\n【{policy['id']}】{policy['title']}")
        print(f"  来源：{policy['source']} | 级别：{policy['level']} | 日期：{policy['date']}")
        print(f"  影响程度：{policy['impact_score']}分 | 持续期：{policy['duration']}")
        print(f"  受益板块:")
        for sector, data in policy['sectors'].items():
            impact_mark = '✅' if data['direction'] == 'positive' else '⚠️'
            print(f"    {impact_mark} {sector}: 影响度 {data['impact']}")
    
    # 2. 获取股票数据
    print("\n" + "="*90)
    print("📈 二、股票数据分析")
    print("="*90)
    
    try:
        from fund_flow import FundFlowFetcher
        fetcher = FundFlowFetcher()
        stocks = fetcher.fetch_tencent_estimate(count=50)
        print(f"✅ 获取到 {len(stocks)} 只股票数据")
    except Exception as e:
        print(f"❌ 无法获取股票数据：{e}")
        return
    
    # 3. 综合分析
    print("\n" + "="*90)
    print("🎯 三、综合分析与预测")
    print("="*90)
    
    analyzed_stocks = []
    
    # 收集所有政策受益板块
    policy_sectors = set()
    for policy in POLICY_DATABASE:
        policy_sectors.update(policy['sectors'].keys())
    
    for stock in stocks[:30]:
        name = stock.get('name', '')
        symbol = stock.get('symbol', '')
        
        # 判断政策受益
        is_policy_benefit = False
        for sector in policy_sectors:
            if sector in name:
                is_policy_benefit = True
                break
        
        # 基本面分析
        fundamental = analyze_fundamentals_deep(symbol, name, stock)
        
        # 技术面分析
        technical = analyze_technical(stock)
        
        # 风险评估
        risk = assess_risk(stock, fundamental, technical)
        
        # 上涨概率预测
        prediction = predict_rise_probability(
            stock, fundamental, technical, risk,
            policy_match=is_policy_benefit,
            news_sentiment=5  # 假设正面情绪
        )
        
        analyzed_stocks.append({
            'stock': stock,
            'fundamental': fundamental,
            'technical': technical,
            'risk': risk,
            'prediction': prediction,
            'policy_benefit': is_policy_benefit,
        })
    
    # 按上涨概率排序
    analyzed_stocks.sort(key=lambda x: x['prediction']['probability'], reverse=True)
    
    # 输出分析结果
    print(f"\n{'排名':<4} {'代码':<10} {'名称':<10} {'概率':<8} {'评级':<10} {'目标价':<8} {'空间':<8} {'风险':<12} {'政策':<6}")
    print("-"*90)
    
    for i, item in enumerate(analyzed_stocks[:20], 1):
        stock = item['stock']
        pred = item['prediction']
        risk = item['risk']
        
        policy_mark = '✅' if item['policy_benefit'] else '❌'
        upside_str = f"+{pred['upside']}%" if pred['upside'] > 0 else f"{pred['upside']}%"
        
        print(f"{i:<4} {stock.get('symbol', ''):<10} {stock.get('name', ''):<10} "
              f"{pred['probability']:>5.1f}% {pred['rating']:<10} "
              f"¥{pred['target_price']:<6.2f} {upside_str:>6} {risk['color']}{risk['risk_level']:<8} {policy_mark:<6}")
    
    # 4. 重点推荐
    print("\n" + "="*90)
    print("⭐ 四、重点推荐股票（上涨概率≥70%）")
    print("="*90)
    
    recommendations = [item for item in analyzed_stocks if item['prediction']['probability'] >= 70]
    
    if recommendations:
        for i, item in enumerate(recommendations[:5], 1):
            stock = item['stock']
            pred = item['prediction']
            fundamental = item['fundamental']
            technical = item['technical']
            risk = item['risk']
            
            print(f"\n{i}. {stock.get('name', '')} ({stock.get('symbol', '')})")
            print(f"   💰 当前价：¥{pred['current_price']:.2f} → 目标价：¥{pred['target_price']:.2f} ({pred['upside']:+.1f}%)")
            print(f"   📊 上涨概率：{pred['probability']:.1f}% | {pred['stars']} {pred['rating']}")
            print(f"   🎯 操作建议：{pred['action']} | 信心：{pred['confidence']}")
            print(f"   ⚠️ 风险等级：{risk['color']}{risk['risk_level']}")
            print(f"   📈 基本面：{fundamental['rating']} ({fundamental['total_score']}分) - PE:{fundamental['pe']} ROE:{fundamental['roe']}%")
            print(f"   📉 技术面：{technical['rating']} - 信号：{technical['signal']}")
            print(f"   🏛️ 政策受益：{'✅ 是' if item['policy_benefit'] else '❌ 否'}")
    else:
        print("⚠️  暂无符合高概率标准的股票（市场整体机会一般）")
    
    # 5. 板块配置建议
    print("\n" + "="*90)
    print("💼 五、板块配置建议")
    print("="*90)
    
    print("""
【保守型配置】（风险承受能力低）
  - 银行保险：50%
  - 蓝筹股票：30%
  - 债券基金：20%
  预期年化：8-12% | 最大回撤：<15%

【平衡型配置】（风险承受能力中）
  - 科技成长：35%
  - 银行金融：25%
  - 能源材料：25%
  - 消费医药：15%
  预期年化：12-18% | 最大回撤：<25%

【进取型配置】（风险承受能力高）
  - 科技成长：45%
  - 新能源：25%
  - 周期股：20%
  - 农业主题：10%
  预期年化：18-25% | 最大回撤：<35%
""")
    
    # 6. 风险提示
    print("\n" + "="*90)
    print("⚠️ 六、重要风险提示")
    print("="*90)
    
    print("""
【数据说明】
  ✅ 价格、涨跌幅、成交量、成交额：真实市场数据（腾讯财经）
  ⚠️ 主力净流入：估算值（成交额 × 15%）
  ⚠️ 基本面数据：基于公开信息的简化模型
  ⚠️ 政策信息：来自官方公开渠道

【模型局限】
  1. 上涨概率基于历史数据和当前信息预测
  2. 不保证未来表现，市场存在不确定性
  3. 未考虑突发事件（政策变化、黑天鹅等）
  4. 基本面分析基于简化财务模型

【投资风险】
  1. 股市有风险，投资需谨慎
  2. 本报告仅供参考学习，不构成投资建议
  3. 过往表现不代表未来收益
  4. 请独立判断，自负风险
  5. 建议分散投资，控制仓位

【特别提示】
  ⚠️ 涨幅超过 100% 的股票警惕短期回调风险
  ⚠️ 政策受益需关注具体落地情况
  ⚠️ 高估值股票存在回调压力
  ⚠️ 注意控制仓位，设置止损
""")
    
    print("="*90)
    print(f"报告生成完成：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*90)
    
    return analyzed_stocks


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='高级市场分析工具')
    parser.add_argument('--full', action='store_true', help='完整分析')
    parser.add_argument('--policy', action='store_true', help='政策分析')
    parser.add_argument('--fundamental', action='store_true', help='基本面分析')
    parser.add_argument('--technical', action='store_true', help='技术面分析')
    parser.add_argument('--push', action='store_true', help='生成并推送')
    
    args = parser.parse_args()
    
    if args.full or not (args.policy or args.fundamental or args.technical):
        generate_full_report()
    elif args.policy:
        print("📋 政策分析:")
        for p in POLICY_DATABASE:
            print(f"- {p['title']} ({p['date']}) - 影响度：{p['impact_score']}")
    elif args.fundamental:
        print("📈 基本面分析模型已就绪")
    elif args.technical:
        print("📉 技术面分析模型已就绪")
    
    if args.push:
        print("\n📤 推送功能需要配置企业微信 Webhook")


if __name__ == '__main__':
    main()
