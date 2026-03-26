#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用浏览器自动化获取 K 线数据
通过 browser 工具执行 JavaScript 获取真实数据
"""

import json
import os

def get_kline_via_browser(code, name, start_date, end_date):
    """
    通过浏览器获取 K 线数据
    
    在 browser 工具中执行以下 JavaScript：
    
    async () => {
        try {
            const url = 'https://push2.eastmoney.com/api/qt/stock/kline/get';
            const params = {
                secid: '0.002475',
                fields1: 'f1,f2,f3,f4,f5,f6',
                fields2: 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                klt: '101',
                fqt: '1',
                beg: '20250325',
                end: '20260325',
                lmt: '300'
            };
            const queryString = new URLSearchParams(params).toString();
            const resp = await fetch(url + '?' + queryString);
            const data = await resp.json();
            return JSON.stringify(data);
        } catch(e) {
            return 'Error: ' + e.message;
        }
    }
    """
    
    print(f"""
📡 通过浏览器获取 {name}({code}) K 线数据

请在 browser 工具中执行以下命令：

browser action=act kind=evaluate fn="async () => {{
    try {{
        const url = 'https://push2.eastmoney.com/api/qt/stock/kline/get';
        const params = {{
            secid: '{'1.' + code if code.startswith('6') else '0.' + code}',
            fields1: 'f1,f2,f3,f4,f5,f6',
            fields2: 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            klt: '101',
            fqt: '1',
            beg: '{start_date.replace('-', '')}',
            end: '{end_date.replace('-', '')}',
            lmt: '300'
        }};
        const queryString = new URLSearchParams(params).toString();
        const resp = await fetch(url + '?' + queryString);
        const data = await resp.json();
        return JSON.stringify(data);
    }} catch(e) {{
        return 'Error: ' + e.message;
    }}
}}" timeoutMs=20000

""")

def main():
    print("=" * 80)
    print(" " * 25 + "K 线数据获取 - 浏览器方案")
    print("=" * 80)
    
    get_kline_via_browser('002475', '立讯精密', '2025-03-25', '2026-03-25')
    
    print("=" * 80)
    print("说明：")
    print("1. 浏览器环境可以绕过 API 限制")
    print("2. 在 browser 工具中执行上述 JavaScript 代码")
    print("3. 返回的 JSON 数据即为 K 线数据")
    print("=" * 80)

if __name__ == "__main__":
    main()
