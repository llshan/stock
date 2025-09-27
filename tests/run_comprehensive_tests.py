#!/usr/bin/env python3
"""
综合测试运行器
执行所有新增的复杂交易场景测试
"""

import sys
import unittest
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_test_suite():
    """运行完整的测试套件"""
    
    print("=" * 80)
    print("🧪 股票交易系统 - 综合测试套件")
    print("=" * 80)
    
    # 定义测试模块
    test_modules = [
        'tests.trading.test_comprehensive_aapl_scenario',
        'tests.trading.test_interactive_trading_flows', 
        'tests.trading.test_edge_cases_lot_tracking',
        'tests.trading.test_performance_large_volumes',
        'tests.trading.test_cost_basis_comprehensive',
    ]
    
    test_descriptions = [
        "📈 综合AAPL交易场景 (10买+5卖)",
        "🔄 交互式交易流程测试",
        "⚠️  边缘情况和异常场景",
        "🚀 大容量交易性能测试", 
        "🎯 成本基础方法综合验证",
    ]
    
    total_start_time = time.time()
    results = {}
    
    for i, (module_name, description) in enumerate(zip(test_modules, test_descriptions), 1):
        print(f"\n{i}/5 {description}")
        print("-" * 60)
        
        # 动态导入测试模块
        try:
            test_module = __import__(module_name, fromlist=[''])
            
            # 创建测试套件
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(test_module)
            
            # 运行测试
            runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
            
            start_time = time.time()
            result = runner.run(suite)
            end_time = time.time()
            
            # 记录结果
            results[module_name] = {
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'success': result.wasSuccessful(),
                'duration': end_time - start_time
            }
            
            print(f"⏱️  耗时: {end_time - start_time:.2f}秒")
            
        except ImportError as e:
            print(f"❌ 无法导入测试模块 {module_name}: {e}")
            results[module_name] = {
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'success': False,
                'duration': 0,
                'import_error': str(e)
            }
        except Exception as e:
            print(f"❌ 运行测试时出错: {e}")
            results[module_name] = {
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'success': False,
                'duration': 0,
                'runtime_error': str(e)
            }
    
    total_end_time = time.time()
    
    # 生成测试报告
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)
    
    total_tests = 0
    total_failures = 0
    total_errors = 0
    successful_suites = 0
    
    for i, (module_name, description) in enumerate(zip(test_modules, test_descriptions), 1):
        result = results[module_name]
        
        total_tests += result['tests_run']
        total_failures += result['failures']
        total_errors += result['errors']
        
        if result['success']:
            status = "✅ 通过"
            successful_suites += 1
        else:
            status = "❌ 失败"
        
        print(f"{i}. {description}")
        print(f"   状态: {status}")
        print(f"   测试: {result['tests_run']}个")
        
        if result['failures'] > 0:
            print(f"   失败: {result['failures']}个")
        if result['errors'] > 0:
            print(f"   错误: {result['errors']}个")
        if 'import_error' in result:
            print(f"   导入错误: {result['import_error']}")
        if 'runtime_error' in result:
            print(f"   运行错误: {result['runtime_error']}")
            
        print(f"   耗时: {result['duration']:.2f}秒")
        print()
    
    # 总体统计
    print("=" * 80)
    print("🎯 总体统计")
    print("-" * 40)
    print(f"测试套件: {successful_suites}/{len(test_modules)} 通过")
    print(f"测试用例: {total_tests} 个")
    print(f"成功: {total_tests - total_failures - total_errors} 个")
    print(f"失败: {total_failures} 个") 
    print(f"错误: {total_errors} 个")
    print(f"总耗时: {total_end_time - total_start_time:.2f} 秒")
    
    # 成功率
    if total_tests > 0:
        success_rate = ((total_tests - total_failures - total_errors) / total_tests) * 100
        print(f"成功率: {success_rate:.1f}%")
    
    print("=" * 80)
    
    # 返回总体成功状态
    overall_success = (total_failures == 0 and total_errors == 0 and successful_suites == len(test_modules))
    
    if overall_success:
        print("🎉 所有测试通过！交易系统功能正常。")
        return 0
    else:
        print("⚠️  存在测试失败，请检查相关功能。")
        return 1


def run_specific_test(test_name: str):
    """运行指定的测试"""
    
    test_mapping = {
        'aapl': 'tests.trading.test_comprehensive_aapl_scenario',
        'interactive': 'tests.trading.test_interactive_trading_flows',
        'edge': 'tests.trading.test_edge_cases_lot_tracking', 
        'performance': 'tests.trading.test_performance_large_volumes',
        'cost': 'tests.trading.test_cost_basis_comprehensive',
    }
    
    if test_name in test_mapping:
        module_name = test_mapping[test_name]
        print(f"运行测试: {module_name}")
        
        try:
            test_module = __import__(module_name, fromlist=[''])
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(test_module)
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(suite)
            
            return 0 if result.wasSuccessful() else 1
            
        except Exception as e:
            print(f"❌ 运行测试失败: {e}")
            return 1
    else:
        print(f"❌ 未知的测试名称: {test_name}")
        print("可用的测试:")
        for name, module in test_mapping.items():
            print(f"  {name}: {module}")
        return 1


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 运行指定测试
        test_name = sys.argv[1]
        exit_code = run_specific_test(test_name)
    else:
        # 运行完整测试套件
        exit_code = run_test_suite()
    
    sys.exit(exit_code)