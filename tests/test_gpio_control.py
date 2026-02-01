"""
GPIO制御モジュールのテスト
テスト計画書 4. 単体テスト手順 に基づく
"""

import unittest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.gpio_control import GPIOController, SignalReceiver
from config.settings import GPIO_PINS, SWITCH_SETTINGS, MORSE_TIMING


class TestGPIOController(unittest.TestCase):
    """GPIOコントローラーのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.simulation_mode = True
        self.gpio_controller = GPIOController(simulation_mode=self.simulation_mode)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.gpio_controller.cleanup()
    
    def test_initialization(self):
        """初期化テスト"""
        self.assertTrue(self.gpio_controller.simulation_mode)
        self.assertEqual(self.gpio_controller.pins, GPIO_PINS)
        self.assertFalse(self.gpio_controller.switch_pressed)
        self.assertIsNone(self.gpio_controller.switch_press_start)
        self.assertEqual(len(self.gpio_controller.switch_callbacks), 0)
    
    def test_switch_callback_registration(self):
        """スイッチコールバック登録テスト"""
        callback = Mock()
        self.gpio_controller.add_switch_callback(callback)
        self.assertEqual(len(self.gpio_controller.switch_callbacks), 1)
        self.assertIn(callback, self.gpio_controller.switch_callbacks)
    
    def test_transmit_high_low(self):
        """送信ピン制御テスト"""
        # HIGH設定テスト
        self.gpio_controller.set_transmit_high()
        # シミュレーションモードでは例外が発生しないことを確認
        
        # LOW設定テスト
        self.gpio_controller.set_transmit_low()
        # シミュレーションモードでは例外が発生しないことを確認
    
    def test_transmit_dot(self):
        """ドット信号送信テスト"""
        start_time = time.time()
        self.gpio_controller.transmit_dot()
        elapsed_time = time.time() - start_time
        
        # ドット信号の時間 + 文字内間隔の時間が経過したことを確認
        expected_time = MORSE_TIMING['dot'] + MORSE_TIMING['intra_char_gap']
        self.assertAlmostEqual(elapsed_time, expected_time, delta=0.1)
    
    def test_transmit_dash(self):
        """ダッシュ信号送信テスト"""
        start_time = time.time()
        self.gpio_controller.transmit_dash()
        elapsed_time = time.time() - start_time
        
        # ダッシュ信号の時間 + 文字内間隔の時間が経過したことを確認
        expected_time = MORSE_TIMING['dash'] + MORSE_TIMING['intra_char_gap']
        self.assertAlmostEqual(elapsed_time, expected_time, delta=0.1)
    
    def test_get_receive_state(self):
        """受信ピン状態取得テスト"""
        state = self.gpio_controller.get_receive_state()
        self.assertFalse(state)  # シミュレーションモードでは常にFalse
    
    def test_simulate_switch_press(self):
        """スイッチ押下シミュレーションテスト"""
        callback = Mock()
        self.gpio_controller.add_switch_callback(callback)
        
        # 短押しシミュレーション
        test_duration = 0.2
        self.gpio_controller.simulate_switch_press(test_duration)
        
        # コールバックが呼ばれたことを確認
        callback.assert_called_once_with(test_duration)
    
    def test_cleanup(self):
        """クリーンアップテスト"""
        # クリーンアップが例外なく完了することを確認
        self.gpio_controller.cleanup()


class TestSignalReceiver(unittest.TestCase):
    """信号受信クラスのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.gpio_controller = GPIOController(simulation_mode=True)
        self.signal_receiver = SignalReceiver(self.gpio_controller)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.signal_receiver.stop_monitoring()
        self.gpio_controller.cleanup()
    
    def test_initialization(self):
        """初期化テスト"""
        self.assertEqual(len(self.signal_receiver.received_signals), 0)
        self.assertEqual(len(self.signal_receiver.current_char_signals), 0)
        self.assertIsNone(self.signal_receiver.last_signal_time)
        self.assertEqual(len(self.signal_receiver.char_complete_callbacks), 0)
    
    def test_char_complete_callback_registration(self):
        """文字完了コールバック登録テスト"""
        callback = Mock()
        self.signal_receiver.add_char_complete_callback(callback)
        self.assertEqual(len(self.signal_receiver.char_complete_callbacks), 1)
        self.assertIn(callback, self.signal_receiver.char_complete_callbacks)
    
    def test_start_stop_monitoring(self):
        """監視開始・停止テスト"""
        # 監視開始
        self.signal_receiver.start_monitoring()
        self.assertIsNotNone(self.signal_receiver.receive_thread)
        self.assertFalse(self.signal_receiver.stop_event.is_set())
        
        # 監視停止
        self.signal_receiver.stop_monitoring()
        self.assertTrue(self.signal_receiver.stop_event.is_set())
    
    def test_signal_detection(self):
        """信号検知テスト"""
        callback = Mock()
        self.signal_receiver.add_char_complete_callback(callback)
        
        # ドット信号をシミュレート
        dot_duration = MORSE_TIMING['dot'] * 0.5  # ドットとして判定される時間
        self.signal_receiver._signal_detected(dot_duration)
        
        # 少し待ってから文字区切りを待つ
        time.sleep(MORSE_TIMING['inter_char_gap'] + 0.1)
        
        # ドットが検知されたことを確認
        self.assertEqual(len(self.signal_receiver.current_char_signals), 1)
        self.assertEqual(self.signal_receiver.current_char_signals[0], '.')
    
    def test_get_received_signals(self):
        """受信信号取得テスト"""
        # 信号を手動で追加
        self.signal_receiver.received_signals.append('.')
        self.signal_receiver.received_signals.append('-')
        
        signals = self.signal_receiver.get_received_signals()
        self.assertEqual(signals, ['.'])
        self.assertEqual(len(signals), 1)  # コピーが返されることを確認
    
    def test_clear_received_signals(self):
        """受信信号クリアテスト"""
        # 信号を追加
        self.signal_receiver.received_signals.append('.')
        self.signal_receiver.current_char_signals.append('-')
        
        # クリア
        self.signal_receiver.clear_received_signals()
        
        # クリアされたことを確認
        self.assertEqual(len(self.signal_receiver.received_signals), 0)
        self.assertEqual(len(self.signal_receiver.current_char_signals), 0)


