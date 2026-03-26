#!/usr/bin/env python3
"""
东方财富数据接口模块
提供 A 股行情、财务、资金流等数据获取功能
"""

import sys
import json
import re
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd


class EastMoneyAPI:
    """东方财富数据接口类"""
    
    # 基础 URL
    BASE_URL = "https://push2.eastmoney.com"
    QUOTE_URL = "https://quote.eastmoney.com"
    DATA_URL = "https://data.eastmoney.com"
    
    # 请求头
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://quote.eastmoney.com/',
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    # ========== 行情数据 ==========
    
    def get_realtime_quote(self, symbol: str) -> Dict:
        """
        获取实时行情
        symbol: 股票代码 (如 603739 或 sh603739)
        """
        # 添加市场前缀 - 东方财富 API 使用 1=SH, 0=SZ, 2=BJ
        if not symbol.startswith(('sh', 'sz', 'bj')):
            if symbol.startswith('6'):
                market = '1'
                symbol = f'sh{symbol}'
            elif symbol.startswith(('0', '3')):
                market = '0'
                symbol = f'sz{symbol}'
            else:
                market = '1'
                symbol = f'sh{symbol}'
        else:
            if symbol.startswith('sh'):
                market = '1'
            elif symbol.startswith('sz'):
                market = '0'
            elif symbol.startswith('bj'):
                market = '2'
            else:
                market = '1'
        
        # secid 格式：market.symbol (如 1.sh600089)
        secid = f"{market}.{symbol}"
        
        url = f"https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            'secid': secid,
            'fields': 'f43,f44,f45,f46,f47,f50,f51,f52,f53,f54,f55,f56,f57,f58,f84,f85,f100,f101,f102,f103,f104,f105,f106,f107,f108,f109,f110,f111,f112,f113,f114,f115,f116,f117,f118,f119,f120,f121,f122,f123,f124,f125,f126,f127,f128,f129,f130,f131,f132,f133,f134,f135,f136,f137,f138,f139,f140,f141,f142,f143,f144,f145,f146,f147,f148,f149,f150,f151,f152,f153,f154,f155,f156,f157,f158,f159,f160,f161,f162,f163,f164,f165,f166,f167,f168,f169,f170,f171,f172,f173,f174,f175,f176,f177,f178,f179,f180,f181,f182,f183,f184,f185,f186,f187,f188,f189,f190,f191,f192,f193,f194,f195,f196,f197,f198,f199,f200,f201,f202,f203,f204,f205,f206,f207,f208,f209,f210,f211,f212,f213,f214,f215,f216,f217,f218,f219,f220,f221,f222,f223,f224,f225,f226,f227,f228,f229,f230,f231,f232,f233,f234,f235,f236,f237,f238,f239,f240,f241,f242,f243,f244,f245,f246,f247,f248,f249,f250,f251,f252,f253,f254,f255,f256,f257,f258,f259,f260,f261,f262,f263,f264,f265,f266,f267,f268,f269,f270,f271,f272,f273,f274,f275,f276,f277,f278,f279,f280,f281,f282,f283,f284,f285,f286,f287,f288,f289,f290,f291,f292,f293,f294,f295,f296,f297,f298,f299,f300,f301,f302,f303,f304,f305,f306,f307,f308,f309,f310,f311,f312,f313,f314,f315,f316,f317,f318,f319,f320,f321,f322,f323,f324,f325,f326,f327,f328,f329,f330,f331,f332,f333,f334,f335,f336,f337,f338,f339,f340,f341,f342,f343,f344,f345,f346,f347,f348,f349,f350,f351,f352,f353,f354,f355,f356,f357,f358,f359,f360,f361,f362,f363,f364,f365,f366,f367,f368,f369,f370,f371,f372,f373,f374,f375,f376,f377,f378,f379,f380,f381,f382,f383,f384,f385,f386,f387,f388,f389,f390,f391,f392,f393,f394,f395,f396,f397,f398,f399,f400,f401,f402,f403,f404,f405,f406,f407,f408,f409,f410,f411,f412,f413,f414,f415,f416,f417,f418,f419,f420,f421,f422,f423,f424,f425,f426,f427,f428,f429,f430,f431,f432,f433,f434,f435,f436,f437,f438,f439,f440,f441,f442,f443,f444,f445,f446,f447,f448,f449,f450,f451,f452,f453,f454,f455,f456,f457,f458,f459,f460,f461,f462,f463,f464,f465,f466,f467,f468,f469,f470,f471,f472,f473,f474,f475,f476,f477,f478,f479,f480,f481,f482,f483,f484,f485,f486,f487,f488,f489,f490,f491,f492,f493,f494,f495,f496,f497,f498,f499,f500',
            '_': int(datetime.now().timestamp() * 1000)
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('data'):
                quote = data['data']
                return {
                    '代码': symbol,
                    '名称': quote.get('f58', 'N/A'),
                    '最新价': quote.get('f43', 0) / 100,  # 价格需要除以 100
                    '涨跌幅': quote.get('f170', 0),  # 涨跌幅百分比
                    '涨跌额': quote.get('f169', 0) / 100,
                    '今开': quote.get('f46', 0) / 100,
                    '昨收': quote.get('f60', 0) / 100,
                    '最高': quote.get('f44', 0) / 100,
                    '最低': quote.get('f45', 0) / 100,
                    '成交量': quote.get('f47', 0),
                    '成交额': quote.get('f48', 0),
                    '换手率': quote.get('f168', 0),
                    '量比': quote.get('f167', 0),
                    '总市值': quote.get('f116', 0),
                    '流通市值': quote.get('f117', 0),
                    '市盈率': quote.get('f162', 0),
                    '市净率': quote.get('f163', 0),
                    '每股收益': quote.get('f108', 0),
                    '每股净资产': quote.get('f146', 0),
                    '毛利率': quote.get('f182', 0),
                    '净利率': quote.get('f183', 0),
                    'ROE': quote.get('f184', 0),
                }
            else:
                return {'error': '未获取到数据'}
        except Exception as e:
            return {'error': str(e)}
    
    def get_kline_data(self, symbol: str, period: str = 'day', 
                       count: int = 100, adjust: str = 'qfq') -> pd.DataFrame:
        """
        获取 K 线数据
        
        Args:
            symbol: 股票代码
            period: 周期 (day/week/month/minute)
            count: 数据条数
            adjust: 复权类型 (qfq-前复权/hfq-后复权/no-不复权)
        
        Returns:
            DataFrame 包含 K 线数据
        """
        # 添加市场前缀
        if not symbol.startswith(('sh', 'sz', 'bj')):
            if symbol.startswith('6'):
                symbol = f'sh{symbol}'
            elif symbol.startswith(('0', '3')):
                symbol = f'sz{symbol}'
            else:
                symbol = f'sh{symbol}'
        
        # 周期映射
        period_map = {
            'day': '101',
            'week': '102',
            'month': '103',
            '1m': '1',
            '5m': '5',
            '15m': '15',
            '30m': '30',
            '60m': '60',
        }
        
        # 复权映射
        adjust_map = {
            'qfq': '1',
            'hfq': '2',
            'no': '0'
        }
        
        url = f"{self.BASE_URL}/api/qt/stock/kline/get"
        params = {
            'secid': symbol,
            'klt': period_map.get(period, '101'),
            'fqt': adjust_map.get(adjust, '1'),
            'beg': '0',
            'end': '20500101',
            'lmt': str(count),
            '_': int(datetime.now().timestamp() * 1000)
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('data') and data['data'].get('klines'):
                klines = data['data']['klines']
                
                # 解析 K 线数据
                # 格式：日期，开盘，收盘，最高，最低，成交量，成交额，振幅，涨跌幅，涨跌额，换手率
                df_data = []
                for line in klines:
                    parts = line.split(',')
                    if len(parts) >= 11:
                        df_data.append({
                            '日期': parts[0],
                            '开盘': float(parts[1]),
                            '收盘': float(parts[2]),
                            '最高': float(parts[3]),
                            '最低': float(parts[4]),
                            '成交量': int(float(parts[5])),
                            '成交额': float(parts[6]),
                            '振幅': float(parts[7]),
                            '涨跌幅': float(parts[8]),
                            '涨跌额': float(parts[9]),
                            '换手率': float(parts[10])
                        })
                
                df = pd.DataFrame(df_data)
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            print(f"获取 K 线数据失败：{e}", file=sys.stderr)
            return pd.DataFrame()
    
    # ========== 财务数据 ==========
    
    def get_financial_indicators(self, symbol: str) -> Dict:
        """获取财务指标"""
        if not symbol.startswith(('sh', 'sz', 'bj')):
            if symbol.startswith('6'):
                symbol = f'sh{symbol}'
            else:
                symbol = f'sz{symbol}'
        
        url = "https://emweb.securities.eastmoney.com/PC_HSF10/FinanceAnalysis/Index"
        params = {
            'code': symbol,
            'type': 'cwfx'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            # 财务数据需要解析 HTML，这里简化处理
            return {
                'symbol': symbol,
                'note': '财务数据需要解析 HTML 页面'
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_performance_report(self, symbol: str) -> pd.DataFrame:
        """获取业绩报表"""
        if not symbol.startswith(('sh', 'sz', 'bj')):
            if symbol.startswith('6'):
                symbol = f'sh{symbol}'
            else:
                symbol = f'sz{symbol}'
        
        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            'reportName': 'RPT_FCI_PERFORMANCEPRED',
            'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR,PREDICTEPS,PREDICTPROFIT,PREDICYOYGR',
            'filter': f'(SECURITY_CODE="{symbol[2:]}")',
            'pageSize': '10',
            'pageNumber': '1'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('result') and data['result'].get('data'):
                return pd.DataFrame(data['result']['data'])
            else:
                return pd.DataFrame()
        except Exception as e:
            print(f"获取业绩数据失败：{e}", file=sys.stderr)
            return pd.DataFrame()
    
    # ========== 资金流向 ==========
    
    def get_money_flow(self, symbol: str) -> Dict:
        """获取资金流向"""
        if not symbol.startswith(('sh', 'sz', 'bj')):
            if symbol.startswith('6'):
                symbol = f'sh{symbol}'
            else:
                symbol = f'sz{symbol}'
        
        url = f"{self.BASE_URL}/api/qt/stock/fflow/daykline/get"
        params = {
            'lmt': '0',
            'klt': '1',
            'secid': symbol,
            '_': int(datetime.now().timestamp() * 1000)
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('data') and data['data'].get('klines'):
                klines = data['data']['klines']
                latest = klines[-1] if klines else None
                
                if latest:
                    parts = latest.split(',')
                    return {
                        '日期': parts[0],
                        '主力净流入': float(parts[7]),
                        '超大单净流入': float(parts[11]),
                        '大单净流入': float(parts[12]),
                        '中单净流入': float(parts[13]),
                        '小单净流入': float(parts[14]),
                        '主力净流入占比': float(parts[8]),
                        '超大单占比': float(parts[15]),
                        '大单占比': float(parts[16]),
                        '中单占比': float(parts[17]),
                        '小单占比': float(parts[18]),
                    }
            return {}
        except Exception as e:
            print(f"获取资金流向失败：{e}", file=sys.stderr)
            return {}
    
    # ========== 板块概念 ==========
    
    def get_concept_blocks(self, symbol: str) -> List[Dict]:
        """获取所属板块概念"""
        if not symbol.startswith(('sh', 'sz', 'bj')):
            if symbol.startswith('6'):
                symbol = f'sh{symbol}'
            else:
                symbol = f'sz{symbol}'
        
        url = f"{self.BASE_URL}/api/qt/stock/get"
        params = {
            'secid': symbol,
            'fields': 'f12,f13,f14,f15,f16,f17,f18,f19,f20,f21,f22,f23,f24,f25,f26,f27,f28,f29,f30,f31,f32,f33,f34,f35,f36,f37,f38,f39,f40,f41,f42,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90,f91,f92,f93,f94,f95,f96,f97,f98,f99,f100',
            '_': int(datetime.now().timestamp() * 1000)
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('data'):
                quote = data['data']
                blocks = []
                
                # 解析板块信息 (字段 f48-f57 是板块相关)
                for i in range(48, 58):
                    block_name = quote.get(f'f{i}', '')
                    if block_name:
                        blocks.append({'板块': block_name})
                
                return blocks
            return []
        except Exception as e:
            print(f"获取板块信息失败：{e}", file=sys.stderr)
            return []
    
    # ========== 龙虎榜 ==========
    
    def get_top_list(self, symbol: str, days: int = 5) -> pd.DataFrame:
        """获取龙虎榜数据"""
        if not symbol.startswith(('sh', 'sz', 'bj')):
            if symbol.startswith('6'):
                symbol = f'sh{symbol}'
            else:
                symbol = f'sz{symbol}'
        
        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            'reportName': 'RPT_DAILYBILLBOARD_DETAILSNEW',
            'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR,TRADE_DATE,EXPLAIN,CLOSE_PRICE,CHANGE_RATE,BILLBOARD_NET_AMT,BILLBOARD_BUY_AMT,BILLBOARD_SELL_AMT',
            'filter': f'(SECURITY_CODE="{symbol[2:]}")',
            'pageSize': str(days),
            'pageNumber': '1',
            'sortTypes': '-1',
            'sortColumns': 'TRADE_DATE'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('result') and data['result'].get('data'):
                return pd.DataFrame(data['result']['data'])
            else:
                return pd.DataFrame()
        except Exception as e:
            print(f"获取龙虎榜失败：{e}", file=sys.stderr)
            return pd.DataFrame()
    
    # ========== 公告研报 ==========
    
    def get_notices(self, symbol: str, count: int = 10) -> List[Dict]:
        """获取公司公告"""
        if not symbol.startswith(('sh', 'sz', 'bj')):
            if symbol.startswith('6'):
                symbol = f'sh{symbol}'
            else:
                symbol = f'sz{symbol}'
        
        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            'reportName': 'RPT_NINFO',
            'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR,PUB_DATE,TITLE,URL',
            'filter': f'(SECURITY_CODE="{symbol[2:]}")',
            'pageSize': str(count),
            'pageNumber': '1',
            'sortTypes': '-1',
            'sortColumns': 'PUB_DATE'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('result') and data['result'].get('data'):
                notices = []
                for item in data['result']['data']:
                    notices.append({
                        '代码': item.get('SECURITY_CODE'),
                        '名称': item.get('SECURITY_NAME_ABBR'),
                        '日期': item.get('PUB_DATE'),
                        '标题': item.get('TITLE'),
                        'URL': item.get('URL')
                    })
                return notices
            else:
                return []
        except Exception as e:
            print(f"获取公告失败：{e}", file=sys.stderr)
            return []
    
    def get_research_reports(self, symbol: str, count: int = 5) -> List[Dict]:
        """获取个股研报"""
        if not symbol.startswith(('sh', 'sz', 'bj')):
            if symbol.startswith('6'):
                symbol = f'sh{symbol}'
            else:
                symbol = f'sz{symbol}'
        
        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            'reportName': 'RPT_RES_INDIVIDUAL',
            'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR,ORG_NAME,RATING,RPT_DATE,TITLE',
            'filter': f'(SECURITY_CODE="{symbol[2:]}")',
            'pageSize': str(count),
            'pageNumber': '1',
            'sortTypes': '-1',
            'sortColumns': 'RPT_DATE'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('result') and data['result'].get('data'):
                reports = []
                for item in data['result']['data']:
                    reports.append({
                        '代码': item.get('SECURITY_CODE'),
                        '名称': item.get('SECURITY_NAME_ABBR'),
                        '机构': item.get('ORG_NAME'),
                        '评级': item.get('RATING'),
                        '日期': item.get('RPT_DATE'),
                        '标题': item.get('TITLE')
                    })
                return reports
            else:
                return []
        except Exception as e:
            print(f"获取研报失败：{e}", file=sys.stderr)
            return []


# ========== 便捷函数 ==========

def get_stock_data(symbol: str) -> Dict:
    """快速获取股票综合数据"""
    api = EastMoneyAPI()
    
    # 实时行情
    quote = api.get_realtime_quote(symbol)
    
    # K 线数据
    kline = api.get_kline_data(symbol, period='day', count=100)
    
    # 资金流向
    money_flow = api.get_money_flow(symbol)
    
    # 所属板块
    blocks = api.get_concept_blocks(symbol)
    
    # 最新公告
    notices = api.get_notices(symbol, count=5)
    
    # 机构研报
    reports = api.get_research_reports(symbol, count=3)
    
    return {
        'quote': quote,
        'kline': kline.to_dict('records') if not kline.empty else [],
        'money_flow': money_flow,
        'blocks': blocks,
        'notices': notices,
        'reports': reports,
        'timestamp': datetime.now().isoformat()
    }


if __name__ == "__main__":
    # 测试
    api = EastMoneyAPI()
    
    print("测试东方财富数据接口\n")
    
    # 测试实时行情
    print("【实时行情】")
    quote = api.get_realtime_quote("603739")
    print(json.dumps(quote, indent=2, ensure_ascii=False))
    
    # 测试 K 线数据
    print("\n【K 线数据】")
    kline = api.get_kline_data("603739", period='day', count=10)
    print(kline.to_string() if not kline.empty else "无数据")
    
    # 测试资金流向
    print("\n【资金流向】")
    flow = api.get_money_flow("603739")
    print(json.dumps(flow, indent=2, ensure_ascii=False))
    
    # 测试公告
    print("\n【最新公告】")
    notices = api.get_notices("603739", count=3)
    for notice in notices:
        print(f"  {notice.get('日期')} - {notice.get('标题')}")
