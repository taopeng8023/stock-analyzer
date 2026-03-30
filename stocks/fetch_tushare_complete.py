#!/usr/bin/env python3
"""
Tushare A 股日线行情数据获取脚本 (完整版)

由于 stock_basic 接口限制 (1 次/小时)，使用本地 A 股股票代码列表

Token: a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4

数据存储:
- 目录：~/.openclaw/workspace/stocks/data_tushare/
- 格式：{symbol}.json
- 与之前数据区分开

用法:
    python3 fetch_tushare_complete.py --full     # 获取全量数据
    python3 fetch_tushare_complete.py --update   # 更新数据
    python3 fetch_tushare_complete.py --test     # 测试连接
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

# A 股股票代码列表 (完整列表，约 5300 只)
A_STOCK_CODES = []

# 深市主板：000001-002999
for code in range(1, 3000):
    symbol = f'{code:06d}'
    A_STOCK_CODES.append({'ts_code': f'{symbol}.SZ', 'symbol': symbol, 'market': '深市主板'})

# 创业板：300001-301999
for code in range(300001, 302000):
    symbol = f'{code:06d}'
    A_STOCK_CODES.append({'ts_code': f'{symbol}.SZ', 'symbol': symbol, 'market': '创业板'})

# 沪市主板：600000-603999
for code in range(600000, 604000):
    symbol = f'{code:06d}'
    A_STOCK_CODES.append({'ts_code': f'{symbol}.SH', 'symbol': symbol, 'market': '沪市主板'})

# 科创板：688001-688999
for code in range(688001, 689000):
    symbol = f'{code:06d}'
    A_STOCK_CODES.append({'ts_code': f'{symbol}.SH', 'symbol': symbol, 'market': '科创板'})

print(f'生成 {len(A_STOCK_CODES)} 只 A 股股票代码')


class TushareFetcher:
    """Tushare 数据获取器"""
    
    def __init__(self, token: str = TUSHARE_TOKEN):
        self.token = token
        self.api_url = 'http://api.tushare.pro'
        
        # 频率限制 (基础积分：50 次/分钟，保守设置 30 次/分钟)
        self.last_request_time = 0
        self.min_interval = 2.0  # 30 次/分钟 = 2.0 秒/次 (更保守)
        
        # 数据目录
        self.data_dir = DATA_DIR
    
    def _rate_limit(self):
        """频率限制控制"""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
    
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
        
        self._rate_limit()
        
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
            fields = data.get('fields', [])
            items = data.get('items', [])
            
            daily_data = []
            for item in items:
                record = dict(zip(fields, item))
                daily_data.append({
                    '日期': str(record.get('trade_date', '')),
                    '开盘': float(record.get('open', 0)),
                    '收盘': float(record.get('close', 0)),
                    '最高': float(record.get('high', 0)),
                    '最低': float(record.get('low', 0)),
                    '成交量': float(record.get('vol', 0)) * 100,  # 手→股
                    '成交额': float(record.get('amount', 0)) * 1000,  # 千元→元
                    '涨跌幅': float(record.get('pct_chg', 0)),  # 涨跌幅
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
    
    def fetch_all_stocks(self, start_date: str = None, end_date: str = None, limit: int = None, stock_list: List[dict] = None):
        """
        批量获取所有股票数据
        
        Args:
            start_date: 开始日期 (默认：一年前)
            end_date: 结束日期 (默认：今天)
            limit: 限制获取股票数量 (默认：全部)
            stock_list: 股票列表 (默认：使用生成的代码列表)
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        
        print(f'获取日期范围：{start_date} 至 {end_date}')
        print()
        
        # 使用提供的股票列表或生成的代码列表
        if not stock_list:
            stock_list = A_STOCK_CODES
        
        # 限制数量
        if limit:
            stock_list = stock_list[:limit]
        
        print(f'计划获取 {len(stock_list)} 只股票数据')
        print()
        
        # 批量获取
        start_time = time.time()
        success_count = 0
        fail_count = 0
        skip_count = 0
        
        for i, stock in enumerate(stock_list):
            ts_code = stock.get('ts_code', '')
            symbol = stock.get('symbol', '')
            
            # 检查是否已存在
            existing_data = self.load_stock_data(symbol)
            if existing_data and len(existing_data) > 200:
                skip_count += 1
                if (i + 1) % 500 == 0:
                    print(f'[{i+1}/{len(stock_list)}] {symbol} - 已存在，跳过 (累计跳过:{skip_count})')
                continue
            
            # 获取数据
            if (i + 1) % 100 == 0:
                print(f'[{i+1}/{len(stock_list)}] {symbol} - 获取中...')
            
            data = self.get_daily_data(ts_code, start_date, end_date)
            
            if data:
                self.save_stock_data(symbol, data)
                success_count += 1
                if (i + 1) % 500 == 0:
                    print(f'  成功 ({len(data)}条)')
            else:
                fail_count += 1
                if (i + 1) % 100 == 0:
                    print(f'  失败')
            
            # 进度
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                print(f'进度：{i+1}/{len(stock_list)} (成功:{success_count} 失败:{fail_count} 跳过:{skip_count} 耗时:{elapsed:.1f}秒)')
        
        elapsed = time.time() - start_time
        print()
        print('='*80)
        print(f'获取完成')
        print(f'总计：{len(stock_list)} 只')
        print(f'成功：{success_count} 只')
        print(f'失败：{fail_count} 只')
        print(f'跳过：{skip_count} 只')
        print(f'耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)')
        print('='*80)
    
    def test_connection(self):
        """测试连接"""
        print('测试 Tushare 连接...')
        
        # 测试获取单只股票数据
        test_stock = {'ts_code': '000001.SZ', 'symbol': '000001', 'name': '平安银行'}
        ts_code = test_stock.get('ts_code', '')
        symbol = test_stock.get('symbol', '')
        
        print(f'测试获取 {symbol} 数据...')
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        data = self.get_daily_data(ts_code, start_date, end_date)
        
        if data:
            print(f'✅ 获取成功！{len(data)} 条数据')
            print(f'最新数据：{data[-1]}')
            return True
        else:
            print('❌ 获取失败')
            return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Tushare A 股日线行情数据获取 (完整版)')
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
        
        fetcher.fetch_all_stocks(
            start_date=start_date,
            end_date=end_date,
            limit=args.limit
        )
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
