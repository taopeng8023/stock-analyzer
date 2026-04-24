#!/usr/bin/env python3
"""
Tushare A 股日线行情数据获取脚本 - 补充失败数据

只获取还没有数据的股票

Token: a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4

用法:
    python3 fetch_tushare_retry.py --all     # 获取全部缺失数据
    python3 fetch_tushare_retry.py --limit 100  # 限制数量
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

# 深市主板：000001-000999
for code in range(1, 1000):
    symbol = f'{code:06d}'
    A_STOCK_CODES.append({'ts_code': f'{symbol}.SZ', 'symbol': symbol, 'market': '深市主板'})

# 深市中小板：002001-002999
for code in range(2001, 3000):
    symbol = f'{code:06d}'
    A_STOCK_CODES.append({'ts_code': f'{symbol}.SZ', 'symbol': symbol, 'market': '深市中小板'})

# 创业板：300001-300999
for code in range(300001, 301000):
    symbol = f'{code:06d}'
    A_STOCK_CODES.append({'ts_code': f'{symbol}.SZ', 'symbol': symbol, 'market': '创业板'})

# 沪市主板：600000-601999
for code in range(600000, 602000):
    symbol = f'{code:06d}'
    A_STOCK_CODES.append({'ts_code': f'{symbol}.SH', 'symbol': symbol, 'market': '沪市主板'})

# 沪市主板：603000-603999
for code in range(603000, 604000):
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
        
        # 频率限制 (更保守设置 15 次/分钟)
        self.last_request_time = 0
        self.min_interval = 4.0  # 15 次/分钟 = 4.0 秒/次 (更保守)
        
        # 数据目录
        self.data_dir = DATA_DIR
    
    def _rate_limit(self):
        """频率限制控制"""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _request(self, api_name: str, params: dict) -> Optional[dict]:
        """发送 API 请求"""
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
                return None
            
            return result.get('data')
        
        except Exception as e:
            return None
    
    def get_daily_data(self, ts_code: str, start_date: str, end_date: str) -> Optional[List[dict]]:
        """获取日线行情数据"""
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
                    '成交量': float(record.get('vol', 0)) * 100,
                    '成交额': float(record.get('amount', 0)) * 1000,
                    '涨跌幅': float(record.get('pct_chg', 0)),
                })
            
            daily_data.sort(key=lambda x: x['日期'])
            return daily_data
        
        return None
    
    def save_stock_data(self, symbol: str, data: List[dict]):
        """保存股票数据到文件"""
        filepath = self.data_dir / f'{symbol}.json'
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_stock_data(self, symbol: str) -> Optional[List[dict]]:
        """从文件加载股票数据"""
        filepath = self.data_dir / f'{symbol}.json'
        
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    def get_missing_stocks(self) -> List[dict]:
        """获取缺失数据的股票列表"""
        missing = []
        
        for stock in A_STOCK_CODES:
            symbol = stock.get('symbol', '')
            existing_data = self.load_stock_data(symbol)
            
            # 如果不存在或数据太少 (< 200 条)
            if not existing_data or len(existing_data) < 200:
                missing.append(stock)
        
        return missing
    
    def fetch_missing_stocks(self, limit: int = None):
        """批量获取缺失的股票数据"""
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        end_date = datetime.now().strftime('%Y%m%d')
        
        print(f'获取日期范围：{start_date} 至 {end_date}')
        print()
        
        # 获取缺失的股票列表
        missing_stocks = self.get_missing_stocks()
        print(f'缺失数据股票：{len(missing_stocks)} 只')
        print()
        
        # 限制数量
        if limit:
            missing_stocks = missing_stocks[:limit]
            print(f'限制获取：{len(missing_stocks)} 只')
            print()
        
        if not missing_stocks:
            print('没有缺失数据！')
            return
        
        # 批量获取
        start_time = time.time()
        success_count = 0
        fail_count = 0
        
        for i, stock in enumerate(missing_stocks):
            ts_code = stock.get('ts_code', '')
            symbol = stock.get('symbol', '')
            
            # 获取数据
            if (i + 1) % 50 == 0:
                print(f'[{i+1}/{len(missing_stocks)}] {symbol} - 获取中...')
            
            data = self.get_daily_data(ts_code, start_date, end_date)
            
            if data:
                self.save_stock_data(symbol, data)
                success_count += 1
                if (i + 1) % 100 == 0:
                    print(f'  成功 ({len(data)}条)')
            else:
                fail_count += 1
                if (i + 1) % 50 == 0:
                    print(f'  失败')
            
            # 进度
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                print(f'进度：{i+1}/{len(missing_stocks)} (成功:{success_count} 失败:{fail_count} 耗时:{elapsed:.1f}秒)')
        
        elapsed = time.time() - start_time
        print()
        print('='*80)
        print(f'获取完成')
        print(f'总计：{len(missing_stocks)} 只')
        print(f'成功：{success_count} 只')
        print(f'失败：{fail_count} 只')
        print(f'耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)')
        print('='*80)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Tushare A 股日线行情数据获取 - 补充失败数据')
    parser.add_argument('--all', action='store_true', help='获取全部缺失数据')
    parser.add_argument('--limit', type=int, help='限制获取股票数量')
    
    args = parser.parse_args()
    
    fetcher = TushareFetcher()
    
    if args.all or args.limit:
        fetcher.fetch_missing_stocks(limit=args.limit)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
