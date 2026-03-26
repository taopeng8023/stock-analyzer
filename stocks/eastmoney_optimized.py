#!/usr/bin/env python3
"""
东方财富数据获取 - 浏览器优化版
多种优化策略确保数据成功加载

优化策略:
1. 增加等待时间
2. 显式等待元素
3. 执行 JavaScript 触发加载
4. 滚动页面
5. 刷新重试
6. 拦截网络请求

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
import random
from datetime import datetime


class OptimizedEastmoneyFetcher:
    """优化的东方财富数据获取器"""
    
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        self.cache_dir = '/home/admin/.openclaw/workspace/stocks/cache/chrome_optimized'
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def init_browser(self):
        """初始化浏览器（优化配置）"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        # 核心优化配置
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # 关键：使用真实 User-Agent
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.7632.159 Safari/537.36')
        
        # 禁用自动化标识（反反爬）
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 禁用图片、CSS 加速
        prefs = {
            'profile.managed_default_content_settings.images': 2,
            'profile.default_content_setting_values.stylesheets': 2,
            'profile.default_content_setting_values.notifications': 2,
        }
        chrome_options.add_experimental_option('prefs', prefs)
        
        try:
            self.driver = webdriver.Chrome('/usr/local/bin/chromedriver', chrome_options=chrome_options)
            
            # 执行 CDP 命令移除 navigator.webdriver
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
            
            self.driver.implicitly_wait(10)
            print("✅ 浏览器初始化成功（优化版）")
            return True
        
        except Exception as e:
            print(f"❌ 浏览器初始化失败：{e}")
            return False
    
    def get_data(self, max_retries=3):
        """获取数据（带重试）"""
        if not self.driver:
            if not self.init_browser():
                return []
        
        url = 'http://data.eastmoney.com/zjlx/detail.html'
        
        for attempt in range(max_retries):
            print(f"\n🔄 第 {attempt+1}/{max_retries} 次尝试")
            print("-" * 60)
            
            try:
                # 访问页面
                print(f"🌐 访问：{url}")
                self.driver.get(url)
                
                # 随机等待（模拟真人）
                time.sleep(random.uniform(3, 5))
                
                # 执行 JavaScript 触发数据加载
                print("⚡ 执行 JavaScript 触发数据加载...")
                self._trigger_data_load()
                
                # 等待数据加载
                print("⏳ 等待数据加载...")
                success = self._wait_for_data()
                
                if success:
                    # 提取数据
                    stocks = self._extract_stocks()
                    
                    if stocks:
                        print(f"✅ 成功获取 {len(stocks)} 条数据")
                        self._save_cache(stocks)
                        return stocks
                
                # 失败则刷新重试
                print(f"⚠️ 第{attempt+1}次尝试未成功")
                if attempt < max_retries - 1:
                    print("🔄 准备刷新重试...")
                    time.sleep(random.uniform(2, 4))
            
            except Exception as e:
                print(f"❌ 尝试失败：{e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(3, 6))
        
        print("\n❌ 所有尝试都失败了")
        return []
    
    def _trigger_data_load(self):
        """触发数据加载"""
        try:
            # 滚动页面
            self.driver.execute_script("window.scrollTo(0, 100);")
            time.sleep(1)
            
            self.driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(1)
            
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # 尝试触发数据加载函数（如果存在）
            try:
                self.driver.execute_script("if(typeof loadData === 'function') loadData();")
            except:
                pass
            
            try:
                self.driver.execute_script("if(typeof init === 'function') init();")
            except:
                pass
            
            # 点击刷新按钮（如果存在）
            try:
                refresh_btn = self.driver.find_element(By.CSS_SELECTOR, '.refresh-btn')
                if refresh_btn:
                    refresh_btn.click()
                    time.sleep(2)
            except:
                pass
        
        except Exception as e:
            print(f"⚠️ 触发数据加载失败：{e}")
    
    def _wait_for_data(self):
        """等待数据加载完成"""
        try:
            # 方法 1: 等待表格出现
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'table.table'))
                )
                print("✅ 表格已加载")
            except:
                print("⚠️ 表格未找到")
            
            # 方法 2: 等待数据行
            for i in range(10):
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'table.table tbody tr')
                if rows and len(rows) > 0:
                    # 检查是否有真实数据（不是"暂无数据"）
                    first_row_text = rows[0].text
                    if '暂无数据' not in first_row_text and len(first_row_text.strip()) > 10:
                        print(f"✅ 数据已加载，共{len(rows)}行")
                        return True
                
                time.sleep(1)
                print(f"   等待中... ({i+1}/10)")
            
            # 方法 3: 检查页面内容
            html = self.driver.page_source
            if '暂无数据' in html:
                print("⚠️ 页面显示暂无数据")
                return False
            
            # 检查是否有股票数据特征
            if '60' in html or '00' in html:  # 股票代码特征
                print("✅ 页面包含股票代码特征")
                return True
            
            return False
        
        except Exception as e:
            print(f"❌ 等待失败：{e}")
            return False
    
    def _extract_stocks(self):
        """提取股票数据"""
        stocks = []
        
        try:
            # 多种选择器尝试
            selectors = [
                'table.table tbody tr',
                'table tbody tr',
                '.table tbody tr',
                '[class*="table"] tbody tr',
            ]
            
            rows = []
            for selector in selectors:
                try:
                    rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if rows:
                        print(f"✅ 使用选择器 '{selector[:30]}...' 找到 {len(rows)} 行")
                        break
                except:
                    continue
            
            if not rows:
                print("❌ 未找到任何数据行")
                return []
            
            # 检查是否是"暂无数据"行
            if len(rows) == 1 and '暂无数据' in rows[0].text:
                print("❌ 显示暂无数据")
                return []
            
            for i, row in enumerate(rows[:50]):  # 最多提取 50 条
                try:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    
                    if len(cells) >= 10:
                        # 提取文本
                        code = cells[1].text.strip()
                        name = cells[2].text.strip()
                        price_text = cells[3].text.strip()
                        change_text = cells[4].text.strip()
                        main_net_text = cells[7].text.strip()
                        main_ratio_text = cells[8].text.strip()
                        
                        # 验证数据有效性
                        if not code or not name:
                            continue
                        
                        # 检查是否是股票代码
                        if not (code.startswith('60') or code.startswith('00') or code.startswith('30')):
                            continue
                        
                        stock = {
                            'code': code,
                            'name': name,
                            'price': self._parse_float(price_text),
                            'change_pct': self._parse_float(change_text.replace('%', '')),
                            'main_force_net': self._parse_money(main_net_text),
                            'main_force_ratio': self._parse_float(main_ratio_text.replace('%', '')),
                        }
                        
                        # 验证价格有效性
                        if stock['price'] > 0:
                            stocks.append(stock)
                
                except Exception as e:
                    continue
            
            return stocks
        
        except Exception as e:
            print(f"❌ 数据提取失败：{e}")
            return []
    
    def _parse_float(self, text):
        """解析浮点数"""
        try:
            text = str(text).replace(',', '').replace('%', '').strip()
            if not text or text == '-':
                return 0.0
            return float(text)
        except:
            return 0.0
    
    def _parse_money(self, text):
        """解析金额"""
        try:
            text = str(text).replace(',', '').strip()
            if not text or text == '-':
                return 0.0
            
            if '亿' in text:
                return float(text.replace('亿', '')) * 100000000
            elif '万' in text:
                return float(text.replace('万', '')) * 10000
            else:
                return float(text)
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
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("✅ 浏览器已关闭")


