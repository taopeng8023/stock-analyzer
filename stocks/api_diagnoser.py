#!/usr/bin/env python3
"""
东方财富 API 故障诊断工具
分析失败原因并提供优化方案

鹏总专用 - 2026 年 3 月 27 日
"""

import urllib.request
import urllib.error
import json
import time
import socket
from datetime import datetime


class APIDiagnoser:
    """API 诊断器"""
    
    def __init__(self):
        self.results = []
        self.base_url = "http://push2.eastmoney.com/api/qt/clist/get"
        self.backup_urls = [
            "http://nufm.dfcfw.com/EM_Fund2099/QF_StockStockEm/GetStockDataList",
            "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getRank",
        ]
    
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        self.results.append(log_msg)
    
    def test_network_connectivity(self) -> bool:
        """测试网络连通性"""
        self.log("\n🌐 测试网络连通性...")
        
        try:
            # 测试 DNS 解析
            socket.gethostbyname('data.eastmoney.com')
            self.log("✅ DNS 解析正常")
            
            # 测试网关
            socket.create_connection(('www.baidu.com', 80), timeout=5)
            self.log("✅ 网络连接正常")
            
            return True
        
        except socket.gaierror:
            self.log("❌ DNS 解析失败")
            return False
        
        except socket.timeout:
            self.log("❌ 网络连接超时")
            return False
        
        except Exception as e:
            self.log(f"❌ 网络错误：{e}")
            return False
    
    def test_api_endpoint(self, url: str, timeout: int = 10) -> dict:
        """测试 API 端点"""
        result = {
            'url': url[:80] + '...',
            'status': 'unknown',
            'response_time': 0,
            'error': None,
        }
        
        try:
            start_time = time.time()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'http://data.eastmoney.com/',
                'Connection': 'keep-alive',
            }
            
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = response.read()
                result['response_time'] = (time.time() - start_time) * 1000
                result['status'] = 'success'
                result['data_size'] = len(data)
                
                # 尝试解析 JSON
                try:
                    json_data = json.loads(data.decode('utf-8'))
                    result['json_valid'] = True
                except:
                    try:
                        json_data = json.loads(data.decode('gbk'))
                        result['json_valid'] = True
                    except:
                        result['json_valid'] = False
                        result['error'] = 'JSON 解析失败'
        
        except urllib.error.HTTPError as e:
            result['status'] = 'http_error'
            result['error'] = f'HTTP {e.code}'
        
        except urllib.error.URLError as e:
            result['status'] = 'url_error'
            result['error'] = str(e.reason)
        
        except socket.timeout:
            result['status'] = 'timeout'
            result['error'] = '连接超时'
        
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    def diagnose(self):
        """执行完整诊断"""
        self.log("="*60)
        self.log("🔍 东方财富 API 故障诊断")
        self.log("="*60)
        
        # 1. 网络连通性测试
        network_ok = self.test_network_connectivity()
        
        if not network_ok:
            self.log("\n❌ 网络不通，无法继续测试")
            self.log("\n💡 建议:")
            self.log("   1. 检查网络连接")
            self.log("   2. 检查 DNS 设置")
            self.log("   3. 检查防火墙")
            return
        
        # 2. API 端点测试
        self.log("\n📡 测试 API 端点...")
        
        test_urls = [
            # 主力资金流 API
            f"{self.base_url}?pn=1&pz=5&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f4001&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f12,f14,f2,f3,f4001,f4002&_=1711440000000",
            
            # 备用 API 1
            f"{self.backup_urls[0]}?cb=&js=var&rt=52776474&mp=1&p=1&pz=5&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f4001&fs=m:0+t:6,m:0+t:80&fields=f12,f14,f2,f3,f4001&_=1711440000000",
            
            # 测试百度（确认外网）
            "http://www.baidu.com",
        ]
        
        for i, url in enumerate(test_urls, 1):
            self.log(f"\n[{i}/{len(test_urls)}] 测试：{url[:60]}...")
            result = self.test_api_endpoint(url, timeout=15)
            
            if result['status'] == 'success':
                self.log(f"   ✅ 成功 (响应时间：{result['response_time']:.0f}ms, 数据大小：{result.get('data_size', 0)} bytes)")
                if result.get('json_valid'):
                    self.log(f"   ✅ JSON 格式有效")
                else:
                    self.log(f"   ⚠️ JSON 格式无效")
            else:
                self.log(f"   ❌ 失败：{result['error']}")
        
        # 3. 分析失败原因
        self.log("\n" + "="*60)
        self.log("📊 诊断结果分析")
        self.log("="*60)
        
        self.analyze_results()
        
        # 4. 提供优化建议
        self.log("\n" + "="*60)
        self.log("💡 优化建议")
        self.log("="*60)
        
        self.provide_recommendations()
    
    def analyze_results(self):
        """分析结果"""
        success_count = sum(1 for r in self.results if '✅ 成功' in r)
        error_count = sum(1 for r in self.results if '❌ 失败' in r or '❌' in r)
        
        self.log(f"\n成功：{success_count} 次")
        self.log(f"失败：{error_count} 次")
        
        if error_count > success_count:
            self.log("\n⚠️ 失败次数多于成功次数")
            
            # 分析错误类型
            if any('timeout' in r.lower() for r in self.results):
                self.log("\n🔴 主要原因：连接超时")
                self.log("   - 服务器响应慢")
                self.log("   - 网络延迟高")
            
            if any('http 403' in r.lower() or 'http 429' in r.lower() for r in self.results):
                self.log("\n🔴 主要原因：HTTP 错误")
                self.log("   - 可能被反爬虫机制拦截")
                self.log("   - 请求频率过高")
            
            if any('dns' in r.lower() for r in self.results):
                self.log("\n🔴 主要原因：DNS 问题")
                self.log("   - DNS 解析失败")
                self.log("   - 域名无法访问")
    
    def provide_recommendations(self):
        """提供优化建议"""
        
        self.log("""
1. 🔄 增加重试机制
   - 失败自动重试 3 次
   - 指数退避策略
   - 当前已实现 ✅

2. ⏱️ 优化延迟设置
   - 请求间延迟：2-5 秒
   - 分页延迟：3-6 秒
   - 避免被识别为爬虫

3. 🎭 优化请求头
   - 使用真实浏览器 User-Agent
   - 添加 Referer
   - 模拟正常用户行为

4. 🌐 使用代理 IP
   - 避免单 IP 频繁请求
   - 准备多个代理 IP 池
   - 自动切换

5. 📦 数据缓存
   - 缓存已获取数据
   - 减少重复请求
   - 设置合理过期时间

6. 🔄 多数据源备份
   - 东方财富（主）
   - 新浪财经（备）
   - 同花顺（备）

7. 🕐 优化请求时间
   - 避开高峰期（9:30-10:00）
   - 选择低峰期（14:20-15:00）
   - 分散请求时间

8. 📊 监控与告警
   - 监控 API 成功率
   - 失败自动告警
   - 及时发现问题
""")


if __name__ == "__main__":
    print("\n🔍 东方财富 API 故障诊断工具\n")
    print("="*60)
    
    diagnoser = APIDiagnoser()
    diagnoser.diagnose()
    
    # 保存诊断报告
    report_file = '/home/admin/.openclaw/workspace/stocks/cache/api_diagnosis_report.txt'
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(diagnoser.results))
    
    print(f"\n📁 诊断报告已保存：{report_file}\n")
