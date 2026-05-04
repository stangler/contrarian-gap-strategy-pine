# ズレ手法 — PineScript v6 ストラテジー

## 概要

5分足 逆張り戦略。  
連続陰線後、次足始値ロング。

- 条件: 直近N本 陰線（`close < open`）
- エントリー: 次足始値
- ナンピン: 最大2回
- 決済:
  - TP: 平均取得価格 + tick
  - SL: 初回価格基準 固定
  - 大引け: 強制クローズ（15:25）

---

## ATR動的モード

ボラ適応 TP/SL/ナンピン 自動調整。

- ATR期間: 14
- SL倍率: 2.0
- TP倍率: 0.8
- ナンピン1: 1.3
- ナンピン2: 1.5

指針:
- 低ボラ: OFF + 固定値
- 高ボラ: ON + ATR倍率調整

---

## 使い方（Pine）

1. TradingViewで5分足チャート開く  
2. スクリプト適用  
3. パラメータ調整  
4. Strategy Testerで結果確認  

---

## Backtest Scraper

TradingView Strategy Tester数値 → CSV保存。  
半自動（手動操作 必須）

---

## 前提

- Chrome remote debugging起動
- TradingViewログイン済
- チャート + Strategy適用済
- watchlistに銘柄追加済

---

## 実行手順（固定）

### STEP 1: Chrome起動（PowerShell A）

※ このウィンドウ閉じない

```powershell
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 2
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Temp\tv-profile" --profile-directory=Default
````

---

### STEP 2: TradingViewログイン

[https://jp.tradingview.com/](https://jp.tradingview.com/)

---

### STEP 3: スクリプト実行（PowerShell B）

```powershell
cd C:\Users\payor\Desktop\ContrarianGap_Strategy_PineScript\contrarian-gap-strategy-pine
uv run python tv_backtest_scraper.py
```

---

## 実行中操作（必須）

銘柄ごと:

1. Strategy Testerタブ開く
2. 必要なら戦略再適用
3. 数値更新確認
4. Enter押下

---

## 入力

`urls.txt`

```txt
BTCUSD
ETHUSD
# コメント可
```

---

## 出力

```csv
銘柄, BTCUSD
指標, 値
純利益, xxxx
勝率, xx%
ドローダウン, xxxx
```

ファイル:

```
SYMBOL_YYYYMMDD.csv
```

---

## 抽出ロジック

* 画面全テキスト走査（TreeWalker）
* キーワード一致抽出:

  * 損益 / 勝率 / トレード / ドローダウン / 純利益 / 期待
* 「ラベル + 次行」ペア取得

---

## 制約

* UI依存（TradingView変更で破損）
* 日本語UI前提
* 完全自動不可（手動更新必要）
* watchlist構造依存

---

## トラブル

データ取得失敗
→ Strategy Tester未更新 / タブ未選択

銘柄切替できない
→ watchlist未登録

接続失敗
→ Chrome未起動 / ポート不一致

---

## 改善余地

DOMセレクタ固定化（class依存回避）
