#!/usr/bin/env python3
"""
市场新闻分析与股票预测
基于公开新闻、政策、行业动态分析潜在上涨股票

⚠️  仅用于研究学习，不构成投资建议

用法:
    python3 market_analysis.py --news          # 分析最新财经新闻
    python3 market_analysis.py --policy        # 分析政策利好
    python3 market_analysis.py --industry      # 分析行业动态
    python3 market_analysis.py --all           # 综合分析
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

# 尝试导入 web_search
try:
    from web_search import web_search
    HAS_SEARCH = True
except ImportError:
    HAS_SEARCH = False
    print("⚠️  web_search 不可用，使用备用方案")


def search_market_news(keyword: str, count: int = 10):
    """搜索市场新闻"""
    if not HAS_SEARCH:
        return search_news_backup(keyword, count)
    
    try:
        results = web_search(
            query=keyword,
            count=count,
            freshness="day"
        )
        return results
    except Exception as e:
        print(f"搜索失败：{e}")
        return search_news_backup(keyword, count)


def search_news_backup(keyword: str, count: int = 10):
    """备用新闻搜索（模拟）"""
    # 返回预设的热点新闻
    news_templates = {
        '股票': [
            {'title': 'A 股市场今日放量上涨，成交量突破万亿', 'url': 'http://example.com/1', 'snippet': '今日 A 股三大指数集体上涨...'},
            {'title': '北向资金连续 3 日净流入，外资看好 A 股', 'url': 'http://example.com/2', 'snippet': '北向资金今日净流入超 50 亿元...'},
        ],
        '政策': [
            {'title': '央行降准降息，释放流动性支持实体经济', 'url': 'http://example.com/3', 'snippet': '中国人民银行宣布下调存款准备金率...'},
            {'title': '证监会出台新规，支持资本市场健康发展', 'url': 'http://example.com/4', 'snippet': '证监会发布多项资本市场改革措施...'},
        ],
        '科技': [
            {'title': '人工智能产业迎来政策利好，多股涨停', 'url': 'http://example.com/5', 'snippet': '工信部发布人工智能产业发展规划...'},
            {'title': '芯片国产化加速，半导体板块走强', 'url': 'http://example.com/6', 'snippet': '国产芯片企业获大额订单...'},
        ],
    }
    
    return news_templates.get(keyword, news_templates['股票'])[:count]


def analyze_news_sentiment(news_list: list) -> dict:
    """分析新闻情绪"""
    if not news_list:
        return {'positive': 0, 'neutral': 0, 'negative': 0, 'score': 0}
    
    positive_keywords = ['上涨', '利好', '增长', '突破', '创新高', '净流入', '放量', '涨停', '支持', '发展']
    negative_keywords = ['下跌', '利空', '下降', '跌破', '净流出', '缩量', '跌停', '风险', '警告', '处罚']
    
    positive_count = 0
    negative_count = 0
    
    for news in news_list:
        title = news.get('title', '') + news.get('snippet', '')
        
        for kw in positive_keywords:
            if kw in title:
                positive_count += 1
                break
        
        for kw in negative_keywords:
            if kw in title:
                negative_count += 1
                break
    
    total = len(news_list)
    score = (positive_count - negative_count) / total * 100
    
    return {
        'positive': positive_count,
        'negative': negative_count,
        'neutral': total - positive_count - negative_count,
        'score': score,
        'total': total
    }


def analyze_policy_benefits():
    """分析政策利好板块"""
    print("\n" + "="*70)
    print("📋 政策利好分析")
    print("="*70)
    
    # 搜索政策新闻
    news = search_market_news('A 股 政策利好 2026', count=5)
    
    if news:
        print(f"\n最新政策新闻:")
        for i, n in enumerate(news[:5], 1):
            print(f"{i}. {n.get('title', 'N/A')}")
            print(f"   {n.get('snippet', '')[:100]}...")
        
        # 分析情绪
        sentiment = analyze_news_sentiment(news)
        print(f"\n政策情绪分析:")
        print(f"  利好：{sentiment['positive']} 条")
        print(f"  利空：{sentiment['negative']} 条")
        print(f"  中性：{sentiment['neutral']} 条")
        print(f"  情绪得分：{sentiment['score']:+.1f}分")
    
    # 受益板块分析
    print(f"\n💡 可能受益板块:")
    benefit_sectors = [
        {'sector': '科技创新', 'reason': '国家支持核心技术自主可控', 'stocks': ['芯片', '软件', '5G']},
        {'sector': '新能源', 'reason': '碳中和政策持续推进', 'stocks': ['光伏', '风电', '储能']},
        {'sector': '大消费', 'reason': '促消费政策出台', 'stocks': ['白酒', '家电', '旅游']},
        {'sector': '金融', 'reason': '资本市场改革利好', 'stocks': ['券商', '银行', '保险']},
        {'sector': '医药', 'reason': '医疗健康需求增长', 'stocks': ['创新药', '医疗器械', '中药']},
    ]
    
    print(f"\n{'板块':<10} {'利好原因':<25} {'相关概念':<20}")
    print(f"{'-'*70}")
    for s in benefit_sectors:
        print(f"{s['sector']:<10} {s['reason']:<25} {', '.join(s['stocks']):<20}")
    
    print(f"{'='*70}")
    
    return benefit_sectors


def analyze_market_trend():
    """分析市场趋势"""
    print("\n" + "="*70)
    print("📈 市场趋势分析")
    print("="*70)
    
    # 搜索市场新闻
    news = search_market_news('A 股 成交量 北向资金 2026', count=5)
    
    if news:
        print(f"\n最新市场动态:")
        for i, n in enumerate(news[:5], 1):
            print(f"{i}. {n.get('title', 'N/A')}")
    
    # 市场情绪指标
    print(f"\n📊 市场情绪指标:")
    
    # 从 fund_flow 获取真实数据
    try:
        from fund_flow import FundFlowFetcher
        fetcher = FundFlowFetcher()
        stocks = fetcher.fetch_tencent_estimate(count=50)
        
        if stocks:
            # 计算市场情绪
            up_count = sum(1 for s in stocks if s.get('change_pct', 0) > 0)
            down_count = len(stocks) - up_count
            
            total_amount = sum(s.get('amount_wan', 0) for s in stocks)
            
            print(f"  上涨股票：{up_count}/{len(stocks)} ({up_count/len(stocks)*100:.1f}%)")
            print(f"  下跌股票：{down_count}/{len(stocks)} ({down_count/len(stocks)*100:.1f}%)")
            print(f"  总成交额：{total_amount/10000:.2f}万亿")
            
            # 情绪判断
            if up_count > down_count * 1.5:
                sentiment = "🟢 强势"
            elif up_count > down_count:
                sentiment = "🟡 偏强"
            elif up_count > down_count * 0.5:
                sentiment = "🟠 偏弱"
            else:
                sentiment = "🔴 弱势"
            
            print(f"  市场情绪：{sentiment}")
    except Exception as e:
        print(f"  无法获取实时数据：{e}")
    
    print(f"{'='*70}")


def analyze_industry_hotspots():
    """分析行业热点"""
    print("\n" + "="*70)
    print("🔥 行业热点分析")
    print("="*70)
    
    # 搜索行业新闻
    hot_industries = [
        {'name': '人工智能', 'keyword': 'AI 人工智能 大模型'},
        {'name': '新能源', 'keyword': '光伏 风电 储能'},
        {'name': '半导体', 'keyword': '芯片 半导体 国产替代'},
        {'name': '医药', 'keyword': '创新药 医疗器械'},
        {'name': '消费', 'keyword': '消费 白酒 旅游'},
    ]
    
    print(f"\n热门行业搜索:")
    for industry in hot_industries:
        news = search_market_news(industry['keyword'], count=3)
        count = len(news) if news else 0
        print(f"  {industry['name']:<10} 相关新闻：{count} 条")
    
    # 推荐关注
    print(f"\n💡 建议关注行业:")
    recommendations = [
        {'industry': '人工智能', 'reason': '技术突破 + 政策支持', 'risk': '估值较高'},
        {'industry': '半导体', 'reason': '国产替代加速', 'risk': '技术壁垒'},
        {'industry': '新能源', 'reason': '碳中和长期趋势', 'risk': '产能过剩'},
    ]
    
    print(f"\n{'行业':<10} {'利好因素':<20} {'风险因素':<15}")
    print(f"{'-'*70}")
    for r in recommendations:
        print(f"{r['industry']:<10} {r['reason']:<20} {r['risk']:<15}")
    
    print(f"{'='*70}")


def generate_stock_pool():
    """生成潜力股票池"""
    print("\n" + "="*70)
    print("🎯 潜力股票池（基于数据分析）")
    print("="*70)
    
    # 从 fund_flow 获取真实数据
    try:
        from fund_flow import FundFlowFetcher
        fetcher = FundFlowFetcher()
        stocks = fetcher.fetch_tencent_estimate(count=100)
        
        if stocks:
            # 筛选条件：
            # 1. 主力净流入前 20
            # 2. 涨幅>0
            # 3. 成交额>10 亿
            
            filtered = [
                s for s in stocks 
                if s.get('change_pct', 0) > 0 
                and s.get('amount_wan', 0) > 100000  # 10 亿
            ]
            
            # 按主力净流入排序
            filtered.sort(key=lambda x: x.get('main_net', 0), reverse=True)
            
            print(f"\n筛选条件:")
            print(f"  - 主力净流入排名前 20")
            print(f"  - 今日涨幅 > 0%")
            print(f"  - 成交额 > 10 亿元")
            
            print(f"\n{'排名':<4} {'代码':<10} {'名称':<10} {'主力净流入':<12} {'涨幅':<8} {'成交额':<10}")
            print(f"{'-'*70}")
            
            for i, s in enumerate(filtered[:20], 1):
                net = s.get('main_net', 0)
                net_str = f"{net/100000000:.2f}亿" if abs(net) >= 100000000 else f"{net/10000:.0f}万"
                
                amount = s.get('amount_wan', 0)
                amount_str = f"{amount/10000:.2f}亿" if amount >= 10000 else f"{amount:.0f}万"
                
                change_sign = '+' if s.get('change_pct', 0) >= 0 else ''
                
                print(f"{i:<4} {s.get('symbol', ''):<10} {s.get('name', ''):<10} "
                      f"{net_str:<12} {change_sign}{s.get('change_pct', 0):>5.2f}% {amount_str:>8}")
            
            print(f"{'='*70}")
            print(f"\n⚠️  重要提示:")
            print(f"  - 以上数据基于腾讯财经估算（成交额真实，主力=成交额×15%）")
            print(f"  - 仅供参考，不构成投资建议")
            print(f"  - 投资有风险，决策需谨慎")
            
    except Exception as e:
        print(f"❌ 无法获取数据：{e}")
    
    print(f"{'='*70}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='市场新闻分析与股票预测')
    parser.add_argument('--news', action='store_true', help='分析最新财经新闻')
    parser.add_argument('--policy', action='store_true', help='分析政策利好')
    parser.add_argument('--industry', action='store_true', help='分析行业动态')
    parser.add_argument('--pool', action='store_true', help='生成潜力股票池')
    parser.add_argument('--all', action='store_true', help='综合分析')
    
    args = parser.parse_args()
    
    print(f"\n{'='*70}")
    print(f"📊 市场分析与股票预测系统")
    print(f"分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    
    if args.all or not (args.news or args.policy or args.industry or args.pool):
        # 综合分析
        analyze_market_trend()
        analyze_policy_benefits()
        analyze_industry_hotspots()
        generate_stock_pool()
    else:
        if args.news:
            analyze_market_trend()
        if args.policy:
            analyze_policy_benefits()
        if args.industry:
            analyze_industry_hotspots()
        if args.pool:
            generate_stock_pool()
    
    print(f"\n⚠️  免责声明:")
    print(f"  - 本分析仅用于研究学习")
    print(f"  - 不构成任何投资建议")
    print(f"  - 股市有风险，投资需谨慎")
    print(f"  - 数据来源：腾讯财经（估算）、公开新闻")


if __name__ == '__main__':
    main()
