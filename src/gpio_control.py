"""
GPIO制御モジュール
シンプルGPIO信号通信システム
"""

import time
import threading
from datetime import datetime
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("警告: RPi.GPIOがインポートできません。シミュレーションモードで動作します。")
    GPIO = None

from config.settings import GPIO_PINS, SWITCH_SETTINGS


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
        self.received_signals = []  # 受信した信号のリスト
        self.running = False
        self.transmit_thread = None
        self.receive_thread = None

        if not self.simulation_mode:
            try:
                self._setup_gpio()
            except RuntimeError as e:
                print(f"GPIO初期化エラー: {e}")
                print("GPIOが利用できないため、シミュレーションモードに切り替えます")
                self.simulation_mode = True

        print(f"GPIOコントローラー初期化完了 (シミュレーションモード: {self.simulation_mode})")

    def _setup_gpio(self):
        """GPIOの初期設定"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # 送信ピン: 出力
        GPIO.setup(self.pins['transmit'], GPIO.OUT)
        GPIO.output(self.pins['transmit'], GPIO.LOW)

        # 受信ピン: 入力、プルダウン
        GPIO.setup(self.pins['receive'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        # スイッチピン: 入力、プルアップ
        GPIO.setup(self.pins['switch'], GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def start(self):
        """通信開始"""
        if self.running:
            return

        self.running = True
        self.transmit_thread = threading.Thread(target=self._transmit_loop, daemon=True)
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.transmit_thread.start()
        self.receive_thread.start()
        print("GPIO通信を開始しました")

    def stop(self):
        """通信停止"""
        self.running = False
        if self.transmit_thread:
            self.transmit_thread.join(timeout=1.0)
        if self.receive_thread:
            self.receive_thread.join(timeout=1.0)
        print("GPIO通信を停止しました")

    def _transmit_loop(self):
        """送信ループ: スイッチ押下で送信ピンをHIGH"""
        while self.running:
            if not self.simulation_mode:
                switch_state = GPIO.input(self.pins['switch'])
                transmit_state = GPIO.LOW if switch_state == GPIO.HIGH else GPIO.HIGH  # スイッチがLOW(押下)ならHIGH
                GPIO.output(self.pins['transmit'], transmit_state)
            time.sleep(0.01)  # 10ms polling

    def _receive_loop(self):
        """受信ループ: 受信ピンの状態変化を検知し、モールス符号を解釈"""
        last_state = GPIO.LOW if not self.simulation_mode else 0
        signal_start = None
        current_morse = ""
        last_signal_time = time.time()

        while self.running:
            if not self.simulation_mode:
                current_state = GPIO.input(self.pins['receive'])
            else:
                current_state = 0  # シミュレーションでは常にLOW

            current_time = time.time()

            if current_state != last_state:
                if current_state == GPIO.HIGH:
                    # HIGH信号開始
                    signal_start = current_time
                else:
                    # HIGH信号終了
                    if signal_start:
                        duration = current_time - signal_start
                        # 短点/長点判定
                        if duration < 0.25:
                            morse_char = "・"  # 短点
                        else:
                            morse_char = "－"  # 長点

                        current_morse += morse_char
                        print(f"受信信号: {morse_char} (持続時間: {duration:.2f}秒)")

                        # モールス文字を記録
                        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                        self.received_signals.append({
                            'timestamp': timestamp,
                            'signal': morse_char,
                            'morse': current_morse
                        })

                        # 最新20件のみ保持
                        if len(self.received_signals) > 20:
                            self.received_signals.pop(0)

                        signal_start = None
                        last_signal_time = current_time

            # LOW信号の持続時間をチェック（文字間隔判定）
            elif current_state == GPIO.LOW and signal_start is None:
                low_duration = current_time - last_signal_time
                if low_duration > 1.0 and current_morse:  # 1秒以上LOWで文字区切り
                    print(f"文字完了: {current_morse}")
                    # ここで文字を追加（オプション）
                    current_morse = ""
                    last_signal_time = current_time

            last_state = current_state
            time.sleep(0.01)  # 10ms polling

    def get_received_signals(self):
        """受信した信号を取得"""
        return self.received_signals.copy()

    def get_switch_state(self):
        """スイッチの状態を取得"""
        if self.simulation_mode:
            return 'RELEASED'
        switch_state = GPIO.input(self.pins['switch'])
        return 'PRESSED' if switch_state == GPIO.LOW else 'RELEASED'

    def cleanup(self):
        """クリーンアップ"""
        self.stop()
        if not self.simulation_mode:
            GPIO.cleanup()
