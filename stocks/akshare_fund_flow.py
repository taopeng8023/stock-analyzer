#!/usr/bin/env python3
"""
AKShare 个股资金流接口使用示例

接口：stock_fund_flow_individual
数据源：同花顺数据中心
https://data.10jqka.com.cn/funds/ggzjl/

用法:
    python3.11 akshare_fund_flow.py
"""

import akshare as ak
import time
import json
from pathlib import Path
from datetime import datetime


def get_fund_flow_rank(period: str = '即时', save_to_file: bool = True) -> dict:
    """
    获取个股资金流排行
    
    Args:
        period: 排行周期
            - 即时：即时资金流
            - 3 日排行：3 日资金流
            - 5 日排行：5 日资金流
            - 10 日排行：10 日资金流
            - 20 日排行：20 日资金流
        save_to_file: 是否保存到文件
    
    Returns:
        资金流数据字典
    """
    print(f'获取{period}资金流排行...')
    
    try:
        data = ak.stock_fund_flow_individual(symbol=period)
        
        print(f'✅ 获取成功！{len(data)} 只股票')
        
        # 转换为字典
        result = {
            'period': period,
            'count': len(data),
            'time': datetime.now().isoformat(),
            'data': data.to_dict('records'),
            'columns': list(data.columns),
        }
        
        # 保存到文件
        if save_to_file:
            cache_dir = Path(__file__).parent / 'cache'
            cache_dir.mkdir(exist_ok=True)
            
            filename = f'fund_flow_{period}_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
            filepath = cache_dir / filename
            
            # 只保存前 100 条以减小文件大小
            result['top100'] = data.head(100).to_dict('records')
            del result['data']  # 删除完整数据
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f'✅ 数据已保存：{filepath}')
        
        return result
        
    except Exception as e:
        print(f'❌ 获取失败：{e}')
        return None


def get_stock_fund_flow(symbol: str) -> dict:
    """
    获取单只股票的资金流数据
    
    Args:
        symbol: 股票代码 (如 '600152')
    
    Returns:
        资金流数据
    """
    print(f'获取 {symbol} 资金流数据...')
    
    try:
        # 获取即时排行，然后筛选
        data = ak.stock_fund_flow_individual(symbol='即时')
        
        # 筛选指定股票
        stock_data = data[data['股票代码'] == symbol]
        
        if stock_data.empty:
            print(f'❌ 未找到 {symbol} 的资金流数据')
            return None
        
        print(f'✅ 获取成功！')
        return stock_data.to_dict('records')[0]
        
    except Exception as e:
        print(f'❌ 获取失败：{e}')
        return None


def analyze_top_stocks(period: str = '即时', top_n: int = 20) -> list:
    """
    分析资金流前 N 只股票
    
    Args:
        period: 排行周期
        top_n: 分析前 N 只
    
    Returns:
        分析结果列表
    """
    print(f'分析{period}资金流前{top_n}只股票...')
    print('='*70)
    
    result = get_fund_flow_rank(period=period, save_to_file=False)
    
    if not result or not result.get('top100'):
        return []
    
    data = result['top100'][:top_n]
    
    print()
    print(f'{"排名":>4} {"代码":<8} {"名称":<12} {"最新价":>8} {"涨幅":>8} {"主力净流入":>12}')
    print('-'*70)
    
    for i, stock in enumerate(data, 1):
        code = stock.get('股票代码', 'N/A')
        name = stock.get('股票名称', 'N/A')
        price = stock.get('最新价', 0)
        change = stock.get('涨跌幅', 0)
        
        # 根据周期选择字段
        if period == '即时':
            flow = stock.get('主力资金净流入', 0)
        else:
            flow = stock.get(f'{period}主力资金净流入', 0)
        
        # 格式化金额
        if abs(flow) >= 100000000:
            flow_str = f'{flow/100000000:.2f}亿'
        elif abs(flow) >= 10000000:
            flow_str = f'{flow/10000:.1f}万'
        else:
            flow_str = f'{flow:.0f}'
        
        print(f'{i:>4} {code:<8} {name:<12} {price:>8.2f} {change:>+7.2f}% {flow_str:>12}')
    
    print()
    print('='*70)
    
    return data


def main():
    print('='*70)
    print('AKShare 个股资金流接口测试')
    print('='*70)
    print()
    
    # 测试 1: 即时资金流
    print('1. 获取即时资金流排行...')
    result = get_fund_flow_rank(period='即时', save_to_file=True)
    if result:
        print(f'   共{result["count"]}只股票')
    print()
    
    # 测试 2: 5 日资金流
    print('2. 获取 5 日资金流排行...')
    time.sleep(2)
    result = get_fund_flow_rank(period='5 日排行', save_to_file=True)
    if result:
        print(f'   共{result["count"]}只股票')
    print()
    
    # 测试 3: 分析前 20 只
    print('3. 分析即时资金流前 20 只股票...')
    time.sleep(2)
    analyze_top_stocks(period='即时', top_n=20)
    print()
    
    # 测试 4: 查询单只股票
    print('4. 查询维科技术 (600152) 资金流...')
    time.sleep(2)
    stock = get_stock_fund_flow('600152')
    if stock:
        print()
        print('资金流数据:')
        for key, value in stock.items():
            print(f'  {key}: {value}')
    print()
    
    print('='*70)
    print('测试完成！')
    print('='*70)


if __name__ == '__main__':
    main()
