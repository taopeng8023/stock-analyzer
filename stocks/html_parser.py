#!/usr/bin/env python3
"""
HTML 解析器模块 - 用于解析财经网站 HTML 数据
使用 Python 标准库，无需额外依赖
"""

from html.parser import HTMLParser
from typing import List, Dict, Optional
import re


class StockTableParser(HTMLParser):
    """股票表格 HTML 解析器"""
    
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.current_cell = ''
        self.rows = []
        self.headers = []
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        if tag == 'table':
            self.in_table = True
        elif tag == 'tr' and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag in ['td', 'th'] and self.in_row:
            self.in_cell = True
            self.current_cell = ''
    
    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
        elif tag == 'tr' and self.in_row:
            self.in_row = False
            if self.current_row:
                if not self.headers:
                    self.headers = self.current_row
                else:
                    self.rows.append(self.current_row)
        elif tag in ['td', 'th'] and self.in_cell:
            self.in_cell = False
            self.current_row.append(self.current_cell.strip())
    
    def handle_data(self, data):
        if self.in_cell:
            self.current_cell += data
    
    def parse(self, html: str) -> List[Dict]:
        """解析 HTML 表格"""
        self.feed(html)
        
        # 转换为字典列表
        results = []
        for row in self.rows:
            if len(row) >= len(self.headers):
                item = {}
                for i, header in enumerate(self.headers):
                    item[header] = row[i] if i < len(row) else ''
                results.append(item)
        
        return results


class SimpleHTMLParser:
    """简单 HTML 解析器"""
    
    @staticmethod
    def extract_table(html: str) -> List[List[str]]:
        """提取 HTML 中的表格数据"""
        parser = StockTableParser()
        parser.parse(html)
        return parser.rows
    
    @staticmethod
    def extract_text_by_class(html: str, class_name: str) -> List[str]:
        """根据 class 名提取文本"""
        pattern = rf'class=["\']?{re.escape(class_name)}["\']?>([^<]+)'
        matches = re.findall(pattern, html)
        return [m.strip() for m in matches]
    
    @staticmethod
    def extract_json_from_html(html: str) -> Optional[Dict]:
        """从 HTML 中提取 JSON 数据"""
        # 查找 <script> 标签中的 JSON
        pattern = r'var\s+\w+\s*=\s*(\{[^}]+\})'
        matches = re.findall(pattern, html)
        
        for match in matches:
            try:
                return eval(match)  # 简单解析
            except:
                continue
        
        return None
    
    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        """从文本中提取数字"""
        pattern = r'[-+]?\d*\.?\d+'
        matches = re.findall(pattern, text)
        return [float(m) for m in matches if m]


# 测试
if __name__ == '__main__':
    test_html = """
    <table>
        <tr><th>代码</th><th>名称</th><th>价格</th></tr>
        <tr><td>600519</td><td>贵州茅台</td><td>1800.00</td></tr>
        <tr><td>000858</td><td>五粮液</td><td>150.00</td></tr>
    </table>
    """
    
    parser = SimpleHTMLParser()
    rows = parser.extract_table(test_html)
    
    print("提取的表格数据:")
    for row in rows:
        print(f"  {row}")
