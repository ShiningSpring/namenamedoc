"""
Flask Webアプリケーションモジュール
モールス信号通信システムのWeb UIを提供
"""

from flask import Flask, render_template, request, jsonify, session
import json
import threading
from datetime import datetime

from config.settings import WEB_CONFIG, COMMUNICATION
from .morse_logic import MorseCommunicationManager
from .gpio_control import GPIOController
from .sound_led import FeedbackController


class MorseWebApp:
    """モールス信号Webアプリケーション"""
    
    def __init__(self, simulation_mode=False):
        """
        初期化
        Args:
            simulation_mode (bool): シミュレーションモードフラグ
        """
        self.app = Flask(__name__)
        self.app.secret_key = 'morse_communication_secret_key'
        self.simulation_mode = simulation_mode
        
        # コンポーネント初期化
        self.gpio_controller = GPIOController(simulation_mode)
        self.feedback_controller = FeedbackController(simulation_mode)
        self.communication_manager = MorseCommunicationManager(self.gpio_controller)
        
        # コールバック設定
        self._setup_callbacks()
        
        # ルート設定
        self._setup_routes()
        
        # テンプレートメッセージ
        self.template_messages = [
            "HELLO",
            "SOS",
            "TEST",
            "OK",
            "HELP",
            "THANK YOU",
            "GOOD MORNING",
            "GOOD NIGHT"
        ]
        
        print(f"Webアプリケーション初期化完了 (シミュレーションモード: {self.simulation_mode})")
    
    def _setup_callbacks(self):
        """コールバック関数を設定"""
        # メッセージ受信コールバック
        self.communication_manager.add_message_received_callback(self._on_message_received)
        
        # 文字受信コールバック
        self.communication_manager.add_char_received_callback(self._on_char_received)
        
        # スイッチコールバック
        self.gpio_controller.add_switch_callback(self._on_switch_pressed)
    
    def _setup_routes(self):
        """Flaskルートを設定"""
        
        @self.app.route('/')
        def index():
            """メインページ"""
            return render_template('index.html', 
                                 template_messages=self.template_messages,
                                 status=self.get_system_status())
        
        @self.app.route('/api/send', methods=['POST'])
        def send_message():
            """メッセージ送信API"""
            try:
                data = request.get_json()
                message = data.get('message', '').strip()
                
                if not message:
                    return jsonify({'error': 'メッセージが空です'}), 400
                
                # メッセージ送信
                success = self.communication_manager.send_message(
                    message, 
                    callback=self._on_send_complete
                )
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': message,
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({'error': '送信中です。完了までお待ちください。'}), 429
                    
            except Exception as e:
                return jsonify({'error': f'送信エラー: {str(e)}'}), 500
        
        @self.app.route('/api/receive')
        def get_received_message():
            """受信メッセージ取得API"""
            try:
                message = self.communication_manager.get_received_message()
                return jsonify({
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({'error': f'受信エラー: {str(e)}'}), 500
        
        @self.app.route('/api/clear', methods=['POST'])
        def clear_messages():
            """メッセージクリアAPI"""
            try:
                self.communication_manager.clear_messages()
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': f'クリアエラー: {str(e)}'}), 500
        
        @self.app.route('/api/status')
        def get_status():
            """システムステータス取得API"""
            try:
                return jsonify(self.get_system_status())
            except Exception as e:
                return jsonify({'error': f'ステータス取得エラー: {str(e)}'}), 500
        
        @self.app.route('/api/settings', methods=['POST'])
        def update_settings():
            """設定更新API"""
            try:
                data = request.get_json()
                
                # LED設定
                if 'led_enabled' in data:
                    self.feedback_controller.set_led_enabled(data['led_enabled'])
                
                if 'led_brightness' in data:
                    self.feedback_controller.set_led_brightness(data['led_brightness'])
                
                # サウンド設定
                if 'sound_enabled' in data:
                    self.feedback_controller.set_sound_enabled(data['sound_enabled'])
                
                if 'buzzer_frequency' in data:
                    self.feedback_controller.set_buzzer_frequency(data['buzzer_frequency'])
                
                # 通信設定
                if 'remote_pi_ip' in data:
                    COMMUNICATION['remote_pi_ip'] = data['remote_pi_ip']
                
                return jsonify({
                    'success': True,
                    'settings': self.get_current_settings()
                })
                
            except Exception as e:
                return jsonify({'error': f'設定更新エラー: {str(e)}'}), 500
        
        @self.app.route('/api/communication/start', methods=['POST'])
        def start_communication():
            """通信開始API"""
            try:
                self.communication_manager.start_communication()
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': f'通信開始エラー: {str(e)}'}), 500
        
        @self.app.route('/api/communication/stop', methods=['POST'])
        def stop_communication():
            """通信停止API"""
            try:
                self.communication_manager.stop_communication()
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': f'通信停止エラー: {str(e)}'}), 500
        
        @self.app.route('/api/test/led', methods=['POST'])
        def test_led():
            """LEDテストAPI"""
            try:
                self.feedback_controller.led_controller.blink(0.5, 3, 1.0)
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': f'LEDテストエラー: {str(e)}'}), 500
        
        @self.app.route('/api/test/buzzer', methods=['POST'])
        def test_buzzer():
            """ブザーテストAPI"""
            try:
                self.feedback_controller.buzzer_controller.beep(0.3, 1000)
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': f'ブザーテストエラー: {str(e)}'}), 500
        
        @self.app.route('/api/test/switch', methods=['POST'])
        def test_switch():
            """スイッチテストAPI"""
            try:
                self.gpio_controller.simulate_switch_press(0.2)  # ドット
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': f'スイッチテストエラー: {str(e)}'}), 500
    
    def _on_message_received(self, message):
        """メッセージ受信時のコールバック"""
        print(f"Webアプリ - メッセージ受信: {message}")
        # WebSocketやSSEでリアルタイム通知を実装可能
    
    def _on_char_received(self, char):
        """文字受信時のコールバック"""
        print(f"Webアプリ - 文字受信: {char}")
        self.feedback_controller.on_char_received(char)
    
    def _on_switch_pressed(self, duration):
        """スイッチ押下時のコールバック"""
        print(f"Webアプリ - スイッチ押下: {duration:.2f}秒")
        
        # ドット/ダッシュ判定
        if duration < 0.4:
            morse_char = '.'
        else:
            morse_char = '-'
        
        # モールス信号を送信
        self.communication_manager.transmitter.transmit_text(morse_char)
        self.feedback_controller.on_signal_received(morse_char)
    
    def _on_send_complete(self):
        """送信完了時のコールバック"""
        print("Webアプリ - 送信完了")
        self.feedback_controller.on_transmit_end()
    
    def get_system_status(self):
        """システムステータスを取得"""
        feedback_status = self.feedback_controller.get_status()
        
        return {
            'communication_active': self.communication_manager.communication_active,
            'is_transmitting': self.communication_manager.transmitter.is_transmitting,
            'simulation_mode': self.simulation_mode,
            'feedback': feedback_status,
            'remote_pi_ip': COMMUNICATION['remote_pi_ip'],
            'timestamp': datetime.now().isoformat()
        }
    
    def get_current_settings(self):
        """現在の設定を取得"""
        feedback_status = self.feedback_controller.get_status()
        
        return {
            'led_enabled': feedback_status['led_enabled'],
            'led_brightness': feedback_status['led_brightness'],
            'sound_enabled': feedback_status['sound_enabled'],
            'buzzer_frequency': feedback_status['buzzer_frequency'],
            'remote_pi_ip': COMMUNICATION['remote_pi_ip']
        }
    
    def run(self):
        """Webアプリケーションを起動"""
        print(f"Webアプリケーション起動中... http://{WEB_CONFIG['host']}:{WEB_CONFIG['port']}")
        
        try:
            self.app.run(
                host=WEB_CONFIG['host'],
                port=WEB_CONFIG['port'],
                debug=WEB_CONFIG['debug'],
                threaded=True
            )
        except KeyboardInterrupt:
            print("Webアプリケーション停止")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """クリーンアップ"""
        try:
            self.communication_manager.stop_communication()
            self.feedback_controller.cleanup()
            self.gpio_controller.cleanup()
            print("Webアプリケーションクリーンアップ完了")
        except Exception as e:
            print(f"クリーンアップエラー: {e}")


# アプリケーションインスタンス作成関数
def create_app(simulation_mode=False):
    """
    Flaskアプリケーションを作成
    Args:
        simulation_mode (bool): シミュレーションモードフラグ
    Returns:
        Flask: Flaskアプリケーションインスタンス
    """
    web_app = MorseWebApp(simulation_mode)
    return web_app.app


if __name__ == '__main__':
    # 直接実行時の処理
    import sys
    
    simulation = '--simulation' in sys.argv
    web_app = MorseWebApp(simulation)
    web_app.run()
