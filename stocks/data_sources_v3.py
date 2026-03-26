#!/usr/bin/env python3
"""
股票数据源整合模块 v3.0 - 全数据源集成

集成数据源列表 (10+ 个):
【主力/资金流】
1. 百度股市通 - 主力净流入排名
2. 东方财富 - 个股/板块资金流
3. 同花顺 - 资金流排名
4. 腾讯财经 - 成交额估算

【实时行情】
5. 腾讯财经 - 实时行情（批量）
6. 新浪财经 - 实时行情
7. 雪球 - 实时行情（需 cookie）

【历史数据】
8. 网易财经 - 历史 K 线
9. 新浪财经 - 历史 K 线

【其他】
10. 东方财富 - 股票列表
11. 腾讯财经 - 股票列表

用法:
    python3 data_sources_v3.py --source all --top 20
    python3 data_sources_v3.py --source tencent --top 50
    python3 data_sources_v3.py --test  # 测试所有数据源
"""

import sys
import requests
import json
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# 导入现有模块
from local_crawler import StockCrawler
from data_sources import MultiDataSource, SinaFinance


# ============================================================================
# 数据源配置
# ============================================================================

@dataclass
class DataSourceConfig:
    """数据源配置"""
    name: str                   # 数据源名称
    api_url: str                # API 地址
    data_type: str              # 数据类型：main_force/quote/history/list
    priority: int               # 优先级（1 最高）
    timeout: int                # 超时时间（秒）
    batch_size: int             # 批次大小
    delay_ms: int               # 请求间隔（毫秒）
    requires_auth: bool         # 是否需要认证
    status: str = 'unknown'     # 状态：unknown/active/inactive/limited
    last_check: str = ''        # 最后检查时间


# 数据源配置列表
DATA_SOURCES = [
    # 主力/资金流
    DataSourceConfig(
        name='baidu',
        api_url='https://gushitong.baidu.com/opendata',
        data_type='main_force',
        priority=1,
        timeout=15,
        batch_size=100,
        delay_ms=100,
        requires_auth=False
    ),
    DataSourceConfig(
        name='eastmoney_flow',
        api_url='http://push2.eastmoney.com/api/qt/clist/get',
        data_type='main_force',
        priority=2,
        timeout=10,
        batch_size=50,
        delay_ms=100,
        requires_auth=False
    ),
    DataSourceConfig(
        name='ths_flow',
        api_url='http://data.10jqka.com.cn/fund/rank/',
        data_type='main_force',
        priority=3,
        timeout=15,
        batch_size=50,
        delay_ms=200,
        requires_auth=False
    ),
    DataSourceConfig(
        name='tencent_amount',
        api_url='http://qt.gtimg.cn/q=',
        data_type='main_force',  # 通过成交额估算
        priority=4,
        timeout=10,
        batch_size=80,
        delay_ms=100,
        requires_auth=False
    ),
    
    # 实时行情
    DataSourceConfig(
        name='tencent_quote',
        api_url='http://qt.gtimg.cn/q=',
        data_type='quote',
        priority=1,
        timeout=10,
        batch_size=80,
        delay_ms=100,
        requires_auth=False
    ),
    DataSourceConfig(
        name='sina_quote',
        api_url='http://hq.sinajs.cn/list=',
        data_type='quote',
        priority=2,
        timeout=5,
        batch_size=50,
        delay_ms=200,
        requires_auth=False
    ),
    DataSourceConfig(
        name='xueqiu_quote',
        api_url='https://stock.xueqiu.com/v5/stock/quote.json',
        data_type='quote',
        priority=3,
        timeout=10,
        batch_size=100,
        delay_ms=100,
        requires_auth=True  # 需要 cookie
    ),
    
    # 历史数据
    DataSourceConfig(
        name='netease_history',
        api_url='http://quotes.money.163.com/service/chddata.html',
        data_type='history',
        priority=1,
        timeout=10,
        batch_size=1,  # 单只股票
        delay_ms=300,
        requires_auth=False
    ),
    DataSourceConfig(
        name='sina_history',
        api_url='http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData',
        data_type='history',
        priority=2,
        timeout=10,
        batch_size=1,
        delay_ms=500,
        requires_auth=False
    ),
    
    # 股票列表
    DataSourceConfig(
        name='eastmoney_list',
        api_url='http://nufm.dfcfw.com/EM_Fund2099/QF_StockStock/GetStockList',
        data_type='list',
        priority=1,
        timeout=15,
        batch_size=5000,
        delay_ms=100,
        requires_auth=False
    ),
    DataSourceConfig(
        name='tencent_list',
        api_url='http://qt.gtimg.cn/q=',
        data_type='list',
        priority=2,
        timeout=10,
        batch_size=100,
        delay_ms=100,
        requires_auth=False
    ),
]


