#!/usr/bin/env python3
"""
研究数据导入工具
从多个数据源导入数据到研究数据库

⚠️  仅用于个人研究学习

用法:
    python3 research_import.py --all              # 导入全部股票
    python3 research_import.py --code 600000.SH   # 导入单只股票
    python3 research_import.py --industry 银行    # 导入特定行业
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from research_db import ResearchDatabase
from datetime import datetime, timedelta
import time


def import_from_tushare(db: ResearchDatabase, ts_codes: list = None, 
                        days: int = 250):
    """
    从 Tushare 导入数据
    
    Args:
        db: 研究数据库实例
        ts_codes: 股票代码列表，None 则导入全部
        days: 导入天数（默认 250 个交易日，约 1 年）
    """
    try:
        from tushare_flow import TushareFetcher
    except ImportError:
        print("❌ Tushare 模块未安装")
        return
    
    fetcher = TushareFetcher()
    
    if not fetcher.token:
        print("⚠️  Tushare Token 未配置")
        print("提示：python3 tushare_flow.py --config <your_token>")
        return
    
    # 检查 Token 有效性
    if not fetcher.check_token():
        print("⚠️  Tushare Token 无效，跳过导入")
        return
    
    # 获取股票列表
    if ts_codes is None:
        print("[1/3] 获取股票列表...")
        stock_list = fetcher.get_stock_basic()
        if not stock_list:
            return
        ts_codes = [s['ts_code'] for s in stock_list[:100]]  # 限制前 100 只
        print(f"  将导入 {len(ts_codes)} 只股票")
    
    # 导入每只股票的数据
    for i, ts_code in enumerate(ts_codes, 1):
        print(f"\n[{i}/{len(ts_codes)}] 导入 {ts_code}...")
        
        # 获取日线数据
        print(f"  [日线] ", end='')
        try:
            # 这里调用 Tushare API
            # 由于需要积分，使用示例代码
            print("需要 Tushare 积分，请手动导入或使用其他数据源")
        except Exception as e:
            print(f"失败：{e}")
        
        time.sleep(0.1)  # 避免请求过快


def import_from_local(db: ResearchDatabase, csv_file: str, ts_code: str):
    """
    从本地 CSV 文件导入
    
    Args:
        db: 研究数据库实例
        csv_file: CSV 文件路径
        ts_code: 股票代码
    """
    import pandas as pd
    
    print(f"从 CSV 导入 {ts_code}...")
    
    try:
        df = pd.read_csv(csv_file)
        
        # 导入日线
        if 'trade_date' in df.columns and 'close' in df.columns:
            bars = df.to_dict('records')
            db.insert_daily_bar(ts_code, bars)
            print(f"  ✅ 导入 {len(bars)} 条日线数据")
        
        # 导入资金流
        if 'net_mf_amount' in df.columns:
            flows = df.to_dict('records')
            db.insert_moneyflow(ts_code, flows)
            print(f"  ✅ 导入 {len(flows)} 条资金流数据")
        
    except Exception as e:
        print(f"  ❌ 导入失败：{e}")


def generate_sample_data(db: ResearchDatabase, ts_code: str = '600000.SH', 
                         days: int = 250):
    """
    ⚠️  已删除 - 根据 DATA_POLICY.md 政策，禁止生成模拟数据
    
    所有股票交易数据必须来自真实市场数据源
    """
    print(f"\n❌ 模拟数据生成功能已禁用")
    print(f"\n⚠️  根据数据政策，本系统仅使用真实市场数据")
    print(f"\n💡 请使用以下真实数据源:")
    print(f"   1. Tushare Pro (真实数据，需要 Token)")
    print(f"      python3 research_import.py --code {ts_code}")
    print(f"\n   2. 从 CSV 导入 (已有数据文件)")
    print(f"      python3 research_import.py --csv data.csv --code {ts_code}")
    print(f"\n   3. 从现有缓存导入")
    print(f"      python3 research_import.py --from-cache {ts_code}")
    print(f"\n📚 详见：DATA_POLICY.md")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='研究数据导入工具')
    parser.add_argument('--all', action='store_true', help='导入全部股票')
    parser.add_argument('--code', type=str, help='导入单只股票')
    parser.add_argument('--industry', type=str, help='导入特定行业')
    parser.add_argument('--csv', type=str, help='从 CSV 导入')
    parser.add_argument('--sample', action='store_true', help='⚠️ 已禁用 - 不使用模拟数据')
    parser.add_argument('--days', type=int, default=250, help='导入天数')
    
    args = parser.parse_args()
    
    db = ResearchDatabase()
    
    if args.sample:
        # ⚠️ 已禁用 - 不使用模拟数据
        generate_sample_data(db, days=args.days)
        return
    
    if args.csv:
        # 从 CSV 导入
        ts_code = args.code or '600000.SH'
        if not ts_code.endswith('.SH') and not ts_code.endswith('.SZ'):
            ts_code += '.SH' if ts_code.startswith('6') else '.SZ'
        
        import_from_local(db, args.csv, ts_code)
        return
    
    if args.all or args.code or args.industry:
        # 从 Tushare 导入
        ts_codes = None
        
        if args.code:
            ts_code = args.code.upper()
            if not ts_code.endswith('.SH') and not ts_code.endswith('.SZ'):
                ts_code += '.SH' if ts_code.startswith('6') else '.SZ'
            ts_codes = [ts_code]
        
        import_from_tushare(db, ts_codes=ts_codes, days=args.days)
        return
    
    # 默认显示帮助
    parser.print_help()
    
    print(f"\n{'='*60}")
    print(f"💡 使用建议:")
    print(f"{'='*60}")
    print(f"⚠️  本系统仅使用真实市场数据，不使用模拟数据")
    print(f"\n1. 从 Tushare 导入真实数据（推荐）:")
    print(f"   python3 tushare_flow.py --config <your_token>")
    print(f"   python3 research_import.py --code 600000.SH")
    print(f"\n2. 从 CSV 导入（已有数据文件）:")
    print(f"   python3 research_import.py --csv data.csv --code 600000.SH")
    print(f"\n3. 从现有缓存导入:")
    print(f"   python3 research_import.py --from-cache 600000.SH")
    print(f"\n📚 详见：DATA_POLICY.md")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
