#!/usr/bin/env python3
"""
东方财富个股资金流历史数据获取
获取指定股票过去 N 天的主力资金流向数据
"""

import urllib.request
import urllib.error
import json
from datetime import datetime, timedelta
import sys


class StockMoneyFlowHistory:
    """个股资金流历史数据"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://data.eastmoney.com/',
        }
    
    def _fetch(self, url: str) -> dict:
        """获取 JSON 数据"""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                data = response.read().decode('utf-8')
                # 处理 jQuery callback
                if data.startswith('jQuery'):
                    # 提取 JSON 部分
                    start = data.find('(') + 1
                    end = data.rfind(')')
                    data = data[start:end]
                return json.loads(data)
        except Exception as e:
            print(f"请求失败：{e}")
            return {}
    
    def _get_secid(self, code: str) -> str:
        """获取 secid 格式"""
        # 去掉可能的后缀
        code = code.replace('.SZ', '').replace('.SH', '').replace('.BJ', '')
        
        if code.startswith('6'):
            return f"1.{code}"  # 上海
        elif code.startswith(('0', '3')):
            return f"0.{code}"  # 深圳
        elif code.startswith(('8', '4')):
            return f"2.{code}"  # 北京
        else:
            return f"1.{code}"
    
    def get_history_flow(self, code: str, days: int = 30) -> list:
        """
        获取个股资金流历史数据
        
        参数:
            code: 股票代码 (如 002709)
            days: 天数 (默认30天)
        
        返回:
            资金流历史数据列表
        """
        secid = self._get_secid(code)
        
        # 东方财富个股资金流历史 API (有效接口)
        url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
        params = {
            'lmt': str(days),
            'klt': '101',  # 日线
            'secid': secid,
            'fields1': 'f1,f2,f3,f4,f5',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63',
            'ut': 'b2884a393a59ad6400f92eafb616aab8',
            '_': str(int(datetime.now().timestamp() * 1000))
        }
        
        query = '&'.join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query}"
        
        data = self._fetch(full_url)
        
        if data.get('data') and data['data'].get('klines'):
            return self._parse_klines(data['data']['klines'])
        
        return []
    
    def _get_flow_v2(self, code: str, days: int = 30) -> list:
        """备用接口"""
        secid = self._get_secid(code)
        
        url = "https://push2his.eastmoney.com/api/qt/stock/fflow/kline/get"
        params = {
            'cb': 'jQuery',
            'lmt': str(days),
            'klt': '101',
            'secid': secid,
            'fields1': 'f1,f2,f3,f4,f5,f6,f7,f8',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59',
            'ut': 'b2884a393a59ad6400f92eafb616aab8',
            '_': str(int(datetime.now().timestamp() * 1000))
        }
        
        query = '&'.join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query}"
        
        print(f"备用接口 URL: {full_url}")
        
        data = self._fetch(full_url)
        
        if data.get('data') and data['data'].get('klines'):
            return self._parse_klines(data['data']['klines'])
        
        return []
    
    def _parse_klines(self, klines: list) -> list:
        """解析 K 线资金流数据"""
        result = []
        
        for line in klines:
            parts = line.split(',')
            if len(parts) >= 13:
                try:
                    # 格式: 日期,主力净流入,超大单净流入,大单净流入,中单净流入,小单净流入,主力占比,超大单占比,大单占比,中单占比,小单占比,收盘价,涨跌幅
                    item = {
                        '日期': parts[0],
                        '收盘价': float(parts[11]) if parts[11] != '-' else 0,
                        '涨跌幅': float(parts[12]) if parts[12] != '-' else 0,
                        '主力净流入': float(parts[1]) if parts[1] != '-' else 0,
                        '超大单净流入': float(parts[2]) if parts[2] != '-' else 0,
                        '大单净流入': float(parts[3]) if parts[3] != '-' else 0,
                        '中单净流入': float(parts[4]) if parts[4] != '-' else 0,
                        '小单净流入': float(parts[5]) if parts[5] != '-' else 0,
                        '主力净流入占比': float(parts[6]) if parts[6] != '-' else 0,
                        '超大单占比': float(parts[7]) if parts[7] != '-' else 0,
                        '大单占比': float(parts[8]) if parts[8] != '-' else 0,
                        '中单占比': float(parts[9]) if parts[9] != '-' else 0,
                        '小单占比': float(parts[10]) if parts[10] != '-' else 0,
                    }
                    result.append(item)
                except (ValueError, IndexError) as e:
                    print(f"解析错误：{e}, line: {line}")
        
        return result
    
    def print_flow_history(self, data: list, code: str):
        """打印资金流历史数据"""
        if not data:
            print("暂无数据")
            return
        
        print(f"\n{'='*100}")
        print(f"  {code} 资金流历史数据 ({len(data)}天)")
        print(f"  更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*100}")
        print(f"{'日期':<12} {'收盘':>8} {'涨跌%':>7} {'主力净额':>12} {'主力占比':>8} {'超大单':>12} {'大单':>12}")
        print(f"{'':<12} {'':>8} {'':>7} {'(亿元)':>12} {'':>8} {'(亿元)':>12} {'(亿元)':>12}")
        print(f"{'-'*100}")
        
        for item in data:
            main_flow = item['主力净流入'] / 100000000  # 元转亿元
            super_flow = item['超大单净流入'] / 100000000
            big_flow = item['大单净流入'] / 100000000
            flow_icon = "🟢" if main_flow > 0 else "🔴"
            print(f"{item['日期']:<12} {item['收盘价']:>7.2f} {item['涨跌幅']:>6.2f}% {flow_icon}{main_flow:>8.2f}亿 {item['主力净流入占比']:>7.2f}% {super_flow:>8.2f}亿 {big_flow:>8.2f}亿")
        
        print(f"{'='*100}\n")
        
        # 统计分析
        self._print_statistics(data)
    
    def _print_statistics(self, data: list):
        """统计分析"""
        if not data:
            return
        
        # 主力净流入统计
        main_inflows = [d['主力净流入'] / 100000000 for d in data]  # 元转亿元
        
        if main_inflows:
            total_main = sum(main_inflows)
            avg_main = total_main / len(main_inflows)
            positive_days = sum(1 for x in main_inflows if x > 0)
            negative_days = sum(1 for x in main_inflows if x < 0)
            
            print(f"📊 资金流统计分析:")
            print(f"   统计天数：{len(main_inflows)}天")
            print(f"   主力总净流入：{total_main:.2f}亿元")
            print(f"   日均主力净流入：{avg_main:.2f}亿元")
            print(f"   主力净流入天数：{positive_days}天 ({positive_days/len(main_inflows)*100:.1f}%)")
            print(f"   主力净流出天数：{negative_days}天 ({negative_days/len(main_inflows)*100:.1f}%)")
            
            # 最近5天趋势
            recent = data[:5]
            recent_main = [d['主力净流入'] / 100000000 for d in recent]
            recent_total = sum(recent_main)
            
            print(f"\n   最近5天主力净流入：{recent_total:.2f}亿元")
            for r in recent:
                main = r['主力净流入'] / 100000000
                flow_icon = "🟢" if main > 0 else "🔴"
                print(f"   {r['日期']}: {flow_icon}{main:.2f}亿 ({r['主力净流入占比']:.1f}%)")
            
            # 超大单统计
            super_inflows = [d['超大单净流入'] / 100000000 for d in data]
            total_super = sum(super_inflows)
            print(f"\n   超大单总净流入：{total_super:.2f}亿元")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法：python fetch_stock_money_flow_history.py <股票代码> [天数]")
        print("示例：python fetch_stock_money_flow_history.py 002709 30")
        sys.exit(1)
    
    code = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    flow = StockMoneyFlowHistory()
    
    print(f"\n📊 正在获取 {code} 过去 {days} 天资金流数据...\n")
    
    data = flow.get_history_flow(code, days)
    
    flow.print_flow_history(data, code)
    
    # 保存数据
    if data:
        output_file = f"/Users/taopeng/.openclaw/workspace/stocks/data/flow_history_{code}_{datetime.now().strftime('%Y%m%d')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 数据已保存：{output_file}")
    
    print("\n✅ 数据获取完成！\n")


if __name__ == "__main__":
    main()