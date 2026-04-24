#!/usr/bin/env python3
"""
资金流数据更新 - 修正版
"""

import json
import requests
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / f"zjlx_ranking_{datetime.now().strftime('%Y%m%d')}.json"

API_URL = "http://push2.eastmoney.com/api/qt/clist/get"

def parse_number(s):
    """解析数字 (处理字符串和空值)"""
    if s is None or s == '' or s == '-':
        return 0
    try:
        return float(s)
    except:
        return 0

def fetch_zjlx_ranking():
    """获取资金流排行"""
    print(f"\n{'='*60}")
    print("📊 获取最新资金流排行 (修正版)")
    print(f"{'='*60}")
    
    params = {
        'pn': 1,
        'pz': 100,
        'po': 1,
        'np': 1,
        'ut': 'bd1d9ddb04089700cf3c27f2672e909d',
        'fltt': 2,
        'invt': 2,
        'fid': 'f62',
        'fs': 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23',
        'fields': 'f12,f14,f2,f3,f5,f6,f62,f63,f103,f104',
        '_': int(datetime.now().timestamp() * 1000)
    }
    
    try:
        response = requests.get(API_URL, params=params, timeout=10)
        data = response.json()
        
        if data.get('data') and data['data'].get('diff'):
            stocks = data['data']['diff']
            
            print(f"✅ 获取成功：{len(stocks)} 只股票")
            
            ranking = []
            for i, stock in enumerate(stocks[:50], 1):
                # 主力净流入 (元转万元)
                main_net = parse_number(stock.get('f62', 0)) / 10000
                super_net = parse_number(stock.get('f103', 0)) / 10000
                
                ranking.append({
                    '序号': i,
                    '代码': stock.get('f12', ''),
                    '名称': stock.get('f14', ''),
                    '最新价': parse_number(stock.get('f2', 0)),
                    '涨跌幅': parse_number(stock.get('f3', 0)),
                    '主力净流入_净额': round(main_net, 2),  # 万元
                    '主力净流入_净占比': parse_number(stock.get('f63', 0)),
                    '超大单净流入_净额': round(super_net, 2),  # 万元
                    '超大单净流入_净占比': parse_number(stock.get('f104', 0))
                })
            
            DATA_DIR.mkdir(exist_ok=True)
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'total': len(ranking),
                    'ranking': ranking
                }, f, indent=2, ensure_ascii=False)
            
            print(f"💾 已保存：{OUTPUT_FILE}")
            
            print(f"\n{'='*60}")
            print("🏆 主力资金流 TOP10 (单位：万元)")
            print(f"{'='*60}")
            print(f"{'排名':<4} {'代码':<8} {'名称':<10} {'净流入':<10} {'占比':<8}")
            print(f"{'-'*60}")
            
            for s in ranking[:10]:
                print(f"{s['序号']:<4} {s['代码']:<8} {s['名称']:<10} {s['主力净流入_净额']:>8.2f} {s['主力净流入_净占比']:>6.2f}%")
            
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
