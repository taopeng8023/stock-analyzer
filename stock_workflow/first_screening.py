#!/usr/bin/env python3
"""
股票筛选与多因子决策工作流 - 第一次筛选（纯 Python 版）
不依赖 pandas/numpy，使用纯 Python 实现
"""

from datetime import datetime
from pathlib import Path
import json

print("="*70)
print("📊 股票筛选与多因子决策工作流 - 第一次筛选（纯 Python 版）")
print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)

# ==================== 阶段 1: 股票筛选 ====================
print("\n" + "="*70)
print("📋 阶段 1: 股票筛选")
print("="*70)

# 模拟全市场股票数据
print("获取全市场股票数据...")
all_stocks = [
    {'code': '600519', 'name': '贵州茅台', 'market': '主板'},
    {'code': '000858', 'name': '五粮液', 'market': '主板'},
    {'code': '600036', 'name': '招商银行', 'market': '主板'},
    {'code': '000002', 'name': '万科 A', 'market': '主板'},
    {'code': '000651', 'name': '格力电器', 'market': '主板'},
    {'code': '300750', 'name': '宁德时代', 'market': '创业板'},
    {'code': '688981', 'name': '中芯国际', 'market': '科创板'},
    {'code': '601398', 'name': '工商银行', 'market': '主板'},
    {'code': '000725', 'name': '京东方 A', 'market': '主板'},
    {'code': '601857', 'name': '中国石油', 'market': '主板'},
]

print(f"全市场股票数：{len(all_stocks)}")

# 主板筛选
main_board = [s for s in all_stocks if s['market'] == '主板']
print(f"主板股票数：{len(main_board)}")

# 成交量放大筛选（模拟数据）
print("\n成交量放大筛选...")
volume_data = {
    '600519': {'vol_t': 10000, 'vol_ma5': 5000},
    '000858': {'vol_t': 8000, 'vol_ma5': 5000},
    '600036': {'vol_t': 15000, 'vol_ma5': 6000},
    '000002': {'vol_t': 5000, 'vol_ma5': 5000},
    '000651': {'vol_t': 12000, 'vol_ma5': 5000},
    '601398': {'vol_t': 20000, 'vol_ma5': 15000},
    '000725': {'vol_t': 18000, 'vol_ma5': 10000},
    '601857': {'vol_t': 25000, 'vol_ma5': 20000},
}

# 计算成交量放大倍数并筛选
amplified = []
for code, data in volume_data.items():
    ratio = data['vol_t'] / (data['vol_ma5'] + 1)
    if ratio > 1.5:
        amplified.append({'code': code, 'volume_ratio': ratio})

print(f"成交量放大股票数：{len(amplified)}")

# 合并筛选结果
stock_pool = []
for stock in main_board:
    for amp in amplified:
        if stock['code'] == amp['code']:
            stock['volume_ratio'] = amp['volume_ratio']
            stock_pool.append(stock)

print(f"\n✅ 候选股票池：{len(stock_pool)}只")
for s in stock_pool:
    print(f"  {s['code']} {s['name']} - 成交量放大{s['volume_ratio']:.2f}倍")

# ==================== 阶段 2: 基本面分析 ====================
print("\n" + "="*70)
print("📊 阶段 2: 基本面分析")
print("="*70)

# 模拟基本面数据
fundamental_data = {
    '600519': {'pe_ttm': 30, 'pb': 8, 'roe': 25},
    '000858': {'pe_ttm': 25, 'pb': 6, 'roe': 20},
    '600036': {'pe_ttm': 10, 'pb': 1.5, 'roe': 15},
    '000002': {'pe_ttm': 8, 'pb': 1.2, 'roe': 12},
    '000651': {'pe_ttm': 12, 'pb': 3, 'roe': 18},
    '601398': {'pe_ttm': 15, 'pb': 1.8, 'roe': 10},
    '000725': {'pe_ttm': 20, 'pb': 2.5, 'roe': 12},
    '601857': {'pe_ttm': 25, 'pb': 3, 'roe': 15},
}

# 计算综合评分（简化版）
for stock in stock_pool:
    code = stock['code']
    data = fundamental_data.get(code, {'pe_ttm': 20, 'pb': 3, 'roe': 15})
    
    # 综合评分 = -PE*0.3 - PB*0.2 + ROE*0.5（简化）
    score = -data['pe_ttm']*0.03 - data['pb']*0.1 + data['roe']*0.05
    stock['fundamental_score'] = score
    stock['pe_ttm'] = data['pe_ttm']
    stock['pb'] = data['pb']
    stock['roe'] = data['roe']

print(f"基本面分析完成")
for s in stock_pool:
    print(f"  {s['code']} {s['name']} - PE:{s['pe_ttm']} PB:{s['pb']} ROE:{s['roe']}% 评分:{s['fundamental_score']:.2f}")

