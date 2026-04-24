#!/usr/bin/env python3
"""
资金流数据快速更新脚本
使用东方财富 API 直接获取最新资金流排行
"""

import json
import requests
from datetime import datetime
from pathlib import Path

# 配置
DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / f"zjlx_ranking_{datetime.now().strftime('%Y%m%d')}.json"

# 东方财富资金流 API
API_URL = "http://push2.eastmoney.com/api/qt/clist/get"

def fetch_zjlx_ranking():
    """获取资金流排行"""
    print(f"\n{'='*60}")
    print("📊 获取最新资金流排行")
    print(f"{'='*60}")
    
    # 主板股票参数
    params = {
        'pn': 1,
        'pz': 100,  # 取前 100 只
        'po': 1,
        'np': 1,
        'ut': 'bd1d9ddb04089700cf3c27f2672e909d',
        'fltt': 2,
        'invt': 2,
        'fid': 'f62',  # 按主力净流入排名
        'fs': 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23',  # 主板
        'fields': 'f12,f14,f2,f3,f5,f6,f62,f63,f103,f104',
        '_': int(datetime.now().timestamp() * 1000)
    }
    
    try:
        response = requests.get(API_URL, params=params, timeout=10)
        data = response.json()
        
        if data.get('data') and data['data'].get('diff'):
            stocks = data['data']['diff']
            
            print(f"✅ 获取成功：{len(stocks)} 只股票")
            
            # 整理数据
            ranking = []
            for i, stock in enumerate(stocks[:50], 1):
                ranking.append({
                    '序号': i,
                    '代码': stock['f12'],
                    '名称': stock['f14'],
                    '最新价': stock['f2'],
                    '涨跌幅': stock['f3'],
                    '主力净流入_净额': stock['f62'],
                    '主力净流入_净占比': stock['f63'],
                    '超大单净流入_净额': stock.get('f103', 0),
                    '超大单净流入_净占比': stock.get('f104', 0)
                })
            
            # 保存
            DATA_DIR.mkdir(exist_ok=True)
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'total': len(ranking),
                    'ranking': ranking
                }, f, indent=2, ensure_ascii=False)
            
            print(f"💾 已保存：{OUTPUT_FILE}")
            
            # 显示 TOP10
            print(f"\n{'='*60}")
            print("🏆 主力资金流 TOP10")
            print(f"{'='*60}")
            print(f"{'排名':<4} {'代码':<8} {'名称':<12} {'主力净流入':<12} {'净占比':<8}")
            print(f"{'-'*60}")
            
            for s in ranking[:10]:
                net = s['主力净流入_净额'] / 10000  # 万元
                ratio = s['主力净流入_净占比']
                print(f"{s['序号']:<4} {s['代码']:<8} {s['名称']:<12} {net:>10.0f}万 {ratio:>6.2f}%")
            
            print(f"\n{'='*60}")
            return ranking
            
        else:
            print("❌ API 返回数据为空")
            return None
            
    except Exception as e:
        print(f"❌ 获取失败：{e}")
        return None

if __name__ == "__main__":
    fetch_zjlx_ranking()
