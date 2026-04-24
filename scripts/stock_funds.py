#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票资金流数据获取脚本
使用东方财富 API，无需 API Key
"""

import requests
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Optional

# 东方财富资金流 API（使用 HTTPS）
FFLOW_API = "https://push2.eastmoney.com/api/qt/stock/fflow/daykline/get"
FFLOW_PARAMS = {
    "lmt": 0,
    "klt": 1,
    "fields1": "f1,f2,f3,f7",
    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
    "ut": "b2884a393a59ad64002292a3e90d46a5"
}

# 请求头（模拟浏览器）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "http://quote.eastmoney.com/",
    "Accept": "application/json"
}

# 股票池（51 只）
STOCK_POOL = [
    "002475", "300308", "300383", "300394", "600487", "600549", "688781", "688525",
    "301682", "603601", "002281", "600498", "600111", "600589", "601869", "000988",
    "002428", "601899", "600522", "688521", "300017", "603986", "688313", "002371",
    "601985", "002460", "002467", "603618", "600157", "603799", "603993", "300763",
    "000592", "601138", "300136", "300548", "688041", "000426", "688167", "300751",
    "002466", "002580", "600726", "000690", "600011", "002353", "000960", "300442",
    "603179", "600875"
]

def get_secid(code: str) -> str:
    """获取证券 ID（1=沪市，0=深市）"""
    if code.startswith("6") or code.startswith("9"):
        return f"1.{code}"  # 沪市
    elif code.startswith("0") or code.startswith("3"):
        return f"0.{code}"  # 深市
    elif code.startswith("4") or code.startswith("8"):
        return f"0.{code}"  # 北交所
    else:
        return f"1.{code}"

def fetch_funds(code: str, retry: int = 3) -> Optional[Dict]:
    """获取单只股票资金流数据"""
    for attempt in range(retry):
        try:
            params = FFLOW_PARAMS.copy()
            params["secid"] = get_secid(code)
            
            resp = requests.get(FFLOW_API, params=params, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("rc") == 0 and data.get("data"):
                klines = data["data"].get("klines", [])
                if klines:
                    latest = klines[-1].split(",")
                    return {
                        "code": code,
                        "name": data["data"].get("name", ""),
                        "date": latest[0],
                        "main_net_inflow": float(latest[1]) / 10000,
                        "small_net_inflow": float(latest[2]) / 10000,
                        "medium_net_inflow": float(latest[3]) / 10000,
                        "large_net_inflow": float(latest[4]) / 10000,
                        "super_large_net_inflow": float(latest[5]) / 10000,
                        "main_net_ratio": float(latest[6]),
                        "small_ratio": float(latest[7]),
                        "medium_ratio": float(latest[8]),
                        "large_ratio": float(latest[9]),
                        "super_large_ratio": float(latest[10]),
                    }
            time.sleep(0.3)  # 请求间隔
            break
        except Exception as e:
            if attempt < retry - 1:
                print(f"  Retry {attempt+1}/{retry} for {code}...")
                time.sleep(1)
            else:
                print(f"Error fetching {code}: {e}")
    return None

def fetch_all_funds(codes: List[str]) -> List[Dict]:
    """批量获取资金流数据"""
    results = []
    for i, code in enumerate(codes):
        print(f"[{i+1}/{len(codes)}] Fetching {code}...")
        data = fetch_funds(code)
        if data:
            results.append(data)
    return results

def calculate_fund_score(funds: Dict) -> float:
    """计算资金流评分（0-20 分）"""
    score = 10.0  # 基础分
    
    # 主力净流入占比评分（最高 +5 分）
    main_ratio = funds.get("main_net_ratio", 0)
    if main_ratio > 5:
        score += 5
    elif main_ratio > 2:
        score += 3
    elif main_ratio > 0:
        score += 1
    elif main_ratio < -5:
        score -= 5
    elif main_ratio < -2:
        score -= 3
    elif main_ratio < 0:
        score -= 1
    
    # 超大单净流入评分（最高 +5 分）
    super_ratio = funds.get("super_large_ratio", 0)
    if super_ratio > 3:
        score += 5
    elif super_ratio > 1:
        score += 3
    elif super_ratio > 0:
        score += 1
    elif super_ratio < -3:
        score -= 5
    elif super_ratio < -1:
        score -= 3
    
    return max(0, min(20, score))

def main():
    """主函数"""
    print("=" * 60)
    print("股票资金流数据获取")
    print("=" * 60)
    
    # 获取资金流数据
    funds_data = fetch_all_funds(STOCK_POOL)
    
    # 计算评分并排序
    for item in funds_data:
        item["fund_score"] = calculate_fund_score(item)
    
    # 按评分排序
    sorted_funds = sorted(funds_data, key=lambda x: x["fund_score"], reverse=True)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("资金流评分 TOP 10")
    print("=" * 60)
    print(f"{'排名':<4} {'代码':<8} {'名称':<10} {'主力净流入 (万)':<14} {'主力占比':<8} {'评分':<6}")
    print("-" * 60)
    
    for i, item in enumerate(sorted_funds[:10], 1):
        print(f"{i:<4} {item['code']:<8} {item['name']:<10} {item['main_net_inflow']:<14.1f} {item['main_net_ratio']:<8.2f}% {item['fund_score']:<6.1f}")
    
    # 保存结果
    output_dir = "/home/admin/.openclaw/workspace/data"
    os.makedirs(output_dir, exist_ok=True)
    output_file = "{}/funds_{}.json".format(
        output_dir,
        datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(sorted_funds, f, ensure_ascii=False, indent=2)
    
    print(f"\n数据已保存至：{output_file}")
    return sorted_funds

if __name__ == "__main__":
    main()
