#!/usr/bin/env python3
"""
多数据源股票数据获取模块 v2.0 - 增强版
为 v8.0-Financial-Enhanced 工作流添加更多数据源

新增数据源:
1. 同花顺 - 资金流排名
2. 网易财经 - 历史行情
3. 雪球 - 实时行情
4. 东方财富 - 个股资金流
5. 腾讯财经 - 增强版（多批次）
6. 新浪财经 - 备用实时行情

用法:
    python3 data_sources_v2.py --source all --top 50
    python3 data_sources_v2.py --source ths --top 20
    python3 data_sources_v2.py --source netease --codes 600519,000858
"""

import sys
import requests
import json
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed


class MultiSourceFetcher:
    """多数据源股票获取器 v2.0"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        # 通用请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        
        # 请求延迟（避免被封）
        self.request_delay = 0.1
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def _get_stock_prefix(self, code: str) -> str:
        """获取股票代码前缀"""
        if code.startswith('6'):
            return 'sh'
        elif code.startswith('0') or code.startswith('3'):
            return 'sz'
        return 'sh'
    
    # =========================================================================
    # 1. 同花顺资金流
    # =========================================================================
    
    def get_ths_flow_rank(self, top_n: int = 50) -> List[Dict]:
        """
        从同花顺获取资金流排名（API 版）
        
        Args:
            top_n: 获取数量
        
        Returns:
            list: 资金流排名数据
        """
        print("[同花顺] 获取资金流排名...")
        
        # 使用同花顺 API
        url = "http://data.10jqka.com.cn/fund/rank/"
        
        try:
            headers = self.headers.copy()
            headers['Referer'] = 'http://data.10jqka.com.cn/'
            
            resp = self.session.get(url, headers=headers, timeout=15)
            
            if resp.status_code != 200:
                # 降级：使用东方财富
                print("[同花顺] 降级使用东方财富")
                return self.get_em_individual_flow(top_n)
            
            # 解析 HTML
            content = resp.text
            stocks = []
            
            # 匹配股票代码
            pattern = r'data-code="(\d{6})"[^>]*>([^<]+)<'
            matches = re.findall(pattern, content)
            
            for code, name in matches[:top_n]:
                stocks.append({
                    'code': code,
                    'name': name.strip(),
                    'source': 'ths',
                    'crawl_time': datetime.now().isoformat(),
                })
            
            print(f"[同花顺] 获取 {len(stocks)} 条")
            return stocks
            
        except Exception as e:
            print(f"[同花顺] 失败：{e}")
            # 降级使用东方财富
            return self.get_em_individual_flow(top_n)
        
        finally:
            time.sleep(self.request_delay)
    
    # =========================================================================
    # 2. 网易财经历史行情
    # =========================================================================
    
    def get_netease_history(self, code: str, days: int = 60) -> Optional[Dict]:
        """
        从网易财经获取历史行情
        
        Args:
            code: 股票代码
            days: 天数
        
        Returns:
            dict: 股票历史数据
        """
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
            resp.raise_for_status()
            
            content = resp.content.decode('gbk')
            lines = content.strip().split('\n')[1:]  # 跳过表头
            
            if not lines:
                return None
            
            # 解析最新数据
            latest = lines[0].split(',')
            if len(latest) >= 10:
                return {
                    'code': code,
                    'close': float(latest[1]) if latest[1] else 0,
                    'open': float(latest[3]) if latest[3] else 0,
                    'high': float(latest[2]) if latest[2] else 0,
                    'low': float(latest[3]) if latest[3] else 0,
                    'volume': int(float(latest[9])) if latest[9] else 0,
                    'turnover': float(latest[8]) if latest[8] else 0,
                    'change_pct': float(latest[6]) if latest[6] else 0,
                    'source': 'netease',
                    'crawl_time': datetime.now().isoformat(),
                }
        
        except Exception as e:
            print(f"[网易] {code} 失败：{e}")
        
        finally:
            time.sleep(self.request_delay)
        
        return None
    
    # =========================================================================
    # 3. 雪球实时行情
    # =========================================================================
    
    def get_xueqiu_quote(self, codes: List[str]) -> List[Dict]:
        """
        从雪球获取实时行情
        
        Args:
            codes: 股票代码列表
        
        Returns:
            list: 行情数据
        """
        print(f"[雪球] 获取 {len(codes)} 只股票行情...")
        
        # 转换股票代码格式
        stock_symbols = []
        for code in codes:
            prefix = self._get_stock_prefix(code)
            stock_symbols.append(f'{prefix}{code}')
        
        url = "https://stock.xueqiu.com/v5/stock/quote.json"
        params = {
            'symbol': ','.join(stock_symbols),
        }
        
        try:
            # 需要 cookie（从浏览器获取）
            headers = self.headers.copy()
            headers['Cookie'] = 'xq_is_login=1; xq_r_token=abc123'
            
            resp = self.session.get(url, params=params, headers=headers, timeout=10)
            
            if resp.status_code != 200:
                print("[雪球] 需要登录，跳过")
                return []
            
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
            
            print(f"[雪球] 获取 {len(stocks)} 条")
            return stocks
            
        except Exception as e:
            print(f"[雪球] 失败：{e}")
            return []
        
        finally:
            time.sleep(self.request_delay)
    
    # =========================================================================
    # 4. 东方财富个股资金流
    # =========================================================================
    
    def get_em_individual_flow(self, top_n: int = 50) -> List[Dict]:
        """
        从东方财富获取个股资金流排名
        
        Args:
            top_n: 获取数量
        
        Returns:
            list: 资金流排名
        """
        print("[东方财富] 获取个股资金流排名...")
        
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
            
            print(f"[东方财富] 获取 {len(stocks)} 条")
            return stocks
            
        except Exception as e:
            print(f"[东方财富] 失败：{e}")
            return []
        
        finally:
            time.sleep(self.request_delay)
    
    # =========================================================================
    # 5. 腾讯财经增强版（多批次并行）
    # =========================================================================
    
    def get_tencent_batch(self, codes: List[str], batch_size: int = 50) -> List[Dict]:
        """
        腾讯财经批量获取（增强版）
        
        Args:
            codes: 股票代码列表
            batch_size: 批次大小
        
        Returns:
            list: 行情数据
        """
        print(f"[腾讯财经] 批量获取 {len(codes)} 只股票...")
        
        all_stocks = []
        
        # 分批请求
        for i in range(0, len(codes), batch_size):
            batch = codes[i:i+batch_size]
            batch_symbols = [f"{self._get_stock_prefix(c)}{c}" for c in batch]
            
            url = "http://qt.gtimg.cn/q=" + ','.join(batch_symbols)
            
            try:
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
                
                print(f"  批次 {i//batch_size + 1}: 获取 {len(batch)} 只")
                
            except Exception as e:
                print(f"[腾讯] 批次 {i//batch_size + 1} 失败：{e}")
            
            time.sleep(self.request_delay)
        
        print(f"[腾讯财经] 共获取 {len(all_stocks)} 只")
        return all_stocks
    
    # =========================================================================
    # 6. 新浪财经备用
    # =========================================================================
    
    def get_sina_quote(self, codes: List[str]) -> List[Dict]:
        """
        新浪财经实时行情（备用数据源）
        
        Args:
            codes: 股票代码列表
        
        Returns:
            list: 行情数据
        """
        print(f"[新浪财经] 获取 {len(codes)} 只股票...")
        
        all_stocks = []
        
        for code in codes:
            prefix = self._get_stock_prefix(code)
            url = f"http://hq.sinajs.cn/list={prefix}{code}"
            
            try:
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
                
            except Exception as e:
                print(f"[新浪] {code} 失败：{e}")
            
            time.sleep(self.request_delay)
        
        print(f"[新浪财经] 获取 {len(all_stocks)} 条")
        return all_stocks
    
    # =========================================================================
    # 聚合方法
    # =========================================================================
    
    def fetch_all_sources(self, top_n: int = 50) -> Dict[str, List[Dict]]:
        """
        从所有数据源获取数据
        
        Args:
            top_n: 每个数据源获取数量
        
        Returns:
            dict: 各数据源数据
        """
        results = {}
        
        # 1. 同花顺
        ths_data = self.get_ths_flow_rank(top_n)
        if ths_data:
            results['ths'] = ths_data
        
        # 2. 东方财富
        em_data = self.get_em_individual_flow(top_n)
        if em_data:
            results['eastmoney'] = em_data
        
        # 3. 腾讯财经（需要代码列表）
        # 先从其他源获取代码
        all_codes = set()
        for source_data in results.values():
            for stock in source_data:
                if 'code' in stock:
                    all_codes.add(stock['code'])
        
        if all_codes:
            tencent_data = self.get_tencent_batch(list(all_codes)[:100], batch_size=50)
            if tencent_data:
                results['tencent'] = tencent_data
        
        return results
    
    def merge_results(self, sources_data: Dict[str, List[Dict]]) -> List[Dict]:
        """
        合并多数据源结果
        
        Args:
            sources_data: 各数据源数据
        
        Returns:
            list: 合并后的数据
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
                
                # 添加源数据
                merged[code]['sources'].append(source)
                
                # 合并字段
                for key, value in stock.items():
                    if key not in ['code', 'name', 'sources', 'crawl_time']:
                        source_key = f"{source}_{key}"
                        merged[code][source_key] = value
        
        return list(merged.values())


