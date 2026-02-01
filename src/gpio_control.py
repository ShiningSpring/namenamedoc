"""
GPIO制御モジュール
Raspberry PiのGPIOピンを制御するためのモジュール
"""

import time
import threading
from datetime import datetime
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("警告: RPi.GPIOがインポートできません。シミュレーションモードで動作します。")
    GPIO = None

from config.settings import GPIO_PINS, SWITCH_SETTINGS, MORSE_TIMING


class GPIOController:
    """GPIO制御クラス"""
    
    def __init__(self, simulation_mode=False):
        """
        初期化
        Args:
            simulation_mode (bool): シミュレーションモードフラグ
        """
        self.simulation_mode = simulation_mode or GPIO is None
        self.pins = GPIO_PINS
        self.switch_pressed = False
        self.switch_press_start = None
        self.switch_callbacks = []
        
        if not self.simulation_mode:
            self._setup_gpio()
        
        print(f"GPIOコントローラー初期化完了 (シミュレーションモード: {self.simulation_mode})")
    
    def _setup_gpio(self):
        """GPIOの初期設定"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # 出力ピン設定
        GPIO.setup(self.pins['transmit'], GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.pins['led'], GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.pins['buzzer'], GPIO.OUT, initial=GPIO.LOW)
        
        # 入力ピン設定（スイッチ）
        GPIO.setup(self.pins['switch'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # スイッチ割り込み設定
        GPIO.add_event_detect(
            self.pins['switch'], 
            GPIO.BOTH, 
            callback=self._switch_callback,
            bouncetime=int(SWITCH_SETTINGS['debounce_time'] * 1000)
        )
    
    def _switch_callback(self, channel):
        """スイッチ割り込みコールバック"""
        if self.simulation_mode:
            return
        
        current_state = GPIO.input(channel) == GPIO.LOW  # LOW = 押されている
        
        if current_state and not self.switch_pressed:
            # スイッチが押された
            self.switch_pressed = True
            self.switch_press_start = time.time()
            print("スイッチ押下検出")
            
        elif not current_state and self.switch_pressed:
            # スイッチが離された
            self.switch_pressed = False
            press_duration = time.time() - self.switch_press_start
            self.switch_press_start = None
            
            print(f"スイッチ解放検出 (押下時間: {press_duration:.2f}秒)")
            
            # コールバック関数を呼び出し
            for callback in self.switch_callbacks:
                callback(press_duration)
    
    def add_switch_callback(self, callback):
        """スイッチコールバック関数を追加"""
        self.switch_callbacks.append(callback)
    
    def set_transmit_high(self):
        """送信ピンをHIGHに設定"""
        if not self.simulation_mode:
            GPIO.output(self.pins['transmit'], GPIO.HIGH)
        print("送信ピン: HIGH")
    
    def set_transmit_low(self):
        """送信ピンをLOWに設定"""
        if not self.simulation_mode:
            GPIO.output(self.pins['transmit'], GPIO.LOW)
        print("送信ピン: LOW")
    
    def transmit_dot(self):
        """ドット信号を送信"""
        self.set_transmit_high()
        time.sleep(MORSE_TIMING['dot'])
        self.set_transmit_low()
        time.sleep(MORSE_TIMING['intra_char_gap'])
    
    def transmit_dash(self):
        """ダッシュ信号を送信"""
        self.set_transmit_high()
        time.sleep(MORSE_TIMING['dash'])
        self.set_transmit_low()
        time.sleep(MORSE_TIMING['intra_char_gap'])
    
    def get_receive_state(self):
        """受信ピンの状態を取得"""
        if self.simulation_mode:
            return False  # シミュレーションでは常にLOW
        return GPIO.input(self.pins['receive']) == GPIO.HIGH
    
    def monitor_receive_signal(self, callback, stop_event):
        """
        受信信号を監視するスレッド
        Args:
            callback: 信号検知時のコールバック関数
            stop_event: 停止イベント
        """
        last_state = False
        signal_start = None
        
        while not stop_event.is_set():
            current_state = self.get_receive_state()
            
            if current_state and not last_state:
                # 信号の立ち上がりを検知
                signal_start = time.time()
                print("受信信号開始検知")
                
            elif not current_state and last_state and signal_start:
                # 信号の立ち下がりを検知
                signal_duration = time.time() - signal_start
                print(f"受信信号終了検知 (持続時間: {signal_duration:.2f}秒)")
                
                # コールバックを呼び出し
                if callback:
                    callback(signal_duration)
                
                signal_start = None
            
            last_state = current_state
            time.sleep(0.01)  # 10msごとにチェック
    
    def simulate_switch_press(self, duration):
        """スイッチ押下をシミュレート（テスト用）"""
        print(f"スイッチ押下シミュレーション (時間: {duration:.2f}秒)")
        for callback in self.switch_callbacks:
            callback(duration)
    
    def cleanup(self):
        """GPIOのクリーンアップ"""
        if not self.simulation_mode:
            GPIO.cleanup()
        print("GPIOクリーンアップ完了")


class SignalReceiver:
    """信号受信クラス"""
    
    def __init__(self, gpio_controller):
        """
        初期化
        Args:
            gpio_controller: GPIOControllerインスタンス
        """
        self.gpio_controller = gpio_controller
        self.received_signals = []
        self.current_char_signals = []
        self.last_signal_time = None
        self.stop_event = threading.Event()
        self.receive_thread = None
        self.char_complete_callbacks = []
    
    def add_char_complete_callback(self, callback):
        """文字完了コールバックを追加"""
        self.char_complete_callbacks.append(callback)
    
    def start_monitoring(self):
        """信号監視を開始"""
        self.stop_event.clear()
        self.receive_thread = threading.Thread(
            target=self.gpio_controller.monitor_receive_signal,
            args=(self._signal_detected, self.stop_event)
        )
        self.receive_thread.daemon = True
        self.receive_thread.start()
        print("信号監視開始")
    
    def stop_monitoring(self):
        """信号監視を停止"""
        self.stop_event.set()
        if self.receive_thread:
            self.receive_thread.join()
        print("信号監視停止")
    
    def _signal_detected(self, duration):
        """信号検知時の処理"""
        current_time = time.time()
        
        # ドット/ダッシュ判定
        if duration < MORSE_TIMING['dash'] * 0.7:  # しきい値で判定
            signal = '.'
            print(f"ドット検知 (時間: {duration:.2f}秒)")
        else:
            signal = '-'
            print(f"ダッシュ検知 (時間: {duration:.2f}秒)")
        
        self.current_char_signals.append(signal)
        self.last_signal_time = current_time
        
        # 文字区切りタイマー開始
        self._start_char_timer()
    
    def _start_char_timer(self):
        """文字区切りタイマー"""
        def check_char_complete():
            time.sleep(MORSE_TIMING['inter_char_gap'])
            
            if (self.last_signal_time and 
                time.time() - self.last_signal_time >= MORSE_TIMING['inter_char_gap'] and
                self.current_char_signals):
                
                # 文字が完成した
                morse_char = ''.join(self.current_char_signals)
                self.received_signals.append(morse_char)
                
                print(f"文字受信完了: {morse_char}")
                
                # コールバックを呼び出し
                for callback in self.char_complete_callbacks:
                    callback(morse_char)
                
                self.current_char_signals = []
        
        timer_thread = threading.Thread(target=check_char_complete)
        timer_thread.daemon = True
        timer_thread.start()
    
    def get_received_signals(self):
        """受信した信号を取得"""
        return self.received_signals.copy()
    
    def clear_received_signals(self):
        """受信信号をクリア"""
        self.received_signals.clear()
        self.current_char_signals = []
        print("受信信号をクリア")
