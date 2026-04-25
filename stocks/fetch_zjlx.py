#!/usr/bin/env python3
"""
资金流数据获取脚本 V3 - 增强版
==============================

功能：
1. 获取东方财富资金流排行数据
2. 多 API 端点 fallback
3. 自动重试 + 缓存降级
4. 数据验证 + 异常检测
5. 支持多种输出格式

使用方法:
    python3 fetch_zjlx.py              # 获取并保存
    python3 fetch_zjlx.py --json       # 输出 JSON
    python3 fetch_zjlx.py --top 10     # 仅显示 TOP 10
    python3 fetch_zjlx.py --latest     # 显示上次获取的数据
    python3 fetch_zjlx.py --validate   # 验证数据完整性
"""

import json
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

# 配置
DATA_DIR = Path(__file__).parent / "data"
API_URLS = [
    "https://push2.eastmoney.com/api/qt/clist/get",
    "https://push2his.eastmoney.com/api/qt/clist/get",
]
DEFAULT_FIELDS = "f2,f3,f12,f14,f62,f184,f185,f186,f187,f188,f189,f190,f191,f192"
FS_FILTER = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"

# 数据验证阈值
VALIDATION_RULES = {
    "min_stocks": 10,          # 最少股票数
    "max_price": 10000,        # 最高价格（排除异常值）
    "max_change_pct": 100,     # 最大涨跌幅（排除异常值）
    "min_main_inflow": -100,   # 最小主力净流入（排除异常值）
}


def parse_amount(text: str) -> float:
    """解析金额字符串为亿元"""
    if not text:
        return 0.0
    text = text.strip()
    try:
        if "亿" in text:
            return round(float(text.replace("亿", "")), 2)
        elif "万" in text:
            return round(float(text.replace("万", "")) / 10000, 2)
        return round(float(text), 2)
    except:
        return 0.0


def parse_pct(text: str) -> float:
    """解析百分比"""
    if not text:
        return 0.0
    try:
        return round(float(text.replace("%", "")), 2)
    except:
        return 0.0


def validate_data(data: dict) -> dict:
    """验证数据完整性"""
    stocks = data.get("data", [])
    if not stocks:
        return {"valid": False, "reason": "数据为空"}
    
    if len(stocks) < VALIDATION_RULES["min_stocks"]:
        return {"valid": False, "reason": f"股票数不足 ({len(stocks)} < {VALIDATION_RULES['min_stocks']})"}
    
    # 检查异常值
    anomalies = []
    for s in stocks:
        if s.get("price", 0) > VALIDATION_RULES["max_price"]:
            anomalies.append(f"{s['name']} 价格异常: {s['price']}")
        if abs(s.get("change_pct", 0)) > VALIDATION_RULES["max_change_pct"]:
            anomalies.append(f"{s['name']} 涨跌幅异常: {s['change_pct']}%")
    
    result = {
        "valid": len(anomalies) == 0,
        "total": len(stocks),
        "anomalies": anomalies[:10],  # 最多返回 10 个异常
    }
    
    return result


