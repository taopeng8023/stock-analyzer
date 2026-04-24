#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票市场舆情监测系统

监测内容:
1. 股票相关新闻
2. 公司公告/财报
3. 机构研报
4. 政策法规
5. 行业动态

功能:
1. 实时抓取信息
2. 情感分析 (利好/利空/中性)
3. 影响程度评估 (高/中/低)
4. 关联股票识别
5. 微信推送告警
"""

import json
import requests
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import time

# 配置
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/sentiment_data')
LOG_DIR = Path('/home/admin/.openclaw/workspace/stocks/logs')
CONFIG_FILE = Path('/home/admin/.openclaw/workspace/stocks/push_config.json')

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# 加载推送配置
def load_push_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


# ============== 信息抓取模块 ==============

class NewsScraper:
    """新闻信息抓取器"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def fetch_eastmoney_news(self, symbol=None, limit=20):
        """
        抓取东方财富新闻
        
        Args:
            symbol: 股票代码 (可选，为 None 则抓取全市场)
            limit: 限制数量
        """
        news_list = []
        
        try:
            if symbol:
                # 个股新闻
                url = f'http://newsapi.eastmoney.com/api/content/list'
                params = {
                    'appType': 'web',
                    'appCode': '001',
                    'pageIndex': 1,
                    'pageSize': limit,
                    'symbol': symbol
                }
            else:
                # 全市场新闻
                url = f'http://api.eastmoney.com/v2/News/getList'
                params = {
                    'pageIndex': 1,
                    'pageSize': limit,
                    'type': 'whole'
                }
            
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            result = resp.json()
            
            if result.get('code') == 0:
                data = result.get('data', {})
                items = data.get('items', [])
                
                for item in items:
                    news_list.append({
                        'title': item.get('Title', ''),
                        'content': item.get('Content', ''),
                        'publish_time': item.get('ShowTime', ''),
                        'source': item.get('Source', ''),
                        'url': item.get('Url', ''),
                        'type': 'news'
                    })
        
        except Exception as e:
            print(f"抓取东方财富新闻失败：{e}")
        
        return news_list
    
    def fetch_company_announcement(self, symbol, limit=10):
        """
        抓取公司公告
        
        Args:
            symbol: 股票代码
            limit: 限制数量
        """
        announcements = []
        
        try:
            # 确定市场
            if symbol.startswith('6'):
                market = 'SH'
            else:
                market = 'SZ'
            
            url = 'http://api.eastmoney.com/v2/Announcement/getList'
            params = {
                'pageIndex': 1,
                'pageSize': limit,
                'securityCode': symbol,
                'market': market
            }
            
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            result = resp.json()
            
            if result.get('code') == 0:
                data = result.get('data', {})
                items = data.get('items', [])
                
                for item in items:
                    announcements.append({
                        'title': item.get('Title', ''),
                        'content': item.get('Content', ''),
                        'publish_time': item.get('AnnouncementDate', ''),
                        'source': '公司公告',
                        'type': 'announcement'
                    })
        
        except Exception as e:
            print(f"抓取公告失败：{e}")
        
        return announcements
    
    def fetch_research_reports(self, symbol=None, limit=10):
        """
        抓取机构研报
        
        Args:
            symbol: 股票代码 (可选)
            limit: 限制数量
        """
        reports = []
        
        try:
            url = 'http://api.eastmoney.com/v2/Research/getList'
            params = {
                'pageIndex': 1,
                'pageSize': limit
            }
            
            if symbol:
                params['securityCode'] = symbol
            
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            result = resp.json()
            
            if result.get('code') == 0:
                data = result.get('data', {})
                items = data.get('items', [])
                
                for item in items:
                    reports.append({
                        'title': item.get('Title', ''),
                        'institution': item.get('OrganName', ''),
                        'publish_time': item.get('PublishTime', ''),
                        'analyst': item.get('Author', ''),
                        'rating': item.get('Rating', ''),
                        'source': '机构研报',
                        'type': 'research'
                    })
        
        except Exception as e:
            print(f"抓取研报失败：{e}")
        
        return reports
    
    def fetch_stock_info(self, symbol):
        """
        抓取股票基本信息
        
        Args:
            symbol: 股票代码
        """
        info = {}
        
        try:
            url = 'http://push2.eastmoney.com/api/qt/stock/get'
            params = {
                'secid': f'1.{symbol}' if symbol.startswith('6') else f'0.{symbol}',
                'fields': 'f12,f14,f43,f46,f44,f45,f47,f48,f170,f169,f168,f167,f164,f165'
            }
            
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            result = resp.json()
            
            if result.get('data'):
                data = result['data']
                info = {
                    'code': data.get('f12', ''),
                    'name': data.get('f14', ''),
                    'price': data.get('f43', 0) / 100,
                    'change_pct': data.get('f170', 0) / 100,
                    'volume': data.get('f47', 0),
                    'amount': data.get('f48', 0),
                    'turnover': data.get('f168', 0),
                    'pe_ratio': data.get('f164', 0),
                    'pb_ratio': data.get('f165', 0)
                }
        
        except Exception as e:
            print(f"抓取股票信息失败：{e}")
        
        return info


