"""
モールス論理モジュールのテスト
テスト計画書 4. 単体テスト手順 に基づく
"""

import unittest
import time
import threading
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.morse_logic import MorseConverter, MorseTransmitter, MorseReceiver, MorseCommunicationManager
from src.gpio_control import GPIOController
from config.settings import MORSE_CODE_DICT, REVERSE_MORSE_DICT


class TestMorseConverter(unittest.TestCase):
    """モールス変換クラスのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.converter = MorseConverter()
    
    def test_initialization(self):
        """初期化テスト"""
        self.assertEqual(self.converter.char_to_morse, MORSE_CODE_DICT)
        self.assertEqual(self.converter.morse_to_char, REVERSE_MORSE_DICT)
    
    def test_text_to_morse_basic(self):
        """基本テキスト→モールス変換テスト"""
        test_cases = [
            ('S', '...'),
            ('O', '---'),
            ('A', '.-'),
            ('B', '-...'),
            ('HELLO', '.... . .-.. .-.. ---')
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = self.converter.text_to_morse(text)
                self.assertEqual(result, expected)
    
    def test_text_to_morse_empty(self):
        """空文字列のテスト"""
        result = self.converter.text_to_morse('')
        self.assertEqual(result, '')
    
    def test_text_to_morse_case_insensitive(self):
        """大文字小文字の区別なしテスト"""
        result_lower = self.converter.text_to_morse('hello')
        result_upper = self.converter.text_to_morse('HELLO')
        self.assertEqual(result_lower, result_upper)
    
    def test_text_to_morse_with_spaces(self):
        """スペースを含むテキストテスト"""
        result = self.converter.text_to_morse('HELLO WORLD')
        expected = '.... . .-.. .-.. --- / .-- --- .-. .-.. -..'
        self.assertEqual(result, expected)
    
    def test_text_to_morse_unknown_chars(self):
        """不明な文字のテスト"""
        result = self.converter.text_to_morse('HELLO!')
        expected = '.... . .-.. .-.. --- -.-.--'
        self.assertEqual(result, expected)
    
    def test_morse_to_text_basic(self):
        """基本モールス→テキスト変換テスト"""
        test_cases = [
            ('...', 'S'),
            ('---', 'O'),
            ('.-', 'A'),
            ('-...', 'B'),
            ('.... . .-.. .-.. ---', 'HELLO')
        ]
        
        for morse, expected in test_cases:
            with self.subTest(morse=morse):
                result = self.converter.morse_to_text(morse)
                self.assertEqual(result, expected)
    
    def test_morse_to_text_empty(self):
        """空文字列のテスト"""
        result = self.converter.morse_to_text('')
        self.assertEqual(result, '')
    
    def test_morse_to_text_with_word_separator(self):
        """単語区切りのテスト"""
        result = self.converter.morse_to_text('.... . .-.. .-.. --- / .-- --- .-. .-.. -..')
        self.assertEqual(result, 'HELLO WORLD')
    
    def test_morse_to_text_unknown_morse(self):
        """不明なモールス符号のテスト"""
        result = self.converter.morse_to_text('.... . .-.. .-.. --- .-.-')
        self.assertEqual(result, 'HELLO?')
    
    def test_get_morse_timing(self):
        """モールス符号タイミング取得テスト"""
        dot_time = self.converter.get_morse_timing('.')
        dash_time = self.converter.get_morse_timing('-')
        invalid_time = self.converter.get_morse_timing('x')
        
        self.assertGreater(dot_time, 0)
        self.assertGreater(dash_time, 0)
        self.assertGreater(dash_time, dot_time)
        self.assertEqual(invalid_time, 0)


class TestMorseTransmitter(unittest.TestCase):
    """モールス送信クラスのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.gpio_controller = GPIOController(simulation_mode=True)
        self.transmitter = MorseTransmitter(self.gpio_controller)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.transmitter.stop_transmit()
        self.gpio_controller.cleanup()
    
    def test_initialization(self):
        """初期化テスト"""
        self.assertIsNotNone(self.transmitter.gpio_controller)
        self.assertIsNotNone(self.transmitter.converter)
        self.assertFalse(self.transmitter.is_transmitting)
        self.assertIsNone(self.transmitter.transmit_thread)
    
    def test_transmit_simple_text(self):
        """簡単なテキスト送信テスト"""
        callback = Mock()
        
        # 送信開始
        success = self.transmitter.transmit_text('S', callback)
        self.assertTrue(success)
        self.assertTrue(self.transmitter.is_transmitting)
        
        # 送信完了を待機
        time.sleep(1.0)
        
        # コールバックが呼ばれたことを確認
        callback.assert_called_once()
    
    def test_transmit_while_busy(self):
        """送信中の重複送信テスト"""
        callback = Mock()
        
        # 最初の送信
        self.transmitter.transmit_text('HELLO', callback)
        
        # 送信中に2回目の送信を試みる
        success = self.transmitter.transmit_text('WORLD', callback)
        self.assertFalse(success)
    
    def test_stop_transmit(self):
        """送信停止テスト"""
        # 長いメッセージを送信開始
        self.transmitter.transmit_text('HELLO WORLD THIS IS A TEST')
        
        # 少し待ってから停止
        time.sleep(0.1)
        self.transmitter.stop_transmit()
        
        # 停止したことを確認
        self.assertFalse(self.transmitter.is_transmitting)


