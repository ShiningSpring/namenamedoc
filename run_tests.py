"""
テスト実行スクリプト
テスト計画書に基づくすべてのテストを実行
"""

import unittest
import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def run_all_tests():
    """すべてのテストを実行"""
    print("=" * 60)
    print("Raspberry Pi モールス信号通信システム テスト実行")
    print("=" * 60)
    
    # テストディレクトリを追加
    tests_dir = project_root / 'tests'
    sys.path.insert(0, str(tests_dir))
    
    # テストスイートを作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストモジュールを追加
    test_modules = [
        'test_gpio_control',
        'test_morse_logic', 
        'test_integration'
    ]
    
    for module_name in test_modules:
        try:
            module = __import__(module_name)
            suite.addTests(loader.loadTestsFromModule(module))
            print(f"✓ {module_name} を読み込みました")
        except ImportError as e:
            print(f"✗ {module_name} の読み込みに失敗しました: {e}")
    
    print("\nテスト実行中...")
    print("-" * 60)
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    print("-" * 60)
    print(f"テスト完了")
    print(f"実行数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n失敗したテスト:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nエラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    # 終了コードを返す
    return 0 if result.wasSuccessful() else 1


def run_specific_test(test_name):
    """特定のテストを実行"""
    print(f"特定のテストを実行: {test_name}")
    
    tests_dir = project_root / 'tests'
    sys.path.insert(0, str(tests_dir))
    
    try:
        module = __import__(test_name)
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(module)
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return 0 if result.wasSuccessful() else 1
        
    except ImportError as e:
        print(f"テストモジュール {test_name} が見つかりません: {e}")
        return 1


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='モールス信号通信システム テスト実行')
    parser.add_argument('--test', '-t', help='特定のテストモジュールを実行')
    parser.add_argument('--list', '-l', action='store_true', help='利用可能なテストを一覧表示')
    
    args = parser.parse_args()
    
    if args.list:
        print("利用可能なテスト:")
        test_modules = [
            'test_gpio_control - GPIO制御モジュールテスト',
            'test_morse_logic - モールス論理モジュールテスト',
            'test_integration - 統合テスト'
        ]
        for module in test_modules:
            print(f"  {module}")
        return 0
    
    if args.test:
        return run_specific_test(args.test)
    else:
        return run_all_tests()


if __name__ == '__main__':
    sys.exit(main())
