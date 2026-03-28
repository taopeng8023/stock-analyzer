#!/usr/bin/env python3
"""
AKShare 雪球接口使用示例

注意：需要先获取雪球 Token 才能使用
"""

import akshare as ak
import time
import os


def get_xueqiu_token():
    """
    获取雪球 Token
    
    优先级:
    1. 环境变量 AKSHARE_XUEQIU_TOKEN
    2. 配置文件 ~/.akshare/xueqiu_token.txt
    3. 手动输入
    """
    # 1. 尝试环境变量
    token = os.getenv('AKSHARE_XUEQIU_TOKEN')
    if token:
        print('从环境变量获取 Token')
        return token
    
    # 2. 尝试配置文件
    config_path = os.path.expanduser('~/.akshare/xueqiu_token.txt')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            token = f.read().strip()
        if token:
            print('从配置文件获取 Token')
            return token
    
    # 3. 提示手动输入
    print('未找到 Token，请使用以下方式之一:')
    print('  1. 设置环境变量：export AKSHARE_XUEQIU_TOKEN=your_token')
    print('  2. 创建配置文件：~/.akshare/xueqiu_token.txt')
    print('  3. 直接在代码中传入 token 参数')
    print()
    print('获取 Token 方法:')
    print('  1. 访问 https://xueqiu.com/')
    print('  2. 登录账号')
    print('  3. F12 打开开发者工具')
    print('  4. Network 标签查看请求的 Cookie')
    print()
    
    return None


def test_xueqiu_spot(token, symbol='SH600152'):
    """
    测试雪球个股实时行情
    """
    print(f'测试个股实时行情：{symbol}')
    print('-'*60)
    
    try:
        data = ak.stock_individual_spot_xq(
            symbol=symbol,
            token=token,
            timeout=10
        )
        
        print('✅ 获取成功！')
        print()
        print(data)
        return True
        
    except Exception as e:
        print(f'❌ 获取失败：{e}')
        return False


def test_xueqiu_info(token, symbol='SH600152'):
    """
    测试雪球个股基本信息
    """
    print(f'测试个股基本信息：{symbol}')
    print('-'*60)
    
    try:
        data = ak.stock_individual_basic_info_xq(
            symbol=symbol,
            token=token,
            timeout=10
        )
        
        print('✅ 获取成功！')
        print()
        print(data)
        return True
        
    except Exception as e:
        print(f'❌ 获取失败：{e}')
        return False


def test_batch_stocks(token, symbols=None):
    """
    批量获取股票行情
    """
    if symbols is None:
        symbols = ['SH600152', 'SH600089', 'SZ002475', 'SZ000815', 'SH600930']
    
    print(f'批量获取 {len(symbols)} 只股票行情...')
    print('-'*60)
    
    results = []
    for symbol in symbols:
        try:
            data = ak.stock_individual_spot_xq(
                symbol=symbol,
                token=token,
                timeout=10
            )
            
            if not data.empty:
                current = data['current'].iloc[0] if 'current' in data.columns else 0
                percent = data['percent'].iloc[0] if 'percent' in data.columns else 0
                results.append({
                    'symbol': symbol,
                    'price': current,
                    'change': percent
                })
                print(f"{symbol}: ¥{current:.2f} {percent:+.2f}%")
            
            time.sleep(1)  # 避免限流
            
        except Exception as e:
            print(f"{symbol}: 获取失败 - {e}")
    
    return results


def main():
    print('='*60)
    print('AKShare 雪球接口测试')
    print('='*60)
    print()
    
    # 获取 Token
    token = get_xueqiu_token()
    
    if not token:
        print('❌ 无法获取 Token，测试终止')
        print()
        print('建议使用其他无需认证的接口:')
        print('  - ak.stock_zh_a_hist()  # 东财历史行情')
        print('  - local_crawler.py      # 腾讯/新浪接口')
        return
    
    print()
    
    # 测试 1: 个股实时行情
    test_xueqiu_spot(token, 'SH600152')
    print()
    
    # 测试 2: 个股基本信息
    time.sleep(2)
    test_xueqiu_info(token, 'SH600152')
    print()
    
    # 测试 3: 批量获取
    time.sleep(2)
    results = test_batch_stocks(token)
    print()
    
    print('='*60)
    print('测试完成！')
    print('='*60)


if __name__ == '__main__':
    main()
