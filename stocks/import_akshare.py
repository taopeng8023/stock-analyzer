#!/usr/bin/env python3
"""
导入 AKShare/同花顺真实数据到研究数据库

⚠️  仅用于个人研究学习

用法:
    python3 import_akshare.py --all              # 导入全部排行数据
    python3 import_akshare.py --code 浦发银行     # 导入个股详情
    python3 import_akshare.py --industry         # 导入行业数据
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

# 检查 AKShare
try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False
    print("❌ AKShare 未安装")
    print("请运行：pip install akshare")
    sys.exit(1)

from research_db import ResearchDatabase


def import_stock_rank(db: ResearchDatabase, top_n: int = 50):
    """
    导入个股资金流排行
    
    Args:
        db: 研究数据库
        top_n: 导入数量
    """
    print("\n[导入] 个股资金流排行...")
    
    try:
        # 获取排行数据
        data = ak.stock_individual_fund_flow_rank(indicator="今日")
        
        if data is None or len(data) == 0:
            print("  ❌ 未获取到数据")
            return
        
        # 取前 N 只
        data = data.head(top_n)
        
        # 导入每只股票的详情
        for idx, row in data.iterrows():
            symbol = row.get('名称', '')
            if not symbol:
                continue
            
            # 判断市场
            code = row.get('代码', '')
            market = "沪" if code.startswith('6') else "深"
            
            print(f"  导入 {symbol} ({code})...")
            
            # 获取个股详情
            try:
                detail = ak.stock_individual_fund_flow(symbol=symbol, market=market)
                
                if detail is not None and len(detail) > 0:
                    # 转换为 ts_code
                    ts_code = f"{code}.SH" if market == "沪" else f"{code}.SZ"
                    
                    # 插入基本信息
                    db.insert_stock_basic([{
                        'ts_code': ts_code,
                        'symbol': code,
                        'name': symbol,
                        'industry': row.get('所属行业', ''),
                        'list_date': '',
                        'updated_at': datetime.now().isoformat()
                    }])
                    
                    # 插入资金流数据
                    flows = []
                    for _, d in detail.iterrows():
                        flows.append({
                            'trade_date': d.get('日期', ''),
                            'buy_sm_amount': d.get('小单净流入金额', 0),
                            'sell_sm_amount': 0,
                            'buy_md_amount': d.get('中单净流入金额', 0),
                            'sell_md_amount': 0,
                            'buy_lg_amount': d.get('大单净流入金额', 0),
                            'sell_lg_amount': 0,
                            'buy_elg_amount': d.get('特大单净流入金额', 0),
                            'sell_elg_amount': 0,
                            'net_mf_amount': d.get('主力净流入-净额', 0),
                        })
                    
                    db.insert_moneyflow(ts_code, flows)
                    print(f"    ✅ 导入 {len(flows)} 条资金流数据")
                
            except Exception as e:
                print(f"    ⚠️  获取失败：{e}")
            
            # 控制频率
            import time
            time.sleep(0.5)
        
        print(f"\n✅ 完成导入 {top_n} 只股票")
        
    except Exception as e:
        print(f"❌ 导入失败：{e}")


def import_industry_flow(db: ResearchDatabase):
    """
    导入行业资金流
    
    Args:
        db: 研究数据库
    """
    print("\n[导入] 行业资金流...")
    
    try:
        data = ak.stock_fund_flow_industry(symbol="今日")
        
        if data is None or len(data) == 0:
            print("  ❌ 未获取到数据")
            return
        
        print(f"  ✅ 获取到 {len(data)} 个行业数据")
        
        # 保存到 CSV（行业数据不存入数据库）
        cache_dir = Path(__file__).parent / 'cache'
        cache_dir.mkdir(exist_ok=True)
        
        filepath = cache_dir / f"industry_flow_{datetime.now().strftime('%Y%m%d')}.csv"
        data.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"  ✅ 已保存：{filepath}")
        
    except Exception as e:
        print(f"❌ 导入失败：{e}")


def import_single_stock(db: ResearchDatabase, symbol: str, market: str = "沪"):
    """
    导入单只股票资金流详情
    
    Args:
        db: 研究数据库
        symbol: 股票名称
        market: 市场（沪/深）
    """
    print(f"\n[导入] {symbol} ({market}) 资金流详情...")
    
    try:
        # 获取详情
        data = ak.stock_individual_fund_flow(symbol=symbol, market=market)
        
        if data is None or len(data) == 0:
            print("  ❌ 未获取到数据")
            return
        
        # 获取股票代码
        code_data = ak.stock_individual_fund_flow_rank(indicator="今日")
        code = None
        if code_data is not None:
            match = code_data[code_data['名称'] == symbol]
            if len(match) > 0:
                code = match.iloc[0].get('代码', '')
        
        if not code:
            print("  ❌ 未找到股票代码")
            return
        
        # 转换为 ts_code
        ts_code = f"{code}.SH" if market == "沪" else f"{code}.SZ"
        
        # 插入基本信息
        db.insert_stock_basic([{
            'ts_code': ts_code,
            'symbol': code,
            'name': symbol,
            'industry': '',
            'list_date': '',
            'updated_at': datetime.now().isoformat()
        }])
        
        # 插入资金流数据
        flows = []
        for _, row in data.iterrows():
            flows.append({
                'trade_date': row.get('日期', ''),
                'buy_sm_amount': row.get('小单净流入金额', 0),
                'sell_sm_amount': 0,
                'buy_md_amount': row.get('中单净流入金额', 0),
                'sell_md_amount': 0,
                'buy_lg_amount': row.get('大单净流入金额', 0),
                'sell_lg_amount': 0,
                'buy_elg_amount': row.get('特大单净流入金额', 0),
                'sell_elg_amount': 0,
                'net_mf_amount': row.get('主力净流入 - 净额', 0),
            })
        
        db.insert_moneyflow(ts_code, flows)
        print(f"  ✅ 导入 {len(flows)} 条资金流数据")
        
        db.print_stats()
        
    except Exception as e:
        print(f"❌ 导入失败：{e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='导入 AKShare/同花顺数据')
    parser.add_argument('--all', action='store_true', help='导入全部排行数据')
    parser.add_argument('--code', type=str, help='导入个股（股票名称）')
    parser.add_argument('--industry', action='store_true', help='导入行业数据')
    parser.add_argument('--top', type=int, default=10, help='导入前 N 只股票')
    
    args = parser.parse_args()
    
    if not HAS_AKSHARE:
        print("\n❌ AKShare 未安装")
        print("请运行：pip install akshare")
        return
    
    db = ResearchDatabase()
    
    if args.all:
        import_stock_rank(db, top_n=args.top)
        return
    
    if args.code:
        # 判断市场
        market = "沪" if args.code in ['浦发银行', '中国平安', '招商银行', '贵州茅台'] else "深"
        import_single_stock(db, args.code, market=market)
        return
    
    if args.industry:
        import_industry_flow(db)
        return
    
    # 默认帮助
    parser.print_help()
    
    print(f"\n{'='*60}")
    print(f"💡 使用示例:")
    print(f"{'='*60}")
    print(f"1. 导入个股资金流排行前 10:")
    print(f"   python3 import_akshare.py --all --top 10")
    print(f"\n2. 导入单只股票详情:")
    print(f"   python3 import_akshare.py --code 浦发银行")
    print(f"\n3. 导入行业资金流:")
    print(f"   python3 import_akshare.py --industry")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