# ============== 情感分析模块 ==============

class SentimentAnalyzer:
    """情感分析器"""
    
    def __init__(self):
        # 利好词汇
        self.positive_words = [
            '增长', '上涨', '上升', '盈利', '利润', '收益', '利好', '突破',
            '创新高', '超预期', '大幅增长', '扭亏', '复苏', '回暖', '景气',
            '订单', '签约', '合作', '中标', '收购', '重组', '分红', '增持',
            '回购', '定增', '获批', '通过', '成功', '领先', '优势', '龙头'
        ]
        
        # 利空词汇
        self.negative_words = [
            '下跌', '下降', '下滑', '亏损', '亏损', '利空', '暴跌', '崩盘',
            '退市', 'ST', '处罚', '调查', '诉讼', '纠纷', '违约', '减持',
            '解禁', '质押', '冻结', '风险', '警告', '下滑', '萎缩', '衰退',
            '困难', '危机', '破产', '重组失败', '终止', '取消', '推迟'
        ]
        
        # 高影响词汇
        self.high_impact_words = [
            '涨停', '跌停', '翻倍', '暴涨', '暴跌', '重大', '特别', '紧急',
            '首次', '历史', '创纪录', '异常', '停牌', '复牌', '退市', 'ST'
        ]
    
    def analyze_sentiment(self, text: str) -> Tuple[str, float]:
        """
        分析文本情感
        
        Args:
            text: 待分析文本
        
        Returns:
            (情感类型，置信度)
            情感类型：'positive' (利好), 'negative' (利空), 'neutral' (中性)
            置信度：0-1
        """
        if not text:
            return 'neutral', 0.5
        
        text_lower = text.lower()
        
        # 计算词汇匹配
        pos_count = sum(1 for word in self.positive_words if word in text_lower)
        neg_count = sum(1 for word in self.negative_words if word in text_lower)
        high_impact_count = sum(1 for word in self.high_impact_words if word in text_lower)
        
        # 计算情感得分
        total = pos_count + neg_count
        if total == 0:
            return 'neutral', 0.5
        
        # 置信度
        confidence = min(1.0, (pos_count + neg_count + high_impact_count * 2) / 10)
        
        # 判断情感
        if pos_count > neg_count * 1.5:
            return 'positive', confidence
        elif neg_count > pos_count * 1.5:
            return 'negative', confidence
        else:
            return 'neutral', 0.5
    
    def analyze_impact_level(self, text: str, sentiment: str) -> str:
        """
        分析影响程度
        
        Args:
            text: 文本
            sentiment: 情感类型
        
        Returns:
            'high' (高), 'medium' (中), 'low' (低)
        """
        text_lower = text.lower()
        
        # 高影响关键词
        high_impact = sum(1 for word in self.high_impact_words if word in text_lower)
        
        # 长度因素
        length_factor = len(text) / 100 if len(text) < 500 else 5
        
        # 综合评分
        score = high_impact * 2 + length_factor
        
        if score >= 5:
            return 'high'
        elif score >= 2:
            return 'medium'
        else:
            return 'low'
    
    def extract_stock_symbols(self, text: str) -> List[str]:
        """
        从文本中提取股票代码
        
        Args:
            text: 文本
        
        Returns:
            股票代码列表
        """
        symbols = []
        
        # 匹配 6 位数字代码
        pattern = r'\b(\d{6})\b'
        matches = re.findall(pattern, text)
        
        for match in matches:
            # 验证是否为有效代码
            if match.startswith(('0', '3', '6')):
                symbols.append(match)
        
        return list(set(symbols))


