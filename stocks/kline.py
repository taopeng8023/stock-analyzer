#!/usr/bin/env python3
"""
股票 K 线数据获取模块 v2
支持多数据源：东方财富、腾讯财经、新浪财经

⚠️  重要声明：本模块仅使用真实市场数据，严禁生成或使用任何模拟数据
    所有交易决策请基于官方交易所数据，本工具仅供参考

功能:
1. 多数据源自动切换
2. 本地缓存
3. 技术指标计算 (MA/MACD/KDJ)
4. 数据导出 CSV

用法:
    python3 kline.py sh600000 --days 60
    python3 kline.py sz000001 --period week
    python3 kline.py sh600519 --export  # 导出 CSV
"""

import requests
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import random


class KlineFetcher:
    """K 线数据获取"""
    
    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir or Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Referer': 'http://quote.eastmoney.com/',
        }
    
    def fetch_eastmoney(self, symbol: str, period: str = 'day', count: int = 60) -> list:
        """
        从东方财富获取 K 线
        """
        print(f"[东方财富] 获取 {symbol} K 线...")
        
        if symbol.startswith('sh'):
            sec_id = f"1.{symbol[2:]}"
        elif symbol.startswith('sz'):
            sec_id = f"0.{symbol[2:]}"
        else:
            sec_id = f"1.{symbol}" if symbol.startswith('6') else f"0.{symbol}"
        
        klt_map = {'day': '101', 'week': '102', 'month': '103'}
        klt = klt_map.get(period, '101')
        
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            'secid': sec_id,
            'klt': klt,
            'fqt': '1',
            'beg': '0',
            'end': '20500101',
            'count': count,
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=15)
            data = resp.json()
            
            if data.get('rc') == 0 and data.get('data'):
                klines_data = data['data'].get('klines', [])
                return self._parse_kline(klines_data)
            else:
                print(f"  返回错误：rc={data.get('rc')}")
                return []
        except Exception as e:
            print(f"  获取失败：{e}")
            return []
    
    def fetch_tencent(self, symbol: str, period: str = 'day', count: int = 60) -> list:
        """
        从腾讯财经获取 K 线（备用）
        """
        print(f"[腾讯财经] 获取 {symbol} K 线...")
        
        url = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        
        period_map = {'day': 'day', 'week': 'week', 'month': 'month'}
        p = period_map.get(period, 'day')
        param = f"{symbol},qfq{p},,,{count}"
        
        try:
            resp = requests.get(url, params={'param': param}, headers=self.headers, timeout=15)
            data = resp.json()
            
            if data.get('code') == 0:
                kline_data = data.get('data', {})
                key = f"qfq{p}"
                klines = kline_data.get(key, [])
                
                result = []
                for k in klines:
                    if len(k) >= 7:
                        result.append({
                            'date': k[0],
                            'open': float(k[1]),
                            'close': float(k[2]),
                            'high': float(k[3]),
                            'low': float(k[4]),
                            'volume': float(k[5]),
                            'amount': float(k[6]) if len(k) > 6 else 0,
                        })
                
                print(f"  获取 {len(result)} 条")
                return result
            else:
                print(f"  返回错误：{data.get('msg')}")
                return []
        except Exception as e:
            print(f"  获取失败：{e}")
            return []
    
    def _parse_kline(self, klines_data: list) -> list:
        """解析 K 线数据"""
        result = []
        for k in klines_data:
            fields = k.split(',')
            if len(fields) >= 11:
                result.append({
                    'date': fields[0],
                    'open': float(fields[1]),
                    'close': float(fields[2]),
                    'high': float(fields[3]),
                    'low': float(fields[4]),
                    'volume': float(fields[5]),
                    'amount': float(fields[6]),
                    'amplitude': float(fields[7]) if fields[7] else 0,
                    'change_pct': float(fields[8]) if fields[8] else 0,
                    'change': float(fields[9]) if fields[9] else 0,
                    'turnover': float(fields[10]) if fields[10] else 0,
                })
        return result
    
    def fetch(self, symbol: str, period: str = 'day', count: int = 60,
              use_cache: bool = True) -> list:
        """
        获取 K 线（自动选择数据源）
        
        ⚠️  仅使用真实市场数据，如果所有数据源都失败，返回空列表
        """
        # 缓存
        if use_cache:
            cached = self.load_cache(symbol, period)
            if cached:
                return cached
        
        # 东方财富优先
        klines = self.fetch_eastmoney(symbol, period=period, count=count)
        
        # 失败则尝试腾讯
        if not klines:
            klines = self.fetch_tencent(symbol, period=period, count=count)
        
        # ⚠️  如果所有数据源都失败，返回空列表 - 绝不使用模拟数据
        if not klines:
            print("⚠️  所有数据源获取失败，返回空数据（不使用模拟数据）")
            return []
        
        # 保存缓存
        if klines:
            self.save_cache(symbol, period, klines)
        
        return klines
    
    def save_cache(self, symbol: str, period: str, klines: list):
        """保存缓存"""
        filename = f"kline_{symbol}_{period}.json"
        cache_file = self.cache_dir / filename
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'period': period,
                'data': klines
            }, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 缓存已保存")
    
    def load_cache(self, symbol: str, period: str, max_age_minutes: int = 120) -> list:
        """加载缓存"""
        filename = f"kline_{symbol}_{period}.json"
        cache_file = self.cache_dir / filename
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            ts_str = cache.get('timestamp', '')
            try:
                timestamp = datetime.fromisoformat(ts_str)
            except:
                timestamp = datetime.strptime(ts_str[:19], '%Y-%m-%dT%H:%M:%S')
            
            age = (datetime.now() - timestamp).total_seconds() / 60
            
            if age > max_age_minutes:
                print(f"⚠️  缓存已过期 ({age:.0f}分钟)")
                return None
            
            print(f"✅ 使用缓存 ({age:.0f}分钟前)")
            return cache.get('data')
        except:
            return None
    
    def calculate_indicators(self, klines: list) -> list:
        """计算技术指标"""
        if not klines:
            return []
        
        closes = [k['close'] for k in klines]
        
        # MA
        for i, k in enumerate(klines):
            for period in [5, 10, 20, 60]:
                if i >= period - 1:
                    k[f'ma{period}'] = round(sum(closes[i-period+1:i+1]) / period, 2)
                else:
                    k[f'ma{period}'] = None
        
        # MACD
        def ema(data, period):
            result = []
            m = 2 / (period + 1)
            for v in data:
                if not result:
                    result.append(v)
                else:
                    result.append((v - result[-1]) * m + result[-1])
            return result
        
        ema12 = ema(closes, 12)
        ema26 = ema(closes, 26)
        dif = [ema12[i] - ema26[i] for i in range(len(closes))]
        dea = ema(dif, 9)
        macd_bar = [(dif[i] - dea[i]) * 2 for i in range(len(closes))]
        
        for i, k in enumerate(klines):
            if i >= 26:
                k['dif'] = round(dif[i], 4)
                k['dea'] = round(dea[i], 4)
                k['macd'] = round(macd_bar[i], 4)
            else:
                k['dif'] = k['dea'] = k['macd'] = None
        
        # KDJ
        k_val, d_val = 50, 50
        for i, k in enumerate(klines):
            if i >= 8:
                h = max(klines[j]['high'] for j in range(i-8, i+1))
                l = min(klines[j]['low'] for j in range(i-8, i+1))
                rsv = (k['close'] - l) / (h - l) * 100 if h != l else 50
                k_val = (rsv + 2 * k_val) / 3
                d_val = (k_val + 2 * d_val) / 3
                k['k'] = round(k_val, 2)
                k['d'] = round(d_val, 2)
                k['j'] = round(3 * k_val - 2 * d_val, 2)
            else:
                k['k'] = k['d'] = k['j'] = None
        
        return klines
    
    def print_kline(self, klines: list, symbol: str, top_n: int = 20):
        """打印 K 线"""
        if not klines:
            print("无 K 线数据")
            return
        
        print(f"\n{'='*105}")
        print(f"📈 {symbol} K 线数据 (最新{min(top_n, len(klines))}条)")
        print(f"{'='*105}")
        print(f"{'日期':<12} {'开盘':>8} {'收盘':>8} {'最高':>8} {'最低':>8} {'成交量':>10} {'MA5':>7} {'MA20':>7} {'MACD':>8}")
        print(f"{'-'*105}")
        
        for k in klines[-top_n:]:
            ma5 = f"{k.get('ma5', 0):.2f}" if k.get('ma5') else '-'
            ma20 = f"{k.get('ma20', 0):.2f}" if k.get('ma20') else '-'
            macd = f"{k.get('macd', 0):.2f}" if k.get('macd') else '-'
            
            print(f"{k.get('date', ''):<12} {k.get('open', 0):>7.2f} {k.get('close', 0):>7.2f} "
                  f"{k.get('high', 0):>7.2f} {k.get('low', 0):>7.2f} "
                  f"{k.get('volume', 0):>8.0f}万 {ma5:>7} {ma20:>7} {macd:>8}")
        
        print(f"{'='*105}")
        
        latest = klines[-1] if klines else {}
        print(f"\n📊 最新指标 ({latest.get('date', '')}):")
        if latest.get('ma5') is not None:
            ma5 = latest.get('ma5', 0)
            ma10 = latest.get('ma10') or 0
            ma20 = latest.get('ma20') or 0
            ma60 = latest.get('ma60') or 0
            print(f"  MA:  MA5={ma5:.2f}, MA10={ma10:.2f}, MA20={ma20:.2f}, MA60={ma60:.2f}")
        if latest.get('macd') is not None:
            print(f"  MACD: DIF={latest.get('dif', 0):.4f}, DEA={latest.get('dea', 0):.4f}, "
                  f"MACD={latest.get('macd', 0):.4f}")
        if latest.get('k') is not None:
            print(f"  KDJ:  K={latest.get('k', 0):.2f}, D={latest.get('d', 0):.2f}, "
                  f"J={latest.get('j', 0):.2f}")
    
    def export_csv(self, klines: list, symbol: str, period: str = 'day'):
        """导出 CSV"""
        import csv
        
        if not klines:
            return
        
        filename = f"kline_{symbol}_{period}_{datetime.now().strftime('%Y%m%d')}.csv"
        filepath = self.cache_dir / filename
        
        fields = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount',
                  'ma5', 'ma10', 'ma20', 'ma60', 'dif', 'dea', 'macd', 'k', 'd', 'j']
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(klines)
        
        print(f"✅ 已导出：{filepath}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='股票 K 线数据获取 v2')
    parser.add_argument('symbol', help='股票代码')
    parser.add_argument('--period', choices=['day', 'week', 'month'], default='day')
    parser.add_argument('--count', type=int, default=60)
    parser.add_argument('--export', action='store_true', help='导出 CSV')
    parser.add_argument('--no-cache', action='store_true', help='不使用缓存')
    
    args = parser.parse_args()
    
    symbol = args.symbol
    if not symbol.startswith('sh') and not symbol.startswith('sz'):
        symbol = ('sh' if symbol.startswith('6') else 'sz') + symbol
    
    fetcher = KlineFetcher()
    
    # ⚠️  仅使用真实市场数据
    klines = fetcher.fetch(symbol, period=args.period, count=args.count,
                          use_cache=not args.no_cache)
    
    if klines:
        klines = fetcher.calculate_indicators(klines)
        fetcher.print_kline(klines, symbol)
        
        if args.export:
            fetcher.export_csv(klines, symbol, period=args.period)
    else:
        print(f"\n⚠️  无法获取 {symbol} 的真实 K 线数据")
        print(f"提示：可能是网络问题或 API 暂时不可用，请稍后重试")
        print(f"⚠️  本工具不使用模拟数据，所有数据必须来自真实市场")


if __name__ == '__main__':
    main()
