"""
LED・ブザー制御モジュール
視覚・聴覚フィードバックを担当
"""

import time
import threading
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("警告: RPi.GPIOがインポートできません。シミュレーションモードで動作します。")
    GPIO = None

from config.settings import GPIO_PINS, FEEDBACK, MORSE_TIMING


class LEDController:
    """LED制御クラス"""
    
    def __init__(self, simulation_mode=False):
        """
        初期化
        Args:
            simulation_mode (bool): シミュレーションモードフラグ
        """
        self.simulation_mode = simulation_mode or GPIO is None
        self.led_pin = GPIO_PINS['led']
        self.enabled = FEEDBACK['led_enabled']
        self.brightness = FEEDBACK['led_brightness']
        self.is_blinking = False
        self.blink_thread = None
        self.stop_blinking = threading.Event()
        
        if not self.simulation_mode:
            self._setup_led()
        
        print(f"LEDコントローラー初期化完了 (シミュレーションモード: {self.simulation_mode})")
    
    def _setup_led(self):
        """LEDの初期設定"""
        GPIO.setup(self.led_pin, GPIO.OUT, initial=GPIO.LOW)
        # PWM制御を有効にする
        self.pwm = GPIO.PWM(self.led_pin, 1000)  # 1kHz
        self.pwm.start(0)  # 初期は消灯
    
    def turn_on(self, brightness=None):
        """LEDを点灯"""
        if not self.enabled:
            return
        
        if brightness is None:
            brightness = self.brightness
        
        if not self.simulation_mode:
            duty_cycle = int(brightness * 100)
            self.pwm.ChangeDutyCycle(duty_cycle)
        
        print(f"LED点灯 (輝度: {brightness:.0%})")
    
    def turn_off(self):
        """LEDを消灯"""
        if not self.enabled:
            return
        
        if not self.simulation_mode:
            self.pwm.ChangeDutyCycle(0)
        
        print("LED消灯")
    
    def blink(self, duration=0.2, count=1, brightness=None):
        """
        LEDを点滅
        Args:
            duration (float): 点灯時間（秒）
            count (int): 点滅回数
            brightness (float): 輝度 (0.0-1.0)
        """
        if not self.enabled:
            return
        
        def blink_sequence():
            for i in range(count):
                if self.stop_blinking.is_set():
                    break
                
                self.turn_on(brightness)
                time.sleep(duration)
                self.turn_off()
                
                if i < count - 1:  # 最後の点滅以外は待機
                    time.sleep(duration)
        
        blink_thread = threading.Thread(target=blink_sequence)
        blink_thread.daemon = True
        blink_thread.start()
    
    def start_continuous_blink(self, on_duration=0.5, off_duration=0.5, brightness=None):
        """
        連続点滅を開始
        Args:
            on_duration (float): 点灯時間（秒）
            off_duration (float): 消灯時間（秒）
            brightness (float): 輝度 (0.0-1.0)
        """
        if self.is_blinking:
            print("警告: 連続点滅は既に開始されています")
            return
        
        self.is_blinking = True
        self.stop_blinking.clear()
        
        def continuous_blink():
            while not self.stop_blinking.is_set():
                self.turn_on(brightness)
                time.sleep(on_duration)
                self.turn_off()
                time.sleep(off_duration)
        
        self.blink_thread = threading.Thread(target=continuous_blink)
        self.blink_thread.daemon = True
        self.blink_thread.start()
        print("連続点滅開始")
    
    def stop_continuous_blink(self):
        """連続点滅を停止"""
        self.stop_blinking.set()
        if self.blink_thread:
            self.blink_thread.join()
        self.is_blinking = False
        self.turn_off()
        print("連続点滅停止")
    
    def set_brightness(self, brightness):
        """
        輝度を設定
        Args:
            brightness (float): 輝度 (0.0-1.0)
        """
        self.brightness = max(0.0, min(1.0, brightness))
        print(f"LED輝度設定: {self.brightness:.0%}")
    
    def set_enabled(self, enabled):
        """
        LEDを有効/無効化
        Args:
            enabled (bool): 有効フラグ
        """
        self.enabled = enabled
        if not enabled:
            self.turn_off()
        print(f"LED有効設定: {enabled}")
    
    def cleanup(self):
        """LEDのクリーンアップ"""
        self.stop_continuous_blink()
        if not self.simulation_mode:
            self.pwm.stop()
        print("LEDクリーンアップ完了")


