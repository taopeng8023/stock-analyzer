#!/usr/bin/env python3
"""
主板资金流排行获取脚本 - 浏览器版
通过 OpenClaw 浏览器服务获取东方财富资金流数据
支持自动化选股系统集成

使用方法:
1. CLI调用: python3 zjlx_browser_fetcher.py --top 20
2. 集成调用: from zjlx_browser_fetcher import fetch_zjlx_ranking
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 配置
BROWSER_PROFILE = "openclaw"
BROWSER_CONTROL_URL = "http://127.0.0.1:18791"
ZJLX_URL = "https://data.eastmoney.com/zjlx/detail.html"
DATA_DIR = Path(__file__).parent / "data"


class BrowserFetcher:
    """浏览器数据获取器"""
    
    def __init__(self):
        self.browser_started = False
    
    def start_browser(self) -> bool:
        """启动浏览器服务"""
        try:
            result = subprocess.run(
                ["openclaw", "browser", "start"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                self.browser_started = True
                time.sleep(2)  # 等待浏览器初始化
                return True
            print(f"启动浏览器失败: {result.stderr}")
            return False
        except Exception as e:
            print(f"启动浏览器异常: {e}")
            return False
    
    def stop_browser(self):
        """关闭浏览器"""
        if self.browser_started:
            subprocess.run(["openclaw", "browser", "stop"], capture_output=True)
            self.browser_started = False
    
    def open_page(self, url: str) -> bool:
        """打开页面"""
        # 使用 canvas 或 exec 调用浏览器 API
        # 这里简化为返回 True，实际由 OpenClaw 工具调用
        return True
    
    def fetch_table_data(self) -> list:
        """获取表格数据 - 返回解析后的列表"""
        # 这个方法由外部工具（browser tool）实际执行
        # 返回空列表，实际数据通过 browser action 获取
        return []


def parse_raw_data(raw_text: str) -> list:
    """解析原始表格文本数据"""
    data = []
    lines = raw_text.strip().split('\n')
    
    for line in lines:
        if not line.strip():
            continue
        
        parts = line.split('|')
        if len(parts) < 6:
            continue
        
        try:
            item = {
                "序号": int(parts[0]) if parts[0].isdigit() else 0,
                "代码": parts[1],
                "名称": parts[2].split(' ')[0] if ' ' in parts[2] else parts[2],
                "最新价": parts[3],
                "涨跌幅": parts[4],
                "主力净流入_净额": parts[5] if len(parts) > 5 else "",
                "主力净流入_净占比": parts[6] if len(parts) > 6 else "",
                "超大单净流入_净额": parts[7] if len(parts) > 7 else "",
                "超大单净流入_净占比": parts[8] if len(parts) > 8 else "",
            }
            
            # 清理数据
            item["名称"] = item["名称"].replace("详情", "").replace("数据", "").replace("股吧", "").strip()
            
            # 提取金额数值
            item["主力净流入_金额"] = parse_amount(item["主力净流入_净额"])
            
            data.append(item)
        except Exception as e:
            print(f"解析行失败: {line}, {e}")
            continue
    
    return data


def parse_amount(text: str) -> float:
    """解析金额文本为数值（亿元）"""
    if not text:
        return 0.0
    
    text = text.strip()
    
    try:
        if "亿" in text:
            return float(text.replace("亿", "").replace("-", ""))
        elif "万" in text:
            return float(text.replace("万", "").replace("-", "")) / 10000
        else:
            return float(text)
    except:
        return 0.0


def analyze_zjlx_data(data: list, top_n: int = 20) -> dict:
    """分析资金流数据"""
    
    if not data:
        return {"error": "无数据"}
    
    # 取前N条
    top_data = data[:top_n]
    
    # 统计
    total_inflow = sum(d["主力净流入_金额"] for d in top_data)
    
    # 高占比股票（主力占比>20%）
    high_ratio = [
        d for d in top_data 
        if d.get("主力净流入_净占比") and parse_ratio(d["主力净流入_净占比"]) > 20
    ]
    
    # 涨停股
    limit_up = [
        d for d in top_data
        if d.get("涨跌幅") and "10" in d["涨跌幅"]
    ]
    
    # 按板块分类（简化）
    sectors = {}
    for d in top_data:
        # 根据代码判断板块
        code = d["代码"]
        if code.startswith("688"):
            sector = "科创板"
        elif code.startswith("300"):
            sector = "创业板"
        elif code.startswith("00"):
            sector = "深市主板"
        elif code.startswith("60"):
            sector = "沪市主板"
        else:
            sector = "其他"
        
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(d["名称"])
    
    return {
        "top_data": top_data,
        "total_inflow": round(total_inflow, 2),
        "high_ratio_count": len(high_ratio),
        "high_ratio_stocks": [d["名称"] for d in high_ratio],
        "limit_up_count": len(limit_up),
        "limit_up_stocks": [d["名称"] for d in limit_up],
        "sectors": sectors,
        "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def parse_ratio(text: str) -> float:
    """解析占比百分比"""
    if not text:
        return 0.0
    try:
        return float(text.replace("%", ""))
    except:
        return 0.0


def save_result(data: list, analysis: dict) -> str:
    """保存结果到文件"""
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"zjlx_ranking_{date_str}.json"
    filepath = DATA_DIR / filename
    
    result = {
        "data": data,
        "analysis": analysis,
        "fetch_time": datetime.now().isoformat(),
        "source": ZJLX_URL
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 数据已保存: {filepath}")
    return str(filepath)


def print_summary(analysis: dict):
    """打印摘要报告"""
    
    print("\n" + "=" * 60)
    print("📊 主板资金流排行分析报告")
    print("=" * 60)
    print(f"分析时间: {analysis['analysis_time']}")
    print(f"TOP20总流入: {analysis['total_inflow']} 亿元")
    print()
    
    print("🟢 强烈买入信号（主力占比>20%）:")
    for stock in analysis['high_ratio_stocks']:
        print(f"  • {stock}")
    print()
    
    print(f"🚀 涨停股数量: {analysis['limit_up_count']}")
    for stock in analysis['limit_up_stocks']:
        print(f"  • {stock}")
    print()
    
    print("📈 板块分布:")
    for sector, stocks in analysis['sectors'].items():
        print(f"  {sector}: {', '.join(stocks)}")
    
    print("\n" + "=" * 60)


def fetch_zjlx_ranking(top_n: int = 20) -> dict:
    """
    主函数 - 获取资金流排行
    
    返回格式:
    {
        "success": True,
        "data": [...],
        "analysis": {...},
        "filepath": "..."
    }
    
    注意: 此函数返回空数据，实际数据需通过 browser tool 获取
    """
    
    # 这个函数作为接口，实际获取由 OpenClaw browser tool 执行
    # 返回提示信息
    return {
        "success": False,
        "message": "请使用 OpenClaw browser tool 获取数据",
        "hint": "browser action=open targetUrl=https://data.eastmoney.com/zjlx/detail.html"
    }


def main():
    """CLI 主函数"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="主板资金流排行获取")
    parser.add_argument("--top", type=int, default=20, help="获取TOP N数据")
    parser.add_argument("--save", action="store_true", help="保存结果到文件")
    parser.add_argument("--analyze", action="store_true", help="仅分析已保存的数据")
    
    args = parser.parse_args()
    
    if args.analyze:
        # 分析已有数据
        date_str = datetime.now().strftime("%Y%m%d")
        filepath = DATA_DIR / f"zjlx_ranking_{date_str}.json"
        
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                result = json.load(f)
            
            if "analysis" in result:
                print_summary(result["analysis"])
            else:
                print("数据文件无分析结果")
        else:
            print(f"数据文件不存在: {filepath}")
        return
    
    print("⚠️ 此脚本需要配合 OpenClaw browser tool 使用")
    print()
    print("使用方法:")
    print("1. 启动浏览器: openclaw browser start")
    print("2. 打开页面: browser action=open targetUrl=" + ZJLX_URL)
    print("3. 等待加载: browser action=act request={\"kind\": \"wait\", \"timeMs\": 3000}")
    print("4. 获取数据: browser action=act request={\"kind\": \"evaluate\", \"fn\": \"...\"}")
    print("5. 解析数据: python3 zjlx_browser_fetcher.py --analyze")
    print()
    print("或直接在 OpenClaw 会话中调用，自动完成上述流程")


if __name__ == "__main__":
    main()