#!/usr/bin/env python3
"""
多数据源股票数据获取模块 v1.0

支持数据源:
1. AKShare - 开源财经数据接口 (Python 3.8+)
2. 新浪财经 - HTTP 实时行情
3. BaoStock - 证券宝历史数据
4. 腾讯财经 - 实时行情 (已有)
5. 百度股市通 - 资金流排行 (已有)
6. 东方财富 - 板块资金流 (已有)

用法:
    python3 data_sources.py --source akshare --top 20
    python3 data_sources.py --source sina --codes sh600000,sz000001
    python3 data_sources.py --source baostock --code 600000.SH --days 60
    python3 data_sources.py --source all --top 10
"""

import sys
import requests
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional


class MainstreamRank:
    """
    主流排名信息获取模块
    
    获取各主流财经平台的股票排名数据:
    - 主力净流入排名 (核心)
    - 成交额排名
    - 涨跌幅排名
    """
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://gushitong.baidu.com/',
        }
    
    def get_main_force_rank(self, top_n: int = 100) -> List[Dict]:
        """
        获取主力净流入排名 (核心功能)
        
        数据源优先级:
        1. 百度股市通 - 真实主力净流入数据
        2. 腾讯财经 - 按成交额估算主力
        
        Args:
            top_n: 获取数量
        
        Returns:
            list: 主力排名数据
        """
        print("[主力排名] 获取主力净流入排行...")
        
        # 优先使用百度股市通
        baidu_data = self._get_baidu_main_force_rank(top_n * 2)
        
        if baidu_data:
            print(f"[主力排名] 百度数据 {len(baidu_data)} 条")
            return baidu_data[:top_n]
        
        # 百度失败则使用腾讯成交额估算
        print("[主力排名] 百度失败，使用腾讯成交额排名...")
        return self._get_rank_by_amount(top_n)
    
    def _get_baidu_main_force_rank(self, count: int) -> List[Dict]:
        """
        从百度股市通获取主力净流入排名
        
        Args:
            count: 获取数量
        
        Returns:
            list: 主力排名数据
        """
        url = "https://gushitong.baidu.com/opendata"
        params = {
            'resource_id': '5350',
            'query': '沪深 A 股',
            'market': 'ab',
            'group': 'asyn_rank',
            'pn': '0',
            'rn': str(count),
            'pc_web': '1',
            'code': '110000',
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=15)
            data = resp.json()
            
            if data.get('ResultCode') == '0' and data.get('Result'):
                result = data['Result'][0]
                result_data = result.get('DisplayData', {}).get('resultData', {})
                
                rows = result_data.get('newTable', {}).get('data', [])
                if not rows:
                    rows = result_data.get('result', [])
                
                result_list = []
                for i, row in enumerate(rows, 1):
                    code = row.get('股票代码') or row.get('code', '')
                    symbol = f"sh{code}" if code.startswith('6') else f"sz{code}"
                    
                    result_list.append({
                        'rank': i,
                        'symbol': symbol,
                        'name': row.get('股票名称') or row.get('name', ''),
                        'price': float(row.get('最新价') or 0),
                        'change_pct': float(row.get('涨跌幅') or 0),
                        'main_net': float(row.get('主力净流入') or 0),
                        'amount': float(row.get('成交额') or 0) * 10000,  # 万转元
                        'volume': int(float(row.get('成交量') or 0)),
                        'main_force_rank': i,  # 主力排名
                        'main_force_score': max(0, 100 - i),  # 主力分数
                        'source': 'baidu_main_force',
                        'crawl_time': datetime.now().isoformat(),
                    })
                
                return result_list
            
            return []
            
        except Exception as e:
            print(f"[百度主力排名] 获取失败：{e}")
            return []
    
    def _get_rank_by_amount(self, top_n: int) -> List[Dict]:
        """
        按成交额获取排名 (备用方案)
        
        Args:
            top_n: 获取数量
        
        Returns:
            list: 排名数据
        """
        from local_crawler import StockCrawler
        
        crawler = StockCrawler(self.cache_dir)
        stocks = crawler.crawl_tencent()
        
        if stocks:
            # 按成交额排序
            stocks.sort(key=lambda x: x.get('amount', 0), reverse=True)
            
            result = []
            for i, s in enumerate(stocks[:top_n], 1):
                result.append({
                    'rank': i,
                    'symbol': s.get('symbol', ''),
                    'name': s.get('name', ''),
                    'price': s.get('price', 0),
                    'change_pct': s.get('change_pct', 0),
                    'amount': s.get('amount', 0),
                    'volume': s.get('volume', 0),
                    'main_force_rank': i,  # 使用成交额排名代替
                    'main_force_score': max(0, 100 - i),
                    'source': 'amount_rank',
                    'crawl_time': datetime.now().isoformat(),
                })
            
            print(f"[成交额排名] 获取 {len(result)} 只")
            return result
        
        return []
    
    def get_sector_rank(self, sector_type: str = 'industry', top_n: int = 50) -> List[Dict]:
        """
        获取行业/概念板块主力排名
        
        Args:
            sector_type: 'industry' (行业) 或 'concept' (概念)
            top_n: 获取数量
        
        Returns:
            list: 板块排名数据
        """
        print(f"[板块主力排名] 获取{sector_type}板块主力排名...")
        
        from local_crawler import StockCrawler
        
        crawler = StockCrawler(self.cache_dir)
        sectors = crawler.crawl_eastmoney_sector(sector_type)
        
        if sectors:
            sectors.sort(key=lambda x: x.get('main_net', 0), reverse=True)
            
            result = []
            for i, s in enumerate(sectors[:top_n], 1):
                result.append({
                    'rank': i,
                    'code': s.get('code', ''),
                    'name': s.get('name', ''),
                    'main_net': s.get('main_net', 0),
                    'change_pct': s.get('change_pct', 0),
                    'stock_count': s.get('stock_count', 0),
                    'main_force_rank': i,
                    'source': 'eastmoney_sector',
                    'crawl_time': datetime.now().isoformat(),
                })
            
            print(f"[板块主力排名] 获取 {len(result)} 个板块")
            return result
        
        return []


