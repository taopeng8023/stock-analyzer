#!/usr/bin/env python3
"""
东方财富主力排名数据 - 优化版
解决编码问题和连接失败问题

优化内容:
1. 多编码支持 (utf-8, gbk, gb2312, utf-8-sig)
2. 增加重试机制 (指数退避)
3. 优化请求头 (模拟真实浏览器)
4. 增加超时时间

鹏总专用 - 2026 年 3 月 27 日
"""

import urllib.request
import urllib.error
import json
import time
from datetime import datetime


def fetch_with_retry(url: str, retry: int = 3, timeout: int = 15) -> dict:
    """
    带重试的 HTTP 请求（支持多编码）
    
    参数:
        url: 请求 URL
        retry: 重试次数
        timeout: 超时时间 (秒)
    
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
    
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw_data = response.read()
                
                # 尝试多种编码
                for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']:
                    try:
                        data = raw_data.decode(encoding)
                        
                        # 清理可能的 var 声明
                        if 'var ' in data:
                            data = data.split('=', 1)[1] if '=' in data else data
                        
                        data = data.strip().strip('"').strip("'")
                        
                        return json.loads(data)
                    
                    except UnicodeDecodeError:
                        continue
                    except json.JSONDecodeError:
                        # 可能是 HTML 错误页面
                        if '<html' in data.lower():
                            raise Exception("返回 HTML 错误页面")
                        continue
                
                # 所有编码都失败了
                raise Exception(f"无法解析数据 (尝试了 utf-8, gbk, gb2312, utf-8-sig)")
        
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP 错误 {e.code}"
            if i < retry - 1:
                delay = 2 ** i  # 指数退避：2, 4, 8 秒
                print(f"{error_msg}，{delay}秒后重试...")
                time.sleep(delay)
            else:
                print(f"请求失败：{error_msg}")
        
        except urllib.error.URLError as e:
            error_msg = f"URL 错误：{e.reason}"
            if i < retry - 1:
                delay = 2 ** i
                print(f"{error_msg}，{delay}秒后重试...")
                time.sleep(delay)
            else:
                print(f"请求失败：{error_msg}")
        
        except Exception as e:
            if i < retry - 1:
                delay = 2 ** i
                print(f"错误：{e}，{delay}秒后重试...")
                time.sleep(delay)
            else:
                print(f"请求失败：{e}")
    
    return {}


def get_main_force_rank_optimized(page: int = 1, page_size: int = 20) -> list:
    """
    获取主力排名（优化版）
    
    参数:
        page: 页码
        page_size: 每页数量
    
    返回:
        主力排名列表
    """
    url = "http://nufm.dfcfw.com/EM_Fund2099/QF_StockStockEm/GetStockDataList"
    
    params = {
        'cb': '',
        'js': 'var',
        'rt': '52776474',
        'mp': '1',
        'p': str(page),
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
    
    query = '&'.join(f"{k}={v}" for k, v in params.items())
    full_url = f"{url}?{query}"
    
    print(f"📊 获取主力排名 (第{page}页)...")
    
    data = fetch_with_retry(full_url, retry=3, timeout=15)
    
    if data:
        # 不同 API 返回格式不同
        if 'data' in data and isinstance(data['data'], list):
            result = data['data']
        elif isinstance(data, list):
            result = data
        else:
            result = []
        
        print(f"✅ 获取成功，共{len(result)}条")
        return result
    
    print("❌ 获取失败")
    return []


def test_all_encodings():
    """测试各种编码"""
    print("\n🧪 测试编码解析...\n")
    
    test_url = "http://nufm.dfcfw.com/EM_Fund2099/QF_StockStockEm/GetStockDataList"
    params = {
        'cb': '',
        'js': 'var',
        'rt': '52776474',
        'mp': '1',
        'p': '1',
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
    
    query = '&'.join(f"{k}={v}" for k, v in params.items())
    full_url = f"{test_url}?{query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    try:
        req = urllib.request.Request(full_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            raw_data = response.read()
            
            print(f"原始数据大小：{len(raw_data)} bytes\n")
            
            # 测试各种编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']
            
            for encoding in encodings:
                try:
                    data = raw_data.decode(encoding)
                    print(f"✅ {encoding}: 解码成功 ({len(data)} 字符)")
                    
                    # 尝试解析 JSON
                    if 'var ' in data:
                        data = data.split('=', 1)[1]
                    data = data.strip().strip('"')
                    
                    json_data = json.loads(data)
                    print(f"   ✅ JSON 解析成功")
                    
                    if isinstance(json_data, dict) and 'data' in json_data:
                        print(f"   📊 数据条数：{len(json_data['data'])}")
                    
                    return True
                
                except Exception as e:
                    print(f"❌ {encoding}: {e}")
            
            return False
    
    except Exception as e:
        print(f"❌ 请求失败：{e}")
        return False


if __name__ == "__main__":
    print("\n📊 东方财富主力排名数据 - 优化版\n")
    print("="*60)
    
    # 测试编码
    print("\n1️⃣ 测试编码解析...\n")
    test_all_encodings()
    
    # 测试数据获取
    print("\n\n2️⃣ 测试数据获取...\n")
    data = get_main_force_rank_optimized(page=1, page_size=10)
    
    if data:
        print(f"\n📊 前 10 条数据:\n")
        for i, stock in enumerate(data[:10], 1):
            if isinstance(stock, dict):
                code = stock.get('f12', 'N/A')
                name = stock.get('f14', 'N/A')
                price = stock.get('f2', 0) or 0
                change = stock.get('f3', 0) or 0
                print(f"{i}. {name}({code}) ¥{price:.2f} ({change:+.2f}%)")
    
    print("\n" + "="*60)
    print("\n✅ 测试完成\n")
