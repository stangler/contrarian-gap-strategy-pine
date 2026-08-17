# ズレ手法 — PineScript v6 ストラテジー

## 概要

5分足逆張り戦略。N本連続陰線を確認後、次足始値でロングエントリー。含み損深化時にナンピン最大2回。TP/SLまたはスロット終了で決済。

バックテスト結果（総損益・勝率等）に加え、**GapUp / GapDown / 続き足（Cont）別の勝敗集計**に対応。取引時間帯は固定ではなく、**11個の時間帯プリセット（スロット）を切り替えてバックテスト**できる。

---

## ストラテジーロジック

### エントリー条件
- 直近 `bearCount` 本連続陰線（`close < open`）
- バックテスト期間内 (`inRange`)
- 選択中の時間帯スロット内（`timeOk`）
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
| スロット終了 | 選択中スロットの終了時刻以降にポジション保有 → 強制クローズ |

> **SLの実態**: ナンピン込みの合計距離。`entryPrice − (nap1 + nap2 + sl) × tickSize`で計算。

### 事前アラート
`alertPreSignal = true` 時、N-1本陰線確定で「次足がエントリー候補」アラートを発火。

### GU / GD / Cont 判定
エントリー発生日の寄り付き（9:00足）の `open` と前日終値を比較し、3パターンに分類。

| パターン | 条件 |
|---------|------|
| GapUp (GU) | `(open − 前日終値) / 前日終値 > gap_threshold_pct` |
| GapDown (GD) | `(open − 前日終値) / 前日終値 < −gap_threshold_pct` |
| 続き足 (Cont) | 上記以外（ギャップなし） |

勝敗はエントリーごとに `strategy.closedtrades.profit()` で判定し、パターン別に集計。

> GU/GD/Cont判定は寄り付き（9:00台）のギャップで決まる。選択中の時間帯スロットとは独立した分類で、どのスロットでバックテストしてもGU/GD/Cont集計対象は変わらない。

---

## 時間帯スロット設定

`slotPreset`（設定ダイアログ「時間帯設定」グループ）で以下11個から選択：

| スロット | 開始(分) | 終了(分) |
|---------|---------|---------|
| 9:00-9:30 | 540 | 570 |
| 9:30-10:00 | 570 | 600 |
| 10:00-10:30 | 600 | 630 |
| 10:30-11:00 | 630 | 660 |
| 11:00-11:30 | 660 | 690 |
| 12:30-13:00 | 750 | 780 |
| 13:00-13:30 | 780 | 810 |
| 13:30-14:00 | 810 | 840 |
| 14:00-14:30 | 840 | 870 |
| 14:30-15:00 | 870 | 900 |
| 15:00-15:25 | 900 | 925 |

選択中のスロット情報（`slotStartMin`/`slotEndMin`）は `display.data_window` でデータウィンドウにも出力（`Slot開始(分)` / `Slot終了(分)`）。スクレイパーがこれを読み取り、CSVのファイル名・スロット列を自動判定する。**python側で時間帯を手動指定する必要はない。**

> 現状、スロット切替はTradingView側で手動操作（11スロット×銘柄数を回す場合、スロットごとに全銘柄を回し切ってから次のスロットへ切り替える運用）。Settings操作の自動化はStrategy Testerパネルが設定ボタンを物理的に遮蔽する問題が未解決のため未実装。

---

## パラメータ

### 基本設定
| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `bearCount` | `2` | 連続陰線本数（min: 2, max: 6） |
| `alertPreSignal` | `true` | 事前アラート（N-1本陰線時） |

### ティック設定
| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `tpTicks` | `15` | TP（ティック） |
| `slTicks` | `15` | SL（ティック） |
| `nappin1Ticks` | `15` | ナンピン1距離（ティック） |
| `nappin2Ticks` | `15` | ナンピン2距離（ティック） |

### GU/GD/Cont設定
| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `gap_threshold_pct` | `0.1` | ギャップ判定閾値（%）。寄り付きの前日比がこの値を超えたらGU/GD |

### 時間帯設定
| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `slotPreset` | `"9:00-9:30"` | 時間帯スロット（11プリセットから選択） |

### バックテスト期間
コード内ハードコード。変更する場合は `.pine` ファイルの該当行を直接編集。

| 項目 | 値 |
|------|-----|
| 開始 | 2026-04-01 00:00 |
| 終了 | 2026-04-24 23:59 |

### ポジションサイジング
- `default_qty_type`: 資産の割合
- `default_qty_value`: 10%

---

