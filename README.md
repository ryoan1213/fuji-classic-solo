# Fuji Classic — Solo Player Reservations

訪日外国人のお客様向けの「一人予約 空き枠」公開ページ＋自動更新ロボ一式です。
ValueGolf の富士クラシック一人予約を読み取り、**外国人向け価格・正確な人数・最新時刻**で表示し、
お客様に「すでに人が入っている枠」を選んでもらうことで、前日16:00時点の不成立（キャンセル）を防ぎます。

## 2つのURL

| | URL |
|---|---|
| 🌐 公開サイト（お客様に見せる） | https://ryoan1213.github.io/fuji-classic-solo/ |
| 💻 コード（このリポジトリ） | https://github.com/ryoan1213/fuji-classic-solo |

## 構成

| ファイル | 役割 |
|---|---|
| `index.html` | 公開ページ本体（デザイン・表示ロジック） |
| `fetch_slots.py` | ロボ。ValueGolfから取得して `data.js` を生成（Python標準ライブラリのみ） |
| `data.js` / `data.json` | ロボが生成する枠データ。**手で編集しない** |
| `assets/` | 富士クラシックのロゴ・コース写真 |
| `.github/workflows/update.yml` | 自動更新（GitHub Actions のタイマー：毎時＋締切前30分ごと） |
| `HANDOFF.md` | **詳しい引き継ぎ資料（仕組み・接続方法・データの読み方）** |

## 自動更新

GitHub Actions が定期的に `fetch_slots.py` を実行 → `data.js` を更新 → コミット → サイトに反映。
PCを起動しておく必要はなく、クラウドで24時間自動で動きます。

## 社長プラットフォームへの接続予定（HANDOFF.md 参照）

1. 問い合わせ受信時、AIの初回返信メールに**このサイトのURLを自動で差し込む**
2. お客様が「Request this group」を押した結果を、**社長のプラットフォームに直接送信** → AIが自動予約・確定返信

詳細・データの正データの所在（`plan.cfm` の「ご予約状況」）・価格の取り方は **[HANDOFF.md](./HANDOFF.md)** に記載。
