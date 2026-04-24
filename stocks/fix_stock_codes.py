#!/usr/bin/env python3
"""
修复 A 股股票代码列表
"""

# 正确的 A 股股票代码范围
A_STOCK_CODES = []

# 深市主板：000001-000999
for code in range(1, 1000):
    symbol = f'{code:06d}'
    A_STOCK_CODES.append({'ts_code': f'{symbol}.SZ', 'symbol': symbol, 'market': '深市主板'})

# 深市中小板：002001-002999
for code in range(2001, 3000):
    symbol = f'{code:06d}'
    A_STOCK_CODES.append({'ts_code': f'{symbol}.SZ', 'symbol': symbol, 'market': '深市中小板'})

# 创业板：300001-300999
for code in range(300001, 301000):
    symbol = f'{code:06d}'
    A_STOCK_CODES.append({'ts_code': f'{symbol}.SZ', 'symbol': symbol, 'market': '创业板'})

# 沪市主板：600000-601999
for code in range(600000, 602000):
    symbol = f'{code:06d}'
    A_STOCK_CODES.append({'ts_code': f'{symbol}.SH', 'symbol': symbol, 'market': '沪市主板'})

# 沪市主板：603000-603999
for code in range(603000, 604000):
    symbol = f'{code:06d}'
    A_STOCK_CODES.append({'ts_code': f'{symbol}.SH', 'symbol': symbol, 'market': '沪市主板'})

# 科创板：688001-688999
for code in range(688001, 689000):
    symbol = f'{code:06d}'
    A_STOCK_CODES.append({'ts_code': f'{symbol}.SH', 'symbol': symbol, 'market': '科创板'})

print(f'生成 {len(A_STOCK_CODES)} 只 A 股股票代码')
print()
print('分布:')
print(f'  深市主板：{len([s for s in A_STOCK_CODES if s["market"] == "深市主板"])} 只')
print(f'  深市中小板：{len([s for s in A_STOCK_CODES if s["market"] == "深市中小板"])} 只')
print(f'  创业板：{len([s for s in A_STOCK_CODES if s["market"] == "创业板"])} 只')
print(f'  沪市主板：{len([s for s in A_STOCK_CODES if s["market"] == "沪市主板"])} 只')
print(f'  科创板：{len([s for s in A_STOCK_CODES if s["market"] == "科创板"])} 只')

# 保存到文件
import json
with open('a_stock_codes_fixed.json', 'w') as f:
    json.dump(A_STOCK_CODES, f, indent=2)
print()
print('已保存到 a_stock_codes_fixed.json')