def fetch_zjlx_data(count: int = 50, timeout: int = 15, max_retries: int = 3) -> dict:
    """获取资金流排行数据（多端点 + 重试）"""
    params = {
        "fid": "f62",
        "po": "1",
        "pz": str(count),
        "pn": "1",
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fs": FS_FILTER,
        "fields": DEFAULT_FIELDS,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://data.eastmoney.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }

    print(f"📡 正在获取东方财富资金流排行数据...")
    print(f"   目标: {count} 只股票")

    last_error = None
    data = None
    
    # 尝试多个 API 端点
    for api_url in API_URLS:
        print(f"   尝试: {api_url}")
        
        for attempt in range(max_retries):
            try:
                resp = requests.get(api_url, params=params, headers=headers, timeout=timeout)
                resp.raise_for_status()
                data = resp.json()
                
                if data.get("data") and data["data"].get("diff"):
                    print(f"   ✅ 成功: {len(data['data']['diff'])} 只股票")
                    break
                else:
                    last_error = "数据为空"
                    
            except Exception as e:
                last_error = str(e)
                print(f"   ❌ 失败: {e}")
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                print(f"   ⏳ 等待 {wait_time}s 后重试...")
                time.sleep(wait_time)
        
        if data and data.get("data") and data["data"].get("diff"):
            break
    
    if not data or not data.get("data") or not data["data"].get("diff"):
        print(f"\n❌ 所有端点均失败: {last_error}")
        return {"success": False, "error": str(last_error)}

    stocks = data["data"]["diff"]
    print(f"\n✅ 获取成功: {len(stocks)} 只股票")

    result = []
    for i, s in enumerate(stocks[:count]):
        item = {
            "rank": i + 1,
            "code": str(s.get("f12", "")),
            "name": str(s.get("f14", "")),
            "price": round((s.get("f2", 0) or 0) / 100, 2),
            "change_pct": round((s.get("f3", 0) or 0) / 100, 2),
            "main_net_inflow": round((s.get("f62", 0) or 0) / 100000000, 2),
            "main_net_pct": round((s.get("f184", 0) or 0) / 10000, 2),
            "super_large_net": round((s.get("f185", 0) or 0) / 100000000, 2),
            "super_large_pct": round((s.get("f186", 0) or 0) / 10000, 2),
            "large_net": round((s.get("f187", 0) or 0) / 100000000, 2),
            "large_pct": round((s.get("f188", 0) or 0) / 10000, 2),
            "medium_net": round((s.get("f189", 0) or 0) / 100000000, 2),
            "medium_pct": round((s.get("f190", 0) or 0) / 10000, 2),
            "small_net": round((s.get("f191", 0) or 0) / 100000000, 2),
            "small_pct": round((s.get("f192", 0) or 0) / 10000, 2),
        }
        result.append(item)

    return {
        "success": True,
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(result),
        "data": result,
    }


def analyze_data(result: dict, top_n: int = 20) -> dict:
    """分析资金流数据"""
    stocks = result.get("data", [])
    if not stocks:
        return {}

    top = stocks[:top_n]

    # 行业板块识别
    lithium_names = ["多氟多", "天齐锂业", "赣锋锂业", "恩捷股份", "华友钴业", "天赐材料",
                     "盛新锂能", "璞泰来", "融捷股份", "亿纬锂能", "西藏珠峰", "盐湖股份",
                     "江特电机", "天华新能"]
    tech_names = ["海光信息", "中芯国际", "中科曙光", "拓维信息", "通富微电", "华虹公司",
                  "富瀚微", "浪潮信息", "长电科技", "华丰科技", "仕佳光子", "C盛合",
                  "盛科通信", "豪威集团", "江波龙", "协创数据"]
    consumer_names = ["贵州茅台", "五粮液", "泸州老窖", "伊利股份", "海天味业", "中国中免"]
    financial_names = ["招商银行", "平安银行", "中信证券", "华泰证券", "东方财富"]

    industry_groups = {}
    for s in top:
        if s["name"] in lithium_names:
            key = "锂电/新能源"
        elif s["name"] in tech_names:
            key = "科技/芯片"
        elif s["name"] in consumer_names:
            key = "消费"
        elif s["name"] in financial_names:
            key = "金融"
        else:
            key = "其他"

        if key not in industry_groups:
            industry_groups[key] = {"count": 0, "stocks": [], "inflow": 0}
        industry_groups[key]["count"] += 1
        industry_groups[key]["stocks"].append(f'{s["name"]}({s["code"]})')
        industry_groups[key]["inflow"] = round(industry_groups[key]["inflow"] + s["main_net_inflow"], 2)

    # 高占比 (>20%)
    high_ratio = [s for s in top if s["main_net_pct"] > 20]

    # 涨停
    limit_up = [s for s in top if s["change_pct"] >= 9.9]

    return {
        "fetch_time": result.get("update_time", ""),
        "top_n": top_n,
        "top_total_inflow": round(sum(s["main_net_inflow"] for s in top), 2),
        "high_ratio_stocks": [{"name": s["name"], "code": s["code"], "pct": s["main_net_pct"]} for s in high_ratio],
        "limit_up_stocks": [{"name": s["name"], "code": s["code"], "pct": s["change_pct"]} for s in limit_up],
        "industry_groups": industry_groups,
    }


def print_summary(result: dict, analysis: dict):
    """打印摘要"""
    print("\n" + "=" * 70)
    print(f"📊 主力资金流排行 TOP {analysis.get('top_n', 20)}")
    print("=" * 70)
    print(f"更新时间: {result.get('update_time', '')}")
    print(f"总记录: {result.get('total', 0)} 只")
    print(f"TOP{analysis.get('top_n', 20)} 总流入: {analysis.get('top_total_inflow', 0)} 亿")
    print("-" * 70)

    header = "{:<4} {:<8} {:<12} {:>8} {:>8} {:>12} {:>8}".format(
        "排名", "代码", "名称", "现价", "涨跌%", "主力净流入", "净占比")
    print(header)
    print("-" * 70)

    for item in result["data"][:analysis.get("top_n", 20)]:
        line = "{:<4} {:<8} {:<12} {:>8.2f} {:>7.2f}% {:>11.2f}亿 {:>7.2f}%".format(
            item["rank"], item["code"], item["name"], item["price"],
            item["change_pct"], item["main_net_inflow"], item["main_net_pct"])
        print(line)

    # 行业板块分析
    industry = analysis.get("industry_groups", {})
    if industry:
        print(f"\n🔥 热门板块分析:")
        for sector, info in sorted(industry.items(), key=lambda x: -x[1]["inflow"]):
            if sector == "其他":
                continue
            print(f"  {sector}板块: {info['count']} 只上榜, 总流入 {info['inflow']:.2f} 亿")
            for stock in info["stocks"][:5]:
                s = next((x for x in result["data"] if x["name"] in stock), None)
                if s:
                    print(f"    - {s['name']}({s['code']}): {s['main_net_inflow']:.2f}亿 ({s['main_net_pct']:.2f}%)")

    # 高占比信号
    high = analysis.get("high_ratio_stocks", [])
    if high:
        print(f"\n🟢 强烈买入信号（主力占比>20%）:")
        for s in high:
            print(f"  • {s['name']}({s['code']}): {s['pct']:.2f}%")

    # 涨停
    limit = analysis.get("limit_up_stocks", [])
    if limit:
        print(f"\n🚀 涨停股: {', '.join(s['name'] for s in limit)}")

    print("\n" + "=" * 70)


def save_result(result: dict, analysis: dict) -> str:
    """保存结果"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"zjlx_ranking_{date_str}.json"
    filepath = DATA_DIR / filename

    output = {
        "update_time": result.get("update_time", ""),
        "total": result.get("total", 0),
        "analysis": analysis,
        "data": result["data"],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 同时保存为 latest
    latest_path = DATA_DIR / "zjlx_ranking_latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ 数据已保存: {filepath}")
    print(f"✅ 最新数据: {latest_path}")
    return str(filepath)


def load_latest() -> dict:
    """加载上次获取的数据"""
    latest_path = DATA_DIR / "zjlx_ranking_latest.json"
    if not latest_path.exists():
        return None
    with open(latest_path, encoding="utf-8") as f:
        return json.load(f)


def validate_command(args):
    """验证数据完整性"""
    data = load_latest()
    if not data:
        print("❌ 没有找到数据文件")
        return 1
    
    print("📋 数据验证报告")
    print("=" * 50)
    print(f"更新时间: {data.get('update_time', '')}")
    print(f"股票数: {data.get('total', 0)}")
    
    result = {"data": data["data"]}
    validation = validate_data(result)
    
    if validation["valid"]:
        print(f"✅ 数据验证通过")
    else:
        print(f"❌ 数据验证失败: {validation['reason']}")
    
    if validation.get("anomalies"):
        print(f"\n⚠️ 异常值 ({len(validation['anomalies'])} 个):")
        for anomaly in validation["anomalies"]:
            print(f"  - {anomaly}")
    
    return 0


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="主力资金流排行自动获取 V3")
    parser.add_argument("--top", type=int, default=20, help="显示 TOP N (默认 20)")
    parser.add_argument("--count", type=int, default=50, help="获取数量 (默认 50)")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--no-save", action="store_true", help="不保存文件")
    parser.add_argument("--latest", action="store_true", help="显示上次获取的数据")
    parser.add_argument("--validate", action="store_true", help="验证数据完整性")
    parser.add_argument("--timeout", type=int, default=15, help="请求超时秒数 (默认 15)")
    parser.add_argument("--retries", type=int, default=3, help="最大重试次数 (默认 3)")

    args = parser.parse_args()

    # 验证数据
    if args.validate:
        return validate_command(args)

    # 查看上次数据
    if args.latest:
        data = load_latest()
        if not data:
            print("❌ 没有找到上次获取的数据")
            return 1
        result = {"data": data["data"], "update_time": data["update_time"], "total": data["total"]}
        analysis = analyze_data(result, top_n=args.top)
        print_summary(result, analysis)
        return 0

    # 获取新数据
    result = fetch_zjlx_data(count=args.count, timeout=args.timeout, max_retries=args.retries)
    if not result.get("success"):
        print("❌ 获取失败:", result.get("error"))
        # 尝试加载缓存
        cached = load_latest()
        if cached:
            print("⚠️ 使用缓存数据...")
            result = {"data": cached["data"], "update_time": cached["update_time"], "total": cached["total"]}
        else:
            return 1

    # 验证数据
    if isinstance(result, dict) and "data" in result:
        validation = validate_data(result)
        if not validation.get("valid", True):
            print(f"⚠️ 数据验证警告: {validation.get('reason', '未知问题')}")
        elif validation.get("anomalies"):
            print(f"⚠️ 发现 {len(validation['anomalies'])} 个异常值")

    # 分析
    analysis = analyze_data(result, top_n=args.top)

    # 保存
    if not args.no_save:
        save_result(result, analysis)

    # 输出
    if args.json:
        output = {
            "update_time": result.get("update_time", ""),
            "total": result.get("total", 0),
            "analysis": analysis,
            "data": result["data"][:args.top],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_summary(result, analysis)

    return 0


if __name__ == "__main__":
    sys.exit(main())