class BuzzerController:
    """ブザー制御クラス"""
    
    def __init__(self, simulation_mode=False):
        """
        初期化
        Args:
            simulation_mode (bool): シミュレーションモードフラグ
        """
        self.simulation_mode = simulation_mode or GPIO is None
        self.buzzer_pin = GPIO_PINS['buzzer']
        self.enabled = FEEDBACK['sound_enabled']
        self.frequency = FEEDBACK['buzzer_frequency']
        self.is_beeping = False
        self.beep_thread = None
        self.stop_beeping = threading.Event()
        
        if not self.simulation_mode:
            self._setup_buzzer()
        
        print(f"ブザーコントローラー初期化完了 (シミュレーションモード: {self.simulation_mode})")
    
    def _setup_buzzer(self):
        """ブザーの初期設定"""
        GPIO.setup(self.buzzer_pin, GPIO.OUT, initial=GPIO.LOW)
        self.pwm = GPIO.PWM(self.buzzer_pin, self.frequency)
        self.pwm.start(0)  # 初期は消音
    
    def turn_on(self, frequency=None):
        """ブザーを鳴らす"""
        if not self.enabled:
            return
        
        if frequency is None:
            frequency = self.frequency
        
        if not self.simulation_mode:
            self.pwm.ChangeFrequency(frequency)
            self.pwm.ChangeDutyCycle(50)  # 50%デューティ比
        
        print(f"ブザーON (周波数: {frequency}Hz)")
    
    def turn_off(self):
        """ブザーを消音"""
        if not self.enabled:
            return
        
        if not self.simulation_mode:
            self.pwm.ChangeDutyCycle(0)
        
        print("ブザーOFF")
    
    def beep(self, duration=0.2, frequency=None):
        """
        ブザーを鳴らす
        Args:
            duration (float): 鳴動時間（秒）
            frequency (int): 周波数 (Hz)
        """
        if not self.enabled:
            return
        
        def beep_sequence():
            self.turn_on(frequency)
            time.sleep(duration)
            self.turn_off()
        
        beep_thread = threading.Thread(target=beep_sequence)
        beep_thread.daemon = True
        beep_thread.start()
    
    def play_morse_signal(self, morse_char):
        """
        モールス信号をブザーで再生
        Args:
            morse_char (str): モールス符号（.または-）
        """
        if not self.enabled:
            return
        
        if morse_char == '.':
            duration = MORSE_TIMING['dot']
        elif morse_char == '-':
            duration = MORSE_TIMING['dash']
        else:
            return
        
        self.beep(duration)
        print(f"モールス信号再生: {morse_char} ({duration}秒)")
    
    def play_tone(self, frequency, duration):
        """
        特定のトーンを再生
        Args:
            frequency (int): 周波数 (Hz)
            duration (float): 再生時間（秒）
        """
        if not self.enabled:
            return
        
        def tone_sequence():
            self.turn_on(frequency)
            time.sleep(duration)
            self.turn_off()
        
        tone_thread = threading.Thread(target=tone_sequence)
        tone_thread.daemon = True
        tone_thread.start()
    
    def set_frequency(self, frequency):
        """
        周波数を設定
        Args:
            frequency (int): 周波数 (Hz)
        """
        self.frequency = max(100, min(10000, frequency))
        print(f"ブザー周波数設定: {self.frequency}Hz")
    
    def set_enabled(self, enabled):
        """
        ブザーを有効/無効化
        Args:
            enabled (bool): 有効フラグ
        """
        self.enabled = enabled
        if not enabled:
            self.turn_off()
        print(f"ブザー有効設定: {enabled}")
    
    def cleanup(self):
        """ブザーのクリーンアップ"""
        self.turn_off()
        if not self.simulation_mode:
            self.pwm.stop()
        print("ブザークリーンアップ完了")


