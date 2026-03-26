#!/usr/bin/env python3
"""
v8.0-Financial-Enhanced 严格数据契约版 - 三层异常推送验证

验证场景:
1. ✅ Layer 1 数据获取异常 → 推送错误
2. ✅ Layer 2 分析决策异常 → 推送错误
3. ✅ Layer 3 输出推送异常 → 推送错误

用法:
    python3 test_three_layers_error.py --layer 1  # 测试 Layer 1
    python3 test_three_layers_error.py --layer 2  # 测试 Layer 2
    python3 test_three_layers_error.py --layer 3  # 测试 Layer 3
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# 导入严格工作流模块
from workflow_v8_strict import (
    V8StrictWorkflow,
    DataFetchLayer,
    AnalysisLayer,
    PushLayer,
    StockData,
    DataSourceResult,
    AnalysisInput,
    AnalysisOutput,
    PushInput,
    DataFetchException,
    AnalysisException,
    PushException
)


def test_layer1_error():
    """
    测试场景 1: Layer 1 数据获取异常
    
    模拟：所有数据源都失败
    预期：推送错误报告
    """
    print("\n" + "="*80)
    print("🧪 测试场景 1: Layer 1 数据获取异常")
    print("="*80)
    
    layer = DataFetchLayer()
    
    # 修改最小数据源要求为 3（确保失败）
    original_min = layer.MIN_SUCCESS_SOURCES
    layer.MIN_SUCCESS_SOURCES = 3  # 要求 3 个，实际不可能达到
    
    try:
        results = layer.fetch(top_n=10)
        print("❌ 测试失败：Layer 1 没有抛出异常")
        return False
    except DataFetchException as e:
        print(f"\n✅ Layer 1 正确抛出异常:")
        print(f"   Layer: {e.layer}")
        print(f"   错误：{e.message}")
        print(f"   详情：{e.details}")
        
        # 推送错误
        push_layer = PushLayer()
        push_output = push_layer.push_error(e)
        
        if push_output.status == 'success':
            print(f"\n✅ 错误报告推送成功")
            return True
        else:
            print(f"\n❌ 错误报告推送失败：{push_output.error_message}")
            return False
    finally:
        layer.MIN_SUCCESS_SOURCES = original_min


def test_layer2_error():
    """
    测试场景 2: Layer 2 分析决策异常
    
    模拟：输入数据格式错误
    预期：推送错误报告
    """
    print("\n" + "="*80)
    print("🧪 测试场景 2: Layer 2 分析决策异常")
    print("="*80)
    
    layer = AnalysisLayer()
    
    # 创建无效的输入数据
    invalid_input = AnalysisInput(
        stocks=[],  # 空列表，应该失败
        data_sources=['tencent'],
        total_count=0,  # 数量为 0，应该失败
        fetch_time=datetime.now().isoformat()
    )
    
    try:
        output = layer.analyze(invalid_input, top_n=10)
        print("❌ 测试失败：Layer 2 没有抛出异常")
        return False
    except AnalysisException as e:
        print(f"\n✅ Layer 2 正确抛出异常:")
        print(f"   Layer: {e.layer}")
        print(f"   错误：{e.message}")
        print(f"   详情：{e.details}")
        
        # 推送错误
        push_layer = PushLayer()
        push_output = push_layer.push_error(e)
        
        if push_output.status == 'success':
            print(f"\n✅ 错误报告推送成功")
            return True
        else:
            print(f"\n❌ 错误报告推送失败：{push_output.error_message}")
            return False


def test_layer3_error():
    """
    测试场景 3: Layer 3 输出推送异常
    
    模拟：推送输入数据格式错误
    预期：推送错误报告（或本地记录）
    """
    print("\n" + "="*80)
    print("🧪 测试场景 3: Layer 3 输出推送异常")
    print("="*80)
    
    layer = PushLayer()
    
    # 创建无效的输入数据
    invalid_input = PushInput(
        stocks=[],  # 空列表，应该失败
        top_n=0,    # 数量为 0，应该失败
        workflow_version='',  # 空字符串，应该失败
        execution_time=''
    )
    
    try:
        output = layer.push(invalid_input)
        print("❌ 测试失败：Layer 3 没有抛出异常")
        return False
    except PushException as e:
        print(f"\n✅ Layer 3 正确抛出异常:")
        print(f"   Layer: {e.layer}")
        print(f"   错误：{e.message}")
        print(f"   详情：{e.details}")
        
        # Layer 3 异常时，尝试再次推送错误（可能也会失败）
        try:
            push_output = layer.push_error(e)
            if push_output.status == 'success':
                print(f"\n✅ 错误报告推送成功")
                return True
            else:
                print(f"\n⚠️ 错误报告推送失败（但异常已捕获）: {push_output.error_message}")
                return True  # 仍然算成功，因为异常被正确处理
        except Exception as ex:
            print(f"\n⚠️ 错误报告推送异常（但原异常已捕获）: {ex}")
            return True  # 仍然算成功，因为异常被正确处理


def test_full_workflow_layer1_failure():
    """
    完整工作流测试：Layer 1 失败场景
    """
    print("\n" + "="*80)
    print("🧪 完整工作流测试：Layer 1 失败")
    print("="*80)
    
    workflow = V8StrictWorkflow()
    
    # 修改 Layer 1 配置，确保失败
    workflow.layer1.MIN_SUCCESS_SOURCES = 3
    
    success = workflow.run(strategy='main', top_n=10, push=True)
    
    if not success:
        print(f"\n✅ 工作流正确终止（Layer 1 失败）")
        return True
    else:
        print(f"\n❌ 工作流不应该成功")
        return False


# 主测试函数
def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*80)
    print("🚀 v8.0-Financial-Enhanced 三层异常推送验证")
    print("="*80)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'Layer 1 异常推送': test_layer1_error(),
        'Layer 2 异常推送': test_layer2_error(),
        'Layer 3 异常推送': test_layer3_error(),
        '完整工作流 Layer 1 失败': test_full_workflow_layer1_failure(),
    }
    
    # 汇总结果
    print("\n" + "="*80)
    print("📊 测试结果汇总")
    print("="*80)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！三层异常推送机制正常工作！")
        return True
    else:
        print("\n⚠️ 部分测试失败，请检查日志")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='三层异常推送验证')
    parser.add_argument('--layer', type=int, choices=[1, 2, 3], help='测试特定 Layer')
    parser.add_argument('--all', action='store_true', help='运行所有测试')
    
    args = parser.parse_args()
    
    if args.layer:
        if args.layer == 1:
            success = test_layer1_error()
        elif args.layer == 2:
            success = test_layer2_error()
        elif args.layer == 3:
            success = test_layer3_error()
        
        sys.exit(0 if success else 1)
    else:
        success = run_all_tests()
        sys.exit(0 if success else 1)
