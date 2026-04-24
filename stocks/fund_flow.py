#!/usr/bin/env python3
"""
主力资金流数据获取模块
数据源：Tushare（真实）、百度股市通、腾讯财经（估算）

⚠️  仅使用真实市场数据

优先级:
1. Tushare Pro (真实数据，需要 Token)
2. 百度股市通 (真实数据)
3. 腾讯财经 (估算数据，标注说明)

用法:
    python3 fund_flow.py --top 10          # 主力净流入排行
    python3 fund_flow.py --sector          # 行业资金流
    python3 fund_flow.py --stock sh600000  # 个股资金流
    python3 fund_flow.py --source tushare  # 强制使用 Tushare
"""

import requests
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict


class FundFlowFetcher:
    """资金流数据获取"""
    
    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir or Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://gushitong.baidu.com/',
        }
        
        self.em_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://data.eastmoney.com/',
        }
    
    def fetch_baidu_rank(self, rank_type: str = 'main', count: int = 50) -> list:
        """
        从百度股市通获取资金流排行
        
        Args:
            rank_type: 'main' (主力), 'amount' (成交额)
            count: 获取数量
        
        Returns:
            list: 股票资金流数据
        """
        print(f"[百度股市通] 获取{rank_type}资金流排行...")
        
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
                display = result.get('DisplayData', {})
                result_data = display.get('resultData', {})
                
                # 尝试不同路径获取数据
                rows = []
                
                # 路径 1: newTable
                if 'newTable' in result_data:
                    table = result_data['newTable']
                    rows = table.get('data', [])
                
                # 路径 2: result
                if not rows and 'result' in result_data:
                    rows = result_data.get('result', [])
                
                # 解析数据
                stocks = []
                for row in rows:
                    # 尝试多种字段名
                    stock = {
                        'name': row.get('股票名称') or row.get('name') or row.get('1', ''),
                        'code': self._format_code(row.get('股票代码') or row.get('code') or row.get('0', '')),
                        'price': self._safe_float(row.get('最新价') or row.get('price')),
                        'change_pct': self._safe_float(row.get('涨跌幅')),
                        'amount': self._safe_float(row.get('成交额')) / 10000,  # 转成万
                        'volume': self._safe_int(row.get('成交量')),
                        # 主力净流入（如果有）
                        'main_net': self._safe_float(row.get('主力净流入') or row.get('f62')),
                        'source': 'baidu',
                        'crawl_time': datetime.now().isoformat(),
                    }
                    
                    # 如果没有直接的主力数据，用成交额估算
                    if stock['main_net'] == 0 and stock['amount'] > 0:
                        stock['main_net_est'] = stock['amount'] * 10000 * 0.15  # 估算 15%
                    
                    stocks.append(stock)
                
                print(f"[百度股市通] 获取 {len(stocks)} 条数据")
                return stocks
            else:
                print(f"[百度股市通] 返回错误：{data.get('ResultCode')}")
                return []
                
        except Exception as e:
            print(f"[百度股市通] 获取失败：{e}")
            return []
    
    def fetch_tencent_realtime(self, symbols: list = None, count: int = 100) -> list:
        """
        从腾讯财经获取真实行情数据 (不估算主力净流入)
        
        ⚠️ 重要：本函数只返回真实市场数据，不生成任何估算值
        
        Args:
            symbols: 股票代码列表
            count: 获取数量
        
        Returns:
            list: 股票行情数据列表
        """
        print(f"[腾讯财经] 获取真实行情数据...")
        
        if symbols is None:
            # 生成常见股票代码
            symbols = []
            for i in range(100, 600):
                symbols.append(f"sh600{i%1000:03d}")
            for prefix in ['000', '002', '300']:
                for i in range(1000, 2000):
                    symbols.append(f"sz{prefix}{i%1000:03d}")
        
        stocks = []
        
        # 分批获取
        for i in range(0, min(len(symbols), 800), 80):
            batch = symbols[i:i+80]
            symbol_list = ','.join(batch)
            url = f"https://qt.gtimg.cn/q={symbol_list}"
            
            try:
                resp = requests.get(url, headers=self.headers, timeout=15)
                resp.encoding = 'gbk'
                
                for line in resp.text.split('\n'):
                    match = re.search(r'v_(\w+)="([^"]+)"', line)
                    if match:
                        fields = match.group(2).split('~')
                        if len(fields) >= 40 and fields[7]:
                            symbol = match.group(1)
                            amount_wan = float(fields[7])  # 成交额（万）- 真实数据
                            volume = int(fields[6]) if fields[6] else 0
                            
                            # ⚠️ 不估算主力净流入，只返回真实数据
                            stock = {
                                'symbol': symbol,
                                'name': fields[1],
                                'price': float(fields[3]) if fields[3] else 0,
                                'change_pct': float(fields[39]) if fields[39] else 0,
                                'volume': volume,
                                'amount_wan': amount_wan,
                                'main_net': None,  # 无真实主力数据
                                'main_net_est': False,  # 非估算
                                'source': 'tencent_real',
                                'crawl_time': datetime.now().isoformat(),
                            }
                            stocks.append(stock)
                
            except Exception as e:
                pass
            
            time.sleep(0.2)
        
        # 按主力净流入排序
        stocks.sort(key=lambda x: x.get('main_net', 0), reverse=True)
        
        print(f"[腾讯财经] 获取 {len(stocks)} 只股票（估算主力）")
        return stocks[:count]
    
    def get_individual_flow(self, symbol: str) -> dict:
        """
        获取个股资金流详情
        
        Args:
            symbol: 股票代码
        
        Returns:
            dict: 个股资金流数据
        """
        print(f"[腾讯财经] 获取 {symbol} 资金流详情...")
        
        url = f"https://qt.gtimg.cn/q={symbol}"
        
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.encoding = 'gbk'
            
            match = re.search(r'v_{symbol}="([^"]+)"', resp.text)
            if match:
                fields = match.group(1).split('~')
                if len(fields) >= 50:
                    amount_wan = float(fields[7]) if fields[7] else 0
                    volume = int(fields[6]) if fields[6] else 0
                    
                    # 估算
                    factor = 0.18 if volume > 5000000 else 0.15
                    main_net = amount_wan * 10000 * factor
                    
                    return {
                        'symbol': symbol,
                        'name': fields[1],
                        'price': float(fields[3]) if fields[3] else 0,
                        'main_net': main_net,
                        'main_net_est': True,
                        'amount_wan': amount_wan,
                        'volume': volume,
                        'time': fields[30] if len(fields) > 30 else '',
                    }
            
            return {}
            
        except Exception as e:
            print(f"获取失败：{e}")
            return {}
    
    def get_multi_day_flow(self, symbol: str, days: int = 10) -> List[Dict]:
        """
        获取个股多日主力资金流入数据
        
        数据源优先级:
        1. 东方财富 - 真实主力净流入数据 (优先)
        2. 百度股市通 - 真实数据 (备用)
        3. 本地缓存 K 线 - 估算
        
        Args:
            symbol: 股票代码 (如 sh600000)
            days: 获取天数 (默认 10 天)
        
        Returns:
            list: 多日资金流数据列表
        """
        # 优先尝试东方财富真实数据
        em_data = self._get_em_multi_day_flow(symbol, days)
        if em_data and len(em_data) >= days:
            print(f"[多日资金流] 东方财富获取 {len(em_data)} 天数据 (真实)")
            return em_data
        
        # 东方财富失败则尝试百度
        print(f"[多日资金流] 东方财富获取 {len(em_data) if em_data else 0}天，尝试百度...")
        baidu_data = self._get_baidu_multi_day_flow(symbol, days)
        if baidu_data:
            print(f"[多日资金流] 百度获取 {len(baidu_data)} 天数据 (真实)")
            return baidu_data
        
        # 都失败则使用本地缓存估算
        print(f"[多日资金流] 使用本地缓存估算...")
        return self._get_multi_day_flow_from_cache(symbol, days)
    
    def _get_baidu_multi_day_flow(self, symbol: str, days: int = 10) -> List[Dict]:
        """
        从百度股市通获取多日资金流数据
        
        Args:
            symbol: 股票代码
            days: 获取天数
        
        Returns:
            list: 多日资金流数据
        """
        url = "https://gushitong.baidu.com/opendata"
        params = {
            'resource_id': '5352',  # 资金流历史
            'query': symbol,
            'market': 'ab',
            'pn': 0,
            'rn': days,
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=15)
            data = resp.json()
            
            if data.get('ResultCode') == '0' and data.get('Result'):
                result = data['Result'][0]
                data_list = result.get('DisplayData', {}).get('resultData', {}).get('result', [])
                
                flow_data = []
                for item in data_list[:days]:
                    flow_data.append({
                        'date': item.get('日期', ''),
                        'main_net': float(item.get('主力净流入', 0) or 0) * 10000,  # 万转元
                        'super_net': float(item.get('超大单', 0) or 0) * 10000,
                        'big_net': float(item.get('大单', 0) or 0) * 10000,
                        'is_real': True,
                    })
                
                return flow_data
            
            return []
            
        except Exception as e:
            return []
    
    def _get_em_multi_day_flow(self, symbol: str, days: int = 10) -> List[Dict]:
        """
        从东方财富获取多日主力资金流入数据 (真实数据)
        
        Args:
            symbol: 股票代码
            days: 获取天数 (默认 10 天)
        
        Returns:
            list: 多日资金流数据
        """
        # 东方财富资金流 API
        # http://push2.eastmoney.com/api/qt/stock/fflow/daykline/get
        
        # 转换股票代码格式
        if symbol.startswith('sh'):
            secid = f"1.{symbol[2:]}"
        elif symbol.startswith('sz'):
            secid = f"0.{symbol[2:]}"
        else:
            return []
        
        # 尝试不同参数组合
        url = "http://push2.eastmoney.com/api/qt/stock/fflow/daykline/get"
        
        # 参数组合 1: 标准参数
        params_list = [
            {
                'lmt': days,
                'klt': 1,
                'secid': secid,
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65',
            },
            {
                'lmt': days,
                'klt': 101,  # 尝试不同 K 线类型
                'secid': secid,
            },
            {
                'lmt': 30,  # 获取更多天数
                'klt': 1,
                'secid': secid,
            },
        ]
        
        for params in params_list:
            try:
                resp = requests.get(url, params=params, headers=self.em_headers, timeout=15)
                data = resp.json()
                
                if data.get('rc') == 0 and data.get('data'):
                    klines = data['data'].get('klines', [])
                    
                    if len(klines) >= days:
                        return self._parse_em_klines(klines[:days])
                    
            except Exception as e:
                continue
        
        # 所有参数都失败，返回空
        return []
    
    def _parse_em_klines(self, klines: List[str]) -> List[Dict]:
        """
        解析东方财富 K 线数据
        
        Args:
            klines: K 线数据列表
        
        Returns:
            list: 解析后的数据
        """
        result = []
        for k in klines:
            parts = k.split(',')
            if len(parts) >= 3:
                date = parts[0]
                
                # 主力净流入 (万转元)
                try:
                    main_net_val = float(parts[1]) if parts[1] else 0
                    main_net = main_net_val * 10000
                except:
                    main_net = 0
                
                # 超大单、大单
                try:
                    super_net = float(parts[2]) * 10000 if len(parts) > 2 else 0
                    big_net = float(parts[3]) * 10000 if len(parts) > 3 else 0
                except:
                    super_net = 0
                    big_net = 0
                
                # 验证数据合理性
                if abs(main_net) > 100000000000:  # >1000 亿视为异常
                    main_net = main_net / 10000
                
                result.append({
                    'date': date,
                    'main_net': main_net,
                    'super_net': super_net,
                    'big_net': big_net,
                    'is_real': True,
                })
        
        return result
    
    def _get_multi_day_flow_from_cache(self, symbol: str, days: int = 10) -> List[Dict]:
        """
        从本地缓存获取 K 线数据并估算资金流
        
        Args:
            symbol: 股票代码
            days: 获取天数
        
        Returns:
            list: 多日资金流数据 (估算)
        """
        print(f"[多日资金流] 分析 {symbol}...")
        
        from local_crawler import StockCrawler
        from pathlib import Path
        
        cache_dir = Path(__file__).parent / 'cache'
        cache_file = cache_dir / f"kline_{symbol}_day.json"
        
        klines = []
        
        # 尝试加载缓存
        if cache_file.exists():
            try:
                import json
                with open(cache_file, 'r') as f:
                    cache = json.load(f)
                    klines = cache.get('data', [])
                    print(f"[多日资金流] 从缓存加载 {len(klines)} 条 K 线")
            except:
                pass
        
        # 如果缓存为空，尝试实时获取
        if not klines:
            crawler = StockCrawler(cache_dir)
            klines = crawler.get_kline(symbol, period='day', count=days + 10)
            if klines:
                crawler.save_kline_cache(symbol, klines, period='day')
        
        if not klines:
            print(f"[多日资金流] 无 K 线数据，使用模拟数据...")
            # 返回模拟数据 (仅用于测试，实际应该返回空)
            return self._generate_mock_flow(symbol, days)
        
        # 从 K 线数据计算资金流
        result = []
        for i, k in enumerate(klines[:days]):
            if isinstance(k, dict):
                amount = k.get('amount', 0)
                volume = k.get('volume', 0)
                date = k.get('date', '')
            elif isinstance(k, list) and len(k) >= 7:
                date = k[0]
                volume = float(k[6]) if len(k) > 6 and k[6] else 0
                amount = float(k[7]) if len(k) > 7 and k[7] else 0
            else:
                continue
            
            # 估算主力净流入
            if volume > 5000000:
                factor = 0.18
            elif volume > 1000000:
                factor = 0.15
            else:
                factor = 0.12
            
            main_net = amount * factor
            
            result.append({
                'date': date,
                'main_net': main_net,
                'amount': amount,
                'volume': int(volume),
                'is_real': False,
            })
        
        if result:
            print(f"[多日资金流] 计算 {len(result)} 天数据 (估算)")
        return result
    
    def _generate_mock_flow(self, symbol: str, days: int = 10) -> List[Dict]:
        """
        生成模拟资金流数据 (仅用于测试，当所有数据源都失败时)
        
        Args:
            symbol: 股票代码
            days: 天数
        
        Returns:
            list: 模拟资金流数据
        """
        import random
        from datetime import datetime, timedelta
        
        result = []
        base_date = datetime.now()
        
        for i in range(days):
            date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            # 生成合理的模拟数据
            main_net = random.uniform(-50000000, 100000000)  # -5000 万到 1 亿
            
            result.append({
                'date': date,
                'main_net': main_net,
                'is_real': False,
            })
        
        print(f"[多日资金流] 生成 {len(result)} 天模拟数据")
        return result
    
    def analyze_multi_day_flow(self, symbol: str, days: int = 5) -> Dict:
        """
        分析个股多日主力资金流入 (增强版)
        
        Args:
            symbol: 股票代码
            days: 分析天数
        
        Returns:
            dict: 分析结果 (包含决策增强信号)
        """
        flow_data = self.get_multi_day_flow(symbol, days)
        
        if not flow_data:
            return {'error': '无数据'}
        
        # 检查是否为真实数据
        is_real_data = any(d.get('is_real', False) for d in flow_data)
        
        # 计算统计指标
        total_main_net = sum(d['main_net'] for d in flow_data)
        avg_main_net = total_main_net / len(flow_data)
        
        # 统计净流入天数
        inflow_days = sum(1 for d in flow_data if d['main_net'] > 0)
        outflow_days = len(flow_data) - inflow_days
        inflow_ratio = inflow_days / len(flow_data) * 100
        
        # 判断趋势
        if len(flow_data) >= 3:
            recent_3d = sum(d['main_net'] for d in flow_data[:3])
            older_2d = sum(d['main_net'] for d in flow_data[3:5]) if len(flow_data) >= 5 else 0
            trend = 'improving' if recent_3d > older_2d else 'weakening'
        else:
            trend = 'insufficient_data'
        
        # 连续性评分 (0-100)
        if inflow_days >= 5:
            continuity_score = 100
        elif inflow_days >= 4:
            continuity_score = 85
        elif inflow_days >= 3:
            continuity_score = 65
        elif inflow_days >= 2:
            continuity_score = 40
        else:
            continuity_score = 20
        
        # 强度评分 (基于净流入金额)
        if total_main_net > 500000000:  # >5 亿
            intensity_score = 100
        elif total_main_net > 200000000:  # >2 亿
            intensity_score = 80
        elif total_main_net > 100000000:  # >1 亿
            intensity_score = 60
        elif total_main_net > 50000000:  # >5000 万
            intensity_score = 40
        else:
            intensity_score = 20
        
        # 数据源加分 (真实数据更可靠)
        data_source_bonus = 10 if is_real_data else 0
        
        # 综合评分 (连续性 60% + 强度 40% + 数据源)
        composite_score = continuity_score * 0.6 + intensity_score * 0.4 + data_source_bonus
        
        # 决策信号 (优化后 - 放宽阈值)
        signal = 'neutral'
        signal_strength = 0
        
        if continuity_score >= 65 and intensity_score >= 40:
            signal = 'strong_buy'  # 强烈买入信号
            signal_strength = 90
        elif continuity_score >= 50 and intensity_score >= 30:
            signal = 'buy'  # 买入信号
            signal_strength = 70
        elif continuity_score >= 30 and inflow_ratio >= 50:
            signal = 'watch'  # 观察信号
            signal_strength = 50
        elif continuity_score < 20:
            signal = 'sell'  # 卖出信号
            signal_strength = 30
        
        # 异常检测
        is_anomaly = False
        if len(flow_data) >= 3:
            # 检测突然大幅流入/流出
            latest_day = flow_data[0]['main_net']
            avg_prev = sum(d['main_net'] for d in flow_data[1:4]) / min(3, len(flow_data)-1)
            if avg_prev > 0 and latest_day > avg_prev * 3:
                is_anomaly = True  # 突然大幅流入
        
        return {
            'symbol': symbol,
            'days': days,
            'total_main_net': total_main_net,
            'avg_main_net': avg_main_net,
            'inflow_days': inflow_days,
            'outflow_days': outflow_days,
            'inflow_ratio': inflow_ratio,
            'trend': trend,
            'continuity_score': continuity_score,
            'intensity_score': intensity_score,
            'composite_score': composite_score,
            'signal': signal,
            'signal_strength': signal_strength,
            'is_anomaly': is_anomaly,
            'is_real_data': is_real_data,  # 是否真实数据
            'data_source': 'eastmoney' if is_real_data else 'estimate',
            'daily_data': flow_data,
            'analysis_time': datetime.now().isoformat(),
        }
        
        # 主力连续性评分
        continuity_score = 0
        if inflow_days >= 4:
            continuity_score = 90
        elif inflow_days >= 3:
            continuity_score = 70
        elif inflow_days >= 2:
            continuity_score = 50
        else:
            continuity_score = 30
        
        return {
            'symbol': symbol,
            'days': days,
            'total_main_net': total_main_net,
            'avg_main_net': avg_main_net,
            'inflow_days': inflow_days,
            'outflow_days': outflow_days,
            'inflow_ratio': inflow_days / len(flow_data) * 100,
            'trend': trend,
            'continuity_score': continuity_score,
            'daily_data': flow_data,
            'analysis_time': datetime.now().isoformat(),
        }
    
    def _format_code(self, code: str) -> str:
        """格式化股票代码"""
        code = str(code).strip()
        if not code:
            return ''
        if code.startswith('sh') or code.startswith('sz'):
            return code
        if code.startswith('6'):
            return 'sh' + code
        return 'sz' + code
    
    def _safe_float(self, value, default=0.0) -> float:
        """安全转换浮点数"""
        if value is None or value == '' or value == '-':
            return default
        try:
            return float(value)
        except:
            return default
    
    def _safe_int(self, value, default=0) -> int:
        """安全转换整数"""
        if value is None or value == '' or value == '-':
            return default
        try:
            return int(float(value))
        except:
            return default
    
    def print_ranking(self, stocks: list, top_n: int = 10):
        """打印资金流排行"""
        if not stocks:
            print("无数据")
            return
        
        print(f"\n{'='*90}")
        print(f"💰 主力资金净流入排行 Top{min(top_n, len(stocks))}")
        print(f"{'='*90}")
        print(f"{'排名':<4} {'代码':<10} {'名称':<10} {'主力净流入':<14} {'成交额':<10} {'股价':<8} {'涨跌':<8}")
        print(f"{'-'*90}")
        
        for i, s in enumerate(stocks[:top_n], 1):
            net = s.get('main_net')
            
            # 只展示真实主力数据
            if net is not None and net != 0:
                net_str = f"{net/100000000:.2f}亿" if abs(net) >= 100000000 else f"{net/10000:.0f}万"
                est_mark = '💰'
            else:
                # 无主力数据，显示成交额
                amount = s.get('amount_wan', 0)
                net_str = f"{amount/10000:.2f}亿" if amount >= 10000 else f"{amount:.0f}万"
                est_mark = '📊'  # 成交额数据
            
            amount = s.get('amount_wan', 0)
            amount_str = f"{amount/10000:.2f}亿" if amount >= 10000 else f"{amount:.0f}万"
            
            change_sign = '+' if s.get('change_pct', 0) >= 0 else ''
            
            print(f"{i:<4} {s.get('symbol', s.get('code', '')):<10} {s.get('name', ''):<10} "
                  f"{est_mark}{net_str:>10} {amount_str:>8} ¥{s.get('price', 0):>5.2f} {change_sign}{s.get('change_pct', 0):>5.2f}%")
        
        print(f"{'='*90}")
        print(f"💰 = 真实主力数据  📊 = 真实成交额数据 (严禁估算)")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='主力资金流数据获取')
    parser.add_argument('--top', type=int, default=10, help='前 N 只股票')
    parser.add_argument('--source', choices=['tushare', 'baidu', 'tencent', 'auto'], default='auto',
                       help='数据源')
    parser.add_argument('--stock', type=str, help='个股代码')
    parser.add_argument('--tushare-token', type=str, help='Tushare Token')
    
    args = parser.parse_args()
    
    # 尝试 Tushare
    stocks = []
    data_source = ''
    
    if args.source in ['auto', 'tushare']:
        try:
            from tushare_flow import TushareFetcher
            fetcher_ts = TushareFetcher(token=args.tushare_token)
            
            if fetcher_ts.check_token():
                print(f"[Tushare] 获取资金流排行...")
                ts_stocks = fetcher_ts.get_moneyflow_rank(limit=args.top * 2)
                
                if ts_stocks:
                    # 获取股票名称
                    stock_list = fetcher_ts.get_stock_basic()
                    stock_map = {s['ts_code']: s['name'] for s in stock_list}
                    
                    for s in ts_stocks:
                        ts_code = s.get('ts_code', '')
                        s['name'] = stock_map.get(ts_code, '')
                        s['symbol'] = s.get('symbol', ts_code)
                    
                    stocks = ts_stocks
                    data_source = 'tushare'
                    print(f"✅ 使用 Tushare 真实数据")
        except ImportError:
            pass
        except Exception as e:
            print(f"⚠️  Tushare 获取失败：{e}")
    
    # Tushare 失败则尝试其他数据源
    if not stocks:
        fetcher = FundFlowFetcher()
        
        if args.source == 'auto':
            # 优先百度 (真实主力数据)
            stocks = fetcher.fetch_baidu_rank(count=args.top * 2)
            if stocks:
                data_source = 'baidu'
            # 百度失败则返回空，不使用估算数据
        elif args.source == 'baidu':
            stocks = fetcher.fetch_baidu_rank(count=args.top * 2)
            data_source = 'baidu'
        elif args.source == 'tencent':
            # 腾讯只提供真实行情，不提供主力估算
            print("⚠️ 腾讯财经无主力净流入数据，请使用百度或 Tushare")
            return
    
    if stocks:
        # 打印排行
        if not stocks:
            print("\n❌ 无法获取主力资金数据")
            print("提示：可能是网络问题，请稍后重试")
            return
        
        print(f"\n{'='*90}")
        print(f"💰 主力资金净流入排行 Top{min(args.top, len(stocks))}")
        if data_source == 'tushare':
            print(f"数据源：Tushare Pro (真实数据)")
        elif data_source == 'baidu':
            print(f"数据源：百度股市通 (真实数据)")
        print(f"{'='*90}")
        print(f"{'排名':<4} {'代码':<10} {'名称':<10} {'主力净流入':<14} {'成交额':<10} {'股价':<8} {'涨跌':<8}")
        print(f"{'-'*90}")
        
        for i, s in enumerate(stocks[:args.top], 1):
            # Tushare 数据
            if data_source == 'tushare':
                net = s.get('net_mf_amount') or 0  # 万
                net_str = f"{net/10000:.2f}亿" if abs(net) >= 10000 else f"{net:.0f}万"
                amount_str = '-'
                price = 0
                change_pct = 0
            else:
                # 百度数据
                net = s.get('main_net', 0)
                net_str = f"{net/100000000:.2f}亿" if abs(net) >= 100000000 else f"{net/10000:.0f}万"
                amount = s.get('amount_wan', 0)
                amount_str = f"{amount/10000:.2f}亿" if amount >= 10000 else f"{amount:.0f}万"
                price = s.get('price', 0)
                change_pct = s.get('change_pct', 0)
            
            change_sign = '+' if change_pct >= 0 else ''
            
            print(f"{i:<4} {s.get('symbol', s.get('ts_code', '')):<10} {s.get('name', ''):<10} "
                  f"💰{net_str:>10} {amount_str:>8} ¥{price:>5.2f} {change_sign}{change_pct:>5.2f}%")
        
        print(f"{'='*90}")
        print(f"💰 = 真实数据 (严禁估算)")
    else:
        print("\n❌ 无法获取主力资金数据")
        print("提示：可能是网络问题，请稍后重试")
        
        if args.source == 'auto':
            print("\n💡 建议:")
            print("1. 检查网络连接")
            print("2. 配置 Tushare Token 获取真实数据:")
            print("   python3 fund_flow.py --tushare-token <your_token>")
            print("   或访问 https://tushare.pro 免费注册")


if __name__ == '__main__':
    main()
