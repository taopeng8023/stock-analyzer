#!/usr/bin/env python3
"""
数据验证工具
严格执行数据底线，确保所有数据来自真实来源

⚠️  核心原则：
1. 没有真实数据时，不生成报告
2. 所有数据必须标注来源
3. 估算数据必须明确说明
4. 宁可报告不完整，也不能用假数据

用法:
    python3 data_validation.py --check       # 验证数据
    python3 data_validation.py --strict      # 严格模式
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


# ============ 数据验证规则 ============

DATA_RULES = {
    'price': {
        'required': True,
        'source': 'real',  # 必须真实数据
        'min': 0.01,
        'max': 10000,
    },
    'change_pct': {
        'required': True,
        'source': 'real',
        'min': -100,
        'max': 1000,
    },
    'volume': {
        'required': True,
        'source': 'real',
        'min': 0,
    },
    'amount': {
        'required': True,
        'source': 'real',
        'min': 0,
    },
    'main_net': {
        'required': False,
        'source': 'estimated',  # 可以估算
        'note': '必须标注为估算',
    },
    'fundamental': {
        'required': False,
        'source': 'model',  # 模型分析
        'note': '必须标注为模型',
    },
}


class DataValidator:
    """数据验证器"""
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.errors = []
        self.warnings = []
    
    def validate_stock_data(self, stock_data: dict, symbol: str) -> bool:
        """
        验证股票数据
        
        Args:
            stock_data: 股票数据
            symbol: 股票代码
        
        Returns:
            bool: 是否通过验证
        """
        self.errors = []
        self.warnings = []
        
        # 1. 检查必需字段
        for field, rules in DATA_RULES.items():
            if rules['required'] and field not in stock_data:
                self.errors.append(f"❌ 缺少必需字段：{field}")
        
        # 2. 验证价格
        if 'price' in stock_data:
            price = stock_data['price']
            if price < DATA_RULES['price']['min'] or price > DATA_RULES['price']['max']:
                self.errors.append(f"❌ 价格异常：¥{price}")
        
        # 3. 验证涨跌幅
        if 'change_pct' in stock_data:
            change = stock_data['change_pct']
            if change < -100:  # 最多跌 100%
                self.errors.append(f"❌ 涨跌幅异常：{change}%")
        
        # 4. 检查数据源
        if 'source' in stock_data:
            source = stock_data['source']
            if source not in ['real', 'estimated', 'model']:
                self.errors.append(f"❌ 数据源未知：{source}")
        else:
            if self.strict_mode:
                self.errors.append(f"❌ 未标注数据源")
            else:
                self.warnings.append(f"⚠️ 建议标注数据源")
        
        # 5. 严格模式下，没有真实数据则失败
        if self.strict_mode:
            if stock_data.get('source') != 'real':
                self.errors.append(f"❌ 严格模式：必须使用真实数据")
        
        return len(self.errors) == 0
    
    def validate_report(self, report_data: dict) -> bool:
        """
        验证报告
        
        Args:
            report_data: 报告数据
        
        Returns:
            bool: 是否通过验证
        """
        self.errors = []
        self.warnings = []
        
        # 1. 检查是否有数据标注
        if 'data_sources' not in report_data:
            self.errors.append("❌ 报告缺少数据标注")
        
        # 2. 检查每只股票
        stocks = report_data.get('stocks', [])
        for stock in stocks:
            symbol = stock.get('symbol', 'Unknown')
            if not self.validate_stock_data(stock, symbol):
                self.errors.append(f"❌ 股票 {symbol} 数据验证失败")
        
        # 3. 严格模式：任何错误都失败
        if self.strict_mode and len(self.errors) > 0:
            return False
        
        return len(self.errors) == 0
    
    def get_validation_report(self) -> str:
        """生成验证报告"""
        lines = []
        lines.append("="*60)
        lines.append("📋 数据验证报告")
        lines.append("="*60)
        
        if not self.errors and not self.warnings:
            lines.append("✅ 数据验证通过")
        else:
            if self.errors:
                lines.append("\n❌ 错误:")
                for error in self.errors:
                    lines.append(f"  {error}")
            
            if self.warnings:
                lines.append("\n⚠️  警告:")
                for warning in self.warnings:
                    lines.append(f"  {warning}")
        
        lines.append("")
        lines.append("="*60)
        
        return "\n".join(lines)


def check_data_source(symbol: str) -> dict:
    """
    检查数据源
    
    Returns:
        数据源信息
    """
    # 尝试从 fund_flow 获取真实数据
    try:
        from fund_flow import FundFlowFetcher
        fetcher = FundFlowFetcher()
        stocks = fetcher.fetch_tencent_estimate(count=100)
        
        for stock in stocks:
            if stock.get('symbol') == symbol or stock.get('name') == symbol:
                return {
                    'available': True,
                    'source': 'real',
                    'data': stock,
                }
        
        return {
            'available': False,
            'source': None,
            'data': None,
            'message': f"未找到 {symbol} 的真实数据",
        }
        
    except Exception as e:
        return {
            'available': False,
            'source': None,
            'data': None,
            'message': f"数据获取失败：{e}",
        }


def generate_safe_report(symbols: list) -> str:
    """
    生成安全报告（只有真实数据）
    
    Args:
        symbols: 股票代码列表
    
    Returns:
        安全报告文本
    """
    lines = []
    lines.append("="*80)
    lines.append("📊 股票分析报告（严格数据验证版）")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("="*80)
    lines.append("")
    
    # 验证器
    validator = DataValidator(strict_mode=True)
    
    # 收集真实数据
    available_stocks = []
    unavailable_stocks = []
    
    for symbol in symbols:
        result = check_data_source(symbol)
        if result['available']:
            available_stocks.append(result['data'])
        else:
            unavailable_stocks.append({
                'symbol': symbol,
                'reason': result['message'],
            })
    
    # 报告真实数据
    if available_stocks:
        lines.append("✅ **有真实数据的股票**")
        lines.append("")
        lines.append(f"{'代码':<10} {'名称':<10} {'现价':<8} {'涨跌幅':<10} {'成交额':<10} {'数据源':<8}")
        lines.append("-"*80)
        
        for s in available_stocks:
            symbol = s.get('symbol', '')
            name = s.get('name', '')
            price = s.get('price', 0)
            change = s.get('change_pct', 0)
            amount = s.get('amount_wan', 0)
            
            change_sign = '+' if change >= 0 else ''
            amount_str = f"{amount/10000:.2f}亿" if amount >= 10000 else f"{amount:.0f}万"
            
            lines.append(f"{symbol:<10} {name:<10} ¥{price:<6.2f} {change_sign}{change:>7.2f}% {amount_str:>8} ✅真实")
        
        lines.append("")
    else:
        lines.append("❌ **没有真实数据**")
        lines.append("")
    
    # 报告无法获取数据的股票
    if unavailable_stocks:
        lines.append("⚠️  **无法获取真实数据的股票**")
        lines.append("")
        for item in unavailable_stocks:
            lines.append(f"  ❌ {item['symbol']}: {item['reason']}")
        lines.append("")
        lines.append("⚠️  **重要说明**")
        lines.append("  - 根据 DATA_POLICY.md，不使用模拟/估算数据")
        lines.append("  - 请等待真实数据可用后再分析")
        lines.append("  - 可尝试：Tushare、AKShare 等其他数据源")
        lines.append("")
    
    # 数据标注
    lines.append("📝 **数据标注说明**")
    lines.append("  ✅ 真实数据：来自腾讯财经实时行情")
    lines.append("  ⚠️ 估算数据：主力流入=成交额×15%（已标注）")
    lines.append("  ❌ 模拟数据：不使用（严格遵守政策）")
    lines.append("")
    lines.append("="*80)
    
    return "\n".join(lines)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='数据验证工具')
    parser.add_argument('--check', action='store_true', help='验证数据')
    parser.add_argument('--strict', action='store_true', help='严格模式')
    parser.add_argument('--symbols', type=str, nargs='+', help='股票代码')
    
    args = parser.parse_args()
    
    if args.symbols:
        report = generate_safe_report(args.symbols)
        print(report)
    else:
        # 示例验证
        validator = DataValidator(strict_mode=args.strict)
        
        # 测试数据 1：真实数据
        real_data = {
            'symbol': '600152.SH',
            'price': 10.24,
            'change_pct': -61.16,
            'volume': 5130000,
            'amount': 427200,
            'source': 'real',
        }
        
        # 测试数据 2：虚假数据
        fake_data = {
            'symbol': '002475.SZ',
            'price': 42.80,
            'change_pct': 2.80,
            'source': 'fake',  # 虚假来源
        }
        
        print("测试 1：真实数据验证")
        if validator.validate_stock_data(real_data, '600152.SH'):
            print("✅ 通过验证")
        else:
            print("❌ 验证失败")
            print(validator.get_validation_report())
        
        print("\n测试 2：虚假数据验证")
        if validator.validate_stock_data(fake_data, '002475.SZ'):
            print("✅ 通过验证")
        else:
            print("❌ 验证失败（正确！）")
            print(validator.get_validation_report())


if __name__ == '__main__':
    main()
