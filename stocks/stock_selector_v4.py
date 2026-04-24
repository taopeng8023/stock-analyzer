#!/usr/bin/env python3
"""
选股系统 V4.0 - 资金流排行集成版
整合资金流排行数据到选股流程

特性:
1. ML模型预测 + 资金流排行双重筛选
2. 高置信度 + 主力流入 = 强烈买入信号
3. 自动对比持仓股资金流状态

使用方法:
    python3 stock_selector_v4.py
"""

import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# 配置
WORKSPACE = Path(__file__).parent
DATA_DIR = WORKSPACE / "data"
MODELS_DIR = WORKSPACE / "models"
HISTORY_DIR = WORKSPACE / "data_history_2022_2026"

# 资金流排行配置
ZJLX_FETCHER = WORKSPACE / "zjlx_auto_fetcher.py"


class StockSelectorV4:
    """选股系统 V4 - 资金流集成版"""
    
    def __init__(self):
        self.ml_predictions = []
        self.zjlx_ranking = []
        self.holdings = []
    
    def fetch_zjlx_ranking(self) -> list:
        """获取资金流排行"""
        print("\n📊 获取主板资金流排行...")
        
        # 调用自动获取脚本
        result = subprocess.run(
            ["python3", str(ZJLX_FETCHER), "--json"],
            capture_output=True, text=True, timeout=60
        )
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                if data.get("success"):
                    self.zjlx_ranking = data.get("data", [])
                    print(f"✅ 获取成功: {len(self.zjlx_ranking)} 条")
                    return self.zjlx_ranking
            except Exception as e:
                print(f"解析JSON失败: {e}")
        
        # 尝试读取最近的数据文件
        print("⚠️ 自动获取失败，尝试读取缓存数据...")
        return self.load_cached_zjlx()
    
    def load_cached_zjlx(self) -> list:
        """读取缓存的资金流数据"""
        
        # 查找最新的资金流数据文件
        zjlx_files = list(DATA_DIR.glob("zjlx_ranking_*.json"))
        
        if not zjlx_files:
            print("❌ 无缓存数据")
            return []
        
        # 取最新的
        latest = max(zjlx_files, key=lambda f: f.stat().st_mtime)
        
        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 兼容两种数据格式
        if isinstance(data, list):
            self.zjlx_ranking = data
        elif isinstance(data, dict):
            self.zjlx_ranking = data.get("data", [])
        else:
            self.zjlx_ranking = []
        
        print(f"✅ 读取缓存: {latest.name} ({len(self.zjlx_ranking)} 条)")
        return self.zjlx_ranking
    
    def load_ml_predictions(self) -> list:
        """加载ML预测结果"""
        
        # 查找最近的ML选股结果
        ml_files = list(DATA_DIR.glob("neural_selection_*.json"))
        
        if not ml_files:
            print("⚠️ 无ML预测数据")
            return []
        
        latest = max(ml_files, key=lambda f: f.stat().st_mtime)
        
        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.ml_predictions = data.get("selections", [])
        print(f"✅ ML预测: {len(self.ml_predictions)} 条")
        return self.ml_predictions
    
    def load_holdings(self) -> list:
        """加载持仓信息"""
        
        holdings_file = WORKSPACE.parent / "MEMORY.md"
        
        # 简化：使用已知持仓
        self.holdings = [
            {"代码": "002709", "名称": "天赐材料", "盈亏": -0.17},
            {"代码": "600089", "名称": "特变电工", "盈亏": -2.71},
            {"代码": "603739", "名称": "蔚蓝生物", "盈亏": -10.08},
            {"代码": "600930", "名称": "华电新能", "盈亏": -13.54},
            {"代码": "600163", "名称": "中闽能源", "盈亏": -19.7},
        ]
        
        return self.holdings
    
    def cross_match(self) -> list:
        """交叉匹配 ML预测 + 资金流排行"""
        
        matches = []
        
        for ml in self.ml_predictions:
            ml_code = ml.get("代码", ml.get("code", ""))
            
            # 在资金流排行中查找
            for zjlx in self.zjlx_ranking:
                zjlx_code = zjlx.get("代码", "")
                
                if ml_code == zjlx_code:
                    match = {
                        "代码": ml_code,
                        "名称": ml.get("名称", zjlx.get("名称")),
                        "ML置信度": ml.get("置信度", ml.get("confidence", 0)),
                        "资金流排行": zjlx.get("序号", 0),
                        "主力净流入": zjlx.get("主力净流入", ""),
                        "主力占比": zjlx.get("主力占比", ""),
                        "涨跌幅": zjlx.get("涨跌幅", ""),
                        "评级": self.get_combined_rating(ml, zjlx),
                        "信号": "双重确认 ⭐⭐⭐⭐⭐"
                    }
                    matches.append(match)
        
        return matches
    
    def get_combined_rating(self, ml: dict, zjlx: dict) -> str:
        """获取综合评级"""
        
        confidence = ml.get("置信度", ml.get("confidence", 0))
        ratio = self.parse_ratio(zjlx.get("主力占比", ""))
        amount = self.parse_amount(zjlx.get("主力净流入", ""))
        
        score = 0
        
        # ML置信度
        if confidence > 90:
            score += 30
        elif confidence > 85:
            score += 20
        elif confidence > 75:
            score += 10
        
        # 主力占比
        if ratio > 30:
            score += 30
        elif ratio > 20:
            score += 20
        elif ratio > 10:
            score += 10
        
        # 流入金额
        if amount > 5:
            score += 20
        elif amount > 3:
            score += 10
        
        # 评级
        if score >= 70:
            return "⭐⭐⭐⭐⭐ 强烈买入"
        elif score >= 50:
            return "⭐⭐⭐⭐ 买入"
        elif score >= 30:
            return "⭐⭐⭐ 关注"
        else:
            return "⭐⭐ 观察"
    
    def parse_ratio(self, text: str) -> float:
        """解析占比"""
        if not text:
            return 0.0
        try:
            return float(text.replace("%", ""))
        except:
            return 0.0
    
    def parse_amount(self, text: str) -> float:
        """解析金额"""
        if not text:
            return 0.0
        try:
            if "亿" in text:
                return float(text.replace("亿", ""))
            return 0.0
        except:
            return 0.0
    
    def check_holdings_zjlx(self) -> list:
        """检查持仓股资金流状态"""
        
        holdings_status = []
        
        for holding in self.holdings:
            code = holding["代码"]
            
            # 在资金流排行中查找
            found = False
            for zjlx in self.zjlx_ranking[:50]:  # 只查TOP50
                if zjlx.get("代码") == code:
                    holdings_status.append({
                        "代码": code,
                        "名称": holding["名称"],
                        "盈亏": holding["盈亏"],
                        "资金流排行": zjlx.get("序号"),
                        "主力净流入": zjlx.get("主力净流入"),
                        "主力占比": zjlx.get("主力占比"),
                        "状态": "在榜" if zjlx.get("序号") <= 20 else "未在TOP20",
                        "建议": self.get_holding_suggestion(holding, zjlx)
                    })
                    found = True
                    break
            
            if not found:
                holdings_status.append({
                    "代码": code,
                    "名称": holding["名称"],
                    "盈亏": holding["盈亏"],
                    "资金流排行": None,
                    "主力净流入": "未在榜",
                    "状态": "未在TOP50",
                    "建议": self.get_holding_suggestion(holding, None)
                })
        
        return holdings_status
    
    def get_holding_suggestion(self, holding: dict, zjlx: dict) -> str:
        """获取持仓建议"""
        
        profit = holding.get("盈亏", 0)
        
        # 止损检查
        if profit <= -15:
            return "🚨 立即止损（亏损超15%）"
        
        if profit <= -10:
            return "⚠️ 止损警戒（亏损超10%）"
        
        # 资金流检查
        if zjlx:
            ratio = self.parse_ratio(zjlx.get("主力占比", ""))
            amount = self.parse_amount(zjlx.get("主力净流入", ""))
            
            if amount > 3 and ratio > 10:
                return "✅ 持有/加仓（资金流入强劲）"
            elif amount > 0:
                return "🟡 持有观察（小幅流入）"
            else:
                return "🟠 减仓观望（资金流出）"
        
        # 未在榜
        if profit >= 0:
            return "🟡 持有（未在TOP50）"
        else:
            return "⚠️ 考虑止损"
    
    def select_top_from_zjlx(self, top_n: int = 10) -> list:
        """从资金流排行选取TOP股票"""
        
        top_picks = []
        
        for zjlx in self.zjlx_ranking[:top_n]:
            ratio = self.parse_ratio(zjlx.get("主力占比", ""))
            amount = self.parse_amount(zjlx.get("主力净流入", ""))
            
            pick = {
                "排行": zjlx.get("序号"),
                "代码": zjlx.get("代码"),
                "名称": zjlx.get("名称"),
                "最新价": zjlx.get("最新价"),
                "涨跌幅": zjlx.get("涨跌幅"),
                "主力净流入": zjlx.get("主力净流入"),
                "主力占比": zjlx.get("主力占比"),
                "金额": amount,
                "占比数值": ratio,
                "评级": zjlx.get("评级"),
                "推荐理由": []
            }
            
            # 推荐理由
            if ratio > 30:
                pick["推荐理由"].append(f"主力占比{zjlx['主力占比']}（强烈控盘）")
            if amount > 5:
                pick["推荐理由"].append(f"流入{zjlx['主力净流入']}（大资金进场）")
            if "10" in zjlx.get("涨跌幅", ""):
                pick["推荐理由"].append("涨停")
            
            top_picks.append(pick)
        
        return top_picks
    
    def generate_report(self) -> dict:
        """生成综合报告"""
        
        report = {
            "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "数据来源": "东方财富资金流排行 + ML预测",
        }
        
        # 1. 交叉匹配结果
        matches = self.cross_match()
        report["双重确认股票"] = matches
        
        # 2. 资金流TOP推荐
        top_zjlx = self.select_top_from_zjlx(10)
        report["资金流TOP10"] = top_zjlx
        
        # 3. 持仓状态
        holdings_status = self.check_holdings_zjlx()
        report["持仓资金流状态"] = holdings_status
        
        # 4. 强烈推荐
        strong_buy = [
            p for p in top_zjlx 
            if p["占比数值"] > 20 or p["金额"] > 5
        ]
        report["强烈推荐"] = strong_buy[:5]
        
        # 5. 需止损
        need_stop = [
            h for h in holdings_status
            if "止损" in h["建议"]
        ]
        report["需止损股票"] = need_stop
        
        return report
    
    def save_report(self, report: dict) -> str:
        """保存报告"""
        
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"selection_v4_{date_str}.json"
        filepath = DATA_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    def print_report(self, report: dict):
        """打印报告"""
        
        print("\n" + "=" * 70)
        print("📊 选股系统 V4.0 - 资金流排行集成版")
        print("=" * 70)
        print(f"生成时间: {report['生成时间']}")
        print()
        
        # 双重确认
        if report.get("双重确认股票"):
            print("🎯 双重确认股票（ML预测 + 资金流排行）:")
            for m in report["双重确认股票"]:
                print(f"  {m['评级']} {m['代码']} {m['名称']}")
                print(f"     ML置信度: {m['ML置信度']}%, 排行: #{m['资金流排行']}")
                print(f"     主力流入: {m['主力净流入']}, 占比: {m['主力占比']}")
                print(f"     信号: {m['信号']}")
            print()
        
        # 资金流TOP
        print("📈 资金流TOP10推荐:")
        for p in report.get("资金流TOP10", [])[:10]:
            reasons = ", ".join(p.get("推荐理由", []))
            print(f"  #{p['排行']} {p['评级']} {p['代码']} {p['名称']}")
            print(f"     流入: {p['主力净流入']}, 占比: {p['主力占比']}")
            if reasons:
                print(f"     推荐: {reasons}")
        print()
        
        # 持仓状态
        print("💼 持仓资金流状态:")
        for h in report.get("持仓资金流状态", []):
            print(f"  {h['代码']} {h['名称']}: 盈亏 {h['盈亏']}%")
            print(f"     资金流排行: {h['资金流排行'] if h['资金流排行'] else '未在榜'}")
            print(f"     建议: {h['建议']}")
        print()
        
        # 强烈推荐
        print("🔥 强烈推荐 TOP5:")
        for s in report.get("强烈推荐", [])[:5]:
            print(f"  {s['评级']} {s['代码']} {s['名称']}")
            print(f"     流入: {s['主力净流入']}, 占比: {s['主力占比']}")
        
        # 止损提醒
        if report.get("需止损股票"):
            print("\n🚨 止损提醒:")
            for s in report["需止损股票"]:
                print(f"  {s['代码']} {s['名称']}: {s['建议']}")
        
        print("\n" + "=" * 70)
    
    def run(self) -> dict:
        """完整流程"""
        
        print("\n🚀 选股系统 V4.0 启动...")
        
        # 1. 获取资金流排行
        self.fetch_zjlx_ranking()
        
        # 2. 加载ML预测
        self.load_ml_predictions()
        
        # 3. 加载持仓
        self.load_holdings()
        
        # 4. 生成报告
        report = self.generate_report()
        
        # 5. 保存
        filepath = self.save_report(report)
        print(f"\n✅ 报告已保存: {filepath}")
        
        # 6. 打印
        self.print_report(report)
        
        return report


def main():
    """CLI入口"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="选股系统V4 - 资金流集成")
    parser.add_argument("--json", action="store_true", help="输出JSON")
    parser.add_argument("--no-fetch", action="store_true", help="不自动获取资金流")
    
    args = parser.parse_args()
    
    selector = StockSelectorV4()
    
    if args.no_fetch:
        selector.load_cached_zjlx()
    else:
        selector.fetch_zjlx_ranking()
    
    selector.load_ml_predictions()
    selector.load_holdings()
    
    report = selector.generate_report()
    filepath = selector.save_report(report)
    
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        selector.print_report(report)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())