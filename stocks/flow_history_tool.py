#!/usr/bin/env python3
"""
东方财富个股资金流历史数据获取工具
基于 https://data.eastmoney.com/zjlx/detail.html 页面数据

使用方法：
python3 flow_history_tool.py <股票代码> [天数]

示例：
python3 flow_history_tool.py 002709 30
python3 flow_history_tool.py 600089 15
"""

import urllib.request
import json
import sys
from datetime import datetime


def get_stock_flow_history(code: str, days: int = 30) -> list:
    """
    获取个股资金流历史数据
    
    参数:
        code: 股票代码 (如 002709, 600089)
        days: 天数 (默认30)
    
    返回:
        资金流历史数据列表
    """
    # 市场代码: 上海=1, 深圳=0, 北京=2
    if code.startswith('6'):
        secid = f"1.{code}"
    elif code.startswith(('0', '3')):
        secid = f"0.{code}"
    else:
        secid = f"2.{code}"
    
    # 东方财富资金流历史 API
    url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
    params = {
        'lmt': str(days),
        'klt': '101',  # 日线
        'secid': secid,
        'fields1': 'f1,f2,f3,f4,f5',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63',
        'ut': 'b2884a393a59ad6400f92eafb616aab8',
    }
    
    query = '&'.join(f"{k}={v}" for k, v in params.items())
    full_url = f"{url}?{query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://data.eastmoney.com/zjlx/',
        'Accept': 'application/json',
    }
    
    try:
        req = urllib.request.Request(full_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            
            if data.get('data') and data['data'].get('klines'):
                klines = data['data']['klines']
                stock_name = data['data'].get('name', code)
                return parse_klines(klines, stock_name)
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    return []


def parse_klines(klines: list, stock_name: str) -> list:
    """解析资金流 K 线数据"""
    result = []
    
    for line in klines:
        parts = line.split(',')
        if len(parts) >= 13:
            try:
                result.append({
                    'name': stock_name,
                    'date': parts[0],
                    'close': float(parts[11]),
                    'change': float(parts[12]),
                    'main_flow': float(parts[1]) / 100000000,  # 元转亿元
                    'super_flow': float(parts[2]) / 100000000,
                    'big_flow': float(parts[3]) / 100000000,
                    'mid_flow': float(parts[4]) / 100000000,
                    'small_flow': float(parts[5]) / 100000000,
                    'main_pct': float(parts[6]),
                    'super_pct': float(parts[7]),
                    'big_pct': float(parts[8]),
                })
            except ValueError:
                continue
    
    return result


def print_flow_report(data: list, code: str):
    """打印资金流报告"""
    if not data:
        print("暂无数据")
        return
    
    name = data[0].get('name', code)
    
    print(f"\n{'='*90}")
    print(f"  {name} ({code}) 资金流历史 ({len(data)}天)")
    print(f"  数据来源: 东方财富网 https://data.eastmoney.com/zjlx/detail.html")
    print(f"{'='*90}")
    print(f"{'日期':<12} {'收盘':>8} {'涨跌%':>7} {'主力净额':>12} {'主力%':>8} {'超大单':>10} {'大单':>10}")
    print("-"*90)
    
    for item in data:
        icon = "🟢" if item['main_flow'] > 0 else "🔴"
        print(f"{item['date']:<12} {item['close']:>7.2f} {item['change']:>6.1f}% {icon}{item['main_flow']:>8.2f}亿 {item['main_pct']:>7.1f}% {item['super_flow']:>8.2f}亿 {item['big_flow']:>8.2f}亿")
    
    print("="*90)
    
    # 统计分析
    total_main = sum(d['main_flow'] for d in data)
    avg_main = total_main / len(data)
    positive = sum(1 for d in data if d['main_flow'] > 0)
    negative = sum(1 for d in data if d['main_flow'] < 0)
    
    print(f"\n📊 统计分析:")
    print(f"   主力总净流入: {total_main:.2f}亿元")
    print(f"   日均主力净流入: {avg_main:.2f}亿元")
    print(f"   流入天数: {positive}天 ({positive/len(data)*100:.1f}%)")
    print(f"   流出天数: {negative}天 ({negative/len(data)*100:.1f}%)")
    
    # 最近5天趋势
    recent = data[:5]
    recent_total = sum(d['main_flow'] for d in recent)
    trend = "🟢 近期流入" if recent_total > 0 else "🔴 近期流出"
    
    print(f"\n   最近5天: {recent_total:.2f}亿元")
    print(f"   资金趋势: {trend}")
    
    for d in recent:
        icon = "🟢" if d['main_flow'] > 0 else "🔴"
        print(f"   {d['date']}: {icon}{d['main_flow']:>6.2f}亿 ({d['main_pct']:>5.1f}%)")


def main():
    if len(sys.argv) < 2:
        print("用法: python3 flow_history_tool.py <股票代码> [天数]")
        print("示例: python3 flow_history_tool.py 002709 30")
        sys.exit(1)
    
    code = sys.argv[1].replace('.SZ', '').replace('.SH', '')
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    print(f"\n📊 获取 {code} 过去 {days} 天资金流数据...")
    
    data = get_stock_flow_history(code, days)
    print_flow_report(data, code)
    
    # 保存数据
    if data:
        import os
        save_dir = "/Users/taopeng/.openclaw/workspace/stocks/data"
        os.makedirs(save_dir, exist_ok=True)
        save_file = f"{save_dir}/flow_{code}_{datetime.now().strftime('%Y%m%d')}.json"
        with open(save_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 数据已保存: {save_file}")
    
    print("\n✅ 完成\n")


if __name__ == "__main__":
    main()