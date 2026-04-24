#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用东方财富 API 获取今日收盘后交易数据（带重试机制）
"""

import json
import time
import random
import requests
from pathlib import Path
from datetime import datetime

# 配置
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
LOG_DIR = Path('/home/admin/.openclaw/workspace/stocks/logs')

# 今日日期
TODAY = datetime.now().strftime('%Y%m%d')

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'http://quote.eastmoney.com/',
}

print("=" * 80)
print("东方财富 今日数据获取（带重试）")
print("=" * 80)
print(f"数据源：东方财富 (免费)")
print(f"目标日期：{TODAY}")
print()

def get_market_quotes(market, page=1, page_size=100, retry=3):
    """获取市场批量行情（带重试）"""
    url = 'http://push2.eastmoney.com/api/qt/clist/get'
    params = {
        'pn': page,
        'pz': page_size,
        'po': '1',
        'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2',
        'invt': '2',
        'fid': 'f3',
        'fs': f'm:{market} t:6,t:80',
        'fields': 'f12,f14,f43,f46,f44,f45,f47,f48,f170,f169'
    }
    
    for i in range(retry):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
            result = resp.json()
            
            if result.get('data') and result['data'].get('diff'):
                return result['data']['diff']
            
            return []
            
        except Exception as e:
            if i < retry - 1:
                wait_time = random.uniform(1, 3)
                time.sleep(wait_time)
            else:
                print(f"    失败：{e}")
                return []
    
    return []


def main():
    start_time = time.time()
    
    success = 0
    exists = 0
    fail = 0
    
    # 获取沪市和深市数据
    for market_name, market_id in [('沪市 A 股', 1), ('深市 A 股', 0)]:
        print(f"获取 {market_name} 数据...")
        
        page = 1
        while True:
            print(f"  页码 {page}...", end=" ")
            quotes = get_market_quotes(market_id, page, 100)
            
            if not quotes:
                print("无数据")
                break
            
            print(f"{len(quotes)} 只")
            
            for quote in quotes:
                code = quote.get('f12', '')
                
                if not code:
                    continue
                
                symbol = code
                filepath = DATA_DIR / f'{symbol}.json'
                
                # 构建数据
                new_data = {
                    '日期': TODAY,
                    '开盘': float(quote.get('f46', 0)) / 100 if quote.get('f46') else 0,
                    '收盘': float(quote.get('f43', 0)) / 100 if quote.get('f43') else 0,
                    '最高': float(quote.get('f44', 0)) / 100 if quote.get('f44') else 0,
                    '最低': float(quote.get('f45', 0)) / 100 if quote.get('f45') else 0,
                    '成交量': int(quote.get('f47', 0)) if quote.get('f47') else 0,
                    '成交额': float(quote.get('f48', 0)) if quote.get('f48') else 0,
                    '涨跌幅': float(quote.get('f170', 0)) / 100 if quote.get('f170') else 0
                }
                
                # 读取现有数据
                if filepath.exists():
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            existing_data = json.load(f)
                        
                        existing_dates = [d['日期'] for d in existing_data]
                        if new_data['日期'] in existing_dates:
                            exists += 1
                            continue
                        
                        existing_data.append(new_data)
                        existing_data.sort(key=lambda x: x['日期'])
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(existing_data, f, ensure_ascii=False, indent=2)
                        
                        success += 1
                        
                    except Exception as e:
                        fail += 1
                else:
                    try:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump([new_data], f, ensure_ascii=False, indent=2)
                        success += 1
                    except:
                        fail += 1
            
            page += 1
            if page > 50:  # 最多 50 页=5000 只
                break
            
            # 随机延迟，避免被封
            time.sleep(random.uniform(0.5, 1.5))
        
        print()
    
    elapsed = time.time() - start_time
    
    print("=" * 80)
    print("执行完成")
    print("=" * 80)
    print(f"   成功更新：{success} 只")
    print(f"   已存在：{exists} 只")
    print(f"   失败：{fail} 只")
    print(f"   总耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
    print("=" * 80)
    
    # 保存报告
    report = {
        'date': TODAY,
        'time': datetime.now().isoformat(),
        'data_source': '东方财富',
        'summary': {
            'success': success,
            'exists': exists,
            'fail': fail
        },
        'elapsed': elapsed
    }
    
    report_file = LOG_DIR / f'update_report_{TODAY}_eastmoney.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 报告已保存：{report_file}")
    print("\n✅ 今日数据获取完成！")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ 执行异常：{e}")
        import traceback
        traceback.print_exc()