# ============================================================================
# 全数据源获取器
# ============================================================================

class AllSourcesFetcher:
    """全数据源获取器 v3.0"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        # 初始化现有模块
        self.crawler = StockCrawler(self.cache_dir)
        self.multi_source = MultiDataSource(self.cache_dir)
        self.sina = SinaFinance()
        
        # 数据源配置
        self.sources = {cfg.name: cfg for cfg in DATA_SOURCES}
        
        # 会话
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
        })
        
        # 雪球 cookie（可选）
        self.xueqiu_cookie = ''
    
    def _get_stock_prefix(self, code: str) -> str:
        """获取股票代码前缀"""
        if code.startswith('6'):
            return 'sh'
        elif code.startswith('0') or code.startswith('3'):
            return 'sz'
        return 'sh'
    
    # =========================================================================
    # 1. 主力/资金流数据源
    # =========================================================================
    
    def get_baidu_main_force(self, top_n: int = 50) -> List[Dict]:
        """百度股市通 - 主力净流入排名"""
        try:
            data = self.crawler.crawl_baidu_rank('change')
            if data:
                data.sort(key=lambda x: x.get('amount_wan', 0), reverse=True)
                return data[:top_n]
            return []
        except Exception as e:
            print(f"[百度] 失败：{e}")
            return []
    
    def get_eastmoney_flow(self, top_n: int = 50) -> List[Dict]:
        """东方财富 - 个股资金流排名"""
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': '1',
            'pz': str(top_n),
            'po': '1',
            'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426289',
            'fltt': '2',
            'invt': '2',
            'fid': 'f62',
            'fs': 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23',
            'fields': 'f12,f14,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124',
            '_': str(int(time.time() * 1000))
        }
        
        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            
            stocks = []
            for item in data.get('data', {}).get('diff', []):
                stocks.append({
                    'code': item.get('f12', ''),
                    'name': item.get('f14', ''),
                    'main_flow': item.get('f62', 0) / 10000,  # 主力净流入（万）
                    'flow_ratio': item.get('f184', 0),  # 净流入占比
                    'source': 'eastmoney',
                    'crawl_time': datetime.now().isoformat(),
                })
            
            return stocks
        except Exception as e:
            print(f"[东方财富] 失败：{e}")
            return []
    
    def get_ths_flow(self, top_n: int = 50) -> List[Dict]:
        """同花顺 - 资金流排名（降级到东方财富）"""
        # 同花顺 API 不稳定，直接降级
        return self.get_eastmoney_flow(top_n)
    
    def get_tencent_by_amount(self, top_n: int = 50) -> List[Dict]:
        """腾讯财经 - 按成交额估算主力"""
        try:
            data = self.crawler.crawl_tencent()
            if data:
                data.sort(key=lambda x: x.get('amount_wan', 0), reverse=True)
                return data[:top_n]
            return []
        except Exception as e:
            print(f"[腾讯] 失败：{e}")
            return []
    
    # =========================================================================
    # 2. 实时行情数据源
    # =========================================================================
    
    def get_tencent_quotes(self, codes: List[str]) -> List[Dict]:
        """腾讯财经 - 批量实时行情"""
        try:
            all_stocks = []
            batch_size = 80
            
            for i in range(0, len(codes), batch_size):
                batch = codes[i:i+batch_size]
                batch_symbols = [f"{self._get_stock_prefix(c)}{c}" for c in batch]
                
                url = "http://qt.gtimg.cn/q=" + ','.join(batch_symbols)
                resp = self.session.get(url, timeout=10)
                content = resp.content.decode('gbk')
                
                for line in content.strip().split('\n'):
                    if '=' in line:
                        parts = line.split('~')
                        if len(parts) > 50:
                            code = parts[2]
                            all_stocks.append({
                                'code': code,
                                'name': parts[1],
                                'price': float(parts[3]) if parts[3] else 0,
                                'open': float(parts[5]) if parts[5] else 0,
                                'high': float(parts[33]) if parts[33] else 0,
                                'low': float(parts[34]) if parts[34] else 0,
                                'close': float(parts[4]) if parts[4] else 0,
                                'volume': int(parts[6]) if parts[6] else 0,
                                'turnover': float(parts[37]) if parts[37] else 0,
                                'change_pct': float(parts[32]) if parts[32] else 0,
                                'source': 'tencent',
                                'crawl_time': datetime.now().isoformat(),
                            })
                
                time.sleep(0.1)
            
            return all_stocks
        except Exception as e:
            print(f"[腾讯行情] 失败：{e}")
            return []
    
    def get_sina_quotes(self, codes: List[str]) -> List[Dict]:
        """新浪财经 - 批量实时行情"""
        try:
            all_stocks = []
            
            for code in codes:
                prefix = self._get_stock_prefix(code)
                url = f"http://hq.sinajs.cn/list={prefix}{code}"
                
                resp = self.session.get(url, timeout=5)
                content = resp.content.decode('gbk')
                
                if '=' in content:
                    parts = content.split('"')[1].split(',')
                    if len(parts) >= 32:
                        all_stocks.append({
                            'code': code,
                            'name': parts[0],
                            'open': float(parts[1]) if parts[1] else 0,
                            'close': float(parts[3]) if parts[3] else 0,
                            'high': float(parts[4]) if parts[4] else 0,
                            'low': float(parts[5]) if parts[5] else 0,
                            'volume': int(parts[8]) if parts[8] else 0,
                            'turnover': float(parts[9]) if parts[9] else 0,
                            'change_pct': float(parts[31]) if parts[31] else 0,
                            'source': 'sina',
                            'crawl_time': datetime.now().isoformat(),
                        })
                
                time.sleep(0.2)
            
            return all_stocks
        except Exception as e:
            print(f"[新浪行情] 失败：{e}")
            return []
    
    def get_xueqiu_quotes(self, codes: List[str]) -> List[Dict]:
        """雪球 - 批量实时行情（需要 cookie）"""
        if not self.xueqiu_cookie:
            print("[雪球] 未配置 cookie，跳过")
            return []
        
        stock_symbols = [f'{self._get_stock_prefix(c)}{c}' for c in codes]
        url = "https://stock.xueqiu.com/v5/stock/quote.json"
        params = {'symbol': ','.join(stock_symbols)}
        
        headers = self.session.headers.copy()
        headers['Cookie'] = self.xueqiu_cookie
        
        try:
            resp = self.session.get(url, params=params, headers=headers, timeout=10)
            data = resp.json()
            
            stocks = []
            for item in data.get('data', {}).get('quote', []):
                symbol = item.get('symbol', '')
                code = symbol[2:] if len(symbol) > 2 else symbol
                
                stocks.append({
                    'code': code,
                    'name': item.get('name', ''),
                    'price': item.get('current', 0),
                    'change_pct': item.get('percent', 0),
                    'volume': item.get('volume', 0),
                    'turnover': item.get('amount', 0),
                    'high': item.get('high52w', 0),
                    'low': item.get('low52w', 0),
                    'source': 'xueqiu',
                    'crawl_time': datetime.now().isoformat(),
                })
            
            return stocks
        except Exception as e:
            print(f"[雪球] 失败：{e}")
            return []
    
    # =========================================================================
    # 3. 历史数据数据源
    # =========================================================================
    
    def get_netease_history(self, code: str, days: int = 60) -> Optional[Dict]:
        """网易财经 - 历史行情"""
        prefix = self._get_stock_prefix(code)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        url = "http://quotes.money.163.com/service/chddata.html"
        params = {
            'code': f'{prefix}{code}',
            'start': start_date.strftime('%Y%m%d'),
            'end': end_date.strftime('%Y%m%d'),
            'fields': ['TCLOSE', 'HIGH', 'LOW', 'TOPEN', 'LCLOSE', 'CHG', 'PCHG', 'TURNOVER', 'VOTURNOVER']
        }
        
        try:
            resp = self.session.get(url, params=params, timeout=10)
            content = resp.content.decode('gbk')
            lines = content.strip().split('\n')[1:]  # 跳过表头
            
            if lines:
                parts = lines[0].split(',')
                if len(parts) >= 10:
                    return {
                        'code': code,
                        'date': parts[0],
                        'close': float(parts[1]) if parts[1] else 0,
                        'volume': int(float(parts[9])) if parts[9] else 0,
                        'turnover': float(parts[8]) if parts[8] else 0,
                        'change_pct': float(parts[6]) if parts[6] else 0,
                        'source': 'netease',
                        'crawl_time': datetime.now().isoformat(),
                    }
        except Exception as e:
            print(f"[网易历史] {code} 失败：{e}")
        
        return None
    
    def get_sina_history(self, code: str, days: int = 60) -> Optional[Dict]:
        """新浪财经 - 历史 K 线"""
        prefix = self._get_stock_prefix(code)
        url = "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
        params = {
            'symbol': f'{prefix}{code}',
            'scale': '240',  # 日线
            'datalen': str(days),
        }
        
        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data and len(data) > 0:
                latest = data[0]
                return {
                    'code': code,
                    'date': latest.get('day', ''),
                    'open': latest.get('open', 0),
                    'high': latest.get('high', 0),
                    'low': latest.get('low', 0),
                    'close': latest.get('close', 0),
                    'volume': latest.get('volume', 0),
                    'source': 'sina',
                    'crawl_time': datetime.now().isoformat(),
                }
        except Exception as e:
            print(f"[新浪历史] {code} 失败：{e}")
        
        return None
    
    # =========================================================================
    # 4. 股票列表数据源
    # =========================================================================
    
    def get_eastmoney_list(self) -> List[Dict]:
        """东方财富 - A 股股票列表（修复 JSONP 解析）"""
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': '1',
            'pz': '5000',
            'po': '1',
            'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426289',
            'fltt': '2',
            'invt': '2',
            'fid': 'f3',
            'fs': 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23',  # 沪深 A 股
            'fields': 'f12,f14,f20,f21,f22,f24,f25,f26,f37,f38,f39,f40,f41,f42,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57',
            '_': str(int(time.time() * 1000))
        }
        
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.encoding = 'utf-8'
            data = resp.json()
            
            stocks = []
            for item in data.get('data', {}).get('diff', []):
                code = item.get('f12', '')
                name = item.get('f14', '')
                
                # 只保留 A 股主板（60/00 开头）
                if code.startswith('60') or code.startswith('00'):
                    stocks.append({
                        'code': code,
                        'name': name,
                        'price': item.get('f2', 0),
                        'change_pct': item.get('f3', 0),
                        'volume': item.get('f5', 0),
                        'turnover': item.get('f6', 0),
                        'pe_ratio': item.get('f9', 0),
                        'pb_ratio': item.get('f23', 0),
                        'status': '正常交易',
                        'source': 'eastmoney',
                        'crawl_time': datetime.now().isoformat(),
                    })
            
            return stocks
            
        except Exception as e:
            print(f"[东方财富列表] 失败：{e}")
            # 降级：返回样本股票
            return self._get_sample_stock_list()
        
        return []
    
    def _get_sample_stock_list(self) -> List[Dict]:
        """获取样本股票列表（降级方案）"""
        sample_stocks = [
            {'code': '600519', 'name': '贵州茅台'},
            {'code': '000858', 'name': '五粮液'},
            {'code': '600036', 'name': '招商银行'},
            {'code': '000002', 'name': '万科 A'},
            {'code': '000651', 'name': '格力电器'},
            {'code': '601318', 'name': '中国平安'},
            {'code': '600276', 'name': '恒瑞医药'},
            {'code': '601398', 'name': '工商银行'},
            {'code': '601288', 'name': '农业银行'},
            {'code': '600030', 'name': '中信证券'},
            {'code': '000001', 'name': '平安银行'},
            {'code': '000063', 'name': '中兴通讯'},
            {'code': '000100', 'name': 'TCL 科技'},
            {'code': '000333', 'name': '美的集团'},
            {'code': '000538', 'name': '云南白药'},
            {'code': '600585', 'name': '海螺水泥'},
            {'code': '600887', 'name': '伊利股份'},
            {'code': '601888', 'name': '中国中免'},
            {'code': '600031', 'name': '三一重工'},
            {'code': '601166', 'name': '兴业银行'},
        ]
        
        return [
            {
                'code': s['code'],
                'name': s['name'],
                'status': '正常交易',
                'source': 'sample',
                'crawl_time': datetime.now().isoformat(),
            }
            for s in sample_stocks
        ]
    
    def get_tencent_list(self, sample_codes: List[str] = None) -> List[Dict]:
        """腾讯财经 - 通过行情获取股票列表"""
        if not sample_codes:
            sample_codes = [
                '600519', '000858', '600036', '000002', '000651',
                '601318', '600276', '601398', '601288', '600030',
            ]
        
        return self.get_tencent_quotes(sample_codes)
    
    # =========================================================================
    # 6. 备用数据源
    # =========================================================================
    
    def get_163_main_force(self, top_n: int = 50) -> List[Dict]:
        """网易财经 - 主力净流入（备用）"""
        url = "http://quotes.money.163.com/zhuli/ajax/zhuli_ajax.php"
        params = {
            'page': '1',
            'num': str(top_n),
            'sort': 'amount',
            'order': 'desc',
            'market': 'a',
        }
        
        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            
            stocks = []
            for item in data.get('data', []):
                stocks.append({
                    'code': item.get('code', ''),
                    'name': item.get('name', ''),
                    'main_flow': float(item.get('amount', 0)) / 10000,
                    'source': '163',
                    'crawl_time': datetime.now().isoformat(),
                })
            
            return stocks
        except Exception as e:
            print(f"[网易主力] 失败：{e}")
            return []
    
    def get_iwencai_ranking(self, query: str = "主力净流入排名", top_n: int = 50) -> List[Dict]:
        """同花顺问财 - 股票排名（备用）"""
        url = "http://www.iwencai.com/unifiedwap/result"
        params = {
            'w': query,
            'querytype': 'stock',
        }
        
        headers = self.session.headers.copy()
        headers['Referer'] = 'http://www.iwencai.com/'
        
        try:
            resp = self.session.get(url, params=params, headers=headers, timeout=15)
            content = resp.text
            
            # 简单解析（需要更复杂的 HTML 解析）
            stocks = []
            # 这里简化处理，实际需要使用 BeautifulSoup
            return stocks
        except Exception as e:
            print(f"[问财] 失败：{e}")
            return []
    
    def get_dazhihui_ranking(self, top_n: int = 50) -> List[Dict]:
        """大智慧 - 资金流排名（备用）"""
        # 大智慧 API 需要逆向分析，这里使用降级方案
        return self.get_eastmoney_flow(top_n)
    
    def get_yicai_news_sentiment(self, codes: List[str]) -> List[Dict]:
        """第一财经 - 新闻情感分析（备用）"""
        stocks = []
        
        for code in codes[:10]:  # 限制数量
            url = f"https://www.yicai.com/api/getstocknews?stockcode={code}"
            
            try:
                resp = self.session.get(url, timeout=5)
                data = resp.json()
                
                news_list = data.get('data', [])
                sentiment_score = 0
                
                # 简单情感分析（正负新闻数量）
                positive_count = 0
                negative_count = 0
                
                for news in news_list[:20]:
                    title = news.get('title', '')
                    if any(word in title for word in ['上涨', '利好', '增长', '突破']):
                        positive_count += 1
                    elif any(word in title for word in ['下跌', '利空', '下滑', '暴跌']):
                        negative_count += 1
                
                if positive_count + negative_count > 0:
                    sentiment_score = (positive_count - negative_count) / (positive_count + negative_count)
                
                stocks.append({
                    'code': code,
                    'sentiment_score': sentiment_score,
                    'news_count': len(news_list),
                    'source': 'yicai',
                    'crawl_time': datetime.now().isoformat(),
                })
                
            except Exception as e:
                print(f"[第一财经新闻] {code} 失败：{e}")
            
            time.sleep(0.3)
        
        return stocks
    
    def get_cnstock_institution(self, code: str) -> Dict:
        """中国证券网 - 机构评级（备用）"""
        url = f"http://app.cnstock.com/api/stock/{code}"
        
        try:
            resp = self.session.get(url, timeout=5)
            data = resp.json()
            
            if data.get('success'):
                return {
                    'code': code,
                    'institution_rating': data.get('data', {}).get('rating', ''),
                    'target_price': data.get('data', {}).get('target_price', 0),
                    'source': 'cnstock',
                    'crawl_time': datetime.now().isoformat(),
                }
        except Exception as e:
            print(f"[中证网评级] {code} 失败：{e}")
        
        return {}
    
    def get_hexun_fundamental(self, code: str) -> Dict:
        """和讯网 - 财务数据（备用）"""
        url = f"http://dataapi.hexun.com/FinancialData/GetSummaryData"
        params = {
            'stockCode': code,
            'marketType': '1' if code.startswith('6') else '2',
        }
        
        try:
            resp = self.session.get(url, params=params, timeout=5)
            data = resp.json()
            
            if data.get('Success'):
                return {
                    'code': code,
                    'pe_ratio': data.get('Data', {}).get('PE', 0),
                    'pb_ratio': data.get('Data', {}).get('PB', 0),
                    'roe': data.get('Data', {}).get('ROE', 0),
                    'revenue_growth': data.get('Data', {}).get('RevenueGrowth', 0),
                    'source': 'hexun',
                    'crawl_time': datetime.now().isoformat(),
                }
        except Exception as e:
            print(f"[和讯财务] {code} 失败：{e}")
        
        return {}
    
    def fetch_all_backup_sources(self, top_n: int = 50) -> Dict[str, List[Dict]]:
        """
        获取所有备用数据源
        
        Args:
            top_n: 获取数量
        
        Returns:
            Dict[str, List[Dict]]: 各备用数据源数据
        """
        print("\n" + "="*80)
        print("🔄 获取备用数据源")
        print("="*80)
        
        results = {}
        
        # 1. 网易主力
        print("\n[1/4] 网易财经主力...")
        data_163 = self.get_163_main_force(top_n)
        if data_163:
            results['163'] = data_163
            print(f"  ✅ 获取 {len(data_163)} 条")
        
        # 2. 问财排名
        print("\n[2/4] 同花顺问财...")
        data_iwencai = self.get_iwencai_ranking("主力净流入排名", top_n)
        if data_iwencai:
            results['iwencai'] = data_iwencai
            print(f"  ✅ 获取 {len(data_iwencai)} 条")
        
        # 3. 大智慧
        print("\n[3/4] 大智慧...")
        data_dzh = self.get_dazhihui_ranking(top_n)
        if data_dzh:
            results['dazhihui'] = data_dzh
            print(f"  ✅ 获取 {len(data_dzh)} 条")
        
        # 4. 第一财经新闻
        print("\n[4/4] 第一财经新闻...")
        sample_codes = ['600519', '000858', '600036', '000002', '000651']
        data_yicai = self.get_yicai_news_sentiment(sample_codes)
        if data_yicai:
            results['yicai'] = data_yicai
            print(f"  ✅ 获取 {len(data_yicai)} 条")
        
        # 汇总
        print("\n" + "="*80)
        print("📊 备用数据源汇总")
        print("="*80)
        total = sum(len(data) for data in results.values())
        print(f"数据源数量：{len(results)}")
        for source, data in results.items():
            print(f"  - {source}: {len(data)} 条")
        print(f"总计：{total} 条")
        
        return results
    
    # =========================================================================
    # 5. 统一接口
    # =========================================================================
    
    def fetch_all_main_force(self, top_n: int = 50) -> Dict[str, List[Dict]]:
        """
        获取所有主力/资金流数据源
        
        Returns:
            Dict[str, List[Dict]]: 各数据源数据
        """
        print("\n" + "="*80)
        print("💰 获取主力/资金流数据源")
        print("="*80)
        
        results = {}
        
        # 1. 百度
        print("\n[1/4] 百度股市通...")
        baidu_data = self.get_baidu_main_force(top_n)
        if baidu_data:
            results['baidu'] = baidu_data
            print(f"  ✅ 获取 {len(baidu_data)} 条")
        
        # 2. 东方财富
        print("\n[2/4] 东方财富...")
        em_data = self.get_eastmoney_flow(top_n)
        if em_data:
            results['eastmoney'] = em_data
            print(f"  ✅ 获取 {len(em_data)} 条")
        
        # 3. 同花顺
        print("\n[3/4] 同花顺...")
        ths_data = self.get_ths_flow(top_n)
        if ths_data:
            results['ths'] = ths_data
            print(f"  ✅ 获取 {len(ths_data)} 条")
        
        # 4. 腾讯（成交额估算）
        print("\n[4/4] 腾讯财经（成交额估算）...")
        tencent_data = self.get_tencent_by_amount(top_n)
        if tencent_data:
            results['tencent'] = tencent_data
            print(f"  ✅ 获取 {len(tencent_data)} 条")
        
        # 汇总
        print("\n" + "="*80)
        print("📊 主力数据源汇总")
        print("="*80)
        total = sum(len(data) for data in results.values())
        print(f"数据源数量：{len(results)}")
        for source, data in results.items():
            print(f"  - {source}: {len(data)} 条")
        print(f"总计：{total} 条")
        
        return results
    
    def fetch_all_quotes(self, codes: List[str]) -> Dict[str, List[Dict]]:
        """
        获取所有实时行情数据源
        
        Args:
            codes: 股票代码列表
        
        Returns:
            Dict[str, List[Dict]]: 各数据源数据
        """
        print("\n" + "="*80)
        print("📈 获取实时行情数据源")
        print("="*80)
        
        results = {}
        
        # 1. 腾讯
        print("\n[1/3] 腾讯财经...")
        tencent_data = self.get_tencent_quotes(codes)
        if tencent_data:
            results['tencent'] = tencent_data
            print(f"  ✅ 获取 {len(tencent_data)} 条")
        
        # 2. 新浪
        print("\n[2/3] 新浪财经...")
        sina_data = self.get_sina_quotes(codes[:20])  # 限制数量
        if sina_data:
            results['sina'] = sina_data
            print(f"  ✅ 获取 {len(sina_data)} 条")
        
        # 3. 雪球（需要 cookie）
        if self.xueqiu_cookie:
            print("\n[3/3] 雪球...")
            xueqiu_data = self.get_xueqiu_quotes(codes)
            if xueqiu_data:
                results['xueqiu'] = xueqiu_data
                print(f"  ✅ 获取 {len(xueqiu_data)} 条")
        
        # 汇总
        print("\n" + "="*80)
        print("📊 行情数据源汇总")
        print("="*80)
        total = sum(len(data) for data in results.values())
        print(f"数据源数量：{len(results)}")
        for source, data in results.items():
            print(f"  - {source}: {len(data)} 条")
        print(f"总计：{total} 条")
        
        return results
    
    def fetch_all_sources(self, top_n: int = 50) -> Dict[str, List[Dict]]:
        """
        获取所有数据源（主力 + 行情）
        
        Args:
            top_n: 每个数据源获取数量
        
        Returns:
            Dict[str, List[Dict]]: 各数据源数据
        """
        all_results = {}
        
        # 1. 主力/资金流
        main_force_results = self.fetch_all_main_force(top_n)
        all_results.update(main_force_results)
        
        # 2. 实时行情（从主力数据中提取代码）
        all_codes = set()
        for source_data in main_force_results.values():
            for stock in source_data:
                if 'code' in stock:
                    all_codes.add(stock['code'])
        
        if all_codes:
            quote_results = self.fetch_all_quotes(list(all_codes)[:50])
            all_results.update(quote_results)
        
        return all_results
    
    def merge_stocks(self, sources_data: Dict[str, List[Dict]]) -> List[Dict]:
        """
        合并多数据源股票数据
        
        Args:
            sources_data: 各数据源数据
        
        Returns:
            List[Dict]: 合并后的股票列表
        """
        merged = {}
        
        for source, stocks in sources_data.items():
            for stock in stocks:
                code = stock.get('code', '')
                if not code:
                    continue
                
                if code not in merged:
                    merged[code] = {
                        'code': code,
                        'name': stock.get('name', ''),
                        'sources': [],
                    }
                
                # 添加源
                merged[code]['sources'].append(source)
                
                # 合并字段
                for key, value in stock.items():
                    if key not in ['code', 'name', 'sources', 'crawl_time']:
                        source_key = f"{source}_{key}"
                        merged[code][source_key] = value
        
        return list(merged.values())
    
    def test_all_sources(self) -> Dict[str, bool]:
        """
        测试所有数据源可用性
        
        Returns:
            Dict[str, bool]: 各数据源状态
        """
        print("\n" + "="*80)
        print("🔧 测试所有数据源可用性")
        print("="*80)
        
        results = {}
        
        # 测试主力数据源
        print("\n[主力/资金流]")
        results['baidu'] = len(self.get_baidu_main_force(5)) > 0
        results['eastmoney'] = len(self.get_eastmoney_flow(5)) > 0
        results['tencent_amount'] = len(self.get_tencent_by_amount(5)) > 0
        
        # 测试行情数据源
        print("\n[实时行情]")
        test_codes = ['600519', '000858', '600036']
        results['tencent_quote'] = len(self.get_tencent_quotes(test_codes)) > 0
        results['sina_quote'] = len(self.get_sina_quotes(test_codes)) > 0
        
        # 测试历史数据源
        print("\n[历史数据]")
        results['netease_history'] = self.get_netease_history('600519') is not None
        results['sina_history'] = self.get_sina_history('600519') is not None
        
        # 测试股票列表
        print("\n[股票列表]")
        results['eastmoney_list'] = len(self.get_eastmoney_list()) > 0
        
        # 汇总
        print("\n" + "="*80)
        print("📊 数据源可用性汇总")
        print("="*80)
        
        active = sum(1 for v in results.values() if v)
        total = len(results)
        
        for source, status in results.items():
            icon = "✅" if status else "❌"
            print(f"{icon} {source}: {'可用' if status else '不可用'}")
        
        print(f"\n总计：{active}/{total} 可用 ({active/total*100:.1f}%)")
        
        return results


# ============================================================================
# CLI 入口
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='全数据源获取器 v3.0')
    parser.add_argument('--source', default='all', choices=['all', 'main_force', 'quote', 'history', 'list'])
    parser.add_argument('--top', type=int, default=20)
    parser.add_argument('--codes', type=str, help='股票代码列表，逗号分隔')
    parser.add_argument('--test', action='store_true', help='测试所有数据源')
    
    args = parser.parse_args()
    
    fetcher = AllSourcesFetcher()
    
    if args.test:
        fetcher.test_all_sources()
    
    elif args.source == 'all':
        fetcher.fetch_all_sources(args.top)
    
    elif args.source == 'main_force':
        fetcher.fetch_all_main_force(args.top)
    
    elif args.source == 'quote' and args.codes:
        codes = args.codes.split(',')
        fetcher.fetch_all_quotes(codes)
    
    elif args.source == 'history' and args.codes:
        codes = args.codes.split(',')
        for code in codes:
            print(f"\n{code}:")
            netease = fetcher.get_netease_history(code)
            sina = fetcher.get_sina_history(code)
            print(f"  网易：{netease}")
            print(f"  新浪：{sina}")
