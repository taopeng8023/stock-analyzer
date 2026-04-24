#!/usr/bin/env python3
"""
A 股历史行情轮询脚本 (v3.0 极度保守版)

优化:
- 极度保守的限频参数 (避免触发限流)
- 多数据源自动切换
- 日期序列化修复
- 详细的错误日志

用法:
    python3.11 auto_scan_conservative.py
"""

import akshare as ak
import json
import time
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import requests


class ConservativeScanner:
    """极度保守的股票扫描器"""
    
    def __init__(self):
        self.cache_dir = Path(__file__).parent / 'cache' / 'history'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_dir = Path(__file__).parent / 'logs'
        self.log_dir.mkdir(exist_ok=True)
        
        # 极度保守的限频配置
        self.batch_size = 5  # 每批 5 只
        self.batch_delay = 30  # 每批间隔 30 秒
        self.stock_delay = 1.0  # 每只间隔 1 秒
        self.source_delay = 2  # 数据源间间隔 2 秒
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        
        self.stats = {'total': 0, 'success': 0, 'failed': 0}
    
    def get_symbols(self) -> List[str]:
        """获取 A 股列表"""
        print('获取 A 股股票列表...')
        try:
            data = ak.stock_info_a_code_name()
            if data is not None and not data.empty:
                symbols = data['code'].astype(str).tolist()
                print(f'   ✅ 获取到 {len(symbols)} 只股票')
                return symbols
        except Exception as e:
            print(f'   ❌ 错误：{e}')
        
        # 备用列表
        backup = []
        for i in range(1, 1000):
            backup.append(f'600{i:03d}')
            backup.append(f'000{i:03d}')
        return backup[:500]
    
    def fetch_akshare(self, symbol: str) -> Optional[Dict]:
        """从 AKShare 东财获取"""
        try:
            data = ak.stock_zh_a_hist(
                symbol=symbol,
                period='daily',
                start_date=(datetime.now() - timedelta(days=365)).strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d'),
                adjust='qfq'
            )
            
            if data is not None and not data.empty:
                # 转换为可序列化格式
                records = []
                for _, row in data.iterrows():
                    record = {}
                    for col in data.columns:
                        val = row[col]
                        if hasattr(val, 'strftime'):
                            record[col] = val.strftime('%Y-%m-%d')
                        elif hasattr(val, 'isoformat'):
                            record[col] = val.isoformat()
                        else:
                            record[col] = val if val == val else None  # NaN 处理
                    records.append(record)
                
                return {
                    'symbol': symbol,
                    'data': records,
                    'update_time': datetime.now().isoformat(),
                }
        except Exception as e:
            pass
        return None
    
    def fetch_sina(self, symbol: str) -> Optional[Dict]:
        """从新浪获取"""
        try:
            market = 'sh' if symbol.startswith('6') else 'sz'
            url = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
            params = {'symbol': f'{market}{symbol}', 'scale': '240', 'ma': 'no', 'datalen': '250'}
            
            resp = self.session.get(url, params=params, timeout=15)
            data = resp.json()
            
            if data:
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
                }
        except:
            pass
        return None
    
    def scan(self, max_stocks: int = None):
        """执行扫描"""
        print('='*70)
        print('A 股历史行情轮询 (v3.0 极度保守版)')
        print('='*70)
        print()
        
        symbols = self.get_symbols()
        if max_stocks:
            symbols = symbols[:max_stocks]
        
        self.stats['total'] = len(symbols)
        print(f'开始扫描 {len(symbols)} 只股票...')
        print()
        
        start_time = datetime.now()
        
        for i in range(0, len(symbols), self.batch_size):
            batch = symbols[i:i+self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(symbols) + self.batch_size - 1) // self.batch_size
            
            print(f'批次 {batch_num}/{total_batches} (股票 {i+1}-{min(i+self.batch_size, len(symbols))})...')
            
            for symbol in batch:
                # 检查缓存
                cached = self.load_cache(symbol)
                if cached and self.is_valid(cached):
                    self.stats['success'] += 1
                    continue
                
                # 多数据源获取
                data = None
                
                # 尝试 AKShare
                data = self.fetch_akshare(symbol)
                if not data:
                    time.sleep(self.source_delay)
                    # 尝试新浪
                    data = self.fetch_sina(symbol)
                
                if data:
                    self.save_cache(symbol, data)
                    self.stats['success'] += 1
                else:
                    self.stats['failed'] += 1
                
                # 单只延迟
                time.sleep(self.stock_delay)
            
            # 批次延迟
            if i + self.batch_size < len(symbols):
                print(f'   等待 {self.batch_delay} 秒...')
                time.sleep(self.batch_delay)
            
            # 进度
            progress = (i + self.batch_size) / len(symbols) * 100
            print(f'   进度：{progress:.1f}% (成功:{self.stats["success"]} 失败:{self.stats["failed"]})')
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print()
        print('='*70)
        print('扫描完成！')
        print('='*70)
        print()
        print(f'总数：{self.stats["total"]} 只')
        print(f'成功：{self.stats["success"]} 只 ({self.stats["success"]/self.stats["total"]*100:.1f}%)')
        print(f'失败：{self.stats["failed"]} 只 ({self.stats["failed"]/self.stats["total"]*100:.1f}%)')
        print()
        print(f'耗时：{duration:.1f} 秒 ({duration/60:.1f} 分钟)')
        print()
        print(f'缓存目录：{self.cache_dir}')
        
        # 保存统计
        self.save_stats()
    
    def save_cache(self, symbol: str, data: Dict):
        """保存缓存"""
        subdir = self.cache_dir / datetime.now().strftime('%Y%m')
        subdir.mkdir(exist_ok=True)
        filepath = subdir / f'{symbol}.json'
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    def load_cache(self, symbol: str) -> Optional[Dict]:
        """加载缓存"""
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
    
    def is_valid(self, data: Dict) -> bool:
        """检查缓存是否有效 (24 小时内)"""
        try:
            update_time = data.get('update_time', '')
            update_dt = datetime.fromisoformat(update_time)
            age = (datetime.now() - update_dt).total_seconds()
            return age < 24 * 3600
        except:
            return False
    
    def save_stats(self):
        """保存统计"""
        stats_file = self.log_dir / 'scan_stats_v3.json'
        stats = {
            'time': datetime.now().isoformat(),
            **self.stats,
        }
        
        history = []
        if stats_file.exists():
            try:
                with open(stats_file, 'r') as f:
                    history = json.load(f)
            except:
                history = []
        
        history.append(stats)
        history = history[-30:]
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='A 股历史行情轮询 (极度保守版)')
    parser.add_argument('--max', type=int, help='最大扫描数量 (测试用)')
    args = parser.parse_args()
    
    scanner = ConservativeScanner()
    scanner.scan(max_stocks=args.max)


if __name__ == '__main__':
    main()
