# ズレ手法 — PineScript v6 ストラテジー

## 概要

5分足逆張り戦略。N本連続陰線を確認後、次足始値でロングエントリー。含み損深化時にナンピン最大2回。TP/SLまたは大引けで決済。

---

## ストラテジーロジック

### エントリー条件
- 直近 `bearCount` 本連続陰線（`close < open`）
- バックテスト期間内 (`inRange`)
- 取引時間内 (`timeOk`)
- 大引け時刻でない（15:25以降は不可）
- ポジションなし

### ナンピン
| 回数 | 条件 |
|------|------|
| 1回目 | 初回エントリー価格 − ナンピン1ティック 以下に下落 |
| 2回目 | 初回エントリー価格 − (ナンピン1 + ナンピン2)ティック 以下に下落 |

### 決済
| 種別 | 条件 |
|------|------|
| TP | 平均取得価格 + TPティック 以上に上昇 |
| SL | 初回エントリー価格 − (ナンピン1 + ナンピン2 + SL)ティック 以下に下落 |
| 大引け | 15:25以降にポジション保有 → 強制クローズ |

> **SLの実態**: ナンピン込みの合計距離。`entryPrice − (nap1 + nap2 + sl) × tickSize`で計算。

### 事前アラート
`alertPreSignal = true` 時、N-1本陰線確定で「次足がエントリー候補」アラートを発火。

---

## パラメータ

### 基本設定
| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `bearCount` | `2` | 連続陰線本数（min: 2, max: 6） |
| `alertPreSignal` | `true` | 事前アラート（N-1本陰線時） |

### ATR動的モード
| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `useATR` | `true` | ATR動的モード使用（false = 固定ティック） |
| `atrLen` | `14` | ATR計算期間 |
| `atrMultTP` | `0.8` | TP = ATR × この倍率 |
| `atrMultSL` | `2.0` | SL = ATR × この倍率 |
| `atrMultNap1` | `1.3` | ナンピン1距離 = ATR × この倍率 |
| `atrMultNap2` | `1.5` | ナンピン2距離 = ATR × この倍率 |

### 固定ティックモード（`useATR = false` 時）
| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `tpTicks` | `15` | TP（ティック） |
| `slTicks` | `15` | SL（ティック） |
| `nappin1Ticks` | `15` | ナンピン1距離（ティック） |
| `nappin2Ticks` | `15` | ナンピン2距離（ティック） |

### バックテスト期間
| パラメータ | デフォルト |
|-----------|-----------|
| `startDate` | 2026-04-01 00:00 |
| `endDate` | 2026-04-24 23:59 |

### 取引時間
| パラメータ | デフォルト |
|-----------|-----------|
| 開始 | 09:00 |
| 終了 | 15:30 |
| 大引け強制決済 | 15:25 |

### ポジションサイジング
- `default_qty_type`: 資産の割合
- `default_qty_value`: 10%

---

## ワークフロー

```
TradingView Strategy Tester
        ↓
tv_backtest_scraper.py（Chrome経由で自動取得）
        ↓
SYMBOL_YYYYMMDD.csv（銘柄ごと）
        ↓
extract_data.py（全CSV → format.xlsx 一括転記）
```

---

## ファイル構成

| ファイル | 役割 |
|---------|------|
| `contrarian-gap-strategy.pine` | PineScript v6 ストラテジー本体 |
| `tv_backtest_scraper.py` | TradingViewバックテスト結果を自動スクレイプ |
| `extract_data.py` | 全CSVをformat.xlsxへ一括転記 |
| `inspect_data.py` | CSV・Excel内容の確認用 |
| `urls.txt` | スクレイプ対象銘柄URLリスト |
| `format.xlsx` | バックテスト結果まとめ（出力先） |

---

## 実行手順

### 1. Chrome起動（デバッグポート付き）

```powershell
Get-Process chrome | Stop-Process -Force
Start-Sleep 2
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Temp\tv-profile"
```

### 2. TradingView準備

1. TradingViewにログイン
2. 対象銘柄チャートを開き、ストラテジー適用
3. Strategy Testerを開く
4. `urls.txt` に対象銘柄URL登録済みであることを確認

### 3. スクレイパー実行

```powershell
uv run python tv_backtest_scraper.py
```

実行後、銘柄ごとに `SYMBOL_YYYYMMDD.csv` が生成される。

### 4. Excel一括転記

```powershell
uv run python extract_data.py
```

`format.xlsx` の各銘柄行に以下が書き込まれる:
- 総損益 / 最大ドローダウン / トレード総数
- 勝ちトレード数 / 負けトレード数 / 勝率
- プロフィットファクター

### 5. 確認（任意）

```powershell
uv run python inspect_data.py
```

---

## 出力フォーマット（format.xlsx）

| 列 | 内容 |
|----|------|
| A | 連番 |
| B | 銘柄 |
| C | 総損益 |
| D | 最大ドローダウン |
| E | トレード総数 |
| F | 勝ちトレード数 |
| G | 負けトレード数 |
| H | 勝率 |
| I | プロフィットファクター |

---

## 注意事項

- TradingViewのUI変更でスクレイパーが破損する可能性あり
- 日本語UI前提（指標名が日本語でCSVに出力される）
- Strategy Testerの結果反映にEnter押下が必要な場合あり
- `format.xlsx` を開いたまま `extract_data.py` を実行するとPermissionErrorが発生するため、実行前に閉じること