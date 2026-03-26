#!/usr/bin/env python3
"""
东方财富主力资金排名数据获取
鹏总专用 - 实时主力排名分析
"""

import urllib.request
import urllib.error
import json
from datetime import datetime


class EastmoneyMoneyFlow:
    """东方财富资金流向数据获取"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer': 'http://data.eastmoney.com/zjlx/',
        }
    
    def _fetch(self, url: str) -> dict:
        """获取 JSON 数据"""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read().decode('utf-8')
                return json.loads(data)
        except Exception as e:
            print(f"请求失败：{e}")
            return {}
    
    def get_main_force_rank(self, page: int = 1, page_size: int = 20) -> list:
        """
        获取主力净流入排名
        
        参数:
            page: 页码
            page_size: 每页数量
        
        返回:
            主力净流入排名列表
        """
        # 东方财富资金流向 API
        url = f"http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': str(page),
            'pz': str(page_size),
            'po': '1',  # 降序
            'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2',
            'invt': '2',
            'fid': 'f4001',  # 主力净流入
            'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',  # 全部 A 股
            'fields': 'f12,f14,f2,f3,f4001,f4002,f4003,f4004,f4005,f4006,f4007,f4008,f4009,f4010',
            '_': str(int(datetime.now().timestamp() * 1000))
        }
        
        query = '&'.join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query}"
        
        data = self._fetch(full_url)
        
        if data.get('data') and data['data'].get('diff'):
            return data['data']['diff']
        return []
    
    def get_main_force_inflow_rank(self, page: int = 1, page_size: int = 20) -> list:
        """
        获取主力净流入占比排名
        
        参数:
            page: 页码
            page_size: 每页数量
        
        返回:
            主力净流入占比排名列表
        """
        url = f"http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': str(page),
            'pz': str(page_size),
            'po': '1',
            'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2',
            'invt': '2',
            'fid': 'f4002',  # 主力净流入占比
            'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
            'fields': 'f12,f14,f2,f3,f4001,f4002,f4003,f4004,f4005',
            '_': str(int(datetime.now().timestamp() * 1000))
        }
        
        query = '&'.join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query}"
        
        data = self._fetch(full_url)
        
        if data.get('data') and data['data'].get('diff'):
            return data['data']['diff']
        return []
    
    def print_rank(self, rank_data: list, title: str = "主力排名"):
        """打印排名数据"""
        if not rank_data:
            print("暂无数据")
            return
        
        print(f"\n{'='*90}")
        print(f"  {title}")
        print(f"  更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*90}")
        print(f"{'序号':<5} {'代码':<8} {'名称':<12} {'现价':>8} {'涨幅':>8} {'主力净额':>10} {'主力占比':>8} {'超大单':>10} {'大单':>10}")
        print(f"{'':<5} {'':<8} {'':<12} {'':>8} {'':>8} {'(亿)':>10} {'':>8} {'(亿)':>10} {'(亿)':>10}")
        print(f"{'-'*90}")
        
        for i, stock in enumerate(rank_data[:20], 1):
            code = stock.get('f12', '')
            name = stock.get('f14', '')
            price = stock.get('f2', 0) or 0
            change = stock.get('f3', 0) or 0
            main_net = (stock.get('f4001', 0) or 0) / 100000000  # 转亿
            main_ratio = stock.get('f4002', 0) or 0
            super_net = (stock.get('f4003', 0) or 0) / 100000000
            big_net = (stock.get('f4004', 0) or 0) / 100000000
            
            print(f"{i:<5} {code:<8} {name:<12} {price:>7.2f} {change:>7.2f}% {main_net:>10.2f} {main_ratio:>7.2f}% {super_net:>10.2f} {big_net:>10.2f}")
        
        print(f"{'='*90}\n")


def analyze_top_stocks(rank_data: list) -> dict:
    """分析前 10 大主力净流入股票"""
    if not rank_data:
        return {}
    
    top10 = rank_data[:10]
    
    analysis = {
        'total_count': len(top10),
        'avg_change': sum(s.get('f3', 0) or 0 for s in top10) / len(top10),
        'total_inflow': sum(s.get('f4001', 0) or 0 for s in top10) / 100000000,
        'positive_count': sum(1 for s in top10 if (s.get('f3', 0) or 0) > 0),
        'negative_count': sum(1 for s in top10 if (s.get('f3', 0) or 0) < 0),
    }
    
    # 行业分布
    industries = {}
    for stock in top10:
        name = stock.get('f14', '')
        # 简单行业判断
        if any(kw in name for kw in ['科技', '电子', '芯片', '半导体']):
            industries['科技'] = industries.get('科技', 0) + 1
        elif any(kw in name for kw in ['银行', '保险', '证券']):
            industries['金融'] = industries.get('金融', 0) + 1
        elif any(kw in name for kw in ['能源', '石油', '煤炭']):
            industries['能源'] = industries.get('能源', 0) + 1
        elif any(kw in name for kw in ['医药', '生物', '医疗']):
            industries['医药'] = industries.get('医药', 0) + 1
        else:
            industries['其他'] = industries.get('其他', 0) + 1
    
    analysis['industries'] = industries
    
    return analysis


if __name__ == "__main__":
    flow = EastmoneyMoneyFlow()
    
    print("\n📊 正在获取东方财富主力资金排名数据...\n")
    
    # 获取主力净流入排名
    main_rank = flow.get_main_force_rank(page=1, page_size=50)
    flow.print_rank(main_rank, "今日主力净流入排名 TOP 20")
    
    # 获取主力净流入占比排名
    ratio_rank = flow.get_main_force_inflow_rank(page=1, page_size=20)
    flow.print_rank(ratio_rank, "主力净流入占比排名 TOP 20")
    
    # 分析
    if main_rank:
        analysis = analyze_top_stocks(main_rank)
        if analysis:
            print("📈 前 10 大主力净流入股票分析:")
            print(f"   平均涨幅：{analysis['avg_change']:.2f}%")
            print(f"   总净流入：{analysis['total_inflow']:.2f}亿")
            print(f"   上涨家数：{analysis['positive_count']}")
            print(f"   下跌家数：{analysis['negative_count']}")
            print(f"   行业分布：{analysis['industries']}")
            print()
    
    # 保存数据
    if main_rank:
        output_file = f"/home/admin/.openclaw/workspace/stocks/cache/main_force_rank_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(main_rank, f, ensure_ascii=False, indent=2)
        print(f"💾 数据已保存：{output_file}")
    
    print("\n✅ 数据获取完成！\n")
