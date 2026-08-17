import csv
from pathlib import Path

CSV_DIR = Path("csv")   # スクレイプ結果CSVの置き場・出力先
TEMPLATE_FILE = Path("format_template.csv")   # 銘柄マスタ（プロジェクトルート、手動管理）

def extract_from_csv(csv_file):
    data = {'_file': str(csv_file)}
    with open(csv_file, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        first_row = next(reader, None)
        if first_row and len(first_row) >= 1:
            data['銘柄'] = first_row[0].strip()
        next(reader, None)  # ヘッダー行スキップ
        for row in reader:
            if len(row) >= 2:
                key = row[0].strip()
                value = row[1].strip()
                if key not in data:
                    data[key] = value
    return data

def slot_key_from_data(data: dict) -> str:
    """CSV内のSlot開始(分)/Slot終了(分)からスロット識別子を生成。
    複数スロットのCSVが同じフォルダに混在していても、これでグループ分けできる。"""
    try:
        start = int(float(data.get('Slot開始', '')))
        end = int(float(data.get('Slot終了', '')))
    except (TypeError, ValueError):
        return "unknown"
    def hhmm(m):
        h, mi = divmod(m, 60)
        return f"{h:02d}{mi:02d}"
    return f"{hhmm(start)}_{hhmm(end)}"

def load_template_rows(template=TEMPLATE_FILE):
    """テンプレートCSVから (連番, 銘柄コード, 銘柄名) の並び順を読み込む。"""
    rows = []
    with open(template, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        for row in reader:
            code = (row.get("銘柄コード") or "").strip()
            if code:
                rows.append((
                    (row.get("連番") or "").strip(),
                    code,
                    (row.get("銘柄名") or "").strip(),
                ))
    return header, rows

def update_csv(csv_data_list, template=TEMPLATE_FILE, output_name="format.csv"):
    header, template_rows = load_template_rows(template)

    out_rows = []
    for seq, code, name in template_rows:
        csv_data = next((d for d in csv_data_list if d.get('銘柄') == code), None)

        if csv_data:
            if '勝率' not in csv_data:
                try:
                    win = float(csv_data.get('勝ちトレード', ''))
                    total = float(csv_data.get('トレード総数', ''))
                    csv_data['勝率'] = f"{win / total * 100:.1f}%" if total else ''
                except (TypeError, ValueError):
                    csv_data['勝率'] = ''
            row = [seq, code, name]
            for key in [
                '総損益', '最大ドローダウン', 'トレード総数',
                '勝ちトレード', '負けトレード', '勝率', 'プロフィットファクター',
                'GU_勝', 'GU_負', 'GU_勝率',
                'GD_勝', 'GD_負', 'GD_勝率',
                'Cont_勝', 'Cont_負', 'Cont_勝率',
            ]:
                row.append(csv_data.get(key, ''))
            out_rows.append(row)
            print(f"  ✓ {code} {name}")
        else:
            # データなし: 連番/銘柄コード/銘柄名のみ、他は空欄
            out_rows.append([seq, code, name] + [''] * 16)
            print(f"  ✗ {code} {name}: CSVなし")

    with open(output_name, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(out_rows)

    print(f"  Saved to {output_name}")

def main():
    CSV_DIR.mkdir(exist_ok=True)

    # csv/ フォルダ内から、出力済みファイル（format_*.csv）は集計対象から除外
    csv_files = sorted(
        (p for p in CSV_DIR.glob("*.csv") if not p.name.startswith("format_")),
        key=lambda p: p.stat().st_mtime,
    )
    print(f"Found {len(csv_files)} CSV files in {CSV_DIR}/")

    csv_data_list = [extract_from_csv(f) for f in csv_files]

    # スロット別にグループ分け（同フォルダに複数スロットのCSVが混在していてもOK）
    # 同一銘柄+スロットのCSVが複数（別日付など）ある場合は、mtimeが新しい方を採用
    # （csv_filesをmtime昇順にしてあるので、辞書への代入で後勝ち＝最新が残る）
    grouped: dict[str, dict] = {}
    for d in csv_data_list:
        slot = slot_key_from_data(d)
        symbol = d.get('銘柄')
        bucket = grouped.setdefault(slot, {})
        if symbol in bucket:
            print(f"  ⚠ 重複検出: {symbol}（スロット{slot}） "
                  f"{bucket[symbol]['_file']} → {d['_file']} を採用（新しい方）")
        bucket[symbol] = d

    print(f"検出スロット: {list(grouped.keys())}\n")

    for slot, symbol_map in grouped.items():
        items = list(symbol_map.values())
        if slot == "unknown":
            out_name = CSV_DIR / "format.csv"  # スロット情報なしCSV（旧形式）は従来通り
        else:
            out_name = CSV_DIR / f"format_{slot}.csv"
        print(f"--- スロット「{slot}」（{len(items)}件） → {out_name} ---")
        update_csv(items, template=TEMPLATE_FILE, output_name=out_name)
        print()

if __name__ == "__main__":
    main()
