#!/usr/bin/env python3
"""
东方财富个股资金流历史数据获取和分析工具

使用方法：
1. 直接调用 API 获取数据
2. 或从保存的 JSON 文件解析

API 格式：
https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?lmt=30&klt=101&secid=0.{code}&fields1=f1,f2,f3,f4,f5&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63&ut=b2884a393a59ad6400f92eafb616aab8

数据格式 (每行)：
日期,主力净流入,超大单净流入,大单净流入,中单净流入,小单净流入,主力占比,超大单占比,大单占比,中单占比,小单占比,收盘价,涨跌幅
"""

import json
from datetime import datetime


def parse_flow_data(klines: list) -> list:
    """解析资金流 K 线数据"""
    result = []
    
    for line in klines:
        parts = line.split(',')
        if len(parts) >= 13:
            try:
                item = {
                    '日期': parts[0],
                    '收盘价': float(parts[11]) if parts[11] != '-' else 0,
                    '涨跌幅': float(parts[12]) if parts[12] != '-' else 0,
                    '主力净流入': float(parts[1]) if parts[1] != '-' else 0,
                    '超大单净流入': float(parts[2]) if parts[2] != '-' else 0,
                    '大单净流入': float(parts[3]) if parts[3] != '-' else 0,
                    '中单净流入': float(parts[4]) if parts[4] != '-' else 0,
                    '小单净流入': float(parts[5]) if parts[5] != '-' else 0,
                    '主力净流入占比': float(parts[6]) if parts[6] != '-' else 0,
                }
                result.append(item)
            except ValueError as e:
                print(f"解析错误：{e}")
    
    return result


def analyze_flow_data(data: list, code: str) -> dict:
    """分析资金流数据"""
    if not data:
        return {}
    
    # 主力净流入统计
    main_flows = [d['主力净流入'] / 100000000 for d in data]  # 元转亿元
    
    analysis = {
        'code': code,
        'days': len(data),
        'total_main': sum(main_flows),
        'avg_main': sum(main_flows) / len(main_flows),
        'positive_days': sum(1 for x in main_flows if x > 0),
        'negative_days': sum(1 for x in main_flows if x < 0),
        'recent_5d': sum(main_flows[:5]),
        'latest': {
            'date': data[0]['日期'],
            'main_flow': main_flows[0],
            'main_pct': data[0]['主力净流入占比'],
            'close': data[0]['收盘价'],
            'change': data[0]['涨跌幅']
        }
    }
    
    # 判断资金趋势
    if analysis['recent_5d'] > 0:
        analysis['trend'] = '主力近期流入'
    else:
        analysis['trend'] = '主力近期流出'
    
    return analysis


def print_flow_report(data: list, code: str):
    """打印资金流报告"""
    print(f"\n{'='*80}")
    print(f"  {code} 资金流历史数据 ({len(data)}天)")
    print(f"{'='*80}")
    
    for item in data:
        main_flow = item['主力净流入'] / 100000000
        flow_icon = "🟢" if main_flow > 0 else "🔴"
        print(f"{item['日期']} | 收盘:{item['收盘价']:>7.2f} | 涨跌:{item['涨跌幅']:>5.1f}% | {flow_icon}主力:{main_flow:>6.2f}亿 ({item['主力净流入占比']:>5.1f}%)")
    
    print(f"{'='*80}")
    
    # 统计
    analysis = analyze_flow_data(data, code)
    if analysis:
        print(f"\n📊 统计分析:")
        print(f"   主力总净流入: {analysis['total_main']:.2f}亿元")
        print(f"   日均主力净流入: {analysis['avg_main']:.2f}亿元")
        print(f"   流入天数: {analysis['positive_days']}天 | 流出天数: {analysis['negative_days']}天")
        print(f"   最近5天: {analysis['recent_5d']:.2f}亿元")
        print(f"   资金趋势: {analysis['trend']}")


if __name__ == "__main__":
    # 示例数据 (天赐材料 30天)
    sample_data = [
        "2026-04-15,-175753696,185339104,-9585408,-159035616,-16718080,-2.92,3.08,-0.16,-2.64,-0.28,48.00,-2.74",
        "2026-04-14,711423728,-417487312,-293936432,220376944,491046784,11.62,-6.82,-4.80,3.60,8.02,49.35,5.65",
        "2026-04-13,86448624,-88370672,1922064,33048416,53400208,1.64,-1.68,0.04,0.63,1.02,46.71,-0.02",
        "2026-04-10,262610960,-272050784,9439808,8458752,254152208,3.75,-3.89,0.13,0.12,3.63,46.72,6.45",
        "2026-04-09,-330169408,247912624,82256768,-205719776,-124449632,-9.20,6.90,2.29,-5.73,-3.47,43.89,-2.42",
    ]
    
    parsed = parse_flow_data(sample_data)
    print_flow_report(parsed, "002709")