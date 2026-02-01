"""
メインコントローラーモジュール
Raspberry Piモールス信号通信システムのメインエントリーポイント
"""

import sys
import signal
import argparse
import logging
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.web_app import MorseWebApp
from config.settings import WEB_CONFIG


def setup_logging(log_level=logging.INFO):
    """
    ログ設定を初期化
    Args:
        log_level: ログレベル
    """
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('morse_communication.log', encoding='utf-8')
        ]
    )
    
    # Flaskのログレベルを設定
    logging.getLogger('werkzeug').setLevel(logging.WARNING)


def signal_handler(signum, frame):
    """シグナルハンドラ"""
    print(f"\nシグナル {signum} を受信しました。プログラムを終了します...")
    sys.exit(0)


def parse_arguments():
    """
    コマンドライン引数を解析
    Returns:
        argparse.Namespace: 解析された引数
    """
    parser = argparse.ArgumentParser(
        description='Raspberry Piモールス信号通信システム',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python src/main.py                    # 通常モードで起動
  python src/main.py --simulation       # シミュレーションモードで起動
  python src/main.py --debug            # デバッグモードで起動
  python src/main.py --port 8080        # ポート8080で起動
        """
    )
    
    parser.add_argument(
        '--simulation',
        action='store_true',
        help='シミュレーションモードで実行（GPIOなし）'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='デバッグモードで実行'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default=WEB_CONFIG['host'],
        help=f'Webサーバーのホストアドレス (デフォルト: {WEB_CONFIG["host"]})'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=WEB_CONFIG['port'],
        help=f'Webサーバーのポート番号 (デフォルト: {WEB_CONFIG["port"]})'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='ログレベル (デフォルト: INFO)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser.parse_args()


def validate_environment(simulation_mode=False):
    """
    実行環境を検証
    Args:
        simulation_mode (bool): シミュレーションモードフラグ
    Returns:
        bool: 環境が有効かどうか
    """
    print("環境検証中...")
    
    # Pythonバージョンチェック
    if sys.version_info < (3, 7):
        print("エラー: Python 3.7以上が必要です")
        return False
    
    # 必要なモジュールのチェック
    required_modules = [
        'flask',
        'threading',
        'time',
        'json',
        'pathlib'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"エラー: 必要なモジュールが不足しています: {', '.join(missing_modules)}")
        print("pip install -r requirements.txt を実行してください")
        return False
    
    # GPIOモジュールのチェック（シミュレーションモード以外）
    if not simulation_mode:
        try:
            import RPi.GPIO
            print("RPi.GPIOモジュールが利用可能です")
        except ImportError:
            print("警告: RPi.GPIOモジュールが見つかりません")
            print("シミュレーションモードで実行します")
            return True  # シミュレーションモードで続行
    
    # 設定ファイルのチェック
    config_files = [
        'config/settings.py',
        'src/gpio_control.py',
        'src/morse_logic.py',
        'src/sound_led.py',
        'src/web_app.py'
    ]
    
    missing_files = []
    for file_path in config_files:
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"エラー: 必要なファイルが見つかりません: {', '.join(missing_files)}")
        return False
    
    # テンプレート/静的ファイルのチェック
    template_file = project_root / 'templates/index.html'
    css_file = project_root / 'static/css/style.css'
    
    if not template_file.exists():
        print("警告: テンプレートファイルが見つかりません: templates/index.html")
    
    if not css_file.exists():
        print("警告: CSSファイルが見つかりません: static/css/style.css")
    
    print("環境検証完了")
    return True


def print_startup_info(args):
    """
    起動情報を表示
    Args:
        args (argparse.Namespace): コマンドライン引数
    """
    print("=" * 60)
    print("Raspberry Pi モールス信号通信システム")
    print("=" * 60)
    print(f"バージョン: 1.0.0")
    print(f"シミュレーションモード: {'ON' if args.simulation else 'OFF'}")
    print(f"デバッグモード: {'ON' if args.debug else 'OFF'}")
    print(f"Webサーバー: http://{args.host}:{args.port}")
    print(f"ログレベル: {args.log_level}")
    print("=" * 60)
    print("Ctrl+Cで終了します")
    print()


def main():
    """メイン関数"""
    try:
        # コマンドライン引数の解析
        args = parse_arguments()
        
        # ログ設定
        log_level = getattr(logging, args.log_level)
        setup_logging(log_level)
        
        # 起動情報の表示
        print_startup_info(args)
        
        # 環境検証
        if not validate_environment(args.simulation):
            sys.exit(1)
        
        # シグナルハンドラの設定
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Webアプリケーションの作成と設定
        web_app = MorseWebApp(simulation_mode=args.simulation)
        
        # 設定の更新
        WEB_CONFIG['host'] = args.host
        WEB_CONFIG['port'] = args.port
        WEB_CONFIG['debug'] = args.debug
        
        print("Webアプリケーションを起動します...")
        
        # アプリケーションの起動
        web_app.run()
        
    except KeyboardInterrupt:
        print("\nプログラムが中断されました")
    except Exception as e:
        print(f"致命的なエラーが発生しました: {e}")
        logging.exception("致命的なエラー")
        sys.exit(1)
    finally:
        print("プログラムを終了します")


if __name__ == '__main__':
    main()
