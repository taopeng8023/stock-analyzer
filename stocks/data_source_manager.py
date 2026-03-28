#!/usr/bin/env python3
"""
多数据源股票数据接口管理器

集成数据源:
- 雪球 (xueqiu) - 需要 Token
- 东方财富 (eastmoney) - 限流
- 新浪财经 (sina) - 稳定
- 腾讯财经 (tencent) - 稳定

功能:
- 自动限频 (避免反爬)
- 自动重试
- 数据缓存
- 多数据源 fallback

用法:
    from data_source_manager import StockDataSource
    manager = StockDataSource()
    data = manager.get_stock_history('600152')
"""

import time
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from collections import deque
import hashlib

# 尝试导入 AKShare
try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False

# 尝试导入 requests
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class RateLimiter:
    """请求速率限制器"""
    
    def __init__(self, max_requests: int, time_window: int):
        """
        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口 (秒)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
    
    def wait_if_needed(self):
        """如果需要，等待直到可以发送请求"""
        now = time.time()
        
        # 移除超出时间窗口的请求
        while self.requests and self.requests[0] <= now - self.time_window:
            self.requests.popleft()
        
        # 如果达到限制，等待
        if len(self.requests) >= self.max_requests:
            sleep_time = self.requests[0] + self.time_window - now
            if sleep_time > 0:
                print(f'   限频：等待 {sleep_time:.1f} 秒...')
                time.sleep(sleep_time)
                # 再次清理
                now = time.time()
                while self.requests and self.requests[0] <= now - self.time_window:
                    self.requests.popleft()
        
        # 记录请求
        self.requests.append(time.time())


class DataSourceManager:
    """多数据源管理器"""
    
    # 各数据源的限频配置 (请求数/时间窗口)
    RATE_LIMITS = {
        'xueqiu': (5, 10),      # 雪球：5 次/10 秒
        'eastmoney': (3, 10),   # 东财：3 次/10 秒
        'sina': (10, 10),       # 新浪：10 次/10 秒
        'tencent': (10, 10),    # 腾讯：10 次/10 秒
    }
    
    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # 秒
    
    def __init__(self, cache_dir: str = None, token: str = None):
        """
        Args:
            cache_dir: 缓存目录
            token: 雪球 Token (不传则从配置文件读取)
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        # 雪球 Token
        self.xueqiu_token = token or self._load_xueqiu_token()
        
        # 初始化速率限制器
        self.rate_limiters = {
            source: RateLimiter(max_req, window)
            for source, (max_req, window) in self.RATE_LIMITS.items()
        }
        
        # 初始化 Session
        if HAS_REQUESTS:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            })
        else:
            self.session = None
        
        # 统计
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'errors': 0,
        }
    
    def _load_xueqiu_token(self) -> str:
        """从配置文件加载雪球 Token"""
        token_path = os.path.expanduser('~/.akshare/xueqiu_token.txt')
        if os.path.exists(token_path):
            with open(token_path, 'r') as f:
                return f.read().strip()
        return ''
    
    def _get_cache_key(self, source: str, symbol: str, **kwargs) -> str:
        """生成缓存键"""
        key_str = f"{source}:{symbol}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.json"
    
    def _load_from_cache(self, cache_key: str, max_age: int = 300) -> Optional[Dict]:
        """
        从缓存加载数据
        
        Args:
            cache_key: 缓存键
            max_age: 最大缓存时间 (秒)，默认 5 分钟
        """
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查缓存是否过期
            cache_time = data.get('_cache_time', 0)
            if time.time() - cache_time > max_age:
                return None
            
            self.stats['cache_hits'] += 1
            return data.get('data')
            
        except Exception:
            return None
    
    def _save_to_cache(self, cache_key: str, data: Dict):
        """保存数据到缓存"""
        cache_path = self._get_cache_path(cache_key)
        
        cache_data = {
            'data': data,
            '_cache_time': time.time(),
            '_source': 'local',
        }
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    def _request_with_retry(self, func, *args, **kwargs):
        """带重试的请求"""
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                if attempt > 0:
                    delay = self.RETRY_DELAY * attempt
                    print(f'   重试 {attempt}/{self.MAX_RETRIES} (等待{delay}秒)...')
                    time.sleep(delay)
                
                return func(*args, **kwargs)
                
            except Exception as e:
                last_error = e
                self.stats['errors'] += 1
                print(f'   请求失败 (尝试{attempt+1}/{self.MAX_RETRIES}): {e}')
        
        raise last_error
    
    def get_stock_history(self, symbol: str, source: str = 'auto',
                         start_date: str = None, end_date: str = None,
                         adjust: str = 'qfq', use_cache: bool = True) -> Optional[List[Dict]]:
        """
        获取个股历史行情
        
        Args:
            symbol: 股票代码 (如 '600152')
            source: 数据源 ('xueqiu'/'eastmoney'/'sina'/'tencent'/'auto')
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            adjust: 复权 ('qfq'/'hfq'/'none')
            use_cache: 是否使用缓存
        
        Returns:
            历史行情数据列表
        """
        # 定义数据源优先级 (auto 模式下依次尝试)
        source_order = ['eastmoney', 'sina', 'tencent']
        
        # 如果指定了数据源，只尝试该数据源
        if source != 'auto':
            source_order = [source]
        
        # 尝试从缓存加载
        cache_key = self._get_cache_key('auto', symbol,
                                        start_date=start_date,
                                        end_date=end_date,
                                        adjust=adjust)
        if use_cache:
            cached = self._load_from_cache(cache_key, max_age=300)
            if cached:
                print(f'   ✅ 从缓存获取')
                return cached
        
        # 依次尝试不同数据源
        for src in source_order:
            try:
                # 限频等待
                self.rate_limiters[src].wait_if_needed()
                
                print(f'   从 {src} 获取数据...')
                self.stats['total_requests'] += 1
                
                if src == 'eastmoney':
                    data = self._get_from_eastmoney(symbol, start_date, end_date, adjust)
                elif src == 'sina':
                    data = self._get_from_sina(symbol, start_date, end_date)
                elif src == 'tencent':
                    data = self._get_from_tencent(symbol, start_date, end_date)
                else:
                    continue
                
                if data:
                    # 保存到缓存
                    if use_cache:
                        self._save_to_cache(cache_key, data)
                    print(f'   ✅ 获取成功 ({len(data)} 条)')
                    return data
                else:
                    print(f'   ❌ 返回空数据')
                    
            except Exception as e:
                print(f'   ❌ 获取失败：{e}')
                # 继续尝试下一个数据源
                continue
        
        # 所有数据源都失败
        return None
    
    def _select_best_source(self, symbol: str) -> str:
        """自动选择最佳数据源"""
        # 优先顺序：缓存 > 东财 (AKShare) > 新浪 > 腾讯 > 雪球
        # 优先使用 AKShare 东财接口，数据最全最准确
        return 'eastmoney'
    
    def _get_from_xueqiu(self, symbol: str, start_date: str,
                        end_date: str, adjust: str) -> Optional[List[Dict]]:
        """从雪球获取数据"""
        if not HAS_AKSHARE:
            raise ImportError('AKShare 未安装')
        
        if not self.xueqiu_token:
            raise ValueError('雪球 Token 未配置')
        
        # 转换股票代码格式
        if symbol.startswith('6'):
            xq_symbol = f'SH{symbol}'
        else:
            xq_symbol = f'SZ{symbol}'
        
        data = ak.stock_zh_a_hist(
            symbol=xq_symbol,
            period='daily',
            start_date=start_date or '20250101',
            end_date=end_date or datetime.now().strftime('%Y%m%d'),
            adjust=adjust
        )
        
        if data is None or data.empty:
            return None
        
        # 转换为字典列表
        return data.to_dict('records')
    
    def _get_from_eastmoney(self, symbol: str, start_date: str,
                           end_date: str, adjust: str) -> Optional[List[Dict]]:
        """从东方财富获取数据 (带重试机制)"""
        if not HAS_AKSHARE:
            raise ImportError('AKShare 未安装')
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = 2 * attempt
                    time.sleep(delay)
                
                data = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period='daily',
                    start_date=start_date or '20250101',
                    end_date=end_date or datetime.now().strftime('%Y%m%d'),
                    adjust=adjust
                )
                
                if data is not None and not data.empty:
                    return data.to_dict('records')
                else:
                    return None
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                continue
        
        return None
    
    def _get_from_sina(self, symbol: str, start_date: str,
                      end_date: str) -> Optional[List[Dict]]:
        """从新浪获取数据"""
        # 确定市场前缀
        if symbol.startswith('6'):
            market = 'sh'
        else:
            market = 'sz'
        
        full_symbol = f'{market}{symbol}'
        
        url = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
        params = {
            'symbol': full_symbol,
            'scale': '240',  # 日线
            'ma': 'no',
            'datalen': '250',
        }
        
        resp = self.session.get(url, params=params, timeout=15)
        data = resp.json()
        
        if not data:
            return None
        
        # 转换格式
        result = []
        for k in data:
            result.append({
                '日期': k.get('day'),
                '开盘': float(k.get('open', 0)),
                '收盘': float(k.get('close', 0)),
                '最高': float(k.get('high', 0)),
                '最低': float(k.get('low', 0)),
                '成交量': int(k.get('volume', 0)),
            })
        
        return result
    
    def _get_from_tencent(self, symbol: str, start_date: str,
                         end_date: str) -> Optional[List[Dict]]:
        """从腾讯财经获取数据"""
        # 确定市场前缀
        if symbol.startswith('6'):
            market = 'sh'
        else:
            market = 'sz'
        
        full_symbol = f'{market}{symbol}'
        
        url = f'https://qt.gtimg.cn/q={full_symbol}'
        
        resp = self.session.get(url, timeout=15)
        resp.encoding = 'gbk'
        
        # 解析腾讯格式
        line = resp.text.strip()
        if '=' not in line:
            return None
        
        data_part = line.split('=')[1].strip('"')
        fields = data_part.split('~')
        
        if len(fields) < 50:
            return None
        
        # 腾讯返回的是实时数据，不是历史数据
        # 这里仅做演示
        return [{
            '日期': datetime.now().strftime('%Y-%m-%d'),
            '开盘': float(fields[2]) if fields[2] else 0,
            '收盘': float(fields[3]) if fields[3] else 0,
            '最高': float(fields[33]) if fields[33] else 0,
            '最低': float(fields[34]) if fields[34] else 0,
            '成交量': int(fields[6]) if fields[6] else 0,
        }]
    
    def get_stock_spot(self, symbol: str, source: str = 'auto') -> Optional[Dict]:
        """
        获取个股实时行情
        
        Args:
            symbol: 股票代码
            source: 数据源
        
        Returns:
            实时行情数据
        """
        if source == 'auto':
            source = self._select_best_source(symbol)
        
        self.rate_limiters[source].wait_if_needed()
        self.stats['total_requests'] += 1
        
        try:
            if source == 'xueqiu':
                if not HAS_AKSHARE:
                    raise ImportError('AKShare 未安装')
                
                if symbol.startswith('6'):
                    xq_symbol = f'SH{symbol}'
                else:
                    xq_symbol = f'SZ{symbol}'
                
                data = ak.stock_individual_spot_xq(
                    symbol=xq_symbol,
                    token=self.xueqiu_token,
                    timeout=15
                )
                
                if data is not None and not data.empty:
                    return data.to_dict('records')[0]
            
            # 其他数据源...
            
        except Exception as e:
            print(f'获取实时行情失败：{e}')
        
        return None
    
    def get_fund_flow_rank(self, period: str = '即时') -> Optional[List[Dict]]:
        """
        获取个股资金流排行
        
        Args:
            period: 排行周期 (即时/3 日排行/5 日排行/10 日排行/20 日排行)
        
        Returns:
            资金流数据列表
        """
        if not HAS_AKSHARE:
            raise ImportError('AKShare 未安装')
        
        # 限频等待
        self.rate_limiters['eastmoney'].wait_if_needed()
        self.stats['total_requests'] += 1
        
        try:
            print(f'   获取{period}资金流排行...')
            data = ak.stock_fund_flow_individual(symbol=period)
            
            if data is not None and not data.empty:
                print(f'   ✅ 获取成功 ({len(data)}只股票)')
                return data.to_dict('records')
            else:
                print(f'   ❌ 获取失败：返回空数据')
                return None
                
        except Exception as e:
            print(f'   ❌ 获取失败：{e}')
            return None
    
    def get_stock_fund_flow(self, symbol: str) -> Optional[Dict]:
        """
        获取单只股票的资金流数据
        
        Args:
            symbol: 股票代码
        
        Returns:
            资金流数据
        """
        # 获取全量排行后筛选
        fund_data = self.get_fund_flow_rank(period='即时')
        
        if not fund_data:
            return None
        
        # 筛选指定股票 (转换为字符串比较)
        symbol_str = str(symbol).zfill(6)  # 补齐 6 位
        for stock in fund_data:
            stock_code = str(stock.get('股票代码', '')).zfill(6)
            if stock_code == symbol_str:
                return stock
        
        return None
    
    def get_cyq_data(self, symbol: str, adjust: str = 'qfq') -> Optional[Dict]:
        """
        获取个股筹码分布数据 (CYQ)
        
        Args:
            symbol: 股票代码
            adjust: 复权类型 (qfq/hfq/空)
        
        Returns:
            筹码分布数据
        """
        if not HAS_AKSHARE:
            raise ImportError('AKShare 未安装')
        
        # 限频等待
        self.rate_limiters['eastmoney'].wait_if_needed()
        self.stats['total_requests'] += 1
        
        try:
            print(f'   获取{symbol}筹码分布...')
            data = ak.stock_cyq_em(symbol=symbol, adjust=adjust)
            
            if data is not None and not data.empty:
                print(f'   ✅ 获取成功 ({len(data)} 个价位)')
                return {
                    'symbol': symbol,
                    'data': data.to_dict('records'),
                    'columns': list(data.columns),
                }
            else:
                print(f'   ❌ 获取失败：返回空数据')
                return None
                
        except Exception as e:
            print(f'   ❌ 获取失败：{e}')
            return None
    
    def get_hot_rank(self) -> Optional[List[Dict]]:
        """
        获取股票热度排行榜 (雪球关注榜)
        
        Returns:
            热度排行数据列表
        """
        if not HAS_AKSHARE:
            raise ImportError('AKShare 未安装')
        
        # 限频等待
        self.rate_limiters['xueqiu'].wait_if_needed()
        self.stats['total_requests'] += 1
        
        try:
            print('   获取雪球关注榜...')
            data = ak.stock_hot_follow_xq(symbol='最热门')
            
            if data is not None and not data.empty:
                print(f'   ✅ 获取成功 ({len(data)} 只股票)')
                return data.to_dict('records')
            else:
                print(f'   ❌ 获取失败：返回空数据')
                return None
                
        except Exception as e:
            print(f'   ❌ 获取失败：{e}')
            return None
    
    def get_stock_hot_rank(self, symbol: str, hot_data: List[Dict] = None) -> Optional[Dict]:
        """
        获取单只股票的热度排名
        
        Args:
            symbol: 股票代码
            hot_data: 热度排行数据 (可选，避免重复获取)
        
        Returns:
            热度排名信息
        """
        # 如果没有传入热度数据，获取全量
        if hot_data is None:
            hot_data = self.get_hot_rank()
        
        if not hot_data:
            return None
        
        # 查找股票排名
        symbol_str = str(symbol).zfill(6)
        for i, stock in enumerate(hot_data):
            stock_code = str(stock.get('股票代码', ''))
            # 去除市场前缀
            if stock_code.startswith('SH') or stock_code.startswith('SZ'):
                stock_code = stock_code[2:]
            
            if stock_code == symbol_str:
                return {
                    'rank': i + 1,
                    'symbol': symbol,
                    'name': stock.get('股票简称', ''),
                    'follow_count': stock.get('关注', 0),
                    'price': stock.get('最新价', 0),
                }
        
        return None  # 未找到
    
    def heat_score(self, rank: int, total: int = 5500) -> float:
        """
        根据热度排名计算评分 (0-2 分)
        
        Args:
            rank: 热度排名
            total: 总排名数
        
        Returns:
            评分 (0-2 分)
        """
        if rank <= 0:
            return 0
        
        # 排名百分比
        rank_pct = rank / total
        
        if rank_pct < 0.01:  # 前 1% (前 55)
            return 1.0  # 极热，警惕
        elif rank_pct < 0.05:  # 前 5% (前 275)
            return 2.0  # 高度关注
        elif rank_pct < 0.15:  # 前 15% (前 825)
            return 1.5  # 适度关注 (最佳)
        elif rank_pct < 0.50:  # 前 50%
            return 1.0  # 关注度一般
        else:
            return 0.5  # 关注度低
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            'cache_hit_rate': (
                self.stats['cache_hits'] / self.stats['total_requests'] * 100
                if self.stats['total_requests'] > 0 else 0
            ),
        }


