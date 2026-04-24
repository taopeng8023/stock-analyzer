#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票实时行情 API
支持新浪财经、东方财富接口
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import re

class StockAPI:
    """股票行情 API 封装"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        })
        self.retry_count = 3
        self.timeout = 10
    
    def get_quote_sina(self, code: str) -> Optional[Dict]:
        """
        获取实时行情（新浪财经）
        返回：{code, name, price, change, change_percent, open, high, low, 
              volume, amount, bid, ask, date, time}
        """
        try:
            # 转换代码格式
            if code.startswith('6') or code.startswith('9'):
                symbol = f'sh{code}'
            else:
                symbol = f'sz{code}'
            
            url = f'http://hq.sinajs.cn/list={symbol}'
            resp = self.session.get(url, timeout=5)
            resp.raise_for_status()
            
            # 解析数据
            text = resp.text
            if '=' not in text:
                return None
            
            data_str = text.split('=')[1].strip('"').strip("'")
            elements = data_str.split(',')
            
            if len(elements) < 32:
                return None
            
            return {
                'code': code,
                'name': elements[0],
                'price': float(elements[3]),  # 当前价
                'open': float(elements[1]),   # 开盘价
                'high': float(elements[4]),   # 最高价
                'low': float(elements[5]),    # 最低价
                'close': float(elements[2]),  # 昨收
                'volume': int(elements[8]),   # 成交量（手）
                'amount': float(elements[9]), # 成交额（元）
                'bid': float(elements[11]),   # 买一价
                'ask': float(elements[13]),   # 卖一价
                'date': elements[30],         # 日期
                'time': elements[31],         # 时间
                'change': round(float(elements[3]) - float(elements[2]), 2),
                'change_percent': round((float(elements[3]) - float(elements[2])) / float(elements[2]) * 100, 2)
            }
        except Exception as e:
            print(f"❌ 获取行情失败 {code}: {e}")
            return None
    
    def get_kline_sina(self, code: str, period: str = 'day', days: int = 60) -> Optional[List[Dict]]:
        """
        获取 K 线数据（新浪财经）
        period: day(日)/week(周)/month(月)/minute(分钟)
        """
        try:
            # 转换代码格式
            if code.startswith('6') or code.startswith('9'):
                symbol = f'sh{code}'
            else:
                symbol = f'sz{code}'
            
            # 新浪财经 K 线 API
            url = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
            params = {
                'symbol': symbol,
                'scale': period,
                'datalen': str(days)
            }
            
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            
            text = resp.text
            if not text or text.startswith('<'):
                print(f"⚠️ API 返回异常：{text[:100]}")
                return None
            
            data = resp.json()
            
            if not isinstance(data, list):
                print(f"⚠️ 数据格式异常：{type(data)}")
                return None
            
            kline_data = []
            for item in data:
                if isinstance(item, dict):
                    kline_data.append({
                        'date': item.get('day', ''),
                        'open': float(item.get('open', 0)),
                        'high': float(item.get('high', 0)),
                        'low': float(item.get('low', 0)),
                        'close': float(item.get('close', 0)),
                        'volume': int(item.get('volume', 0))
                    })
            
            return kline_data
        except Exception as e:
            print(f"❌ 获取 K 线失败 {code}: {e}")
            return None
    
    def get_fund_flow(self, code: str) -> Optional[Dict]:
        """
        获取资金流数据（东方财富 API）
        返回：{main_net_inflow, main_ratio, super_ratio, large_ratio, medium_ratio, small_ratio}
        """
        try:
            # 转换证券 ID
            if code.startswith('6') or code.startswith('9'):
                secid = f'1.{code}'
            else:
                secid = f'0.{code}'
            
            url = 'https://push2.eastmoney.com/api/qt/stock/fflow/daykline/get'
            params = {
                'lmt': 0,
                'klt': 1,
                'fields1': 'f1,f2,f3,f7',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65',
                'ut': 'b2884a393a59ad64002292a3e90d46a5',
                'secid': secid
            }
            
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            
            if data.get('rc') != 0 or not data.get('data'):
                return None
            
            klines = data['data'].get('klines', [])
            if not klines:
                return None
            
            # 解析最新一天数据
            latest = klines[-1].split(',')
            
            return {
                'code': code,
                'name': data['data'].get('name', ''),
                'date': latest[0],
                'main_net_inflow': float(latest[1]) / 10000,  # 万元
                'small_net_inflow': float(latest[2]) / 10000,
                'medium_net_inflow': float(latest[3]) / 10000,
                'large_net_inflow': float(latest[4]) / 10000,
                'super_large_net_inflow': float(latest[5]) / 10000,
                'main_ratio': float(latest[6]),
                'small_ratio': float(latest[7]),
                'medium_ratio': float(latest[8]),
                'large_ratio': float(latest[9]),
                'super_large_ratio': float(latest[10]),
            }
        except Exception as e:
            print(f"❌ 获取资金流失败 {code}: {e}")
            return None
    
    def get_batch_quotes(self, codes: List[str]) -> List[Dict]:
        """批量获取行情"""
        results = []
        
        # 拼接代码
        symbols = []
        for code in codes:
            if code.startswith('6') or code.startswith('9'):
                symbols.append(f'sh{code}')
            else:
                symbols.append(f'sz{code}')
        
        symbol_str = ','.join(symbols)
        
        try:
            url = f'http://hq.sinajs.cn/list={symbol_str}'
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            # 解析多条数据
            for line in resp.text.strip().split('\n'):
                if '=' not in line:
                    continue
                
                var_name, data_str = line.split('=')
                code = var_name.split('_')[-1][2:]  # 提取代码
                data_str = data_str.strip('"').strip("'")
                elements = data_str.split(',')
                
                if len(elements) >= 32:
                    results.append({
                        'code': code,
                        'name': elements[0],
                        'price': float(elements[3]),
                        'open': float(elements[1]),
                        'high': float(elements[4]),
                        'low': float(elements[5]),
                        'close': float(elements[2]),
                        'volume': int(elements[8]),
                        'amount': float(elements[9]),
                        'change': round(float(elements[3]) - float(elements[2]), 2),
                        'change_percent': round((float(elements[3]) - float(elements[2])) / float(elements[2]) * 100, 2),
                        'date': elements[30],
                        'time': elements[31],
                    })
        except Exception as e:
            print(f"❌ 批量获取行情失败：{e}")
        
        return results
    
    def get_index_quote(self, index_code: str) -> Optional[Dict]:
        """
        获取指数行情
        index_code: sh000001(上证指数), sz399001(深证成指), sz399006(创业板指)
        """
        return self.get_quote_sina(index_code)

# ==================== 技术指标计算 ====================

def calculate_indicators(kline_data: List[Dict]) -> Dict:
    """计算技术指标"""
    if not kline_data:
        return {}
    
    # 提取收盘价
    closes = [d['close'] for d in kline_data]
    highs = [d['high'] for d in kline_data]
    lows = [d['low'] for d in kline_data]
    opens = [d['open'] for d in kline_data]
    
    indicators = {}
    
    # MACD
    exp1 = []
    exp2 = []
    for i in range(len(closes)):
        if i == 0:
            exp1.append(closes[0])
            exp2.append(closes[0])
        else:
            exp1.append(closes[i] * 2/13 + exp1[-1] * 11/13)
            exp2.append(closes[i] * 2/27 + exp2[-1] * 25/27)
    
    dif = [exp1[i] - exp2[i] for i in range(len(exp1))]
    dea = []
    for i in range(len(dif)):
        if i == 0:
            dea.append(dif[0])
        else:
            dea.append(dif[i] * 2/10 + dea[-1] * 8/10)
    
    macd_bar = [(dif[i] - dea[i]) * 2 for i in range(len(dif))]
    indicators['macd'] = {
        'dif': dif[-1],
        'dea': dea[-1],
        'bar': macd_bar[-1],
        'trend': '金叉' if dif[-1] > dea[-1] else '死叉'
    }
    
    # KDJ
    low_min = []
    high_max = []
    for i in range(len(closes)):
        if i < 8:
            low_min.append(min(lows[:i+1]))
            high_max.append(max(highs[:i+1]))
        else:
            low_min.append(min(lows[i-8:i+1]))
            high_max.append(max(highs[i-8:i+1]))
    
    rsv = [(closes[i] - low_min[i]) / (high_max[i] - low_min[i]) * 100 if high_max[i] != low_min[i] else 50 
           for i in range(len(closes))]
    
    k = []
    d = []
    for i in range(len(rsv)):
        if i == 0:
            k.append(rsv[0])
            d.append(rsv[0])
        else:
            k.append(rsv[i] * 2/3 + k[-1] * 1/3)
            d.append(k[-1] * 2/3 + d[-1] * 1/3)
    
    j = [3 * k[i] - 2 * d[i] for i in range(len(k))]
    indicators['kdj'] = {
        'k': k[-1],
        'd': d[-1],
        'j': j[-1],
        'position': '超买' if k[-1] > 80 else ('超卖' if k[-1] < 20 else '中性')
    }
    
    # RSI
    def calc_rsi(period):
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [max(0, d) for d in deltas]
        losses = [max(0, -d) for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period if len(gains) >= period else 0
        avg_loss = sum(losses[-period:]) / period if len(losses) >= period else 1
        
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        return 100 - (100 / (1 + rs))
    
    indicators['rsi'] = {
        'rsi6': calc_rsi(6),
        'rsi12': calc_rsi(12),
        'rsi24': calc_rsi(24)
    }
    
    # 均线
    indicators['ma'] = {}
    for period in [5, 10, 20, 60]:
        if len(closes) >= period:
            indicators['ma'][f'ma{period}'] = sum(closes[-period:]) / period
        else:
            indicators['ma'][f'ma{period}'] = closes[-1] if closes else 0
    
    # 成交量
    if kline_data:
        latest = kline_data[-1]
        avg_volume = sum(d['volume'] for d in kline_data[-5:]) / 5 if len(kline_data) >= 5 else latest['volume']
        indicators['volume'] = {
            'volume_ratio': latest['volume'] / avg_volume if avg_volume > 0 else 1,
            'turnover_rate': 0  # 需要总股本数据
        }
    
    return indicators

# ==================== 主函数 ====================

def main():
    """测试 API"""
    print("=" * 70)
    print(" " * 20 + "股票实时行情 API")
    print("=" * 70)
    
    api = StockAPI()
    
    # 测试股票
    test_codes = ['002475', '300308', '300394', '601138', '601899']
    
    # 获取实时行情
    print("\n📊 获取实时行情...")
    quotes = api.get_batch_quotes(test_codes)
    
    if quotes:
        print(f"\n{'代码':<8} {'名称':<10} {'现价':<8} {'涨跌':<8} {'涨幅':<8} {'成交量':<12}")
        print("-" * 70)
        for q in quotes:
            print(f"{q['code']:<8} {q['name']:<10} {q['price']:<8.2f} {q['change']:<8.2f} {q['change_percent']:<8.2f}% {q['volume']:<12,}")
    
    # 获取 K 线数据
    print("\n📈 获取 K 线数据（立讯精密）...")
    kline = api.get_kline_sina('002475', period='day', days=60)
    if kline:
        print(f"✅ 获取 {len(kline)} 条 K 线数据")
        print(f"最新：{kline[-1]['date']} O:{kline[-1]['open']:.2f} H:{kline[-1]['high']:.2f} L:{kline[-1]['low']:.2f} C:{kline[-1]['close']:.2f}")
        
        # 计算技术指标
        print("\n📊 计算技术指标...")
        indicators = calculate_indicators(kline)
        
        if indicators:
            print(f"  MACD: DIF={indicators['macd']['dif']:.4f}, DEA={indicators['macd']['dea']:.4f}, 趋势={indicators['macd']['trend']}")
            print(f"  KDJ: K={indicators['kdj']['k']:.2f}, D={indicators['kdj']['d']:.2f}, J={indicators['kdj']['j']:.2f}, 位置={indicators['kdj']['position']}")
            print(f"  RSI: RSI6={indicators['rsi']['rsi6']:.2f}, RSI12={indicators['rsi']['rsi12']:.2f}, RSI24={indicators['rsi']['rsi24']:.2f}")
            print(f"  均线：MA5={indicators['ma']['ma5']:.2f}, MA10={indicators['ma']['ma10']:.2f}, MA20={indicators['ma']['ma20']:.2f}, MA60={indicators['ma']['ma60']:.2f}")
    
    # 获取资金流
    print("\n💰 获取资金流数据（立讯精密）...")
    fund_flow = api.get_fund_flow('002475')
    if fund_flow:
        print(f"  主力净流入：{fund_flow['main_net_inflow']:,.0f}万")
        print(f"  主力占比：{fund_flow['main_ratio']:.2f}%")
        print(f"  超大单占比：{fund_flow['super_large_ratio']:.2f}%")
        print(f"  大单占比：{fund_flow['large_ratio']:.2f}%")
    
    print("\n✅ API 测试完成！")

if __name__ == "__main__":
    main()
