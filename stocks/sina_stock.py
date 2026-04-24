#!/usr/bin/env python3
"""
腾讯财经 A 股数据获取脚本
无需 API Key，免费公开接口

用法:
    python sina_stock.py sh600000        # 获取单只股票
    python sina_stock.py sh600000,sz000001  # 获取多只股票
    python sina_stock.py list            # 查看示例代码
"""

import requests
import re
import time
from datetime import datetime


def get_stock_quote(symbols):
    """
    获取股票实时行情 (使用腾讯财经接口)
    
    Args:
        symbols: 股票代码列表，如 ['sh600000', 'sz000001']
                 格式：sh+6 位数字 (沪市) 或 sz+6 位数字 (深市)
    
    Returns:
        list: 股票数据字典列表
    """
    if isinstance(symbols, str):
        symbols = [s.strip() for s in symbols.split(',')]
    
    results = []
    
    # 腾讯财经接口 (返回 GBK 编码)
    symbol_list = ','.join(symbols)
    url = f"https://qt.gtimg.cn/q={symbol_list}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://stockapp.finance.qq.com/'
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'  # 腾讯返回 GBK 编码
        
        for line in resp.text.split('\n'):
            if not line.strip():
                continue
            
            # 解析格式：v_sh600000="51~浦发银行~600000~10.38~10.29~10.27~..."
            match = re.search(r'v_(\w+)="([^"]+)"', line)
            if match:
                symbol = match.group(1)
                fields = match.group(2).split('~')
                
                if len(fields) >= 50:
                    data = {
                        'symbol': symbol,
                        'name': fields[1],
                        'current': float(fields[3]) if fields[3] else 0,   # 当前价格
                        'close': float(fields[4]) if fields[4] else 0,     # 昨收
                        'open': float(fields[5]) if fields[5] else 0,      # 今开
                        'high': float(fields[33]) if fields[33] else 0,    # 最高
                        'low': float(fields[34]) if fields[34] else 0,     # 最低
                        'volume': int(fields[6]) if fields[6] else 0,      # 成交量 (手)
                        'amount_wan': float(fields[7]) if fields[7] else 0,    # 成交额 (万元)
                        'bid': float(fields[10]) if fields[10] else 0,     # 买一价
                        'ask': float(fields[18]) if fields[18] else 0,     # 卖一价
                        'change': float(fields[38]) if fields[38] else 0,  # 涨跌额
                        'change_percent': float(fields[39]) if fields[39] else 0,  # 涨跌幅
                        'time': fields[30] if len(fields) > 30 else '',    # 时间
                    }
                    # 成交额换算
                    data['amount'] = data['amount_wan'] * 10000  # 元
                    
                    results.append(data)
    
    except Exception as e:
        print(f"获取数据失败：{e}")
    
    return results


def format_quote(data):
    """格式化输出股票数据"""
    change_sign = '+' if data.get('change', 0) >= 0 else ''
    
    # 成交额格式化（亿元/万元）
    amount = data.get('amount', 0)
    if amount >= 100_000_000:
        amount_str = f"{amount / 100_000_000:.2f} 亿元"
    else:
        amount_str = f"{amount / 10_000:.2f} 万元"
    
    print(f"\n{'='*50}")
    print(f"{data['name']} ({data['symbol']})")
    print(f"{'='*50}")
    print(f"当前价格：¥{data['current']:.2f}")
    print(f"涨跌幅：  {change_sign}{data.get('change', 0):.2f} ({change_sign}{data.get('change_percent', 0):.2f}%)")
    print(f"今开：    ¥{data['open']:.2f}")
    print(f"昨收：    ¥{data['close']:.2f}")
    print(f"最高：    ¥{data['high']:.2f}")
    print(f"最低：    ¥{data['low']:.2f}")
    print(f"成交量：  {data['volume']:,} 手")
    print(f"成交额：  {amount_str}")
    print(f"买一价：  ¥{data['bid']:.2f}")
    print(f"卖一价：  ¥{data['ask']:.2f}")
    print(f"时间：    {data.get('time', '')}")
    print(f"{'='*50}")


def get_kline(symbol, scale=60, ma=5, no=32):
    """
    获取 K 线数据 (日线)
    
    Args:
        symbol: 股票代码，如 'sh600000'
        scale: K 线类型 60=日线，60=周线，60=月线
        ma: MA 均线
        no: 返回条数
    
    Returns:
        list: K 线数据
    """
    url = "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData/getKLineData"
    params = {
        'symbol': f"{symbol[0]}{symbol[1:]}",  # 去掉 s_ 前缀
        'scale': scale,
        'ma': ma,
        'no': no
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        return resp.json()
    except Exception as e:
        print(f"获取 K 线失败：{e}")
        return []


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        # 默认示例：浦发银行
        symbols = ['sh600000']
    elif sys.argv[1] == 'list':
        print(__doc__)
        print("\n常用股票代码示例:")
        print("  sh600000 - 浦发银行")
        print("  sh600519 - 贵州茅台")
        print("  sz000001 - 平安银行")
        print("  sz000858 - 五粮液")
        print("  sh000001 - 上证指数")
        print("  sz399001 - 深证成指")
        sys.exit(0)
    else:
        symbols = sys.argv[1:]
    
    # 获取数据
    quotes = get_stock_quote(symbols)
    
    if quotes:
        for q in quotes:
            format_quote(q)
    else:
        print("未获取到数据，请检查股票代码或网络连接")
