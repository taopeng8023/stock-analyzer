#!/usr/bin/env python3
"""
东方财富数据获取 - 终极优化版
使用 Selenium Wire 拦截网络请求，直接获取 API 数据

核心思路:
1. 使用 selenium-wire 拦截所有网络请求
2. 找到数据 API 请求
3. 直接获取 JSON 数据
4. 绕过页面渲染问题

依赖安装:
pip install selenium-wire

鹏总专用 - 2026 年 3 月 27 日
"""

import json
import time
import os
from datetime import datetime
from typing import List, Dict, Optional

try:
    from seleniumwire import webdriver
    from selenium.webdriver.chrome.options import Options
    SELENIUM_WIRE_AVAILABLE = True
except ImportError:
    SELENIUM_WIRE_AVAILABLE = False
    print("⚠️ selenium-wire 未安装，请先安装：pip install selenium-wire")
    
    # 降级使用普通 Selenium
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options


class UltimateEastmoneyFetcher:
    """终极版东方财富数据获取器"""
    
    def __init__(self, headless=True, intercept_api=True):
        self.headless = headless
        self.intercept_api = intercept_api  # 是否拦截 API
        self.driver = None
        self.captured_data = None
        self.cache_dir = '/home/admin/.openclaw/workspace/stocks/cache/ultimate'
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def init_browser(self):
        """初始化浏览器（终极配置）"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        # 核心配置
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.7632.159 Safari/537.36')
        
        # 反反爬
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 性能优化
        prefs = {
            'profile.managed_default_content_settings.images': 2,
            'profile.default_content_setting_values.stylesheets': 2,
            'profile.default_content_setting_values.notifications': 2,
            'profile.default_content_setting_values.popups': 2,
            'profile.default_content_setting_values.geolocation': 2,
        }
        chrome_options.add_experimental_option('prefs', prefs)
        
        try:
            if SELENIUM_WIRE_AVAILABLE and self.intercept_api:
                # 使用 selenium-wire 拦截请求
                print("🔍 使用 Selenium Wire 拦截模式...")
                self.driver = webdriver.Chrome('/usr/local/bin/chromedriver', options=chrome_options)
            else:
                # 普通 Selenium
                print("🌐 使用普通 Selenium 模式...")
                self.driver = webdriver.Chrome('/usr/local/bin/chromedriver', chrome_options=chrome_options)
            
            # 注入 CDP 命令
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
            
            self.driver.implicitly_wait(10)
            print("✅ 浏览器初始化成功（终极版）")
            return True
        
        except Exception as e:
            print(f"❌ 浏览器初始化失败：{e}")
            return False
    
    def get_data(self, max_retries=5):
        """获取数据（终极版）"""
        if not self.driver:
            if not self.init_browser():
                return []
        
        url = 'http://data.eastmoney.com/zjlx/detail.html'
        
        for attempt in range(max_retries):
            print(f"\n🔄 第 {attempt+1}/{max_retries} 次尝试")
            print("="*70)
            
            try:
                # 清空之前的请求
                if hasattr(self.driver, 'requests'):
                    self.driver.requests.clear()
                
                # 访问页面
                print(f"🌐 访问：{url}")
                self.driver.get(url)
                
                # 等待并触发数据加载
                print("⏳ 等待数据加载...")
                self._smart_wait()
                
                # 尝试 1: 拦截 API 请求
                if SELENIUM_WIRE_AVAILABLE and self.intercept_api:
                    print("🔍 尝试拦截 API 请求...")
                    data = self._intercept_api_request()
                    if data:
                        print(f"✅ 成功拦截 API，获取到 {len(data)} 条数据")
                        self._save_cache(data)
                        return data
                
                # 尝试 2: 从页面提取
                print("📄 尝试从页面提取数据...")
                stocks = self._extract_from_page()
                
                if stocks:
                    print(f"✅ 成功提取 {len(stocks)} 条数据")
                    self._save_cache(stocks)
                    return stocks
                
                # 尝试 3: 执行 JavaScript 获取
                print("⚡ 尝试 JavaScript 获取...")
                js_data = self._get_data_via_js()
                
                if js_data:
                    print(f"✅ JavaScript 获取成功，{len(js_data)} 条数据")
                    self._save_cache(js_data)
                    return js_data
                
                print(f"⚠️ 第{attempt+1}次尝试未获取到数据")
                
                if attempt < max_retries - 1:
                    wait_time = 5 + attempt * 3
                    print(f"🔄 {wait_time}秒后重试...")
                    time.sleep(wait_time)
            
            except Exception as e:
                print(f"❌ 尝试失败：{e}")
                if attempt < max_retries - 1:
                    time.sleep(5 + attempt * 3)
        
        print("\n❌ 所有尝试都失败了")
        return []
    
    def _smart_wait(self):
        """智能等待"""
        try:
            # 阶段 1: 等待页面加载
            time.sleep(3)
            
            # 阶段 2: 滚动触发
            print("   📜 滚动页面触发加载...")
            self.driver.execute_script("window.scrollTo(0, 200);")
            time.sleep(2)
            
            self.driver.execute_script("window.scrollTo(0, 800);")
            time.sleep(2)
            
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            # 阶段 3: 尝试触发数据加载函数
            print("   ⚡ 触发数据加载函数...")
            js_functions = [
                'if(typeof loadData === "function") loadData();',
                'if(typeof init === "function") init();',
                'if(typeof refresh === "function") refresh();',
                'if(typeof getData === "function") getData();',
            ]
            
            for js in js_functions:
                try:
                    self.driver.execute_script(js)
                except:
                    pass
            
            time.sleep(3)
            
            # 阶段 4: 检查是否加载完成
            print("   ✓ 检查数据加载状态...")
            for i in range(5):
                html = self.driver.page_source
                if '60' in html or '00' in html:  # 股票代码特征
                    print(f"   ✅ 检测到股票代码特征")
                    break
                time.sleep(1)
        
        except Exception as e:
            print(f"   ⚠️ 智能等待异常：{e}")
    
    def _intercept_api_request(self) -> Optional[List[Dict]]:
        """拦截 API 请求"""
        try:
            # 查找数据请求
            api_keywords = [
                'push2.eastmoney.com',
                'api/qt/clist/get',
                'f4001',  # 主力净流入字段
                'zjlx',  # 资金流向
            ]
            
            for request in self.driver.requests:
                if any(keyword in request.url for keyword in api_keywords):
                    print(f"   🎯 找到 API 请求：{request.url[:100]}")
                    
                    try:
                        # 获取响应
                        response = request.response
                        if response:
                            body = response.body
                            
                            # 尝试解析
                            try:
                                data = json.loads(body)
                                if 'data' in data and 'diff' in data['data']:
                                    return data['data']['diff']
                            except:
                                pass
                    except Exception as e:
                        print(f"   ⚠️ 解析响应失败：{e}")
            
            print("   ❌ 未找到合适的 API 请求")
            return None
        
        except Exception as e:
            print(f"   ❌ 拦截失败：{e}")
            return None
    
    def _extract_from_page(self) -> List[Dict]:
        """从页面提取数据"""
        stocks = []
        
        try:
            # 多种选择器
            selectors = [
                'table.table tbody tr',
                'table tbody tr',
                '.table tbody tr',
            ]
            
            rows = []
            for selector in selectors:
                try:
                    rows = self.driver.find_elements_by_css_selector(selector)
                    if rows and len(rows) > 0:
                        print(f"   ✅ 找到 {len(rows)} 行数据")
                        break
                except:
                    continue
            
            if not rows:
                print("   ❌ 未找到数据行")
                return []
            
            # 提取数据
            for i, row in enumerate(rows[:50]):
                try:
                    cells = row.find_elements_by_tag_name('td')
                    
                    if len(cells) >= 10:
                        code = cells[1].text.strip()
                        name = cells[2].text.strip()
                        
                        # 验证股票代码
                        if code and (code.startswith('60') or code.startswith('00') or code.startswith('30')):
                            stock = {
                                'code': code,
                                'name': name,
                                'price': self._parse_float(cells[3].text),
                                'change_pct': self._parse_float(cells[4].text.replace('%', '')),
                                'main_force_net': self._parse_money(cells[7].text),
                                'main_force_ratio': self._parse_float(cells[8].text.replace('%', '')),
                            }
                            
                            if stock['price'] > 0:
                                stocks.append(stock)
                
                except Exception as e:
                    continue
            
            return stocks
        
        except Exception as e:
            print(f"   ❌ 页面提取失败：{e}")
            return []
    
    def _get_data_via_js(self) -> Optional[List[Dict]]:
        """通过 JavaScript 获取数据"""
        try:
            # 尝试从全局变量获取
            js_scripts = [
                # 尝试获取全局数据对象
                '''
                (function() {
                    var data = [];
                    // 尝试常见全局变量
                    if(window.stockData) data = window.stockData;
                    else if(window.result) data = window.result;
                    else if(window.data) data = window.data;
                    return JSON.stringify(data);
                })();
                ''',
                
                # 尝试从页面脚本中提取
                '''
                (function() {
                    var scripts = document.getElementsByTagName('script');
                    for(var i=0; i<scripts.length; i++) {
                        var text = scripts[i].text;
                        if(text && text.indexOf('f12') > -1 && text.indexOf('f14') > -1) {
                            // 可能包含数据
                            return text.substring(0, 1000);
                        }
                    }
                    return '';
                })();
                ''',
            ]
            
            for script in js_scripts:
                try:
                    result = self.driver.execute_script(script)
                    if result and len(result) > 10:
                        print(f"   ✓ JavaScript 返回数据：{len(result)} 字符")
                        # 尝试解析
                        try:
                            data = json.loads(result)
                            if isinstance(data, list) and len(data) > 0:
                                return data
                        except:
                            pass
                except:
                    continue
            
            return None
        
        except Exception as e:
            print(f"   ❌ JavaScript 获取失败：{e}")
            return None
    
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
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("✅ 浏览器已关闭")


def test_ultimate_fetcher():
    """测试终极版获取器"""
    print("\n" + "="*70)
    print("📊 测试终极版东方财富数据获取")
    print("="*70 + "\n")
    
    fetcher = UltimateEastmoneyFetcher(headless=True, intercept_api=True)
    
    try:
        stocks = fetcher.get_data(max_retries=5)
        
        if stocks:
            print("\n" + "="*70)
            print(f"🎉 成功获取 {len(stocks)} 条数据！")
            print("="*70)
            print(f"{'序号':<4} {'代码':<8} {'名称':<10} {'价格':<8} {'涨幅':<8} {'主力净额':<12}")
            print("-"*70)
            
            for i, stock in enumerate(stocks[:15], 1):
                print(f"{i:<4} {stock['code']:<8} {stock['name']:<10} "
                      f"¥{stock['price']:<7.2f} {stock['change_pct']:>+7.2f}% "
                      f"{stock['main_force_net']/100000000:>8.2f}亿")
            
            print("-"*70)
            print(f"\n✅ 测试成功！")
            print(f"✅ 数据已保存到：{fetcher.cache_dir}")
        else:
            print("\n" + "="*70)
            print("❌ 未能获取到数据")
            print("="*70)
            print("\n💡 建议:")
            print("   1. 检查网络连接（可能需要国内 IP）")
            print("   2. 安装 selenium-wire: pip install selenium-wire")
            print("   3. 考虑使用 Tushare 等稳定数据源")
    
    finally:
        fetcher.close()
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    test_ultimate_fetcher()
