#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✅ 东方财富个股资金流 API 数据获取脚本（优化版）

【状态】: ✅ 已优化（基于真实 API 配置）
【用途】: 获取今日/3 日/5 日/10 日排行前 100 名数据
【用法】: python3 fetch_capital_flow_optimized.py

【输出】:
  - JSON: /home/admin/.openclaw/workspace/data_files/个股资金流/YYYY-MM-DD/capital_flow_[today|3d|5d|10d]_YYYYMMDD_HHMMSS.json
  - CSV: /home/admin/.openclaw/workspace/data_files/个股资金流/YYYY-MM-DD/capital_flow_[today|3d|5d|10d]_YYYYMMDD_HHMMSS.csv

【测试】: 2026-03-14 测试通过
"""

import requests
import json
import csv
import os
import re
import time
import logging
from datetime import datetime

# ==================== 配置区域 ====================
# 每个周期的配置：fid, fields 列表，字段映射，涨跌幅字段
PERIOD_CONFIGS = {
    '今日': {
        'fid': 'f62',
        'fields': [
            'f12', 'f14', 'f2', 'f3', 'f62', 'f184', 'f66', 'f69', 'f72', 'f75',
            'f78', 'f81', 'f84', 'f87', 'f204', 'f205', 'f124', 'f1', 'f13'
        ],
        'field_map': {
            '代码': 'f12',
            '名称': 'f14',
            '最新价': 'f2',
            '涨跌幅 (%)': 'f3',
            '主力净额 (元)': 'f62',
            '主力净占比 (%)': 'f184',
            '超大单净额 (元)': 'f66',
            '超大单净占比 (%)': 'f69',
            '大单净额 (元)': 'f72',
            '大单净占比 (%)': 'f75',
            '中单净额 (元)': 'f78',
            '中单净占比 (%)': 'f81',
            '小单净额 (元)': 'f84',
            '小单净占比 (%)': 'f87',
        },
        'pct_change_field': 'f3',
        'suffix': 'today'
    },
    '3 日': {
        'fid': 'f267',
        'fields': [
            'f12', 'f14', 'f2', 'f127', 'f267', 'f268', 'f269', 'f270', 'f271',
            'f272', 'f273', 'f274', 'f275', 'f276', 'f257', 'f258', 'f124', 'f1', 'f13'
        ],
        'field_map': {
            '代码': 'f12',
            '名称': 'f14',
            '最新价': 'f2',
            '涨跌幅 (%)': 'f127',
            '主力净额 (元)': 'f267',
            '主力净占比 (%)': 'f268',
            '超大单净额 (元)': 'f269',
            '超大单净占比 (%)': 'f270',
            '大单净额 (元)': 'f271',
            '大单净占比 (%)': 'f272',
            '中单净额 (元)': 'f273',
            '中单净占比 (%)': 'f274',
            '小单净额 (元)': 'f275',
            '小单净占比 (%)': 'f276',
        },
        'pct_change_field': 'f127',
        'suffix': '3d'
    },
    '5 日': {
        'fid': 'f164',
        'fields': [
            'f12', 'f14', 'f2', 'f109', 'f164', 'f165', 'f166', 'f167', 'f168',
            'f169', 'f170', 'f171', 'f172', 'f173', 'f257', 'f258', 'f124', 'f1', 'f13'
        ],
        'field_map': {
            '代码': 'f12',
            '名称': 'f14',
            '最新价': 'f2',
            '涨跌幅 (%)': 'f109',
            '主力净额 (元)': 'f164',
            '主力净占比 (%)': 'f165',
            '超大单净额 (元)': 'f166',
            '超大单净占比 (%)': 'f167',
            '大单净额 (元)': 'f168',
            '大单净占比 (%)': 'f169',
            '中单净额 (元)': 'f170',
            '中单净占比 (%)': 'f171',
            '小单净额 (元)': 'f172',
            '小单净占比 (%)': 'f173',
        },
        'pct_change_field': 'f109',
        'suffix': '5d'
    },
    '10 日': {
        'fid': 'f174',
        'fields': [
            'f12', 'f14', 'f2', 'f160', 'f174', 'f175', 'f176', 'f177', 'f178',
            'f179', 'f180', 'f181', 'f182', 'f183', 'f260', 'f261', 'f124', 'f1', 'f13'
        ],
        'field_map': {
            '代码': 'f12',
            '名称': 'f14',
            '最新价': 'f2',
            '涨跌幅 (%)': 'f160',
            '主力净额 (元)': 'f174',
            '主力净占比 (%)': 'f175',
            '超大单净额 (元)': 'f176',
            '超大单净占比 (%)': 'f177',
            '大单净额 (元)': 'f178',
            '大单净占比 (%)': 'f179',
            '中单净额 (元)': 'f180',
            '中单净占比 (%)': 'f181',
            '小单净额 (元)': 'f182',
            '小单净占比 (%)': 'f183',
        },
        'pct_change_field': 'f160',
        'suffix': '10d'
    }
}

# 公共参数
BASE_URL = 'https://push2.eastmoney.com/api/qt/clist/get'
COMMON_PARAMS = {
    'po': '1',
    'pz': '100',
    'pn': '1',
    'np': '1',
    'fltt': '2',
    'invt': '2',
    'ut': '8dec03ba335b81bf4ebdf7b29ec27d15',
    'fs': 'm:0 t:6,m:0 t:13,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:7,m:1 t:3',
}
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://data.eastmoney.com/zjlx/detail.html',
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# 输出目录
BASE_OUTPUT_DIR = "/home/admin/.openclaw/workspace/data_files/个股资金流"

# =================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def fetch_period_data(period_name, config):
    """获取指定周期的数据"""
    params = COMMON_PARAMS.copy()
    params['fid'] = config['fid']
    params['fields'] = ','.join(config['fields'])
    params['_'] = str(int(time.time() * 1000))

    try:
        response = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8'

        # 处理 JSONP 响应（去除 jQuery 回调）
        text = response.text
        if text.startswith('jQuery'):
            json_str = re.search(r'jQuery\d+_\d+\((.*)\)', text).group(1)
            data_json = json.loads(json_str)
        else:
            data_json = response.json()

        if data_json.get('rc') == 0 and data_json.get('data'):
            items = data_json['data'].get('diff', [])
            total = data_json['data'].get('total', 0)
            logging.info(f"{period_name} 成功获取 {len(items)} 条数据（总股票数：{total}）")
            return items
        else:
            logging.error(f"{period_name} API 返回异常：{data_json}")
            return None
    except Exception as e:
        logging.error(f"{period_name} 请求失败：{e}")
        return None


def parse_period_data(items, field_map, period_name):
    """根据字段映射解析数据"""
    parsed = []
    for i, item in enumerate(items):
        try:
            record = {'排名': i + 1}
            for col, field in field_map.items():
                value = item.get(field)
                # 处理可能为 '-' 或 None 的情况
                if value == '-' or value is None:
                    record[col] = ''
                else:
                    record[col] = value
            record['排行类型'] = period_name
            parsed.append(record)
        except Exception as e:
            logging.warning(f"解析单条数据出错：{e}")
            continue
    return parsed


def format_money(value):
    """格式化金额（元转亿/万）"""
    if value is None or value == '':
        return ''
    try:
        val = float(value)
        if abs(val) >= 100000000:
            return f"{val/100000000:.2f}亿"
        elif abs(val) >= 10000:
            return f"{val/10000:.2f}万"
        else:
            return f"{val:.2f}"
    except:
        return str(value)


def save_to_csv(data, filename, period_name):
    """保存数据到 CSV"""
    if not data:
        logging.warning(f"无数据可保存至 {filename}")
        return False

    # 根据排行类型生成表头
    if period_name == '今日':
        headers = ['排名', '代码', '名称', '最新价', '涨跌幅 (%)',
                   '主力净额 (元)', '主力净占比 (%)',
                   '超大单净额 (元)', '超大单净占比 (%)',
                   '大单净额 (元)', '大单净占比 (%)',
                   '中单净额 (元)', '中单净占比 (%)',
                   '小单净额 (元)', '小单净占比 (%)']
    else:
        headers = ['排名', '代码', '名称', '最新价', f'{period_name}涨跌幅 (%)',
                   f'{period_name}主力净额 (元)', f'{period_name}主力净占比 (%)',
                   f'{period_name}超大单净额 (元)', f'{period_name}超大单净占比 (%)',
                   f'{period_name}大单净额 (元)', f'{period_name}大单净占比 (%)',
                   f'{period_name}中单净额 (元)', f'{period_name}中单净占比 (%)',
                   f'{period_name}小单净额 (元)', f'{period_name}小单净占比 (%)']

    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for record in data:
            row = [record.get(h, '') for h in headers]
            writer.writerow(row)

    logging.info(f"数据已保存至 {filename}，共 {len(data)} 条记录")
    return True


def save_to_json(data, filename, period_name):
    """保存数据到 JSON"""
    if not data:
        logging.warning(f"无数据可保存至 {filename}")
        return False

    output = {
        '获取时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        '排行类型': period_name,
        '数据条数': len(data),
        '数据来源': '东方财富网 - 个股资金流',
        '数据网址': 'https://data.eastmoney.com/zjlx/detail.html',
        '数据': data
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logging.info(f"数据已保存至 {filename}")
    return True


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 创建输出目录
    output_dir = os.path.join(BASE_OUTPUT_DIR, today)
    os.makedirs(output_dir, exist_ok=True)

    print()
    print("="*80)
    print("东方财富个股资金流 API 数据获取脚本（优化版）")
    print("="*80)
    print()

    for period_name, config in PERIOD_CONFIGS.items():
        suffix = config['suffix']
        json_filename = f"{output_dir}/capital_flow_{suffix}_{timestamp}.json"
        csv_filename = f"{output_dir}/capital_flow_{suffix}_{timestamp}.csv"

        # 检查文件是否已存在
        if os.path.exists(json_filename) and os.path.exists(csv_filename):
            logging.info(f"文件已存在，跳过 {period_name} 排行抓取。")
            continue

        logging.info(f"开始抓取 {period_name} 排行数据...")
        items = fetch_period_data(period_name, config)

        if items:
            data = parse_period_data(items, config['field_map'], period_name)
            if data:
                print(f"\n{period_name} 排行前 5 条预览：")
                for i, d in enumerate(data[:5]):
                    code = d.get('代码', 'N/A')
                    name = d.get('名称', 'N/A')
                    inflow = d.get('主力净额 (元)', 'N/A')
                    inflow_fmt = format_money(inflow)
                    print(f"  {i+1}. {name}({code}) 主力净额：{inflow_fmt}")

                save_to_json(data, json_filename, period_name)
                save_to_csv(data, csv_filename, period_name)
            else:
                logging.warning(f"{period_name} 排行解析后无数据")
        else:
            logging.error(f"获取 {period_name} 排行数据失败")

        # 避免请求过快
        time.sleep(0.5)

    print()
    print("="*80)
    print("✅ 全部完成!")
    print("="*80)
    print(f"\n📁 输出目录：{output_dir}")
    print()


if __name__ == "__main__":
    main()
