#!/usr/bin/env python3
"""
备用数据源测试模块

测试多个备用财经数据源
"""

import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Optional


class BackupSourcesTester:
    """备用数据源测试器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
        })
        self.results = {}
    
    def test_sina_realtime(self, code: str = '600519') -> bool:
        """测试新浪实时行情"""
        url = f"http://hq.sinajs.cn/list=sh{code}"
        try:
            resp = self.session.get(url, timeout=5)
            content = resp.content.decode('gbk')
            
            if 'sh' + code in content and len(content) > 50:
                self.results['sina_realtime'] = '✅ 可用'
                return True
            else:
                self.results['sina_realtime'] = '❌ 数据异常'
                return False
        except Exception as e:
            self.results['sina_realtime'] = f'❌ {str(e)}'
            return False
    
    def test_netease_realtime(self, code: str = '600519') -> bool:
        """测试网易实时行情"""
        url = f"http://quotes.money.163.com/quote/price/{code}.html"
        try:
            resp = self.session.get(url, timeout=5)
            
            if resp.status_code == 200 and len(resp.text) > 1000:
                self.results['netease_realtime'] = '✅ 可用'
                return True
            else:
                self.results['netease_realtime'] = '❌ 不可用'
                return False
        except Exception as e:
            self.results['netease_realtime'] = f'❌ {str(e)}'
            return False
    
    def test_cnstock(self, code: str = '600519') -> bool:
        """测试中国证券网"""
        url = f"http://app.cnstock.com/api/stock/{code}"
        try:
            resp = self.session.get(url, timeout=5)
            data = resp.json()
            
            if data.get('success'):
                self.results['cnstock'] = '✅ 可用'
                return True
            else:
                self.results['cnstock'] = '❌ API 返回失败'
                return False
        except Exception as e:
            self.results['cnstock'] = f'❌ {str(e)}'
            return False
    
    def test_hexun(self, code: str = '600519') -> bool:
        """测试和讯网财务数据"""
        url = "http://dataapi.hexun.com/FinancialData/GetSummaryData"
        params = {
            'stockCode': code,
            'marketType': '1',
        }
        try:
            resp = self.session.get(url, params=params, timeout=5)
            
            if resp.status_code == 200:
                self.results['hexun'] = '✅ 可用'
                return True
            else:
                self.results['hexun'] = f'❌ 状态码 {resp.status_code}'
                return False
        except Exception as e:
            self.results['hexun'] = f'❌ {str(e)}'
            return False
    
    def test_akshare_api(self) -> bool:
        """测试 AKShare API（如果已安装）"""
        try:
            import akshare as ak
            stock_info = ak.stock_zh_a_spot_em()
            
            if len(stock_info) > 0:
                self.results['akshare'] = '✅ 可用'
                return True
            else:
                self.results['akshare'] = '❌ 无数据'
                return False
        except ImportError:
            self.results['akshare'] = '📝 未安装'
            return False
        except Exception as e:
            self.results['akshare'] = f'❌ {str(e)}'
            return False
    
    def test_tushare_pro(self, token: str = None) -> bool:
        """测试 Tushare Pro"""
        if not token:
            self.results['tushare'] = '📝 未配置 token'
            return False
        
        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()
            
            # 测试获取股票列表
            data = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name')
            
            if len(data) > 0:
                self.results['tushare'] = '✅ 可用'
                return True
            else:
                self.results['tushare'] = '❌ 无数据'
                return False
        except ImportError:
            self.results['tushare'] = '📝 未安装'
            return False
        except Exception as e:
            self.results['tushare'] = f'❌ {str(e)}'
            return False
    
    def test_all_backup_sources(self, tushare_token: str = None) -> Dict[str, str]:
        """测试所有备用数据源"""
        print("\n" + "="*80)
        print("🔧 测试备用数据源")
        print("="*80)
        
        # 1. 新浪实时
        print("\n[1/6] 新浪实时行情...")
        self.test_sina_realtime()
        print(f"  {self.results['sina_realtime']}")
        time.sleep(0.5)
        
        # 2. 网易实时
        print("\n[2/6] 网易实时行情...")
        self.test_netease_realtime()
        print(f"  {self.results['netease_realtime']}")
        time.sleep(0.5)
        
        # 3. 中证网
        print("\n[3/6] 中国证券网...")
        self.test_cnstock()
        print(f"  {self.results['cnstock']}")
        time.sleep(0.5)
        
        # 4. 和讯网
        print("\n[4/6] 和讯网财务...")
        self.test_hexun()
        print(f"  {self.results['hexun']}")
        time.sleep(0.5)
        
        # 5. AKShare
        print("\n[5/6] AKShare...")
        self.test_akshare_api()
        print(f"  {self.results['akshare']}")
        
        # 6. Tushare Pro
        print("\n[6/6] Tushare Pro...")
        self.test_tushare_pro(tushare_token)
        print(f"  {self.results['tushare']}")
        
        # 汇总
        print("\n" + "="*80)
        print("📊 备用数据源测试结果")
        print("="*80)
        
        active = sum(1 for v in self.results.values() if v.startswith('✅'))
        total = len(self.results)
        
        for source, status in self.results.items():
            print(f"{status} {source}")
        
        print(f"\n总计：{active}/{total} 可用")
        
        return self.results


if __name__ == '__main__':
    tester = BackupSourcesTester()
    
    # 可以从配置文件读取 Tushare token
    # tushare_token = 'your_token_here'
    tushare_token = None
    
    tester.test_all_backup_sources(tushare_token)