## ワークフロー

```
format_template.csv（連番・銘柄コード・銘柄名の一覧、プロジェクトルート、手動管理）
        ↓
[TradingView側でslotPresetを希望の時間帯に手動設定]
        ↓
tv_backtest_scraper_contrarian.py（Playwright自動操作 / Spaceキーで銘柄切替 / スロットはデータウィンドウから自動検出）
        ↓
csv/SYMBOL_HHMM_HHMM_YYYYMMDD.csv（銘柄×スロットごと）
        ↓
extract_data_contrarian.py（csv/内のCSVをスロット別に集約 → csv/format_HHMM_HHMM.csv を生成。並び順は format_template.csv 準拠）
        ↓
[スロットを切り替えて再度スクレイパー〜extract_data_contrarianを繰り返す]
        ↓
merge_format_csv.py（csv/内の format_*.csv を1ファイルに統合 → csv/format_all_slots.csv）
```

---

## ファイル構成

| ファイル/フォルダ | 役割 |
|---------|------|
| `contrarian-gap-strategy.pine` | PineScript v6 ストラテジー本体 |
| `tv_backtest_scraper_contrarian.py` | Playwrightでバックテスト結果を全自動スクレイプ（スロット自動検出対応） |
| `extract_data_contrarian.py` | `csv/`内の全CSVをスロット別に集約し `csv/format_HHMM_HHMM.csv` へ転記 |
| `merge_format_csv.py` | `csv/`内の複数スロットの `format_*.csv` を1ファイル（`csv/format_all_slots.csv`）に統合 |
| `format_template.csv` | 銘柄マスタ兼出力テンプレート（連番・銘柄コード・銘柄名、プロジェクトルートで手動管理。スクレイプ対象銘柄と出力の並び順を兼ねる） |
| `csv/` | スクレイプ結果CSV・集計結果CSVの出力先（自動生成） |
| `png/` | 銘柄切替失敗時のデバッグスクリーンショット出力先（自動生成） |

---

## 実行手順

### 0. TradingView側の準備（スロット切替）

ストラテジー設定 → 「時間帯設定」グループ → `slotPreset` を対象スロットに設定。データウィンドウが開いていること（GU/GD/Cont、Slot開始/終了の取得に必要）。

### 1. スクレイパー実行

```powershell
cd C:\Users\payor\Desktop\ContrarianGap_Strategy_PineScript\contrarian-gap-strategy-pine
uv run python tv_backtest_scraper_contrarian.py
```

- Playwright管理のChromeが自動起動
- セッションは `C:\Temp\tv-profile-pw` に保存
- **初回のみ**: ログイン + ストラテジー適用済みチャートを開く + Strategy Testerパネルを表示 + **データウィンドウを開く** → Enter
- **2回目以降**: そのままEnterで自動実行開始
- 銘柄切替時にタイトル変化が検知できない場合（フォーカス問題等）、Escape→1回だけ自動リトライ。それでも失敗した銘柄はスキップされ、最後に失敗銘柄リストが表示される

> **注意**: GU/GD/Cont・スロット情報の取得にはデータウィンドウが開いている必要がある。

実行後、銘柄×スロットごとに `csv/SYMBOL_HHMM_HHMM_YYYYMMDD.csv` が生成される（`csv/`フォルダが存在しなければ自動作成）。

### 2. スロット別CSV転記

```powershell
uv run python extract_data_contrarian.py
```

`csv/`内のスクレイプ結果CSVをスロット別（`Slot開始`/`Slot終了`の値）に自動グルーピングし、各スロットごとに `csv/format_HHMM_HHMM.csv` を生成。銘柄の並び順は `format_template.csv`（プロジェクトルート）の「銘柄コード」列の並びに準拠する。同一銘柄・同一スロットのCSVが複数（別日付）残っている場合は、更新日時（mtime）が最新のものを採用する。データが見つからなかった銘柄は連番・銘柄コード・銘柄名のみで他列は空欄になる。

全スロット分のデータが必要な場合は、手順0〜2をスロットごとに繰り返す。

### 3. スロット統合

```powershell
uv run python merge_format_csv.py
```

`csv/`内の `format_HHMM_HHMM.csv` をすべて読み込み、「スロット」列を付与して1ファイルに縦結合、`csv/format_all_slots.csv` として出力。

---

## format_template.csv フォーマット

スクレイプ対象銘柄と、出力CSVの銘柄並び順を定義するマスタファイル（プロジェクトルートに配置、手動管理）。

