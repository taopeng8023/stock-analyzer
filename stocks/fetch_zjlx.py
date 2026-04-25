#!/usr/bin/env python3
"""
资金流数据获取脚本 V6 - 浏览器自动化增强版
===========================================

只获取、保存、展示资金流数据，不做任何选股或分析。
非交易日自动获取上一个交易日数据（优先 API，浏览器自动化+缓存兜底）。

数据源：东方财富 API + 浏览器自动化
输出：JSON 文件 (data/zjlx_ranking_latest.json + 带时间戳备份)

使用方法:
    python3 fetch_zjlx.py              # 获取并保存 (默认 100 只)
    python3 fetch_zjlx.py --top 20     # 终端显示 TOP 20
    python3 fetch_zjlx.py --json       # 输出原始 JSON
    python3 fetch_zjlx.py --latest     # 显示上次缓存
    python3 fetch_zjlx.py --validate   # 验证数据完整性
"""

import json
import sys
import time
import re
import requests
from datetime import datetime, timedelta
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"

# 实时接口（交易日盘中可用）
API_REALTIME = "https://push2.eastmoney.com/api/qt/clist/get"
# 历史接口（非交易日可查上一个交易日）
API_HISTORY = "https://push2his.eastmoney.com/api/qt/clist/get"

DEFAULT_FIELDS = "f2,f3,f12,f14,f62,f184,f185,f186,f187,f188,f189,f190,f191,f192"
FS_FILTER = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"

# 东方财富网页地址（用于浏览器自动化）
EASTMONEY_URL = "https://data.eastmoney.com/zjlx/detail.html?mkt=hsa&stat=1&order=desc"

# 2026 年中国法定节假日（用于判断非交易日）
HOLIDAYS_2026 = {
    "2026-01-01", "2026-01-02", "2026-01-03",
    "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19",
    "2026-02-20", "2026-02-21", "2026-02-22",
    "2026-04-04", "2026-04-05", "2026-04-06",
    "2026-05-01", "2026-05-02", "2026-05-03",
    "2026-05-04", "2026-05-05",
    "2026-06-22", "2026-06-23", "2026-06-24",
    "2026-10-01", "2026-10-02", "2026-10-03",
    "2026-10-04", "2026-10-05", "2026-10-06", "2026-10-07",
}


# ── 工具函数 ──────────────────────────────────────────
def _is_trading_day(dt):
    """判断是否为交易日"""
    if dt.weekday() >= 5:
        return False
    return dt.strftime("%Y-%m-%d") not in HOLIDAYS_2026


def _get_prev_trading_days(n=10):
    """获取前 N 个交易日日期列表"""
    today = datetime.now().date()
    days = []
    check_date = today
    while len(days) < n:
        check_date -= timedelta(days=1)
        if _is_trading_day(check_date):
            days.append(check_date.strftime("%Y-%m-%d"))
    return days


def _parse_stock(s, rank):
    """将 API 返回的原始数据解析为标准化字典"""
    return {
        "rank": rank,
        "code": str(s.get("f12", "")),
        "name": str(s.get("f14", "")),
        "price": round((s.get("f2", 0) or 0) / 100, 2),
        "change_pct": round((s.get("f3", 0) or 0) / 100, 2),
        "main_net_inflow": round((s.get("f62", 0) or 0) / 1e8, 2),
        "main_net_pct": round((s.get("f184", 0) or 0) / 1e4, 2),
        "super_large_net": round((s.get("f185", 0) or 0) / 1e8, 2),
        "super_large_pct": round((s.get("f186", 0) or 0) / 1e4, 2),
        "large_net": round((s.get("f187", 0) or 0) / 1e8, 2),
        "large_pct": round((s.get("f188", 0) or 0) / 1e4, 2),
        "medium_net": round((s.get("f189", 0) or 0) / 1e8, 2),
        "medium_pct": round((s.get("f190", 0) or 0) / 1e4, 2),
        "small_net": round((s.get("f191", 0) or 0) / 1e8, 2),
        "small_pct": round((s.get("f192", 0) or 0) / 1e4, 2),
    }


def _has_diff(data):
    """检查响应是否包含有效数据"""
    return bool(data and data.get("data") and data["data"].get("diff"))


