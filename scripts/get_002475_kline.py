#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取 002475 立讯精密 K 线数据
在本地电脑运行此脚本获取真实 K 线数据
"""

import requests
import json
from datetime import datetime

def get_kline_data(code, name, start_date, end_date):
    """获取 K 线数据"""
    
    # 转换证券 ID
    if code.startswith('6'):
        secid = f'1.{code}'
    else:
        secid = f'0.{code}'
    
    url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
    params = {
        'secid': secid,
        'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'klt': '101',  # 日 K
        'fqt': '1',     # 前复权
        'beg': start_date.replace('-', ''),
        'end': end_date.replace('-', ''),
        'lmt': '300'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://quote.eastmoney.com/'
    }
    
    print(f"📡 正在获取 {name}({code}) 的 K 线数据...")
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        
        data = resp.json()
        
        if not data.get('data') or not data['data'].get('klines'):
            print("❌ 未获取到数据")
            return None
        
        klines = data['data']['klines']
        print(f"✅ 成功获取 {len(klines)} 条 K 线数据")
        
        # 解析数据
        parsed_data = []
        for k in klines:
            f = k.split(',')
            parsed_data.append({
                'date': f[0],
                'open': float(f[1]),
                'close': float(f[2]),
                'high': float(f[3]),
                'low': float(f[4]),
                'volume': int(f[5]),
                'amount': float(f[6]),
                'amplitude': float(f[7]),
                'change_pct': float(f[8]),
                'change': float(f[9]),
                'turnover': float(f[10])
            })
        
        return parsed_data
        
    except Exception as e:
        print(f"❌ 获取失败：{e}")
        return None

def print_kline_table(klines, show_count=30):
    """打印 K 线数据表格"""
    
    print("\n" + "=" * 100)
    print(f"{'日期':<12} {'开盘':<10} {'收盘':<10} {'最高':<10} {'最低':<10} {'成交量':<12} {'成交额 (亿)':<12} {'涨跌幅':<10}")
    print("=" * 100)
    
    # 显示最新数据
    for k in klines[-show_count:]:
        print(f"{k['date']:<12} {k['open']:<10.2f} {k['close']:<10.2f} {k['high']:<10.2f} {k['low']:<10.2f} {k['volume']:<12,} {k['amount']/100000000:<12.2f} {k['change_pct']:>9.2f}%")
    
    print("=" * 100)

def print_statistics(klines):
    """打印统计信息"""
    
    if not klines:
        return
    
    prices = [k['close'] for k in klines]
    highs = [k['high'] for k in klines]
    lows = [k['low'] for k in klines]
    volumes = [k['volume'] for k in klines]
    
    print("\n📊 统计信息")
    print("=" * 50)
    print(f"数据范围：{klines[0]['date']} 至 {klines[-1]['date']}")
    print(f"数据条数：{len(klines)} 条")
    print(f"最高价：{max(highs):.2f} 元")
    print(f"最低价：{min(lows):.2f} 元")
    print(f"最新价：{prices[-1]:.2f} 元")
    print(f"区间涨幅：{(prices[-1] - prices[0]) / prices[0] * 100:.2f}%")
    print(f"平均成交量：{sum(volumes)/len(volumes):,.0f} 手")
    print(f"最大成交量：{max(volumes):,} 手")
    print("=" * 50)

def save_to_file(klines, code, name):
    """保存到文件"""
    
    filename = f"{code}_{name}_kline.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(klines, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 数据已保存至：{filename}")

def main():
    """主函数"""
    
    print("=" * 100)
    print(" " * 35 + "002475 立讯精密 K 线数据获取")
    print("=" * 100)
    
    # 获取一年数据
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = '2025-03-25'
    
    klines = get_kline_data('002475', '立讯精密', start_date, end_date)
    
    if klines:
        # 打印统计信息
        print_statistics(klines)
        
        # 打印最新 30 条数据
        print_kline_table(klines, show_count=30)
        
        # 保存到文件
        save_to_file(klines, '002475', '立讯精密')
        
        # 打印关键价位
        print("\n📈 关键价位")
        print("=" * 50)
        print(f"52 周最高：{max([k['high'] for k in klines]):.2f} 元")
        print(f"52 周最低：{min([k['low'] for k in klines]):.2f} 元")
        print(f"当前价格：{klines[-1]['close']:.2f} 元")
        print(f"今日涨停：{klines[-1]['close'] * 1.1:.2f} 元")
        print("=" * 50)

if __name__ == "__main__":
    main()
