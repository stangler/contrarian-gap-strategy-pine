import csv
from pathlib import Path
from openpyxl import load_workbook

def extract_from_csv(csv_file):
    data = {}
    with open(csv_file, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        # 1行目: 銘柄名のみ
        first_row = next(reader, None)
        if first_row and len(first_row) >= 1:
            data['銘柄'] = first_row[0].strip()

        # 2行目: ヘッダー（指標,値）スキップ
        next(reader, None)

        # 3行目以降: 指標と値
        for row in reader:
            if len(row) >= 2:
                key = row[0].strip()
                value = row[1].strip()
                if key not in data:
                    data[key] = value

    return data

def update_excel(csv_data_list):
    wb = load_workbook("format.xlsx")
    ws = wb.active

    headers = [cell.value for cell in ws[1]]
    print(f"Excel headers: {headers}")

    for row_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
        symbol_cell = row[1]  # 列B
        if not symbol_cell.value:
            continue

        symbol = str(symbol_cell.value).strip()
        print(f"\nRow {row_idx}: Looking for symbol '{symbol}'")

        csv_data = next((d for d in csv_data_list if d.get('銘柄') == symbol), None)

        if csv_data:
            print(f"  Found: {list(csv_data.keys())}")
            row[2].value = csv_data.get('総損益')
            row[3].value = csv_data.get('最大ドローダウン')
            row[4].value = csv_data.get('トレード総数')
            row[5].value = csv_data.get('勝ちトレード')
            row[6].value = csv_data.get('負けトレード')
            row[7].value = csv_data.get('勝率')
            row[8].value = csv_data.get('プロフィットファクター')
            for col, key in zip([2,3,4,5,6,7,8],
                                 ['総損益','最大ドローダウン','トレード総数',
                                  '勝ちトレード','負けトレード','勝率','プロフィットファクター']):
                val = csv_data.get(key)
                row[col].value = val
                print(f"  Set {key}: {val}")
        else:
            print(f"  No CSV data found for symbol '{symbol}'")

    wb.save("format.xlsx")
    print("\nSaved to format.xlsx")

def main():
    csv_files = list(Path(".").glob("*.csv"))
    print(f"Found {len(csv_files)} CSV files")

    csv_data_list = []
    for csv_file in csv_files:
        data = extract_from_csv(csv_file)
        csv_data_list.append(data)
        print(f"\n{csv_file.name}: {list(data.keys())}")

    update_excel(csv_data_list)

if __name__ == "__main__":
    main()