# CLI 入口
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='多数据源股票数据获取 v2.0')
    parser.add_argument('--source', default='all', choices=['ths', 'netease', 'xueqiu', 'eastmoney', 'tencent', 'sina', 'all'])
    parser.add_argument('--top', type=int, default=50)
    parser.add_argument('--codes', type=str, help='股票代码列表，逗号分隔')
    
    args = parser.parse_args()
    
    fetcher = MultiSourceFetcher()
    
    if args.source == 'all':
        results = fetcher.fetch_all_sources(args.top)
        print(f"\n总计 {len(results)} 个数据源")
        for source, data in results.items():
            print(f"  - {source}: {len(data)} 条")
    
    elif args.source == 'ths':
        data = fetcher.get_ths_flow_rank(args.top)
        print(f"\n同花顺：{len(data)} 条")
    
    elif args.source == 'eastmoney':
        data = fetcher.get_em_individual_flow(args.top)
        print(f"\n东方财富：{len(data)} 条")
    
    elif args.source == 'tencent' and args.codes:
        codes = args.codes.split(',')
        data = fetcher.get_tencent_batch(codes)
        print(f"\n腾讯：{len(data)} 条")
    
    elif args.source == 'sina' and args.codes:
        codes = args.codes.split(',')
        data = fetcher.get_sina_quote(codes)
        print(f"\n新浪：{len(data)} 条")
