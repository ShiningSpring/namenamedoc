"""
Flask Webアプリケーションモジュール
シンプルGPIO信号通信システムのWeb UIを提供
"""

from flask import Flask, render_template, jsonify
import os

from config.settings import WEB_CONFIG
from .gpio_control import GPIOController


class SimpleWebApp:
    """シンプル信号通信Webアプリケーション"""

    def __init__(self, simulation_mode=False):
        """
        初期化
        Args:
            simulation_mode (bool): シミュレーションモードフラグ
        """
        # プロジェクトルートを取得
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.app = Flask(__name__,
                        template_folder=os.path.join(project_root, 'templates'),
                        static_folder=os.path.join(project_root, 'static'))
        self.app.secret_key = 'simple_signal_secret_key'
        self.simulation_mode = simulation_mode

        # GPIOコントローラー初期化
        self.gpio_controller = GPIOController(simulation_mode)

        # ルート設定
        self._setup_routes()

    def _setup_routes(self):
        """ルート設定"""

        @self.app.route('/')
        def index():
            """メインページ"""
            return render_template('index.html', status={'simulation_mode': self.simulation_mode})

        @self.app.route('/api/start', methods=['POST'])
        def start_communication():
            """通信開始"""
            try:
                self.gpio_controller.start()
                return jsonify({'success': True, 'message': '通信を開始しました'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/stop', methods=['POST'])
        def stop_communication():
            """通信停止"""
            try:
                self.gpio_controller.stop()
                return jsonify({'success': True, 'message': '通信を停止しました'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/status')
        def get_status():
            """ステータス取得"""
            return jsonify({
                'simulation_mode': self.simulation_mode,
                'running': self.gpio_controller.running,
                'switch_state': self.gpio_controller.get_switch_state()
            })

        @self.app.route('/api/signals')
        def get_signals():
            """受信信号取得"""
            signals = self.gpio_controller.get_received_signals()
            return jsonify({'signals': signals})

    def run(self, host=None, port=None, debug=None):
        """アプリケーション実行"""
        host = host or WEB_CONFIG['host']
        port = port or WEB_CONFIG['port']
        debug = debug if debug is not None else WEB_CONFIG['debug']

        print(f"Webサーバーを起動します: http://{host}:{port}")
        print(f"シミュレーションモード: {self.simulation_mode}")

        try:
            self.app.run(host=host, port=port, debug=debug)
        except KeyboardInterrupt:
            print("Webサーバーを停止します")
        finally:
            self.gpio_controller.cleanup()
