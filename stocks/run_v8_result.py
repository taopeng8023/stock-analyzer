#!/usr/bin/env python3
"""运行 v8.0 工作流并显示结果"""
import sys
sys.path.insert(0, '/home/admin/.openclaw/workspace/stocks')

from workflow_v8_strict import V8StrictWorkflow, DataFetchLayer, AnalysisLayer

# 运行工作流
print("="*80)
print("🚀 v8.0-Financial-Enhanced 工作流")
print("="*80)

# Layer 1: 数据获取
layer1 = DataFetchLayer()
layer1_results = layer1.fetch(20)

all_stocks = []
for result in layer1_results:
    if result.status == 'success':
        all_stocks.extend(result.stocks)
        print(f"✅ {result.source_name}: {result.stock_count} 条")
    else:
        print(f"❌ {result.source_name}: 失败 - {result.error_message}")

print(f"\n共获取 {len(all_stocks)} 只股票")

# Layer 2: 分析决策
layer2 = AnalysisLayer()
from workflow_v8_strict import AnalysisInput
analysis_input = AnalysisInput(
    stocks=all_stocks,
    data_sources=[r.source_name for r in layer1_results if r.status == 'success'],
    total_count=len(all_stocks),
    fetch_time=__import__('datetime').datetime.now().isoformat()
)

output = layer2.analyze(analysis_input, 20)

# 显示结果
print("\n" + "="*80)
print("📊 最终决策 Top 20")
print("="*80 + "\n")

for i, stock in enumerate(output.stocks[:20], 1):
    code = stock.get('code', 'N/A')
    name = stock.get('name', 'N/A')
    price = stock.get('price', 0)
    change = stock.get('change_pct', 0)
    turnover = stock.get('turnover', 0) / 100000000  # 亿
    score = stock.get('score', 0)
    rating = stock.get('rating', 'N/A')
    
    rating_icon = {'强烈推荐': '⭐⭐⭐', '推荐': '⭐⭐', '关注': '⭐', '观望': '⭕'}.get(rating, '')
    
    if change > 2:
        icon = '📗'
    elif change < -2:
        icon = '📉'
    elif change > 0:
        icon = '📈'
    else:
        icon = '📉'
    
    print(f"{i:2}. {rating_icon} {icon} {name}({code})")
    print(f"    ¥{price:.2f} {change:+.2f}% 成交{turnover:.2f}亿 评分:{score}")
    print(f"    止盈¥{stock.get('stop_profit', 0):.2f} 止损¥{stock.get('stop_loss', 0):.2f}")
    print(f"    {stock.get('tags', '')}")
    print()

print("="*80)
print("✅ 工作流执行完成")
print("="*80)
