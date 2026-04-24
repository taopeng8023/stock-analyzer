#!/usr/bin/env python3
"""
AKShare 东财个股接口使用示例

基于 Python 3.11 + AKShare 1.18.47
"""

import akshare as ak
import time
from datetime import datetime


def get_stock_history(symbol: str, start_date: str = None, end_date: str = None, max_retries: int = 3):
    """
    获取个股历史行情（带重试机制）
    
    Args:
        symbol: 股票代码 (如 '600152')
        start_date: 开始日期 (如 '20260101')
        end_date: 结束日期 (如 '20260327')
        max_retries: 最大重试次数
    
    Returns:
        DataFrame: 历史行情数据
    """
    if not end_date:
        end_date = datetime.now().strftime('%Y%m%d')
    if not start_date:
        start_date = '20250101'
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                delay = 3 * attempt
                print(f'   重试 {attempt}/{max_retries} (等待{delay}秒)...')
                time.sleep(delay)
            
            data = ak.stock_zh_a_hist(
                symbol=symbol,
                period='daily',
                start_date=start_date,
                end_date=end_date,
                adjust='qfq'
            )
            return data
        except Exception as e:
            if attempt == max_retries - 1:
                print(f'   获取失败：{e}')
                return None
            continue


def get_stock_info(symbol: str):
    """
    获取个股基本信息
    
    Args:
        symbol: 股票代码
    
    Returns:
        dict: 股票基本信息
    """
    data = get_stock_history(symbol)
    if data is None or len(data) == 0:
        return None
    
    latest = data.iloc[-1]
    
    return {
        '代码': symbol,
        '名称': latest.get('股票代码', 'N/A'),  # 需要从其他接口获取
        '最新价': latest.get('收盘', 0),
        '开盘': latest.get('开盘', 0),
        '最高': latest.get('最高', 0),
        '最低': latest.get('最低', 0),
        '成交量': latest.get('成交量', 0),
        '成交额': latest.get('成交额', 0),
        '涨跌幅': latest.get('涨跌幅', 0),
        '换手率': latest.get('换手率', 0),
        '数据日期': latest.get('日期', 'N/A'),
    }


def get_industry_sectors():
    """
    获取行业板块列表
    
    Returns:
        DataFrame: 行业板块数据
    """
    try:
        data = ak.stock_board_industry_name_em()
        return data
    except Exception as e:
        print(f'获取失败：{e}')
        return None


def main():
    print('='*70)
    print('AKShare 东财个股接口测试')
    print('='*70)
    print()
    
    # 1. 获取个股历史行情
    print('1. 获取维科技术 (600152) 历史行情...')
    data = get_stock_history('600152', '20260301', '20260327')
    if data is not None:
        print(f'   ✅ 获取到 {len(data)} 条数据')
        print(f'   最新数据：{data.iloc[-1]["日期"]} 收盘¥{data.iloc[-1]["收盘"]:.2f}')
    print()
    
    # 2. 获取多只股票
    print('2. 获取多只股票最新行情...')
    symbols = ['600152', '600089', '002475', '000815', '600930']
    for symbol in symbols:
        info = get_stock_info(symbol)
        if info:
            print(f"   {symbol}: ¥{info['最新价']:.2f} {info['涨跌幅']:+.2f}%")
        time.sleep(1)  # 避免限流
    print()
    
    # 3. 获取行业板块
    print('3. 获取行业板块...')
    sectors = get_industry_sectors()
    if sectors is not None:
        print(f'   ✅ 获取到 {len(sectors)} 个行业板块')
        print('   前 10 个板块:')
        print(sectors.head(10))
    print()
    
    print('='*70)
    print('测试完成！')
    print('='*70)


if __name__ == '__main__':
    main()
