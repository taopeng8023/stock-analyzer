#!/usr/bin/env python3
"""
选股模块核心逻辑 v2.0 - 优化版

优化内容:
1. 统一数据源管理 - 支持热插拔
2. 多因子评分系统 - 可配置权重
3. 数据质量验证 - 自动过滤异常
4. 智能缓存策略 - 增量更新
5. 并行数据获取 - 性能提升
6. 配置化管理 - YAML 配置

用法:
    python3 stock_selector.py --strategy main      # 主力策略
    python3 stock_selector.py --strategy multi     # 多因子策略
    python3 stock_selector.py --strategy custom    # 自定义策略
    python3 stock_selector.py --config config.yaml # 使用配置文件
"""

import sys
import json
import time
import requests
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))


# ============ 数据类 ============

@dataclass
class StockData:
    """股票数据结构"""
    symbol: str = ""
    name: str = ""
    price: float = 0.0
    change_pct: float = 0.0
    volume: int = 0  # 手
    amount: float = 0.0  # 元
    turnover_rate: float = 0.0  # 换手率%
    pe_ratio: float = 0.0  # 市盈率
    pb_ratio: float = 0.0  # 市净率
    
    # 资金流
    main_net: float = 0.0  # 主力净流入 (元)
    super_net: float = 0.0  # 超大单 (元)
    big_net: float = 0.0  # 大单 (元)
    
    # 技术指标
    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    ma60: float = 0.0
    
    # 评分
    score: float = 0.0
    rank: int = 0
    
    # 元数据
    source: str = ""
    crawl_time: str = ""
    data_quality: float = 1.0  # 数据质量 0-1
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FactorConfig:
    """因子配置"""
    # 因子权重
    amount_weight: float = 0.25  # 成交额
    change_weight: float = 0.20  # 涨跌幅
    volume_weight: float = 0.15  # 成交量
    main_flow_weight: float = 0.25  # 主力流入
    turnover_weight: float = 0.10  # 换手率
    technical_weight: float = 0.05  # 技术面
    
    # 过滤条件
    min_amount: float = 100000000  # 最小成交额 1 亿
    min_volume: int = 10000  # 最小成交量 1 万手
    max_change_pct: float = 20.0  # 最大涨跌幅 (排除 ST)
    min_price: float = 1.0  # 最小股价
    max_price: float = 500.0  # 最大股价
    
    # 数据质量
    min_quality: float = 0.8  # 最小数据质量
    
    # 主力选股池配置
    main_pool_size: int = 100  # 主力选股池数量
    main_pool_min_amount: float = 50000000  # 主力选股池最小成交额 5000 万
    
    def to_dict(self) -> dict:
        return asdict(self)


# ============ 数据源基类 ============

class DataSource:
    """数据源基类"""
    
    name = "base"
    priority = 0  # 优先级，越高越优先
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        self._lock = threading.Lock()
    
    def fetch(self, **kwargs) -> List[StockData]:
        """获取数据"""
        raise NotImplementedError
    
    def save_cache(self, data: List[StockData], filename: str):
        """保存缓存"""
        with self._lock:
            cache_file = self.cache_dir / filename
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'count': len(data),
                'source': self.name,
                'data': [d.to_dict() for d in data]
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    def load_cache(self, filename: str, max_age_minutes: int = 10) -> Optional[List[StockData]]:
        """加载缓存"""
        cache_file = self.cache_dir / filename
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            # 检查过期
            ts_str = cache.get('timestamp', '')
            try:
                timestamp = datetime.fromisoformat(ts_str)
            except:
                return None
            
            age = (datetime.now() - timestamp).total_seconds() / 60
            if age > max_age_minutes:
                return None
            
            # 转换回 StockData
            data = []
            for item in cache.get('data', []):
                stock = StockData(**item)
                data.append(stock)
            
            return data
        except Exception as e:
            return None


# ============ 具体数据源 ============

