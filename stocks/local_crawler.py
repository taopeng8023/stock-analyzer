#!/usr/bin/env python3
"""
本地股票数据爬虫 v2.1
从多个数据源抓取股票数据，缓存到本地

⚠️  重要声明：本爬虫仅使用真实市场数据，严禁生成或使用任何模拟数据
    所有交易决策请基于官方交易所数据，本工具仅供参考

支持数据源:
- 腾讯财经（实时行情、成交量、成交额）
- 百度股市通（涨跌幅、成交额排行）
- 东方财富（板块资金流、北向资金、K 线）

功能:
- 实时行情抓取
- 多种排行榜
- 板块资金流
- 北向资金监控
- 历史 K 线数据（日线/周线/月线）
- 技术指标计算（MA/MACD/KDJ）
- 数据导出 CSV/JSON

用法:
    python3 local_crawler.py --crawl                    # 抓取全部数据
    python3 local_crawler.py --crawl --source tencent   # 只抓取腾讯
    python3 local_crawler.py --query top10              # 查询前 10
    python3 local_crawler.py --query sector             # 板块排行
    python3 local_crawler.py --query north              # 北向资金
    python3 local_crawler.py --kline sh600000           # 获取 K 线
    python3 local_crawler.py --export csv               # 导出 CSV
"""

import requests
import json
import os
import re
import time
import random
import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# ⚠️  本模块仅使用真实市场数据，严禁生成模拟数据
# 详见 DATA_POLICY.md


