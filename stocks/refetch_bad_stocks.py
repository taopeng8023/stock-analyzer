#!/usr/bin/env python3
"""
重新获取异常股票的历史数据

从 bad_stocks_list.txt 读取 132 只异常股票
使用新浪财经 API 重新获取历史 K 线数据
覆盖保存到 data_tushare/ 目录
"""

import json
import requests
import time
from pathlib import Path
from datetime import datetime

CACHE_DIR = Path('data_tushare')
CACHE_DIR.mkdir(exist_ok=True)


def fetch_sina_history(code: str, days: int = 365):
    """
    新浪财经 - 历史 K 线
    返回完整历史数据列表
    """
    # 确定市场前缀
    if code.startswith('6') or code.startswith('9'):
        prefix = 'sh'
    else:
        prefix = 'sz'
    
    url = "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
    params = {
        'symbol': f'{prefix}{code}',
        'scale': '240',  # 日线
        'datalen': str(days),
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        data = resp.json()
        
        if data and len(data) > 0:
            result = []
            for item in data:
                try:
                    result.append({
                        '日期': item.get('day', ''),
                        '开盘': float(item.get('open', 0)),
                        '收盘': float(item.get('close', 0)),
                        '最高': float(item.get('high', 0)),
                        '最低': float(item.get('low', 0)),
                        '成交量': int(float(item.get('volume', 0))),
                        '成交额': float(item.get('turnover', 0)),
                        '涨跌幅': float(item.get('changepercent', 0)),
                    })
                except (ValueError, TypeError) as e:
                    continue
            
            # 按日期排序
            result.sort(key=lambda x: x['日期'])
            return result
    except Exception as e:
        print(f"[{code}] 失败：{e}")
    
    return None


def validate_data(data):
    """验证数据是否合法"""
    if not data or len(data) < 50:
        return False
    
    # 检查价格是否为正且合理
    for d in data:
        if d['收盘'] <= 0 or d['收盘'] > 10000:
            return False
        if d['最高'] <= 0 or d['最低'] <= 0:
            return False
        if d['最高'] < d['最低']:
            return False
        if d['成交量'] < 0:
            return False
    
    return True


def main():
    # 读取异常股票列表
    bad_stocks_file = Path('bad_stocks_list.txt')
    if not bad_stocks_file.exists():
        print("❌ 未找到 bad_stocks_list.txt")
        return
    
    with open(bad_stocks_file, 'r') as f:
        bad_stocks = [line.strip() for line in f if line.strip()]
    
    print("=" * 80)
    print("🔄 重新获取异常股票历史数据")
    print(f"📅 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print(f"📋 异常股票数量：{len(bad_stocks)}")
    print(f"📁 保存目录：{CACHE_DIR.absolute()}")
    print()
    
    success = 0
    failed = 0
    skipped = 0
    
    for i, code in enumerate(bad_stocks, 1):
        filepath = CACHE_DIR / f'{code}.json'
        
        # 尝试获取新数据
        print(f"[{i:3d}/{len(bad_stocks)}] {code} ...", end=" ", flush=True)
        
        data = fetch_sina_history(code, days=365)
        
        if data and validate_data(data):
            # 备份旧数据
            if filepath.exists():
                backup_path = filepath.with_suffix('.json.bad')
                filepath.rename(backup_path)
            
            # 保存新数据
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 成功 ({len(data)}条)")
            success += 1
        else:
            if data:
                print(f"⚠️  数据异常 (已跳过)")
            else:
                print(f"❌ 失败")
            failed += 1
        
        # 每 10 只股票暂停一下
        if i % 10 == 0:
            time.sleep(0.5)
    
    print()
    print("=" * 80)
    print("✅ 完成")
    print(f"   成功：{success} 只")
    print(f"   失败：{failed} 只")
    print(f"   跳过：{skipped} 只")
    print("=" * 80)


if __name__ == '__main__':
    main()
