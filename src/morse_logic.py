"""
モールス符号変換ロジックモジュール
文字とモールス符号の相互変換、および送受信ロジックを担当
"""

import time
import threading
from datetime import datetime
from config.settings import MORSE_CODE_DICT, REVERSE_MORSE_DICT, MORSE_TIMING


class MorseConverter:
    """モールス符号変換クラス"""
    
    def __init__(self):
        """初期化"""
        self.char_to_morse = MORSE_CODE_DICT
        self.morse_to_char = REVERSE_MORSE_DICT
        print("モールス変換器初期化完了")
    
    def text_to_morse(self, text):
        """
        テキストをモールス符号に変換
        Args:
            text (str): 変換するテキスト
        Returns:
            str: モールス符号
        """
        if not text:
            return ""
        
        text = text.upper()
        morse_codes = []
        
        for char in text:
            if char in self.char_to_morse:
                morse_codes.append(self.char_to_morse[char])
            else:
                print(f"警告: 文字 '{char}' はモールス符号に変換できません")
                morse_codes.append('?')  # 不明な文字は?で表現
        
        return ' '.join(morse_codes)
    
    def morse_to_text(self, morse):
        """
        モールス符号をテキストに変換
        Args:
            morse (str): モールス符号（スペース区切り）
        Returns:
            str: 変換されたテキスト
        """
        if not morse:
            return ""
        
        morse_chars = morse.split(' ')
        text_chars = []
        
        for morse_char in morse_chars:
            if morse_char in self.morse_to_char:
                text_chars.append(self.morse_to_char[morse_char])
            elif morse_char == '/':  # 単語区切り
                text_chars.append(' ')
            else:
                print(f"警告: モールス符号 '{morse_char}' は変換できません")
                text_chars.append('?')
        
        return ''.join(text_chars)
    
    def get_morse_timing(self, morse_char):
        """
        モールス符号のタイミング情報を取得
        Args:
            morse_char (str): モールス符号（.または-）
        Returns:
            float: 信号の持続時間（秒）
        """
        if morse_char == '.':
            return MORSE_TIMING['dot']
        elif morse_char == '-':
            return MORSE_TIMING['dash']
        else:
            return 0.0


class MorseTransmitter:
    """モールス信号送信クラス"""
    
    def __init__(self, gpio_controller):
        """
        初期化
        Args:
            gpio_controller: GPIOControllerインスタンス
        """
        self.gpio_controller = gpio_controller
        self.converter = MorseConverter()
        self.is_transmitting = False
        self.transmit_thread = None
        self.stop_transmission = threading.Event()
        print("モールス送信器初期化完了")
    
    def transmit_text(self, text, callback=None):
        """
        テキストをモールス信号として送信
        Args:
            text (str): 送信するテキスト
            callback: 送信完了時のコールバック関数
        """
        if self.is_transmitting:
            print("警告: 送信中です。完了までお待ちください。")
            return False
        
        morse_code = self.converter.text_to_morse(text)
        print(f"送信テキスト: {text}")
        print(f"モールス符号: {morse_code}")
        
        self.transmit_thread = threading.Thread(
            target=self._transmit_morse_sequence,
            args=(morse_code, callback)
        )
        self.transmit_thread.start()
        return True
    
    def _transmit_morse_sequence(self, morse_code, callback):
        """モールス符号シーケンスを送信"""
        self.is_transmitting = True
        self.stop_transmission.clear()
        
        try:
            morse_chars = morse_code.split(' ')
            
            for i, morse_char in enumerate(morse_chars):
                if self.stop_transmission.is_set():
                    print("送信が中断されました")
                    break
                
                if morse_char == '/':  # 単語区切り
                    time.sleep(MORSE_TIMING['inter_word_gap'])
                    print("単語区切り")
                else:
                    # ドットまたはダッシュを送信
                    if morse_char == '.':
                        self.gpio_controller.transmit_dot()
                    elif morse_char == '-':
                        self.gpio_controller.transmit_dash()
                    
                    print(f"送信: {morse_char}")
                    
                    # 文字間の待機（最後の文字以外）
                    if i < len(morse_chars) - 1 and morse_chars[i + 1] != '/':
                        time.sleep(MORSE_TIMING['inter_char_gap'])
            
            print("送信完了")
            
        except Exception as e:
            print(f"送信エラー: {e}")
        
        finally:
            self.is_transmitting = False
            if callback:
                callback()
    
    def stop_transmit(self):
        """送信を停止"""
        self.stop_transmission.set()
        if self.transmit_thread:
            self.transmit_thread.join()
        print("送信停止要求")


