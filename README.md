# ズレ手法 — PineScript v6 ストラテジー

## 概要
5分足逆張り戦略。連続陰線後、次足始値ロング。

- 条件: 直近N本陰線 (`close < open`)
- エントリー: 次足始値
- ナンピン: 最大2回
- 決済: TP/SL + 大引け強制クローズ(15:25)

**ATR動的モード**搭載（ボラ適応 TP/SL/ナンピン）。

---

## ワークフロー
1. TradingView Strategy Tester実行 → CSV出力（tv_backtest_scraper.py）
2. 全CSV → format.xlsx 自動転記（extract_data.py）

---

## ファイル構成

**メイン**
- `tv_backtest_scraper.py` — TradingView結果自動取得
- `extract_data.py` — CSV複数 → format.xlsx 一括更新

**確認用**
- `inspect_data.py` — CSV/Excel内容確認

---

## 実行手順

### 1. Chrome起動（PowerShell）
```powershell
Get-Process chrome | Stop-Process -Force
Start-Sleep 2
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Temp\tv-profile"
```

### 2. TradingView準備
- ログイン
- 対象銘柄チャート + 戦略適用
- Strategy Tester開く
- watchlist登録済

### 3. スクレイパー実行
```powershell
uv run python tv_backtest_scraper.py
```

### 4. Excel更新
```bash
python extract_data.py
```

**確認**
```bash
python inspect_data.py
```

---

## 入力
`urls.txt`（銘柄リスト）

## 出力
- `SYMBOL_YYYYMMDD.csv`（各銘柄）
- `format.xlsx`（全銘柄まとめ）

---

## 注意
- UI変更でスクレイパー破損可能性あり
- 日本語UI前提
- Strategy Tester手動更新必須（Enter押下）
```

**変更点**:  
ワークフロー明確化、extract_data連携追加、ファイル役割整理、手順簡略化。  

必要ならさらに修正指示。