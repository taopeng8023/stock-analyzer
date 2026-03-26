#!/usr/bin/env python3
"""
东方财富数据获取 - 多域名轮询版
尝试多个 API 域名，提高成功率

核心思路：
1. 准备多个 API 域名
2. 依次尝试，成功即返回
3. 全部失败才返回错误

鹏总专用 - 2026 年 3 月 27 日
"""

import urllib.request
import urllib.error
import json
import time
from datetime import datetime
from typing import List, Dict, Optional


# API 域名列表
API_DOMAINS = [
    'http://push2.eastmoney.com',
    'http://push2his.eastmoney.com',
    'http://nufm.dfcfw.com',
    'http://data.eastmoney.com',
]


def fetch_with_domains(url_path: str, params: dict, retry: int = 3) -> Optional[dict]:
    """
    多域名轮询获取数据
    
    参数:
        url_path: API 路径
        params: 请求参数
        retry: 重试次数
    
    返回:
        JSON 数据
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'http://data.eastmoney.com/',
        'Connection': 'keep-alive',
    }
    
    query = '&'.join(f"{k}={v}" for k, v in params.items())
    
    print(f"🌐 开始尝试 {len(API_DOMAINS)} 个域名...")
    
    for i, domain in enumerate(API_DOMAINS, 1):
        print(f"\n[{i}/{len(API_DOMAINS)}] 尝试域名：{domain}")
        
        full_url = f"{domain}{url_path}?{query}"
        
        # 尝试多次
        for attempt in range(retry):
            try:
                req = urllib.request.Request(full_url, headers=headers)
                
                with urllib.request.urlopen(req, timeout=15) as response:
                    raw_data = response.read()
                    
                    # 检查是否是 HTML（被拦截）
                    if raw_data.startswith(b'<!DOCTYPE html>') or raw_data.startswith(b'<html'):
                        print(f"   ❌ 返回 HTML 页面（被拦截）")
                        break
                    
                    # 尝试多种编码
                    for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']:
                        try:
                            data = raw_data.decode(encoding)
                            
                            # 清理 var 声明
                            if 'var ' in data:
                                data = data.split('=', 1)[1] if '=' in data else data
                            
                            data = data.strip().strip('"').strip("'")
                            
                            json_data = json.loads(data)
                            
                            print(f"   ✅ 成功！响应大小：{len(data)} bytes")
                            
                            return json_data
                        
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            continue
                    
                    print(f"   ❌ 无法解析数据")
                    break
            
            except urllib.error.HTTPError as e:
                print(f"   ❌ HTTP {e.code}，{attempt+1}/{retry} 重试...")
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)  # 指数退避
            
            except urllib.error.URLError as e:
                print(f"   ❌ URL 错误：{e.reason}")
                break
            
            except Exception as e:
                print(f"   ❌ 错误：{e}")
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)
    
    print(f"\n❌ 所有域名都失败了")
    return None


def get_main_force_rank_multi_domain(page: int = 1, page_size: int = 20) -> List[Dict]:
    """
    获取主力排名（多域名轮询）
    
    参数:
        page: 页码
        page_size: 每页数量
    
    返回:
        主力排名列表
    """
    url_path = "/api/qt/clist/get"
    
    params = {
        'pn': str(page),
        'pz': str(page_size),
        'po': '1',
        'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2',
        'invt': '2',
        'fid': 'f4001',
        'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
        'fields': 'f12,f14,f2,f3,f4001,f4002,f4003,f4004',
        '_': str(int(datetime.now().timestamp() * 1000))
    }
    
    print(f"\n📊 获取主力资金流排名 (第{page}页，{page_size}条)...")
    print("="*60)
    
    data = fetch_with_domains(url_path, params, retry=3)
    
    if data:
        # 提取数据
        if 'data' in data and 'diff' in data['data']:
            stocks = data['data']['diff']
            print(f"\n✅ 获取成功！共{len(stocks)}条数据")
            return stocks
        elif isinstance(data, dict) and 'data' in data:
            stocks = data['data']
            print(f"\n✅ 获取成功！共{len(stocks)}条数据")
            return stocks
    
    print("\n❌ 获取失败")
    return []


def test_all_domains():
    """测试所有域名"""
    print("\n🧪 测试所有 API 域名\n")
    print("="*60)
    
    url_path = "/api/qt/clist/get"
    
    params = {
        'pn': '1',
        'pz': '5',
        'po': '1',
        'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2',
        'invt': '2',
        'fid': 'f4001',
        'fs': 'm:0+t:6,m:0+t:80',
        'fields': 'f12,f14,f2,f3,f4001',
        '_': str(int(datetime.now().timestamp() * 1000))
    }
    
    results = []
    
    for i, domain in enumerate(API_DOMAINS, 1):
        print(f"\n[{i}/{len(API_DOMAINS)}] 测试：{domain}")
        print("-"*60)
        
        full_url = f"{domain}{url_path}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        try:
            start_time = time.time()
            
            req = urllib.request.Request(full_url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=15) as response:
                raw_data = response.read()
                duration = (time.time() - start_time) * 1000
                
                # 检查响应类型
                if raw_data.startswith(b'<!DOCTYPE html>') or raw_data.startswith(b'<html'):
                    print(f"   ❌ 返回 HTML（被拦截）")
                    results.append((domain, 'html', duration))
                
                else:
                    # 尝试解析 JSON
                    try:
                        for encoding in ['utf-8', 'gbk', 'utf-8-sig']:
                            try:
                                data = raw_data.decode(encoding)
                                if 'var ' in data:
                                    data = data.split('=', 1)[1]
                                data = data.strip().strip('"')
                                json_data = json.loads(data)
                                print(f"   ✅ JSON 有效 ({duration:.0f}ms, {len(data)} bytes)")
                                results.append((domain, 'success', duration))
                                break
                            except:
                                continue
                        else:
                            print(f"   ⚠️ 数据但无法解析 JSON")
                            results.append((domain, 'unknown', duration))
                    
                    except Exception as e:
                        print(f"   ❌ 解析失败：{e}")
                        results.append((domain, 'error', duration))
        
        except Exception as e:
            print(f"   ❌ 请求失败：{e}")
            results.append((domain, 'failed', 0))
    
    # 总结
    print("\n" + "="*60)
    print("📊 测试结果总结:")
    print("="*60)
    
    success_count = sum(1 for _, status, _ in results if status == 'success')
    
    for domain, status, duration in results:
        icon = '✅' if status == 'success' else '❌' if status in ['failed', 'html'] else '⚠️'
        print(f"{icon} {domain:40s} - {status} ({duration:.0f}ms)")
    
    print(f"\n成功：{success_count}/{len(API_DOMAINS)}")
    
    return success_count > 0


if __name__ == "__main__":
    print("\n📊 东方财富 API - 多域名轮询测试\n")
    print("="*60)
    
    # 测试所有域名
    print("1️⃣ 测试所有域名可用性...\n")
    test_all_domains()
    
    # 获取数据
    print("\n\n2️⃣ 获取主力排名数据...\n")
    stocks = get_main_force_rank_multi_domain(page=1, page_size=10)
    
    if stocks:
        print(f"\n📊 前 10 条数据:\n")
        for i, stock in enumerate(stocks[:10], 1):
            if isinstance(stock, dict):
                code = stock.get('f12', 'N/A')
                name = stock.get('f14', 'N/A')
                price = stock.get('f2', 0) or 0
                change = stock.get('f3', 0) or 0
                main_net = (stock.get('f4001', 0) or 0) / 100000000
                print(f"{i:2d}. {name}({code}) ¥{price:.2f} ({change:+.2f}%) 主力:{main_net:.2f}亿")
        
        print("\n" + "="*60)
        print("✅ 测试完成！")
    else:
        print("\n❌ 未能获取数据")
        print("\n💡 建议:")
        print("   1. 检查网络连接")
        print("   2. 稍后重试")
        print("   3. 使用浏览器自动化方案")
    
    print("="*60 + "\n")