# ==================== 阶段 3: 技术分析 ====================
print("\n" + "="*70)
print("📈 阶段 3: 技术分析")
print("="*70)

# 模拟技术指标
technical_data = {
    '600519': {'ma5_ma20_ratio': 1.15, 'rsi_14': 65},
    '000858': {'ma5_ma20_ratio': 1.08, 'rsi_14': 58},
    '600036': {'ma5_ma20_ratio': 1.02, 'rsi_14': 52},
    '000002': {'ma5_ma20_ratio': 0.98, 'rsi_14': 45},
    '000651': {'ma5_ma20_ratio': 1.05, 'rsi_14': 60},
    '601398': {'ma5_ma20_ratio': 1.10, 'rsi_14': 55},
    '000725': {'ma5_ma20_ratio': 0.95, 'rsi_14': 40},
    '601857': {'ma5_ma20_ratio': 1.12, 'rsi_14': 68},
}

# 技术信号
def get_tech_signal(ratio):
    if ratio > 1.1:
        return '强买入'
    elif ratio > 1.0:
        return '买入'
    elif ratio > 0.95:
        return '中性'
    else:
        return '卖出'

for stock in stock_pool:
    code = stock['code']
    data = technical_data.get(code, {'ma5_ma20_ratio': 1.0, 'rsi_14': 50})
    stock['ma5_ma20_ratio'] = data['ma5_ma20_ratio']
    stock['rsi_14'] = data['rsi_14']
    stock['tech_signal'] = get_tech_signal(data['ma5_ma20_ratio'])

print(f"技术分析完成")
for s in stock_pool:
    print(f"  {s['code']} {s['name']} - MA5/20:{s['ma5_ma20_ratio']:.2f} RSI:{s['rsi_14']} 信号:{s['tech_signal']}")

# ==================== 阶段 4: 数据质量监控 ====================
print("\n" + "="*70)
print("🔍 阶段 4: 数据质量监控")
print("="*70)

# 检查数据完整性
missing_count = sum(1 for s in stock_pool if s.get('fundamental_score') is None)
missing_rate = missing_count / len(stock_pool) if stock_pool else 0
quality_score = (1 - missing_rate) * 100

print(f"缺失率：{missing_rate:.1%}")
print(f"✅ 质量评分：{quality_score:.1f}/100")
print(f"质量状态：{'✅ 合格' if quality_score >= 95 else '⚠️ 需关注'}")

# ==================== 阶段 5: 决策融合 ====================
print("\n" + "="*70)
print("🤖 阶段 5: 决策融合")
print("="*70)

# 计算综合评分
for stock in stock_pool:
    composite = (
        stock['fundamental_score'] * 0.4 +
        stock['ma5_ma20_ratio'] * 30 +
        stock['rsi_14'] / 100 * 20
    )
    stock['composite_score'] = composite

# 排序
stock_pool.sort(key=lambda x: x['composite_score'], reverse=True)

# 添加排名
for i, stock in enumerate(stock_pool):
    stock['rank'] = i + 1

# Top 10 推荐
top_stocks = stock_pool[:10]

print(f"✅ 推荐股票数：{len(top_stocks)}")

# ==================== 阶段 6: 结果输出 ====================
print("\n" + "="*70)
print("📤 阶段 6: 结果输出")
print("="*70)

# 生成报告
print("\n" + "="*70)
print("📊 股票筛选与多因子决策报告")
print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)
print()
print(f"📋 数据质量")
print(f"  质量评分：{quality_score:.1f}/100")
print(f"  质量状态：{'✅ 合格' if quality_score >= 95 else '⚠️ 需关注'}")
print()
print(f"🎯 推荐股票（Top {len(top_stocks)}）")
print("-"*70)

for stock in top_stocks:
    print(f"{stock['rank']}. {stock['name']} ({stock['code']})")
    print(f"   综合评分：{stock['composite_score']:.2f}")
    print(f"   成交量放大：{stock['volume_ratio']:.2f}倍")
    print(f"   基本面评分：{stock['fundamental_score']:.2f}")
    print(f"   技术信号：{stock['tech_signal']}")
    print(f"   RSI: {stock['rsi_14']}")
    print()

print("="*70)
print("⚠️ 风险提示：本报告仅供参考，不构成投资建议")
print("="*70)

# 保存结果
result_file = Path(__file__).parent / 'data' / f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
result_file.parent.mkdir(parents=True, exist_ok=True)

with open(result_file, 'w', encoding='utf-8') as f:
    json.dump(top_stocks, f, ensure_ascii=False, indent=2)

print(f"\n📁 结果已保存：{result_file}")

print("\n✅ 第一次筛选完成！")