class TencentDataSource(DataSource):
    """腾讯财经数据源"""
    
    name = "tencent"
    priority = 10
    
    def __init__(self, cache_dir: Path = None):
        super().__init__(cache_dir)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    
    def fetch(self, symbols: List[str] = None, batch_size: int = 80) -> List[StockData]:
        """获取腾讯财经数据"""
        print("[腾讯财经] 获取实时行情...")
        
        if symbols is None:
            symbols = self._generate_symbols()
        
        all_stocks = []
        
        for i in range(0, min(len(symbols), 800), batch_size):
            batch = symbols[i:i+batch_size]
            symbol_list = ','.join(batch)
            url = f"https://qt.gtimg.cn/q={symbol_list}"
            
            try:
                resp = requests.get(url, headers=self.headers, timeout=15)
                resp.encoding = 'gbk'
                
                for line in resp.text.split('\n'):
                    match = re.search(r'v_(\w+)="([^"]+)"', line)
                    if match:
                        fields = match.group(2).split('~')
                        if len(fields) >= 50 and fields[6]:
                            stock = self._parse_field(match.group(1), fields)
                            if stock and stock.data_quality > 0:
                                all_stocks.append(stock)
                
            except Exception as e:
                pass
            
            time.sleep(0.1)
        
        print(f"[腾讯财经] 获取 {len(all_stocks)} 只股票")
        return all_stocks
    
    def _parse_field(self, symbol: str, fields: List[str]) -> Optional[StockData]:
        """解析腾讯数据"""
        try:
            price = float(fields[3]) if fields[3] else 0
            if price <= 0:
                return None
            
            # 成交额解析
            amount_yuan = 0.0
            if len(fields) > 35 and '/' in fields[35]:
                parts = fields[35].split('/')
                if len(parts) >= 3:
                    amount_yuan = float(parts[2])
            
            # 成交量
            volume = int(float(fields[36])) if fields[36] else int(float(fields[6])) if fields[6] else 0
            
            # 数据质量评估
            quality = 1.0
            if amount_yuan <= 0:
                quality = 0.5
            if volume <= 0:
                quality = 0.3
            
            return StockData(
                symbol=symbol,
                name=fields[1],
                price=price,
                change_pct=float(fields[32]) if fields[32] else 0,
                volume=volume,
                amount=amount_yuan,
                turnover_rate=float(fields[37]) if len(fields) > 37 and fields[37] else 0,
                pe_ratio=float(fields[39]) if len(fields) > 39 and fields[39] else 0,
                source='tencent',
                crawl_time=datetime.now().isoformat(),
                data_quality=quality
            )
        except:
            return None
    
    def _generate_symbols(self) -> List[str]:
        """生成 A 股代码"""
        symbols = []
        for prefix in range(600, 606):
            for suffix in range(1000):
                symbols.append(f"sh{prefix}{suffix%1000:03d}")
        for prefix in ['000', '002', '300', '301']:
            for i in range(5000):
                symbols.append(f"sz{prefix}{i%1000:03d}")
        return list(set(symbols))[:1500]


class SinaDataSource(DataSource):
    """新浪财经数据源"""
    
    name = "sina"
    priority = 8
    
    def __init__(self, cache_dir: Path = None):
        super().__init__(cache_dir)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    
    def fetch(self, codes: List[str] = None, top_gainers: bool = False) -> List[StockData]:
        """获取新浪财经数据"""
        if top_gainers:
            return self._fetch_top_gainers()
        
        if not codes:
            codes = ['sh600000', 'sh600001', 'sh600004', 'sh600006', 'sh600007']
        
        symbol_list = ','.join(codes)
        url = f"http://hq.sinajs.cn/list={symbol_list}"
        
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.encoding = 'gbk'
            
            results = []
            for line in resp.text.split('\n'):
                if not line.strip():
                    continue
                match = line.split('="')
                if len(match) != 2:
                    continue
                
                symbol_part = match[0].replace('var hq_str_', '')
                data_part = match[1].strip('";')
                fields = data_part.split(',')
                
                if len(fields) < 10:
                    continue
                
                price = float(fields[1]) if fields[1] else 0
                if price <= 0:
                    continue
                
                stock = StockData(
                    symbol=symbol_part,
                    name=fields[0],
                    price=price,
                    change_pct=((price - float(fields[2])) / float(fields[2]) * 100) if fields[1] and fields[2] else 0,
                    volume=int(float(fields[8])) if fields[8] else 0,
                    amount=float(fields[9]) if fields[9] else 0,
                    source='sina',
                    crawl_time=datetime.now().isoformat(),
                    data_quality=0.9
                )
                results.append(stock)
            
            return results
        except Exception as e:
            print(f"[新浪财经] 获取失败：{e}")
            return []
    
    def _fetch_top_gainers(self) -> List[StockData]:
        """获取涨幅榜"""
        url = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
        params = {
            'page': 1, 'num': 50, 'sort': 'changepercent', 'asc': 0, 'node': 'hs_a',
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=15)
            data = resp.json()
            
            results = []
            for item in data:
                price = float(item.get('price', 0))
                if price <= 0:
                    continue
                
                stock = StockData(
                    symbol=item.get('symbol', ''),
                    name=item.get('name', ''),
                    price=price,
                    change_pct=float(item.get('changepercent', 0)),
                    volume=int(float(item.get('volume', 0))) if item.get('volume') else 0,
                    amount=float(item.get('amount', 0)) if item.get('amount') else 0,
                    source='sina_top',
                    crawl_time=datetime.now().isoformat(),
                    data_quality=0.85
                )
                results.append(stock)
            
            return results
        except Exception as e:
            return []


