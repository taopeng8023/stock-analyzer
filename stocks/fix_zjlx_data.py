#!/usr/bin/env python3
"""
资金流数据修正脚本
修正 20260424 数据的字段问题
"""

import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
INPUT_FILE = DATA_DIR / "zjlx_ranking_20260424.json"
OUTPUT_FILE = DATA_DIR / "zjlx_ranking_20260424_fixed.json"

def fix_zjlx_data():
    """修正资金流数据"""
    print(f"\n{'='*60}")
    print("🔧 修正资金流数据")
    print(f"{'='*60}")
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    ranking = data.get('ranking', [])
    print(f"原始数据：{len(ranking)} 条")
    
    fixed_ranking = []
    for s in ranking:
        # 修正字段
        fixed = {
            '序号': s.get('序号', 0),
            '代码': s.get('代码', ''),
            '名称': s.get('名称', ''),
            '最新价': float(s.get('最新价', 0)) if s.get('最新价') else 0,
            '涨跌幅': float(s.get('涨跌幅', 0)) if s.get('涨跌幅') else 0,
            '主力净流入_净额': float(s.get('主力净流入_净额', 0)) / 10000 if s.get('主力净流入_净额') else 0,  # 转万元
            '主力净流入_净占比': float(s.get('主力净流入_净占比', 0)) / 100 if s.get('主力净流入_净占比') else 0,  # 转百分比
            '超大单净流入_净额': 0,  # 字段错误，暂设 0
            '超大单净流入_净占比': 0
        }
        fixed_ranking.append(fixed)
    
    # 保存修正后数据
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'total': len(fixed_ranking),
            'ranking': fixed_ranking
        }, f, indent=2, ensure_ascii=False)
    
    print(f"修正完成：{len(fixed_ranking)} 条")
    print(f"已保存：{OUTPUT_FILE}")
    
    print(f"\n{'='*60}")
    print("🏆 主力资金流 TOP10 (修正后，单位：万元)")
    print(f"{'='*60}")
    print(f"{'排名':<4} {'代码':<8} {'名称':<10} {'净流入':<10} {'占比':<8}")
    print(f"{'-'*60}")
    
    for s in fixed_ranking[:10]:
        print(f"{s['序号']:<4} {s['代码']:<8} {s['名称']:<10} {s['主力净流入_净额']:>8.2f} {s['主力净流入_净占比']:>6.2f}%")
    
    print(f"\n{'='*60}")
    
    return fixed_ranking

if __name__ == "__main__":
    fix_zjlx_data()
