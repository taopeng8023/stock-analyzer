"""
数据采集模块
使用 AKShare 获取 A 股数据（免费开源）
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time


class DataFetcher:
    """股票数据获取器"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 分钟缓存
    
    def get_stock_info(self, stock_code: str) -> dict:
        """获取股票基本信息"""
        try:
            # 获取实时行情
            if stock_code.startswith('6'):
                symbol = f"sh{stock_code}"
            else:
                symbol = f"sz{stock_code}"
            
            # 实时行情
            quote = ak.stock_zh_a_spot_em()
            stock_data = quote[quote['代码'] == stock_code]
            
            if stock_data.empty:
                return None
            
            return {
                'code': stock_code,
                'name': stock_data['名称'].values[0],
                'price': stock_data['最新价'].values[0],
                'change_pct': stock_data['涨跌幅'].values[0],
                'volume': stock_data['成交量'].values[0],
                'turnover': stock_data['成交额'].values[0],
                'market_cap': stock_data['总市值'].values[0],
                'pe_ttm': stock_data['市盈率 - 动态'].values[0],
                'pb': stock_data['市净率'].values[0],
            }
        except Exception as e:
            print(f"获取股票信息失败：{e}")
            return None
    
    def get_historical_data(self, stock_code: str, days: int = 60) -> pd.DataFrame:
        """获取历史 K 线数据"""
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
            
            # 获取日线数据
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if df.empty:
                return pd.DataFrame()
            
            # 重命名列
            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 
                         'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
            
            return df.sort_values('date').reset_index(drop=True)
        except Exception as e:
            print(f"获取历史数据失败：{e}")
            return pd.DataFrame()
    
    def get_financial_data(self, stock_code: str) -> dict:
        """获取财务数据"""
        try:
            # 获取财务指标
            financial = ak.stock_financial_analysis_indicator(symbol=stock_code)
            
            if financial.empty:
                return None
            
            # 获取最新数据
            latest = financial.iloc[0] if len(financial) > 0 else None
            
            if latest is None:
                return None
            
            return {
                'roe': latest.get('净资产收益率 (%)', 0),
                'revenue_growth': latest.get('营业总收入同比增长率 (%)', 0),
                'profit_growth': latest.get('归属母公司股东的净利润同比增长率 (%)', 0),
                'debt_ratio': latest.get('资产负债率 (%)', 0),
                'gross_margin': latest.get('销售毛利率 (%)', 0),
                'net_margin': latest.get('销售净利率 (%)', 0),
            }
        except Exception as e:
            print(f"获取财务数据失败：{e}")
            return None
    
    def get_money_flow(self, stock_code: str) -> dict:
        """获取资金流向数据"""
        try:
            # 获取资金流向
            flow = ak.stock_individual_fund_flow_rank(indicator="今日")
            
            stock_flow = flow[flow['代码'] == stock_code]
            
            if stock_flow.empty:
                return {
                    'main_force_net': 0,
                    'northbound_net': 0,
                    'retail_net': 0,
                }
            
            return {
                'main_force_net': stock_flow['主力净流入 - 万元'].values[0] / 10000,  # 转亿
                'northbound_net': 0,  # 北向数据需要单独获取
                'retail_net': stock_flow['散户净流入 - 万元'].values[0] / 10000,
            }
        except Exception as e:
            print(f"获取资金流向失败：{e}")
            return {
                'main_force_net': 0,
                'northbound_net': 0,
                'retail_net': 0,
            }
    
    def get_industry_info(self, stock_code: str) -> dict:
        """获取行业信息"""
        try:
            # 获取行业板块
            industry = ak.stock_board_industry_name_em()
            # 这里简化处理，实际需要匹配股票所属行业
            return {
                'industry': '未知',
                'industry_pe': 0,
            }
        except Exception as e:
            print(f"获取行业信息失败：{e}")
            return {
                'industry': '未知',
                'industry_pe': 0,
            }


# 测试用
if __name__ == "__main__":
    fetcher = DataFetcher()
    
    # 测试获取数据
    print("测试数据获取...")
    info = fetcher.get_stock_info("603659")
    print(f"股票信息：{info}")
    
    hist = fetcher.get_historical_data("603659", 30)
    print(f"历史数据条数：{len(hist)}")
    
    financial = fetcher.get_financial_data("603659")
    print(f"财务数据：{financial}")
