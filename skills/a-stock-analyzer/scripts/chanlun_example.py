#!/usr/bin/env python3
"""
缠论分析示例脚本
演示如何使用缠论模块进行股票分析
"""

import sys
import os

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chanlun import (
    find_fractals, filter_fractals, form_bis, form_duan,
    find_zhongshu, find_beichi, find_buy_sell_points,
    generate_chanlun_report, print_chanlun_report
)
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta


def demo_with_real_data(symbol: str = "603739"):
    """使用真实数据演示缠论分析"""
    print(f"\n{'='*70}")
    print(f"缠论分析示例 - {symbol}")
    print(f"{'='*70}\n")
    
    # 获取历史数据
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
    
    print(f"获取 {symbol} 历史数据...")
    try:
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        print(f"获取到 {len(df)} 条数据\n")
    except Exception as e:
        print(f"数据获取失败：{e}")
        return
    
    # 方法 1: 使用完整报告生成
    print("【方法 1: 完整缠论报告】")
    report = generate_chanlun_report(df)
    print_chanlun_report(report)
    
    # 方法 2: 分步演示
    print("\n【方法 2: 分步解析】")
    
    # 步骤 1: 识别分型
    fractals = find_fractals(df)
    fractals = filter_fractals(fractals)
    print(f"\n1. 识别分型：共 {len(fractals)} 个")
    print(f"   顶分型：{sum(1 for f in fractals if f.fractal_type.name == 'TOP')}")
    print(f"   底分型：{sum(1 for f in fractals if f.fractal_type.name == 'BOTTOM')}")
    
    # 步骤 2: 形成笔
    bis = form_bis(fractals, df)
    print(f"\n2. 形成笔：共 {len(bis)} 笔")
    print(f"   向上笔：{sum(1 for b in bis if b.direction == 1)}")
    print(f"   向下笔：{sum(1 for b in bis if b.direction == -1)}")
    
    # 步骤 3: 形成线段
    duans = form_duan(bis)
    print(f"\n3. 形成线段：共 {len(duans)} 个")
    
    # 步骤 4: 识别中枢
    zhongshus = find_zhongshu(bis)
    print(f"\n4. 识别中枢：共 {len(zhongshus)} 个")
    for i, zs in enumerate(zhongshus[-3:], 1):
        print(f"   中枢{i}: [{zs.low:.2f}, {zs.high:.2f}]")
    
    # 步骤 5: 识别背驰
    beichis = find_beichi(bis, df)
    print(f"\n5. 识别背驰：共 {len(beichis)} 个")
    for bc in beichis[-3:]:
        print(f"   {bc.beichi_type}: 强度 {bc.strength:.2f}")
    
    # 步骤 6: 识别买卖点
    points = find_buy_sell_points(bis, zhongshus, beichis)
    print(f"\n6. 识别买卖点：共 {len(points)} 个")
    for pt in points[-5:]:
        print(f"   ⭐ {pt['type']}: {pt['description']}")
    
    print(f"\n{'='*70}\n")


def demo_with_sample_data():
    """使用示例数据演示"""
    print(f"\n{'='*70}")
    print("缠论分析示例 - 模拟数据")
    print(f"{'='*70}\n")
    
    # 创建模拟数据 (一个完整的上涨 - 下跌 - 上涨周期)
    import numpy as np
    
    np.random.seed(42)
    n = 100
    
    # 生成价格走势
    trend = np.linspace(10, 15, n)
    noise = np.cumsum(np.random.randn(n)) * 0.1
    price = trend + noise
    
    df = pd.DataFrame({
        '日期': pd.date_range('2024-01-01', periods=n),
        '开盘': price + np.random.randn(n) * 0.05,
        '最高': price + np.abs(np.random.randn(n)) * 0.1,
        '最低': price - np.abs(np.random.randn(n)) * 0.1,
        '收盘': price,
        '成交量': np.random.randint(1000, 10000, n)
    })
    
    df['日期'] = df['日期'].astype(str)
    
    print(f"生成 {n} 条模拟数据\n")
    
    # 生成报告
    report = generate_chanlun_report(df)
    print_chanlun_report(report)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='缠论分析示例')
    parser.add_argument('--symbol', type=str, default='603739', 
                        help='股票代码 (默认：603739)')
    parser.add_argument('--sample', action='store_true',
                        help='使用模拟数据演示')
    
    args = parser.parse_args()
    
    if args.sample:
        demo_with_sample_data()
    else:
        try:
            demo_with_real_data(args.symbol)
        except Exception as e:
            print(f"演示失败：{e}")
            print("\n尝试使用模拟数据演示...")
            demo_with_sample_data()
