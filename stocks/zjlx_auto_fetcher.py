#!/usr/bin/env python3
"""
资金流排行自动获取脚本 - 集成版
自动启动浏览器、获取数据、分析并保存

集成到选股系统使用方法:
    python3 zjlx_auto_fetcher.py
    
返回 JSON 格式数据供其他脚本使用
"""

import json
import subprocess
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

# 配置
BROWSER_CONTROL_URL = "http://127.0.0.1:18791"
ZJLX_URL = "https://data.eastmoney.com/zjlx/detail.html"
DATA_DIR = Path(__file__).parent / "data"
CDP_PORT = 18800

# JavaScript 提取函数
JS_EXTRACT_TABLE = """
() => {
  const table = document.querySelectorAll('table')[1];
  if (!table) return '表格未找到';
  const rows = table.querySelectorAll('tbody tr');
  const data = [];
  for (let i = 0; i < Math.min(50, rows.length); i++) {
    const cells = rows[i].querySelectorAll('td');
    if (cells.length >= 9) {
      data.push({
        序号: i + 1,
        代码: cells[1]?.innerText?.trim() || '',
        名称: cells[2]?.innerText?.trim().split(' ')[0] || '',
        最新价: cells[3]?.innerText?.trim() || '',
        涨跌幅: cells[4]?.innerText?.trim() || '',
        主力净流入_净额: cells[5]?.innerText?.trim() || '',
        主力净流入_净占比: cells[6]?.innerText?.trim() || '',
        超大单净流入_净额: cells[7]?.innerText?.trim() || '',
        超大单净流入_净占比: cells[8]?.innerText?.trim() || ''
      });
    }
  }
  return JSON.stringify(data);
}
"""


