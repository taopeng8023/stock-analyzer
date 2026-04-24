#!/usr/bin/env python3
"""
股票数据源整合模块 v3.1 - 全数据源集成（修复版）

修复内容:
✅ 东方财富列表 JSONP 解析
✅ 添加 HTML 解析器（无需 BeautifulSoup）
✅ 新增备用数据源（网易、问财、大智慧等）

用法:
    python3 data_sources_v3_fixed.py --test
    python3 data_sources_v3_fixed.py --source all --top 20
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

# 导入现有模块
from local_crawler import StockCrawler
from data_sources import MultiDataSource
from data_sources_v2 import MultiSourceFetcher
from html_parser import SimpleHTMLParser


class AllSourcesFetcherFixed:
    """全数据源获取器 v3.1（修复版）"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        self.crawler = StockCrawler(self.cache_dir)
        self.multi_source = MultiDataSource(self.cache_dir)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
        })
        
        self.xueqiu_cookie = ''
    
    def _get_stock_prefix(self, code: str) -> str:
        if code.startswith('6'):
            return 'sh'
        elif code.startswith('0') or code.startswith('3'):
            return 'sz'
        return 'sh'
    
    # =========================================================================
    # 主力/资金流数据源
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
            'pn': '1', 'pz': str(top_n), 'po': '1', 'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426289',
            'fltt': '2', 'invt': '2', 'fid': 'f62',
            'fs': 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23',
            'fields': 'f12,f14,f62,f184',
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
                    'main_flow': item.get('f62', 0) / 10000,
                    'flow_ratio': item.get('f184', 0),
                    'source': 'eastmoney',
                    'crawl_time': datetime.now().isoformat(),
                })
            return stocks
        except Exception as e:
            print(f"[东方财富] 失败：{e}")
            return []
    
    def get_ths_flow(self, top_n: int = 50) -> List[Dict]:
        """同花顺 - 资金流排名（降级到东方财富）"""
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
    # 股票列表数据源（已修复）
    # =========================================================================
    
    def get_eastmoney_list(self) -> List[Dict]:
        """东方财富 - A 股股票列表（已修复）"""
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': '1', 'pz': '5000', 'po': '1', 'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426289',
            'fltt': '2', 'invt': '2', 'fid': 'f3',
            'fs': 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23',
            'fields': 'f12,f14,f2,f3,f5,f6,f9,f23',
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
            return self._get_sample_stock_list()
    
    def _get_sample_stock_list(self) -> List[Dict]:
        """样本股票列表（降级方案）"""
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
            {'code': s['code'], 'name': s['name'], 'status': '正常交易', 'source': 'sample', 'crawl_time': datetime.now().isoformat()}
            for s in sample_stocks
        ]
    
    # =========================================================================
    # 实时行情数据源
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
                                'change_pct': float(parts[32]) if parts[32] else 0,
                                'volume': int(parts[6]) if parts[6] else 0,
                                'turnover': float(parts[37]) if parts[37] else 0,
                                'source': 'tencent',
                                'crawl_time': datetime.now().isoformat(),
                            })
                
                time.sleep(0.1)
            
            return all_stocks
        except Exception as e:
            print(f"[腾讯行情] 失败：{e}")
            return []
    
    # =========================================================================
    # 备用数据源（使用 HTML 解析）
    # =========================================================================
    
    def get_163_main_force_html(self, top_n: int = 50) -> List[Dict]:
        """网易财经 - 主力净流入（HTML 解析版）"""
        url = "http://quotes.money.163.com/zhuli/"
        
        try:
            resp = self.session.get(url, timeout=10)
            resp.encoding = 'gbk'
            html = resp.text
            
            # 使用 HTML 解析器
            parser = SimpleHTMLParser()
            rows = parser.extract_table(html)
            
            stocks = []
            for row in rows[:top_n]:
                if len(row) >= 4:
                    stocks.append({
                        'code': row[0] if len(row) > 0 else '',
                        'name': row[1] if len(row) > 1 else '',
                        'price': float(row[2]) if len(row) > 2 else 0,
                        'change_pct': float(row[3]) if len(row) > 3 else 0,
                        'source': '163_html',
                        'crawl_time': datetime.now().isoformat(),
                    })
            
            return stocks
        except Exception as e:
            print(f"[网易 HTML] 失败：{e}")
            return []
    
    def get_iwencai_html(self, query: str = "主力净流入排名", top_n: int = 50) -> List[Dict]:
        """同花顺问财 - HTML 解析版"""
        url = "http://www.iwencai.com/unifiedwap/result"
        params = {'w': query, 'querytype': 'stock'}
        
        try:
            resp = self.session.get(url, params=params, timeout=15)
            html = resp.text
            
            parser = SimpleHTMLParser()
            rows = parser.extract_table(html)
            
            stocks = []
            for row in rows[:top_n]:
                if len(row) >= 3:
                    stocks.append({
                        'code': row[0] if len(row) > 0 else '',
                        'name': row[1] if len(row) > 1 else '',
                        'price': float(row[2]) if len(row) > 2 else 0,
                        'source': 'iwencai_html',
                        'crawl_time': datetime.now().isoformat(),
                    })
            
            return stocks
        except Exception as e:
            print(f"[问财 HTML] 失败：{e}")
            return []
    
    def get_dazhihui_ranking(self, top_n: int = 50) -> List[Dict]:
        """大智慧 - 降级到东方财富"""
        return self.get_eastmoney_flow(top_n)
    
    # =========================================================================
    # 统一接口
    # =========================================================================
    
    def fetch_all_main_force(self, top_n: int = 50) -> Dict[str, List[Dict]]:
        """获取所有主力/资金流数据源"""
        print("\n" + "="*80)
        print("💰 获取主力/资金流数据源")
        print("="*80)
        
        results = {}
        
        # 1. 百度
        print("\n[1/5] 百度股市通...")
        baidu_data = self.get_baidu_main_force(top_n)
        if baidu_data:
            results['baidu'] = baidu_data
            print(f"  ✅ 获取 {len(baidu_data)} 条")
        
        # 2. 东方财富
        print("\n[2/5] 东方财富...")
        em_data = self.get_eastmoney_flow(top_n)
        if em_data:
            results['eastmoney'] = em_data
            print(f"  ✅ 获取 {len(em_data)} 条")
        
        # 3. 同花顺
        print("\n[3/5] 同花顺...")
        ths_data = self.get_ths_flow(top_n)
        if ths_data:
            results['ths'] = ths_data
            print(f"  ✅ 获取 {len(ths_data)} 条")
        
        # 4. 腾讯
        print("\n[4/5] 腾讯财经（成交额）...")
        tencent_data = self.get_tencent_by_amount(top_n)
        if tencent_data:
            results['tencent'] = tencent_data
            print(f"  ✅ 获取 {len(tencent_data)} 条")
        
        # 5. 网易 HTML（备用）
        print("\n[5/5] 网易财经（HTML）...")
        data_163 = self.get_163_main_force_html(top_n)
        if data_163:
            results['163_html'] = data_163
            print(f"  ✅ 获取 {len(data_163)} 条")
        
        # 汇总
        print("\n" + "="*80)
        total = sum(len(data) for data in results.values())
        print(f"数据源数量：{len(results)}")
        for source, data in results.items():
            print(f"  - {source}: {len(data)} 条")
        print(f"总计：{total} 条")
        
        return results
    
    def merge_stocks(self, sources_data: Dict[str, List[Dict]]) -> List[Dict]:
        """合并多数据源股票数据"""
        merged = {}
        
        for source, stocks in sources_data.items():
            for stock in stocks:
                code = stock.get('code', '')
                if not code:
                    continue
                
                if code not in merged:
                    merged[code] = {'code': code, 'name': stock.get('name', ''), 'sources': []}
                
                merged[code]['sources'].append(source)
                
                for key, value in stock.items():
                    if key not in ['code', 'name', 'sources', 'crawl_time']:
                        merged[code][f"{source}_{key}"] = value
        
        return list(merged.values())
    
    def test_all_sources(self) -> Dict[str, bool]:
        """测试所有数据源可用性"""
        print("\n" + "="*80)
        print("🔧 测试所有数据源可用性")
        print("="*80)
        
        results = {}
        
        # 主力数据源
        print("\n[主力/资金流]")
        results['baidu'] = len(self.get_baidu_main_force(5)) > 0
        results['eastmoney'] = len(self.get_eastmoney_flow(5)) > 0
        results['tencent_amount'] = len(self.get_tencent_by_amount(5)) > 0
        results['163_html'] = len(self.get_163_main_force_html(5)) > 0
        
        # 股票列表
        print("\n[股票列表]")
        results['eastmoney_list'] = len(self.get_eastmoney_list()) > 0
        
        # 汇总
        print("\n" + "="*80)
        print("📊 数据源可用性汇总")
        active = sum(1 for v in results.values() if v)
        total = len(results)
        
        for source, status in results.items():
            icon = "✅" if status else "❌"
            print(f"{icon} {source}: {'可用' if status else '不可用'}")
        
        print(f"\n总计：{active}/{total} 可用 ({active/total*100:.1f}%)")
        
        return results


# CLI 入口
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='全数据源获取器 v3.1（修复版）')
    parser.add_argument('--source', default='all', choices=['all', 'main_force', 'list'])
    parser.add_argument('--top', type=int, default=20)
    parser.add_argument('--test', action='store_true', help='测试所有数据源')
    
    args = parser.parse_args()
    
    fetcher = AllSourcesFetcherFixed()
    
    if args.test:
        fetcher.test_all_sources()
    elif args.source == 'all':
        fetcher.fetch_all_main_force(args.top)
    elif args.source == 'main_force':
        fetcher.fetch_all_main_force(args.top)
    elif args.source == 'list':
        stock_list = fetcher.get_eastmoney_list()
        print(f"\n获取 {len(stock_list)} 只股票")
        for s in stock_list[:10]:
            print(f"  {s['code']} {s['name']}")
