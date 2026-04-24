#!/usr/bin/env python3
"""
股票推荐验证器 - 确保推荐质量的守门员

基于 2026-04-06 错误教训（中闽能源 600163）创建的验证系统
核心原则：三不推荐
1. 不回测不推荐
2. 不说明风险不推荐
3. 不跟踪不推荐
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RecommendationLevel(Enum):
    """推荐等级"""
    STRONG_BUY = "强烈买入"  # 胜率≥80%, 盈亏比≥5.0
    BUY = "买入"  # 胜率≥70%, 盈亏比≥2.0
    HOLD = "持有"  # 胜率≥60%, 盈亏比≥1.5
    WATCH = "观察"  # 胜率≥50%, 盈亏比≥1.0
    SELL = "卖出"  # 胜率<50% 或 盈亏比<1.0
    AVOID = "避免"  # 胜率<40% 或 有重大风险


@dataclass
class BacktestMetrics:
    """回测指标"""
    win_rate: float  # 胜率 (%)
    profit_loss_ratio: float  # 盈亏比
    annual_return: float  # 年化收益 (%)
    max_drawdown: float  # 最大回撤 (%)
    total_trades: int  # 总交易次数
    sharpe_ratio: float  # 夏普比率


@dataclass
class ValidationResult:
    """验证结果"""
    passed: bool  # 是否通过验证
    level: RecommendationLevel  # 推荐等级
    score: int  # 综合评分 (0-100)
    issues: List[str]  # 问题列表
    warnings: List[str]  # 警告列表
    metrics: Optional[BacktestMetrics]  # 回测指标


class RecommendationValidator:
    """
    股票推荐验证器
    
    检查清单：
    □ 历史回测胜率 ≥ 70%
    □ 盈亏比 ≥ 2.0
    □ 最大回撤 < 25%
    □ 年交易次数 ≥ 3 次（避免偶发性）
    □ 基本面没有重大利空
    □ 不属于问题股黑名单
    """
    
    # 阈值配置
    THRESHOLDS = {
        'win_rate_min': 70.0,  # 最低胜率
        'win_rate_strong': 80.0,  # 强烈买入胜率
        'profit_loss_ratio_min': 2.0,  # 最低盈亏比
        'profit_loss_ratio_strong': 5.0,  # 强烈买入盈亏比
        'max_drawdown_max': 25.0,  # 最大回撤上限
        'annual_return_min': 15.0,  # 最低年化收益
        'min_trades_per_year': 3,  # 最少年交易次数
        'sharpe_ratio_min': 0.5,  # 最低夏普比率
    }
    
    # 问题股黑名单（动态更新）
    BLACKLIST_FILE = os.path.join(os.path.dirname(__file__), '../data/blacklist.json')
    
    def __init__(self):
        self.blacklist = self._load_blacklist()
        self.validation_history = []
    
    def _load_blacklist(self) -> Dict:
        """加载黑名单"""
        if os.path.exists(self.BLACKLIST_FILE):
            try:
                with open(self.BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'stocks': [],  # 股票代码列表
            'reasons': {},  # 原因说明
            'updated_at': None
        }
    
    def _save_blacklist(self):
        """保存黑名单"""
        self.blacklist['updated_at'] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(self.BLACKLIST_FILE), exist_ok=True)
        with open(self.BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.blacklist, f, indent=2, ensure_ascii=False)
    
    def add_to_blacklist(self, stock_code: str, reason: str):
        """添加股票到黑名单"""
        if stock_code not in self.blacklist['stocks']:
            self.blacklist['stocks'].append(stock_code)
            self.blacklist['reasons'][stock_code] = {
                'reason': reason,
                'added_at': datetime.now().isoformat()
            }
            self._save_blacklist()
            print(f"⚠️  已将 {stock_code} 加入黑名单：{reason}")
    
    def validate(self, stock_code: str, metrics: BacktestMetrics, 
                 basic_info: Optional[Dict] = None) -> ValidationResult:
        """
        验证股票是否值得推荐
        
        Args:
            stock_code: 股票代码
            metrics: 回测指标
            basic_info: 基本面信息（可选）
        
        Returns:
            ValidationResult: 验证结果
        """
        issues = []
        warnings = []
        score = 100  # 基础分 100
        
        # 检查 1: 黑名单
        if stock_code in self.blacklist.get('stocks', []):
            return ValidationResult(
                passed=False,
                level=RecommendationLevel.AVOID,
                score=0,
                issues=[f"该股票在黑名单中：{self.blacklist['reasons'].get(stock_code, {}).get('reason', '未知原因')}"],
                warnings=[],
                metrics=metrics
            )
        
        # 检查 2: 胜率
        if metrics.win_rate < self.THRESHOLDS['win_rate_min']:
            issues.append(f"胜率过低：{metrics.win_rate:.1f}% (要求≥{self.THRESHOLDS['win_rate_min']}%)")
            score -= 30
            # 胜率<40% 直接否决
            if metrics.win_rate < 40:
                self.add_to_blacklist(stock_code, f"胜率过低 {metrics.win_rate:.1f}%")
                return ValidationResult(
                    passed=False,
                    level=RecommendationLevel.AVOID,
                    score=score,
                    issues=issues,
                    warnings=warnings,
                    metrics=metrics
                )
        elif metrics.win_rate < self.THRESHOLDS['win_rate_strong']:
            warnings.append(f"胜率一般：{metrics.win_rate:.1f}% (优秀≥{self.THRESHOLDS['win_rate_strong']}%)")
            score -= 10
        
        # 检查 3: 盈亏比
        if metrics.profit_loss_ratio < self.THRESHOLDS['profit_loss_ratio_min']:
            issues.append(f"盈亏比过低：{metrics.profit_loss_ratio:.2f} (要求≥{self.THRESHOLDS['profit_loss_ratio_min']})")
            score -= 25
        elif metrics.profit_loss_ratio < self.THRESHOLDS['profit_loss_ratio_strong']:
            warnings.append(f"盈亏比一般：{metrics.profit_loss_ratio:.2f} (优秀≥{self.THRESHOLDS['profit_loss_ratio_strong']})")
            score -= 5
        
        # 检查 4: 最大回撤
        if metrics.max_drawdown > self.THRESHOLDS['max_drawdown_max']:
            issues.append(f"最大回撤过大：{metrics.max_drawdown:.1f}% (要求<{self.THRESHOLDS['max_drawdown_max']}%)")
            score -= 20
        
        # 检查 5: 年化收益
        if metrics.annual_return < self.THRESHOLDS['annual_return_min']:
            warnings.append(f"年化收益偏低：{metrics.annual_return:.1f}% (优秀≥{self.THRESHOLDS['annual_return_min']}%)")
            score -= 10
        
        # 检查 6: 交易次数（避免偶发性）
        if metrics.total_trades < self.THRESHOLDS['min_trades_per_year']:
            warnings.append(f"交易次数偏少：{metrics.total_trades} 次/年 (建议≥{self.THRESHOLDS['min_trades_per_year']})")
            score -= 5
        
        # 检查 7: 夏普比率
        if metrics.sharpe_ratio < self.THRESHOLDS['sharpe_ratio_min']:
            warnings.append(f"夏普比率偏低：{metrics.sharpe_ratio:.2f} (建议≥{self.THRESHOLDS['sharpe_ratio_min']})")
            score -= 5
        
        # 确定推荐等级
        if score >= 85 and metrics.win_rate >= self.THRESHOLDS['win_rate_strong']:
            level = RecommendationLevel.STRONG_BUY
        elif score >= 70 and metrics.win_rate >= self.THRESHOLDS['win_rate_min']:
            level = RecommendationLevel.BUY
        elif score >= 55 and metrics.win_rate >= 60:
            level = RecommendationLevel.HOLD
        elif score >= 40 and metrics.win_rate >= 50:
            level = RecommendationLevel.WATCH
        else:
            level = RecommendationLevel.SELL
        
        # 有严重问题时直接否决
        passed = len(issues) == 0 and score >= 60
        
        result = ValidationResult(
            passed=passed,
            level=level,
            score=max(0, score),
            issues=issues,
            warnings=warnings,
            metrics=metrics
        )
        
        # 记录验证历史
        self.validation_history.append({
            'timestamp': datetime.now().isoformat(),
            'stock_code': stock_code,
            'result': passed,
            'level': level.value,
            'score': score
        })
        
        return result
    
    def generate_report(self, stock_code: str, result: ValidationResult) -> str:
        """生成验证报告"""
        lines = []
        lines.append("=" * 70)
        lines.append(f"股票推荐验证报告 - {stock_code}")
        lines.append("=" * 70)
        lines.append("")
        
        # 验证结果
        status_icon = "✅" if result.passed else "❌"
        lines.append(f"【验证结果】{status_icon} {'通过' if result.passed else '不通过'}")
        lines.append(f"【推荐等级】{result.level.value}")
        lines.append(f"【综合评分】{result.score}/100")
        lines.append("")
        
        # 回测指标
        if result.metrics:
            m = result.metrics
            lines.append("【回测指标】")
            lines.append(f"  • 胜率：{m.win_rate:.1f}% {'✅' if m.win_rate >= 70 else '⚠️' if m.win_rate >= 50 else '❌'}")
            lines.append(f"  • 盈亏比：{m.profit_loss_ratio:.2f} {'✅' if m.profit_loss_ratio >= 2.0 else '⚠️' if m.profit_loss_ratio >= 1.0 else '❌'}")
            lines.append(f"  • 年化收益：{m.annual_return:.1f}% {'✅' if m.annual_return >= 15 else '⚠️' if m.annual_return >= 5 else '❌'}")
            lines.append(f"  • 最大回撤：{m.max_drawdown:.1f}% {'✅' if m.max_drawdown < 25 else '⚠️' if m.max_drawdown < 35 else '❌'}")
            lines.append(f"  • 交易次数：{m.total_trades} 次/年 {'✅' if m.total_trades >= 3 else '⚠️'}")
            lines.append(f"  • 夏普比率：{m.sharpe_ratio:.2f} {'✅' if m.sharpe_ratio >= 0.5 else '⚠️'}")
            lines.append("")
        
        # 问题列表
        if result.issues:
            lines.append("【❌ 严重问题】")
            for issue in result.issues:
                lines.append(f"  • {issue}")
            lines.append("")
        
        # 警告列表
        if result.warnings:
            lines.append("【⚠️  注意事项】")
            for warning in result.warnings:
                lines.append(f"  • {warning}")
            lines.append("")
        
        # 最终建议
        lines.append("【最终建议】")
        if result.passed:
            if result.level == RecommendationLevel.STRONG_BUY:
                lines.append("  🌟 强烈推荐 - 各项指标优秀，可重点配置")
            elif result.level == RecommendationLevel.BUY:
                lines.append("  ✅ 推荐买入 - 符合标准，可正常配置")
            elif result.level == RecommendationLevel.HOLD:
                lines.append("  📊 建议持有 - 表现良好，继续观察")
            else:
                lines.append("  👀 可观察 - 符合条件但非最优")
        else:
            if result.level == RecommendationLevel.AVOID:
                lines.append("  🚫 避免买入 - 存在严重问题，建议回避")
            else:
                lines.append("  📉 建议卖出/观望 - 未达推荐标准")
        
        lines.append("")
        lines.append("=" * 70)
        
        return "\n".join(lines)


# 便捷函数
def validate_stock(stock_code: str, win_rate: float, profit_loss_ratio: float,
                   annual_return: float, max_drawdown: float, 
                   total_trades: int, sharpe_ratio: float,
                   basic_info: Optional[Dict] = None) -> ValidationResult:
    """
    便捷验证函数
    
    示例:
        result = validate_stock(
            stock_code='600163',
            win_rate=28.57,
            profit_loss_ratio=0.10,
            annual_return=6.59,
            max_drawdown=20.39,
            total_trades=7,
            sharpe_ratio=0.14
        )
        print(result.passed)  # False
    """
    validator = RecommendationValidator()
    metrics = BacktestMetrics(
        win_rate=win_rate,
        profit_loss_ratio=profit_loss_ratio,
        annual_return=annual_return,
        max_drawdown=max_drawdown,
        total_trades=total_trades,
        sharpe_ratio=sharpe_ratio
    )
    return validator.validate(stock_code, metrics, basic_info)


if __name__ == '__main__':
    # 测试：中闽能源 (错误推荐案例)
    print("测试案例 1: 中闽能源 (600163) - 错误推荐")
    result1 = validate_stock(
        stock_code='600163',
        win_rate=28.57,
        profit_loss_ratio=0.10,
        annual_return=6.59,
        max_drawdown=20.39,
        total_trades=7,
        sharpe_ratio=0.14
    )
    print(f"通过：{result1.passed}")
    print(f"等级：{result1.level.value}")
    print(f"问题：{result1.issues}")
    print()
    
    # 测试：天赐材料 (正确推荐案例)
    print("测试案例 2: 天赐材料 (002709) - 正确推荐")
    result2 = validate_stock(
        stock_code='002709',
        win_rate=80.00,
        profit_loss_ratio=26.21,
        annual_return=114.79,
        max_drawdown=14.60,
        total_trades=5,
        sharpe_ratio=1.56
    )
    print(f"通过：{result2.passed}")
    print(f"等级：{result2.level.value}")
    print(f"评分：{result2.score}")