```
連番,銘柄コード,銘柄名,総損益,最大ドローダウン,トレード総数,勝ちトレード,負けトレード,勝率,プロフィットファクター,GU_勝,GU_負,GU_勝率,GD_勝,GD_負,GD_勝率,Cont_勝,Cont_負,Cont_勝率
1,186A,アストロスケールホールディンク,,,,,,,,,,,,,,,,
2,268A,リガク・ホールディングス,,,,,,,,,,,,,,,,
```

- `連番`・`銘柄コード`・`銘柄名`のみ人手で管理し、それ以降の列は空欄でよい（`extract_data_contrarian.py`実行のたびに上書きされる）
- `tv_backtest_scraper_contrarian.py`はこのファイルの「銘柄コード」列を上から順に読み込んでスクレイプ対象とする（取引所プレフィックス`TSE:`は自動付与するので記載不要）
- 銘柄を追加/削除/並び替えたい場合は、このファイルを直接編集する（行を追加する場合、右側のデータ列は空欄のままでよい）

---

## 出力フォーマット（csv/format_HHMM_HHMM.csv）

| 列 | 内容 |
|----|------|
| A | 連番 |
| B | 銘柄コード |
| C | 銘柄名 |
| D | 総損益 |
| E | 最大ドローダウン |
| F | トレード総数 |
| G | 勝ちトレード数 |
| H | 負けトレード数 |
| I | 勝率 |
| J | プロフィットファクター |
| K | GU_勝 |
| L | GU_負 |
| M | GU_勝率 |
| N | GD_勝 |
| O | GD_負 |
| P | GD_勝率 |
| Q | Cont_勝 |
| R | Cont_負 |
| S | Cont_勝率 |

`csv/format_all_slots.csv` ではこれに加えて末尾に「スロット」列（例: `10:30-11:00`）が付与される。

> CSVはすべて文字列として保存される。エンコーディングはExcelでもそのまま開けるよう UTF-8 (BOM付き / utf-8-sig) で出力している。

---

## CSV フォーマット（tv_backtest_scraper_contrarian.py 出力）

```
186A,10:30-11:00
指標,値
GU_勝,13
GU_負,4
GU_勝率,76%
GD_勝,9
GD_負,4
GD_勝率,69%
Cont_勝,0
Cont_負,1
Cont_勝率,0%
総損益,"+10,467.00"
最大ドローダウン,"10,147.00"
Slot開始,630
Slot終了,660
...
```

- 1行目: 銘柄コード, スロットラベル（自動検出できた場合）
- 2行目: ヘッダー（固定）
- 3行目以降: 指標,値
- ファイル名: `csv/SYMBOL_HHMM_HHMM_YYYYMMDD.csv`（スロット自動検出失敗時はスロットタグなし）

---

## デバッグ

`tv_backtest_scraper_contrarian.py` の `DEBUG_SCRAPE = True` に設定すると `debug_texts.txt` に全DOMテキストノードを出力。GU/GD/Cont・Slot情報未取得時はラベル名の確認に使用する。

銘柄切替時の診断ログは `debug_switch_log.jsonl`（プロジェクトルート）に蓄積される（`has_focus_before`、`title_before`、`title_after`、`search_dialog_visible_after_space`、リトライ時は`attempt`番号も記録）。タイトル変化が検知できない場合の原因調査に使う。

全リトライ失敗時のスクリーンショットは `png/debug_fail_SYMBOL_attemptN_HHMMSS.png` に自動保存される（`DEBUG_SCREENSHOT`の設定に関わらず、失敗時は常に撮る）。

---

## 注意事項

- TradingViewのUI変更でスクレイパーが破損する可能性あり
- 日本語UI前提（指標名が日本語でCSVに出力される）
- 銘柄切替の成功判定は `document.title` に銘柄名と `%` の両方が含まれることを条件にしている（価格・%情報がロードされる前の早すぎる成功判定を防止するため）。タイムアウトは20秒
- 再計算待機時間はデフォルト10秒（`WAIT_RECALC`）。回線が遅い場合はさらに増やす
- スペースキーで検索バーが起動しない場合は `switch_symbol` 内の `"Space"` を `"/"` に変更
- 時間帯スロットの自動切替（Settings操作の自動化）は未実装。Strategy Testerパネルが設定ボタンを遮蔽する問題が解決していないため、現状はTradingView側で手動切替が前提
- `tv_backtest_scraper_contrarian.py` に未修正の `SyntaxWarning: "\s" is invalid escape sequence` が残っている（動作に影響なし）