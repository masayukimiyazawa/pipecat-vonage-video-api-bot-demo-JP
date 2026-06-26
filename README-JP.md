# Pipecat Voice Bot — Vonage Unified Video + LM Studio + pyopenjtalk

Vonage Video セッションに参加し、LM Studio（ローカル LLM/STT）と pyopenjtalk（ローカル日本語 TTS）で応答する音声対話ボットです。日本語と英語の両方に対応します。

## アーキテクチャ

```
ブラウザ (Vonage Video JS SDK)
    │ publish / subscribe
    ▼
Vonage Cloud
    │ Audio Connector (raw PCM16 WebSocket)
    ▼
Cloudflare Tunnel ───→ localhost:8005/ws
                            │
                       FastAPI + Pipecat
                       Pipeline: STT → LLM → TTS
                            │
                   LM Studio (:1234)    pyopenjtalk (local)
```

## 前提条件

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [LM Studio](https://lmstudio.ai/)（LLM + Whisper モデルをロード、`localhost:1234` で待受）
- [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)（トンネル、Homebrew: `brew install cloudflared`）
- Vonage アカウント（[Video API](https://developer.vonage.com/en/video) 有効化済み、Application ID + Private Key）

## セットアップ

### 1. 環境変数

```bash
cp .env.example .env
```

`.env` を編集:

| 変数 | 設定例 | 説明 |
|------|--------|------|
| `VONAGE_APPLICATION_ID` | `abc123` | Vonage Application ID |
| `VONAGE_PRIVATE_KEY` | `-----BEGIN...` | 秘密鍵（PEM文字列またはファイルパス） |
| `WS_URI` | `wss://xxxx.trycloudflare.com/ws` | 公開WebSocket URL（start.sh で自動設定） |
| `STT_LANGUAGE` | `ja` | Whisperの言語コード |

### 2. 依存関係インストール

```bash
uv sync
```

## 起動

### 3. LM Studio を起動

LLM モデルと Whisper モデルをロードし、`localhost:1234` で listening 状態にします。

### 4. ワンコマンド起動（推奨）

```bash
bash start.sh
```

以下の処理を自動で行います:

1. Cloudflare Tunnel（`cloudflared`）を起動し、公開 URL を取得
2. `.env` の `WS_URI` を自動更新
3. Python サーバーを再起動
4. ブラウザで開く URL を表示

### 5. ブラウザを開く

表示された URL にアクセスし、「接続」をクリックしてください。

## API エンドポイント

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/` | GET | フロントエンド（`static/index.html`） |
| `/health` | GET | ヘルスチェック |
| `/ws` | WebSocket | 音声ストリーム（Pipecat pipeline） |
| `/demo/connect` | POST | セッション作成 + Audio Connector起動 |

## ファイル構成

```
├── server.py            # FastAPIサーバ（HTTP + WebSocket）
├── bot.py               # Pipecat pipeline定義
├── tts_piper_plus.py    # pyopenjtalk TTS（日英対応）
├── start.sh             # ワンコマンド起動スクリプト
├── pyproject.toml       # 依存関係
├── .env                 # 認証情報（git管理外）
├── .env.example         # テンプレート
└── static/
    └── index.html       # フロントエンド（Vonage Video JS SDK）
```

## 注意事項

- Cloudflare Tunnel（`trycloudflare.com`）は稼働保証なしのクイックトンネルです。本番運用時は名前付きトンネル＋独自ドメインを推奨します。
