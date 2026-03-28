#!/usr/bin/env python3
"""
A 股历史行情自动轮询脚本

功能:
- 收盘后自动获取全 A 股历史行情
- 批量获取并缓存到本地
- 支持增量更新 (只获取新数据)
- 可设置定时任务 (cron) 执行

用法:
    # 手动执行
    python3.11 auto_scan_stocks.py
    
    # 设置 cron (每天 15:30 执行)
    crontab -e
    30 15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3.11 auto_scan_stocks.py >> logs/auto_scan.log 2>&1
"""

import akshare as ak
import json
import time
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import requests


class StockHistoryScanner:
    """A 股历史行情轮询器"""
    
    def __init__(self, cache_dir: str = None):
        """
        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / 'cache' / 'history'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志目录
        self.log_dir = Path(__file__).parent / 'logs'
        self.log_dir.mkdir(exist_ok=True)
        
        # 限频配置 (v2.0 优化版 - 2026-03-27)
        self.batch_size = 10  # 每批获取 10 只 (降低，减少限流风险)
        self.batch_delay = 15  # 每批间隔 15 秒 (增加，让服务器休息)
        self.stock_delay = 0.5  # 每只股票间隔 0.5 秒 (增加，避免触发限流)
        self.max_retries = 3  # 最大重试次数
        self.retry_delay = 3  # 重试间隔 (秒)
        
        # Session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        
        # 统计
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None,
        }
    
    def get_all_a_share_symbols(self) -> List[str]:
        """
        获取所有 A 股股票代码
        
        Returns:
            股票代码列表
        """
        print('获取 A 股股票列表...')
        
        try:
            # 使用 AKShare 获取 A 股列表
            data = ak.stock_info_a_code_name()
            
            if data is not None and not data.empty:
                symbols = data['code'].astype(str).tolist()
                print(f'   ✅ 获取到 {len(symbols)} 只 A 股股票')
                return symbols
            else:
                print('   ❌ 获取失败，使用备用列表')
                return self._get_backup_symbols()
                
        except Exception as e:
            print(f'   ❌ 错误：{e}')
            print('   使用备用列表...')
            return self._get_backup_symbols()
    
    def _get_backup_symbols(self) -> List[str]:
        """备用股票列表 (前 500 只活跃股票)"""
        # 这里可以预定义一些活跃股票
        # 实际使用时建议从 AKShare 获取
        backup = []
        
        # 沪市主板 (600/601/603/605)
        for i in range(1, 500):
            code = f'600{i:03d}'
            backup.append(code)
        
        # 深市主板 (000/001/002/003)
        for i in range(1, 500):
            code = f'000{i:03d}'
            backup.append(code)
        
        return backup[:500]
    
    def fetch_stock_history(self, symbol: str, start_date: str = None, 
                           end_date: str = None, adjust: str = 'qfq') -> Optional[Dict]:
        """
        获取单只股票历史行情
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型
        
        Returns:
            历史行情数据
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            # 默认获取近 250 个交易日
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        
        try:
            # 使用 AKShare 东财接口
            data = ak.stock_zh_a_hist(
                symbol=symbol,
                period='daily',
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            
            if data is not None and not data.empty:
                # 转换为可序列化的格式
                records = []
                for _, row in data.iterrows():
                    record = {}
                    for col in data.columns:
                        val = row[col]
                        # 处理日期类型
                        if hasattr(val, 'strftime'):
                            record[col] = val.strftime('%Y-%m-%d')
                        else:
                            record[col] = val
                    records.append(record)
                
                return {
                    'symbol': symbol,
                    'data': records,
                    'update_time': datetime.now().isoformat(),
                }
            else:
                return None
                
        except Exception as e:
            return None
    
    def fetch_stock_history_sina(self, symbol: str) -> Optional[Dict]:
        """
        从新浪获取股票历史行情 (备用数据源 1)
        
        Args:
            symbol: 股票代码
        
        Returns:
            历史行情数据
        """
        try:
            # 确定市场前缀
            if symbol.startswith('6'):
                market = 'sh'
            else:
                market = 'sz'
            
            full_symbol = f'{market}{symbol}'
            
            url = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
            params = {
                'symbol': full_symbol,
                'scale': '240',
                'ma': 'no',
                'datalen': '250',
            }
            
            resp = self.session.get(url, params=params, timeout=15)
            data = resp.json()
            
            if data and len(data) > 0:
                # 转换格式
                records = []
                for k in data:
                    records.append({
                        '日期': k.get('day'),
                        '开盘': float(k.get('open', 0)),
                        '收盘': float(k.get('close', 0)),
                        '最高': float(k.get('high', 0)),
                        '最低': float(k.get('low', 0)),
                        '成交量': int(k.get('volume', 0)),
                    })
                
                return {
                    'symbol': symbol,
                    'data': records,
                    'update_time': datetime.now().isoformat(),
                    'source': 'sina',
                }
            else:
                return None
                
        except Exception as e:
            return None
    
    def fetch_stock_history_tencent(self, symbol: str) -> Optional[Dict]:
        """
        从腾讯获取股票历史行情 (备用数据源 2)
        
        Args:
            symbol: 股票代码
        
        Returns:
            历史行情数据
        """
        try:
            # 确定市场前缀
            if symbol.startswith('6'):
                market = 'sh'
            else:
                market = 'sz'
            
            full_symbol = f'{market}{symbol}'
            
            url = f'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={full_symbol},day,,,250,qfq'
            
            resp = self.session.get(url, timeout=15)
            data = resp.json()
            
            if data and 'data' in data and full_symbol in data['data']:
                kline_data = data['data'][full_symbol]
                if 'day' in kline_data:
                    records = []
                    for k in kline_data['day']:
                        parts = k.split('|')
                        if len(parts) >= 7:
                            records.append({
                                '日期': parts[0],
                                '开盘': float(parts[1]),
                                '收盘': float(parts[2]),
                                '最高': float(parts[3]),
                                '最低': float(parts[4]),
                                '成交量': int(parts[5]),
                                '成交额': float(parts[6]),
                            })
                    
                    if records:
                        return {
                            'symbol': symbol,
                            'data': records,
                            'update_time': datetime.now().isoformat(),
                            'source': 'tencent',
                        }
            return None
                
        except Exception as e:
            return None
    
    def fetch_with_fallback(self, symbol: str) -> Optional[Dict]:
        """
        多数据源 fallback 获取股票历史行情
        
        优先级：AKShare 东财 -> 新浪 -> 腾讯 -> 重试 AKShare
        
        Args:
            symbol: 股票代码
        
        Returns:
            历史行情数据
        """
        # 数据源列表
        sources = [
            ('AKShare 东财', self.fetch_stock_history),
            ('新浪', self.fetch_stock_history_sina),
            ('腾讯', self.fetch_stock_history_tencent),
        ]
        
        for source_name, fetch_func in sources:
            try:
                data = fetch_func(symbol)
                if data and data.get('data') and len(data['data']) > 0:
                    print(f'      ✅ 从 {source_name} 获取成功 ({len(data["data"])}条)')
                    return data
                else:
                    print(f'      ⚠️ {source_name} 无数据')
            except Exception as e:
                print(f'      ❌ {source_name} 错误：{e}')
            
            # 数据源间延迟
            time.sleep(1)
        
        # 所有数据源都失败，最后重试一次 AKShare
        print(f'      🔄 所有数据源失败，重试 AKShare...')
        time.sleep(self.retry_delay)
        data = self.fetch_stock_history(symbol)
        if data and data.get('data'):
            print(f'      ✅ 重试 AKShare 成功 ({len(data["data"])}条)')
            return data
        
        return None
    
    def save_to_file(self, symbol: str, data: Dict):
        """
        保存数据到文件
        
        Args:
            symbol: 股票代码
            data: 数据字典
        """
        # 按股票代码分组保存
        year_month = datetime.now().strftime('%Y%m')
        subdir = self.cache_dir / year_month
        subdir.mkdir(exist_ok=True)
        
        filepath = subdir / f'{symbol}.json'
        
        # 转换日期对象为字符串 (修复 JSON 序列化问题)
        if 'data' in data and isinstance(data['data'], list):
            for record in data['data']:
                for key, value in record.items():
                    if hasattr(value, 'isoformat'):  # date/datetime 对象
                        record[key] = str(value)
                    elif isinstance(value, float) and (value != value):  # NaN 检查
                        record[key] = None
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    def load_from_file(self, symbol: str) -> Optional[Dict]:
        """
        从文件加载数据
        
        Args:
            symbol: 股票代码
        
        Returns:
            数据字典
        """
        # 查找最新的缓存文件
        for subdir in sorted(self.cache_dir.iterdir(), reverse=True):
            if subdir.is_dir():
                filepath = subdir / f'{symbol}.json'
                if filepath.exists():
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            return json.load(f)
                    except:
                        continue
        return None
    
    def is_cache_valid(self, data: Dict, max_age_hours: int = 24) -> bool:
        """
        检查缓存是否有效
        
        Args:
            data: 数据字典
            max_age_hours: 最大缓存时间 (小时)
        
        Returns:
            是否有效
        """
        if not data:
            return False
        
        update_time = data.get('update_time', '')
        if not update_time:
            return False
        
        try:
            update_dt = datetime.fromisoformat(update_time)
            age = datetime.now() - update_dt
            return age.total_seconds() < max_age_hours * 3600
        except:
            return False
    
    def scan_all(self, force: bool = False, max_stocks: int = None):
        """
        扫描全部 A 股
        
        Args:
            force: 强制更新 (忽略缓存)
            max_stocks: 最大扫描数量 (用于测试)
        """
        print('='*70)
        print('A 股历史行情自动轮询')
        print('='*70)
        print()
        
        self.stats['start_time'] = datetime.now()
        
        # 获取股票列表
        symbols = self.get_all_a_share_symbols()
        
        # 限制数量 (测试用)
        if max_stocks:
            symbols = symbols[:max_stocks]
            print(f'   测试模式：扫描前 {max_stocks} 只股票')
        
        self.stats['total'] = len(symbols)
        print()
        print(f'开始扫描 {len(symbols)} 只股票...')
        print()
        
        # 分批获取
        for i in range(0, len(symbols), self.batch_size):
            batch = symbols[i:i+self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(symbols) + self.batch_size - 1) // self.batch_size
            
            print(f'批次 {batch_num}/{total_batches} (股票 {i+1}-{min(i+self.batch_size, len(symbols))})...')
            
            for idx, symbol in enumerate(batch, 1):
                try:
                    # 检查缓存
                    cached = self.load_from_file(symbol)
                    if not force and self.is_cache_valid(cached, max_age_hours=48):  # 缓存延长到 48 小时
                        self.stats['success'] += 1
                        continue
                    
                    # 使用多数据源 fallback 获取
                    print(f'   [{i+idx}/{len(symbols)}] {symbol}...', end=' ', flush=True)
                    data = self.fetch_with_fallback(symbol)
                    
                    if data:
                        # 保存
                        self.save_to_file(symbol, data)
                        self.stats['success'] += 1
                    else:
                        self.stats['failed'] += 1
                        print(f'❌ 所有数据源失败', flush=True)
                        continue
                    
                    # 单只股票延迟
                    time.sleep(self.stock_delay)
                    
                except Exception as e:
                    self.stats['failed'] += 1
                    print(f'❌ 异常：{e}', flush=True)
                    continue
            
            # 批次延迟
            if i + self.batch_size < len(symbols):
                print(f'   🕐 等待 {self.batch_delay} 秒 (限流保护)...')
                time.sleep(self.batch_delay)
            
            # 进度
            progress = (i + self.batch_size) / len(symbols) * 100
            success_rate = self.stats['success'] / (self.stats['success'] + self.stats['failed']) * 100 if (self.stats['success'] + self.stats['failed']) > 0 else 0
            elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
            remaining = (len(symbols) / (i + self.batch_size) * elapsed) - elapsed if (i + self.batch_size) > 0 else 0
            print(f'   📊 进度：{progress:.1f}% | ✅:{self.stats["success"]} ❌:{self.stats["failed"]} | 成功率:{success_rate:.1f}% | 剩余:{remaining/60:.1f}分钟')
            print()
        
        self.stats['end_time'] = datetime.now()
        
        # 输出统计
        self._print_summary()
        
        # 保存统计
        self._save_stats()
    
    def _print_summary(self):
        """输出统计摘要"""
        print()
        print('='*70)
        print('扫描完成！')
        print('='*70)
        print()
        print(f'总数：{self.stats["total"]} 只')
        print(f'成功：{self.stats["success"]} 只 ({self.stats["success"]/self.stats["total"]*100:.1f}%)')
        print(f'失败：{self.stats["failed"]} 只 ({self.stats["failed"]/self.stats["total"]*100:.1f}%)')
        print()
        
        duration = self.stats['end_time'] - self.stats['start_time']
        print(f'耗时：{duration.total_seconds():.1f} 秒 ({duration})')
        print()
        print(f'缓存目录：{self.cache_dir}')
        print()
    
    def _save_stats(self):
        """保存统计信息"""
        stats_file = self.log_dir / 'scan_stats.json'
        
        stats = {
            **self.stats,
            'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
            'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None,
        }
        
        # 读取历史统计
        history = []
        if stats_file.exists():
            try:
                with open(stats_file, 'r') as f:
                    history = json.load(f)
            except:
                history = []
        
        # 添加新统计
        history.append(stats)
        
        # 只保留最近 30 次
        history = history[-30:]
        
        # 保存
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='A 股历史行情自动轮询')
    parser.add_argument('--force', action='store_true', help='强制更新 (忽略缓存)')
    parser.add_argument('--max', type=int, help='最大扫描数量 (测试用)')
    parser.add_argument('--cache-dir', type=str, help='缓存目录')
    
    args = parser.parse_args()
    
    scanner = StockHistoryScanner(cache_dir=args.cache_dir)
    scanner.scan_all(force=args.force, max_stocks=args.max)


if __name__ == '__main__':
    main()
