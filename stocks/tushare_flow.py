#!/usr/bin/env python3
"""
Tushare 主力资金流数据接口
https://tushare.pro (免费注册获取 Token)

⚠️  仅使用真实市场数据

用法:
    python3 tushare_flow.py --top 10          # 主力净流入排行
    python3 tushare_flow.py --stock 600000.SH # 个股资金流
    python3 tushare_flow.py --config          # 配置 Token
"""

import requests
import json
import os
from datetime import datetime, timedelta
from pathlib import Path


class TushareFetcher:
    """Tushare 数据接口"""
    
    def __init__(self, token=None, cache_dir=None):
        self.cache_dir = cache_dir or Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        # Token 优先级：参数 > 环境变量 > 配置文件
        self.token = token or os.getenv('TUSHARE_TOKEN') or self._load_token()
        
        self.api_url = "http://api.tushare.pro"
        self.headers = {
            'Content-Type': 'application/json',
        }
    
    def _load_token(self) -> str:
        """从配置文件加载 Token"""
        config_file = self.cache_dir / 'tushare_token.txt'
        if config_file.exists():
            with open(config_file, 'r') as f:
                return f.read().strip()
        return ''
    
    def save_token(self, token: str):
        """保存 Token 到配置"""
        config_file = self.cache_dir / 'tushare_token.txt'
        with open(config_file, 'w') as f:
            f.write(token)
        print(f"✅ Token 已保存：{config_file}")
    
    def _request(self, api_name: str, params: dict = None) -> dict:
        """
        调用 Tushare API
        
        Args:
            api_name: API 接口名称
            params: 请求参数
        
        Returns:
            dict: API 返回数据
        """
        payload = {
            "api_name": api_name,
            "token": self.token,
            "params": params or {}
        }
        
        try:
            resp = requests.post(self.api_url, json=payload, headers=self.headers, timeout=15)
            result = resp.json()
            
            if result.get('code') != 0:
                error_msg = result.get('msg', '未知错误')
                print(f"❌ Tushare API 错误：{error_msg}")
                return None
            
            return result.get('data')
            
        except Exception as e:
            print(f"❌ 请求失败：{e}")
            return None
    
    def check_token(self) -> bool:
        """检查 Token 是否有效"""
        if not self.token:
            print("❌ 未设置 Tushare Token")
            print("\n获取 Token 步骤:")
            print("1. 访问 https://tushare.pro")
            print("2. 注册账号并登录")
            print("3. 进入个人中心 -> 获取 Token")
            print("4. 运行：python3 tushare_flow.py --config <your_token>")
            return False
        
        # 尝试调用简单接口测试
        data = self._request('trade_cal', {
            'exchange': 'SSE',
            'start_date': datetime.now().strftime('%Y%m%d'),
            'end_date': datetime.now().strftime('%Y%m%d'),
            'fields': 'cal_date,is_open'
        })
        
        if data:
            print(f"✅ Tushare Token 有效")
            return True
        else:
            print("❌ Tushare Token 无效或已过期")
            return False
    
    def get_moneyflow_rank(self, trade_date: str = None, limit: int = 50) -> list:
        """
        获取个股资金流排行
        
        API: moneyflow
        字段:
            - ts_code: 股票代码
            - trade_date: 交易日期
            - buy_sm_amount: 小单买入金额（万）
            - sell_sm_amount: 小单卖出金额（万）
            - buy_md_amount: 中单买入金额（万）
            - sell_md_amount: 中单卖出金额（万）
            - buy_lg_amount: 大单买入金额（万）
            - sell_lg_amount: 大单卖出金额（万）
            - buy_elg_amount: 特大单买入金额（万）
            - sell_elg_amount: 特大单卖出金额（万）
            - net_mf_amount: 主力资金净流入净额（万）
        
        Args:
            trade_date: 交易日期（YYYYMMDD），默认最新
            limit: 返回数量
        
        Returns:
            list: 资金流数据列表
        """
        print(f"[Tushare] 获取资金流排行...")
        
        if not trade_date:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        data = self._request('moneyflow', {
            'trade_date': trade_date,
            'fields': 'ts_code,trade_date,buy_sm_amount,sell_sm_amount,buy_md_amount,sell_md_amount,buy_lg_amount,sell_lg_amount,buy_elg_amount,sell_elg_amount,net_mf_amount',
            'limit': limit
        })
        
        if not data or not data.get('items'):
            print(f"❌ 获取失败或无数据")
            return []
        
        # 解析数据
        columns = data.get('fields', [])
        items = data.get('items', [])
        
        stocks = []
        for item in items:
            stock = dict(zip(columns, item))
            
            # 计算主力净流入（特大单 + 大单 - 特大单卖出 - 大单卖出）
            net_main = (
                (stock.get('buy_elg_amount') or 0) + 
                (stock.get('buy_lg_amount') or 0) - 
                (stock.get('sell_elg_amount') or 0) - 
                (stock.get('sell_lg_amount') or 0)
            )
            
            # 使用 API 返回的净额（更准确）
            net_mf = stock.get('net_mf_amount') or 0
            
            stocks.append({
                'ts_code': stock.get('ts_code', ''),
                'symbol': self._format_symbol(stock.get('ts_code', '')),
                'trade_date': stock.get('trade_date', ''),
                'net_mf_amount': net_mf,  # 主力净流入净额（万）
                'net_main': net_main * 10000,  # 计算的主力净流入（元）
                'buy_elg': (stock.get('buy_elg_amount') or 0) * 10000,  # 特大单买入（元）
                'sell_elg': (stock.get('sell_elg_amount') or 0) * 10000,  # 特大单卖出（元）
                'buy_lg': (stock.get('buy_lg_amount') or 0) * 10000,  # 大单买入（元）
                'sell_lg': (stock.get('sell_lg_amount') or 0) * 10000,  # 大单卖出（元）
                'source': 'tushare',
                'crawl_time': datetime.now().isoformat(),
            })
        
        # 按主力净流入排序
        stocks.sort(key=lambda x: x.get('net_mf_amount', 0), reverse=True)
        
        print(f"[Tushare] 获取 {len(stocks)} 条资金流数据")
        return stocks
    
    def get_individual_moneyflow(self, ts_code: str, start_date: str = None, 
                                  end_date: str = None) -> list:
        """
        获取个股资金流历史
        
        Args:
            ts_code: 股票代码（如：600000.SH）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
        
        Returns:
            list: 个股资金流历史数据
        """
        print(f"[Tushare] 获取 {ts_code} 资金流历史...")
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        
        data = self._request('moneyflow', {
            'ts_code': ts_code,
            'start_date': start_date,
            'end_date': end_date,
            'fields': 'ts_code,trade_date,buy_sm_amount,sell_sm_amount,buy_md_amount,sell_md_amount,buy_lg_amount,sell_lg_amount,buy_elg_amount,sell_elg_amount,net_mf_amount'
        })
        
        if not data or not data.get('items'):
            print(f"❌ 获取失败或无数据")
            return []
        
        columns = data.get('fields', [])
        items = data.get('items', [])
        
        history = []
        for item in items:
            stock = dict(zip(columns, item))
            history.append({
                'trade_date': stock.get('trade_date', ''),
                'net_mf_amount': stock.get('net_mf_amount') or 0,  # 主力净流入（万）
                'buy_elg': (stock.get('buy_elg_amount') or 0) * 10000,
                'sell_elg': (stock.get('sell_elg_amount') or 0) * 10000,
                'buy_lg': (stock.get('buy_lg_amount') or 0) * 10000,
                'sell_lg': (stock.get('sell_lg_amount') or 0) * 10000,
            })
        
        print(f"[Tushare] 获取 {len(history)} 条历史数据")
        return history
    
    def get_stock_basic(self) -> list:
        """
        获取股票基本信息
        
        Returns:
            list: 股票列表
        """
        print(f"[Tushare] 获取股票列表...")
        
        data = self._request('stock_basic', {
            'fields': 'ts_code,symbol,name,area,industry,list_date'
        })
        
        if not data or not data.get('items'):
            return []
        
        columns = data.get('fields', [])
        items = data.get('items', [])
        
        stocks = []
        for item in items:
            stock = dict(zip(columns, item))
            stocks.append({
                'ts_code': stock.get('ts_code', ''),
                'symbol': stock.get('symbol', ''),
                'name': stock.get('name', ''),
                'industry': stock.get('industry', ''),
            })
        
        print(f"[Tushare] 获取 {len(stocks)} 只股票")
        return stocks
    
    def _format_symbol(self, ts_code: str) -> str:
        """转换 Tushare 代码格式为通用格式"""
        # 600000.SH -> sh600000
        # 000001.SZ -> sz000001
        if not ts_code:
            return ''
        
        parts = ts_code.split('.')
        if len(parts) == 2:
            code = parts[0]
            exchange = parts[1].lower()
            return f"{exchange}{code}"
        
        return ts_code.lower()
    
    def print_ranking(self, stocks: list, top_n: int = 10):
        """打印资金流排行"""
        if not stocks:
            print("无数据")
            return
        
        print(f"\n{'='*100}")
        print(f"💰 Tushare 主力资金净流入排行 Top{min(top_n, len(stocks))}")
        print(f"数据源：Tushare Pro (真实数据)")
        print(f"{'='*100}")
        print(f"{'排名':<4} {'代码':<12} {'名称':<10} {'主力净流入':<14} {'特大单买入':<12} {'特大单卖出':<12}")
        print(f"{'-'*100}")
        
        for i, s in enumerate(stocks[:top_n], 1):
            net = s.get('net_mf_amount') or 0  # 万
            net_str = f"{net/10000:.2f}亿" if abs(net) >= 10000 else f"{net:.0f}万"
            
            buy_elg = s.get('buy_elg') or 0  # 元
            buy_elg_str = f"{buy_elg/100000000:.2f}亿" if buy_elg >= 100000000 else f"{buy_elg/10000:.0f}万"
            
            sell_elg = s.get('sell_elg') or 0  # 元
            sell_elg_str = f"{sell_elg/100000000:.2f}亿" if sell_elg >= 100000000 else f"{sell_elg/10000:.0f}万"
            
            # 获取股票名称
            name = s.get('name', '')
            if not name and s.get('ts_code'):
                name = s['ts_code'][:6]
            
            print(f"{i:<4} {s.get('symbol', s.get('ts_code', '')):<12} {name:<10} "
                  f"💰{net_str:>10} {buy_elg_str:>10} {sell_elg_str:>10}")
        
        print(f"{'='*100}")
        print(f"💰 = Tushare 真实数据")
    
    def print_individual(self, ts_code: str, history: list):
        """打印个股资金流历史"""
        if not history:
            print("无数据")
            return
        
        print(f"\n{'='*80}")
        print(f"💰 {ts_code} 资金流历史")
        print(f"{'='*80}")
        print(f"{'日期':<12} {'主力净流入':<14} {'特大单买入':<12} {'特大单卖出':<12} {'净额':<12}")
        print(f"{'-'*80}")
        
        for h in history[-10:]:  # 显示最近 10 天
            net = h.get('net_mf_amount') or 0
            net_str = f"{net/10000:.2f}亿" if abs(net) >= 10000 else f"{net:.0f}万"
            
            buy_elg = h.get('buy_elg') or 0
            buy_elg_str = f"{buy_elg/100000000:.2f}亿" if buy_elg >= 100000000 else f"{buy_elg/10000:.0f}万"
            
            sell_elg = h.get('sell_elg') or 0
            sell_elg_str = f"{sell_elg/100000000:.2f}亿" if sell_elg >= 100000000 else f"{sell_elg/10000:.0f}万"
            
            # 净额 = 买入 - 卖出
            net_main = buy_elg - sell_elg
            net_main_str = f"{net_main/100000000:.2f}亿" if abs(net_main) >= 100000000 else f"{net_main/10000:.0f}万"
            
            print(f"{h.get('trade_date', ''):<12} {net_str:>12} {buy_elg_str:>10} {sell_elg_str:>10} {net_main_str:>10}")
        
        print(f"{'='*80}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Tushare 主力资金流数据')
    parser.add_argument('--top', type=int, default=10, help='前 N 只股票')
    parser.add_argument('--stock', type=str, help='个股代码 (如：600000.SH)')
    parser.add_argument('--config', type=str, help='配置 Token')
    parser.add_argument('--check', action='store_true', help='检查 Token 状态')
    parser.add_argument('--date', type=str, help='交易日期 (YYYYMMDD)')
    
    args = parser.parse_args()
    
    fetcher = TushareFetcher()
    
    # 配置 Token
    if args.config:
        fetcher.save_token(args.config)
        print("\n✅ Token 配置完成，请运行 --check 验证")
        return
    
    # 检查 Token
    if args.check:
        fetcher.check_token()
        return
    
    # 检查 Token 是否有效
    if not fetcher.check_token():
        print("\n⚠️  请先配置 Tushare Token:")
        print("python3 tushare_flow.py --config <your_token>")
        return
    
    # 个股资金流
    if args.stock:
        ts_code = args.stock.upper()
        if not ts_code.endswith('.SH') and not ts_code.endswith('.SZ'):
            if ts_code.startswith('6'):
                ts_code += '.SH'
            else:
                ts_code += '.SZ'
        
        history = fetcher.get_individual_moneyflow(ts_code)
        if history:
            fetcher.print_individual(ts_code, history)
        return
    
    # 资金流排行
    stocks = fetcher.get_moneyflow_rank(trade_date=args.date, limit=args.top * 2)
    
    if stocks:
        # 获取股票名称
        stock_list = fetcher.get_stock_basic()
        stock_map = {s['ts_code']: s['name'] for s in stock_list}
        
        for s in stocks:
            ts_code = s.get('ts_code', '')
            s['name'] = stock_map.get(ts_code, '')
        
        fetcher.print_ranking(stocks, top_n=args.top)
    else:
        print("\n❌ 无法获取 Tushare 资金流数据")
        print("提示：检查 Token 是否有效，或积分是否足够")


if __name__ == '__main__':
    main()