def _try_fetch(api_url, params, headers, timeout):
    """单次 HTTP 请求，返回 (data, error)"""
    try:
        resp = requests.get(api_url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if _has_diff(data):
            return data, None
        return None, "数据为空"
    except Exception as e:
        return None, str(e)


def _parse_chinese_number(text):
    """解析中文数字（亿/万）为浮点数"""
    text = text.strip()
    if not text:
        return 0.0
    try:
        if "亿" in text:
            return float(text.replace("亿", ""))
        elif "万" in text:
            return float(text.replace("万", "")) / 10000
        else:
            return float(text)
    except:
        return 0.0


def _parse_percentage(text):
    """解析百分比字符串为浮点数"""
    text = text.strip().replace("%", "")
    try:
        return float(text)
    except:
        return 0.0


def fetch_zjlx_from_browser(count=100):
    """
    通过浏览器自动化获取资金流数据（V6 新增）
    当 API 全部失败时作为兜底方案
    
    注意：此功能需要安装 playwright 或 selenium
    安装命令: pip install playwright && playwright install chromium
    """
    try:
        from playwright.sync_api import sync_playwright
        print(f"  🌐 尝试浏览器自动化获取...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(EASTMONEY_URL, wait_until='networkidle', timeout=30000)
            time.sleep(2)  # 等待数据加载
            
            # 提取表格数据
            js_code = """
            (function() {
                var table = document.querySelectorAll('table')[1];
                if (!table) return '[]';
                var rows = table.querySelectorAll('tbody tr');
                var result = [];
                rows.forEach(function(row) {
                    var cells = row.querySelectorAll('td');
                    if (cells.length >= 15) {
                        result.push({
                            code: cells[1].textContent.trim(),
                            name: cells[2].textContent.trim(),
                            price: cells[4].textContent.trim(),
                            changePct: cells[5].textContent.trim(),
                            mainNetInflow: cells[6].textContent.trim(),
                            mainNetInflowPct: cells[7].textContent.trim(),
                            superLargeNetInflow: cells[8].textContent.trim(),
                            superLargeNetInflowPct: cells[9].textContent.trim(),
                            largeNetInflow: cells[10].textContent.trim(),
                            largeNetInflowPct: cells[11].textContent.trim(),
                            mediumNetInflow: cells[12].textContent.trim(),
                            mediumNetInflowPct: cells[13].textContent.trim(),
                            smallNetInflow: cells[14].textContent.trim(),
                            smallNetInflowPct: cells[15].textContent.trim()
                        });
                    }
                });
                return JSON.stringify(result.slice(0, """ + str(count) + """));
            })()
            """
            
            result = page.evaluate(js_code)
            browser.close()
            
            if result and result != '[]':
                browser_data = json.loads(result)
                print(f"  ✅ 浏览器自动化成功: {len(browser_data)}只")
                
                # 转换为标准格式
                stocks = []
                for i, item in enumerate(browser_data[:count]):
                    stock = {
                        "rank": i + 1,
                        "code": item["code"],
                        "name": item["name"],
                        "price": float(item["price"]),
                        "change_pct": _parse_percentage(item["changePct"]),
                        "main_net_inflow": _parse_chinese_number(item["mainNetInflow"]),
                        "main_net_pct": _parse_percentage(item["mainNetInflowPct"]),
                        "super_large_net": _parse_chinese_number(item["superLargeNetInflow"]),
                        "super_large_pct": _parse_percentage(item["superLargeNetInflowPct"]),
                        "large_net": _parse_chinese_number(item["largeNetInflow"]),
                        "large_pct": _parse_percentage(item["largeNetInflowPct"]),
                        "medium_net": _parse_chinese_number(item["mediumNetInflow"]),
                        "medium_pct": _parse_percentage(item["mediumNetInflowPct"]),
                        "small_net": _parse_chinese_number(item["smallNetInflow"]),
                        "small_pct": _parse_percentage(item["smallNetInflowPct"]),
                    }
                    stocks.append(stock)
                
                return {
                    "success": True,
                    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total": len(stocks),
                    "data": stocks,
                    "source": "browser",
                }
            else:
                print(f"  ⚠️ 浏览器自动化返回空数据")
                return None
                
    except ImportError:
        print(f"  ⚠️ 浏览器自动化需要安装 playwright: pip install playwright && playwright install chromium")
        return None
    except Exception as e:
        print(f"  ⚠️ 浏览器自动化失败: {e}")
        return None


# ── 核心：获取数据 ────────────────────────────────────
def fetch_zjlx_data(count=100, timeout=15, max_retries=3):
    """
    获取资金流排行数据。
    策略:
      1. 实时接口（交易日盘中）
      2. 历史接口（非交易日查上一个交易日）
      3. 历史接口 + 往前推日期（最多 10 个交易日）
      4. 浏览器自动化（V6 新增）
      5. 本地缓存（兜底）
    """
    params = {
        "fid": "f62", "po": "1", "pz": str(count), "pn": "1",
        "np": "1", "fltt": "2", "invt": "2",
        "fs": FS_FILTER, "fields": DEFAULT_FIELDS,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://data.eastmoney.com/",
        "Accept": "application/json, text/plain, */*",
    }

    print(f"📡 获取东方财富资金流数据 (目标: {count}只)")
    last_error = None

    # ── 第 1 层: 实时接口 ──
    print(f"  🔍 尝试实时接口...")
    for attempt in range(max_retries):
        data, err = _try_fetch(API_REALTIME, params, headers, timeout)
        if data:
            print(f"  ✅ 实时接口成功: {len(data['data']['diff'])}只")
            return _build_result(data, count)
        last_error = err
        if attempt < max_retries - 1:
            wait = 2 ** attempt
            print(f"  ⏳ {wait}s 后重试...")
            time.sleep(wait)

    print(f"  ⚠️ 实时接口失败: {last_error}")

    # ── 第 2 层: 历史接口（不指定日期，默认返回最新交易日） ──
    print(f"  🔍 尝试历史接口（默认最新交易日）...")
    for attempt in range(2):
        data, err = _try_fetch(API_HISTORY, params, headers, timeout)
        if data:
            print(f"  ✅ 历史接口成功: {len(data['data']['diff'])}只")
            return _build_result(data, count)
        last_error = err
        if attempt == 0:
            time.sleep(1)

    print(f"  ⚠️ 历史接口失败: {last_error}")

    # ── 第 3 层: 历史接口 + 往前推日期 ──
    prev_days = _get_prev_trading_days(10)
    if prev_days:
        print(f"  🔍 尝试历史接口 + 往前推日期 (最多 {len(prev_days)} 个交易日)...")
        for day in prev_days:
            print(f"  📅 {day}...", end=" ")
            day_params = dict(params)
            day_params["date"] = day.replace("-", "")
            data, err = _try_fetch(API_HISTORY, day_params, headers, timeout)
            if data:
                print(f"✅ 成功: {len(data['data']['diff'])}只")
                return _build_result(data, count)
            print(f"失败: {err}")
            time.sleep(0.5)

    # ── 第 4 层: 浏览器自动化 (V6 新增) ──
    browser_result = fetch_zjlx_from_browser(count)
    if browser_result:
        return browser_result

    # ── 第 5 层: 本地缓存（兜底） ──
    cached = load_latest()
    if cached:
        print(f"  ⚠️ API 全部失败，使用缓存 ({cached.get('update_time', '')})")
        return {
            "success": True,
            "update_time": cached.get("update_time", ""),
            "total": cached.get("total", 0),
            "data": cached.get("data", []),
            "source": "cache",
        }

    print(f"  ❌ 无可用数据: {last_error}")
    return {"success": False, "error": str(last_error)}


def _build_result(api_data, count):
    """将 API 响应转换为统一格式"""
    stocks = api_data["data"]["diff"][:count]
    result = [_parse_stock(s, i + 1) for i, s in enumerate(stocks)]
    return {
        "success": True,
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(result),
        "data": result,
        "source": "api",
    }


# ── 数据验证 ──────────────────────────────────────────
def validate_data(data):
    """基础数据验证"""
    stocks = data.get("data", [])
    if not stocks:
        return {"valid": False, "reason": "数据为空"}
    if len(stocks) < 5:
        return {"valid": False, "reason": f"股票数不足 ({len(stocks)})"}

    anomalies = []
    for s in stocks:
        if s.get("price", 0) > 10000:
            anomalies.append(f"{s['name']} 价格异常: {s['price']}")
        if abs(s.get("change_pct", 0)) > 100:
            anomalies.append(f"{s['name']} 涨跌幅异常: {s['change_pct']}%")

    return {
        "valid": len(anomalies) == 0,
        "total": len(stocks),
        "anomalies": anomalies[:10],
    }


# ── 文件操作 ──────────────────────────────────────────
def save_result(result):
    """保存数据（带时间戳备份 + latest 覆盖）"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M")

    output = {
        "update_time": result.get("update_time", ""),
        "total": result.get("total", 0),
        "source": result.get("source", "api"),
        "data": result["data"],
    }

    # 备份
    backup_path = DATA_DIR / f"zjlx_ranking_{date_str}.json"
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # latest
    latest_path = DATA_DIR / "zjlx_ranking_latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  ✅ 已保存: {backup_path}")
    print(f"  ✅ 最新:   {latest_path}")
    return str(backup_path)


def load_latest():
    """加载最新缓存"""
    latest_path = DATA_DIR / "zjlx_ranking_latest.json"
    if not latest_path.exists():
        return None
    with open(latest_path, encoding="utf-8") as f:
        return json.load(f)


# ── 终端展示 ──────────────────────────────────────────
def print_table(result, top_n=20):
    """终端表格展示"""
    stocks = result.get("data", [])[:top_n]
    if not stocks:
        print("  (无数据)")
        return

    print(f"\n{'排名':<4} {'代码':<8} {'名称':<10} {'现价':>8} {'涨跌%':>7} {'主力净流入':>10} {'占比%':>6}")
    print("-" * 60)
    for s in stocks:
        print(f"{s['rank']:<4} {s['code']:<8} {s['name']:<10} "
              f"{s['price']:>8.2f} {s['change_pct']:>+6.2f}% "
              f"{s['main_net_inflow']:>+9.2f}亿 {s['main_net_pct']:>+5.2f}%")
    print()


# ── CLI ───────────────────────────────────────────────
def main():
    import argparse

    parser = argparse.ArgumentParser(description="资金流数据获取 V6")
    parser.add_argument("--count", type=int, default=100, help="获取数量 (默认 100)")
    parser.add_argument("--top", type=int, default=0, help="终端显示 TOP N (默认 0=不显示)")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON")
    parser.add_argument("--no-save", action="store_true", help="不保存文件")
    parser.add_argument("--latest", action="store_true", help="显示上次缓存")
    parser.add_argument("--validate", action="store_true", help="验证数据")
    parser.add_argument("--timeout", type=int, default=15, help="请求超时秒数")
    args = parser.parse_args()

    # 验证
    if args.validate:
        data = load_latest()
        if not data:
            print("❌ 无缓存数据")
            return 1
        v = validate_data(data)
        print(f"更新时间: {data.get('update_time', '')}")
        print(f"股票数:   {data.get('total', 0)}")
        print(f"数据源:   {data.get('source', 'api')}")
        print(f"验证结果: {'✅ 通过' if v['valid'] else '❌ ' + v.get('reason', '')}")
        for a in v.get("anomalies", []):
            print(f"  ⚠️ {a}")
        return 0

    # 查看缓存
    if args.latest:
        data = load_latest()
        if not data:
            print("❌ 无缓存数据")
            return 1
        result = {
            "data": data["data"],
            "update_time": data["update_time"],
            "total": data["total"],
            "source": data.get("source", "api"),
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"更新时间: {result['update_time']}  股票数: {result['total']}  数据源: {result.get('source', 'api')}")
            print_table(result, args.top or 20)
        return 0

    # 获取新数据
    result = fetch_zjlx_data(count=args.count, timeout=args.timeout)
    if not result.get("success"):
        print(f"❌ 获取失败: {result.get('error')}")
        return 1

    # 验证
    v = validate_data(result)
    reason = v.get("reason", "")
    if not v.get("valid", True) and reason:
        print(f"⚠️ 数据异常: {reason}")

    # 保存
    if not args.no_save:
        save_result(result)

    # 输出
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.top > 0:
        print_table(result, args.top)

    return 0


if __name__ == "__main__":
    sys.exit(main())