# 全局单例
_manager = None

def get_data_source_manager() -> DataSourceManager:
    """获取数据源管理器单例"""
    global _manager
    if _manager is None:
        _manager = DataSourceManager()
    return _manager


if __name__ == '__main__':
    print('='*70)
    print('数据源管理器测试')
    print('='*70)
    print()
    
    manager = DataSourceManager()
    
    # 测试 1: 获取历史行情
    print('1. 测试获取历史行情 (维科技术 600152)...')
    data = manager.get_stock_history(
        symbol='600152',
        source='auto',
        start_date='20260320',
        end_date='20260327',
        use_cache=True
    )
    
    if data:
        print(f'   获取到 {len(data)} 条数据')
        print(f'   最新：{data[-1]}')
    print()
    
    # 测试 2: 获取实时行情
    print('2. 测试获取实时行情...')
    spot = manager.get_stock_spot('600152', source='xueqiu')
    if spot:
        print(f'   获取成功')
        print(f'   {spot}')
    print()
    
    # 测试 3: 查看统计
    print('3. 统计信息:')
    stats = manager.get_stats()
    print(f'   总请求数：{stats["total_requests"]}')
    print(f'   缓存命中：{stats["cache_hits"]}')
    print(f'   缓存命中率：{stats["cache_hit_rate"]:.1f}%')
    print(f'   错误数：{stats["errors"]}')
    print()
    
    print('='*70)
    print('测试完成！')
    print('='*70)