class ZjlxFetcher:
    """资金流排行自动获取器"""
    
    def __init__(self):
        self.session_id = None
        self.page_id = None
    
    def check_browser_status(self) -> dict:
        """检查浏览器状态"""
        try:
            resp = requests.get(f"{BROWSER_CONTROL_URL}/status", timeout=5)
            return resp.json()
        except Exception as e:
            return {"running": False, "error": str(e)}
    
    def start_browser(self) -> bool:
        """启动浏览器"""
        print("🚀 启动浏览器...")
        
        result = subprocess.run(
            ["openclaw", "browser", "start"],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            print("✅ 浏览器已启动")
            time.sleep(3)  # 等待初始化
            return True
        
        print(f"❌ 启动失败: {result.stderr}")
        return False
    
    def stop_browser(self):
        """关闭浏览器"""
        print("🛑 关闭浏览器...")
        subprocess.run(["openclaw", "browser", "stop"], capture_output=True)
    
    def open_page(self, url: str) -> str:
        """打开页面并返回 page_id"""
        print(f"📖 打开页面: {url}")
        
        # 使用 requests 调用浏览器 API
        try:
            resp = requests.post(
                f"{BROWSER_CONTROL_URL}/open",
                json={"url": url},
                timeout=30
            )
            
            result = resp.json()
            if result.get("targetId"):
                self.page_id = result["targetId"]
                print(f"✅ 页面已打开: {self.page_id}")
                return self.page_id
            else:
                print(f"❌ 打开页面失败: {result}")
                return None
        except Exception as e:
            print(f"❌ 请求异常: {e}")
            return None
    
    def wait_for_load(self, ms: int = 3000):
        """等待页面加载"""
        print(f"⏳ 等待 {ms}ms...")
        time.sleep(ms / 1000)
    
    def extract_table_data(self) -> list:
        """提取表格数据"""
        print("📊 提取表格数据...")
        
        # 使用 requests 调用 act API
        try:
            resp = requests.post(
                f"{BROWSER_CONTROL_URL}/act",
                json={
                    "kind": "evaluate",
                    "fn": JS_EXTRACT_TABLE,
                    "targetId": self.page_id
                },
                timeout=30
            )
            
            result = resp.json()
            
            if result.get("ok") and result.get("result"):
                data_str = result["result"]
                data = json.loads(data_str)
                print(f"✅ 提取成功: {len(data)} 条数据")
                return data
            else:
                print(f"❌ 提取失败: {result}")
                return []
        except Exception as e:
            print(f"❌ 提取异常: {e}")
            return []
    
    def parse_and_analyze(self, data: list) -> dict:
        """解析和分析数据"""
        
        if not data:
            return {"error": "无数据"}
        
        # 清理数据
        clean_data = []
        for item in data:
            # 提取金额数值
            main_amount = self.parse_amount(item.get("主力净流入_净额", ""))
            
            clean_item = {
                "序号": item["序号"],
                "代码": item["代码"],
                "名称": item["名称"],
                "最新价": item["最新价"],
                "涨跌幅": item["涨跌幅"],
                "主力净流入": item.get("主力净流入_净额", ""),
                "主力净流入_金额": main_amount,
                "主力占比": item.get("主力净流入_净占比", ""),
                "主力占比_数值": self.parse_ratio(item.get("主力净流入_净占比", "")),
                "超大单净流入": item.get("超大单净流入_净额", ""),
                "评级": self.get_rating(main_amount, self.parse_ratio(item.get("主力净流入_净占比", "")))
            }
            clean_data.append(clean_item)
        
        # 分析
        top20 = clean_data[:20]
        total_inflow = sum(d["主力净流入_金额"] for d in top20)
        
        # 高占比股票
        high_ratio = [d for d in top20 if d["主力占比_数值"] > 20]
        
        # 涨停股
        limit_up = [d for d in top20 if "10" in d["涨跌幅"]]
        
        # 板块分类
        sectors = self.classify_sectors(top20)
        
        # 推荐股票
        recommended = self.get_recommendations(top20)
        
        analysis = {
            "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_count": len(data),
            "top20_total_inflow": round(total_inflow, 2),
            "high_ratio_stocks": [{"名称": d["名称"], "占比": d["主力占比"]} for d in high_ratio],
            "limit_up_stocks": [d["名称"] for d in limit_up],
            "sectors": sectors,
            "recommended": recommended,
            "market_summary": self.get_market_summary(clean_data)
        }
        
        return {
            "data": clean_data,
            "analysis": analysis
        }
    
    def parse_amount(self, text: str) -> float:
        """解析金额（亿元）"""
        if not text:
            return 0.0
        text = text.strip()
        try:
            if "亿" in text:
                return float(text.replace("亿", ""))
            elif "万" in text:
                return float(text.replace("万", "")) / 10000
            return float(text)
        except:
            return 0.0
    
    def parse_ratio(self, text: str) -> float:
        """解析占比"""
        if not text:
            return 0.0
        try:
            return float(text.replace("%", ""))
        except:
            return 0.0
    
    def get_rating(self, amount: float, ratio: float) -> str:
        """获取评级"""
        if ratio > 30:
            return "⭐⭐⭐⭐⭐"
        elif ratio > 20:
            return "⭐⭐⭐⭐"
        elif amount > 5:
            return "⭐⭐⭐⭐"
        elif amount > 3:
            return "⭐⭐⭐"
        else:
            return "⭐⭐"
    
    def classify_sectors(self, data: list) -> dict:
        """板块分类"""
        sectors = {}
        for d in data:
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
                sectors[sector] = {"count": 0, "stocks": [], "inflow": 0}
            sectors[sector]["count"] += 1
            sectors[sector]["stocks"].append(d["名称"])
            sectors[sector]["inflow"] += d["主力净流入_金额"]
        
        return sectors
    
    def get_recommendations(self, data: list) -> list:
        """获取推荐股票"""
        recommendations = []
        
        for d in data[:10]:  # 取前10
            reasons = []
            
            # 主力占比高
            if d["主力占比_数值"] > 20:
                reasons.append(f"主力占比{d['主力占比']}")
            
            # 流入金额大
            if d["主力净流入_金额"] > 5:
                reasons.append(f"流入{d['主力净流入']}")
            
            # 涨停
            if "10" in d["涨跌幅"]:
                reasons.append("涨停")
            
            if reasons:
                recommendations.append({
                    "代码": d["代码"],
                    "名称": d["名称"],
                    "评级": d["评级"],
                    "理由": ", ".join(reasons)
                })
        
        return recommendations
    
    def get_market_summary(self, data: list) -> dict:
        """市场摘要"""
        inflow_count = sum(1 for d in data if d["主力净流入_金额"] > 0)
        outflow_count = len(data) - inflow_count
        
        avg_inflow = sum(d["主力净流入_金额"] for d in data) / len(data) if data else 0
        
        return {
            "流入股票数": inflow_count,
            "流出股票数": outflow_count,
            "平均流入": round(avg_inflow, 2),
            "最强流入": data[0]["名称"] if data else "",
            "最强流入金额": data[0]["主力净流入"] if data else ""
        }
    
    def save_result(self, result: dict) -> str:
        """保存结果"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"zjlx_ranking_{date_str}.json"
        filepath = DATA_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 数据已保存: {filepath}")
        return str(filepath)
    
    def run(self, auto_close: bool = True) -> dict:
        """完整流程"""
        
        print("\n" + "=" * 60)
        print("📊 主板资金流排行自动获取")
        print("=" * 60)
        
        # 1. 检查浏览器状态
        status = self.check_browser_status()
        
        if not status.get("running"):
            # 启动浏览器
            if not self.start_browser():
                return {"success": False, "error": "浏览器启动失败"}
        
        # 2. 打开页面
        page_id = self.open_page(ZJLX_URL)
        if not page_id:
            if auto_close:
                self.stop_browser()
            return {"success": False, "error": "打开页面失败"}
        
        # 3. 等待加载
        self.wait_for_load(3000)
        
        # 4. 提取数据
        raw_data = self.extract_table_data()
        
        # 5. 解析和分析
        result = self.parse_and_analyze(raw_data)
        
        # 6. 保存
        filepath = self.save_result(result)
        
        # 7. 关闭浏览器（可选）
        if auto_close:
            self.stop_browser()
        
        # 8. 打印摘要
        self.print_summary(result["analysis"])
        
        return {
            "success": True,
            "data": result["data"],
            "analysis": result["analysis"],
            "filepath": filepath
        }
    
    def print_summary(self, analysis: dict):
        """打印摘要"""
        print("\n" + "=" * 60)
        print("📊 今日资金流排行分析")
        print("=" * 60)
        print(f"获取时间: {analysis['fetch_time']}")
        print(f"TOP20总流入: {analysis['top20_total_inflow']} 亿元")
        print()
        
        print("🟢 强烈买入信号（主力占比>20%）:")
        for stock in analysis['high_ratio_stocks']:
            print(f"  • {stock['名称']} ({stock['占比']})")
        print()
        
        print(f"🚀 涨停股: {', '.join(analysis['limit_up_stocks'])}")
        print()
        
        print("📈 推荐关注:")
        for rec in analysis['recommended'][:5]:
            print(f"  {rec['评级']} {rec['代码']} {rec['名称']}")
            print(f"     理由: {rec['理由']}")
        
        print("\n" + "=" * 60)


def main():
    """CLI 入口"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="主板资金流排行自动获取")
    parser.add_argument("--keep-browser", action="store_true", help="保持浏览器打开")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    
    args = parser.parse_args()
    
    fetcher = ZjlxFetcher()
    result = fetcher.run(auto_close=not args.keep_browser)
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())