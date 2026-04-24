#!/usr/bin/env python3
"""
实时行情获取器

获取 A 股实时股价、涨跌幅、成交量等数据
- 支持腾讯财经 API
- 支持新浪财经 API
- 批量获取（最多 50 只/次）
- 缓存机制（1 分钟）
"""

import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path


class QuoteFetcher:
    """实时行情获取器"""
    
    def __init__(self):
        self.cache_file = Path(__file__).parent / 'cache' / 'quote_cache.json'
        self.cache_file.parent.mkdir(exist_ok=True)
        self.cache = self._load_cache()
        self.cache_timeout = 60  # 缓存有效期 60 秒
    
    def _load_cache(self) -> dict:
        """加载缓存"""
        if not self.cache_file.exists():
            return {'quotes': {}, 'last_update': None}
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            # 清理过期缓存
            cutoff_time = datetime.now() - timedelta(seconds=self.cache_timeout)
            if cache.get('last_update'):
                last_update = datetime.fromisoformat(cache['last_update'])
                if last_update < cutoff_time:
                    cache['quotes'] = {}
            
            return cache
        except Exception as e:
            return {'quotes': {}, 'last_update': None}
    
    def _save_cache(self, cache: dict):
        """保存缓存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass
    
    def fetch_quotes(self, stock_codes: list) -> dict:
        """
        批量获取实时行情
        
        Args:
            stock_codes: 股票代码列表，如 ['sz300750', 'sh600519']
        
        Returns:
            dict: 行情数据 {code: {name, price, change, change_pct, volume, amount}}
        """
        if not stock_codes:
            return {}
        
        # 检查缓存
        cached = {}
        to_fetch = []
        now = datetime.now()
        
        for code in stock_codes:
            if code in self.cache.get('quotes', {}):
                quote = self.cache['quotes'][code]
                quote_time = datetime.fromisoformat(quote.get('time', ''))
                if now - quote_time < timedelta(seconds=self.cache_timeout):
                    cached[code] = quote
                    continue
            to_fetch.append(code)
        
        # 获取新数据
        fresh = {}
        if to_fetch:
            fresh = self._fetch_from_tencent(to_fetch)
            
            # 如果腾讯失败，尝试新浪
            if not fresh and to_fetch:
                fresh = self._fetch_from_sina(to_fetch)
            
            # 更新缓存
            if fresh:
                self.cache['quotes'].update(fresh)
                self.cache['last_update'] = now.isoformat()
                self._save_cache(self.cache)
        
        # 合并缓存和新数据
        result = {**cached, **fresh}
        return result
    
    def _fetch_from_tencent(self, codes: list) -> dict:
        """从腾讯财经获取行情"""
        quotes = {}
        
        try:
            # 腾讯 API 支持批量查询，最多 50 个
            code_list = ','.join([f'sh{c}' if c.startswith('6') else f'sz{c}' for c in codes])
            url = f'http://qt.gtimg.cn/q={code_list}'
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'http://quote.eastmoney.com/',
            }
            
            resp = requests.get(url, headers=headers, timeout=5)
            text = resp.content.decode('gbk')
            
            for line in text.strip().split('\n'):
                if '=' not in line:
                    continue
                
                code_part, data_part = line.split('=', 1)
                code = code_part.split('_')[-1].strip()
                
                # 解析数据
                # v51~sh600000~58~工商银行~600000~4.52~4.50~4.50~551234~...
                parts = data_part.strip('"').split('~')
                
                if len(parts) >= 40:
                    try:
                        price = float(parts[3]) if parts[3] else 0
                        prev_close = float(parts[4]) if parts[4] else 0
                        change = price - prev_close
                        change_pct = (change / prev_close * 100) if prev_close else 0
                        volume = int(parts[6]) if parts[6] else 0  # 手
                        amount = float(parts[37]) if len(parts) > 37 and parts[37] else 0  # 亿
                        
                        quotes[code] = {
                            'name': parts[1],
                            'code': code,
                            'price': price,
                            'change': change,
                            'change_pct': change_pct,
                            'volume': volume,  # 手
                            'amount': amount,  # 亿
                            'high': float(parts[33]) if len(parts) > 33 and parts[33] else 0,
                            'low': float(parts[34]) if len(parts) > 34 and parts[34] else 0,
                            'open': float(parts[5]) if len(parts) > 5 and parts[5] else 0,
                            'prev_close': prev_close,
                            'time': datetime.now().isoformat(),
                            'source': '腾讯财经',
                        }
                    except (ValueError, IndexError) as e:
                        pass
        except Exception as e:
            pass
        
        return quotes
    
    def _fetch_from_sina(self, codes: list) -> dict:
        """从新浪财经获取行情（备用）"""
        quotes = {}
        
        try:
            for code in codes:
                if code.startswith('sz'):
                    symbol = f'sz{code}'
                elif code.startswith('sh'):
                    symbol = code
                else:
                    symbol = f'sh{code}' if code.startswith('6') else f'sz{code}'
                
                url = f'http://hq.sinajs.cn/list={symbol}'
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                }
                
                resp = requests.get(url, headers=headers, timeout=5)
                text = resp.content.decode('gbk')
                
                if '=' in text:
                    data_part = text.strip().split('=', 1)[1].strip('"')
                    parts = data_part.split(',')
                    
                    if len(parts) >= 32:
                        try:
                            name = parts[0]
                            open_price = float(parts[1])
                            prev_close = float(parts[2])
                            price = float(parts[3])
                            high = float(parts[4])
                            low = float(parts[5])
                            
                            change = price - prev_close
                            change_pct = (change / prev_close * 100) if prev_close else 0
                            
                            volume = int(parts[8])  # 手
                            amount = float(parts[9]) / 100000000 if len(parts) > 9 else 0  # 亿
                            
                            code_clean = symbol[2:] if symbol.startswith('sz') or symbol.startswith('sh') else symbol
                            
                            quotes[code_clean] = {
                                'name': name,
                                'code': code_clean,
                                'price': price,
                                'change': change,
                                'change_pct': change_pct,
                                'volume': volume,
                                'amount': amount,
                                'high': high,
                                'low': low,
                                'open': open_price,
                                'prev_close': prev_close,
                                'time': datetime.now().isoformat(),
                                'source': '新浪财经',
                            }
                        except (ValueError, IndexError) as e:
                            pass
        except Exception as e:
            pass
        
        return quotes
    
    def format_quote(self, code: str, quote: dict) -> str:
        """格式化行情数据为推送文本（v7.1 股市颜色：红涨绿跌）"""
        if not quote:
            return ''
        
        price = quote.get('price', 0)
        change_pct = quote.get('change_pct', 0)
        volume = quote.get('volume', 0)
        amount = quote.get('amount', 0)
        
        # 涨跌符号（中国股市：红涨绿跌）
        if change_pct > 0:
            sign = '+'
            emoji = '🔴'  # 红色 = 上涨
        elif change_pct < 0:
            sign = ''
            emoji = '🟢'  # 绿色 = 下跌
        else:
            sign = ''
            emoji = '⚪'  # 灰色 = 平盘
        
        # 格式化
        price_str = f'¥{price:.2f}' if price > 0 else '--'
        change_str = f'{sign}{change_pct:.2f}%' if price > 0 else '--'
        amount_str = f'{amount:.1f}亿' if amount > 0 else '--'
        
        return f'{emoji} 现价：{price_str} | 涨跌：{change_str} | 成交：{amount_str}'
    
    def get_market_status(self) -> dict:
        """获取市场状态"""
        now = datetime.now()
        
        # 判断是否交易时间
        weekday = now.weekday()
        hour = now.hour
        minute = now.minute
        
        is_trading = False
        session = ''
        
        if weekday < 5:  # 工作日
            if (hour == 9 and minute >= 30) or (hour == 10) or (hour == 11 and minute <= 30):
                is_trading = True
                session = '上午'
            elif (hour == 13) or (hour == 14) or (hour == 15 and minute <= 0):
                is_trading = True
                session = '下午'
        
        return {
            'is_trading': is_trading,
            'session': session,
            'time': now.strftime('%H:%M:%S'),
            'weekday': weekday,
        }


# 测试
if __name__ == '__main__':
    fetcher = QuoteFetcher()
    
    # 测试获取行情
    test_codes = ['300750', '600519', '000858', '601398']
    
    print('='*60)
    print('📈 实时行情测试')
    print('='*60)
    
    quotes = fetcher.fetch_quotes(test_codes)
    
    for code, quote in quotes.items():
        print(f"\n{quote['name']} ({code})")
        print(fetcher.format_quote(code, quote))
    
    print(f"\n市场状态：{fetcher.get_market_status()}")
    print('='*60)
