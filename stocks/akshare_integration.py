#!/usr/bin/env python3
"""
选股系统 - AkShare 数据接口集成
开源财经数据接口库，数据源稳定可靠

安装:
pip install akshare  # 需要 Python 3.9+

如果 Python 版本不够，使用 Tushare:
pip install tushare  # 支持 Python 3.8

鹏总专用 - 2026 年 3 月 27 日
"""

import sys
import os
sys.path.insert(0, '/home/admin/.openclaw/workspace')
sys.path.insert(0, '/home/admin/.openclaw/workspace/stocks')

# 尝试导入 akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    print("✅ AkShare 已安装")
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️ AkShare 未安装（需要 Python 3.9+）")
    print("💡 建议使用 Tushare: pip install tushare")

# 尝试导入 tushare（备用）
try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
    print("✅ Tushare 已安装")
except ImportError:
    TUSHARE_AVAILABLE = False
    print("⚠️ Tushare 未安装")


class AkShareDataFetcher:
    """AkShare 数据获取器"""
    
    def __init__(self):
        self.cache_dir = '/home/admin/.openclaw/workspace/stocks/cache/akshare'
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_main_force_rank(self, date=None):
        """
        获取主力资金排名
        
        参数:
            date: 日期（格式：YYYYMMDD），默认今日
        
        返回:
            主力资金排名列表
        """
        if not AKSHARE_AVAILABLE:
            print("❌ AkShare 未安装")
            return []
        
        try:
            print("📊 使用 AkShare 获取主力资金排名...")
            
            # 获取个股资金流向
            df = ak.stock_individual_fund_flow_rank(indicator="今日")
            
            if df is not None and not df.empty:
                print(f"✅ 获取成功，共{len(df)}条数据")
                
                # 转换为字典列表
                stocks = []
                for _, row in df.head(100).iterrows():
                    try:
                        stock = {
                            'code': str(row.get('代码', '')),
                            'name': str(row.get('名称', '')),
                            'price': float(row.get('最新价', 0) or 0),
                            'change_pct': float(row.get('涨跌幅', 0) or 0),
                            'main_force_net': float(row.get('主力净流入 - 万元', 0) or 0) * 10000,
                            'main_force_ratio': float(row.get('主力净流入占比', 0) or 0),
                        }
                        stocks.append(stock)
                    except Exception as e:
                        continue
                
                print(f"✅ 成功解析 {len(stocks)} 条数据")
                return stocks
            
            else:
                print("❌ 获取数据为空")
                return []
        
        except Exception as e:
            print(f"❌ AkShare 获取失败：{e}")
            return []
    
    def get_sector_rank(self, date=None):
        """
        获取板块资金排名
        
        参数:
            date: 日期
        
        返回:
            板块排名列表
        """
        if not AKSHARE_AVAILABLE:
            return []
        
        try:
            print("🏭 使用 AkShare 获取板块排名...")
            
            # 获取行业资金流向
            df = ak.stock_sector_fund_flow_rank(indicator="10 日", sector_type="行业资金流向")
            
            if df is not None and not df.empty:
                print(f"✅ 板块数据获取成功，共{len(df)}条")
                
                sectors = []
                for _, row in df.head(20).iterrows():
                    try:
                        sector = {
                            'name': str(row.get('板块名称', '')),
                            'change_pct': float(row.get('板块涨跌幅', 0) or 0),
                            'main_force_net': float(row.get('主力资金净流入', 0) or 0),
                        }
                        sectors.append(sector)
                    except:
                        continue
                
                return sectors
            
            return []
        
        except Exception as e:
            print(f"❌ 板块数据获取失败：{e}")
            return []


class TushareDataFetcher:
    """Tushare 数据获取器（备用方案）"""
    
    def __init__(self, token=None):
        self.token = token or 'your_tushare_token'
        self.cache_dir = '/home/admin/.openclaw/workspace/stocks/cache/tushare'
        os.makedirs(self.cache_dir, exist_ok=True)
        
        if TUSHARE_AVAILABLE:
            ts.set_token(self.token)
            self.pro = ts.pro_api()
            print("✅ Tushare 初始化成功")
        else:
            self.pro = None
            print("❌ Tushare 未安装")
    
    def get_main_force_rank(self, date=None):
        """获取主力资金排名"""
        if not self.pro:
            return []
        
        try:
            print("📊 使用 Tushare 获取资金流向...")
            
            # 获取资金流向数据
            df = self.pro.moneyflow(trade_date=date)
            
            if df is not None and not df.empty:
                print(f"✅ 获取成功，共{len(df)}条数据")
                
                # 按主力净流入排序
                df = df.sort_values('buy_sm_amount', ascending=False)
                
                stocks = []
                for _, row in df.head(100).iterrows():
                    try:
                        stock = {
                            'code': str(row.get('ts_code', '')).replace('.SH', '').replace('.SZ', ''),
                            'name': '',  # Tushare 需要额外获取股票名称
                            'price': float(row.get('close', 0) or 0),
                            'change_pct': float(row.get('pct_chg', 0) or 0),
                            'main_force_net': float(row.get('buy_sm_amount', 0) or 0) * 1000,
                        }
                        stocks.append(stock)
                    except:
                        continue
                
                return stocks
            
            return []
        
        except Exception as e:
            print(f"❌ Tushare 获取失败：{e}")
            return []


def test_data_fetchers():
    """测试数据获取器"""
    print("\n" + "="*70)
    print("📊 测试 AkShare/Tushare 数据接口")
    print("="*70 + "\n")
    
    # 测试 AkShare
    if AKSHARE_AVAILABLE:
        print("1️⃣ 测试 AkShare...\n")
        ak_fetcher = AkShareDataFetcher()
        stocks = ak_fetcher.get_main_force_rank()
        
        if stocks:
            print(f"\n📊 AkShare 获取到 {len(stocks)} 条数据")
            print("-"*70)
            print(f"{'序号':<4} {'代码':<8} {'名称':<10} {'价格':<8} {'涨幅':<8} {'主力净额':<12}")
            print("-"*70)
            
            for i, stock in enumerate(stocks[:10], 1):
                print(f"{i:<4} {stock['code']:<8} {stock['name']:<10} "
                      f"¥{stock['price']:<7.2f} {stock['change_pct']:>+7.2f}% "
                      f"{stock['main_force_net']/100000000:>8.2f}亿")
            
            print("-"*70)
        else:
            print("❌ AkShare 未获取到数据")
        
        print()
    
    # 测试 Tushare
    if TUSHARE_AVAILABLE:
        print("2️⃣ 测试 Tushare...\n")
        # 需要配置 Token
        print("⚠️ Tushare 需要配置 Token")
        print("   获取 Token: https://tushare.pro")
        print("   配置：修改代码中的 token='your_tushare_token'\n")
    
    # 总结
    print("="*70)
    if AKSHARE_AVAILABLE:
        print("✅ AkShare 可用！推荐使用")
    elif TUSHARE_AVAILABLE:
        print("✅ Tushare 可用！需要配置 Token")
    else:
        print("❌ 两个库都不可用")
        print("\n💡 建议:")
        print("   1. 升级 Python 到 3.9+ 后安装 AkShare")
        print("   2. 或者安装 Tushare 并配置 Token")
    print("="*70 + "\n")


if __name__ == "__main__":
    test_data_fetchers()
