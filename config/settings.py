"""
設定ファイル
シンプルGPIO信号通信システムの設定値
"""

# GPIOピン設定
GPIO_PINS = {
    'transmit': 17,      # 送信用GPIOピン
    'receive': 18,       # 受信用GPIOピン
    'switch': 23         # スイッチ用GPIOピン
}

# スイッチ設定
SWITCH_SETTINGS = {
    'debounce_time': 0.05,  # デバウンス時間 (秒)
}

# Webアプリケーション設定
WEB_CONFIG = {
    'host': '0.0.0.0',    # ホストIP
    'port': 5000,         # ポート番号
    'debug': False        # デバッグモード
}
