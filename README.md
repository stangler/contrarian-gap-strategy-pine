# ズレ手法 — PineScript v6 ストラテジー

## 概要

5分足チャートで陰線が4本連続した後、次の足の始値でロングエントリーする逆張り手法。

## エントリー条件

- 時間足: 5分足
- 方向: ロング（買い）
- 条件: 直近4本がすべて陰線（`close < open`）
- エントリー: 条件成立バー確定後、次の足の始値で即執行

## 決済条件

| 項目 | 設定 |
|------|------|
| TP | エントリー価格 + ATR × 2.0 |
| SL | エントリー価格 − ATR × 1.0 |
| RR | 2:1 |

## インプット設定

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| ATR期間 | 14 | ATR計算の期間 |
| TP (ATR倍数) | 2.0 | 利確幅 |
| SL (ATR倍数) | 1.0 | 損切幅 |
| 開始日 | 2026-04-01 | バックテスト開始日 |
| 終了日 | 2026-04-24 | バックテスト終了日 |

## 可視化

- 🟢 緑の三角: シグナル発生箇所（期間内のみ）
- グレー背景: バックテスト対象外期間

## ソースコード

```pine
//@version=6
strategy("ズレ手法", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=10)

// 入力
atrLen  = input.int(14, "ATR期間", minval=1)
tpMult  = input.float(2.0, "TP (ATR倍数)", minval=0.1, step=0.1)
slMult  = input.float(1.0, "SL (ATR倍数)", minval=0.1, step=0.1)

// バックテスト期間
startDate = input.time(timestamp("2026-04-01 00:00"), "開始日")
endDate   = input.time(timestamp("2026-04-24 23:59"), "終了日")
inRange   = time >= startDate and time <= endDate

// ATR
atr = ta.atr(atrLen)

// 陰線4本連続判定
bearish(i) => close[i] < open[i]
signal = bearish(1) and bearish(2) and bearish(3) and bearish(4)

// エントリー（期間内のみ）
if signal and strategy.position_size == 0 and inRange
    tp = close + atr * tpMult
    sl = close - atr * slMult
    strategy.entry("Long", strategy.long)
    strategy.exit("Exit", "Long", limit=tp, stop=sl)

// 可視化
plotshape(signal and inRange, "シグナル", shape.triangleup, location.belowbar, color.green, size=size.small)

// 期間外グレーアウト
bgcolor(not inRange ? color.new(color.gray, 90) : na)
```

## 使い方

1. TradingView でチャートを5分足に設定
2. Pine エディタに上記コードを貼り付け
3. 「追加」ボタンでチャートに適用
4. 設定パネルから期間・ATR・TP/SL を調整
5. ストラテジーテスターでバックテスト結果を確認

## 今後の改善候補

- 陰線本数のインプット化（現在は4本固定）
- 複数ポジション対応
- フィルター追加（RSI・出来高など）
- TP/SL を直近高安値ベースに変更