class TestMorseReceiver(unittest.TestCase):
    """モールス受信クラスのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.gpio_controller = GPIOController(simulation_mode=True)
        self.receiver = MorseReceiver(self.gpio_controller)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.receiver.stop_receiving()
        self.gpio_controller.cleanup()
    
    def test_initialization(self):
        """初期化テスト"""
        self.assertIsNotNone(self.receiver.gpio_controller)
        self.assertIsNotNone(self.receiver.converter)
        self.assertIsNone(self.receiver.signal_receiver)
        self.assertEqual(self.receiver.received_text, '')
        self.assertEqual(self.receiver.current_word, '')
    
    def test_callback_registration(self):
        """コールバック登録テスト"""
        text_callback = Mock()
        char_callback = Mock()
        
        self.receiver.add_text_complete_callback(text_callback)
        self.receiver.add_char_received_callback(char_callback)
        
        self.assertEqual(len(self.receiver.text_complete_callbacks), 1)
        self.assertEqual(len(self.receiver.char_received_callbacks), 1)
    
    def test_start_stop_receiving(self):
        """受信開始・停止テスト"""
        # 受信開始
        self.receiver.start_receiving()
        self.assertIsNotNone(self.receiver.signal_receiver)
        
        # 受信停止
        self.receiver.stop_receiving()
    
    def test_get_received_text(self):
        """受信テキスト取得テスト"""
        # テキストを設定
        self.receiver.received_text = 'HELLO'
        self.receiver.current_word = ' WORLD'
        
        result = self.receiver.get_received_text()
        self.assertEqual(result, 'HELLO WORLD')
    
    def test_clear_received_text(self):
        """受信テキストクリアテスト"""
        # テキストを設定
        self.receiver.received_text = 'HELLO'
        self.receiver.current_word = ' WORLD'
        
        # クリア
        self.receiver.clear_received_text()
        
        # クリアされたことを確認
        self.assertEqual(self.receiver.received_text, '')
        self.assertEqual(self.receiver.current_word, '')


class TestMorseCommunicationManager(unittest.TestCase):
    """モールス通信管理クラスのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.gpio_controller = GPIOController(simulation_mode=True)
        self.manager = MorseCommunicationManager(self.gpio_controller)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.manager.stop_communication()
        self.gpio_controller.cleanup()
    
    def test_initialization(self):
        """初期化テスト"""
        self.assertIsNotNone(self.manager.gpio_controller)
        self.assertIsNotNone(self.manager.transmitter)
        self.assertIsNotNone(self.manager.receiver)
        self.assertFalse(self.manager.communication_active)
    
    def test_start_stop_communication(self):
        """通信開始・停止テスト"""
        # 通信開始
        self.manager.start_communication()
        self.assertTrue(self.manager.communication_active)
        
        # 通信停止
        self.manager.stop_communication()
        self.assertFalse(self.manager.communication_active)
    
    def test_send_message_without_communication(self):
        """通信なしでのメッセージ送信テスト"""
        success = self.manager.send_message('HELLO')
        self.assertFalse(success)
    
    def test_send_message_with_communication(self):
        """通信ありでのメッセージ送信テスト"""
        # 通信開始
        self.manager.start_communication()
        
        # メッセージ送信
        callback = Mock()
        success = self.manager.send_message('S', callback)
        self.assertTrue(success)
        
        # 少し待機
        time.sleep(0.5)
        
        # 通信停止
        self.manager.stop_communication()
    
    def test_get_received_message(self):
        """受信メッセージ取得テスト"""
        # メッセージを設定
        self.manager.receiver.received_text = 'HELLO'
        self.manager.receiver.current_word = ' WORLD'
        
        result = self.manager.get_received_message()
        self.assertEqual(result, 'HELLO WORLD')
    
    def test_clear_messages(self):
        """メッセージクリアテスト"""
        # メッセージを設定
        self.manager.receiver.received_text = 'HELLO'
        self.manager.receiver.current_word = ' WORLD'
        
        # クリア
        self.manager.clear_messages()
        
        # クリアされたことを確認
        self.assertEqual(self.manager.get_received_message(), '')
    
    def test_callback_registration(self):
        """コールバック登録テスト"""
        message_callback = Mock()
        char_callback = Mock()
        
        self.manager.add_message_received_callback(message_callback)
        self.manager.add_char_received_callback(char_callback)
        
        self.assertEqual(len(self.manager.receiver.text_complete_callbacks), 1)
        self.assertEqual(len(self.manager.receiver.char_received_callbacks), 1)


class TestMorseIntegration(unittest.TestCase):
    """モールス機能の統合テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.gpio_controller = GPIOController(simulation_mode=True)
        self.manager = MorseCommunicationManager(self.gpio_controller)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.manager.stop_communication()
        self.gpio_controller.cleanup()
    
    def test_full_communication_cycle(self):
        """完全な通信サイクルテスト"""
        received_messages = []
        
        def message_callback(message):
            received_messages.append(message)
        
        self.manager.add_message_received_callback(message_callback)
        
        # 通信開始
        self.manager.start_communication()
        
        # メッセージ送信
        self.manager.send_message('SOS')
        
        # 送信完了を待機
        time.sleep(2.0)
        
        # 通信停止
        self.manager.stop_communication()
        
        # テストが完了したことを確認
        self.assertTrue(self.manager.communication_active == False)


if __name__ == '__main__':
    # テスト実行
    unittest.main(verbosity=2)