# ============== 股票影响分析模块 ==============

class StockImpactAnalyzer:
    """股票影响分析器"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
    
    def analyze_news_impact(self, news: Dict, stock_info: Dict = None) -> Dict:
        """
        分析新闻对股票的影响
        
        Args:
            news: 新闻信息
            stock_info: 股票基本信息
        
        Returns:
            分析结果
        """
        title = news.get('title', '')
        content = news.get('content', '')
        text = f"{title} {content}"
        
        # 情感分析
        sentiment, confidence = self.sentiment_analyzer.analyze_sentiment(text)
        
        # 影响程度
        impact_level = self.sentiment_analyzer.analyze_impact_level(text, sentiment)
        
        # 提取相关股票
        related_stocks = self.sentiment_analyzer.extract_stock_symbols(text)
        
        # 综合评分 (-100 到 100)
        if sentiment == 'positive':
            base_score = 50
        elif sentiment == 'negative':
            base_score = -50
        else:
            base_score = 0
        
        # 根据影响程度调整
        if impact_level == 'high':
            score = base_score * 1.5
        elif impact_level == 'medium':
            score = base_score * 1.0
        else:
            score = base_score * 0.5
        
        # 根据置信度调整
        score *= confidence
        
        return {
            'sentiment': sentiment,
            'confidence': round(confidence, 2),
            'impact_level': impact_level,
            'score': round(score, 1),
            'related_stocks': related_stocks,
            'title': title,
            'publish_time': news.get('publish_time', ''),
            'source': news.get('source', ''),
            'type': news.get('type', ''),
            'url': news.get('url', '')
        }


# ============== 微信推送模块 ==============

class WeChatPusher:
    """微信推送器"""
    
    def __init__(self, config: Dict):
        self.config = config
    
    def push_alert(self, alert: Dict):
        """
        推送告警信息
        
        Args:
            alert: 告警信息
        """
        content = self._format_alert(alert)
        
        # 企业微信
        if self.config.get('wecom_webhook'):
            self._push_wecom(content)
        
        # 钉钉
        if self.config.get('dingtalk_webhook'):
            self._push_dingtalk(content)
    
    def _format_alert(self, alert: Dict) -> str:
        """格式化告警信息"""
        sentiment_map = {
            'positive': '🟢 利好',
            'negative': '🔴 利空',
            'neutral': '⚪ 中性'
        }
        
        impact_map = {
            'high': '🔴 高',
            'medium': '🟡 中',
            'low': '🟢 低'
        }
        
        content = f"""# 📊 市场舆情告警

**时间**: {alert.get('time', '')}
**类型**: {alert.get('type', '')}

## 影响股票
{', '.join(alert.get('stocks', []))}

## 情感分析
{sentiment_map.get(alert.get('sentiment', ''), '')} | 影响程度：{impact_map.get(alert.get('impact_level', ''), '')}

## 综合评分
{'📈' if alert.get('score', 0) > 0 else '📉'} {alert.get('score', 0):.1f}

## 信息来源
**标题**: {alert.get('title', '')}
**来源**: {alert.get('source', '')}
**时间**: {alert.get('publish_time', '')}

