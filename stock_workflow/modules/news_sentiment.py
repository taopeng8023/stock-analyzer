#!/usr/bin/env python3
"""
市场消息模块 - v1.0
目标：量化近半年个股相关的新闻、公告、社交媒体情绪
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime, timedelta
import sys
sys.path.append('..')

from config.loader import Config


class NewsSentimentAnalyzer:
    """市场消息情感分析器"""
    
    def __init__(self, config: Config = None):
        """
        初始化市场消息分析器
        
        Args:
            config: 配置对象
        """
        self.config = config or Config()
        self.news_window_days = int(self.config.get('NEWS_ANALYSIS', 'news_window_days'))
        self.major_event_weight = float(self.config.get('NEWS_ANALYSIS', 'major_event_weight'))
        
        # 重大事件关键词
        self.major_events = [
            '业绩预告', '重组', '股东增持', '分红', '回购',
            '中标', '签约', '新产品', '专利', '获批'
        ]
    
    def get_news_data(self, stock_codes: List[str]) -> Dict[str, List[Dict]]:
        """
        获取新闻数据
        
        Args:
            stock_codes: 股票代码列表
        
        Returns:
            Dict{code: [news_dict]}
        """
        # TODO: 接入新闻 API 获取真实数据
        # 这里使用模拟数据
        news_dict = {}
        for code in stock_codes:
            news_dict[code] = []
            # 生成近 6 个月的模拟新闻
            for i in range(np.random.randint(5, 30)):
                days_ago = np.random.randint(1, self.news_window_days)
                news_date = datetime.now() - timedelta(days=days_ago)
                
                news_dict[code].append({
                    'date': news_date,
                    'title': f'{code} 相关新闻 {i}',
                    'content': '模拟新闻内容',
                    'source': np.random.choice(['新浪财经', '东方财富', '同花顺']),
                    'type': np.random.choice(['普通', '公告', '研报']),
                })
        
        return news_dict
    
    def analyze_sentiment(self, text: str) -> float:
        """
        分析文本情感得分
        
        Args:
            text: 文本内容
        
        Returns:
            情感得分（-1 到 1）
        """
        # TODO: 使用 SnowNLP 进行真实情感分析
        # 这里使用简单模拟
        positive_words = ['增长', '利好', '上涨', '突破', '超预期', '中标', '签约']
        negative_words = ['下滑', '利空', '下跌', '亏损', '不及预期', '处罚', '诉讼']
        
        score = 0
        for word in positive_words:
            if word in text:
                score += 0.2
        for word in negative_words:
            if word in text:
                score -= 0.2
        
        return max(-1, min(1, score))
    
    def is_major_event(self, title: str, content: str) -> bool:
        """
        判断是否为重大事件
        
        Args:
            title: 新闻标题
            content: 新闻内容
        
        Returns:
            是否为重大事件
        """
        text = title + ' ' + content
        for keyword in self.major_events:
            if keyword in text:
                return True
        return False
    
    def aggregate_sentiment(self, news_list: List[Dict]) -> Dict:
        """
        聚合情感统计
        
        Args:
            news_list: 新闻列表
        
        Returns:
            情感统计 Dict
        """
        if not news_list:
            return {
                'sentiment_avg': 0,
                'sentiment_std': 0,
                'pos_news_cnt': 0,
                'neg_news_cnt': 0,
                'event_flag': 0,
            }
        
        sentiments = []
        pos_cnt = 0
        neg_cnt = 0
        event_cnt = 0
        
        for news in news_list:
            text = news.get('title', '') + ' ' + news.get('content', '')
            score = self.analyze_sentiment(text)
            
            # 重大事件加权
            if self.is_major_event(news.get('title', ''), news.get('content', '')):
                score *= self.major_event_weight
                event_cnt += 1
            
            sentiments.append(score)
            
            if score > 0.2:
                pos_cnt += 1
            elif score < -0.2:
                neg_cnt += 1
        
        return {
            'sentiment_avg': np.mean(sentiments),
            'sentiment_std': np.std(sentiments),
            'pos_news_cnt': pos_cnt,
            'neg_news_cnt': neg_cnt,
            'event_flag': 1 if event_cnt > 0 else 0,
        }
    
    def run(self, stock_codes: List[str]) -> Dict:
        """
        运行完整的市场消息分析流程
        
        Args:
            stock_codes: 股票代码列表
        
        Returns:
            分析结果 Dict {
                'features': DataFrame（特征向量）,
                'quality_score': float（0-100）
            }
        """
        print(f"[市场消息] 开始分析 {len(stock_codes)} 只股票...")
        
        # 获取新闻数据
        news_data = self.get_news_data(stock_codes)
        
        # 分析每只股票的情感
        all_features = []
        for code in stock_codes:
            news_list = news_data.get(code, [])
            sentiment_stats = self.aggregate_sentiment(news_list)
            sentiment_stats['code'] = code
            all_features.append(sentiment_stats)
        
        features_df = pd.DataFrame(all_features)
        
        # 计算质量评分
        missing_rate = features_df.isnull().mean().mean()
        quality_score = (1 - missing_rate) * 100
        
        print(f"[市场消息] 完成，质量评分：{quality_score:.1f}")
        
        return {
            'features': features_df,
            'quality_score': quality_score
        }


# 测试
if __name__ == '__main__':
    config = Config()
    analyzer = NewsSentimentAnalyzer(config)
    
    test_codes = ['600519', '000858', '600036', '000002', '000651']
    result = analyzer.run(test_codes)
    
    print("\n" + "="*60)
    print("📊 市场消息分析结果")
    print("="*60)
    print(f"分析股票数：{len(result['features'])}")
    print(f"质量评分：{result['quality_score']:.1f}")
    print("\n特征列:")
    print(result['features'].columns.tolist())
    print("\n数据预览:")
    print(result['features'].head())
