#!/usr/bin/env python3
"""
东方财富数据获取 - 浏览器自动化最终版
使用 Selenium + ChromeDriver 获取真实数据

鹏总专用 - 2026 年 3 月 27 日
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os
from datetime import datetime


class EastmoneyDataFetcher:
    """东方财富数据获取器"""
    
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        self.cache_dir = '/home/admin/.openclaw/workspace/stocks/cache/chrome'
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def init_browser(self):
        """初始化浏览器"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        # 优化配置
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.7632.159 Safari/537.36')
        
        # 禁用图片、CSS 加速加载
        prefs = {
            'profile.managed_default_content_settings.images': 2,
            'profile.default_content_setting_values.stylesheets': 2,
        }
        chrome_options.add_experimental_option('prefs', prefs)
        
        try:
            # 使用本地 ChromeDriver
            self.driver = webdriver.Chrome('/usr/local/bin/chromedriver', chrome_options=chrome_options)
            self.driver.implicitly_wait(10)
            print("✅ 浏览器初始化成功")
            return True
        except Exception as e:
            print(f"❌ 浏览器初始化失败：{e}")
            return False
    
    def get_main_force_data(self, page=1, page_size=20):
        """获取主力资金数据"""
        if not self.driver:
            if not self.init_browser():
                return []
        
        try:
            url = 'http://data.eastmoney.com/zjlx/detail.html'
            print(f"🌐 访问：{url}")
            
            self.driver.get(url)
            
            # 等待页面加载
            print("⏳ 等待页面加载...")
            
            # 方法 1: 等待表格出现
            try:
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'table.table'))
                )
                print("✅ 表格已加载")
            except:
                print("⚠️ 表格未找到，继续等待...")
            
            # 额外等待确保数据加载
            time.sleep(5)
            
            # 滚动页面触发数据加载
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            # 获取页面源码
            html = self.driver.page_source
            
            # 检查是否有数据
            if '暂无数据' in html or 'loading' in html.lower():
                print("⚠️ 页面显示暂无数据或正在加载")
            
            # 尝试提取数据
            stocks = self._extract_data(page_size)
            
            if stocks:
                print(f"✅ 成功提取 {len(stocks)} 条数据")
                self._save_cache(stocks)
            else:
                print("⚠️ 未提取到数据，保存 HTML 调试")
                self._save_html(html)
            
            return stocks
        
        except Exception as e:
            print(f"❌ 获取失败：{e}")
            return []
    
    def _extract_data(self, max_count=20):
        """提取股票数据"""
        stocks = []
        
        try:
            # 尝试多种选择器
            selectors = [
                'table.table tbody tr',
                'table tbody tr',
                '.table tbody tr',
            ]
            
            rows = []
            for selector in selectors:
                try:
                    rows = self.driver.find_elements_by_css_selector(selector)
                    if rows:
                        print(f"✅ 使用选择器 '{selector}' 找到 {len(rows)} 行")
                        break
                except:
                    continue
            
            if not rows:
                print("❌ 未找到任何数据行")
                # 调试：打印页面部分内容
                try:
                    body = self.driver.find_element_by_tag_name('body')
                    print(f"页面内容长度：{len(body.text)}")
                    print(f"页面文本前 500 字符：{body.text[:500]}")
                except:
                    pass
                return []
            
            for i, row in enumerate(rows[:max_count]):
                try:
                    cells = row.find_elements_by_tag_name('td')
                    
                    if len(cells) >= 10:
                        stock = {
                            'code': cells[1].text.strip(),
                            'name': cells[2].text.strip(),
                            'price': self._parse_float(cells[3].text),
                            'change_pct': self._parse_float(cells[4].text.replace('%', '')),
                            'main_force_net': self._parse_money(cells[7].text),
                            'main_force_ratio': self._parse_float(cells[8].text.replace('%', '')),
                        }
                        stocks.append(stock)
                except Exception as e:
                    print(f"⚠️ 提取第{i+1}行失败：{e}")
                    continue
            
        except Exception as e:
            print(f"❌ 数据提取失败：{e}")
        
        return stocks
    
    def _parse_float(self, text):
        """解析浮点数"""
        try:
            text = str(text).replace(',', '').replace('%', '').strip()
            return float(text) if text else 0.0
        except:
            return 0.0
    
    def _parse_money(self, text):
        """解析金额"""
        try:
            text = str(text).replace(',', '').strip()
            if '亿' in text:
                return float(text.replace('亿', '')) * 100000000
            elif '万' in text:
                return float(text.replace('万', '')) * 10000
            else:
                return float(text) if text else 0.0
        except:
            return 0.0
    
    def _save_cache(self, stocks):
        """保存缓存"""
        filename = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.cache_dir, filename)
        
        data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'count': len(stocks),
            'stocks': stocks,
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"📁 数据已缓存：{filepath}")
    
    def _save_html(self, html):
        """保存 HTML 调试"""
        filename = f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(self.cache_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"📁 HTML 已保存：{filepath}")
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("✅ 浏览器已关闭")


def test_fetcher():
    """测试数据获取"""
    print("\n" + "="*60)
    print("📊 测试东方财富数据获取")
    print("="*60 + "\n")
    
    fetcher = EastmoneyDataFetcher(headless=True)
    
    try:
        stocks = fetcher.get_main_force_data(page=1, page_size=20)
        
        if stocks:
            print(f"\n📊 主力资金流 TOP {len(stocks)}:\n")
            print("-" * 80)
            print(f"{'序号':<4} {'代码':<8} {'名称':<10} {'价格':<8} {'涨幅':<8} {'主力净额':<12}")
            print("-" * 80)
            
            for i, stock in enumerate(stocks[:10], 1):
                print(f"{i:<4} {stock['code']:<8} {stock['name']:<10} "
                      f"¥{stock['price']:<7.2f} {stock['change_pct']:>+7.2f}% "
                      f"{stock['main_force_net']/100000000:>8.2f}亿")
            
            print("-" * 80)
            print(f"\n✅ 测试成功！获取到 {len(stocks)} 条数据")
        else:
            print("\n❌ 未获取到数据")
            print("\n💡 建议:")
            print("   1. 检查网络连接")
            print("   2. 增加等待时间")
            print("   3. 查看调试 HTML 文件")
    
    finally:
        fetcher.close()
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    test_fetcher()
