#!/usr/bin/env python3
"""
东方财富主力排名数据 - 备用方案
使用多个 API 源确保数据获取成功
"""

import urllib.request
import urllib.error
import json
from datetime import datetime


def fetch_with_retry(url: str, retry: int = 3) -> dict:
    """带重试的 HTTP 请求"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Referer': 'http://data.eastmoney.com/',
    }
    
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                data = response.read().decode('utf-8')
                return json.loads(data)
        except Exception as e:
            if i < retry - 1:
                import time
                time.sleep(1)
            else:
                print(f"请求失败：{e}")
    return {}


def get_main_force_rank_v2():
    """获取主力排名 - 备用 API"""
    # 方案 1: 东方财富个股资金流向
    url = "http://nufm.dfcfw.com/EM_Fund2099/QF_StockStockEm/GetStockDataList"
    params = {
        'cb': '',
        'js': 'var',
        'rt': '52776474',
        'mp': '1',
        'p': '1',
        'pz': '20',
        'po': '1',
        'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2',
        'invt': '2',
        'fid': 'f4001',
        'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
        'fields': 'f12,f14,f2,f3,f4001,f4002,f4003,f4004',
        '_': str(int(datetime.now().timestamp() * 1000))
    }
    
    query = '&'.join(f"{k}={v}" for k, v in params.items())
    full_url = f"{url}?{query}"
    
    print(f"正在获取数据：{full_url[:100]}...")
    data = fetch_with_retry(full_url)
    
    if data.get('data'):
        return data['data']
    return []


def get_main_force_rank_v3():
    """获取主力排名 - 方案 3"""
    # 使用同花顺资金流向
    url = "http://data.10jqka.com.cn/funds/ggzjl/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'text/html,application/xhtml+xml',
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('gbk', errors='ignore')
            return html[:5000]
    except Exception as e:
        print(f"同花顺请求失败：{e}")
        return None


def print_simple_rank(data: list):
    """简化版排名输出"""
    if not data:
        print("暂无数据")
        return
    
    print(f"\n{'='*80}")
    print(f"  主力资金净流入排名 TOP 20")
    print(f"  更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    print(f"{'序号':<5} {'代码':<8} {'名称':<12} {'现价':>8} {'涨幅':>8} {'主力净额 (亿)':>12}")
    print(f"{'-'*80}")
    
    for i, stock in enumerate(data[:20], 1):
        if isinstance(stock, dict):
            code = stock.get('f12', 'N/A')
            name = stock.get('f14', 'N/A')
            price = stock.get('f2', 0) or 0
            change = stock.get('f3', 0) or 0
            main_net = (stock.get('f4001', 0) or 0) / 100000000
            
            print(f"{i:<5} {code:<8} {name:<12} {price:>7.2f} {change:>7.2f}% {main_net:>12.2f}")
    
    print(f"{'='*80}\n")


if __name__ == "__main__":
    print("\n📊 获取主力资金排名数据...\n")
    
    # 尝试方案 1
    print("方案 1: 东方财富 API...")
    data = get_main_force_rank_v2()
    
    if data:
        print_simple_rank(data)
        
        # 保存
        output_file = f"/home/admin/.openclaw/workspace/stocks/cache/main_force_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 数据已保存：{output_file}")
    else:
        print("方案 1 失败，尝试方案 2...")
        data2 = get_main_force_rank_v3()
        if data2:
            print("同花顺数据获取成功，但需要解析 HTML")
        else:
            print("所有方案都失败了，请稍后再试")
    
    print()
