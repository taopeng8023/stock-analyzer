#!/usr/bin/env python3
"""
东方财富资金流排行API - 正确参数
"""
import requests
import json
from pathlib import Path
from datetime import datetime

print("="*70)
print("获取今日主力资金流排行")
print("="*70)

DATA_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data")
TODAY = datetime.now().strftime("%Y%m%d")

# 东方财富资金流排行 - A股参数
url = "https://push2.eastmoney.com/api/qt/clist/get"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/zjlx/zjlx_list.html"
}

params = {
    "fid": "f62",  # 主力净流入排序
    "po": "1",  # 降序
    "pz": "50",  # 50条数据
    "pn": "1",  # 第1页
    "np": "1",
    "fltt": "2",
    "invt": "2",
    "fs": "b:MK0202,b:MK0203,b:MK0204",  # A股(深A+沪A+创业板)
    "fields": "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f124"
}

try:
    print("\n请求东方财富API...")
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    
    if resp.status_code != 200:
        print(f"HTTP错误: {resp.status_code}")
        exit(1)
    
    data = resp.json()
    
    if data.get("data") and data.get("data").get("diff"):
        items = data["data"]["diff"]
        
        print(f"获取数据: {len(items)}条")
        
        result = []
        
        for i, item in enumerate(items, 1):
            code = item.get("f12", "")
            name = item.get("f14", "")
            
            # 主力净流入(亿元)
            main_flow = item.get("f62", 0)
            if main_flow:
                main_flow = main_flow / 100000000
            
            # 主力占比
            main_pct = item.get("f184", 0)
            if main_pct:
                main_pct = main_pct / 100
            
            # 超大单净流入
            super_flow = item.get("f66", 0)
            if super_flow:
                super_flow = super_flow / 100000000
            
            # 大单净流入
            big_flow = item.get("f69", 0)
            if big_flow:
                big_flow = big_flow / 100000000
            
            # 涨跌幅
            pct_chg = item.get("f3", 0)
            if pct_chg:
                pct_chg = pct_chg / 100
            
            # 收盘价
            close = item.get("f2", 0)
            if close:
                close = close / 100
            
            result.append({
                "排行": i,
                "代码": code,
                "名称": name,
                "收盘价": close,
                "涨跌幅": pct_chg,
                "主力净流入": main_flow,
                "主力占比": main_pct,
                "超大单净流入": super_flow,
                "大单净流入": big_flow
            })
        
        print("\nTOP20 主力资金流入排行:")
        print("-"*70)
        
        for item in result[:20]:
            flow_status = "流入" if item["主力净流入"] > 0 else "流出"
            pct_status = "涨" if item["涨跌幅"] > 0 else "跌"
            
            print(f"\n{item['排行']}. {item['代码']} {item['名称']}")
            print(f"   收盘: ¥{item['收盘价']:.2f} [{pct_status}{item['涨跌幅']:.2f}%]")
            print(f"   主力净流入: {item['主力净流入']:.2f}亿 [{flow_status}]")
            print(f"   主力占比: {item['主力占比']:.2f}%")
            
            # 评级
            if abs(item["主力占比"]) > 20:
                print(f"   评级: ⭐⭐⭐⭐⭐ 主力强势")
            elif abs(item["主力占比"]) > 10:
                print(f"   评级: ⭐⭐⭐⭐ 主力活跃")
            elif abs(item["主力占比"]) > 5:
                print(f"   评级: ⭐⭐⭐ 主力关注")
            else:
                print(f"   评级: ⭐⭐ 一般")
        
        # 保存结果
        output_file = DATA_DIR / f"zjlx_ranking_{TODAY}.json"
        with open(output_file, "w") as f:
            json.dump({
                "date": TODAY,
                "update_time": str(datetime.now()),
                "data": result
            }, f)
        
        print(f"\n保存: {output_file.name}")
        
        # 统计分析
        print("\n" + "="*70)
        print("资金流统计分析")
        print("="*70)
        
        total_main_flow = sum(item["主力净流入"] for item in result)
        avg_main_pct = sum(item["主力占比"] for item in result) / len(result)
        inflow_count = sum(1 for item in result if item["主力净流入"] > 0)
        outflow_count = len(result) - inflow_count
        
        print(f"\nTOP50统计:")
        print(f"  主力总净流入: {total_main_flow:.2f}亿")
        print(f"  平均主力占比: {avg_main_pct:.2f}%")
        print(f"  流入股票数: {inflow_count}只")
        print(f"  流出股票数: {outflow_count}只")
        
    else:
        print("未获取到数据")
        print(f"响应: {data}")

except requests.exceptions.Timeout:
    print("请求超时，请稍后重试")
except requests.exceptions.ConnectionError:
    print("连接错误，可能被限流")
except Exception as e:
    print(f"错误: {e}")

print("\n完成:", datetime.now())