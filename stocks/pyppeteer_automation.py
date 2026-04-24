#!/usr/bin/env python3
"""
东方财富数据获取 - Pyppeteer 无头浏览器版
比 Selenium 更轻量，更适合服务器环境

依赖安装:
pip install pyppeteer asyncio

鹏总专用 - 2026 年 3 月 27 日
"""

import asyncio
import json
import os
from datetime import datetime
from typing import List, Dict

try:
    import pyppeteer
    from pyppeteer import launch
    PYPPETEER_AVAILABLE = True
except ImportError:
    PYPPETEER_AVAILABLE = False
    print("⚠️ Pyppeteer 未安装，请先安装：pip install pyppeteer asyncio")


class EastmoneyPyppeteer:
    """东方财富 Pyppeteer 自动化"""
    
    def __init__(self):
        self.browser = None
        self.page = None
        self.cache_dir = '/home/admin/.openclaw/workspace/stocks/cache/pyppeteer'
        os.makedirs(self.cache_dir, exist_ok=True)
    
    async def init(self):
        """初始化浏览器"""
        if not PYPPETEER_AVAILABLE:
            return False
        
        try:
            self.browser = await launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            self.page = await self.browser.newPage()
            
            # 设置 User-Agent
            await self.page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            print("✅ 浏览器初始化成功")
            return True
        
        except Exception as e:
            print(f"❌ 初始化失败：{e}")
            return False
    
    async def get_main_force_rank(self, page: int = 1, page_size: int = 20) -> List[Dict]:
        """获取主力排名"""
        if not self.page:
            if not await self.init():
                return []
        
        url = "http://data.eastmoney.com/zjlx/detail.html"
        
        print(f"📊 访问东方财富资金流向页面...")
        
        try:
            # 访问页面
            await self.page.goto(url, {'waitUntil': 'networkidle0', 'timeout': 30000})
            
            # 等待数据加载
            await self.page.waitForSelector('table.table tbody tr', {'timeout': 10000})
            
            # 额外等待确保数据加载完成
            await asyncio.sleep(3)
            
            print("✅ 页面加载完成，开始提取数据...")
            
            # 提取数据
            stocks = await self._extract_data(page_size)
            
            print(f"✅ 成功获取 {len(stocks)} 条数据")
            
            return stocks
        
        except Exception as e:
            print(f"❌ 获取失败：{e}")
            return []
    
    async def _extract_data(self, max_count: int = 20) -> List[Dict]:
        """提取股票数据"""
        
        # 使用 JavaScript 提取数据
        stocks = await self.page.evaluate(f'''() => {{
            const stocks = [];
            const rows = document.querySelectorAll('table.table tbody tr');
            
            for (let i = 0; i < Math.min(rows.length, {max_count}); i++) {{
                const cells = rows[i].querySelectorAll('td');
                if (cells.length >= 10) {{
                    stocks.push({{
                        code: cells[1].innerText.trim(),
                        name: cells[2].innerText.trim(),
                        price: parseFloat(cells[3].innerText.replace(',', '')) || 0,
                        change_pct: parseFloat(cells[4].innerText.replace(',', '').replace('%', '')) || 0,
                        main_force_net: cells[7].innerText.trim(),
                        main_force_ratio: cells[8].innerText.trim(),
                    }});
                }}
            }}
            
            return stocks;
        }}''')
        
        return stocks
    
    def save_to_cache(self, data: List[Dict], filename: str = None):
        """保存到缓存"""
        if not filename:
            filename = f"main_force_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join(self.cache_dir, filename)
        
        cache_data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'count': len(data),
            'stocks': data,
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        print(f"📁 数据已缓存：{filepath}")
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            print("✅ 浏览器已关闭")


async def test_pyppeteer():
    """测试 Pyppeteer"""
    print("\n🧪 测试 Pyppeteer 浏览器自动化\n")
    print("="*60)
    
    browser = EastmoneyPyppeteer()
    
    try:
        # 获取数据
        stocks = await browser.get_main_force_rank(page=1, page_size=20)
        
        if stocks:
            print(f"\n📊 主力资金流 TOP {len(stocks)}:\n")
            
            for i, stock in enumerate(stocks[:10], 1):
                print(f"{i:2d}. {stock['name']}({stock['code']}) "
                      f"¥{stock['price']:.2f} ({stock['change_pct']:+.2f}%) "
                      f"主力:{stock['main_force_net']}")
            
            # 保存缓存
            browser.save_to_cache(stocks)
            
            print(f"\n✅ 测试成功！获取到 {len(stocks)} 条数据")
        
        else:
            print("\n❌ 未获取到数据")
    
    finally:
        await browser.close()
    
    print("="*60)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(test_pyppeteer())
