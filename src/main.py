"""
メインコントローラーモジュール
シンプルGPIO信号通信システムのメインエントリーポイント
"""

import sys
import signal
import argparse
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.web_app import SimpleWebApp
from config.settings import WEB_CONFIG


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
        description='シンプルGPIO信号通信システム',
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
        help='シミュレーションモードで起動'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='デバッグモードで起動'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=WEB_CONFIG['port'],
        help=f'ポート番号 (デフォルト: {WEB_CONFIG["port"]})'
    )

    return parser.parse_args()


def main():
    """メイン関数"""
    # シグナルハンドラ設定
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 引数解析
    args = parse_arguments()

    # Webアプリ初期化
    web_app = SimpleWebApp(simulation_mode=args.simulation)

    # サーバー起動
    try:
        web_app.run(
            host=WEB_CONFIG['host'],
            port=args.port,
            debug=args.debug
        )
    except Exception as e:
        print(f"エラー: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