class MorseReceiver:
    """モールス信号受信クラス"""
    
    def __init__(self, gpio_controller):
        """
        初期化
        Args:
            gpio_controller: GPIOControllerインスタンス
        """
        self.gpio_controller = gpio_controller
        self.converter = MorseConverter()
        self.signal_receiver = None
        self.received_text = ""
        self.current_word = ""
        self.text_complete_callbacks = []
        self.char_received_callbacks = []
        print("モールス受信器初期化完了")
    
    def add_text_complete_callback(self, callback):
        """テキスト受信完了コールバックを追加"""
        self.text_complete_callbacks.append(callback)
    
    def add_char_received_callback(self, callback):
        """文字受信コールバックを追加"""
        self.char_received_callbacks.append(callback)
    
    def start_receiving(self):
        """受信を開始"""
        if self.signal_receiver:
            self.signal_receiver.stop_monitoring()
        
        self.signal_receiver = SignalReceiver(self.gpio_controller)
        self.signal_receiver.add_char_complete_callback(self._on_char_received)
        self.signal_receiver.start_monitoring()
        print("モールス受信開始")
    
    def stop_receiving(self):
        """受信を停止"""
        if self.signal_receiver:
            self.signal_receiver.stop_monitoring()
        print("モールス受信停止")
    
    def _on_char_received(self, morse_char):
        """文字受信時の処理"""
        # モールス符号を文字に変換
        text_char = self.converter.morse_to_text(morse_char)
        
        if text_char == ' ':
            # 単語区切り
            self.current_word += ' '
            print(f"単語区切り受信")
        else:
            self.current_word += text_char
            print(f"文字受信: {morse_char} -> {text_char}")
        
        # 文字受信コールバックを呼び出し
        for callback in self.char_received_callbacks:
            callback(text_char)
        
        # 単語完了タイマーを開始
        self._start_word_timer()
    
    def _start_word_timer(self):
        """単語完了タイマー"""
        def check_word_complete():
            time.sleep(MORSE_TIMING['inter_word_gap'])
            
            # 新しい文字が来なければ単語完了と判断
            if (self.signal_receiver and 
                len(self.signal_receiver.current_char_signals) == 0 and
                self.current_word):
                
                self.received_text += self.current_word
                completed_word = self.current_word
                self.current_word = ""
                
                print(f"単語受信完了: {completed_word}")
                
                # テキスト受信完了コールバックを呼び出し
                for callback in self.text_complete_callbacks:
                    callback(completed_word)
        
        timer_thread = threading.Thread(target=check_word_complete)
        timer_thread.daemon = True
        timer_thread.start()
    
    def get_received_text(self):
        """受信したテキストを取得"""
        full_text = self.received_text + self.current_word
        return full_text
    
    def clear_received_text(self):
        """受信テキストをクリア"""
        self.received_text = ""
        self.current_word = ""
        if self.signal_receiver:
            self.signal_receiver.clear_received_signals()
        print("受信テキストをクリア")


# SignalReceiverを再インポート（循環インポート回避）
from .gpio_control import SignalReceiver


class MorseCommunicationManager:
    """モールス通信管理クラス"""
    
    def __init__(self, gpio_controller):
        """
        初期化
        Args:
            gpio_controller: GPIOControllerインスタンス
        """
        self.gpio_controller = gpio_controller
        self.transmitter = MorseTransmitter(gpio_controller)
        self.receiver = MorseReceiver(gpio_controller)
        self.communication_active = False
        print("モールス通信管理器初期化完了")
    
    def start_communication(self):
        """双方向通信を開始"""
        if self.communication_active:
            print("警告: 通信は既に開始されています")
            return
        
        self.receiver.start_receiving()
        self.communication_active = True
        print("双方向通信開始")
    
    def stop_communication(self):
        """双方向通信を停止"""
        self.transmitter.stop_transmit()
        self.receiver.stop_receiving()
        self.communication_active = False
        print("双方向通信停止")
    
    def send_message(self, text, callback=None):
        """メッセージを送信"""
        if not self.communication_active:
            print("警告: 通信が開始されていません")
            return False
        
        return self.transmitter.transmit_text(text, callback)
    
    def get_received_message(self):
        """受信メッセージを取得"""
        return self.receiver.get_received_text()
    
    def clear_messages(self):
        """メッセージをクリア"""
        self.receiver.clear_received_text()
        print("メッセージをクリア")
    
    def add_message_received_callback(self, callback):
        """メッセージ受信コールバックを追加"""
        self.receiver.add_text_complete_callback(callback)
    
    def add_char_received_callback(self, callback):
        """文字受信コールバックを追加"""
        self.receiver.add_char_received_callback(callback)