class BaiduDataSource(DataSource):
    """百度股市通数据源"""
    
    name = "baidu"
    priority = 9
    
    def __init__(self, cache_dir: Path = None):
        super().__init__(cache_dir)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://gushitong.baidu.com/',
        }
    
    def fetch(self, count: int = 50) -> List[StockData]:
        """获取百度资金流排行"""
        print("[百度股市通] 获取资金流排行...")
        
        url = "https://gushitong.baidu.com/opendata"
        params = {
            'resource_id': '5350', 'query': '沪深 A 股', 'market': 'ab',
            'group': 'asyn_rank', 'pn': '0', 'rn': str(count), 'pc_web': '1', 'code': '110000',
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=15)
            data = resp.json()
            
            if data.get('ResultCode') != '0' or not data.get('Result'):
                return []
            
            result = data['Result'][0]
            result_data = result.get('DisplayData', {}).get('resultData', {})
            
            rows = result_data.get('newTable', {}).get('data', [])
            if not rows:
                rows = result_data.get('result', [])
            
            results = []
            for row in rows:
                code = row.get('股票代码') or row.get('code', '')
                if not code:
                    continue
                
                # 格式化代码
                if code.startswith('6'):
                    symbol = f"sh{code}"
                else:
                    symbol = f"sz{code}"
                
                price = float(row.get('最新价') or row.get('price') or 0)
                amount = float(row.get('成交额') or 0)
                
                stock = StockData(
                    symbol=symbol,
                    name=row.get('股票名称') or row.get('name', ''),
                    price=price,
                    change_pct=float(row.get('涨跌幅') or 0),
                    volume=int(float(row.get('成交量') or 0)),
                    amount=amount,
                    main_net=float(row.get('主力净流入') or 0),
                    source='baidu',
                    crawl_time=datetime.now().isoformat(),
                    data_quality=0.9
                )
                results.append(stock)
            
            print(f"[百度股市通] 获取 {len(results)} 条数据")
            return results
        except Exception as e:
            print(f"[百度股市通] 获取失败：{e}")
            return []


# ============ 选股器核心 ============