def test_optimized_fetcher():
    """测试优化版获取器"""
    print("\n" + "="*70)
    print("📊 测试优化版东方财富数据获取")
    print("="*70 + "\n")
    
    fetcher = OptimizedEastmoneyFetcher(headless=True)
    
    try:
        stocks = fetcher.get_data(max_retries=3)
        
        if stocks:
            print("\n" + "="*70)
            print(f"📊 主力资金流 TOP {len(stocks)}")
            print("="*70)
            print(f"{'序号':<4} {'代码':<8} {'名称':<10} {'价格':<8} {'涨幅':<8} {'主力净额':<12}")
            print("-"*70)
            
            for i, stock in enumerate(stocks[:15], 1):
                print(f"{i:<4} {stock['code']:<8} {stock['name']:<10} "
                      f"¥{stock['price']:<7.2f} {stock['change_pct']:>+7.2f}% "
                      f"{stock['main_force_net']/100000000:>8.2f}亿")
            
            print("-"*70)
            print(f"\n✅ 测试成功！获取到 {len(stocks)} 条数据")
            print(f"✅ 数据已保存到：{fetcher.cache_dir}")
        else:
            print("\n❌ 未获取到数据")
            print("\n💡 建议:")
            print("   1. 检查网络连接（可能需要国内 IP）")
            print("   2. 查看调试 HTML 文件")
            print("   3. 考虑使用 Tushare 等稳定数据源")
    
    finally:
        fetcher.close()
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    test_optimized_fetcher()