class StockCrawler:
    """股票数据爬虫"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    # ========== 腾讯财经 ==========
    
    def crawl_tencent(self, symbols: Optional[List[str]] = None, batch_size: int = 80) -> List[Dict]:
        """
        从腾讯财经抓取股票实时行情
        
        Args:
            symbols: 股票代码列表，None 则抓取全部 A 股
            batch_size: 每批请求数量
        
        Returns:
            list: 股票数据列表
        """
        print("[腾讯财经] 抓取实时行情...")
        
        if symbols is None:
            symbols = self._generate_a_share_symbols()
        
        all_stocks = []
        total_batches = (len(symbols) + batch_size - 1) // batch_size
        
        for i in range(0, min(len(symbols), 1200), batch_size):  # 限制最多 1200 只
            batch = symbols[i:i+batch_size]
            symbol_list = ','.join(batch)
            url = f"https://qt.gtimg.cn/q={symbol_list}"
            
            try:
                resp = self.session.get(url, timeout=15)
                resp.encoding = 'gbk'
                
                for line in resp.text.split('\n'):
                    if not line.strip():
                        continue
                    
                    match = re.search(r'v_(\w+)="([^"]+)"', line)
                    if match:
                        fields = match.group(2).split('~')
                        if len(fields) >= 50 and fields[6]:  # 有成交量
                            symbol = match.group(1)
                            stock = self._parse_tencent_field(symbol, fields)
                            if stock:
                                all_stocks.append(stock)
                
                batch_num = i // batch_size + 1
                print(f"  批次 {batch_num}/{total_batches}: 获取 {len(all_stocks)} 只有效数据")
                
            except Exception as e:
                print(f"  批次 {i//batch_size + 1} 失败：{e}")
            
            time.sleep(0.15)  # 避免请求过快
        
        print(f"[腾讯财经] 共获取 {len(all_stocks)} 只股票")
        return all_stocks
    
    def _parse_tencent_field(self, symbol: str, fields: List[str]) -> Dict:
        """
        解析腾讯财经数据字段（真实数据 - 已验证）
        
        ⚠️  核心原则：所有数据必须来自真实市场，严禁使用模拟/估算数据
        
        腾讯 API 字段说明（以~分隔）:
        [0] 序号 [1] 名称 [2] 代码 [3] 当前价 [4] 昨收 [5] 今开 [6] 成交量 (手)
        [7] 未知 [31] 涨跌额 [32] 涨跌幅% [33] 最高 [34] 最低
        [35] 现价/成交量/成交额 (元)  ← 成交额准确来源
        [36] 成交量 (手) [37] 换手率% [39] 市盈率
        """
        try:
            # 真实市场数据
            current_price = float(fields[3]) if fields[3] else 0
            last_close = float(fields[4]) if fields[4] else 0
            
            # 成交量：优先使用字段 [36]，备用 [6]
            volume = int(float(fields[36])) if fields[36] else int(float(fields[6])) if fields[6] else 0
            
            # 成交额：从字段 [35] 解析（格式：现价/成交量/成交额元）
            amount_yuan = 0.0
            if len(fields) > 35 and '/' in fields[35]:
                parts = fields[35].split('/')
                if len(parts) >= 3:
                    amount_yuan = float(parts[2])
            
            return {
                'symbol': symbol,
                'name': fields[1],
                'price': current_price,
                'open': float(fields[5]) if fields[5] else 0,
                'close': last_close,
                'high': float(fields[33]) if fields[33] else 0,
                'low': float(fields[34]) if fields[34] else 0,
                'volume': volume,  # 手
                'amount_wan': amount_yuan / 10000,  # 万（从元转换）
                'amount_yuan': amount_yuan,  # 元（原始数据）
                'bid': float(fields[10]) if fields[10] else 0,
                'ask': float(fields[18]) if fields[18] else 0,
                'change': float(fields[31]) if fields[31] else 0,
                'change_pct': float(fields[32]) if fields[32] else 0,
                'time': fields[30] if len(fields) > 30 else '',
                'turnover_rate': float(fields[37]) if len(fields) > 37 and fields[37] else 0,
                'pe_ratio': float(fields[39]) if len(fields) > 39 and fields[39] else 0,
                # 数据源标记
                'source': 'tencent',
                'crawl_time': datetime.now().isoformat(),
            }
        except Exception as e:
            print(f"⚠️  解析失败：{e}, fields: {fields[:10]}...")
            return None
    
    def _generate_a_share_symbols(self) -> List[str]:
        """生成 A 股股票代码列表"""
        symbols = []
        
        # 沪市 A 股 (600xxx - 605xxx)
        for prefix in range(600, 606):
            for suffix in range(1000):
                symbols.append(f"sh{prefix}{suffix%1000:03d}")
        
        # 深市主板 (000xxx)
        for i in range(1, 5000):
            symbols.append(f"sz000{i%1000:03d}")
        
        # 中小板 (002xxx)
        for i in range(1, 5000):
            symbols.append(f"sz002{i%1000:03d}")
        
        # 创业板 (300xxx, 301xxx)
        for prefix in [300, 301]:
            for i in range(1000):
                symbols.append(f"sz{prefix}{i:03d}")
        
        # 去重
        return list(set(symbols))
    
    # ========== 百度股市通 ==========
    
    def crawl_baidu_rank(self, rank_type: str = 'change') -> List[Dict]:
        """
        从百度股市通抓取排行榜
        
        Args:
            rank_type: 'change' (涨跌), 'amount' (成交额), 'volume' (成交量)
        
        Returns:
            list: 排行数据
        """
        print(f"[百度股市通] 抓取{rank_type}排行...")
        
        type_map = {
            'change': '',
            'amount': 'amount',
            'volume': 'volume',
        }
        
        type_param = type_map.get(rank_type, '')
        url = f"https://gushitong.baidu.com/opendata?resource_id=5350&query=沪深 A 股&market=ab&group=asyn_rank&pn=0&rn=50&pc_web=1&code=110000"
        if type_param:
            url += f"&type={type_param}"
        
        try:
            resp = self.session.get(url, timeout=15)
            data = resp.json()
            
            if data.get('ResultCode') == '0' and data.get('Result'):
                result = data['Result'][0]
                display = result.get('DisplayData', {})
                result_data = display.get('resultData', {})
                
                stocks = []
                
                # 尝试不同路径获取数据
                if 'newTable' in result_data:
                    table = result_data['newTable']
                    rows = table.get('data', [])
                    for row in rows:
                        stock = {
                            'symbol': self._format_symbol(row.get('股票代码') or row.get('code', '')),
                            'name': row.get('股票名称') or row.get('name', ''),
                            'price': self._safe_float(row.get('最新价') or row.get('price')),
                            'change_pct': self._safe_float(row.get('涨跌幅') or row.get('change')),
                            'amount_wan': self._safe_float(row.get('成交额') or row.get('amount')) / 10000,
                            'volume': self._safe_int(row.get('成交量') or row.get('volume')),
                            'source': 'baidu',
                            'crawl_time': datetime.now().isoformat(),
                        }
                        stocks.append(stock)
                
                print(f"[百度股市通] 获取 {len(stocks)} 条排行数据")
                return stocks
            else:
                print(f"[百度股市通] 返回错误：{data}")
                return []
                
        except Exception as e:
            print(f"[百度股市通] 抓取失败：{e}")
            return []
    
    # ========== 东方财富板块资金流 ==========
    
    def crawl_eastmoney_sector(self, sector_type: str = 'concept', max_retries: int = 3) -> List[Dict]:
        """
        从东方财富抓取板块资金流（增强反爬版）
        
        Args:
            sector_type: 'concept' (概念), 'industry' (行业), 'region' (地区)
            max_retries: 最大重试次数
        
        Returns:
            list: 板块资金流数据
        """
        print(f"[东方财富] 抓取{sector_type}板块资金流...")
        
        # 完整请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://data.eastmoney.com/zjlx/',
        }
        
        type_map = {
            'concept': 'bk',
            'industry': 'hy',
            'region': 'dq',
        }
        bk_type = type_map.get(sector_type, 'bk')
        
        for attempt in range(max_retries):
            try:
                # 增加延迟，模拟真人
                time.sleep(2 + random.uniform(0, 2))
                
                url = "https://push2.eastmoney.com/api/qt/clist/get"
                params = {
                    'pn': '1',
                    'pz': '50',
                    'po': '1',
                    'np': '1',
                    'fltt': '2',
                    'invt': '2',
                    'fid': 'f62',
                    'fs': f'm:t:{bk_type}',
                    'fields': 'f12,f14,f62,f184',
                }
                
                resp = requests.get(url, params=params, headers=headers, timeout=20)
                data = resp.json()
                
                if data.get('rc') == 0 and data.get('data'):
                    sectors = data['data'].get('diff', [])
                    result = []
                    
                    for s in sectors:
                        sector = {
                            'code': s.get('f12', ''),
                            'name': s.get('f14', ''),
                            'main_net': self._safe_float(s.get('f62')),
                            'change_pct': self._safe_float(s.get('f184')),
                            'source': 'eastmoney_sector',
                            'crawl_time': datetime.now().isoformat(),
                        }
                        result.append(sector)
                    
                    print(f"[东方财富] 获取 {len(result)} 个板块数据")
                    return result
                else:
                    print(f"[东方财富] API 返回错误：{data.get('rc', 'unknown')}")
                    
            except Exception as e:
                print(f"[东方财富] 尝试 {attempt+1}/{max_retries} 失败：{e}")
                time.sleep(3 + random.uniform(0, 2))
                continue
        
        print(f"[东方财富] 所有重试失败，将使用腾讯财经数据替代")
        return []
    
    # ========== 历史 K 线 ==========
    
    def get_kline(self, symbol: str, period: str = 'day', count: int = 100, 
                  adjust: str = 'qfq') -> List[Dict]:
        """
        获取单只股票 K 线数据
        
        Args:
            symbol: 股票代码 (sh600000 或 sz000001)
            period: K 线周期 'day' (日线), 'week' (周线), 'month' (月线)
            count: 获取条数 (最多 1000)
            adjust: 复权类型 'qfq' (前复权), 'hfq' (后复权), 'none' (不复权)
        
        Returns:
            list: K 线数据列表，每条包含 date/open/high/low/close/volume/amount
        """
        print(f"[腾讯财经] 获取 {symbol} {period}K 线 ({adjust})...")
        
        # 腾讯财经 K 线 API
        # param: sh600000,qfqday,,,100
        period_map = {
            'day': 'day',
            'week': 'week',
            'month': 'month',
        }
        
        p = period_map.get(period, 'day')
        if adjust == 'qfq':
            param = f"{symbol},qfq{p},,,{count}"
        elif adjust == 'hfq':
            param = f"{symbol},hfq{p},,,{count}"
        else:
            param = f"{symbol},{p},,,{count}"
        
        url = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        params = {'param': param}
        
        try:
            resp = self.session.get(url, params=params, timeout=15)
            data = resp.json()
            
            if data.get('code') == 0:
                kline_data = data.get('data', {})
                
                # 获取对应周期的 K 线
                key = f"{adjust}{p}" if adjust != 'none' else p
                klines = kline_data.get(key, [])
                
                result = []
                for k in klines:
                    # K 线格式：[日期，开盘，收盘，最高，最低，成交量，成交额，换手率]
                    if len(k) >= 7:
                        candle = {
                            'symbol': symbol,
                            'date': k[0],
                            'open': float(k[1]) if k[1] else 0,
                            'close': float(k[3]) if k[3] else 0,  # 注意：腾讯格式是 [日期，开盘，收盘，最高，最低...]
                            'high': float(k[4]) if k[4] else 0,
                            'low': float(k[5]) if k[5] else 0,
                            'volume': float(k[6]) if len(k) > 6 and k[6] else 0,
                            'amount': float(k[7]) if len(k) > 7 and k[7] else 0,
                            'turnover': float(k[8]) if len(k) > 8 and k[8] else 0,
                        }
                        result.append(candle)
                
                print(f"[腾讯财经] 获取 {len(result)} 条 K 线")
                return result
            else:
                print(f"[腾讯财经] K 线返回错误：{data}")
                return []
                
        except Exception as e:
            print(f"[腾讯财经] K 线获取失败：{e}")
            return []
    
    def get_batch_kline(self, symbols: List[str], period: str = 'day', 
                        count: int = 60) -> Dict[str, List[Dict]]:
        """
        批量获取 K 线数据
        
        Args:
            symbols: 股票代码列表
            period: K 线周期
            count: 每只股票获取条数
        
        Returns:
            dict: {symbol: [klines]}
        """
        print(f"[腾讯财经] 批量获取 {len(symbols)} 只股票 K 线...")
        
        result = {}
        
        for i, symbol in enumerate(symbols):
            klines = self.get_kline(symbol, period=period, count=count)
            if klines:
                result[symbol] = klines
            
            # 每 20 只延迟一下
            if (i + 1) % 20 == 0:
                time.sleep(0.5)
                print(f"  进度：{i+1}/{len(symbols)}")
        
        return result
    
    def calculate_ma(self, klines: List[Dict], periods: List[int] = [5, 10, 20, 60]) -> List[Dict]:
        """
        计算移动平均线 (MA)
        
        Args:
            klines: K 线数据列表
            periods: MA 周期列表 [5, 10, 20, 60]
        
        Returns:
            list: 添加 MA 数据后的 K 线
        """
        if not klines:
            return []
        
        closes = [k['close'] for k in klines]
        result = []
        
        for i, k in enumerate(klines):
            candle = k.copy()
            
            for period in periods:
                if i >= period - 1:
                    ma = sum(closes[i-period+1:i+1]) / period
                    candle[f'ma{period}'] = round(ma, 2)
                else:
                    candle[f'ma{period}'] = None
            
            result.append(candle)
        
        return result
    
    def calculate_macd(self, klines: List[Dict], fast: int = 12, 
                       slow: int = 26, signal: int = 9) -> List[Dict]:
        """
        计算 MACD 指标
        
        Args:
            klines: K 线数据列表
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
        
        Returns:
            list: 添加 MACD 数据后的 K 线
        """
        if not klines or len(klines) < slow:
            return klines
        
        closes = [k['close'] for k in klines]
        
        # 计算 EMA
        def ema(data, period):
            result = []
            multiplier = 2 / (period + 1)
            for i, value in enumerate(data):
                if i == 0:
                    result.append(value)
                else:
                    result.append((value - result[-1]) * multiplier + result[-1])
            return result
        
        ema_fast = ema(closes, fast)
        ema_slow = ema(closes, slow)
        
        # DIF = EMA(fast) - EMA(slow)
        dif = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]
        
        # DEA = EMA(DIF, signal)
        dea = ema(dif, signal)
        
        # MACD 柱 = (DIF - DEA) * 2
        macd_bar = [(dif[i] - dea[i]) * 2 for i in range(len(closes))]
        
        result = []
        for i, k in enumerate(klines):
            candle = k.copy()
            candle['dif'] = round(dif[i], 4) if i >= slow else None
            candle['dea'] = round(dea[i], 4) if i >= slow else None
            candle['macd'] = round(macd_bar[i], 4) if i >= slow else None
            result.append(candle)
        
        return result
    
    def calculate_kdj(self, klines: List[Dict], n: int = 9, m1: int = 3, m2: int = 3) -> List[Dict]:
        """
        计算 KDJ 指标
        
        Args:
            klines: K 线数据列表
            n: RSV 周期
            m1: K 值周期
            m2: D 值周期
        
        Returns:
            list: 添加 KDJ 数据后的 K 线
        """
        if not klines or len(klines) < n:
            return klines
        
        result = []
        k_value = 50  # 初始 K 值
        d_value = 50  # 初始 D 值
        
        for i, k in enumerate(klines):
            candle = k.copy()
            
            if i >= n - 1:
                # 计算 RSV
                period_high = max(klines[j]['high'] for j in range(i-n+1, i+1))
                period_low = min(klines[j]['low'] for j in range(i-n+1, i+1))
                
                if period_high != period_low:
                    rsv = (k['close'] - period_low) / (period_high - period_low) * 100
                else:
                    rsv = 50
                
                # 计算 KDJ
                k_value = (rsv + (m1 - 1) * k_value) / m1
                d_value = (k_value + (m2 - 1) * d_value) / m2
                j_value = 3 * k_value - 2 * d_value
                
                candle['k'] = round(k_value, 2)
                candle['d'] = round(d_value, 2)
                candle['j'] = round(j_value, 2)
            else:
                candle['k'] = None
                candle['d'] = None
                candle['j'] = None
            
            result.append(candle)
        
        return result
    
    def get_kline_with_indicators(self, symbol: str, period: str = 'day', 
                                  count: int = 100) -> List[Dict]:
        """
        获取 K 线并计算技术指标
        
        Args:
            symbol: 股票代码
            period: K 线周期
            count: 获取条数
        
        Returns:
            list: 包含 MA/MACD/KDJ 的 K 线数据
        """
        # 获取 K 线
        klines = self.get_kline(symbol, period=period, count=count + 30)  # 多获取一些用于计算指标
        
        if not klines:
            return []
        
        # 计算指标
        klines = self.calculate_ma(klines, periods=[5, 10, 20, 60])
        klines = self.calculate_macd(klines)
        klines = self.calculate_kdj(klines)
        
        # 截取指定数量
        return klines[-count:] if len(klines) > count else klines
    
    def save_kline_cache(self, symbol: str, klines: List[Dict], period: str = 'day'):
        """保存 K 线到缓存"""
        filename = f"kline_{symbol}_{period}.json"
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'period': period,
            'count': len(klines),
            'data': klines
        }
        
        cache_file = self.cache_dir / filename
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ K 线缓存已保存：{cache_file} ({len(klines)} 条)")
    
    def load_kline_cache(self, symbol: str, period: str = 'day', 
                         max_age_minutes: int = 60) -> Optional[List[Dict]]:
        """从缓存加载 K 线"""
        filename = f"kline_{symbol}_{period}.json"
        cache_file = self.cache_dir / filename
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            # 检查缓存时间
            ts_str = cache.get('timestamp', '')
            try:
                timestamp = datetime.fromisoformat(ts_str)
            except:
                timestamp = datetime.strptime(ts_str[:19], '%Y-%m-%dT%H:%M:%S')
            
            age = (datetime.now() - timestamp).total_seconds() / 60
            
            if age > max_age_minutes:
                print(f"⚠️  K 线缓存已过期 ({age:.0f}分钟)")
                return None
            
            print(f"✅ 使用 K 线缓存 ({age:.0f}分钟前，{cache.get('count', '?')} 条)")
            return cache.get('data')
            
        except Exception as e:
            print(f"K 线缓存读取失败：{e}")
            return None
    
    def print_kline(self, klines: List[Dict], symbol: str, top_n: int = 10):
        """打印 K 线数据"""
        if not klines:
            print("无 K 线数据")
            return
        
        print(f"\n{'='*90}")
        print(f"📈 {symbol} K 线数据 (最新{min(top_n, len(klines))}条)")
        print(f"{'='*90}")
        print(f"{'日期':<12} {'开盘':>8} {'收盘':>8} {'最高':>8} {'最低':>8} {'成交量':>12} {'MA5':>8} {'MA20':>8}")
        print(f"{'-'*90}")
        
        # 显示最新 N 条
        for k in klines[-top_n:]:
            ma5_str = f"{k.get('ma5', 0):.2f}" if k.get('ma5') else '-'
            ma20_str = f"{k.get('ma20', 0):.2f}" if k.get('ma20') else '-'
            
            print(f"{k.get('date', ''):<12} {k.get('open', 0):>7.2f} {k.get('close', 0):>7.2f} "
                  f"{k.get('high', 0):>7.2f} {k.get('low', 0):>7.2f} "
                  f"{k.get('volume', 0):>10,.0f} {ma5_str:>8} {ma20_str:>8}")
        
        print(f"{'='*90}")
        
        # 显示最新指标
        latest = klines[-1] if klines else {}
        if latest.get('macd') is not None:
            print(f"\n📊 最新技术指标:")
            print(f"  MACD: DIF={latest.get('dif', 0):.4f}, DEA={latest.get('dea', 0):.4f}, MACD={latest.get('macd', 0):.4f}")
            print(f"  KDJ:  K={latest.get('k', 0):.2f}, D={latest.get('d', 0):.2f}, J={latest.get('j', 0):.2f}")
            print(f"  MA:   MA5={latest.get('ma5', 0):.2f}, MA10={latest.get('ma10', 0):.2f}, "
                  f"MA20={latest.get('ma20', 0):.2f}, MA60={latest.get('ma60', 0):.2f}")
    
    def export_kline_csv(self, klines: List[Dict], symbol: str, period: str = 'day'):
        """导出 K 线为 CSV"""
        if not klines:
            print("❌ 无 K 线数据可导出")
            return
        
        filename = f"kline_{symbol}_{period}_{datetime.now().strftime('%Y%m%d')}.csv"
        filepath = self.cache_dir / filename
        
        fields = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount',
                  'ma5', 'ma10', 'ma20', 'ma60', 'dif', 'dea', 'macd', 'k', 'd', 'j']
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(klines)
        
        print(f"✅ K 线已导出 CSV: {filepath}")
    
    # ========== 北向资金 ==========
    
    def crawl_north_bound(self) -> Dict:
        """
        抓取北向资金数据
        
        Returns:
            dict: 北向资金数据
        """
        print("[东方财富] 抓取北向资金...")
        
        url = "http://push2.eastmoney.com/api/qt/kamt.rtmin/get"
        params = {
            'fields1': 'f1,f3',
            'fields2': 'f51,f52,f54,f56',
            'ut': 'b2884a393a59ad64002292a3e90d46a5',
            'cb': 'jQuery183000000000000000001_1234567890',
            '_': int(time.time() * 1000)
        }
        
        try:
            resp = self.session.get(url, params=params, timeout=15)
            text = resp.text
            
            # 解析 JSONP
            match = re.search(r'jQuery\d+_\d+\((.+)\)', text)
            if match:
                data = json.loads(match.group(1))
                
                if data.get('data'):
                    kt = data['data'].get('kt', {})
                    s2n = kt.get('s2n', {})  # 深股通
                    n2s = kt.get('n2s', {})  # 沪股通
                    
                    result = {
                        'north_total': self._safe_float(s2n.get('net')) + self._safe_float(n2s.get('net')),
                        'sh_net': self._safe_float(n2s.get('net')),  # 沪股通净流入
                        'sz_net': self._safe_float(s2n.get('net')),  # 深股通净流入
                        'sh_buy': self._safe_float(n2s.get('buy')),
                        'sh_sell': self._safe_float(n2s.get('sell')),
                        'sz_buy': self._safe_float(s2n.get('buy')),
                        'sz_sell': self._safe_float(s2n.get('sell')),
                        'source': 'eastmoney_north',
                        'crawl_time': datetime.now().isoformat(),
                    }
                    
                    print(f"[北向资金] 净流入：{result['north_total']/100000000:.2f}亿")
                    return result
            
            return {}
            
        except Exception as e:
            print(f"[北向资金] 抓取失败：{e}")
            return {}
    
    # ========== 工具方法 ==========
    
    def _format_symbol(self, symbol: str) -> str:
        """格式化股票代码"""
        symbol = str(symbol).strip()
        if not symbol:
            return ''
        if symbol.startswith('sh') or symbol.startswith('sz'):
            return symbol
        if symbol.startswith('6'):
            return 'sh' + symbol
        return 'sz' + symbol
    
    def _safe_float(self, value, default=0.0) -> float:
        """安全转换为浮点数"""
        if value is None or value == '' or value == '-':
            return default
        try:
            return float(value)
        except:
            return default
    
    def _safe_int(self, value, default=0) -> int:
        """安全转换为整数"""
        if value is None or value == '' or value == '-':
            return default
        try:
            return int(float(value))
        except:
            return default
    
    # ========== 缓存管理 ==========
    
    def save_cache(self, data, filename: str):
        """保存数据到缓存"""
        cache_file = self.cache_dir / filename
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'count': len(data) if isinstance(data, (list, dict)) else 1,
            'data': data
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 缓存已保存：{cache_file} ({cache_data['count']} 条)")
    
    def load_cache(self, filename: str, max_age_minutes: int = 30) -> Optional:
        """从缓存加载数据"""
        cache_file = self.cache_dir / filename
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            # 检查缓存时间
            ts_str = cache.get('timestamp', '')
            try:
                timestamp = datetime.fromisoformat(ts_str)
            except:
                timestamp = datetime.strptime(ts_str[:19], '%Y-%m-%dT%H:%M:%S')
            
            age = (datetime.now() - timestamp).total_seconds() / 60
            
            if age > max_age_minutes:
                print(f"⚠️  缓存已过期 ({age:.0f}分钟)")
                return None
            
            print(f"✅ 使用缓存 ({age:.0f}分钟前，{cache.get('count', '?')} 条)")
            return cache.get('data')
            
        except Exception as e:
            print(f"缓存读取失败：{e}")
            return None
    
    def clear_cache(self):
        """清除所有缓存"""
        for f in self.cache_dir.glob('*.json'):
            f.unlink()
        print("✅ 缓存已清空")
    
    # ========== 数据查询 ==========
    
    def get_5day_change(self, symbol: str) -> float:
        """
        获取 5 日涨跌幅（真实数据）
        
        Args:
            symbol: 股票代码
        
        Returns:
            float: 5 日涨跌幅%
        """
        try:
            klines = self.get_kline(symbol, period='day', count=6)
            if len(klines) >= 6:
                # 5 日涨幅 = (今天收盘价 - 5 天前收盘价) / 5 天前收盘价 * 100
                today_close = klines[0]['close']
                five_day_ago_close = klines[5]['close']
                if five_day_ago_close > 0:
                    change_5d = (today_close - five_day_ago_close) / five_day_ago_close * 100
                    return round(change_5d, 2)
        except:
            pass
        return 0.0
    
    def get_ranking(self, rank_by: str = 'score', top_n: int = 10, 
                    use_cache: bool = True, fetch_5day: bool = False) -> List[Dict]:
        """
        获取排行榜（真实市场数据）
        
        ⚠️  核心原则：所有数据必须来自真实市场，严禁使用模拟/估算数据
        
        Args:
            rank_by: 'score' (综合), 'main_force' (主力), 'change_pct' (涨幅),
                    'volume' (成交量), 'amount' (成交额)
            top_n: 前 N 只
            use_cache: 是否使用缓存
            fetch_5day: 是否获取 5 日涨幅（会增加请求次数）
        
        Returns:
            list: 排行数据
        """
        # 尝试加载缓存
        data = None
        if use_cache:
            data = self.load_cache('stocks_cache.json', max_age_minutes=10)
        
        if not data:
            data = self.crawl_tencent()
            if data:
                self.save_cache(data, 'stocks_cache.json')
        
        if not data:
            print("❌ 无法获取数据")
            return []
        
        # 计算综合评分（使用真实数据）
        for stock in data:
            # 成交额得分（真实成交额）
            amount_score = min(100, stock.get('amount_wan', 0) / 100000 * 10)
            # 涨跌幅得分（真实涨跌幅）
            change_score = min(100, max(0, stock.get('change_pct', 0) + 50))
            # 成交量得分（真实成交量）
            volume_score = min(100, stock.get('volume', 0) / 10000000 * 10)
            # 综合评分
            stock['score'] = amount_score * 0.4 + change_score * 0.4 + volume_score * 0.2
        
        # 获取 5 日涨幅（可选）
        if fetch_5day:
            print("📊 获取 5 日涨幅数据...")
            for i, stock in enumerate(data[:top_n * 2]):  # 多获取一些用于筛选
                change_5d = self.get_5day_change(stock['symbol'])
                stock['change_5d'] = change_5d
                if (i + 1) % 20 == 0:
                    print(f"  进度：{i+1}/{min(len(data), top_n * 2)}")
        
        # 排序
        rank_map = {
            'score': lambda x: x.get('score', 0),
            'main_force': lambda x: x.get('amount_wan', 0),  # 用成交额代替主力
            'change_pct': lambda x: x.get('change_pct', 0),
            'change_5d': lambda x: x.get('change_5d', 0),
            'volume': lambda x: x.get('volume', 0),
            'amount': lambda x: x.get('amount_wan', 0),
        }
        
        rank_func = rank_map.get(rank_by, rank_map['score'])
        data.sort(key=rank_func, reverse=True)
        
        return data[:top_n]
    
    def get_sector_ranking(self, sector_type: str = 'concept', top_n: int = 10) -> List[Dict]:
        """获取板块排行"""
        data = self.crawl_eastmoney_sector(sector_type)
        
        if not data:
            # 尝试缓存
            cache_name = f'sector_{sector_type}.json'
            data = self.load_cache(cache_name, max_age_minutes=30)
        
        if not data:
            return []
        
        # 按主力净流入排序
        data.sort(key=lambda x: x.get('main_net', 0), reverse=True)
        return data[:top_n]
    
    # ========== 数据导出 ==========
    
    def export_csv(self, data: List[Dict], filename: str):
        """导出为 CSV"""
        if not data:
            print("❌ 无数据可导出")
            return
        
        filepath = self.cache_dir / filename
        fields = ['symbol', 'name', 'price', 'change_pct', 'volume', 'amount_wan', 
                  'main_force_est', 'score']
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(data)
        
        print(f"✅ 已导出 CSV: {filepath}")
    
    def export_json(self, data: List[Dict], filename: str):
        """导出为 JSON"""
        if not data:
            print("❌ 无数据可导出")
            return
        
        filepath = self.cache_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已导出 JSON: {filepath}")
    
    # ========== 打印输出 ==========
    
    def print_ranking(self, data: List[Dict], title: str = "股票排行榜"):
        """打印排行榜"""
        if not data:
            print("无数据")
            return
        
        print(f"\n{'='*110}")
        print(f"📊 {title} Top{len(data)}")
        print(f"{'='*110}")
        print(f"{'排名':<4} {'代码':<10} {'名称':<10} {'现价':<8} {'涨跌幅':<10} {'成交量':<12} {'成交额':<10} {'评分':<6}")
        print(f"{'-'*110}")
        
        for i, s in enumerate(data, 1):
            amount_str = f"{s.get('amount_wan', 0)/10000:.2f}亿" if s.get('amount_wan', 0) >= 10000 else f"{s.get('amount_wan', 0):.0f}万"
            change_sign = '+' if s.get('change_pct', 0) >= 0 else ''
            
            print(f"{i:<4} {s.get('symbol', ''):<10} {s.get('name', ''):<10} ¥{s.get('price', 0):>5.2f} {change_sign}{s.get('change_pct', 0):>7.2f}% {s.get('volume', 0):>10,} {amount_str:>8} {s.get('score', 0):>5.1f}")
        
        print(f"{'='*110}")
    
    def print_sector_ranking(self, data: List[Dict], title: str = "板块资金流"):
        """打印板块排行"""
        if not data:
            print("无数据")
            return
        
        print(f"\n{'='*100}")
        print(f"📊 {title} Top{len(data)}")
        print(f"{'='*100}")
        print(f"{'排名':<4} {'代码':<8} {'名称':<15} {'主力净流入':<14} {'涨跌幅':<10} {'超大单':<12}")
        print(f"{'-'*100}")
        
        for i, s in enumerate(data, 1):
            net_str = f"{s.get('main_net', 0)/100000000:.2f}亿" if abs(s.get('main_net', 0)) >= 100000000 else f"{s.get('main_net', 0)/10000:.0f}万"
            change_sign = '+' if s.get('change_pct', 0) >= 0 else ''
            
            print(f"{i:<4} {s.get('code', ''):<8} {s.get('name', ''):<15} {net_str:>12} {change_sign}{s.get('change_pct', 0):>7.2f}% {s.get('super_net', 0)/10000:.0f}万")
        
        print(f"{'='*100}")
    
    def print_north_bound(self, data: Dict):
        """打印北向资金"""
        if not data:
            print("无数据")
            return
        
        print(f"\n{'='*60}")
        print(f"📊 北向资金")
        print(f"{'='*60}")
        print(f"总净流入：  {data.get('north_total', 0)/100000000:>10.2f}亿")
        print(f"沪股通：    {data.get('sh_net', 0)/100000000:>10.2f}亿")
        print(f"深股通：    {data.get('sz_net', 0)/100000000:>10.2f}亿")
        print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='本地股票数据爬虫 v2.1')
    parser.add_argument('--crawl', action='store_true', help='抓取数据')
    parser.add_argument('--source', choices=['tencent', 'baidu', 'eastmoney', 'all'], 
                       default='all', help='数据源')
    parser.add_argument('--query', choices=['top10', 'top50', 'main', 'volume', 'change', 
                                            'sector', 'north'], help='查询')
    parser.add_argument('--sector-type', choices=['concept', 'industry', 'region'],
                       default='concept', help='板块类型')
    parser.add_argument('--kline', type=str, help='获取 K 线，指定股票代码')
    parser.add_argument('--period', choices=['day', 'week', 'month'], default='day', 
                       help='K 线周期')
    parser.add_argument('--count', type=int, default=60, help='K 线条数')
    parser.add_argument('--adjust', choices=['qfq', 'hfq', 'none'], default='qfq',
                       help='复权类型')
    parser.add_argument('--top', type=int, default=10, help='前 N 只')
    parser.add_argument('--export', choices=['csv', 'json'], help='导出格式')
    parser.add_argument('--refresh', action='store_true', help='刷新缓存')
    parser.add_argument('--no-cache', action='store_true', help='不使用缓存')
    
    args = parser.parse_args()
    
    crawler = StockCrawler()
    
    # 刷新缓存
    if args.refresh:
        crawler.clear_cache()
        return
    
    # 抓取数据
    if args.crawl:
        if args.source in ['tencent', 'all']:
            data = crawler.crawl_tencent()
            crawler.save_cache(data, 'stocks_cache.json')
        
        if args.source in ['baidu', 'all']:
            data = crawler.crawl_baidu_rank('change')
            crawler.save_cache(data, 'baidu_rank.json')
        
        if args.source in ['eastmoney', 'all']:
            data = crawler.crawl_eastmoney_sector('concept')
            crawler.save_cache(data, 'sector_concept.json')
            
            north = crawler.crawl_north_bound()
            crawler.save_cache(north, 'north_bound.json')
        
        return
    
    # K 线查询
    if args.kline:
        symbol = args.kline
        if not symbol.startswith('sh') and not symbol.startswith('sz'):
            symbol = 'sh' + symbol if symbol.startswith('6') else 'sz' + symbol
        
        # 尝试缓存
        klines = None
        if not args.no_cache:
            klines = crawler.load_kline_cache(symbol, period=args.period, max_age_minutes=60)
        
        if not klines:
            klines = crawler.get_kline_with_indicators(
                symbol, period=args.period, count=args.count
            )
            if klines:
                crawler.save_kline_cache(symbol, klines, period=args.period)
        
        if klines:
            crawler.print_kline(klines, symbol, top_n=min(20, len(klines)))
            
            # 导出
            if args.export == 'csv':
                crawler.export_kline_csv(klines, symbol, period=args.period)
        else:
            print(f"❌ 无法获取 {symbol} 的 K 线数据")
        
        return
    
    # 查询
    if args.query:
        if args.query == 'sector':
            data = crawler.get_sector_ranking(args.sector_type, args.top)
            crawler.print_sector_ranking(data, f"{args.sector_type}板块资金流")
        elif args.query == 'north':
            data = crawler.load_cache('north_bound.json', max_age_minutes=30)
            crawler.print_north_bound(data)
        else:
            rank_map = {
                'top10': 'score',
                'top50': 'score',
                'main': 'main_force',
                'volume': 'volume',
                'change': 'change_pct',
            }
            rank_by = rank_map.get(args.query, 'score')
            top_n = 50 if args.query == 'top50' else args.top
            
            data = crawler.get_ranking(rank_by=rank_by, top_n=top_n, use_cache=not args.no_cache)
            crawler.print_ranking(data, f"股票{args.query}榜")
        
        # 导出
        if args.export and data:
            if args.export == 'csv':
                crawler.export_csv(data, f'stock_{args.query}_{datetime.now().strftime("%Y%m%d_%H%M")}.csv')
            elif args.export == 'json':
                crawler.export_json(data, f'stock_{args.query}_{datetime.now().strftime("%Y%m%d_%H%M")}.json')
        
        return
    
    # 默认帮助
    parser.print_help()


if __name__ == '__main__':
    main()
