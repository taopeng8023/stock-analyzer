#!/usr/bin/env python3
"""
Tushare A 股日线行情数据获取脚本

调取说明:
- 基础积分：每分钟内可调取 500 次
- 每次：6000 条数据
- 一次请求：相当于提取一个股票 23 年历史

Token: a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4

数据存储:
- 目录：~/.openclaw/workspace/stocks/data_tushare/
- 格式：{symbol}.json
- 与之前数据区分开

用法:
    python3 fetch_tushare_daily.py --full     # 获取全量数据
    python3 fetch_tushare_daily.py --update   # 更新数据
    python3 fetch_tushare_daily.py --test     # 测试连接
"""

import json
import sys
import time
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

# Tushare Token
TUSHARE_TOKEN = 'a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4'

# 数据存储目录
DATA_DIR = Path(__file__).parent / 'data_tushare'
DATA_DIR.mkdir(exist_ok=True)


class TushareFetcher:
    """Tushare 数据获取器"""
    
    def __init__(self, token: str = TUSHARE_TOKEN):
        self.token = token
        self.api_url = 'http://api.tushare.pro'
        
        # 频率限制 (stock_basic 接口：1 次/分钟，daily 接口：500 次/分钟)
        self.last_request_time = {}
        self.min_intervals = {
            'stock_basic': 60.0,  # 1 次/分钟
            'daily': 0.12,        # 500 次/分钟
        }
        
        # 数据目录
        self.data_dir = DATA_DIR
    
    def _rate_limit(self, api_name: str = 'daily'):
        """频率限制控制"""
        min_interval = self.min_intervals.get(api_name, 0.12)
        
        now = time.time()
        last_time = self.last_request_time.get(api_name, 0)
        elapsed = now - last_time
        
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        self.last_request_time[api_name] = time.time()
    
    def _request(self, api_name: str, params: dict) -> Optional[dict]:
        """
        发送 API 请求
        
        Args:
            api_name: API 接口名称
            params: 请求参数
        
        Returns:
            响应数据
        """
        import requests
        
        self._rate_limit(api_name)
        
        payload = {
            'api_name': api_name,
            'token': self.token,
            'params': params,
            'fields': ''
        }
        
        try:
            resp = requests.post(self.api_url, json=payload, timeout=30)
            resp.raise_for_status()
            
            result = resp.json()
            
            if result.get('code') != 0:
                print(f'API 错误：{result.get("msg", "未知错误")}')
                return None
            
            return result.get('data')
        
        except Exception as e:
            print(f'请求失败：{e}')
            return None
    
    def get_stock_list(self, use_cache: bool = True) -> Optional[List[dict]]:
        """
        获取 A 股股票列表
        
        Args:
            use_cache: 是否使用缓存
        
        Returns:
            股票列表
        """
        cache_file = self.data_dir / 'stock_list.json'
        
        # 使用缓存
        if use_cache and cache_file.exists():
            print('从缓存加载股票列表...')
            with open(cache_file, 'r', encoding='utf-8') as f:
                stock_list = json.load(f)
            print(f'加载到 {len(stock_list)} 只 A 股股票')
            return stock_list
        
        print('获取 A 股股票列表...')
        
        data = self._request('stock_basic', {
            'exchange': '',
            'list_status': 'L',  # 正常上市
            'fields': 'ts_code,symbol,name,area,industry,market,list_date'
        })
        
        if data and 'items' in data:
            columns = data.get('columns', [])
            items = data.get('items', [])
            
            stock_list = []
            for item in items:
                stock = dict(zip(columns, item))
                # 只保留 A 股
                if stock.get('market') in ['主板', '创业板', '科创板']:
                    stock_list.append(stock)
            
            print(f'获取到 {len(stock_list)} 只 A 股股票')
            
            # 保存缓存
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(stock_list, f, ensure_ascii=False, indent=2)
            print(f'已保存到缓存：{cache_file}')
            
            return stock_list
        
        return None
    
    def get_daily_data(self, ts_code: str, start_date: str, end_date: str) -> Optional[List[dict]]:
        """
        获取日线行情数据
        
        Args:
            ts_code: 股票代码 (格式：000001.SZ)
            start_date: 开始日期 (格式：YYYYMMDD)
            end_date: 结束日期 (格式：YYYYMMDD)
        
        Returns:
            日线数据列表
        """
        data = self._request('daily', {
            'ts_code': ts_code,
            'start_date': start_date,
            'end_date': end_date
        })
        
        if data and 'items' in data:
            columns = data.get('columns', [])
            items = data.get('items', [])
            
            daily_data = []
            for item in items:
                record = dict(zip(columns, item))
                daily_data.append({
                    '日期': record.get('trade_date', ''),
                    '开盘': float(record.get('open', 0)),
                    '收盘': float(record.get('close', 0)),
                    '最高': float(record.get('high', 0)),
                    '最低': float(record.get('low', 0)),
                    '成交量': float(record.get('vol', 0)) * 100,  # 手→股
                    '成交额': float(record.get('amount', 0)) * 1000,  # 千元→元
                    '振幅': float(record.get('pct_chg', 0)),  # 涨跌幅
                })
            
            # 按日期排序
            daily_data.sort(key=lambda x: x['日期'])
            
            return daily_data
        
        return None
    
    def save_stock_data(self, symbol: str, data: List[dict]):
        """
        保存股票数据到文件
        
        Args:
            symbol: 股票代码
            data: 数据列表
        """
        filepath = self.data_dir / f'{symbol}.json'
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_stock_data(self, symbol: str) -> Optional[List[dict]]:
        """
        从文件加载股票数据
        
        Args:
            symbol: 股票代码
        
        Returns:
            数据列表
        """
        filepath = self.data_dir / f'{symbol}.json'
        
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    def fetch_all_stocks(self, start_date: str = None, end_date: str = None, limit: int = None):
        """
        批量获取所有股票数据
        
        Args:
            start_date: 开始日期 (默认：一年前)
            end_date: 结束日期 (默认：今天)
            limit: 限制获取股票数量 (默认：全部)
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        
        print(f'获取日期范围：{start_date} 至 {end_date}')
        print()
        
        # 获取股票列表
        stock_list = self.get_stock_list()
        if not stock_list:
            print('获取股票列表失败')
            return
        
        # 限制数量
        if limit:
            stock_list = stock_list[:limit]
        
        print(f'计划获取 {len(stock_list)} 只股票数据')
        print()
        
        # 批量获取
        start_time = time.time()
        success_count = 0
        fail_count = 0
        
        for i, stock in enumerate(stock_list):
            ts_code = stock.get('ts_code', '')
            symbol = stock.get('symbol', '')
            name = stock.get('name', '')
            
            # 检查是否已存在
            existing_data = self.load_stock_data(symbol)
            if existing_data and len(existing_data) > 200:
                print(f'[{i+1}/{len(stock_list)}] {symbol} {name} - 已存在，跳过')
                success_count += 1
                continue
            
            # 获取数据
            print(f'[{i+1}/{len(stock_list)}] {symbol} {name} - 获取中...', end=' ')
            
            data = self.get_daily_data(ts_code, start_date, end_date)
            
            if data:
                self.save_stock_data(symbol, data)
                print(f'成功 ({len(data)}条)')
                success_count += 1
            else:
                print('失败')
                fail_count += 1
            
            # 进度
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                print(f'\n进度：{i+1}/{len(stock_list)} (成功:{success_count} 失败:{fail_count} 耗时:{elapsed:.1f}秒)')
        
        elapsed = time.time() - start_time
        print()
        print('='*80)
        print(f'获取完成')
        print(f'总计：{len(stock_list)} 只')
        print(f'成功：{success_count} 只')
        print(f'失败：{fail_count} 只')
        print(f'耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)')
        print('='*80)
    
    def test_connection(self):
        """测试连接"""
        print('测试 Tushare 连接...')
        
        stock_list = self.get_stock_list()
        
        if stock_list:
            print(f'✅ 连接成功！获取到 {len(stock_list)} 只股票')
            
            # 测试获取单只股票数据
            if stock_list:
                test_stock = stock_list[0]
                ts_code = test_stock.get('ts_code', '')
                symbol = test_stock.get('symbol', '')
                
                print(f'\n测试获取 {symbol} 数据...')
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                
                data = self.get_daily_data(ts_code, start_date, end_date)
                
                if data:
                    print(f'✅ 获取成功！{len(data)} 条数据')
                    print(f'最新数据：{data[-1]}')
                else:
                    print('❌ 获取失败')
            
            return True
        else:
            print('❌ 连接失败')
            return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Tushare A 股日线行情数据获取')
    parser.add_argument('--full', action='store_true', help='获取全量数据')
    parser.add_argument('--update', action='store_true', help='更新数据')
    parser.add_argument('--test', action='store_true', help='测试连接')
    parser.add_argument('--limit', type=int, help='限制获取股票数量')
    parser.add_argument('--start', type=str, help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end', type=str, help='结束日期 (YYYYMMDD)')
    
    args = parser.parse_args()
    
    fetcher = TushareFetcher()
    
    if args.test:
        # 测试连接
        fetcher.test_connection()
    
    elif args.full:
        # 获取全量数据
        fetcher.fetch_all_stocks(
            start_date=args.start,
            end_date=args.end,
            limit=args.limit
        )
    
    elif args.update:
        # 更新数据 (只获取最近 30 天)
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        print(f'更新最近 30 天数据 ({start_date} 至 {end_date})')
        print()
        
        # 获取已有数据
        stock_list = fetcher.get_stock_list()
        if not stock_list:
            print('获取股票列表失败')
            return
        
        # 限制数量
        if args.limit:
            stock_list = stock_list[:args.limit]
        
        print(f'计划更新 {len(stock_list)} 只股票数据')
        print()
        
        fetcher.fetch_all_stocks(
            start_date=start_date,
            end_date=end_date,
            limit=args.limit
        )
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
