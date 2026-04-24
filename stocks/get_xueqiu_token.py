#!/usr/bin/env python3
"""
雪球 Token 获取工具

使用方法:
1. 运行此脚本
2. 按提示在浏览器登录雪球
3. 复制 Cookie 到脚本中
4. Token 会自动保存到配置文件

注意：出于安全考虑，不建议在脚本中直接写入账号密码
"""

import requests
import os
import json


def get_token_from_browser():
    """
    指导用户从浏览器获取 Token
    """
    print('='*70)
    print('雪球 Token 获取指南')
    print('='*70)
    print()
    print('请按以下步骤操作:')
    print()
    print('1. 打开浏览器 (Chrome/Edge/Firefox)')
    print('2. 访问：https://xueqiu.com/')
    print('3. 使用账号登录 (18610666886)')
    print('4. 按 F12 打开开发者工具')
    print('5. 点击 "Network" (网络) 标签')
    print('6. 刷新页面 (F5)')
    print('7. 在左侧请求列表中找到任意一个请求 (如 "home")')
    print('8. 点击该请求，查看右侧 "Headers" (请求头)')
    print('9. 找到 "Cookie" 字段，复制整个值')
    print()
    print('Cookie 格式示例:')
    print('  xq_a_token=abc123...; xq_r_token=xyz789...; ...')
    print()
    
    # 获取用户输入的 Cookie
    cookie = input('请粘贴 Cookie 内容：').strip()
    
    if not cookie:
        print('❌ Cookie 不能为空')
        return None
    
    # 提取 token
    token = extract_token_from_cookie(cookie)
    
    if token:
        print()
        print(f'✅ 成功提取 Token: {token[:20]}...')
        
        # 保存 Token
        save_token(token)
        
        # 测试 Token
        print()
        print('正在测试 Token...')
        if test_token(token):
            print('✅ Token 有效！')
            return token
        else:
            print('⚠️ Token 可能已过期，请重新获取')
            return None
    else:
        print('❌ 无法从 Cookie 中提取 Token')
        return None


def extract_token_from_cookie(cookie):
    """
    从 Cookie 字符串中提取 xq_a_token
    """
    import re
    
    # 提取 xq_a_token
    match = re.search(r'xq_a_token=([^;]+)', cookie)
    if match:
        return match.group(1).strip()
    
    # 如果没有 xq_a_token，返回整个 cookie
    return cookie


def save_token(token):
    """
    保存 Token 到配置文件
    """
    config_dir = os.path.expanduser('~/.akshare')
    config_path = os.path.join(config_dir, 'xueqiu_token.txt')
    
    # 创建目录
    os.makedirs(config_dir, exist_ok=True)
    
    # 保存 Token
    with open(config_path, 'w') as f:
        f.write(token)
    
    # 设置文件权限 (仅所有者可读写)
    os.chmod(config_path, 0o600)
    
    print(f'✅ Token 已保存到：{config_path}')
    
    # 同时设置环境变量 (当前会话有效)
    os.environ['AKSHARE_XUEQIU_TOKEN'] = token
    print(f'✅ 环境变量已设置 (当前会话有效)')


def test_token(token):
    """
    测试 Token 是否有效
    """
    try:
        import akshare as ak
        
        # 尝试获取一只股票数据
        data = ak.stock_individual_spot_xq(
            symbol='SH600000',  # 浦发银行
            token=token,
            timeout=10
        )
        
        if not data.empty:
            return True
        return False
        
    except Exception as e:
        print(f'测试失败：{e}')
        return False


def auto_login_get_token(phone, password):
    """
    自动登录获取 Token (不推荐，存在安全风险)
    
    注意：此方法可能因雪球反爬机制而失败
    建议使用浏览器手动登录方式
    """
    print()
    print('⚠️ 警告：自动登录可能被雪球反爬机制拦截')
    print('建议使用浏览器手动登录方式')
    print()
    
    session = requests.Session()
    
    # 雪球登录接口 (可能已变更)
    login_url = 'https://xueqiu.com/user/login'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'https://xueqiu.com/',
    }
    
    payload = {
        'username': phone,
        'password': password,
        'remember_me': 'on',
    }
    
    try:
        # 先访问首页获取 cookie
        session.get('https://xueqiu.com/', headers=headers, timeout=10)
        
        # 尝试登录
        resp = session.post(login_url, data=payload, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            # 获取 cookie
            cookie_dict = session.cookies.get_dict()
            
            if 'xq_a_token' in cookie_dict:
                token = cookie_dict['xq_a_token']
                print(f'✅ 自动登录成功！')
                print(f'Token: {token[:20]}...')
                
                # 保存 Token
                save_token(token)
                
                return token
            else:
                print('❌ 登录响应中没有 Token')
                print(f'响应：{resp.text[:200]}')
        else:
            print(f'❌ 登录失败，状态码：{resp.status_code}')
        
    except Exception as e:
        print(f'❌ 自动登录异常：{e}')
    
    print()
    print('自动登录失败，请使用浏览器手动登录方式')
    return None


def main():
    print()
    print('请选择 Token 获取方式:')
    print()
    print('1. 浏览器手动登录 (推荐，成功率高)')
    print('2. 自动登录 (不推荐，可能被反爬拦截)')
    print()
    
    choice = input('请输入选择 (1/2): ').strip()
    
    if choice == '1':
        # 浏览器手动登录
        token = get_token_from_browser()
    elif choice == '2':
        # 自动登录
        print()
        print('⚠️ 出于安全考虑，不建议在此输入密码')
        print('请使用浏览器手动登录方式')
        print()
        print('如果坚持使用自动登录，请修改此脚本，在代码中写入账号密码')
        print('(但不建议这样做，存在安全风险)')
        return
    else:
        print('无效选择')
        return
    
    if token:
        print()
        print('='*70)
        print('✅ Token 获取成功！')
        print('='*70)
        print()
        print('使用方法:')
        print()
        print('1. 在代码中使用:')
        print('   import akshare as ak')
        print('   data = ak.stock_individual_spot_xq(symbol="SH600152")')
        print()
        print('2. Token 已保存到：~/.akshare/xueqiu_token.txt')
        print('3. 环境变量已设置 (当前会话)')
        print()
        print('测试命令:')
        print('   python3.11 akshare_xueqiu_demo.py')
        print()
    else:
        print()
        print('❌ Token 获取失败')


if __name__ == '__main__':
    main()
