# Raspberry Pi Morse Code Communication System

双方向モールス信号通信システム for Raspberry Pi 4B ×2

## 概要
2台のRaspberry Pi間でモールス信号による双方向通信を実現するシステムです。Web UI、GPIO制御、LED/ブザーによるフィードバック機能を備えています。

## システム構成
- Raspberry Pi 4B ×2
- LED、ブザー、スイッチ
- Flask Web UI
- Pythonモジュール群

## プロジェクト構造
```
namenamedoc/
├── src/
│   ├── gpio_control.py      # GPIO制御モジュール
│   ├── morse_logic.py       # モールス符号変換ロジック
│   ├── sound_led.py         # LED・ブザー制御
│   ├── web_app.py           # Flask Webアプリケーション
│   └── main.py              # メインコントローラー
├── templates/
│   └── index.html           # Web UIテンプレート
├── static/
│   └── css/
│       └── style.css        # スタイルシート
├── tests/
│   ├── test_gpio_control.py
│   ├── test_morse_logic.py
│   └── test_integration.py
├── config/
│   └── settings.py          # 設定ファイル
├── requirements.txt         # Python依存パッケージ
└── README.md               # 本ファイル
```

## セットアップ
1. `pip install -r requirements.txt`
2. `python src/main.py`
3. Webブラウザで `http://localhost:5000` にアクセス

## テスト計画
詳細なテスト項目は別途テスト計画書を参照してください。