class StockSelector:
    """选股器核心"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        # 注册数据源
        self.data_sources: Dict[str, DataSource] = {
            'tencent': TencentDataSource(self.cache_dir),
            'sina': SinaDataSource(self.cache_dir),
            'baidu': BaiduDataSource(self.cache_dir),
        }
        
        # 默认因子配置
        self.factor_config = FactorConfig()
    
    def set_factor_weights(self, **weights):
        """设置因子权重"""
        for key, value in weights.items():
            if hasattr(self.factor_config, key):
                setattr(self.factor_config, key, value)
    
    def calculate_score(self, stock: StockData) -> float:
        """计算综合评分"""
        cfg = self.factor_config
        
        # 归一化处理
        amount_score = min(100, stock.amount / cfg.min_amount * 25)
        change_score = min(100, max(0, (stock.change_pct + 10) / 30 * 100))
        volume_score = min(100, stock.volume / cfg.min_volume * 15)
        
        # 主力流入评分
        if stock.main_net > 0:
            main_score = min(100, stock.main_net / 100000000 * 50)  # 1 亿=50 分
        else:
            main_score = 0
        
        # 换手率评分 (适中最好)
        if 2 <= stock.turnover_rate <= 10:
            turnover_score = 100
        elif stock.turnover_rate < 2:
            turnover_score = stock.turnover_rate / 2 * 100
        else:
            turnover_score = max(0, 100 - (stock.turnover_rate - 10) * 5)
        
        # 技术面评分 (简化)
        technical_score = 50  # 默认中间值
        if stock.ma5 > stock.ma20 > 0:
            technical_score = 70
        if stock.change_pct > 3:
            technical_score += 20
        
        # 加权计算
        score = (
            amount_score * cfg.amount_weight +
            change_score * cfg.change_weight +
            volume_score * cfg.volume_weight +
            main_score * cfg.main_flow_weight +
            turnover_score * cfg.turnover_weight +
            technical_score * cfg.technical_weight
        )
        
        return round(score, 2)
    
    def filter_stocks(self, stocks: List[StockData]) -> List[StockData]:
        """过滤股票"""
        cfg = self.factor_config
        filtered = []
        
        for stock in stocks:
            # 数据质量过滤
            if stock.data_quality < cfg.min_quality:
                continue
            
            # 价格过滤
            if stock.price < cfg.min_price or stock.price > cfg.max_price:
                continue
            
            # 涨跌幅过滤 (排除 ST 和异常)
            if abs(stock.change_pct) > cfg.max_change_pct:
                continue
            
            # 成交额过滤
            if stock.amount < cfg.min_amount:
                continue
            
            # 成交量过滤
            if stock.volume < cfg.min_volume:
                continue
            
            filtered.append(stock)
        
        return filtered
    
    def build_main_pool(self, top_n: int = 100, use_cache: bool = True) -> List[StockData]:
        """
        构建当日主力净流入选股池
        
        Args:
            top_n: 选股池数量 (默认 100)
            use_cache: 是否使用缓存
        
        Returns:
            List[StockData]: 主力净流入前 N 只股票
        """
        print(f"\n{'='*60}")
        print(f"🏦 构建主力净流入选股池 Top{top_n}")
        print(f"{'='*60}\n")
        
        all_stocks = []
        
        # 1. 尝试百度股市通 (真实主力数据)
        baidu_ds = self.data_sources['baidu']
        stocks = None
        
        if use_cache:
            stocks = baidu_ds.load_cache('baidu_flow_cache.json', max_age_minutes=5)
        
        if not stocks:
            stocks = baidu_ds.fetch(count=top_n * 2)
            if stocks:
                baidu_ds.save_cache(stocks, 'baidu_flow_cache.json')
        
        if stocks:
            all_stocks.extend(stocks)
            print(f"[百度股市通] 获取 {len(stocks)} 条主力数据")
        
        # 2. 如果百度数据不足，用腾讯成交额排序作为替代
        # ⚠️ 注意：不使用估算数据，改用成交额排序
        if len(all_stocks) < top_n:
            tencent_ds = self.data_sources['tencent']
            print(f"[腾讯财经] 补充数据 (按成交额排序，不使用估算)...")
            
            tencent_stocks = tencent_ds.fetch()
            
            # 按成交额排序 (真实数据)，代替主力净流入
            # ⚠️ 不再使用估算的主力净流入
            tencent_stocks.sort(key=lambda x: x.amount, reverse=True)
            
            # 只添加有真实成交额的股票
            tencent_stocks = [s for s in tencent_stocks if s.amount > 0]
            
            all_stocks.extend(tencent_stocks)
            print(f"[腾讯财经] 获取 {len(tencent_stocks)} 只股票 (按成交额排序)")
        
        # 3. 过滤
        cfg = self.factor_config
        filtered = []
        for stock in all_stocks:
            # 只过滤价格和数据质量，放宽成交额限制
            if stock.data_quality < 0.5:
                continue
            if stock.price < 0.5 or stock.price > 1000:
                continue
            if stock.amount < cfg.main_pool_min_amount:
                continue
            filtered.append(stock)
        
        # 4. 按真实主力净流入排序 (百度数据有 main_net)，其次按成交额排序
        def sort_key(s):
            # 如果有真实主力数据，优先使用
            if s.main_net != 0:
                return (1, s.main_net)
            # 否则用成交额作为次要排序
            return (0, s.amount)
        
        filtered.sort(key=sort_key, reverse=True)
        
        # 5. 保存选股池
        pool_file = self.cache_dir / f"main_pool_{datetime.now().strftime('%Y%m%d')}.json"
        
        # 只统计真实主力数据
        real_main_stocks = [s for s in filtered[:top_n] if s.main_net != 0]
        total_real_net = sum(s.main_net for s in real_main_stocks)
        
        pool_data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'count': min(top_n, len(filtered)),
            'real_data_count': len(real_main_stocks),
            'total_net': total_real_net,
            'note': '💰=真实主力数据，📊=真实成交额 (非估算)',
            'stocks': [s.to_dict() for s in filtered[:top_n]]
        }
        with open(pool_file, 'w', encoding='utf-8') as f:
            json.dump(pool_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 主力选股池已保存：{pool_file}")
        print(f"   选股池数量：{min(top_n, len(filtered))} 只")
        if len(real_main_stocks) > 0:
            print(f"   真实主力数据：{len(real_main_stocks)} 只")
            print(f"   总主力净流入：{total_real_net/100000000:.2f}亿 (仅真实数据)")
        else:
            print(f"   ⚠️ 无真实主力数据，使用成交额排序 (严禁估算)")
        
        return filtered[:top_n]
    
    def select(self, strategy: str = 'multi', top_n: int = 20, 
               use_cache: bool = True) -> List[StockData]:
        """
        执行选股
        
        Args:
            strategy: 'main'(主力), 'multi'(多因子), 'volume'(成交量), 'change'(涨幅),
                     'main_pool'(主力选股池)
            top_n: 返回数量
            use_cache: 是否使用缓存
        
        Returns:
            List[StockData]: 选中的股票列表
        """
        print(f"\n{'='*60}")
        print(f"🎯 选股策略：{strategy}")
        print(f"{'='*60}\n")
        
        all_stocks = []
        
        # 获取数据
        if strategy == 'main_pool':
            # 主力选股池策略
            return self.build_main_pool(top_n=top_n)
        
        if strategy == 'main':
            # 主力策略：百度 + 腾讯估算
            baidu_ds = self.data_sources['baidu']
            tencent_ds = self.data_sources['tencent']
            
            # 尝试百度
            stocks = None
            if use_cache:
                stocks = baidu_ds.load_cache('baidu_flow_cache.json', max_age_minutes=5)
            
            if not stocks:
                stocks = baidu_ds.fetch(count=top_n * 3)
                if stocks:
                    baidu_ds.save_cache(stocks, 'baidu_flow_cache.json')
            
            all_stocks.extend(stocks)
            
            # 百度失败则用腾讯补充
            if len(all_stocks) < top_n:
                print("[腾讯财经] 补充数据...")
                tencent_stocks = tencent_ds.fetch()
                tencent_stocks.sort(key=lambda x: x.amount, reverse=True)
                all_stocks.extend(tencent_stocks[:top_n * 2])
        
        elif strategy == 'multi':
            # 多因子策略：腾讯 + 百度
            tencent_ds = self.data_sources['tencent']
            baidu_ds = self.data_sources['baidu']
            
            # 并行获取
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_tencent = executor.submit(
                    tencent_ds.fetch if not use_cache else 
                    lambda: tencent_ds.load_cache('tencent_cache.json', 10) or tencent_ds.fetch()
                )
                future_baidu = executor.submit(
                    lambda: baidu_ds.fetch(count=100)
                )
                
                tencent_stocks = future_tencent.result()
                baidu_stocks = future_baidu.result()
            
            all_stocks.extend(tencent_stocks)
            all_stocks.extend(baidu_stocks)
            
            # 保存缓存
            tencent_ds.save_cache(tencent_stocks, 'tencent_cache.json')
            baidu_ds.save_cache(baidu_stocks, 'baidu_flow_cache.json')
        
        elif strategy == 'volume':
            # 成交量策略
            tencent_ds = self.data_sources['tencent']
            stocks = tencent_ds.fetch()
            tencent_ds.save_cache(stocks, 'tencent_cache.json')
            all_stocks.extend(stocks)
        
        elif strategy == 'change':
            # 涨幅策略
            sina_ds = self.data_sources['sina']
            stocks = sina_ds.fetch(top_gainers=True)
            all_stocks.extend(stocks)
        
        # 过滤
        print(f"[过滤前] {len(all_stocks)} 只股票")
        filtered = self.filter_stocks(all_stocks)
        print(f"[过滤后] {len(filtered)} 只股票")
        
        # 计算评分
        for stock in filtered:
            stock.score = self.calculate_score(stock)
        
        # 排序
        if strategy == 'main':
            filtered.sort(key=lambda x: x.main_net, reverse=True)
        elif strategy == 'volume':
            filtered.sort(key=lambda x: x.volume, reverse=True)
        elif strategy == 'change':
            filtered.sort(key=lambda x: x.change_pct, reverse=True)
        else:  # multi
            filtered.sort(key=lambda x: x.score, reverse=True)
        
        # 设置排名
        for i, stock in enumerate(filtered[:top_n], 1):
            stock.rank = i
        
        # 打印结果
        self._print_results(filtered[:top_n], strategy)
        
        return filtered[:top_n]
    
    def _print_results(self, stocks: List[StockData], strategy: str):
        """打印结果"""
        if not stocks:
            print("❌ 无符合条件的股票")
            return
        
        # 主力选股池特殊格式
        if strategy == 'main_pool':
            print(f"\n{'='*110}")
            print(f"🏦 当日主力净流入选股池 Top{len(stocks)}")
            print(f"{'='*110}")
            print(f"{'排名':<4} {'代码':<10} {'名称':<10} {'股价':>8} {'涨跌':>8} {'主力净流入':>14} {'成交额':>10} {'数据源':<12}")
            print(f"{'-'*110}")
            
            total_net = 0
            real_data_count = 0
            for s in stocks:
                # 只有真实主力数据才计入统计
                if s.main_net != 0:
                    net_str = f"{s.main_net/100000000:.2f}亿" if abs(s.main_net) >= 100000000 else f"{s.main_net/10000:.0f}万"
                    total_net += s.main_net
                    real_data_count += 1
                    source_mark = '💰'
                else:
                    net_str = '-'
                    source_mark = '📊(成交额)'
                
                amount_str = f"{s.amount/100000000:.2f}亿" if s.amount >= 100000000 else f"{s.amount/10000:.0f}万"
                change_sign = '+' if s.change_pct >= 0 else ''
                
                print(f"{s.rank:<4} {s.symbol:<10} {s.name:<10} ¥{s.price:>5.2f} "
                      f"{change_sign}{s.change_pct:>5.2f}% {source_mark}{net_str:>10} {amount_str:>8} {s.source:<12}")
            
            print(f"{'-'*110}")
            print(f"📊 选股池统计:")
            print(f"   股票数量：{len(stocks)} 只")
            if real_data_count > 0:
                print(f"   真实主力数据：{real_data_count} 只")
                print(f"   总主力净流入：{total_net/100000000:.2f}亿 (仅真实数据)")
                print(f"   平均主力净流入：{total_net/real_data_count/100000000:.2f}亿")
            else:
                print(f"   ⚠️ 无真实主力数据，按成交额排序")
            print(f"   💰 = 真实主力数据  📊 = 真实成交额数据")
            print(f"{'='*110}")
            return
        
        # 普通策略格式
        print(f"\n{'='*90}")
        print(f"📊 选股结果 Top{len(stocks)}")
        print(f"{'='*90}")
        print(f"{'排名':<4} {'代码':<10} {'名称':<10} {'股价':>8} {'涨跌':>8} {'成交额':>10} {'评分':>6}")
        print(f"{'-'*90}")
        
        for s in stocks:
            amount_str = f"{s.amount/100000000:.2f}亿" if s.amount >= 100000000 else f"{s.amount/10000:.0f}万"
            change_sign = '+' if s.change_pct >= 0 else ''
            score_str = f"{s.score:.1f}" if s.score > 0 else '-'
            
            print(f"{s.rank:<4} {s.symbol:<10} {s.name:<10} ¥{s.price:>5.2f} "
                  f"{change_sign}{s.change_pct:>5.2f}% {amount_str:>8} {score_str:>6}")
        
        print(f"{'='*90}")


# ============ 主函数 ============

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='选股模块 v2.0 - 支持主力选股池')
    parser.add_argument('--strategy', choices=['main', 'multi', 'volume', 'change', 'main_pool'],
                       default='multi', help='选股策略：main=主力，multi=多因子，volume=成交量，change=涨幅，main_pool=主力选股池')
    parser.add_argument('--top', type=int, default=20, help='返回数量 (主力选股池默认 100)')
    parser.add_argument('--no-cache', action='store_true', help='不使用缓存')
    parser.add_argument('--config', type=str, help='配置文件 (JSON)')
    parser.add_argument('--pool', action='store_true', help='快速构建主力选股池 (等价于 --strategy main_pool --top 100)')
    
    args = parser.parse_args()
    
    # 快捷方式：--pool
    if args.pool:
        args.strategy = 'main_pool'
        args.top = 100
    
    selector = StockSelector()
    
    # 加载配置
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
                if 'factors' in config:
                    selector.set_factor_weights(**config['factors'])
        except Exception as e:
            print(f"⚠️  配置文件加载失败：{e}")
    
    # 执行选股
    stocks = selector.select(
        strategy=args.strategy,
        top_n=args.top,
        use_cache=not args.no_cache
    )
    
    # 保存结果
    if stocks:
        result_file = selector.cache_dir / f"select_{args.strategy}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump([s.to_dict() for s in stocks], f, ensure_ascii=False, indent=2)
        print(f"\n✅ 结果已保存：{result_file}")


if __name__ == '__main__':
    main()
