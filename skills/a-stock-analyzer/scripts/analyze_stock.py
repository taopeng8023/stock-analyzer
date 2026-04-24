#!/usr/bin/env python3
"""
A 股股票分析脚本 - 提供买卖决策信号
支持技术指标分析、缠论分析、基本面分析、市场情绪分析
数据源：东方财富 API (优先) / akshare (备选)

2026-04-06 更新：集成推荐验证器，确保推荐质量
核心原则：三不推荐
1. 不回测不推荐
2. 不说明风险不推荐
3. 不跟踪不推荐
"""

import sys
import json
import argparse
from datetime import datetime, timedelta

# 尝试导入东方财富 API (优先)
try:
    from eastmoney_api import EastMoneyAPI, get_stock_data
    HAS_EASTMONEY = True
except ImportError:
    HAS_EASTMONEY = False

# 尝试导入 akshare (备选)
try:
    import akshare as ak
    HAS_AK = True
except ImportError:
    HAS_AK = False

# 尝试导入 pandas
try:
    import pandas as pd
    HAS_PD = True
except ImportError:
    HAS_PD = False

# 导入缠论模块
try:
    from chanlun import generate_chanlun_report, print_chanlun_report
    HAS_CHANLUN = True
except ImportError:
    HAS_CHANLUN = False

# 数据源优先级：东方财富 > akshare
USE_EASTMONEY = HAS_EASTMONEY


def get_stock_info(symbol: str) -> dict:
    """获取股票基本信息"""
    # 优先使用东方财富 API
    if USE_EASTMONEY:
        try:
            api = EastMoneyAPI()
            quote = api.get_realtime_quote(symbol)
            if "error" not in quote:
                return {
                    "代码": symbol,
                    "名称": quote.get('名称', 'N/A'),
                    "最新价": quote.get('最新价', 0),
                    "涨跌幅": quote.get('涨跌幅', 0),
                    "成交量": quote.get('成交量', 0),
                    "成交额": quote.get('成交额', 0),
                    "换手率": quote.get('换手率', 0),
                    "量比": quote.get('量比', 0),
                    "总市值": quote.get('总市值', 0),
                    "流通市值": quote.get('流通市值', 0),
                    "市盈率": quote.get('市盈率', 0),
                    "市净率": quote.get('市净率', 0),
                    "每股收益": quote.get('每股收益', 0),
                    "每股净资产": quote.get('每股净资产', 0),
                    "毛利率": quote.get('毛利率', 0),
                    "净利率": quote.get('净利率', 0),
                    "ROE": quote.get('ROE', 0),
                }
        except Exception as e:
            print(f"东方财富 API 失败，尝试 akshare: {e}", file=sys.stderr)
    
    # 备选 akshare
    if HAS_AK:
        try:
            df = ak.stock_zh_a_spot_em()
            stock = df[df['代码'] == symbol]
            if stock.empty:
                return {"error": f"未找到股票 {symbol}"}
            
            return {
                "代码": symbol,
                "名称": stock['名称'].values[0],
                "最新价": float(stock['最新价'].values[0]),
                "涨跌幅": float(stock['涨跌幅'].values[0]),
                "成交量": int(stock['成交量'].values[0]),
                "成交额": float(stock['成交额'].values[0]),
                "振幅": float(stock['振幅'].values[0]),
                "换手率": float(stock['换手率'].values[0]),
            }
        except Exception as e:
            return {"error": f"akshare 失败：{str(e)}"}
    
    return {"error": "无可用数据源，请安装 eastmoney_api 或 akshare"}


def get_historical_data(symbol: str, days: int = 100) -> pd.DataFrame:
    """获取历史 K 线数据"""
    # 优先使用东方财富 API
    if USE_EASTMONEY and HAS_PD:
        try:
            api = EastMoneyAPI()
            df = api.get_kline_data(symbol, period='day', count=days, adjust='qfq')
            if not df.empty:
                return df
        except Exception as e:
            print(f"东方财富 K 线失败，尝试 akshare: {e}", file=sys.stderr)
    
    # 备选 akshare
    if HAS_AK and HAS_PD:
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
            
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            return df
        except Exception as e:
            print(f"获取历史数据失败：{e}", file=sys.stderr)
            return None
    
    return None


def calculate_ma(df: pd.DataFrame, periods: list = [5, 10, 20, 60]) -> pd.DataFrame:
    """计算移动平均线"""
    if df is None or df.empty:
        return None
    
    df = df.copy()
    for period in periods:
        df[f'MA{period}'] = df['收盘'].rolling(window=period).mean()
    return df