{'**链接**: ' + alert.get('url', '') if alert.get('url') else ''}
"""
        return content
    
    def _push_wecom(self, content: str):
        """推送到企业微信"""
        url = self.config.get('wecom_webhook')
        payload = {
            'msgtype': 'markdown',
            'markdown': {'content': content}
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=10)
            result = resp.json()
            if result.get('errcode') == 0:
                print("✅ 企业微信推送成功")
            else:
                print(f"❌ 企业微信推送失败：{result}")
        except Exception as e:
            print(f"❌ 推送异常：{e}")
    
    def _push_dingtalk(self, content: str):
        """推送到钉钉"""
        url = self.config.get('dingtalk_webhook')
        payload = {
            'msgtype': 'markdown',
            'markdown': {
                'title': '市场舆情告警',
                'text': content
            }
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=10)
            result = resp.json()
            if result.get('errcode') == 0:
                print("✅ 钉钉推送成功")
            else:
                print(f"❌ 钉钉推送失败：{result}")
        except Exception as e:
            print(f"❌ 推送异常：{e}")


# ============== 主监测系统 ==============

class MarketSentimentMonitor:
    """市场舆情监测系统"""
    
    def __init__(self, watchlist: List[str] = None):
        """
        初始化监测系统
        
        Args:
            watchlist: 监控股票列表 (可选)
        """
        self.scraper = NewsScraper()
        self.analyzer = StockImpactAnalyzer()
        self.pusher = WeChatPusher(load_push_config())
        self.watchlist = watchlist or []
        
        # 历史告警 (用于去重)
        self.alert_history = set()
    
    def monitor(self, symbols: List[str] = None):
        """
        执行监测
        
        Args:
            symbols: 指定股票代码列表 (可选)
        """
        symbols = symbols or self.watchlist
        
        print("=" * 80)
        print("市场舆情监测")
        print("=" * 80)
        print(f"监测时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"监控股票：{len(symbols) if symbols else '全市场'} 只")
        print()
        
        all_alerts = []
        
        # 1. 抓取新闻
        print("[1/4] 抓取新闻...")
        news_list = self.scraper.fetch_eastmoney_news(limit=50)
        print(f"   获取新闻：{len(news_list)} 条")
        
        # 2. 抓取公告 (针对监控股票)
        if symbols:
            print(f"\n[2/4] 抓取公告...")
            announcements = []
            for symbol in symbols[:10]:  # 限制数量
                annos = self.scraper.fetch_company_announcement(symbol, limit=3)
                announcements.extend(annos)
                time.sleep(0.5)
            print(f"   获取公告：{len(announcements)} 条")
            news_list.extend(announcements)
        
        # 3. 抓取研报
        print(f"\n[3/4] 抓取研报...")
        reports = self.scraper.fetch_research_reports(limit=20)
        print(f"   获取研报：{len(reports)} 条")
        news_list.extend(reports)
        
        # 4. 分析影响
        print(f"\n[4/4] 分析影响...")
        for news in news_list:
            # 获取股票信息
            stock_symbols = self.analyzer.sentiment_analyzer.extract_stock_symbols(
                f"{news.get('title', '')} {news.get('content', '')}"
            )
            
            if not stock_symbols and symbols:
                # 如果没有明确提到股票，跳过
                continue
            
            # 分析影响
            impact = self.analyzer.analyze_news_impact(news)
            
            # 只关注高影响或强烈情感的信息
            if impact['impact_level'] == 'high' or impact['confidence'] > 0.8:
                # 去重
                alert_key = f"{impact['title']}_{impact['publish_time']}"
                if alert_key not in self.alert_history:
                    self.alert_history.add(alert_key)
                    
                    alert = {
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'stocks': stock_symbols or symbols[:5],
                        **impact
                    }
                    
                    all_alerts.append(alert)
                    
                    # 推送告警
                    print(f"   🚨 发现重要信息：{impact['title'][:30]}...")
                    self.pusher.push_alert(alert)
        
        # 保存结果
        self._save_results(all_alerts)
        
        print()
        print("=" * 80)
        print(f"监测完成")
        print(f"   处理信息：{len(news_list)} 条")
        print(f"   发现告警：{len(all_alerts)} 条")
        print("=" * 80)
        
        return all_alerts
    
    def _save_results(self, alerts: List[Dict]):
        """保存监测结果"""
        if not alerts:
            return
        
        date_str = datetime.now().strftime('%Y%m%d')
        filepath = DATA_DIR / f'sentiment_{date_str}.json'
        
        # 读取已有数据
        existing_alerts = []
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                existing_alerts = json.load(f)
        
        # 合并数据
        existing_alerts.extend(alerts)
        
        # 保存
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(existing_alerts, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 结果已保存：{filepath}")


# ============== 主函数 ==============

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='市场舆情监测系统')
    parser.add_argument('--symbols', type=str, nargs='+', help='监控股票代码列表')
    parser.add_argument('--watchlist', type=str, help='监控股票列表文件')
    
    args = parser.parse_args()
    
    # 确定监控股票
    watchlist = []
    if args.symbols:
        watchlist = args.symbols
    elif args.watchlist:
        with open(args.watchlist, 'r') as f:
            watchlist = [line.strip() for line in f if line.strip()]
    
    # 创建监测系统
    monitor = MarketSentimentMonitor(watchlist)
    
    # 执行监测
    alerts = monitor.monitor()
    
    return alerts


if __name__ == '__main__':
    main()