class TestGPIOIntegration(unittest.TestCase):
    """GPIO制御の統合テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.gpio_controller = GPIOController(simulation_mode=True)
        self.signal_receiver = SignalReceiver(self.gpio_controller)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.signal_receiver.stop_monitoring()
        self.gpio_controller.cleanup()
    
    def test_switch_to_signal_flow(self):
        """スイッチから信号へのフローテスト"""
        received_chars = []
        
        def char_received_callback(morse_char):
            received_chars.append(morse_char)
        
        self.signal_receiver.add_char_complete_callback(char_received_callback)
        self.signal_receiver.start_monitoring()
        
        # スイッチ短押しをシミュレート（ドット）
        self.gpio_controller.simulate_switch_press(0.2)
        
        # 文字区切り時間待機
        time.sleep(MORSE_TIMING['inter_char_gap'] + 0.1)
        
        # ドットが受信されたことを確認
        self.assertIn('.', received_chars)
    
    def test_multiple_signals(self):
        """複数信号テスト"""
        received_chars = []
        
        def char_received_callback(morse_char):
            received_chars.append(morse_char)
        
        self.signal_receiver.add_char_complete_callback(char_received_callback)
        self.signal_receiver.start_monitoring()
        
        # 複数の信号を送信
        self.gpio_controller.simulate_switch_press(0.2)  # ドット
        time.sleep(0.1)
        self.gpio_controller.simulate_switch_press(0.5)  # ダッシュ
        
        # 文字区切り時間待機
        time.sleep(MORSE_TIMING['inter_char_gap'] + 0.2)
        
        # 両方の信号が受信されたことを確認
        self.assertIn('.', received_chars)
        self.assertIn('-', received_chars)


if __name__ == '__main__':
    # テスト実行
    unittest.main(verbosity=2)
