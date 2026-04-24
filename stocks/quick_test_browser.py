#!/usr/bin/env python3
"""
快速测试 - 浏览器获取东方财富数据
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

print("📊 测试获取东方财富数据...\n")

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--window-size=1920,1080')

try:
    # 启动浏览器
    driver = webdriver.Chrome('/usr/local/bin/chromedriver', chrome_options=chrome_options)
    print("✅ 浏览器启动成功")
    
    # 访问页面
    print("🌐 访问东方财富资金流向页面...")
    driver.get('http://data.eastmoney.com/zjlx/detail.html')
    
    # 等待加载
    print("⏳ 等待页面加载...")
    time.sleep(5)
    
    # 检查页面标题
    print(f"📄 页面标题：{driver.title}")
    
    # 查找表格
    try:
        rows = driver.find_elements_by_css_selector('table.table tbody tr')
        print(f"✅ 找到 {len(rows)} 行数据\n")
        
        if rows:
            print("📊 前 10 条数据:")
            print("-" * 80)
            
            for i, row in enumerate(rows[:10], 1):
                try:
                    cells = row.find_elements_by_tag_name('td')
                    if len(cells) >= 10:
                        code = cells[1].text
                        name = cells[2].text
                        price = cells[3].text
                        change = cells[4].text
                        main_net = cells[7].text
                        
                        print(f"{i:2d}. {name}({code}) {price}元 ({change}) 主力:{main_net}")
                except Exception as e:
                    continue
            
            print("-" * 80)
            print(f"\n✅ 成功获取到 {min(10, len(rows))} 条数据!")
        
    except Exception as e:
        print(f"❌ 数据提取失败：{e}")
    
    driver.quit()
    print("\n✅ 测试完成")

except Exception as e:
    print(f"❌ 测试失败：{e}")
