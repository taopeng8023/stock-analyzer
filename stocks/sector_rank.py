#!/usr/bin/env python3
"""
东方财富板块排名数据获取
鹏总专用 - 板块资金流向监控

功能:
1. 行业板块资金流向排名
2. 概念板块资金流向排名
3. 地区板块资金流向排名
4. 板块成分股分析

2026 年 3 月 26 日
"""

import urllib.request
import urllib.error
import json
from datetime import datetime
from typing import Dict, List, Optional


class EastmoneySectorRank:
    """东方财富板块排名数据获取"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Referer': 'http://data.eastmoney.com/bkzj/',
        }
        self.timeout = 15
    
    def _fetch_json(self, url: str, retry: int = 3) -> dict:
        """带重试的 JSON 获取"""
        for i in range(retry):
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    data = response.read().decode('utf-8')
                    return json.loads(data)
            except Exception as e:
                if i < retry - 1:
                    import time
                    time.sleep(1)
                else:
                    print(f"请求失败：{e}")
        return {}
    
    def get_industry_rank(self, page: int = 1, page_size: int = 20) -> list:
        """
        获取行业板块资金流向排名
        
        参数:
            page: 页码
            page_size: 每页数量
        
        返回:
            行业板块排名列表
        """
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': str(page),
            'pz': str(page_size),
            'po': '1',  # 降序
            'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2',
            'invt': '2',
            'fid': 'f62',  # 主力净流入
            'fs': 'm:90+t:3',  # 行业板块
            'fields': 'f1,f2,f3,f4,f12,f14,f18,f19,f20,f21,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f90,f93,f96,f99,f102,f124,f127,f130,f133,f136,f140,f143,f146,f149,f152,f155,f158,f161,f164,f167,f170,f173,f176,f179,f182,f185,f188,f191,f194,f197,f200,f203,f206,f209,f212,f215,f218,f221,f224,f227,f230,f233,f236,f239,f242,f245,f248,f251,f254,f257,f260,f263,f266,f269,f272,f275,f278,f281,f284,f287,f290,f293,f296,f299,f302,f305,f308,f311,f314,f317,f320,f323,f326,f329,f332,f335,f338,f341,f344,f347,f350,f353,f356',
            '_': str(int(datetime.now().timestamp() * 1000))
        }
        
        query = '&'.join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query}"
        
        data = self._fetch_json(full_url)
        
        if data.get('data') and data['data'].get('diff'):
            return data['data']['diff']
        return []
    
    def get_concept_rank(self, page: int = 1, page_size: int = 20) -> list:
        """
        获取概念板块资金流向排名
        
        参数:
            page: 页码
            page_size: 每页数量
        
        返回:
            概念板块排名列表
        """
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': str(page),
            'pz': str(page_size),
            'po': '1',
            'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2',
            'invt': '2',
            'fid': 'f62',
            'fs': 'm:90+t:2',  # 概念板块
            'fields': 'f1,f2,f3,f4,f12,f14,f62,f184',
            '_': str(int(datetime.now().timestamp() * 1000))
        }
        
        query = '&'.join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query}"
        
        data = self._fetch_json(full_url)
        
        if data.get('data') and data['data'].get('diff'):
            return data['data']['diff']
        return []
    
    def get_region_rank(self, page: int = 1, page_size: int = 20) -> list:
        """
        获取地区板块资金流向排名
        
        参数:
            page: 页码
            page_size: 每页数量
        
        返回:
            地区板块排名列表
        """
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': str(page),
            'pz': str(page_size),
            'po': '1',
            'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2',
            'invt': '2',
            'fid': 'f62',
            'fs': 'm:90+t:1',  # 地区板块
            'fields': 'f1,f2,f3,f4,f12,f14,f62,f184',
            '_': str(int(datetime.now().timestamp() * 1000))
        }
        
        query = '&'.join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query}"
        
        data = self._fetch_json(full_url)
        
        if data.get('data') and data['data'].get('diff'):
            return data['data']['diff']
        return []
    
    def get_sector_stocks(self, sector_code: str, page: int = 1, page_size: int = 50) -> list:
        """
        获取板块成分股
        
        参数:
            sector_code: 板块代码
            page: 页码
            page_size: 每页数量
        
        返回:
            成分股列表
        """
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': str(page),
            'pz': str(page_size),
            'po': '1',
            'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2',
            'invt': '2',
            'fid': 'f3',
            'fs': f'b:{sector_code}',
            'fields': 'f12,f14,f2,f3,f4,f5,f6,f12,f13,f14,f20,f21,f22,f23,f24,f25,f26,f32,f33,f34,f35,f36,f37,f38,f39,f40,f41,f42,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            '_': str(int(datetime.now().timestamp() * 1000))
        }
        
        query = '&'.join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query}"
        
        data = self._fetch_json(full_url)
        
        if data.get('data') and data['data'].get('diff'):
            return data['data']['diff']
        return []
    
    def print_sector_rank(self, rank_data: list, title: str = "板块排名"):
        """打印板块排名"""
        if not rank_data:
            print("暂无数据")
            return
        
        print(f"\n{'='*100}")
        print(f"  {title}")
        print(f"  更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*100}")
        print(f"{'序号':<5} {'代码':<8} {'名称':<15} {'最新价':>8} {'涨幅':>8} {'主力净额':>10} {'主力占比':>8} {'流入最大股':<12}")
        print(f"{'':<5} {'':<8} {'':<15} {'':>8} {'':>8} {'(亿)':>10} {'':>8} {'':<12}")
        print(f"{'-'*100}")
        
        for i, sector in enumerate(rank_data[:20], 1):
            code = sector.get('f12', 'N/A')
            name = sector.get('f14', 'N/A')
            price = sector.get('f2', 0) or 0
            change = sector.get('f3', 0) or 0
            main_net = (sector.get('f62', 0) or 0) / 100000000  # 转亿
            main_ratio = sector.get('f184', 0) or 0
            top_stock = sector.get('f19', 'N/A')  # 流入最大股
            
            print(f"{i:<5} {code:<8} {name:<15} {price:>7.2f} {change:>7.2f}% {main_net:>10.2f} {main_ratio:>7.2f}% {top_stock:<12}")
        
        print(f"{'='*100}\n")
    
    def analyze_top_sectors(self, rank_data: list) -> dict:
        """分析前 10 大板块"""
        if not rank_data:
            return {}
        
        top10 = rank_data[:10]
        
        analysis = {
            'total_count': len(top10),
            'avg_change': sum(s.get('f3', 0) or 0 for s in top10) / len(top10),
            'total_inflow': sum(s.get('f62', 0) or 0 for s in top10) / 100000000,
            'positive_count': sum(1 for s in top10 if (s.get('f3', 0) or 0) > 0),
            'negative_count': sum(1 for s in top10 if (s.get('f3', 0) or 0) < 0),
            'top_sectors': [s.get('f14', '') for s in top10[:5]],
        }
        
        return analysis


def get_main_force_rank_stocks(top_n: int = 20) -> list:
    """获取主力净流入排名个股"""
    url = "http://push2.eastmoney.com/api/qt/clist/get"
    params = {
        'pn': '1',
        'pz': str(top_n),
        'po': '1',
        'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2',
        'invt': '2',
        'fid': 'f4001',
        'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
        'fields': 'f12,f14,f2,f3,f4001,f4002',
        '_': str(int(datetime.now().timestamp() * 1000))
    }
    
    query = '&'.join(f"{k}={v}" for k, v in params.items())
    full_url = f"{url}?{query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': 'http://data.eastmoney.com/zjlx/',
    }
    
    try:
        req = urllib.request.Request(full_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        if data.get('data') and data['data'].get('diff'):
            return data['data']['diff']
    except:
        pass
    
    return []


if __name__ == "__main__":
    sector = EastmoneySectorRank()
    
    print("\n📊 正在获取东方财富板块排名数据...\n")
    
    # 1. 行业板块排名
    print("🏭 获取行业板块排名...")
    industry_rank = sector.get_industry_rank(page=1, page_size=20)
    sector.print_sector_rank(industry_rank, "行业板块资金流向排名 TOP 20")
    
    # 2. 概念板块排名
    print("💡 获取概念板块排名...")
    concept_rank = sector.get_concept_rank(page=1, page_size=20)
    sector.print_sector_rank(concept_rank, "概念板块资金流向排名 TOP 20")
    
    # 3. 地区板块排名
    print("🌍 获取地区板块排名...")
    region_rank = sector.get_region_rank(page=1, page_size=20)
    sector.print_sector_rank(region_rank, "地区板块资金流向排名 TOP 20")
    
    # 4. 分析
    if industry_rank:
        analysis = sector.analyze_top_sectors(industry_rank)
        if analysis:
            print("📈 前 10 大行业板块分析:")
            print(f"   平均涨幅：{analysis['avg_change']:.2f}%")
            print(f"   总净流入：{analysis['total_inflow']:.2f}亿")
            print(f"   上涨家数：{analysis['positive_count']}")
            print(f"   下跌家数：{analysis['negative_count']}")
            print(f"   领涨板块：{', '.join(analysis['top_sectors'][:3])}")
            print()
    
    # 5. 主力流入排名个股
    print("📊 获取主力净流入个股排名...")
    stock_rank = get_main_force_rank_stocks(top_n=20)
    if stock_rank:
        print(f"\n{'='*90}")
        print(f"  主力净流入个股排名 TOP 20")
        print(f"  更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*90}")
        print(f"{'序号':<5} {'代码':<8} {'名称':<12} {'现价':>8} {'涨幅':>8} {'主力净额':>10} {'主力占比':>8}")
        print(f"{'':<5} {'':<8} {'':<12} {'':>8} {'':>8} {'(亿)':>10} {'':>8}")
        print(f"{'-'*90}")
        
        for i, stock in enumerate(stock_rank[:20], 1):
            code = stock.get('f12', '')
            name = stock.get('f14', '')
            price = stock.get('f2', 0) or 0
            change = stock.get('f3', 0) or 0
            main_net = (stock.get('f4001', 0) or 0) / 100000000
            main_ratio = stock.get('f4002', 0) or 0
            
            print(f"{i:<5} {code:<8} {name:<12} {price:>7.2f} {change:>7.2f}% {main_net:>10.2f} {main_ratio:>7.2f}%")
        
        print(f"{'='*90}\n")
    
    # 6. 保存数据
    if industry_rank or concept_rank:
        output_file = f"/home/admin/.openclaw/workspace/stocks/cache/sector_rank_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        data_to_save = {
            'industry': industry_rank,
            'concept': concept_rank,
            'region': region_rank,
            'stocks': stock_rank,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        print(f"💾 数据已保存：{output_file}")
    
    print("\n✅ 板块排名数据获取完成！\n")