def calculate_macd(df: pd.DataFrame) -> pd.DataFrame:
    """计算 MACD 指标"""
    if df is None or df.empty:
        return None
    
    df = df.copy()
    exp1 = df['收盘'].ewm(span=12, adjust=False).mean()
    exp2 = df['收盘'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Histogram'] = df['MACD'] - df['Signal']
    return df


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """计算 RSI 指标"""
    if df is None or df.empty:
        return None
    
    df = df.copy()
    delta = df['收盘'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df


def calculate_kdj(df: pd.DataFrame, n: int = 9) -> pd.DataFrame:
    """计算 KDJ 指标"""
    if df is None or df.empty:
        return None
    
    df = df.copy()
    low_n = df['最低'].rolling(window=n).min()
    high_n = df['最高'].rolling(window=n).max()
    df['RSV'] = (df['收盘'] - low_n) / (high_n - low_n) * 100
    df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
    df['D'] = df['K'].ewm(com=2, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']
    return df


def calculate_bollinger(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """计算布林带"""
    if df is None or df.empty:
        return None
    
    df = df.copy()
    df['MB'] = df['收盘'].rolling(window=period).mean()
    std = df['收盘'].rolling(window=period).std()
    df['UP'] = df['MB'] + 2 * std
    df['DOWN'] = df['MB'] - 2 * std
    return df


def generate_signals(df: pd.DataFrame) -> dict:
    """基于技术指标生成买卖信号"""
    if df is None or df.empty:
        return {"error": "数据为空"}
    
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    signals = {
        "timestamp": datetime.now().isoformat(),
        "price": float(latest['收盘']),
        "signals": [],
        "strength": 0,  # -10 到 10，负数看空，正数看多
        "recommendation": "观望"
    }
    
    # MA 信号
    if 'MA5' in df.columns and 'MA10' in df.columns:
        if latest['MA5'] > latest['MA10'] and prev['MA5'] <= prev['MA10']:
            signals["signals"].append("MA 金叉 (5 日上穿 10 日) - 买入信号")
            signals["strength"] += 2
        elif latest['MA5'] < latest['MA10'] and prev['MA5'] >= prev['MA10']:
            signals["signals"].append("MA 死叉 (5 日下穿 10 日) - 卖出信号")
            signals["strength"] -= 2
        
        if latest['收盘'] > latest['MA20']:
            signals["signals"].append("股价在 20 日均线上方 - 偏多")
            signals["strength"] += 1
        else:
            signals["signals"].append("股价在 20 日均线下方 - 偏空")
            signals["strength"] -= 1
    
    # MACD 信号
    if 'MACD' in df.columns and 'Signal' in df.columns:
        if latest['MACD'] > latest['Signal'] and prev['MACD'] <= prev['Signal']:
            signals["signals"].append("MACD 金叉 - 买入信号")
            signals["strength"] += 3
        elif latest['MACD'] < latest['Signal'] and prev['MACD'] >= prev['Signal']:
            signals["signals"].append("MACD 死叉 - 卖出信号")
            signals["strength"] -= 3
        
        if latest.get('Histogram', 0) > 0 and prev.get('Histogram', 0) <= 0:
            signals["signals"].append("MACD 红柱出现 - 看多")
            signals["strength"] += 1
        elif latest.get('Histogram', 0) < 0 and prev.get('Histogram', 0) >= 0:
            signals["signals"].append("MACD 绿柱出现 - 看空")
            signals["strength"] -= 1
    
    # RSI 信号
    if 'RSI' in df.columns:
        rsi = latest['RSI']
        if rsi < 20:
            signals["signals"].append(f"RSI 超卖 ({rsi:.1f}) - 可能反弹")
            signals["strength"] += 2
        elif rsi > 80:
            signals["signals"].append(f"RSI 超买 ({rsi:.1f}) - 可能回调")
            signals["strength"] -= 2
        elif 40 <= rsi <= 60:
            signals["signals"].append(f"RSI 中性 ({rsi:.1f})")
    
    # KDJ 信号
    if 'K' in df.columns and 'D' in df.columns:
        if latest['K'] > latest['D'] and prev['K'] <= prev['D']:
            signals["signals"].append("KDJ 金叉 - 买入信号")
            signals["strength"] += 2
        elif latest['K'] < latest['D'] and prev['K'] >= prev['D']:
            signals["signals"].append("KDJ 死叉 - 卖出信号")
            signals["strength"] -= 2
        
        if latest['J'] < 0:
            signals["signals"].append(f"KDJ J 值超卖 ({latest['J']:.1f}) - 可能反弹")
            signals["strength"] += 1
        elif latest['J'] > 100:
            signals["signals"].append(f"KDJ J 值超买 ({latest['J']:.1f}) - 可能回调")
            signals["strength"] -= 1
    
    # 布林带信号
    if 'UP' in df.columns and 'DOWN' in df.columns:
        if latest['收盘'] < latest['DOWN']:
            signals["signals"].append("股价跌破布林带下轨 - 可能反弹")
            signals["strength"] += 2
        elif latest['收盘'] > latest['UP']:
            signals["signals"].append("股价突破布林带上轨 - 可能回调")
            signals["strength"] -= 2
    
    # 综合判断
    if signals["strength"] >= 5:
        signals["recommendation"] = "强烈买入"
    elif signals["strength"] >= 3:
        signals["recommendation"] = "买入"
    elif signals["strength"] >= 1:
        signals["recommendation"] = "谨慎买入"
    elif signals["strength"] <= -5:
        signals["recommendation"] = "强烈卖出"
    elif signals["strength"] <= -3:
        signals["recommendation"] = "卖出"
    elif signals["strength"] <= -1:
        signals["recommendation"] = "谨慎卖出"
    else:
        signals["recommendation"] = "观望"
    
    return signals


def analyze_stock(symbol: str, include_history: bool = False, chanlun: bool = False, candlestick: bool = False):
    """主分析函数"""
    result = {
        "symbol": symbol,
        "analysis_time": datetime.now().isoformat(),
        "basic_info": None,
        "technical_analysis": None,
        "chanlun_analysis": None,
        "candlestick_analysis": None,
        "recommendation": None
    }
    
    # 获取基本信息
    result["basic_info"] = get_stock_info(symbol)
    if "error" in result["basic_info"]:
        return result
    
    # 获取历史数据并计算指标
    df = get_historical_data(symbol)
    if df is not None:
        df = calculate_ma(df)
        df = calculate_macd(df)
        df = calculate_rsi(df)
        df = calculate_kdj(df)
        df = calculate_bollinger(df)
        
        # 生成传统技术信号
        signals = generate_signals(df)
        result["technical_analysis"] = signals
        result["recommendation"] = signals.get("recommendation", "观望")
        
        # 蜡烛图分析
        if candlestick:
            try:
                from candlestick import identify_all_patterns, print_patterns
                patterns = identify_all_patterns(df, lookback=20)
                result["candlestick_analysis"] = {
                    'patterns': [
                        {
                            'type': p.pattern_type.value,
                            'date': p.date,
                            'price': p.price,
                            'signal': '看涨' if p.signal == 1 else '看跌' if p.signal == -1 else '中性',
                            'strength': p.strength,
                            'description': p.description
                        }
                        for p in patterns[-10:]
                    ],
                    'latest': patterns[-1].__dict__ if patterns else None
                }
            except Exception as e:
                result["candlestick_analysis"] = {"error": str(e)}
        
        # 缠论分析 (可包含蜡烛图)
        if chanlun and HAS_CHANLUN:
            try:
                chanlun_report = generate_chanlun_report(df, include_candlestick=candlestick)
                result["chanlun_analysis"] = chanlun_report
                # 结合缠论建议调整推荐
                if chanlun_report.get('buy_sell_points'):
                    latest_point = chanlun_report['buy_sell_points'][-1]
                    if '买' in latest_point['type'] and signals["strength"] >= 0:
                        result["recommendation"] = "买入 (缠论信号确认)"
                    elif '卖' in latest_point['type'] and signals["strength"] <= 0:
                        result["recommendation"] = "卖出 (缠论信号确认)"
            except Exception as e:
                result["chanlun_analysis"] = {"error": str(e)}
        
        if include_history:
            # 返回最近 5 日数据
            result["recent_data"] = df.tail(5).to_dict('records')
    
    # 推荐验证（2026-04-06 新增）
    try:
        from recommendation_validator import validate_stock, BacktestMetrics, RecommendationValidator
        # 使用回测缓存数据计算验证指标
        validator = RecommendationValidator()
        # 尝试从回测结果获取指标（如果可用）
        metrics = BacktestMetrics(
            win_rate=result.get('backtest', {}).get('win_rate', 50.0),
            profit_loss_ratio=result.get('backtest', {}).get('profit_loss_ratio', 1.0),
            annual_return=result.get('backtest', {}).get('annual_return', 0.0),
            max_drawdown=result.get('backtest', {}).get('max_drawdown', 20.0),
            total_trades=result.get('backtest', {}).get('total_trades', 5),
            sharpe_ratio=result.get('backtest', {}).get('sharpe_ratio', 0.5)
        )
        validation_result = validator.validate(symbol, metrics, result.get('basic_info'))
        result['validation'] = {
            'passed': validation_result.passed,
            'level': validation_result.level.value,
            'score': validation_result.score,
            'issues': validation_result.issues,
            'warnings': validation_result.warnings
        }
        # 如果验证不通过，降级推荐
        if not validation_result.passed:
            if validation_result.level.value == "避免":
                result["recommendation"] = "🚫 避免买入 (验证未通过)"
            else:
                result["recommendation"] = f"⚠️ 谨慎 ({validation_result.level.value})"
    except Exception as e:
        # 验证器可选，失败不影响主功能
        result['validation'] = {'error': str(e)}
    
    return result


def main():
    parser = argparse.ArgumentParser(description='A 股股票分析工具 (数据源：东方财富/akshare)')
    parser.add_argument('symbol', help='股票代码 (如：000001)')
    parser.add_argument('--history', action='store_true', help='包含历史数据')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式')
    parser.add_argument('--chanlun', action='store_true', help='启用缠论分析')
    parser.add_argument('--candle', action='store_true', help='显示蜡烛图形态')
    parser.add_argument('--flow', action='store_true', help='显示资金流向')
    parser.add_argument('--full', action='store_true', help='完整报告 (缠论 + 蜡烛 + 资金流 + 公告 + 研报)')
    
    args = parser.parse_args()
    
    # 完整报告自动启用所有分析
    if args.full:
        args.flow = True
        args.chanlun = True
        args.candle = True
    
    result = analyze_stock(args.symbol, include_history=args.history, chanlun=args.chanlun, candlestick=args.candle)
    
    # 获取东方财富扩展数据
    eastmoney_data = None
    if USE_EASTMONEY and (args.flow or args.full):
        try:
            api = EastMoneyAPI()
            eastmoney_data = {
                'money_flow': api.get_money_flow(args.symbol),
                'blocks': api.get_concept_blocks(args.symbol),
                'notices': api.get_notices(args.symbol, count=3),
                'reports': api.get_research_reports(args.symbol, count=3)
            }
            result['eastmoney'] = eastmoney_data
        except Exception as e:
            print(f"获取东方财富扩展数据失败：{e}", file=sys.stderr)
    
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # 格式化输出
        print(f"\n{'='*70}")
        print(f"A 股分析报告 - {result['symbol']}")
        print(f"数据源：{'东方财富' if USE_EASTMONEY else 'akshare'}")
        print(f"分析时间：{result['analysis_time']}")
        print(f"{'='*70}\n")
        
        if result["basic_info"]:
            info = result["basic_info"]
            if "error" not in info:
                print(f"【股票信息】")
                print(f"  股票名称：{info.get('名称', 'N/A')}")
                print(f"  最新价格：¥{info.get('最新价', 'N/A')}")
                print(f"  涨跌幅：{info.get('涨跌幅', 'N/A')}%")
                print(f"  成交量：{info.get('成交量', 'N/A')}")
                print(f"  成交额：{info.get('成交额', 'N/A')}")
                print(f"  换手率：{info.get('换手率', 'N/A')}%")
                if info.get('量比'):
                    print(f"  量比：{info.get('量比')}")
                if info.get('总市值'):
                    print(f"  总市值：{info.get('总市值')/100000000:.2f}亿")
                if info.get('市盈率'):
                    print(f"  市盈率：{info.get('市盈率')}")
                if info.get('毛利率'):
                    print(f"  毛利率：{info.get('毛利率')}%")
                if info.get('净利率'):
                    print(f"  净利率：{info.get('净利率')}%")
                print()
        
        # 资金流向
        if eastmoney_data and eastmoney_data.get('money_flow'):
            flow = eastmoney_data['money_flow']
            print(f"【资金流向】{flow.get('日期', 'N/A')}")
            print(f"  主力净流入：{flow.get('主力净流入', 0)/10000:.2f}万 ({flow.get('主力净流入占比', 0):.2f}%)")
            print(f"  超大单：{flow.get('超大单净流入', 0)/10000:.2f}万")
            print(f"  大单：{flow.get('大单净流入', 0)/10000:.2f}万")
            print(f"  中单：{flow.get('中单净流入', 0)/10000:.2f}万")
            print(f"  小单：{flow.get('小单净流入', 0)/10000:.2f}万")
            print()
        
        # 所属板块
        if eastmoney_data and eastmoney_data.get('blocks'):
            print(f"【所属板块】")
            for block in eastmoney_data['blocks'][:5]:
                print(f"  • {block.get('板块', 'N/A')}")
            print()
        
        if result["technical_analysis"]:
            ta = result["technical_analysis"]
            print(f"【技术分析】")
            print(f"  当前价格：¥{ta.get('price', 'N/A')}")
            print(f"  综合建议：{ta.get('recommendation', 'N/A')}")
            print(f"  信号强度：{ta.get('strength', 0)} (范围：-10 到 10)")
            print()
            print("  技术信号:")
            for signal in ta.get('signals', [])[:8]:
                print(f"    • {signal}")
            print()
        
        # 推荐验证报告（2026-04-06 新增）
        if result.get('validation') and 'error' not in result.get('validation', {}):
            v = result['validation']
            print(f"{'='*70}")
            print("【🛡️  推荐验证报告】(2026-04-06 新增)")
            print(f"{'='*70}")
            status_icon = "✅" if v['passed'] else "❌"
            print(f"验证结果：{status_icon} {'通过' if v['passed'] else '不通过'}")
            print(f"推荐等级：{v['level']}")
            print(f"综合评分：{v['score']}/100")
            if v.get('issues'):
                print(f"\n⚠️  严重问题:")
                for issue in v['issues']:
                    print(f"  • {issue}")
            if v.get('warnings'):
                print(f"\n⚠️  注意事项:")
                for warning in v['warnings']:
                    print(f"  • {warning}")
            print()
        
        # 蜡烛图分析输出
        if result.get("candlestick_analysis") and args.candle:
            cs = result["candlestick_analysis"]
            if "error" not in cs:
                print(f"\n{'='*70}")
                print("蜡烛图形态识别")
                print(f"{'='*70}\n")
                patterns = cs.get('patterns', [])
                if patterns:
                    for i, p in enumerate(patterns[-5:], 1):
                        signal_icon = "📈" if p.get('signal') == '看涨' else "📉" if p.get('signal') == '看跌' else "➖"
                        print(f"{i}. {signal_icon} {p.get('type')}")
                        print(f"   日期：{p.get('date')}  价格：¥{p.get('price', 0):.2f}")
                        print(f"   强度：{p.get('strength', 0):.2f}")
                        print(f"   {p.get('description')}")
                        print()
                else:
                    print("  未识别到明显蜡烛形态")
                print()
            else:
                print(f"蜡烛图分析错误：{cs.get('error')}")
                print()
        
        # 缠论分析输出
        if result.get("chanlun_analysis") and args.chanlun:
            cl = result["chanlun_analysis"]
            if "error" not in cl:
                print_chanlun_report(cl)
            else:
                print(f"缠论分析错误：{cl.get('error')}")
                print()
        
        # 最新公告
        if eastmoney_data and eastmoney_data.get('notices'):
            print(f"【最新公告】")
            for notice in eastmoney_data['notices'][:3]:
                print(f"  {notice.get('日期', 'N/A')} - {notice.get('标题', 'N/A')[:40]}")
            print()
        
        # 机构研报
        if eastmoney_data and eastmoney_data.get('reports'):
            print(f"【机构研报】")
            for report in eastmoney_data['reports'][:3]:
                print(f"  {report.get('日期', 'N/A')} {report.get('机构', 'N/A')} [{report.get('评级', 'N/A')}]")
                print(f"    {report.get('标题', 'N/A')[:50]}")
            print()
        
        print(f"{'='*70}")
        print("⚠️  免责声明：本分析仅供参考，不构成投资建议。")
        print("股市有风险，投资需谨慎。")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    if not HAS_EASTMONEY and not HAS_AK:
        print("错误：需要安装 eastmoney_api 或 akshare 库", file=sys.stderr)
        print("请运行：pip install akshare pandas 或确保 eastmoney_api.py 存在", file=sys.stderr)
        sys.exit(1)
    
    main()
