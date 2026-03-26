#!/usr/bin/env python3
"""
同花顺资金流数据接口（通过 AKShare）
数据源：同花顺 - 真实市场数据

⚠️  仅用于个人研究学习

安装:
    pip install akshare

用法:
    python3 akshare_flow.py --top 10          # 主力净流入排行
    python3 akshare_flow.py --industry        # 行业资金流
    python3 akshare_flow.py --concept         # 概念资金流
    python3 akshare_flow.py --stock 浦发银行   # 个股资金流
"""

import sys
from datetime import datetime

# 检查 AKShare 是否安装
try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False
    print("⚠️  AKShare 未安装")
    print("\n安装方法:")
    print("  pip install akshare")
    print("\n或使用虚拟环境:")
    print("  python3 -m pip install akshare")


class AKShareFetcher:
    """AKShare 数据获取"""
    
    def __init__(self):
        if not HAS_AKSHARE:
            raise ImportError("AKShare 未安装，请先运行：pip install akshare")
    
    def get_individual_rank(self, indicator: str = "今日", top_n: int = 50):
        """
        获取个股资金流排行
        
        Args:
            indicator: 时间指标，可选：今日、3 日、5 日、10 日
            top_n: 返回数量
        
        Returns:
            DataFrame: 资金流排行数据
        """
        print(f"[AKShare/同花顺] 获取个股资金流排行 ({indicator})...")
        
        try:
            data = ak.stock_individual_fund_flow_rank(indicator=indicator)
            
            if data is not None and len(data) > 0:
                print(f"✅ 获取到 {len(data)} 只股票数据")
                return data.head(top_n)
            else:
                print("❌ 未获取到数据")
                return None
                
        except Exception as e:
            print(f"❌ 获取失败：{e}")
            return None
    
    def get_industry_flow(self, indicator: str = "今日"):
        """
        获取行业资金流
        
        Args:
            indicator: 时间指标，可选：今日、5 日、10 日、20 日
        
        Returns:
            DataFrame: 行业资金流数据
        """
        print(f"[AKShare/同花顺] 获取行业资金流 ({indicator})...")
        
        try:
            data = ak.stock_fund_flow_industry(symbol=indicator)
            
            if data is not None and len(data) > 0:
                print(f"✅ 获取到 {len(data)} 个行业数据")
                return data
            else:
                print("❌ 未获取到数据")
                return None
                
        except Exception as e:
            print(f"❌ 获取失败：{e}")
            return None
    
    def get_concept_flow(self, indicator: str = "今日"):
        """
        获取概念资金流
        
        Args:
            indicator: 时间指标，可选：今日、5 日、10 日、20 日
        
        Returns:
            DataFrame: 概念资金流数据
        """
        print(f"[AKShare/同花顺] 获取概念资金流 ({indicator})...")
        
        try:
            data = ak.stock_fund_flow_concept(symbol=indicator)
            
            if data is not None and len(data) > 0:
                print(f"✅ 获取到 {len(data)} 个概念数据")
                return data
            else:
                print("❌ 未获取到数据")
                return None
                
        except Exception as e:
            print(f"❌ 获取失败：{e}")
            return None
    
    def get_individual_detail(self, symbol: str, market: str = "沪"):
        """
        获取个股资金流详情
        
        Args:
            symbol: 股票名称（如：浦发银行）
            market: 市场，可选：沪、深
        
        Returns:
            DataFrame: 个股资金流历史
        """
        print(f"[AKShare/同花顺] 获取 {symbol} ({market}) 资金流详情...")
        
        try:
            data = ak.stock_individual_fund_flow(symbol=symbol, market=market)
            
            if data is not None and len(data) > 0:
                print(f"✅ 获取到 {len(data)} 条历史数据")
                return data
            else:
                print("❌ 未获取到数据")
                return None
                
        except Exception as e:
            print(f"❌ 获取失败：{e}")
            return None
    
    def print_ranking(self, data, title: str = "资金流排行"):
        """打印排行数据"""
        if data is None or len(data) == 0:
            print("无数据")
            return
        
        print(f"\n{'='*90}")
        print(f"💰 {title}")
        print(f"数据源：AKShare/同花顺 (真实数据)")
        print(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*90}")
        
        # 显示列名
        print(f"\n数据字段：{data.columns.tolist()}")
        
        # 显示前 10 条
        print(f"\n前 10 条数据:")
        print(data.head(10).to_string())
        
        print(f"\n{'='*90}")
    
    def save_to_csv(self, data, filename: str):
        """保存数据到 CSV"""
        if data is None:
            return
        
        try:
            filepath = Path(__file__).parent / 'cache' / filename
            filepath.parent.mkdir(exist_ok=True)
            data.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"✅ 已保存：{filepath}")
        except Exception as e:
            print(f"❌ 保存失败：{e}")


def main():
    import argparse
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description='同花顺资金流数据 (AKShare)')
    parser.add_argument('--top', type=int, default=10, help='前 N 只股票')
    parser.add_argument('--industry', action='store_true', help='行业资金流')
    parser.add_argument('--concept', action='store_true', help='概念资金流')
    parser.add_argument('--stock', type=str, help='个股资金流（股票名称）')
    parser.add_argument('--indicator', type=str, default='今日', 
                       help='时间指标（今日/3 日/5 日/10 日）')
    parser.add_argument('--save', action='store_true', help='保存 CSV')
    
    args = parser.parse_args()
    
    if not HAS_AKSHARE:
        print("\n❌ AKShare 未安装")
        print("\n请运行以下命令安装:")
        print("  pip install akshare")
        print("\n安装后重试")
        return
    
    fetcher = AKShareFetcher()
    
    # 个股详情
    if args.stock:
        market = "沪" if args.stock in ['浦发银行', '中国平安', '招商银行'] else "深"
        data = fetcher.get_individual_detail(args.stock, market=market)
        if data:
            fetcher.print_ranking(data, title=f"{args.stock} 资金流历史")
            if args.save:
                fetcher.save_to_csv(data, f"{args.stock}_flow.csv")
        return
    
    # 行业资金流
    if args.industry:
        data = fetcher.get_industry_flow(indicator=args.indicator)
        if data:
            fetcher.print_ranking(data, title=f"行业资金流 ({args.indicator})")
            if args.save:
                fetcher.save_to_csv(data, f"industry_flow_{args.indicator}.csv")
        return
    
    # 概念资金流
    if args.concept:
        data = fetcher.get_concept_flow(indicator=args.indicator)
        if data:
            fetcher.print_ranking(data, title=f"概念资金流 ({args.indicator})")
            if args.save:
                fetcher.save_to_csv(data, f"concept_flow_{args.indicator}.csv")
        return
    
    # 默认：个股资金流排行
    data = fetcher.get_individual_rank(indicator=args.indicator, top_n=args.top)
    if data:
        fetcher.print_ranking(data, title=f"个股资金流排行 ({args.indicator}) Top{args.top}")
        if args.save:
            fetcher.save_to_csv(data, f"stock_flow_rank_{args.indicator}.csv")


if __name__ == '__main__':
    main()
