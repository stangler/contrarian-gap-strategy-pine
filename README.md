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

選択中のスロット情報（`slotStartMin`/`slotEndMin`）は `display.data_window` でデータウィンドウにも出力（`Slot開始(分)` / `Slot終了(分)`）。スクレイパーがこれを読み取り、CSV/Excelのファイル名・スロット列を自動判定する。**python側で時間帯を手動指定する必要はない。**

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
urls.txt（銘柄リスト）
        ↓
[TradingView側でslotPresetを希望の時間帯に手動設定]
        ↓
tv_backtest_scraper_contrarian.py（Playwright自動操作 / Spaceキーで銘柄切替 / スロットはデータウィンドウから自動検出）
        ↓
SYMBOL_HHMM_HHMM_YYYYMMDD.csv（銘柄×スロットごと）
        ↓
extract_data_contrarian.py（CSVをスロット別に集約 → format_HHMM_HHMM.xlsx を生成）
        ↓
[スロットを切り替えて再度スクレイパー〜extract_data_contrarianを繰り返す]
        ↓
merge_format_xlsx.py（同フォルダの format_*.xlsx を1ファイルに統合 → format_all_slots.xlsx）
```

---

## ファイル構成

| ファイル | 役割 |
|---------|------|
| `contrarian-gap-strategy.pine` | PineScript v6 ストラテジー本体 |
| `tv_backtest_scraper_contrarian.py` | Playwrightでバックテスト結果を全自動スクレイプ（スロット自動検出対応） |
| `extract_data_contrarian.py` | 全CSVをスロット別に集約し `format_HHMM_HHMM.xlsx` へ転記 |
| `merge_format_xlsx.py` | 複数スロットの `format_*.xlsx` を1ファイル（`format_all_slots.xlsx`）に統合 |
| `urls.txt` | スクレイプ対象銘柄リスト（銘柄コードのみ、1行1銘柄） |
| `format.xlsx` | 出力テンプレート（スロットごとのコピーが `format_HHMM_HHMM.xlsx` として生成される） |

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

実行後、銘柄×スロットごとに `SYMBOL_HHMM_HHMM_YYYYMMDD.csv` が生成される。

### 2. スロット別Excel転記

```powershell
uv run python extract_data_contrarian.py
```

同フォルダ内のCSVをスロット別（`Slot開始`/`Slot終了`の値）に自動グルーピングし、各スロットごとに `format_HHMM_HHMM.xlsx` を生成。同一銘柄・同一スロットのCSVが複数（別日付）残っている場合は、更新日時（mtime）が最新のものを採用する。

> **注意**: `format.xlsx` を開いたまま実行するとPermissionErrorが発生するため、実行前に閉じること。

全スロット分のデータが必要な場合は、手順0〜2をスロットごとに繰り返す。

### 3. スロット統合

```powershell
uv run python merge_format_xlsx.py
```

同フォルダ内の `format_HHMM_HHMM.xlsx` をすべて読み込み、「スロット」列を付与して1シートに縦結合、`format_all_slots.xlsx` として出力。

---

## urls.txt フォーマット

```
# 銘柄コードのみ記載（TSE:不要）
186A
268A
3103
9984
```

- `#` 始まりの行はコメント（スキップ）
- 取引所プレフィックスは不要（スクレイパー側で `TSE:` を自動付与）

---

## 出力フォーマット（format_HHMM_HHMM.xlsx）

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
| J | GU_勝 |
| K | GU_負 |
| L | GU_勝率 |
| M | GD_勝 |
| N | GD_負 |
| O | GD_勝率 |
| P | Cont_勝 |
| Q | Cont_負 |
| R | Cont_勝率 |

`format_all_slots.xlsx` ではこれに加えて末尾に「スロット」列（例: `10:30-11:00`）が付与される。

> 銘柄列（B）はExcelテンプレートの仕様上、数字のみの銘柄コード（例: `3103`）は数値型、英字を含むコード（例: `186A`）は文字列型として格納される。pandas等で銘柄突合する場合は型を揃えること（バグではなく仕様）。

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
- ファイル名: `SYMBOL_HHMM_HHMM_YYYYMMDD.csv`（スロット自動検出失敗時はスロットタグなし）

---

## デバッグ

`tv_backtest_scraper_contrarian.py` の `DEBUG_SCRAPE = True` に設定すると `debug_texts.txt` に全DOMテキストノードを出力。GU/GD/Cont・Slot情報未取得時はラベル名の確認に使用する。

銘柄切替時の診断ログは `debug_switch_log.jsonl` に蓄積される（`has_focus_before`、`title_before`、`title_after`、`search_dialog_visible_after_space`、リトライ時は `retry: true` も記録）。タイトル変化が検知できない場合の原因調査に使う。

---

## 注意事項

- TradingViewのUI変更でスクレイパーが破損する可能性あり
- 日本語UI前提（指標名が日本語でCSVに出力される）
- 銘柄切替の成功判定は `document.title` に銘柄名と `%` の両方が含まれることを条件にしている（価格・%情報がロードされる前の早すぎる成功判定を防止するため）。タイムアウトは20秒
- 再計算待機時間はデフォルト10秒（`WAIT_RECALC`）。回線が遅い場合はさらに増やす
- スペースキーで検索バーが起動しない場合は `switch_symbol` 内の `"Space"` を `"/"` に変更
- 時間帯スロットの自動切替（Settings操作の自動化）は未実装。Strategy Testerパネルが設定ボタンを遮蔽する問題が解決していないため、現状はTradingView側で手動切替が前提
- `tv_backtest_scraper_contrarian.py` に未修正の `SyntaxWarning: "\s" is invalid escape sequence` が残っている（動作に影響なし）