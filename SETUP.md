# セットアップガイド

## 概要
このガイドではRaspberry Piモールス信号通信システムのセットアップ手順を説明します。

## 必要なもの
- Raspberry Pi 4B ×2
- microSDカード ×2
- LED ×2
- ブザー ×2
- タクトスイッチ ×2
- ジャンパワイヤー多数
- ブレッドボード ×2
- PC（Web UIアクセス用）
- ネットワーク環境

## 1. システム準備

### 1.1 Raspberry Piのセットアップ
1. Raspberry Pi OSをmicroSDカードにインストール
2. SSHを有効に設定
3. ネットワーク接続を確認
4. システムをアップデート：
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

### 1.2 Python環境のセットアップ
```bash
# Python 3とpipを確認
python3 --version
pip3 --version

# 必要なパッケージをインストール
sudo apt install python3-pip python3-venv -y
```

## 2. プロジェクトのインストール

### 2.1 プロジェクトのクローン
```bash
# Pi1で実行
cd ~
git clone <repository_url> namenamedoc
cd namenamedoc

# Pi2でも同様に実行
```

### 2.2 仮想環境の作成と有効化
```bash
cd ~/namenamedoc
python3 -m venv venv
source venv/bin/activate
```

### 2.3 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

## 3. ハードウェア配線

### 3.1 GPIOピン配線

#### Pi1の配線：
- GPIO 17: 送信信号出力 → Pi2のGPIO 18
- GPIO 18: 受信信号入力 ← Pi2のGPIO 17
- GPIO 23: タクトスイッチ（GNDに接続）
- GPIO 24: LED（抵抗220Ω経由でGNDに接続）
- GPIO 25: ブザー（GNDに接続）

#### Pi2の配線：
- GPIO 17: 送信信号出力 → Pi1のGPIO 18
- GPIO 18: 受信信号入力 ← Pi1のGPIO 17
- GPIO 23: タクトスイッチ（GNDに接続）
- GPIO 24: LED（抵抗220Ω経由でGNDに接続）
- GPIO 25: ブザー（GNDに接続）

### 3.2 配線図
```
Pi1                    Pi2
GPIO17 ────────→ GPIO18
GPIO18 ←─────── GPIO17
GPIO23 ──[SW]── GND
GPIO24 ──[LED]── GND
GPIO25 ──[BZ]── GND
```

## 4. 設定ファイルの更新

### 4.1 IPアドレス設定
`config/settings.py`で相手PiのIPアドレスを設定：

```python
# Pi1の場合
COMMUNICATION = {
    'remote_pi_ip': '192.168.1.101',  # Pi2のIPアドレス
    'remote_pi_port': 5000,
    'timeout': 5.0
}

# Pi2の場合
COMMUNICATION = {
    'remote_pi_ip': '192.168.1.100',  # Pi1のIPアドレス
    'remote_pi_port': 5000,
    'timeout': 5.0
}
```

### 4.2 GPIOピン設定（必要に応じて）
`config/settings.py`でGPIOピン番号を変更可能：

```python
GPIO_PINS = {
    'transmit': 17,
    'receive': 18,
    'led': 24,
    'buzzer': 25,
    'switch': 23
}
```

## 5. システムの起動

### 5.1 シミュレーションモードでのテスト
まずシミュレーションモードで動作確認：

```bash
cd ~/namenamedoc
source venv/bin/activate
python src/main.py --simulation
```

Webブラウザで `http://localhost:5000` にアクセスしてUIを確認。

### 5.2 実機での起動
シミュレーションで問題がなければ実機で起動：

```bash
cd ~/namenamedoc
source venv/bin/activate
python src/main.py
```

### 5.3 自動起動設定
systemdサービスとして登録：

```bash
sudo nano /etc/systemd/system/morse-comm.service
```

以下の内容を貼り付け：
```ini
[Unit]
Description=Morse Communication System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/namenamedoc
Environment=PATH=/home/pi/namenamedoc/venv/bin
ExecStart=/home/pi/namenamedoc/venv/bin/python src/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

サービスを有効化：
```bash
sudo systemctl daemon-reload
sudo systemctl enable morse-comm.service
sudo systemctl start morse-comm.service
```

## 6. テスト実行

### 6.1 単体テスト
```bash
cd ~/namenamedoc
python run_tests.py --test test_gpio_control
python run_tests.py --test test_morse_logic
```

### 6.2 統合テスト
```bash
cd ~/namenamedoc
python run_tests.py --test test_integration
```

### 6.3 全テスト
```bash
cd ~/namenamedoc
python run_tests.py
```

## 7. トラブルシューティング

### 7.1 よくある問題

#### GPIOアクセス権限エラー
```bash
sudo usermod -a -G gpio pi
# 再起動が必要
sudo reboot
```

#### ポートが既に使用されている
```bash
sudo lsof -i :5000
# プロセスを特定して終了
sudo kill -9 <PID>
```

#### ネットワーク接続問題
```bash
# IPアドレスを確認
hostname -I
# 相手Piにpingテスト
ping 192.168.1.XXX
```

#### 依存パッケージ不足
```bash
pip install -r requirements.txt --force-reinstall
```

### 7.2 ログ確認
```bash
# アプリケーションログ
tail -f morse_communication.log

# systemdサービスログ
sudo journalctl -u morse-comm.service -f
```

### 7.3 デバッグモード
デバッグモードで起動：
```bash
python src/main.py --debug
```

## 8. 使い方

### 8.1 Web UIの操作
1. Webブラウザで `http://<PiのIPアドレス>:5000` にアクセス
2. 「通信開始」ボタンをクリック
3. メッセージを入力して「送信」ボタンをクリック
4. スイッチを操作してモールス信号を送信

### 8.2 スイッチ操作
- 短押し（0.4秒未満）：ドット（・）
- 長押し（0.4秒以上）：ダッシュ（－）

### 8.3 設定変更
Web UIから以下の設定を変更可能：
- LEDフィードバックのON/OFF
- LED輝度
- サウンドフィードバックのON/OFF
- ブザー周波数
- 相手PiのIPアドレス

## 9. メンテナンス

### 9.1 定期的なメンテナンス
- システムアップデート：`sudo apt update && sudo apt upgrade`
- パッケージ更新：`pip install -r requirements.txt --upgrade`
- ログローテーション設定

### 9.2 バックアップ
```bash
# 設定ファイルのバックアップ
cp config/settings.py config/settings.py.backup

# プロジェクト全体のバックアップ
tar -czf morse_comm_backup.tar.gz ~/namenamedoc
```

## 10. 発展的な設定

### 10.1 カスタムモールス符号
`config/settings.py`の`MORSE_CODE_DICT`を編集してカスタム符号を追加。

### 10.2 タイミング調整
`config/settings.py`の`MORSE_TIMING`で信号タイミングを調整。

### 10.3 外部API連携
Web APIを拡張して外部システムとの連携を実現。

---

## サポート
問題が発生した場合は、ログファイルとエラーメッセージを添えてサポートに連絡してください。
