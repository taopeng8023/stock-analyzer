#!/usr/bin/env python3
"""
东方财富筹码分布 (CYQ) 接口集成

接口：stock_cyq_em
数据源：东方财富网
https://quote.eastmoney.com/concept/sz000001.html

筹码分布（CYQ）用途:
1. 判断主力持仓成本
2. 识别支撑位和压力位
3. 判断筹码集中度
4. 发现主力吸筹/出货迹象

用法:
    python3.11 akshare_cyq_demo.py
"""

import akshare as ak
import time
from typing import Dict, Optional, List


def get_cyq_data(symbol: str, adjust: str = 'qfq', max_retries: int = 3) -> Optional[Dict]:
    """
    获取个股筹码分布数据
    
    Args:
        symbol: 股票代码 (如 '000001')
        adjust: 复权类型 (qfq/hfq/空)
        max_retries: 最大重试次数
    
    Returns:
        筹码分布数据字典
    """
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                delay = 3 * attempt
                print(f'   重试 {attempt}/{max_retries} (等待{delay}秒)...')
                time.sleep(delay)
            
            data = ak.stock_cyq_em(symbol=symbol, adjust=adjust)
            
            if data is not None and not data.empty:
                # 转换为字典格式
                result = {
                    'symbol': symbol,
                    'data': data.to_dict('records'),
                    'columns': list(data.columns),
                }
                return result
            else:
                return None
                
        except Exception as e:
            if attempt == max_retries - 1:
                print(f'   ❌ 获取失败：{e}')
                return None
            continue
    
    return None


def analyze_cyq(cyq_data: Dict) -> Dict:
    """
    分析筹码分布数据
    
    Args:
        cyq_data: 筹码分布数据
    
    Returns:
        分析结果字典
    """
    if not cyq_data or not cyq_data.get('data'):
        return {'error': '无数据'}
    
    data = cyq_data['data']
    
    # 计算关键指标
    try:
        # 1. 筹码集中度 (90% 筹码的价格区间)
        prices = [item.get('筹码价', 0) for item in data if item.get('筹码价')]
        if not prices:
            return {'error': '无有效数据'}
        
        prices.sort()
        p5_idx = int(len(prices) * 0.05)
        p95_idx = int(len(prices) * 0.95)
        p5 = prices[p5_idx] if p5_idx < len(prices) else prices[-1]
        p95 = prices[p95_idx] if p95_idx < len(prices) else prices[-1]
        
        concentration_range = p95 - p5
        avg_price = sum(prices) / len(prices)
        
        # 2. 筹码集中度 (值越小越集中)
        if avg_price > 0:
            concentration_ratio = concentration_range / avg_price
        else:
            concentration_ratio = 0
        
        # 3. 获利盘比例 (当前价上方的筹码比例)
        current_price = prices[-1] if prices else 0
        profit_chip_count = sum(1 for p in prices if p < current_price)
        profit_ratio = profit_chip_count / len(prices) * 100 if prices else 0
        
        # 4. 平均成本
        avg_cost = avg_price
        
        # 5. 筹码峰值 (最大筹码量的价格)
        max_chip = 0
        peak_price = 0
        for item in data:
            chip = item.get('筹码量', 0)
            if chip > max_chip:
                max_chip = chip
                peak_price = item.get('筹码价', 0)
        
        # 6. 判断主力行为
        if concentration_ratio < 0.2:
            chip_state = '高度集中'
            score = 3
        elif concentration_ratio < 0.4:
            chip_state = '相对集中'
            score = 2
        else:
            chip_state = '分散'
            score = 1
        
        # 7. 与当前价格关系
        if current_price > peak_price * 1.2:
            price_position = '高位 (突破筹码峰)'
        elif current_price < peak_price * 0.8:
            price_position = '低位 (低于筹码峰)'
        else:
            price_position = '震荡 (在筹码峰附近)'
        
        return {
            'symbol': cyq_data.get('symbol'),
            'concentration_range': round(concentration_range, 2),
            'concentration_ratio': round(concentration_ratio, 4),
            'chip_state': chip_state,
            'chip_score': score,
            'profit_ratio': round(profit_ratio, 2),
            'avg_cost': round(avg_cost, 2),
            'peak_price': round(peak_price, 2),
            'price_position': price_position,
            'current_price': current_price,
        }
        
    except Exception as e:
        return {'error': f'分析失败：{e}'}


def cyq_score(cyq_analysis: Dict) -> float:
    """
    筹码分布评分 (0-5 分)
    
    Args:
        cyq_analysis: 筹码分析结果
    
    Returns:
        评分
    """
    if 'error' in cyq_analysis:
        return 0
    
    score = 0.0
    
    # 1. 筹码集中度评分 (0-2 分)
    chip_score = cyq_analysis.get('chip_score', 0)
    score += chip_score
    
    # 2. 获利盘比例评分 (0-2 分)
    profit_ratio = cyq_analysis.get('profit_ratio', 0)
    if profit_ratio > 80:
        score += 2  # 大部分获利，可能回调
    elif profit_ratio > 50:
        score += 1.5
    elif profit_ratio > 30:
        score += 1
    else:
        score += 0.5  # 大部分套牢，可能反弹
    
    # 3. 价格位置评分 (0-1 分)
    price_position = cyq_analysis.get('price_position', '')
    if '低位' in price_position:
        score += 1  # 低位吸筹
    elif '高位' in price_position:
        score += 0.5  # 高位可能出货
    
    return min(score, 5)


def main():
    print('='*70)
    print('东方财富筹码分布 (CYQ) 接口测试')
    print('='*70)
    print()
    
    # 测试股票
    test_symbols = ['000001', '600000', '300059']
    
    for symbol in test_symbols:
        print(f'测试股票：{symbol}')
        print('-'*70)
        
        # 获取数据
        cyq_data = get_cyq_data(symbol=symbol, adjust='qfq')
        
        if cyq_data:
            print(f'✅ 获取成功 ({len(cyq_data["data"])} 个价位)')
            
            # 分析
            analysis = analyze_cyq(cyq_data)
            
            if 'error' not in analysis:
                print()
                print('筹码分析:')
                print(f'  筹码集中度：{analysis["concentration_ratio"]:.4f} ({analysis["chip_state"]})')
                print(f'  获利盘比例：{analysis["profit_ratio"]:.2f}%')
                print(f'  平均成本：¥{analysis["avg_cost"]:.2f}')
                print(f'  筹码峰值：¥{analysis["peak_price"]:.2f}')
                print(f'  价格位置：{analysis["price_position"]}')
                print()
                
                # 评分
                score = cyq_score(analysis)
                print(f'  筹码评分：{score:.1f}/5')
            else:
                print(f'❌ 分析失败：{analysis["error"]}')
        else:
            print('❌ 获取失败')
        
        print()
        time.sleep(2)
    
    print('='*70)
    print('测试完成！')
    print('='*70)


if __name__ == '__main__':
    main()
