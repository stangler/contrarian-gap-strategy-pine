"""
複数スロットの format_HHMM_HHMM.csv を1ファイルに統合する。
extract_data_contrarian.py 実行後、プロジェクトルートで実行すること。

入力: csv/format_0900_0930.csv, csv/format_0930_1000.csv, ... (csv/フォルダ内すべて)
出力: csv/format_all_slots.csv（1ファイルに全スロットを縦に結合、「スロット」列を追加）
"""
import csv
import re
from pathlib import Path

CSV_DIR = Path("csv")
PATTERN = re.compile(r"^format_(\d{4})_(\d{4})\.csv$")
OUTPUT_FILE = CSV_DIR / "format_all_slots.csv"

# 出力から除外する列名
EXCLUDE_COLS = {
    "GU_勝", "GU_負", "GU_勝率",
    "GD_勝", "GD_負", "GD_勝率",
    "Cont_勝", "Cont_負", "Cont_勝率",
}

def hhmm_to_clock(s: str) -> str:
    return f"{s[:2]}:{s[2:]}"

def main():
    files = sorted(p for p in CSV_DIR.glob("format_*.csv") if PATTERN.match(p.name))
    print(f"対象ファイル {len(files)}件: {[f.name for f in files]}\n")

    if not files:
        print("✗ format_HHMM_HHMM.csv 形式のファイルが見つからない（extract_data_contrarian.pyを先に実行）")
        return

    header_written = False
    total_rows = 0
    keep_indices = None  # 除外列を除いた残す列のインデックス一覧

    with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline="") as out_f:
        writer = csv.writer(out_f)

        for f in files:
            m = PATTERN.match(f.name)
            slot_label = f"{hhmm_to_clock(m.group(1))}-{hhmm_to_clock(m.group(2))}"

            with open(f, encoding="utf-8-sig") as in_f:
                reader = csv.reader(in_f)
                rows = list(reader)

            if not rows:
                print(f"  ⚠ {f.name}: 空ファイル、スキップ")
                continue

            if not header_written:
                keep_indices = [i for i, col in enumerate(rows[0]) if col not in EXCLUDE_COLS]
                header = [rows[0][i] for i in keep_indices]
                writer.writerow(header + ["スロット"])
                header_written = True

            count = 0
            for row in rows[1:]:
                filtered = [row[i] for i in keep_indices]
                writer.writerow(filtered + [slot_label])
                count += 1

            print(f"  ✓ {f.name} → スロット「{slot_label}」 {count}行")
            total_rows += count

    print(f"\n合計 {total_rows}行 → {OUTPUT_FILE} に保存")

if __name__ == "__main__":
    main()
