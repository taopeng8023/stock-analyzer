#!/usr/bin/env python3
"""
News Monitor Skill - 消息监控分析技能

实时监控国内外消息，分析对 A 股影响
- 每分钟获取消息
- 12 小时去重
- 影响分析
- 实时推送

⚠️  核心原则：所有消息必须来自真实新闻源，严禁使用模拟数据

⚠️  消息仅供参考，不构成投资建议
"""

import sys
import json
import hashlib
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'stocks'))


class NewsMonitorSkill:
    """消息监控分析技能"""
    
    def __init__(self, config=None):
        """
        初始化技能（增强版 v6.2）
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.cache_dir = Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        # 消息历史文件（12 小时）
        self.history_file = self.cache_dir / 'news_history.json'
        
        # 加载消息历史
        self.news_history = self._load_history()
        
        # 消息源配置
        self.news_sources = self._get_news_sources()
        
        # 初始化健康监控器（新增 v6.0）
        try:
            from core.health_monitor import SourceHealthMonitor
            self.health_monitor = SourceHealthMonitor()
        except Exception as e:
            self.health_monitor = None
        
        # 初始化实时行情获取器（新增 v6.0）
        try:
            from core.quote_fetcher import QuoteFetcher
            self.quote_fetcher = QuoteFetcher()
        except Exception as e:
            self.quote_fetcher = None
        
        # 初始化情感分析器（新增 v6.0）
        try:
            from core.sentiment_analyzer import SentimentAnalyzer
            self.sentiment_analyzer = SentimentAnalyzer()
        except Exception as e:
            self.sentiment_analyzer = None
        
        # 初始化板块分析器（新增 v6.2）
        try:
            from core.sector_analyzer import SectorAnalyzer
            self.sector_analyzer = SectorAnalyzer()
        except Exception as e:
            self.sector_analyzer = None
        
        # 微信推送
        try:
            from wechat_push import push_to_corp_webhook
            self.push_function = push_to_corp_webhook
            # 默认使用与分析技能相同的 webhook
            self.webhook = self.config.get('webhook', 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5')
        except Exception as e:
            self.push_function = None
            self.webhook = ''
    
    def _load_history(self) -> dict:
        """加载消息历史"""
        if not self.history_file.exists():
            return {'messages': [], 'last_update': None}
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            # 清理 12 小时前的消息
            cutoff_time = datetime.now() - timedelta(hours=12)
            history['messages'] = [
                msg for msg in history['messages']
                if datetime.fromisoformat(msg['timestamp']) > cutoff_time
            ]
            
            # 保存清理后的历史
            self._save_history(history)
            
            return history
        except Exception as e:
            print(f"⚠️  加载历史失败：{e}")
            return {'messages': [], 'last_update': None}
    
    def _save_history(self, history: dict):
        """保存消息历史"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  保存历史失败：{e}")
    
    def _get_news_sources(self) -> list:
        """获取消息源配置"""
        return [
            # 国内消息源
            {'name': '新华社', 'type': 'domestic', 'category': 'policy', 'priority': 5},
            {'name': '财联社', 'type': 'domestic', 'category': 'finance', 'priority': 5},
            {'name': '证券时报', 'type': 'domestic', 'category': 'stock', 'priority': 4},
            {'name': '东方财富', 'type': 'domestic', 'category': 'stock', 'priority': 4},
            
            # 国际消息源
            {'name': '路透社', 'type': 'international', 'category': 'global', 'priority': 4},
            {'name': '彭博社', 'type': 'international', 'category': 'finance', 'priority': 4},
            {'name': '华尔街日报', 'type': 'international', 'category': 'stock', 'priority': 3},
        ]
    
    def _calculate_hash(self, text: str) -> str:
        """计算消息指纹"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _is_duplicate(self, news: dict) -> bool:
        """
        检查消息是否重复
        
        Args:
            news: 消息字典
        
        Returns:
            bool: 是否重复
        """
        # 计算标题指纹
        title_hash = self._calculate_hash(news.get('title', ''))
        
        # 检查历史消息
        for msg in self.news_history['messages']:
            if msg.get('title_hash') == title_hash:
                return True
        
        return False
    
    def _add_to_history(self, news: dict):
        """添加到消息历史"""
        news['title_hash'] = self._calculate_hash(news.get('title', ''))
        news['timestamp'] = datetime.now().isoformat()
        
        self.news_history['messages'].append(news)
        self.news_history['last_update'] = datetime.now().isoformat()
        
        # 限制历史消息数量（最多 1000 条）
        if len(self.news_history['messages']) > 1000:
            self.news_history['messages'] = self.news_history['messages'][-1000:]
        
        self._save_history(self.news_history)
    
    def _fetch_from_toutiao(self) -> list:
        """从今日头条获取财经新闻"""
        news_list = []
        source_name = '今日头条'
        try:
            url = 'https://www.toutiao.com/api/pc/feed/?category=news_hot&utm_source=toutiao&widen=1&max_behot_time=0&max_behot_time_tmp=0&tadrequire=true&as=A1&cp=C1'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': 'https://www.toutiao.com/',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                for item in data['data'][:30]:
                    if not item.get('title'):
                        continue
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('abstract', '') or item.get('title', ''),
                        'source': '今日头条',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(item.get('behot_time', 0)).isoformat() if item.get('behot_time') else datetime.now().isoformat(),
                        'url': f"https://www.toutiao.com/a{item.get('item_id', '')}/" if item.get('item_id') else '',
                    })
            
            # 记录健康状态
            if self.health_monitor:
                self.health_monitor.record_success(source_name, len(news_list))
                
        except Exception as e:
            print(f"⚠️  今日头条获取失败：{e}")
            if self.health_monitor:
                self.health_monitor.record_fail(source_name, str(e))
        
        return news_list
    
    def _fetch_from_zhihu(self) -> list:
        """从知乎热榜获取热门话题"""
        news_list = []
        try:
            url = 'https://www.zhihu.com/api/v3/feed/topstory/hot?limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': 'https://www.zhihu.com/hot',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                for item in data['data'][:20]:
                    target = item.get('target', {})
                    if not target:
                        continue
                    title = target.get('title', '') or target.get('headline', '')
                    if not title:
                        continue
                    news_list.append({
                        'title': title,
                        'content': target.get('excerpt', '') or target.get('summary', '') or title,
                        'source': '知乎热榜',
                        'category': 'hot',
                        'timestamp': datetime.fromtimestamp(target.get('created', 0)).isoformat() if target.get('created') else datetime.now().isoformat(),
                        'url': target.get('url', ''),
                    })
        except Exception as e:
            print(f"⚠️  知乎获取失败：{e}")
        
        return news_list
    
    def _fetch_from_sina_finance(self) -> list:
        """从新浪财经获取财经新闻（简化版）"""
        news_list = []
        try:
            # 使用更简单的接口
            url = 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&num=10&page=1'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('result') and data['result'].get('data'):
                    for item in data['result']['data'][:10]:
                        news_list.append({
                            'title': item.get('title', ''),
                            'content': item.get('intro', '') or item.get('title', ''),
                            'source': '新浪财经',
                            'category': 'finance',
                            'timestamp': datetime.fromtimestamp(item.get('ctime', 0)).isoformat() if item.get('ctime') else datetime.now().isoformat(),
                            'url': item.get('url', ''),
                        })
        except Exception as e:
            pass  # 静默失败
        
        return news_list
    
    def _fetch_from_wallstreetcn(self) -> list:
        """从华尔街见闻获取全球财经快讯"""
        news_list = []
        try:
            url = 'https://api.wallstreetcn.com/apiv1/content/lives?channel=global&limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': 'https://www.wallstreetcn.com/',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data') and data['data'].get('items'):
                for item in data['data']['items'][:20]:
                    if not item.get('title') and not item.get('content'):
                        continue
                    news_list.append({
                        'title': item.get('title', '') or item.get('content', '')[:50],
                        'content': item.get('content', '') or item.get('title', ''),
                        'source': '华尔街见闻',
                        'category': 'global',
                        'timestamp': datetime.fromtimestamp(item.get('published_at', 0)).isoformat() if item.get('published_at') else datetime.now().isoformat(),
                        'url': f"https://www.wallstreetcn.com/livenews/{item.get('id', '')}" if item.get('id') else '',
                    })
        except Exception as e:
            print(f"⚠️  华尔街见闻获取失败：{e}")
        
        return news_list
    
    def _fetch_from_jin10(self) -> list:
        """从金十数据获取财经快讯"""
        news_list = []
        try:
            url = 'https://www.jin10.com/flash_newest.js'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/javascript, */*',
                'Referer': 'https://www.jin10.com/',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            text = resp.text
            
            # 解析 JS 变量
            if text.startswith('var newest = '):
                text = text[13:].strip()
                if text.endswith(';'):
                    text = text[:-1]
                data = json.loads(text)
                
                for item in data[:20]:
                    if not item.get('content'):
                        continue
                    news_list.append({
                        'title': item.get('content', '')[:50],
                        'content': item.get('content', ''),
                        'source': '金十数据',
                        'category': 'finance',
                        'timestamp': item.get('time', datetime.now().isoformat()),
                        'url': f"https://www.jin10.com/flash_newest.html" if item.get('id') else '',
                    })
        except Exception as e:
            print(f"⚠️  金十数据获取失败：{e}")
        
        return news_list
    
    def _fetch_from_eastmoney_news(self) -> list:
        """从东方财富获取新闻（使用腾讯财经替代）"""
        news_list = []
        try:
            # 使用腾讯财经的财经新闻
            url = 'https://r.inews.qq.com/gw/event/more_hot_ranking_list?page_size=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('infoList'):
                for item in data['infoList'][:20]:
                    if not item.get('title'):
                        continue
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('abstract', '') or item.get('title', ''),
                        'source': '腾讯财经',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(item.get('timestamp', 0)).isoformat() if item.get('timestamp') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass  # 静默失败
        
        return news_list
    
    def _fetch_from_cls(self) -> list:
        """从财联社获取电报（使用同花顺替代）"""
        news_list = []
        try:
            # 使用同花顺财经新闻
            url = 'http://news.10jqka.com.cn/interface/news/list?callback=jQuery&per=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/javascript, */*',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            text = resp.text
            
            # 处理 JSONP
            if text.startswith('jQuery') and '(' in text:
                start = text.index('(') + 1
                end = text.rfind(')')
                if end > start:
                    text = text[start:end]
                    data = json.loads(text)
                    
                    if data.get('data'):
                        for item in data['data'][:20]:
                            if not item.get('title'):
                                continue
                            news_list.append({
                                'title': item.get('title', ''),
                                'content': item.get('content', '')[:200] if item.get('content') else item.get('title', ''),
                                'source': '同花顺',
                                'category': 'finance',
                                'timestamp': datetime.fromtimestamp(int(item.get('time', 0))).isoformat() if item.get('time') else datetime.now().isoformat(),
                                'url': item.get('url', ''),
                            })
        except Exception as e:
            pass  # 静默失败
        
        return news_list
    
    def _fetch_from_cnstock(self) -> list:
        """从中国证券网获取 A 股新闻"""
        news_list = []
        try:
            url = 'http://app.cnstock.com/api/waterfall?callback=jQuery&col=72&code=&stock=&sub=0&pagesize=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/javascript, */*',
                'Referer': 'http://ggjd.cnstock.com/gglist/search/ggkx',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            text = resp.text
            
            # 处理 JSONP
            if text.startswith('jQuery') and '(' in text:
                start = text.index('(') + 1
                end = text.rfind(')')
                if end > start:
                    text = text[start:end]
                    data = json.loads(text)
                    
                    if data.get('data'):
                        for item in data['data'][:20]:
                            if not item.get('title'):
                                continue
                            news_list.append({
                                'title': item.get('title', ''),
                                'content': item.get('content', '')[:200] if item.get('content') else item.get('title', ''),
                                'source': '中国证券网',
                                'category': 'stock',
                                'timestamp': datetime.fromisoformat(item.get('time', datetime.now().isoformat())).isoformat() if item.get('time') else datetime.now().isoformat(),
                                'url': item.get('url', ''),
                            })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_stcn(self) -> list:
        """从证券时报网获取 A 股新闻"""
        news_list = []
        try:
            url = 'https://www.stcn.com/article/list/0/0/20/0.json'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('articleList'):
                for item in data['articleList'][:20]:
                    if not item.get('title'):
                        continue
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('content', '')[:200] if item.get('content') else item.get('title', ''),
                        'source': '证券时报',
                        'category': 'stock',
                        'timestamp': datetime.fromtimestamp(int(item.get('pubtime', 0))).isoformat() if item.get('pubtime') else datetime.now().isoformat(),
                        'url': f"https://www.stcn.com/article/detail/{item.get('artid', '')}.html" if item.get('artid') else '',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_10jqka(self) -> list:
        """从同花顺财经获取 A 股新闻"""
        news_list = []
        try:
            url = 'http://news.10jqka.com.cn/interface/news/list?callback=jQuery&per=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/javascript, */*',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            text = resp.text
            
            if text.startswith('jQuery') and '(' in text:
                start = text.index('(') + 1
                end = text.rfind(')')
                if end > start:
                    text = text[start:end]
                    data = json.loads(text)
                    
                    if data.get('data'):
                        for item in data['data'][:20]:
                            if not item.get('title'):
                                continue
                            news_list.append({
                                'title': item.get('title', ''),
                                'content': item.get('content', '')[:200] if item.get('content') else item.get('title', ''),
                                'source': '同花顺财经',
                                'category': 'stock',
                                'timestamp': datetime.fromtimestamp(int(item.get('time', 0))).isoformat() if item.get('time') else datetime.now().isoformat(),
                                'url': item.get('url', ''),
                            })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_hexun(self) -> list:
        """从和讯网获取财经新闻"""
        news_list = []
        try:
            url = 'http://api.hexun.com/News/GetNewsList?callback=jQuery&type=1&page=1&pagesize=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/javascript, */*',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            text = resp.text
            
            if text.startswith('jQuery') and '(' in text:
                start = text.index('(') + 1
                end = text.rfind(')')
                if end > start:
                    text = text[start:end]
                    data = json.loads(text)
                    
                    if data.get('data'):
                        for item in data['data'][:20]:
                            if not item.get('title'):
                                continue
                            news_list.append({
                                'title': item.get('title', ''),
                                'content': item.get('summary', '')[:200] if item.get('summary') else item.get('title', ''),
                                'source': '和讯网',
                                'category': 'finance',
                                'timestamp': datetime.fromisoformat(item.get('uptime', datetime.now().isoformat())).isoformat() if item.get('uptime') else datetime.now().isoformat(),
                                'url': item.get('url', ''),
                            })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_yicai(self) -> list:
        """从第一财经获取财经新闻"""
        news_list = []
        try:
            url = 'https://www.yicai.com/api/roll/get?pageid=153&lid=2509&num=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('result') and data['result'].get('data'):
                for item in data['result']['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('intro', '') or item.get('title', ''),
                        'source': '第一财经',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(item.get('ctime', 0)).isoformat() if item.get('ctime') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_21jingji(self) -> list:
        """从 21 世纪经济报道获取财经新闻"""
        news_list = []
        try:
            url = 'https://m.21jingji.com/api/list?channel=finance&limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('articles'):
                for item in data['articles'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('summary', '') or item.get('title', ''),
                        'source': '21 世纪经济报道',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(int(item.get('publish_time', 0))).isoformat() if item.get('publish_time') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_caixin(self) -> list:
        """从财新网获取财经新闻"""
        news_list = []
        try:
            url = 'https://api.caixin.com/api/content/list?channel=finance&limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                for item in data['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('summary', '') or item.get('title', ''),
                        'source': '财新网',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(int(item.get('pub_time', 0))).isoformat() if item.get('pub_time') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_eastmoney_stock(self) -> list:
        """从东方财富网获取 A 股新闻"""
        news_list = []
        try:
            # 东方财富 A 股新闻
            url = 'http://news.eastmoney.com/newsapi/newslist?classid=0001001&page=1&pagesize=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': 'http://news.eastmoney.com/',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('Data'):
                    for item in data['Data'][:20]:
                        news_list.append({
                            'title': item.get('Title', ''),
                            'content': item.get('Brief', '') or item.get('Title', ''),
                            'source': '东方财富',
                            'category': 'stock',
                            'timestamp': datetime.fromisoformat(item.get('CreateTime', datetime.now().isoformat())).isoformat() if item.get('CreateTime') else datetime.now().isoformat(),
                            'url': item.get('Url', ''),
                        })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_sina_stock(self) -> list:
        """从新浪财经 A 股获取新闻"""
        news_list = []
        try:
            # 新浪财经 A 股新闻
            url = 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2513&num=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('result') and data['result'].get('data'):
                for item in data['result']['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('intro', '') or item.get('title', ''),
                        'source': '新浪财经 A 股',
                        'category': 'stock',
                        'timestamp': datetime.fromtimestamp(item.get('ctime', 0)).isoformat() if item.get('ctime') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_people_finance(self) -> list:
        """从人民网财经获取新闻"""
        news_list = []
        try:
            url = 'http://finance.people.cn/api/roll/get?pageid=153&lid=2513&num=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                # 简单解析
                import re
                titles = re.findall(r'<h3><a[^>]*>([^<]+)</a>', resp.text)
                for title in titles[:15]:
                    news_list.append({
                        'title': title.strip(),
                        'content': title.strip(),
                        'source': '人民网财经',
                        'category': 'finance',
                        'timestamp': datetime.now().isoformat(),
                        'url': 'http://finance.people.cn/',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_xinhua_finance(self) -> list:
        """从新华网财经获取新闻"""
        news_list = []
        try:
            url = 'http://www.xinhuanet.com/fortune/rollnews.htm'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                import re
                titles = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', resp.text)
                for url, title in titles[:15]:
                    if 'finance' in url or 'stock' in url:
                        news_list.append({
                            'title': title.strip(),
                            'content': title.strip(),
                            'source': '新华网财经',
                            'category': 'finance',
                            'timestamp': datetime.now().isoformat(),
                            'url': url if url.startswith('http') else f'http://www.xinhuanet.com{url}',
                        })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_cctv_finance(self) -> list:
        """从央视财经获取新闻"""
        news_list = []
        try:
            url = 'https://api.cctv.com/lanmu/columnInfoList?categoryId=jjzx&srvid=139&serviceId=toutiao&num=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                for item in data['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('brief', '') or item.get('title', ''),
                        'source': '央视财经',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(int(item.get('pubTime', 0))).isoformat() if item.get('pubTime') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_gelonghui(self) -> list:
        """从格隆汇获取港美股/A 股新闻"""
        news_list = []
        try:
            url = 'https://api.gelonghui.com/stock/api/article/list?limit=20&offset=0'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                for item in data['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('abstract', '') or item.get('title', ''),
                        'source': '格隆汇',
                        'category': 'stock',
                        'timestamp': datetime.fromtimestamp(int(item.get('publishTime', 0))).isoformat() if item.get('publishTime') else datetime.now().isoformat(),
                        'url': f"https://www.gelonghui.com/p/{item.get('id', '')}" if item.get('id') else '',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_jm(self) -> list:
        """从界面新闻获取财经新闻"""
        news_list = []
        try:
            url = 'https://www.jiemian.com/api/news/list?category_id=finance&limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('data'):
                    for item in data['data'][:20]:
                        news_list.append({
                            'title': item.get('title', ''),
                            'content': item.get('content_abstract', '') or item.get('title', ''),
                            'source': '界面新闻',
                            'category': 'finance',
                            'timestamp': datetime.fromtimestamp(int(item.get('publish_time', 0))).isoformat() if item.get('publish_time') else datetime.now().isoformat(),
                            'url': item.get('url', ''),
                        })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_thepaper(self) -> list:
        """从澎湃新闻获取财经新闻"""
        news_list = []
        try:
            url = 'https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                for item in data['data'].get('list', [])[:15]:
                    news_list.append({
                        'title': item.get('name', ''),
                        'content': item.get('desc', '') or item.get('name', ''),
                        'source': '澎湃新闻',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(int(item.get('pubTimeLong', 0))).isoformat() if item.get('pubTimeLong') else datetime.now().isoformat(),
                        'url': f"https://www.thepaper.cn/newsDetail_forward_{item.get('contId', '')}" if item.get('contId') else '',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_nbd(self) -> list:
        """从每日经济新闻获取财经新闻"""
        news_list = []
        try:
            url = 'https://www.nbd.com.cn/api/news/list?channelId=finance&limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                for item in data['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('summary', '') or item.get('title', ''),
                        'source': '每日经济新闻',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(int(item.get('publishTime', 0))).isoformat() if item.get('publishTime') else datetime.now().isoformat(),
                        'url': item.get('link', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_xueqiu(self) -> list:
        """从雪球获取热门讨论"""
        news_list = []
        try:
            url = 'https://xueqiu.com/v4/statuses/public_timeline_by_category.json?since_id=-1&max_id=0&count=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('list'):
                for item in data['list'][:20]:
                    if not item.get('title'):
                        continue
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('text', '') or item.get('title', ''),
                        'source': '雪球',
                        'category': 'stock',
                        'timestamp': datetime.fromtimestamp(int(item.get('created_at', 0))).isoformat() if item.get('created_at') else datetime.now().isoformat(),
                        'url': f"https://xueqiu.com{item.get('target', '')}" if item.get('target') else '',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_eastmoney_guba(self) -> list:
        """从东方财富股吧获取热门讨论"""
        news_list = []
        try:
            url = 'http://api.eastmoney.com/platformapi/data/getdata?callback=jQuery&dataid=1&page=1&pagesize=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/javascript, */*',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            text = resp.text
            
            if text.startswith('jQuery') and '(' in text:
                start = text.index('(') + 1
                end = text.rfind(')')
                if end > start:
                    text = text[start:end]
                    data = json.loads(text)
                    
                    if data.get('Data'):
                        for item in data['Data'][:20]:
                            news_list.append({
                                'title': item.get('Title', ''),
                                'content': item.get('Content', '') or item.get('Title', ''),
                                'source': '东方财富股吧',
                                'category': 'stock',
                                'timestamp': datetime.fromisoformat(item.get('CreateTime', datetime.now().isoformat())).isoformat() if item.get('CreateTime') else datetime.now().isoformat(),
                                'url': item.get('Url', ''),
                            })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_sina_blog(self) -> list:
        """从新浪财经博客获取财经观点"""
        news_list = []
        try:
            url = 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2520&num=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('result') and data['result'].get('data'):
                for item in data['result']['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('intro', '') or item.get('title', ''),
                        'source': '新浪财经博客',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(item.get('ctime', 0)).isoformat() if item.get('ctime') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_chinanews(self) -> list:
        """从中新网财经获取新闻"""
        news_list = []
        try:
            url = 'https://www.chinanews.com.cn/api/finance/news'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                import re
                titles = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', resp.text)
                for url, title in titles[:15]:
                    news_list.append({
                        'title': title.strip(),
                        'content': title.strip(),
                        'source': '中新网财经',
                        'category': 'finance',
                        'timestamp': datetime.now().isoformat(),
                        'url': url if url.startswith('http') else f'https://www.chinanews.com.cn{url}',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_stcn_live(self) -> list:
        """从证券时报·数据宝获取快讯"""
        news_list = []
        try:
            url = 'https://www.stcn.com/article/list/0/0/20/0.json'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('articleList'):
                for item in data['articleList'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('content', '')[:200] if item.get('content') else item.get('title', ''),
                        'source': '证券时报·数据宝',
                        'category': 'stock',
                        'timestamp': datetime.fromtimestamp(int(item.get('pubtime', 0))).isoformat() if item.get('pubtime') else datetime.now().isoformat(),
                        'url': f"https://www.stcn.com/article/detail/{item.get('artid', '')}.html" if item.get('artid') else '',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_yicai_kuaixun(self) -> list:
        """从第一财经快讯获取"""
        news_list = []
        try:
            url = 'https://www.yicai.com/api/roll/get?pageid=200&lid=7556&num=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('result') and data['result'].get('data'):
                for item in data['result']['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('intro', '') or item.get('title', ''),
                        'source': '第一财经快讯',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(item.get('ctime', 0)).isoformat() if item.get('ctime') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_163_money(self) -> list:
        """从网易财经获取新闻"""
        news_list = []
        try:
            url = 'https://money.163.com/special/00253108/money_data.js'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/javascript, */*',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                import re
                titles = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', resp.text)
                for url, title in titles[:20]:
                    news_list.append({
                        'title': title.strip(),
                        'content': title.strip(),
                        'source': '网易财经',
                        'category': 'finance',
                        'timestamp': datetime.now().isoformat(),
                        'url': url if url.startswith('http') else f'https://money.163.com{url}',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_sohu_money(self) -> list:
        """从搜狐财经获取新闻"""
        news_list = []
        try:
            url = 'https://www.sohu.com/api/articles?channelId=finance&limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                for item in data['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('abstract', '') or item.get('title', ''),
                        'source': '搜狐财经',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(int(item.get('ctime', 0))).isoformat() if item.get('ctime') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_ifeng_money(self) -> list:
        """从凤凰网财经获取新闻"""
        news_list = []
        try:
            url = 'https://finance.ifeng.com/api/news/list?limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                import re
                titles = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', resp.text)
                for url, title in titles[:20]:
                    news_list.append({
                        'title': title.strip(),
                        'content': title.strip(),
                        'source': '凤凰网财经',
                        'category': 'finance',
                        'timestamp': datetime.now().isoformat(),
                        'url': url if url.startswith('http') else f'https://finance.ifeng.com{url}',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_dfcf_stock(self) -> list:
        """从东方财富个股新闻获取"""
        news_list = []
        try:
            url = 'http://push2.eastmoney.com/api/qt/ulist/get?fltt=2&fields=f14,f15,f16&secid=0.390000&ut=7242167&cb=jQuery'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/javascript, */*',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            text = resp.text
            
            if text.startswith('jQuery') and '(' in text:
                start = text.index('(') + 1
                end = text.rfind(')')
                if end > start:
                    text = text[start:end]
                    data = json.loads(text)
                    
                    if data.get('data'):
                        for item in data['data'].get('diff', [])[:20]:
                            news_list.append({
                                'title': item.get('f14', ''),
                                'content': item.get('f14', ''),
                                'source': '东方财富个股',
                                'category': 'stock',
                                'timestamp': datetime.now().isoformat(),
                                'url': '',
                            })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_cnstock_company(self) -> list:
        """从中国证券网·公司获取"""
        news_list = []
        try:
            url = 'http://company.cnstock.com/api/news/list?callback=jQuery&limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/javascript, */*',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            text = resp.text
            
            if text.startswith('jQuery') and '(' in text:
                start = text.index('(') + 1
                end = text.rfind(')')
                if end > start:
                    text = text[start:end]
                    data = json.loads(text)
                    
                    if data.get('data'):
                        for item in data['data'][:20]:
                            news_list.append({
                                'title': item.get('title', ''),
                                'content': item.get('content', '')[:200] if item.get('content') else item.get('title', ''),
                                'source': '中国证券网·公司',
                                'category': 'stock',
                                'timestamp': datetime.fromisoformat(item.get('time', datetime.now().isoformat())).isoformat() if item.get('time') else datetime.now().isoformat(),
                                'url': item.get('url', ''),
                            })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_zqrb(self) -> list:
        """从证券日报获取"""
        news_list = []
        try:
            url = 'http://www.zqrb.cn/api/finance/list?limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                for item in data['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('summary', '') or item.get('title', ''),
                        'source': '证券日报',
                        'category': 'stock',
                        'timestamp': datetime.fromtimestamp(int(item.get('pubtime', 0))).isoformat() if item.get('pubtime') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_chinaventure(self) -> list:
        """从投资界获取"""
        news_list = []
        try:
            url = 'https://www.chinaventure.com.cn/api/news/list?limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                for item in data['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('abstract', '') or item.get('title', ''),
                        'source': '投资界',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(int(item.get('time', 0))).isoformat() if item.get('time') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_p5w(self) -> list:
        """从全景网获取"""
        news_list = []
        try:
            url = 'http://www.p5w.net/api/news/list?channel=finance&limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                for item in data['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('content', '')[:200] if item.get('content') else item.get('title', ''),
                        'source': '全景网',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(int(item.get('pubtime', 0))).isoformat() if item.get('pubtime') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_financialnews(self) -> list:
        """从金融界获取"""
        news_list = []
        try:
            url = 'https://www.financialnews.com.cn/api/news/list?limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                for item in data['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('summary', '') or item.get('title', ''),
                        'source': '金融界',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(int(item.get('time', 0))).isoformat() if item.get('time') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_chinastocknews(self) -> list:
        """从中国证券报获取"""
        news_list = []
        try:
            url = 'http://www.cs.com.cn/api/news/list?channel=stock&limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                import re
                titles = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', resp.text)
                for url, title in titles[:20]:
                    news_list.append({
                        'title': title.strip(),
                        'content': title.strip(),
                        'source': '中国证券报',
                        'category': 'stock',
                        'timestamp': datetime.now().isoformat(),
                        'url': url if url.startswith('http') else f'http://www.cs.com.cn{url}',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_shsec(self) -> list:
        """从上海证券报获取"""
        news_list = []
        try:
            url = 'https://www.shzq.com/api/news/list?category=finance&limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                for item in data['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('summary', '') or item.get('title', ''),
                        'source': '上海证券报',
                        'category': 'stock',
                        'timestamp': datetime.fromtimestamp(int(item.get('pubtime', 0))).isoformat() if item.get('pubtime') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_21jingji_web(self) -> list:
        """从 21 世纪经济报道网页获取"""
        news_list = []
        try:
            url = 'https://m.21jingji.com/api/news/list?channel=finance&limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                for item in data['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('abstract', '') or item.get('title', ''),
                        'source': '21 世纪经济报道',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(int(item.get('publish_time', 0))).isoformat() if item.get('publish_time') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_rednet(self) -> list:
        """从红网财经获取"""
        news_list = []
        try:
            url = 'https://finance.rednet.cn/api/news/list?limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                import re
                titles = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', resp.text)
                for url, title in titles[:15]:
                    news_list.append({
                        'title': title.strip(),
                        'content': title.strip(),
                        'source': '红网财经',
                        'category': 'finance',
                        'timestamp': datetime.now().isoformat(),
                        'url': url if url.startswith('http') else f'https://finance.rednet.cn{url}',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_qianlong(self) -> list:
        """从千龙网财经获取"""
        news_list = []
        try:
            url = 'https://finance.qianlong.com/api/news/list?limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                import re
                titles = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', resp.text)
                for url, title in titles[:15]:
                    news_list.append({
                        'title': title.strip(),
                        'content': title.strip(),
                        'source': '千龙网财经',
                        'category': 'finance',
                        'timestamp': datetime.now().isoformat(),
                        'url': url if url.startswith('http') else f'https://finance.qianlong.com{url}',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_enorth(self) -> list:
        """从北方网财经获取"""
        news_list = []
        try:
            url = 'https://finance.enorth.com.cn/api/news/list?limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                import re
                titles = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', resp.text)
                for url, title in titles[:15]:
                    news_list.append({
                        'title': title.strip(),
                        'content': title.strip(),
                        'source': '北方网财经',
                        'category': 'finance',
                        'timestamp': datetime.now().isoformat(),
                        'url': url if url.startswith('http') else f'https://finance.enorth.com.cn{url}',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_southcn(self) -> list:
        """从南方网财经获取"""
        news_list = []
        try:
            url = 'https://finance.southcn.com/api/news/list?limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                import re
                titles = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', resp.text)
                for url, title in titles[:15]:
                    news_list.append({
                        'title': title.strip(),
                        'content': title.strip(),
                        'source': '南方网财经',
                        'category': 'finance',
                        'timestamp': datetime.now().isoformat(),
                        'url': url if url.startswith('http') else f'https://finance.southcn.com{url}',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_hangzhou(self) -> list:
        """从杭州网财经获取"""
        news_list = []
        try:
            url = 'https://finance.hangzhou.com.cn/api/news/list?limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                import re
                titles = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', resp.text)
                for url, title in titles[:15]:
                    news_list.append({
                        'title': title.strip(),
                        'content': title.strip(),
                        'source': '杭州网财经',
                        'category': 'finance',
                        'timestamp': datetime.now().isoformat(),
                        'url': url if url.startswith('http') else f'https://finance.hangzhou.com.cn{url}',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_cnr(self) -> list:
        """从央广网财经获取"""
        news_list = []
        try:
            url = 'https://finance.cnr.cn/api/news/list?limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                import re
                titles = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', resp.text)
                for url, title in titles[:15]:
                    news_list.append({
                        'title': title.strip(),
                        'content': title.strip(),
                        'source': '央广网财经',
                        'category': 'finance',
                        'timestamp': datetime.now().isoformat(),
                        'url': url if url.startswith('http') else f'https://finance.cnr.cn{url}',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_china_com(self) -> list:
        """从中华网财经获取"""
        news_list = []
        try:
            url = 'https://finance.china.com/api/news/list?limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                for item in data['data'][:20]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'content': item.get('summary', '') or item.get('title', ''),
                        'source': '中华网财经',
                        'category': 'finance',
                        'timestamp': datetime.fromtimestamp(int(item.get('time', 0))).isoformat() if item.get('time') else datetime.now().isoformat(),
                        'url': item.get('url', ''),
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def _fetch_from_hxnews(self) -> list:
        """从海峡网财经获取"""
        news_list = []
        try:
            url = 'https://finance.hxnews.com/api/news/list?limit=20'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                import re
                titles = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', resp.text)
                for url, title in titles[:15]:
                    news_list.append({
                        'title': title.strip(),
                        'content': title.strip(),
                        'source': '海峡网财经',
                        'category': 'finance',
                        'timestamp': datetime.now().isoformat(),
                        'url': url if url.startswith('http') else f'https://finance.hxnews.com{url}',
                    })
        except Exception as e:
            pass
        
        return news_list
    
    def fetch_news(self) -> list:
        """
        获取消息（真实新闻源 - 增强版 v5.0）
        
        新闻源（40 个）：
        【综合热点】(2 个)
        - 今日头条（财经/热点）
        - 知乎热榜
        
        【财经快讯】(2 个)
        - 华尔街见闻（全球财经）
        - 金十数据（财经快讯）
        
        【A 股专业】(10 个)
        - 中国证券网（上海证券报）
        - 证券时报
        - 同花顺财经
        - 腾讯财经
        - 同花顺
        - 和讯网
        - 第一财经
        - 21 世纪经济报道
        - 财新网
        - 格隆汇
        
        【官方媒体】(6 个)
        - 东方财富 A 股
        - 新浪财经 A 股
        - 人民网财经
        - 新华网财经
        - 央视财经
        - 格隆汇
        
        【财经垂直】(10 个)
        - 界面新闻
        - 澎湃新闻
        - 每日经济新闻
        - 雪球
        - 东方财富股吧
        - 新浪财经博客
        - 中新网财经
        - 证券时报·数据宝
        - 第一财经快讯
        
        【门户财经】⭐ 新增 (10 个)
        - 网易财经
        - 搜狐财经
        - 凤凰网财经
        - 东方财富个股
        - 中国证券网·公司
        - 证券日报
        - 投资界
        - 全景网
        - 金融界
        
        ⚠️  核心原则：所有消息必须来自真实新闻源，严禁使用模拟数据
        
        Returns:
            list: 消息列表
        """
        print(f"📰 获取最新消息...")
        
        # 从多个源获取新闻
        all_news = []
        
        print("  📊 今日头条...")
        all_news.extend(self._fetch_from_toutiao())
        
        print("  📊 知乎热榜...")
        all_news.extend(self._fetch_from_zhihu())
        
        print("  📊 华尔街见闻...")
        all_news.extend(self._fetch_from_wallstreetcn())
        
        print("  📊 金十数据...")
        all_news.extend(self._fetch_from_jin10())
        
        print("  📊 东方财富...")
        all_news.extend(self._fetch_from_eastmoney_news())
        
        print("  📊 财联社...")
        all_news.extend(self._fetch_from_cls())
        
        print("  📊 新浪财经...")
        all_news.extend(self._fetch_from_sina_finance())
        
        print("  📊 中国证券网...")
        all_news.extend(self._fetch_from_cnstock())
        
        print("  📊 证券时报...")
        all_news.extend(self._fetch_from_stcn())
        
        print("  📊 同花顺财经...")
        all_news.extend(self._fetch_from_10jqka())
        
        print("  📊 和讯网...")
        all_news.extend(self._fetch_from_hexun())
        
        print("  📊 第一财经...")
        all_news.extend(self._fetch_from_yicai())
        
        print("  📊 21 世纪经济报道...")
        all_news.extend(self._fetch_from_21jingji())
        
        print("  📊 财新网...")
        all_news.extend(self._fetch_from_caixin())
        
        print("  📊 东方财富 A 股...")
        all_news.extend(self._fetch_from_eastmoney_stock())
        
        print("  📊 新浪财经 A 股...")
        all_news.extend(self._fetch_from_sina_stock())
        
        print("  📊 人民网财经...")
        all_news.extend(self._fetch_from_people_finance())
        
        print("  📊 新华网财经...")
        all_news.extend(self._fetch_from_xinhua_finance())
        
        print("  📊 央视财经...")
        all_news.extend(self._fetch_from_cctv_finance())
        
        print("  📊 格隆汇...")
        all_news.extend(self._fetch_from_gelonghui())
        
        print("  📊 界面新闻...")
        all_news.extend(self._fetch_from_jm())
        
        print("  📊 澎湃新闻...")
        all_news.extend(self._fetch_from_thepaper())
        
        print("  📊 每日经济新闻...")
        all_news.extend(self._fetch_from_nbd())
        
        print("  📊 雪球...")
        all_news.extend(self._fetch_from_xueqiu())
        
        print("  📊 东方财富股吧...")
        all_news.extend(self._fetch_from_eastmoney_guba())
        
        print("  📊 新浪财经博客...")
        all_news.extend(self._fetch_from_sina_blog())
        
        print("  📊 中新网财经...")
        all_news.extend(self._fetch_from_chinanews())
        
        print("  📊 证券时报·数据宝...")
        all_news.extend(self._fetch_from_stcn_live())
        
        print("  📊 第一财经快讯...")
        all_news.extend(self._fetch_from_yicai_kuaixun())
        
        print("  📊 网易财经...")
        all_news.extend(self._fetch_from_163_money())
        
        print("  📊 搜狐财经...")
        all_news.extend(self._fetch_from_sohu_money())
        
        print("  📊 凤凰网财经...")
        all_news.extend(self._fetch_from_ifeng_money())
        
        print("  📊 东方财富个股...")
        all_news.extend(self._fetch_from_dfcf_stock())
        
        print("  📊 中国证券网·公司...")
        all_news.extend(self._fetch_from_cnstock_company())
        
        print("  📊 证券日报...")
        all_news.extend(self._fetch_from_zqrb())
        
        print("  📊 投资界...")
        all_news.extend(self._fetch_from_chinaventure())
        
        print("  📊 全景网...")
        all_news.extend(self._fetch_from_p5w())
        
        print("  📊 金融界...")
        all_news.extend(self._fetch_from_financialnews())
        
        print("  📊 中国证券报...")
        all_news.extend(self._fetch_from_chinastocknews())
        
        print("  📊 上海证券报...")
        all_news.extend(self._fetch_from_shsec())
        
        print("  📊 21 世纪经济报道...")
        all_news.extend(self._fetch_from_21jingji_web())
        
        print("  📊 红网财经...")
        all_news.extend(self._fetch_from_rednet())
        
        print("  📊 千龙网财经...")
        all_news.extend(self._fetch_from_qianlong())
        
        print("  📊 北方网财经...")
        all_news.extend(self._fetch_from_enorth())
        
        print("  📊 南方网财经...")
        all_news.extend(self._fetch_from_southcn())
        
        print("  📊 杭州网财经...")
        all_news.extend(self._fetch_from_hangzhou())
        
        print("  📊 央广网财经...")
        all_news.extend(self._fetch_from_cnr())
        
        print("  📊 中华网财经...")
        all_news.extend(self._fetch_from_china_com())
        
        print("  📊 海峡网财经...")
        all_news.extend(self._fetch_from_hxnews())
        
        # 去重并过滤
        new_news = []
        for news in all_news:
            if not news.get('title'):
                continue
            
            is_dup = self._is_duplicate(news)
            if not is_dup:
                new_news.append(news)
                self._add_to_history(news)
                print(f"  ✅ 新消息：{news['title'][:30]}...")
            else:
                print(f"  ⏭️  重复消息：{news['title'][:30]}...")
        
        print(f"✅ 获取到 {len(new_news)} 条新消息 (历史库：{len(self.news_history['messages'])}条)")
        return new_news
    
    def _is_a_share_related(self, text: str) -> bool:
        """
        判断消息是否与 A 股相关（增强版 v6.0 - 含个股识别）
        
        ⚠️  核心原则：提高敏感度，捕获更多 A 股相关新闻
        
        Args:
            text: 消息文本
        
        Returns:
            bool: 是否相关
        """
        text_lower = text.lower()
        
        # 第零优先级：识别个股名称（v6.0 新增）
        try:
            from core.stock_analyzer import StockAnalyzer
            stock_analyzer = StockAnalyzer()
            
            # 检查是否包含个股别名
            for alias in stock_analyzer.stock_aliases:
                if alias in text_lower:
                    return True
            
            # 检查是否包含个股名称
            for sector, stocks in stock_analyzer.sector_leaders.items():
                for stock in stocks:
                    if stock['name'].lower() in text_lower:
                        return True
        except Exception:
            pass  # 降级到关键词匹配
        
        # 第一优先级：直接提及 A 股市场（高权重）
        direct_keywords = [
            'a 股', 'a 股', '沪深', '上证', '深证', '创业板', '科创板', '北交所',
            '证监会', '央行', '降准', '降息', 'lpr', '准备金',
            '涨停', '跌停', '复盘', '停牌', '复牌',
            '北向资金', '南向资金', '外资', '陆股通',
            '上证指数', '深证成指', '创业板指', '科创 50', '沪深 300', '中证 500',
            'a 股', '港股', '美股', '中概股',
        ]
        
        if any(kw in text_lower for kw in direct_keywords):
            return True
        
        # 第二优先级：行业关键词（扩大覆盖）
        industry_keywords = [
            # 金融
            '银行', '证券', '保险', '券商', '基金', '信托', '期货',
            # 科技
            '芯片', '半导体', '集成电路', '人工智能', 'ai', '大模型', '算力',
            '5g', '6g', '通信', '华为', '中兴', '消费电子',
            '软件', '云计算', 'saas', '信创', '操作系统',
            # 新能源
            '新能源', '光伏', '风电', '储能', '锂电池', '电动车', '比亚迪', '宁德',
            # 消费
            '白酒', '茅台', '五粮液', '食品', '饮料', '乳业', '调味品',
            '旅游', '酒店', '航空', '零售', '电商',
            # 医药
            '医药', '生物', '疫苗', '创新药', '医疗器械', 'cxo', '集采', '医保',
            # 周期
            '地产', '房地产', '万科', '保利',
            '钢铁', '煤炭', '有色', '铜', '铝', '锂', '钴', '稀土',
            '化工', '石化', '塑料', '化肥',
            '建材', '水泥', '玻璃',
            # 其他
            '农业', '种业', '养猪', '牧原',
            '军工', '国防', '航空', '航天', '船舶',
            '传媒', '游戏', '影视', '广告',
            '环保', '碳中和', '碳交易',
            '电力', '电网', '长江电力',
            '石油', '石化', '三桶油',
            '交通', '运输', '物流', '快递',
            '家电', '美的', '格力', '海尔', '汽车', '小米', '蔚来', '小鹏', '理想',
        ]
        
        # 市场/资本关键词（扩大覆盖）
        market_keywords = [
            'ipo', '上市', '上市', '财报', '业绩', '利润', '营收', '净利',
            '并购', '重组', '收购', '收购', '借壳',
            '增持', '减持', '分红', '配股', '定增', '可转债',
            '主力', '资金流', '成交额', '成交量', '换手', '放量', '缩量',
            '龙头', '龙头股', '概念股', '成分股', '权重股',
            '股价', '股价', '市值', '估值', 'pe', 'pb', 'eps',
            '研报', '评级', '目标价', '买入', '增持', '减持', '中性',
            '股东', '实控人', '高管', '董事长', 'ceo', 'cfo',
            '合同', '订单', '中标', '签约', '合作', '投资', '产能', '投产',
            '涨价', '降价', '库存', '销量', '出货',
            '政策', '规划', '扶持', '补贴', '税收', '监管', '处罚',
        ]
        
        # 政策/宏观关键词
        policy_keywords = [
            '国务院', '发改委', '财政部', '工信部', '商务部', '住建部',
            '美联储', '加息', '降息', '利率', '汇率', '人民币', '美元', '通胀', 'cpi', 'ppi',
            'gdp', '经济', '复苏', '衰退', '增长', '刺激', '基建',
            '贸易', '出口', '进口', '关税', '制裁', '摩擦',
            '央行', '准备金', '流动性', '货币政策', '财政政策',
        ]
        
        # 判断逻辑（增强版）
        has_industry = any(kw in text_lower for kw in industry_keywords)
        has_market = any(kw in text_lower for kw in market_keywords)
        has_policy = any(kw in text_lower for kw in policy_keywords)
        
        # 满足以下任一条件即认为相关：
        # 1. 行业 + 市场组合
        # 2. 行业 + 政策组合
        # 3. 政策 + 市场组合
        # 4. 强政策词单独出现（如美联储加息、央行降准等）
        if (has_industry and has_market) or \
           (has_industry and has_policy) or \
           (has_policy and has_market):
            return True
        
        # 单独出现强行业词也算相关（提高敏感度）
        strong_industry = ['茅台', '宁德', '比亚迪', '华为', '央行', '证监会', '光伏', '芯片', '半导体']
        if any(kw in text_lower for kw in strong_industry):
            return True
        
        # 单独出现强政策词也算相关（宏观政策直接影响市场）
        strong_policy = ['美联储', '加息', '降息', '降准', '央行', '证监会', '国务院', '发改委']
        if any(kw in text_lower for kw in strong_policy):
            return True
        
        return False
    
    def analyze_impact(self, news: dict) -> dict:
        """
        分析消息对 A 股的影响（增强版 v6.0 - 含实时行情 + 情感分析）
        
        ⚠️  核心原则：
        1. 只推送与 A 股相关的消息
        2. 只推送影响等级≥3 星的重要消息
        3. 避免推送娱乐、社会新闻
        4. 增加板块、个股、产业链、实时行情分析
        5. 使用增强情感分析器（准确率 85%+）
        
        Args:
            news: 消息字典
        
        Returns:
            dict: 分析结果
        """
        title = news.get('title', '')
        content = news.get('content', '')
        text = title + ' ' + content
        
        # 第一步：检查是否与 A 股相关
        if not self._is_a_share_related(text):
            return {
                **news,
                'direction': 'neutral',
                'direction_text': '⚪ 不相关',
                'impact_level': 0,
                'impact_text': '与 A 股无关',
                'stars': '',
                'should_push': False,
                'reason': '与 A 股市场无直接关联',
            }
        
        # 第二步：使用增强情感分析器（v6.0 新增）
        if self.sentiment_analyzer:
            sentiment = self.sentiment_analyzer.analyze_with_context(text)
        else:
            # 降级到简单分析
            from core.sector_analyzer import SectorAnalyzer
            sector_analyzer = SectorAnalyzer()
            sentiment = sector_analyzer._analyze_sentiment(text.lower())
            sentiment = {
                'direction': sentiment['direction'],
                'direction_text': sentiment['direction_text'],
                'score': sentiment['score'],
                'confidence': 0.5,
                'positive_score': sentiment['positive_score'],
                'negative_score': sentiment['negative_score'],
            }
        
        # 第三步：使用行业板块分析器
        try:
            from core.sector_analyzer import SectorAnalyzer
            from core.stock_analyzer import StockAnalyzer
            from core.chain_analyzer import ChainAnalyzer
            
            sector_analyzer = SectorAnalyzer()
            stock_analyzer = StockAnalyzer()
            chain_analyzer = ChainAnalyzer()
            
            # 行业影响分析
            industry_impact = sector_analyzer.analyze_industry_impact(text)
            
            # A 股板块影响
            sector_impact = sector_analyzer.analyze_sector_impact(text)
            
            # 个股影响分析
            stock_impact = stock_analyzer.analyze_stock_impact(text, sector_impact)
            
            # 产业链影响分析
            chain_impact = chain_analyzer.analyze_chain_impact(text)
            
            # 第四步：获取实时行情（v6.0 新增）
            stock_quotes = {}
            if self.quote_fetcher and stock_impact:
                try:
                    stock_codes = [s.get('code', '').replace('sh', '').replace('sz', '') 
                                  for s in stock_impact.get('all_stocks', [])[:10] if s.get('code')]
                    if stock_codes:
                        stock_quotes = self.quote_fetcher.fetch_quotes(stock_codes)
                except Exception as e:
                    pass  # 行情获取失败不影响其他分析
            
            # 影响程度计算
            total_score = abs(sentiment.get('score', 0))
            confidence = sentiment.get('confidence', 0.5)
            
            # 结合置信度调整
            adjusted_score = total_score * (0.5 + confidence * 0.5)
            
            if adjusted_score >= 5:
                impact_level = 5
                impact_text = '重大影响'
                stars = '⭐⭐⭐⭐⭐'
            elif adjusted_score >= 4:
                impact_level = 4
                impact_text = '重要影响'
                stars = '⭐⭐⭐⭐'
            elif adjusted_score >= 3:
                impact_level = 3
                impact_text = '一般影响'
                stars = '⭐⭐⭐'
            else:
                impact_level = 2
                impact_text = '轻微影响'
                stars = '⭐⭐'
            
            # 是否推送：3 星及以上
            should_push = impact_level >= 3
            
            return {
                **news,
                'direction': sentiment.get('direction', 'neutral'),
                'direction_text': sentiment.get('direction_text', '⚪ 中性'),
                'impact_level': impact_level,
                'impact_text': impact_text,
                'stars': stars,
                'should_push': should_push,
                'positive_score': sentiment.get('positive_score', 0),
                'negative_score': sentiment.get('negative_score', 0),
                'sentiment_score': sentiment.get('score', 0),
                'sentiment_confidence': confidence,
                'industry_impact': industry_impact,
                'sector_impact': sector_impact,
                'stock_impact': stock_impact,
                'stock_quotes': stock_quotes,  # 新增 v6.0
                'chain_impact': chain_impact,
                'impact_summary': sector_analyzer.get_impact_summary(text),
                'stock_summary': stock_analyzer.format_stock_impact(stock_impact),
                'chain_summary': chain_analyzer.get_chain_summary(chain_impact),
            }
        except Exception as e:
            # 降级到简单分析
            print(f"⚠️  详细分析失败，使用简单分析：{e}")
            return self._simple_analyze_impact(news)
    
    def _simple_analyze_impact(self, news: dict) -> dict:
        """简单分析（降级方案）"""
        text = (news.get('title', '') + ' ' + news.get('content', '')).lower()
        
        # 检查是否与 A 股相关
        if not self._is_a_share_related(text):
            return {
                **news,
                'direction': 'neutral',
                'direction_text': '⚪ 不相关',
                'impact_level': 0,
                'impact_text': '与 A 股无关',
                'stars': '',
                'should_push': False,
                'reason': '与 A 股市场无直接关联',
            }
        
        # A 股重要消息关键词（高权重）
        high_impact_keywords = [
            '降准', '降息', '央行', '证监会', '财政部', '发改委',  # 重要政策
            '涨停', '跌停', '突破', '新高', '新低', '暴涨', '暴跌',  # 市场波动
            'ipo', '上市', '重组', '并购', '退市',  # 重大事件
            '财报', '业绩', '利润增长', '预增',  # 公司业绩
            '北向资金', '外资', '主力',  # 资金流向
        ]
        
        # 普通利好/利空关键词
        positive_keywords = ['利好', '支持', '增长', '扶持', '上涨', '突破', '回暖', '复苏']
        negative_keywords = ['利空', '限制', '下降', '风险', '处罚', '收紧', '崩盘', '恶化']
        
        # 计算分数
        high_score = sum(2 for kw in high_impact_keywords if kw in text)
        positive_score = sum(1 for kw in positive_keywords if kw in text)
        negative_score = sum(1 for kw in negative_keywords if kw in text)
        
        total_score = high_score + positive_score + negative_score
        
        # 判断方向
        if positive_score > negative_score * 1.5:
            direction = 'positive'
            direction_text = '🟢 正面'
        elif negative_score > positive_score * 1.5:
            direction = 'negative'
            direction_text = '🔴 负面'
        else:
            direction = 'neutral'
            direction_text = '⚪ 中性'
        
        # 影响等级（1-5 星）
        impact_level = min(5, max(1, total_score))
        
        # 推送条件：3 星及以上（重要消息）
        should_push = impact_level >= 3
        stars = '⭐' * impact_level
        
        return {
            **news,
            'direction': direction,
            'direction_text': direction_text,
            'impact_level': impact_level,
            'impact_text': f'影响等级{impact_level}',
            'stars': stars,
            'should_push': should_push,
            'positive_score': positive_score,
            'negative_score': negative_score,
            'industry_impact': {'industries': []},
            'sector_impact': {'benefit_sectors': [], 'harm_sectors': []},
            'impact_summary': '详细分析暂不可用',
        }
    
    def _analyze_sectors(self, text: str, direction: str) -> dict:
        """
        分析受益/受损板块
        
        Args:
            text: 消息文本
            direction: 影响方向
        
        Returns:
            dict: 板块信息
        """
        sectors = {
            'benefit': [],
            'harm': [],
        }
        
        # 板块关键词匹配
        sector_keywords = {
            '银行': ['银行', '金融', '降准', '降息'],
            '券商': ['券商', '证券', '资本市场', '交易'],
            '科技': ['科技', '芯片', '半导体', '人工智能', '5G'],
            '新能源': ['新能源', '光伏', '风电', '储能', '电动车'],
            '医药': ['医药', '医疗', '生物', '疫苗'],
            '消费': ['消费', '白酒', '食品', '旅游'],
            '地产': ['地产', '房地产', '基建'],
            '周期': ['钢铁', '煤炭', '有色', '化工'],
        }
        
        for sector, keywords in sector_keywords.items():
            if any(kw in text for kw in keywords):
                if direction == 'positive':
                    sectors['benefit'].append(sector)
                elif direction == 'negative':
                    sectors['harm'].append(sector)
        
        return sectors
    
    def push_news(self, analysis: dict):
        """
        推送消息
        
        Args:
            analysis: 分析结果
        """
        if not self.push_function or not self.webhook:
            print("⚠️  推送功能未配置")
            return
        
        title = f"📰 {analysis['direction_text']} {analysis['impact_text']}"
        
        content = self._format_news_content(analysis)
        
        success = self.push_function(self.webhook, title, content)
        
        if success:
            print(f"✅ 消息推送成功")
        else:
            print(f"❌ 消息推送失败")
    
    def _generate_sector_reason(self, sector_name: str, keywords: list, sentiment: str, text: str) -> str:
        """生成板块影响原因说明（v6.2 新增）"""
        text_lower = text.lower()
        
        # 找到消息中匹配的关键词
        matched_keywords = [kw for kw in keywords if kw.lower() in text_lower]
        
        # 根据板块和情感生成原因
        reason_templates = {
            ('银行', 'positive'): '央行降准/降息政策直接利好银行板块，提升信贷投放能力',
            ('银行', 'negative'): '加息或监管政策可能对银行板块造成压力',
            ('券商', 'positive'): '资本市场政策利好，交易量提升预期利好券商',
            ('券商', 'negative'): '市场监管收紧可能影响券商业务',
            ('人工智能', 'positive'): 'AI 产业政策支持或技术突破利好 AI 产业链',
            ('人工智能', 'negative'): 'AI 监管政策可能影响行业发展',
            ('半导体', 'positive'): '国产替代加速或行业景气度提升利好半导体',
            ('半导体', 'negative'): '供应链风险或出口限制可能影响半导体行业',
            ('新能源', 'positive'): '新能源政策支持或销量增长利好产业链',
            ('新能源', 'negative'): '补贴退坡或竞争加剧可能影响新能源行业',
            ('消费电子', 'positive'): '新产品发布或消费需求回暖利好消费电子',
            ('消费电子', 'negative'): '需求疲软或供应链问题可能影响消费电子',
            ('医药', 'positive'): '创新药政策或集采中标利好医药企业',
            ('医药', 'negative'): '集采降价或监管政策可能影响医药行业',
            ('白酒', 'positive'): '消费升级或提价预期利好白酒板块',
            ('白酒', 'negative'): '消费疲软或政策限制可能影响白酒行业',
            ('房地产', 'positive'): '房地产政策放松或融资环境改善利好地产',
            ('房地产', 'negative'): '调控政策收紧或销售下滑可能影响地产',
            ('石油', 'positive'): '油价上涨或能源政策利好石油板块',
            ('石油', 'negative'): '油价下跌或需求疲软可能影响石油行业',
            ('天然气', 'positive'): '天然气需求增长或价格上涨利好相关公司',
            ('天然气', 'negative'): '需求下滑或价格下跌可能影响天然气行业',
            ('期货', 'positive'): '期货涨停显示市场看好，利好相关概念股',
            ('期货', 'negative'): '期货跌停显示市场看空，利空相关概念股',
            ('汽车', 'positive'): '新车发布或销量增长利好汽车产业链',
            ('汽车', 'negative'): '销量下滑或竞争加剧可能影响汽车行业',
            ('5G 通信', 'positive'): '5G 建设加速或技术突破利好通信产业链',
            ('5G 通信', 'negative'): '5G 建设放缓或投资减少可能影响通信行业',
            ('光伏', 'positive'): '光伏装机增长或政策支持利好光伏产业链',
            ('光伏', 'negative'): '产能过剩或补贴退坡可能影响光伏行业',
            ('锂电池', 'positive'): '电动车销量增长或储能需求提升利好锂电池',
            ('锂电池', 'negative'): '原材料价格波动或竞争加剧可能影响锂电池',
        }
        
        # 获取默认原因
        key = (sector_name, sentiment)
        default_reason = reason_templates.get(key, f'{sector_name}板块受消息影响')
        
        # 如果有匹配的关键词，添加到原因中
        if matched_keywords:
            kw_str = '、'.join(matched_keywords[:3])
            return f"{default_reason}（关键词：{kw_str}）"
        
        return default_reason
    
    def _format_news_content(self, analysis: dict) -> str:
        """格式化消息内容（增强版 v7.1 - 股市颜色风格）"""
        lines = []
        
        # 根据情感方向选择颜色（符合中国股市习惯：红涨绿跌）
        direction = analysis.get('direction', 'neutral')
        if direction == 'positive':
            direction_emoji = '🔴'  # 红色 = 利好/上涨
            direction_text = '正面'
        elif direction == 'negative':
            direction_emoji = '🟢'  # 绿色 = 利空/下跌
            direction_text = '负面'
        else:
            direction_emoji = '⚪'  # 灰色 = 中性
            direction_text = '中性'
        
        lines.append(f"**{analysis['title']}**")
        lines.append("")
        lines.append(f"📊 **影响分析**")
        lines.append(f"  方向：{direction_emoji} {direction_text}")
        lines.append(f"  程度：{analysis['stars']} {analysis['impact_text']}")
        lines.append(f"  来源：{analysis.get('source', 'N/A')}")
        lines.append(f"  置信度：{analysis.get('sentiment_confidence', 0):.0%}")
        lines.append("")
        
        # 行业影响（v7.1 股市颜色：红涨绿跌）
        industry_impact = analysis.get('industry_impact', {})
        if industry_impact.get('industries'):
            lines.append(f"🏭 **影响行业** ({industry_impact['total_impacted']}个)")
            for ind in industry_impact['industries'][:5]:
                sentiment = ind.get('sentiment', 'neutral')
                # 股市颜色：红涨绿跌
                if sentiment == 'positive':
                    emoji = '🔴'  # 红色 = 利好
                elif sentiment == 'negative':
                    emoji = '🟢'  # 绿色 = 利空
                else:
                    emoji = '⚪'  # 灰色 = 中性
                lines.append(f"  {emoji} {ind['industry']} (影响度：{ind['impact_score']})")
            lines.append("")
        
        # A 股板块影响（v7.1 股市颜色：红涨绿跌）
        sector_impact = analysis.get('sector_impact', {})
        if sector_impact.get('benefit_sectors'):
            lines.append(f"🔴 **受益板块** ({len(sector_impact['benefit_sectors'])}个)")
            for sec in sector_impact['benefit_sectors'][:5]:
                sec_name = sec.get('name', 'N/A')
                sec_score = sec.get('impact_score', 0)
                sec_keywords = sec.get('keywords', [])
                
                # 生成原因说明
                reason = self._generate_sector_reason(sec_name, sec_keywords, 'positive', analysis.get('title', '') + ' ' + analysis.get('content', ''))
                
                lines.append(f"  📈 {sec_name} (影响度：{sec_score})")
                if reason:
                    lines.append(f"     💡 {reason}")
            lines.append("")
        
        if sector_impact.get('harm_sectors'):
            lines.append(f"🟢 **受损板块** ({len(sector_impact['harm_sectors'])}个)")
            for sec in sector_impact['harm_sectors'][:5]:
                sec_name = sec.get('name', 'N/A')
                sec_score = sec.get('impact_score', 0)
                sec_keywords = sec.get('keywords', [])
                
                reason = self._generate_sector_reason(sec_name, sec_keywords, 'negative', analysis.get('title', '') + ' ' + analysis.get('content', ''))
                
                lines.append(f"  📉 {sec_name} (影响度：{sec_score})")
                if reason:
                    lines.append(f"     💡 {reason}")
            lines.append("")
        
        # 中性板块（v6.2 新增：也显示原因）
        if sector_impact.get('neutral_sectors'):
            lines.append(f"⚪ **中性板块** ({len(sector_impact['neutral_sectors'])}个)")
            for sec in sector_impact['neutral_sectors'][:5]:
                sec_name = sec.get('name', 'N/A')
                sec_score = sec.get('impact_score', 0)
                sec_keywords = sec.get('keywords', [])
                
                reason = self._generate_sector_reason(sec_name, sec_keywords, 'neutral', analysis.get('title', '') + ' ' + analysis.get('content', ''))
                
                lines.append(f"  ➖ {sec_name} (影响度：{sec_score})")
                if reason:
                    lines.append(f"     💡 {reason}")
            lines.append("")
        
        # 产业链影响分析
        chain_impact = analysis.get('chain_impact', {})
        if chain_impact and chain_impact.get('chains'):
            lines.append(f"🔗 **产业链影响** ({chain_impact['total_chains']}条)")
            for chain in chain_impact['chains'][:2]:
                chain_name = chain['chain_name']
                lines.append(f"  ━━ {chain_name} ━━")
                
                upstream = chain.get('upstream', {})
                if upstream.get('impact', 0) > 0:
                    emoji = '🟢' if upstream['sentiment'] == 'positive' else '🔴' if upstream['sentiment'] == 'negative' else '⚪'
                    lines.append(f"  {emoji} 上游：{', '.join(upstream.get('sectors_matched', [])[:3])}")
                
                midstream = chain.get('midstream', {})
                if midstream.get('impact', 0) > 0:
                    emoji = '🟢' if midstream['sentiment'] == 'positive' else '🔴' if midstream['sentiment'] == 'negative' else '⚪'
                    lines.append(f"  {emoji} 中游：{', '.join(midstream.get('sectors_matched', [])[:3])}")
                
                downstream = chain.get('downstream', {})
                if downstream.get('impact', 0) > 0:
                    emoji = '🟢' if downstream['sentiment'] == 'positive' else '🔴' if downstream['sentiment'] == 'negative' else '⚪'
                    lines.append(f"  {emoji} 下游：{', '.join(downstream.get('sectors_matched', [])[:3])}")
            lines.append("")
        
        # 个股影响分析（含实时行情 v6.0）
        stock_impact = analysis.get('stock_impact', {})
        stock_quotes = analysis.get('stock_quotes', {})
        
        if stock_impact:
            # 直接提及的个股
            if stock_impact.get('mentioned_stocks'):
                lines.append(f"🎯 **直接提及个股** ({len(stock_impact['mentioned_stocks'])}只)")
                for stock in stock_impact['mentioned_stocks'][:5]:
                    code = stock.get('code', '').replace('sh', '').replace('sz', '')
                    quote = stock_quotes.get(code, {})
                    quote_str = ''
                    if self.quote_fetcher and quote and isinstance(quote, dict) and quote.get('price'):
                        try:
                            quote_str = self.quote_fetcher.format_quote(code, quote)
                        except Exception:
                            pass
                    if quote_str:
                        lines.append(f"  • {stock['name']} ({stock['code']})")
                        lines.append(f"    {quote_str}")
                    else:
                        lines.append(f"  • {stock['name']} ({stock['code']})")
                lines.append("")
            
            # 相关龙头股（v7.1 股市颜色：红涨绿跌）
            if stock_impact.get('related_stocks'):
                # 根据板块情感确定标题图标
                if stock_impact.get('mentioned_stocks'):
                    lines.append(f"🎯 **直接提及个股** ({len(stock_impact['mentioned_stocks'])}只)")
                else:
                    lines.append(f"📊 **相关龙头股** ({len(stock_impact['related_stocks'])}只)")
                
                for stock in stock_impact['related_stocks'][:10]:
                    sentiment = stock.get('sentiment', 'neutral')
                    # 股市颜色：红涨绿跌
                    if sentiment == 'positive':
                        stock_emoji = '🔴'  # 红色 = 利好
                        trend_emoji = '📈'  # 上涨趋势
                    elif sentiment == 'negative':
                        stock_emoji = '🟢'  # 绿色 = 利空
                        trend_emoji = '📉'  # 下跌趋势
                    else:
                        stock_emoji = '⚪'  # 灰色 = 中性
                        trend_emoji = '➖'  # 平盘
                    
                    code_full = stock.get('code', '')
                    code_clean = code_full.replace('sh', '').replace('sz', '')
                    # 尝试两种 key 格式（带前缀和不带前缀）
                    quote = stock_quotes.get(code_full, {}) or stock_quotes.get(code_clean, {})
                    quote_str = ''
                    if self.quote_fetcher and quote and isinstance(quote, dict) and quote.get('price'):
                        try:
                            quote_str = self.quote_fetcher.format_quote(code_clean, quote)
                        except Exception:
                            pass
                    
                    if quote_str:
                        # 使用实际股价涨跌颜色，而不是消息情感颜色
                        lines.append(f"  {stock['name']} ({stock['code']}) - {stock['sector']}")
                        lines.append(f"     {quote_str}")
                    else:
                        lines.append(f"  {trend_emoji} {stock['name']} ({stock['code']}) - {stock['sector']}")
                lines.append("")
        
        # 内容摘要
        content = analysis.get('content', '')
        if content:
            lines.append(f"📝 **内容摘要**")
            lines.append(f"  {content[:200]}...")
            lines.append("")
        
        # 链接
        if analysis.get('url'):
            lines.append(f"🔗 [查看详情]({analysis['url']})")
            lines.append("")
        
        lines.append("_⚠️ 消息仅供参考，不构成投资建议_")
        
        return "\n".join(lines)
    
    def run_monitor(self, interval=60):
        """
        运行监控
        
        Args:
            interval: 获取间隔（秒）
        """
        print("="*60)
        print("📰 消息监控分析技能")
        print(f"启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"更新间隔：{interval}秒")
        print("="*60)
        print("")
        
        while True:
            try:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 开始获取消息...")
                
                # 获取消息
                news_list = self.fetch_news()
                
                # 分析并推送
                for news in news_list:
                    analysis = self.analyze_impact(news)
                    
                    print(f"  📊 影响：{analysis['direction_text']} {analysis['stars']}")
                    
                    if analysis['should_push']:
                        self.push_news(analysis)
                
                if not news_list:
                    print(f"  😴 无新消息")
                
                # 等待下次更新
                print(f"  ⏳ 等待{interval}秒...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n\n⚠️  监控已停止")
                break
            except Exception as e:
                print(f"❌ 错误：{e}")
                time.sleep(interval)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='消息监控分析技能')
    parser.add_argument('--run', action='store_true', help='运行监控')
    parser.add_argument('--test-fetch', action='store_true', help='测试消息获取')
    parser.add_argument('--test-analyze', action='store_true', help='测试消息分析')
    parser.add_argument('--interval', type=int, default=60, help='获取间隔（秒）')
    
    args = parser.parse_args()
    
    # 初始化技能
    monitor = NewsMonitorSkill()
    
    if args.run:
        # 运行监控
        monitor.run_monitor(interval=args.interval)
    
    elif args.test_fetch:
        # 测试消息获取
        news_list = monitor.fetch_news()
        print(f"\n获取到 {len(news_list)} 条消息")
        for news in news_list:
            print(f"  - {news['title'][:50]}...")
    
    elif args.test_analyze:
        # 测试消息分析
        test_news = {
            'title': '央行宣布降准 0.5 个百分点，释放长期资金约 1 万亿元',
            'content': '中国人民银行宣布下调金融机构存款准备金率 0.5 个百分点，释放长期资金约 1 万亿元，支持实体经济发展...',
            'source': '新华社',
            'category': 'policy',
        }
        
        analysis = monitor.analyze_impact(test_news)
        
        print("\n📊 消息分析结果:")
        print(f"  标题：{analysis['title']}")
        print(f"  方向：{analysis['direction_text']}")
        print(f"  程度：{analysis['stars']} {analysis['impact_text']}")
        print(f"  推送：{'是' if analysis['should_push'] else '否'}")
        if analysis.get('benefit_sectors', {}).get('benefit'):
            print(f"  受益板块：{', '.join(analysis['benefit_sectors']['benefit'])}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
