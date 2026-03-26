#!/usr/bin/env python3
"""
个人股票研究数据库
用于研究学习，构建本地股票数据中心

⚠️  仅用于个人研究学习，不得用于交易决策

功能:
- 多数据源数据采集
- SQLite 本地存储
- 历史数据管理
- 数据导出分析

用法:
    python3 research_db.py --init              # 初始化数据库
    python3 research_db.py --update            # 更新数据
    python3 research_db.py --query 600000.SH   # 查询股票
    python3 research_db.py --export            # 导出数据
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# pandas 可选
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class ResearchDatabase:
    """个人股票研究数据库"""
    
    def __init__(self, db_path=None):
        self.db_path = str(db_path or Path(__file__).parent / 'research.db')
        self.init_db()
    
    def init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 股票基本信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_basic (
                ts_code TEXT PRIMARY KEY,
                symbol TEXT,
                name TEXT,
                industry TEXT,
                list_date TEXT,
                updated_at TEXT
            )
        ''')
        
        # 日线行情表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_bar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT,
                trade_date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                change_pct REAL,
                created_at TEXT,
                UNIQUE(ts_code, trade_date)
            )
        ''')
        
        # 资金流表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS moneyflow (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT,
                trade_date TEXT,
                buy_sm_amount REAL,
                sell_sm_amount REAL,
                buy_md_amount REAL,
                sell_md_amount REAL,
                buy_lg_amount REAL,
                sell_lg_amount REAL,
                buy_elg_amount REAL,
                sell_elg_amount REAL,
                net_mf_amount REAL,
                created_at TEXT,
                UNIQUE(ts_code, trade_date)
            )
        ''')
        
        # 技术指标表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT,
                trade_date TEXT,
                ma5 REAL,
                ma10 REAL,
                ma20 REAL,
                ma60 REAL,
                macd_dif REAL,
                macd_dea REAL,
                macd_bar REAL,
                kdj_k REAL,
                kdj_d REAL,
                kdj_j REAL,
                created_at TEXT,
                UNIQUE(ts_code, trade_date)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_code ON daily_bar(ts_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_bar(trade_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_flow_code ON moneyflow(ts_code)')
        
        conn.commit()
        conn.close()
        
        print(f"✅ 数据库已初始化：{self.db_path}")
    
    def insert_stock_basic(self, stocks: list):
        """插入股票基本信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for stock in stocks:
            cursor.execute('''
                INSERT OR REPLACE INTO stock_basic 
                (ts_code, symbol, name, industry, list_date, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                stock.get('ts_code'),
                stock.get('symbol'),
                stock.get('name'),
                stock.get('industry'),
                stock.get('list_date'),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
        print(f"✅ 插入 {len(stocks)} 只股票基本信息")
    
    def insert_daily_bar(self, ts_code: str, bars: list):
        """插入日线行情"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        count = 0
        for bar in bars:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_bar
                    (ts_code, trade_date, open, high, low, close, volume, amount, change_pct, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ts_code,
                    bar.get('trade_date'),
                    bar.get('open'),
                    bar.get('high'),
                    bar.get('low'),
                    bar.get('close'),
                    bar.get('volume'),
                    bar.get('amount'),
                    bar.get('change_pct'),
                    datetime.now().isoformat()
                ))
                count += 1
            except Exception as e:
                pass
        
        conn.commit()
        conn.close()
        print(f"✅ {ts_code} 插入 {count} 条日线数据")
    
    def insert_moneyflow(self, ts_code: str, flows: list):
        """插入资金流数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        count = 0
        for flow in flows:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO moneyflow
                    (ts_code, trade_date, buy_sm_amount, sell_sm_amount, buy_md_amount,
                     sell_md_amount, buy_lg_amount, sell_lg_amount, buy_elg_amount,
                     sell_elg_amount, net_mf_amount, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ts_code,
                    flow.get('trade_date'),
                    flow.get('buy_sm_amount'),
                    flow.get('sell_sm_amount'),
                    flow.get('buy_md_amount'),
                    flow.get('sell_md_amount'),
                    flow.get('buy_lg_amount'),
                    flow.get('sell_lg_amount'),
                    flow.get('buy_elg_amount'),
                    flow.get('sell_elg_amount'),
                    flow.get('net_mf_amount'),
                    datetime.now().isoformat()
                ))
                count += 1
            except Exception as e:
                pass
        
        conn.commit()
        conn.close()
        print(f"✅ {ts_code} 插入 {count} 条资金流数据")
    
    def query_daily(self, ts_code: str, start_date: str = None, 
                    end_date: str = None, limit: int = 100):
        """查询日线数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM daily_bar WHERE ts_code = ?'
        params = [ts_code]
        
        if start_date:
            query += ' AND trade_date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND trade_date <= ?'
            params.append(end_date)
        
        query += ' ORDER BY trade_date DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        if HAS_PANDAS:
            return pd.DataFrame(rows, columns=columns)
        return [dict(zip(columns, row)) for row in rows]
    
    def query_moneyflow(self, ts_code: str, limit: int = 100):
        """查询资金流数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT * FROM moneyflow 
            WHERE ts_code = ? 
            ORDER BY trade_date DESC 
            LIMIT ?
        '''
        
        cursor.execute(query, [ts_code, limit])
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        if HAS_PANDAS:
            return pd.DataFrame(rows, columns=columns)
        return [dict(zip(columns, row)) for row in rows]
    
    def query_stock_list(self, industry: str = None):
        """查询股票列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if industry:
            query = 'SELECT * FROM stock_basic WHERE industry = ?'
            cursor.execute(query, [industry])
        else:
            query = 'SELECT * FROM stock_basic'
            cursor.execute(query)
        
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        if HAS_PANDAS:
            return pd.DataFrame(rows, columns=columns)
        return [dict(zip(columns, row)) for row in rows]
    
    def export_to_csv(self, ts_code: str, output_dir: str = 'export'):
        """导出数据到 CSV"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 导出日线
        daily_df = self.query_daily(ts_code, limit=1000)
        if not daily_df.empty:
            daily_df.to_csv(output_path / f'{ts_code}_daily.csv', index=False)
            print(f"✅ 已导出日线：{output_path / f'{ts_code}_daily.csv'}")
        
        # 导出资金流
        flow_df = self.query_moneyflow(ts_code, limit=1000)
        if not flow_df.empty:
            flow_df.to_csv(output_path / f'{ts_code}_moneyflow.csv', index=False)
            print(f"✅ 已导出资金流：{output_path / f'{ts_code}_moneyflow.csv'}")
    
    def get_stats(self) -> dict:
        """获取数据库统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # 股票数量
        cursor.execute('SELECT COUNT(*) FROM stock_basic')
        stats['stock_count'] = cursor.fetchone()[0]
        
        # 日线数据量
        cursor.execute('SELECT COUNT(*) FROM daily_bar')
        stats['daily_bar_count'] = cursor.fetchone()[0]
        
        # 资金流数据量
        cursor.execute('SELECT COUNT(*) FROM moneyflow')
        stats['moneyflow_count'] = cursor.fetchone()[0]
        
        # 最新数据日期
        cursor.execute('SELECT MAX(trade_date) FROM daily_bar')
        stats['latest_date'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    
    def print_stats(self):
        """打印数据库统计"""
        stats = self.get_stats()
        
        print(f"\n{'='*50}")
        print(f"📊 研究数据库统计")
        print(f"{'='*50}")
        print(f"股票数量：    {stats.get('stock_count', 0)}")
        print(f"日线数据：    {stats.get('daily_bar_count', 0):,} 条")
        print(f"资金流数据：  {stats.get('moneyflow_count', 0):,} 条")
        print(f"最新日期：    {stats.get('latest_date', 'N/A')}")
        print(f"数据库文件：  {self.db_path}")
        print(f"{'='*50}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='个人股票研究数据库')
    parser.add_argument('--init', action='store_true', help='初始化数据库')
    parser.add_argument('--update', action='store_true', help='更新数据')
    parser.add_argument('--query', type=str, help='查询股票（代码）')
    parser.add_argument('--export', type=str, help='导出股票数据')
    parser.add_argument('--stats', action='store_true', help='显示统计')
    
    args = parser.parse_args()
    
    db = ResearchDatabase()
    
    if args.init:
        print("✅ 数据库已初始化")
        return
    
    if args.stats:
        db.print_stats()
        return
    
    if args.query:
        ts_code = args.query.upper()
        if not ts_code.endswith('.SH') and not ts_code.endswith('.SZ'):
            if ts_code.startswith('6'):
                ts_code += '.SH'
            else:
                ts_code += '.SZ'
        
        print(f"\n查询 {ts_code} 数据...")
        
        # 查询日线
        daily_df = db.query_daily(ts_code, limit=10)
        if not daily_df.empty:
            print(f"\n最新 10 条日线:")
            print(daily_df[['trade_date', 'open', 'high', 'low', 'close', 'volume']].to_string())
        
        # 查询资金流
        flow_df = db.query_moneyflow(ts_code, limit=10)
        if not flow_df.empty:
            print(f"\n最新 10 条资金流:")
            print(flow_df[['trade_date', 'net_mf_amount']].to_string())
        
        return
    
    if args.export:
        ts_code = args.export.upper()
        if not ts_code.endswith('.SH') and not ts_code.endswith('.SZ'):
            ts_code += '.SH' if ts_code.startswith('6') else '.SZ'
        
        db.export_to_csv(ts_code)
        return
    
    if args.update:
        print("⚠️  数据更新功能需要配置数据源")
        print("请参考文档手动导入数据")
        return
    
    # 默认显示统计
    db.print_stats()


if __name__ == '__main__':
    main()
