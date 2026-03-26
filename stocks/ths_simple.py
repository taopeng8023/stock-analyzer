#!/usr/bin/env python3
"""
同花顺资金流数据（简单爬虫版）
无需安装额外依赖，使用标准库

⚠️  仅用于个人研究学习
⚠️  数据来自同花顺网页爬虫

用法:
    python3 ths_simple.py --top 10
    python3 ths_simple.py --industry
"""

import requests
import re
import json
from datetime import datetime
from pathlib import Path


class THSSimpleFetcher:
    """同花顺简单爬虫（无需 AKShare）"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'http://data.10jqka.com.cn/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_individual_rank(self, page: int = 1):
        """
        获取个股资金流排行
        
        通过解析同花顺网页获取真实数据
        """
        print(f"[同花顺] 获取个股资金流排行 (第{page}页)...")
        
        # 同花顺资金流排行 URL
        url = f"http://data.10jqka.com.cn/rank/zjlx/field/zljc/order/desc/page/{page}/ajax/1/free/1/"
        
        try:
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'gbk'
            
            if resp.status_code != 200:
                print(f"❌ 请求失败：状态码 {resp.status_code}")
                return None
            
            html = resp.text
            
            # 尝试从 HTML 中提取数据
            # 同花顺数据通常在 script 标签的 JSON 中
            pattern = r'"data":\s*\[(.*?)\]'
            match = re.search(pattern, html, re.DOTALL)
            
            if not match:
                # 尝试直接解析表格
                return self._parse_table(html)
            
            # 解析 JSON 数据
            data_str = '[' + match.group(1) + ']'
            try:
                data = json.loads(data_str)
                print(f"✅ 获取到 {len(data)} 条数据")
                return data
            except:
                return self._parse_table(html)
                
        except Exception as e:
            print(f"❌ 获取失败：{e}")
            return None
    
    def _parse_table(self, html):
        """从 HTML 表格解析数据"""
        print("  尝试从表格解析...")
        
        stocks = []
        
        # 查找表格行
        row_pattern = r'<tr[^>]*>(.*?)</tr>'
        rows = re.findall(row_pattern, html, re.DOTALL)
        
        for row in rows[1:]:  # 跳过表头
            # 提取单元格
            cell_pattern = r'<td[^>]*>(.*?)</td>'
            cells = re.findall(cell_pattern, row, re.DOTALL)
            
            if len(cells) >= 10:
                try:
                    # 清理 HTML 标签
                    cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                    
                    stock = {
                        'rank': cells[0],
                        'code': cells[1],
                        'name': cells[2],
                        'price': cells[3],
                        'change_pct': cells[4],
                        'main_net': cells[5],
                        'main_net_pct': cells[6],
                        'elg_net': cells[7],
                        'lg_net': cells[8],
                        'md_net': cells[9],
                        'sm_net': cells[10] if len(cells) > 10 else '0',
                    }
                    stocks.append(stock)
                except Exception as e:
                    pass
        
        if stocks:
            print(f"  ✅ 解析到 {len(stocks)} 条数据")
        
        return stocks
    
    def get_industry_flow(self):
        """获取行业资金流"""
        print(f"[同花顺] 获取行业资金流...")
        
        url = "http://data.10jqka.com.cn/rank/hyzjlx/field/zljc/order/desc/page/1/ajax/1/free/1/"
        
        try:
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'gbk'
            
            if resp.status_code == 200:
                return self._parse_table(resp.text)
            return None
        except Exception as e:
            print(f"❌ 获取失败：{e}")
            return None
    
    def print_ranking(self, data, title: str = "资金流排行"):
        """打印排行数据"""
        if not data:
            print("无数据")
            return
        
        print(f"\n{'='*90}")
        print(f"💰 {title}")
        print(f"数据源：同花顺 (真实数据)")
        print(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*90}")
        
        print(f"\n{'排名':<4} {'代码':<8} {'名称':<10} {'主力净流入':<12} {'涨跌幅':<8} {'价格':<8}")
        print(f"{'-'*90}")
        
        for item in data[:20]:
            rank = item.get('rank', '')
            code = item.get('code', '')
            name = item.get('name', '')
            main_net = item.get('main_net', '')
            change_pct = item.get('change_pct', '')
            price = item.get('price', '')
            
            print(f"{rank:<4} {code:<8} {name:<10} {main_net:<12} {change_pct:<8} {price:<8}")
        
        print(f"{'='*90}")
        print(f"✅ 数据来自同花顺网页，真实市场数据")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='同花顺资金流数据（简单版，无需 AKShare）')
    parser.add_argument('--top', type=int, default=10, help='前 N 只股票')
    parser.add_argument('--industry', action='store_true', help='行业资金流')
    parser.add_argument('--page', type=int, default=1, help='页码')
    
    args = parser.parse_args()
    
    fetcher = THSSimpleFetcher()
    
    if args.industry:
        data = fetcher.get_industry_flow()
        if data:
            fetcher.print_ranking(data, title="行业资金流排行")
    else:
        data = fetcher.get_individual_rank(page=args.page)
        if data:
            fetcher.print_ranking(data, title=f"个股资金流排行 Top{args.top}")


if __name__ == '__main__':
    main()