class SinaFinance:
    """新浪财经实时行情数据源"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.sina.com.cn/',
        }
    
    def get_realtime_quotes(self, codes: List[str]) -> List[Dict]:
        """
        获取实时行情
        
        Args:
            codes: 股票代码列表，如 ['sh600000', 'sz000001']
        
        Returns:
            list: 行情数据列表
        """
        if not codes:
            return []
        
        symbol_list = ','.join(codes)
        url = f"http://hq.sinajs.cn/list={symbol_list}"
        
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.encoding = 'gbk'
            
            results = []
            for line in resp.text.split('\n'):
                if not line.strip():
                    continue
                
                # 解析格式：var hq_str_sh600000="名称，当前价，昨收，今开，最高，最低，买一，卖一，成交量，成交额，..."
                match = line.split('="')
                if len(match) != 2:
                    continue
                
                symbol_part = match[0].replace('var hq_str_', '')
                data_part = match[1].strip('";')
                
                fields = data_part.split(',')
                if len(fields) < 10:
                    continue
                
                # 字段说明:
                # 0:名称 1:当前价 2:昨收 3:今开 4:最高 5:最低
                # 6:买一价 7:卖一价 8:成交量 (手) 9:成交额 (元)
                # 10:买一量 11:买二价 12:买二量 13:买三价 14:买三量
                # 15:买四价 16:买四量 17:买五价 18:买五量
                # 19:卖一量 20:卖二价 21:卖二量 22:卖三价 23:卖三量
                # 24:卖四价 25:卖四量 26:卖五价 27:卖五量
                # 30:日期 31:时间
                
                stock = {
                    'symbol': symbol_part,
                    'name': fields[0] if len(fields) > 0 else '',
                    'price': float(fields[1]) if fields[1] else 0,
                    'close': float(fields[2]) if fields[2] else 0,
                    'open': float(fields[3]) if fields[3] else 0,
                    'high': float(fields[4]) if fields[4] else 0,
                    'low': float(fields[5]) if fields[5] else 0,
                    'volume': int(float(fields[8])) if fields[8] else 0,
                    'amount': float(fields[9]) if fields[9] else 0,
                    'bid': float(fields[6]) if fields[6] else 0,
                    'ask': float(fields[7]) if fields[7] else 0,
                    'change_pct': ((float(fields[1]) - float(fields[2])) / float(fields[2]) * 100) if fields[1] and fields[2] else 0,
                    'date': fields[30] if len(fields) > 30 else '',
                    'time': fields[31] if len(fields) > 31 else '',
                    'source': 'sina',
                    'crawl_time': datetime.now().isoformat(),
                }
                results.append(stock)
            
            return results
            
        except Exception as e:
            print(f"[新浪财经] 获取失败：{e}")
            return []
    
    def get_top_gainers(self, top_n: int = 50) -> List[Dict]:
        """获取涨幅榜"""
        # 新浪财经涨幅榜 URL
        url = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
        params = {
            'page': 1,
            'num': top_n,
            'sort': 'changepercent',
            'asc': 0,
            'node': 'hs_a',
            '_s_r_a': 'page',
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=15)
            data = resp.json()
            
            results = []
            for item in data:
                stock = {
                    'symbol': item.get('symbol', ''),
                    'name': item.get('name', ''),
                    'price': float(item.get('price', 0)),
                    'change_pct': float(item.get('changepercent', 0)),
                    'volume': int(float(item.get('volume', 0))) if item.get('volume') else 0,
                    'amount': float(item.get('amount', 0)) if item.get('amount') else 0,
                    'source': 'sina_top',
                    'crawl_time': datetime.now().isoformat(),
                }
                results.append(stock)
            
            return results
            
        except Exception as e:
            print(f"[新浪财经] 涨幅榜获取失败：{e}")
            return []


class BaoStockData:
    """BaoStock 证券宝历史数据"""
    
    def __init__(self):
        self.bs = None
        self.logged_in = False
    
    def _login(self):
        """登录 BaoStock"""
        if self.logged_in:
            return True
        
        try:
            import baostock as bs
            self.bs = bs
            lg = bs.login()
            self.logged_in = (lg.error_code == '0')
            if self.logged_in:
                print("[BaoStock] 登录成功")
            else:
                print(f"[BaoStock] 登录失败：{lg.error_msg}")
            return self.logged_in
        except ImportError:
            print("[BaoStock] 未安装，请运行：pip install baostock")
            return False
        except Exception as e:
            print(f"[BaoStock] 登录异常：{e}")
            return False
    
    def get_history_kline(self, code: str, start_date: str = None, 
                          end_date: str = None, frequency: str = 'd') -> List[Dict]:
        """
        获取历史 K 线数据
        
        Args:
            code: 股票代码，如 '600000.SH'
            start_date: 开始日期 '2024-01-01'
            end_date: 结束日期 '2024-12-31'
            frequency: d (日), w (周), m (月), 5/15/30/60 (分钟)
        
        Returns:
            list: K 线数据列表
        """
        if not self._login():
            return []
        
        # 默认获取最近 60 天
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
        
        try:
            rs = self.bs.query_history_k_data_plus(
                code,
                "date,code,open,high,low,close,preclose,volume,amount,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag="3"  # 不复权
            )
            
            results = []
            while (rs.error_code == '0') and rs.next():
                row = rs.get_row_data()
                stock = {
                    'date': row[0],
                    'code': row[1],
                    'open': float(row[2]) if row[2] else 0,
                    'high': float(row[3]) if row[3] else 0,
                    'low': float(row[4]) if row[4] else 0,
                    'close': float(row[5]) if row[5] else 0,
                    'preclose': float(row[6]) if row[6] else 0,
                    'volume': float(row[7]) if row[7] else 0,
                    'amount': float(row[8]) if row[8] else 0,
                    'turn': float(row[9]) if row[9] else 0,
                    'pctChg': float(row[12]) if row[12] else 0,
                    'peTTM': float(row[13]) if row[13] else 0,
                    'pbMRQ': float(row[14]) if row[14] else 0,
                    'source': 'baostock',
                    'crawl_time': datetime.now().isoformat(),
                }
                results.append(stock)
            
            return results
            
        except Exception as e:
            print(f"[BaoStock] 获取 K 线失败：{e}")
            return []
    
    def get_stock_basic(self) -> List[Dict]:
        """获取股票基本信息"""
        if not self._login():
            return []
        
        try:
            rs = self.bs.query_all_stock(day=datetime.now().strftime('%Y-%m-%d'))
            
            results = []
            while (rs.error_code == '0') and rs.next():
                row = rs.get_row_data()
                results.append({
                    'code': row[0] if len(row) > 0 else '',
                    'name': row[1] if len(row) > 1 else '',
                    'source': 'baostock',
                })
            
            return results
            
        except Exception as e:
            print(f"[BaoStock] 获取股票列表失败：{e}")
            return []
    
    def logout(self):
        """登出 BaoStock"""
        if self.logged_in and self.bs:
            self.bs.logout()
            self.logged_in = False


class AKShareData:
    """AKShare 数据源 (需要 Python 3.8+)"""
    
    def __init__(self, python_path: str = 'python3.8'):
        self.python_path = python_path
        self.has_akshare = False
    
    def _check_akshare(self) -> bool:
        """检查 AKShare 是否可用"""
        try:
            import importlib.util
            spec = importlib.util.find_spec('akshare')
            self.has_akshare = spec is not None
            return self.has_akshare
        except:
            return False
    
    def get_fund_flow_rank(self, top_n: int = 50) -> List[Dict]:
        """
        获取资金流排行 (通过子进程调用 Python 3.8)
        
        Args:
            top_n: 获取数量
        
        Returns:
            list: 资金流数据
        """
        if not self._check_akshare():
            print("[AKShare] 未安装，跳过")
            return []
        
        # 使用子进程调用 Python 3.8 获取数据
        import subprocess
        
        script = f'''
import akshare as ak
import json
from datetime import datetime

try:
    data = ak.stock_individual_fund_flow_rank(indicator="今日")
    if data is not None and len(data) > 0:
        data = data.head({top_n})
        result = []
        for _, row in data.iterrows():
            result.append({{
                'name': row.get('名称', ''),
                'code': row.get('代码', ''),
                'price': float(row.get('最新价', 0)) if row.get('最新价') else 0,
                'change_pct': float(row.get('涨跌幅', 0)) if row.get('涨跌幅') else 0,
                'main_net': float(row.get('主力净流入', 0)) if row.get('主力净流入') else 0,
                'amount': float(row.get('成交额', 0)) if row.get('成交额') else 0,
                'volume': int(float(row.get('成交量', 0))) if row.get('成交量') else 0,
                'source': 'akshare',
                'crawl_time': datetime.now().isoformat(),
            }})
        print(json.dumps(result, ensure_ascii=False))
    else:
        print("[]")
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
'''
        
        try:
            result = subprocess.run(
                [self.python_path, '-c', script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout.strip())
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and 'error' in data:
                    print(f"[AKShare] 错误：{data['error']}")
                    return []
            
            return []
            
        except subprocess.TimeoutExpired:
            print("[AKShare] 请求超时")
            return []
        except Exception as e:
            print(f"[AKShare] 获取失败：{e}")
            return []
    
    def get_individual_flow(self, symbol: str, market: str = "沪") -> List[Dict]:
        """获取个股资金流详情"""
        if not self._check_akshare():
            return []
        
        import subprocess
        
        script = f'''
import akshare as ak
import json
from datetime import datetime

try:
    data = ak.stock_individual_fund_flow(symbol="{symbol}", market="{market}")
    if data is not None and len(data) > 0:
        result = []
        for _, row in data.iterrows():
            result.append({{
                'date': row.get('日期', ''),
                'main_net': float(row.get('主力净流入 - 净额', 0)) if row.get('主力净流入 - 净额') else 0,
                'super_net': float(row.get('特大单净流入 - 净额', 0)) if row.get('特大单净流入 - 净额') else 0,
                'big_net': float(row.get('大单净流入 - 净额', 0)) if row.get('大单净流入 - 净额') else 0,
                'mid_net': float(row.get('中单净流入 - 净额', 0)) if row.get('中单净流入 - 净额') else 0,
                'small_net': float(row.get('小单净流入 - 净额', 0)) if row.get('小单净流入 - 净额') else 0,
                'source': 'akshare',
                'crawl_time': datetime.now().isoformat(),
            }})
        print(json.dumps(result, ensure_ascii=False))
    else:
        print("[]")
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
'''
        
        try:
            result = subprocess.run(
                [self.python_path, '-c', script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout.strip())
                if isinstance(data, list):
                    return data
            
            return []
            
        except Exception as e:
            print(f"[AKShare] 获取失败：{e}")
            return []


class MultiDataSource:
    """多数据源统一接口"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        self.sina = SinaFinance()
        self.baostock = BaoStockData()
        self.akshare = AKShareData()
    
    def fetch(self, source: str, **kwargs) -> List[Dict]:
        """
        统一数据获取接口
        
        Args:
            source: 数据源名称 (sina, baostock, akshare, tencent, baidu, eastmoney)
            **kwargs: 参数
        
        Returns:
            list: 数据列表
        """
        if source == 'sina':
            codes = kwargs.get('codes', [])
            if codes:
                return self.sina.get_realtime_quotes(codes)
            else:
                return self.sina.get_top_gainers(kwargs.get('top_n', 50))
        
        elif source == 'baostock':
            code = kwargs.get('code', '600000.SH')
            start_date = kwargs.get('start_date')
            end_date = kwargs.get('end_date')
            frequency = kwargs.get('frequency', 'd')
            return self.baostock.get_history_kline(code, start_date, end_date, frequency)
        
        elif source == 'akshare':
            top_n = kwargs.get('top_n', 50)
            return self.akshare.get_fund_flow_rank(top_n)
        
        else:
            print(f"[未知数据源] {source}")
            return []
    
    def fetch_all(self, top_n: int = 10) -> Dict[str, List[Dict]]:
        """获取所有数据源的数据"""
        results = {}
        
        print("\n[多数据源] 开始获取数据...\n")
        
        # AKShare 资金流
        print("[1/3] AKShare 资金流排行...")
        results['akshare'] = self.fetch('akshare', top_n=top_n)
        print(f"  获取 {len(results['akshare'])} 条\n")
        
        # 新浪财经 涨幅榜
        print("[2/3] 新浪财经 涨幅榜...")
        results['sina'] = self.fetch('sina', top_n=top_n)
        print(f"  获取 {len(results['sina'])} 条\n")
        
        # BaoStock (示例股票)
        print("[3/3] BaoStock 历史数据 (浦发银行)...")
        results['baostock'] = self.fetch('baostock', code='600000.SH')
        print(f"  获取 {len(results['baostock'])} 条\n")
        
        return results
    
    def print_combined_ranking(self, results: Dict[str, List[Dict]], top_n: int = 10):
        """打印合并排行"""
        print("\n" + "="*100)
        print("📊 多数据源股票数据汇总")
        print("="*100)
        
        # AKShare 资金流
        if results.get('akshare'):
            print(f"\n{'='*100}")
            print(f"💰 AKShare 主力净流入排行 Top{min(top_n, len(results['akshare']))}")
            print(f"{'='*100}")
            print(f"{'排名':<4} {'代码':<10} {'名称':<10} {'主力净流入':<14} {'成交额':<12} {'股价':<8} {'涨跌':<8}")
            print(f"{'-'*100}")
            
            for i, s in enumerate(results['akshare'][:top_n], 1):
                net = s.get('main_net', 0)
                net_str = f"{net/100000000:.2f}亿" if abs(net) >= 100000000 else f"{net/10000:.0f}万"
                amount = s.get('amount', 0)
                amount_str = f"{amount/100000000:.2f}亿" if amount >= 100000000 else f"{amount/10000:.0f}万"
                
                change_sign = '+' if s.get('change_pct', 0) >= 0 else ''
                
                print(f"{i:<4} {s.get('code', ''):<10} {s.get('name', ''):<10} "
                      f"💰{net_str:>10} {amount_str:>10} ¥{s.get('price', 0):>5.2f} {change_sign}{s.get('change_pct', 0):>5.2f}%")
        
        # 新浪财经 涨幅榜
        if results.get('sina'):
            print(f"\n{'='*100}")
            print(f"📈 新浪财经 涨幅榜 Top{min(top_n, len(results['sina']))}")
            print(f"{'='*100}")
            print(f"{'排名':<4} {'代码':<10} {'名称':<10} {'股价':<8} {'涨跌幅':<10} {'成交量':<12}")
            print(f"{'-'*100}")
            
            for i, s in enumerate(results['sina'][:top_n], 1):
                change_sign = '+' if s.get('change_pct', 0) >= 0 else ''
                vol_str = f"{s.get('volume', 0)/10000:.0f}万手" if s.get('volume', 0) >= 10000 else f"{s.get('volume', 0):.0f}手"
                
                print(f"{i:<4} {s.get('symbol', ''):<10} {s.get('name', ''):<10} "
                      f"¥{s.get('price', 0):>5.2f} {change_sign}{s.get('change_pct', 0):>7.2f}% {vol_str:>10}")
        
        # BaoStock 历史数据
        if results.get('baostock'):
            print(f"\n{'='*100}")
            print(f"📉 BaoStock 历史 K 线 (最新 10 条)")
            print(f"{'='*100}")
            print(f"{'日期':<12} {'代码':<12} {'开盘':>8} {'最高':>8} {'最低':>8} {'收盘':>8} {'涨跌幅':<8}")
            print(f"{'-'*100}")
            
            for k in results['baostock'][-10:]:
                change_sign = '+' if k.get('pctChg', 0) >= 0 else ''
                print(f"{k.get('date', ''):<12} {k.get('code', ''):<12} "
                      f"{k.get('open', 0):>7.2f} {k.get('high', 0):>7.2f} "
                      f"{k.get('low', 0):>7.2f} {k.get('close', 0):>7.2f} "
                      f"{change_sign}{k.get('pctChg', 0):>5.2f}%")
        
        print(f"\n{'='*100}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='多数据源股票数据获取')
    parser.add_argument('--source', choices=['sina', 'baostock', 'akshare', 'all'], 
                       default='all', help='数据源')
    parser.add_argument('--top', type=int, default=10, help='前 N 条')
    parser.add_argument('--codes', type=str, help='股票代码列表 (逗号分隔)')
    parser.add_argument('--code', type=str, help='股票代码 (BaoStock)')
    parser.add_argument('--days', type=int, default=60, help='获取天数 (BaoStock)')
    
    args = parser.parse_args()
    
    fetcher = MultiDataSource()
    
    if args.source == 'all':
        results = fetcher.fetch_all(top_n=args.top)
        fetcher.print_combined_ranking(results, top_n=args.top)
        
        # 保存结果
        cache_file = fetcher.cache_dir / f"multi_source_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            # 转换 datetime 为字符串
            import json
            def convert(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return obj
            
            json.dump(results, f, ensure_ascii=False, indent=2, default=convert)
        print(f"\n✅ 结果已保存：{cache_file}")
        
    elif args.source == 'sina':
        if args.codes:
            codes = [c.strip() for c in args.codes.split(',')]
            data = fetcher.fetch('sina', codes=codes)
        else:
            data = fetcher.fetch('sina', top_n=args.top)
        
        print(f"\n[新浪财经] 获取 {len(data)} 条数据")
        for s in data[:args.top]:
            print(f"  {s.get('symbol', s.get('code', ''))} {s.get('name', '')} "
                  f"¥{s.get('price', 0):.2f} {s.get('change_pct', 0):+.2f}%")
    
    elif args.source == 'baostock':
        code = args.code or '600000.SH'
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
        
        data = fetcher.fetch('baostock', code=code, start_date=start_date, end_date=end_date)
        
        print(f"\n[BaoStock] 获取 {code} 近{args.days}天数据，共 {len(data)} 条")
        if data:
            print(f"  最新：{data[-1]['date']} 收盘¥{data[-1]['close']:.2f} ({data[-1]['pctChg']:+.2f}%)")
    
    elif args.source == 'akshare':
        data = fetcher.fetch('akshare', top_n=args.top)
        
        print(f"\n[AKShare] 获取 {len(data)} 条资金流数据")
        for i, s in enumerate(data[:args.top], 1):
            net = s.get('main_net', 0)
            net_str = f"{net/100000000:.2f}亿" if abs(net) >= 100000000 else f"{net/10000:.0f}万"
            print(f"  {i}. {s.get('name', '')} ({s.get('code', '')}) 主力净流入{net_str}")
    
    # 清理
    fetcher.baostock.logout()


if __name__ == '__main__':
    main()
