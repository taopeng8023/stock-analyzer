#!/usr/bin/env python3
"""
东方财富数据获取 - 浏览器自动化版
使用 Selenium 模拟真实浏览器，绕过反爬虫

依赖安装:
pip install selenium webdriver-manager

鹏总专用 - 2026 年 3 月 27 日
"""

import time
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ Selenium 未安装，请先安装：pip install selenium webdriver-manager")


class EastmoneyBrowser:
    """东方财富浏览器自动化"""
    
    def __init__(self, headless: bool = True):
        """
        初始化浏览器
        
        参数:
            headless: 是否无头模式（后台运行）
        """
        self.headless = headless
        self.driver = None
        self.cache_dir = '/home/admin/.openclaw/workspace/stocks/cache/browser'
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def init_browser(self):
        """初始化 Chrome 浏览器"""
        if not SELENIUM_AVAILABLE:
            return False
        
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # 优化配置
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # 禁用图片加载（加速）
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.stylesheets": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            # 使用本地 ChromeDriver (兼容 Selenium 3.x)
            self.driver = webdriver.Chrome('/usr/local/bin/chromedriver', chrome_options=chrome_options)
            
            # 设置隐式等待
            self.driver.implicitly_wait(10)
            
            print("✅ 浏览器初始化成功")
            return True
        
        except Exception as e:
            print(f"❌ 浏览器初始化失败：{e}")
            return False
    
    def get_main_force_rank(self, page: int = 1, page_size: int = 20) -> List[Dict]:
        """
        获取主力资金排名
        
        参数:
            page: 页码
            page_size: 每页数量
        
        返回:
            主力排名列表
        """
        if not self.driver:
            if not self.init_browser():
                return []
        
        url = "http://data.eastmoney.com/zjlx/detail.html"
        
        print(f"📊 访问东方财富资金流向页面...")
        
        try:
            # 访问页面
            self.driver.get(url)
            
            # 等待页面加载
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table"))
            )
            
            # 等待数据加载完成
            time.sleep(3)
            
            print("✅ 页面加载完成，开始提取数据...")
            
            # 提取数据
            stocks = self._extract_stock_data(page_size)
            
            print(f"✅ 成功获取 {len(stocks)} 条数据")
            
            return stocks
        
        except TimeoutException:
            print("❌ 页面加载超时")
            return []
        
        except Exception as e:
            print(f"❌ 获取失败：{e}")
            return []
    
    def _extract_stock_data(self, max_count: int = 20) -> List[Dict]:
        """
        提取股票数据
        
        参数:
            max_count: 最大数量
        
        返回:
            股票数据列表
        """
        stocks = []
        
        try:
            # 查找表格行
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
            
            for row in rows[:max_count]:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) >= 10:
                        stock = {
                            'code': cells[1].text.strip(),  # 代码
                            'name': cells[2].text.strip(),  # 名称
                            'price': self._parse_float(cells[3].text),  # 现价
                            'change_pct': self._parse_float(cells[4].text),  # 涨跌幅
                            'main_force_net': self._parse_money(cells[7].text),  # 主力净额
                            'main_force_ratio': self._parse_float(cells[8].text),  # 主力占比
                            'super_net': self._parse_money(cells[9].text),  # 超大单
                        }
                        
                        stocks.append(stock)
                
                except Exception as e:
                    continue
            
            return stocks
        
        except Exception as e:
            print(f"❌ 数据提取失败：{e}")
            return []
    
    def _parse_float(self, text: str) -> float:
        """解析浮点数"""
        try:
            text = text.replace(',', '').replace('%', '')
            return float(text) if text else 0.0
        except:
            return 0.0
    
    def _parse_money(self, text: str) -> float:
        """解析金额（万/亿）"""
        try:
            text = text.replace(',', '').replace('万', '').replace('亿', '')
            
            if '亿' in text:
                return float(text) * 100000000
            elif '万' in text:
                return float(text) * 10000
            else:
                return float(text) if text else 0.0
        except:
            return 0.0
    
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
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("✅ 浏览器已关闭")


def test_browser_automation():
    """测试浏览器自动化"""
    print("\n🧪 测试浏览器自动化获取数据\n")
    print("="*60)
    
    browser = EastmoneyBrowser(headless=True)
    
    try:
        # 获取数据
        stocks = browser.get_main_force_rank(page=1, page_size=20)
        
        if stocks:
            print(f"\n📊 主力资金流 TOP {len(stocks)}:\n")
            
            for i, stock in enumerate(stocks[:10], 1):
                print(f"{i:2d}. {stock['name']}({stock['code']}) "
                      f"¥{stock['price']:.2f} ({stock['change_pct']:+.2f}%) "
                      f"主力:{stock['main_force_net']/10000:.2f}亿")
            
            # 保存缓存
            browser.save_to_cache(stocks)
            
            print(f"\n✅ 测试成功！获取到 {len(stocks)} 条数据")
        
        else:
            print("\n❌ 未获取到数据")
    
    finally:
        browser.close()
    
    print("="*60)


if __name__ == "__main__":
    test_browser_automation()