class FeedbackController:
    """フィードバック制御クラス"""
    
    def __init__(self, simulation_mode=False):
        """
        初期化
        Args:
            simulation_mode (bool): シミュレーションモードフラグ
        """
        self.led_controller = LEDController(simulation_mode)
        self.buzzer_controller = BuzzerController(simulation_mode)
        self.transmit_active = False
        self.receive_active = False
        print("フィードバックコントローラー初期化完了")
    
    def on_transmit_start(self):
        """送信開始時のフィードバック"""
        self.transmit_active = True
        self.led_controller.start_continuous_blink(0.1, 0.1, 1.0)
        print("送信開始フィードバック")
    
    def on_transmit_end(self):
        """送信終了時のフィードバック"""
        self.transmit_active = False
        self.led_controller.stop_continuous_blink()
        self.led_controller.blink(0.5, 2, 0.8)  # 完了通知
        self.buzzer_controller.beep(0.1, 800)  # 完了音
        print("送信終了フィードバック")
    
    def on_receive_start(self):
        """受信開始時のフィードバック"""
        self.receive_active = True
        self.led_controller.turn_on(0.3)  # 薄く点灯
        print("受信開始フィードバック")
    
    def on_receive_end(self):
        """受信終了時のフィードバック"""
        self.receive_active = False
        self.led_controller.turn_off()
        print("受信終了フィードバック")
    
    def on_signal_received(self, morse_char):
        """信号受信時のフィードバック"""
        if self.receive_active:
            self.led_controller.blink(0.2, 1, 0.6)
            self.buzzer_controller.play_morse_signal(morse_char)
            print(f"信号受信フィードバック: {morse_char}")
    
    def on_char_received(self, char):
        """文字受信時のフィードバック"""
        if self.receive_active:
            self.led_controller.blink(0.3, 1, 0.8)
            self.buzzer_controller.beep(0.05, 1200)
            print(f"文字受信フィードバック: {char}")
    
    def on_error(self):
        """エラー時のフィードバック"""
        self.led_controller.start_continuous_blink(0.1, 0.1, 1.0)
        self.buzzer_controller.beep(0.5, 300)  # 低い音
        time.sleep(0.5)
        self.led_controller.stop_continuous_blink()
        print("エラーフィードバック")
    
    def on_connection_established(self):
        """接続確立時のフィードバック"""
        self.led_controller.blink(0.2, 3, 1.0)
        self.buzzer_controller.play_tone(1000, 0.1)
        time.sleep(0.1)
        self.buzzer_controller.play_tone(1200, 0.1)
        time.sleep(0.1)
        self.buzzer_controller.play_tone(1500, 0.1)
        print("接続確立フィードバック")
    
    def set_led_enabled(self, enabled):
        """LEDの有効/無効を設定"""
        self.led_controller.set_enabled(enabled)
    
    def set_sound_enabled(self, enabled):
        """サウンドの有効/無効を設定"""
        self.buzzer_controller.set_enabled(enabled)
    
    def set_led_brightness(self, brightness):
        """LED輝度を設定"""
        self.led_controller.set_brightness(brightness)
    
    def set_buzzer_frequency(self, frequency):
        """ブザー周波数を設定"""
        self.buzzer_controller.set_frequency(frequency)
    
    def get_status(self):
        """フィードバックステータスを取得"""
        return {
            'led_enabled': self.led_controller.enabled,
            'sound_enabled': self.buzzer_controller.enabled,
            'led_brightness': self.led_controller.brightness,
            'buzzer_frequency': self.buzzer_controller.frequency,
            'transmit_active': self.transmit_active,
            'receive_active': self.receive_active
        }
    
    def cleanup(self):
        """フィードバック機能のクリーンアップ"""
        self.led_controller.cleanup()
        self.buzzer_controller.cleanup()
        print("フィードバック機能クリーンアップ完了")
