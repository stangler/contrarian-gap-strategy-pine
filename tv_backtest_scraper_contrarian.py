# tv_backtest_scraper.py
import asyncio
import csv
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# ========== 設定 ==========
URLS_FILE    = Path("urls.txt")
OUTPUT_DIR   = Path(".")
CHART_URL    = "https://jp.tradingview.com/chart/"
USER_DATA    = r"C:\Temp\tv-profile-pw"   # セッション保存先
WAIT_RECALC  = 10      # バックテスト再計算待機（秒）
WAIT_SEARCH  = 1.5    # 検索ダイアログ安定待機（秒）
EXCHANGE     = "TSE"

# ==========================

# Strategy Testerのテキストラベル（日本語DOM）
DEBUG_SCRAPE = True  # Trueにすると全テキストノードをdebug.txtに出力
DEBUG_LOG    = OUTPUT_DIR / "debug_switch_log.jsonl"  # 銘柄切替の診断ログ

def log_debug(record: dict):
    import json
    record["timestamp"] = datetime.now().isoformat(timespec="seconds")
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def load_symbols() -> list[str]:
    lines = URLS_FILE.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lines if l.strip() and not l.startswith("#")]

def save_csv(data: list, symbol: str, slot: str | None = None):
    safe = re.sub(r'[\\/:*?"<>|]', "_", symbol)
    slot_tag = f"_{slot.replace(':', '').replace('-', '_')}" if slot else ""
    fn = OUTPUT_DIR / f"{safe}{slot_tag}_{datetime.now():%Y%m%d}.csv"
    with open(fn, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([symbol, slot or ""])
        writer.writerow(["指標", "値"])
        writer.writerows(data)
    print(f"  ✓ 保存 → {fn}")

def slot_label_from_data(data: list) -> str | None:
    """データウィンドウの Slot開始(分)/Slot終了(分) からスロットラベルを自動生成。
    TradingView側のslotPresetドロップダウンの値そのものを読み取るので、
    python側の設定変更（手動同期）は不要になる。"""
    d = dict(data)
    try:
        start = int(float(d["Slot開始"]))
        end = int(float(d["Slot終了"]))
    except (KeyError, ValueError):
        return None
    def hhmm(m):
        h, mi = divmod(m, 60)
        return f"{h:02d}:{mi:02d}"
    return f"{hhmm(start)}-{hhmm(end)}"

async def switch_symbol(page, symbol: str) -> dict:
    has_focus_before = await page.evaluate("document.hasFocus()")
    title_before = await page.title()

    await page.keyboard.press("Space")
    await page.wait_for_timeout(int(WAIT_SEARCH * 1000))

    # Spaceで検索ダイアログが実際に開いたか（フォーカス問題の直接証拠）
    search_dialog_visible = await page.evaluate("""
        () => {
            const dialogs = document.querySelectorAll('[data-name*="symbol-search"], .tv-dialog, [role="dialog"]');
            return dialogs.length > 0;
        }
    """)

    query = f"{EXCHANGE}:{symbol}"
    await page.keyboard.type(query, delay=80)
    await page.wait_for_timeout(1200)
    await page.keyboard.press("ArrowDown")
    await page.wait_for_timeout(300)
    await page.keyboard.press("Enter")

    return {
        "symbol": symbol,
        "has_focus_before": has_focus_before,
        "title_before": title_before,
        "search_dialog_visible_after_space": search_dialog_visible,
    }

async def wait_for_chart_update(page, symbol: str, debug_info: dict) -> bool:
    ok = True
    try:
        # シンボル名だけでなく「%」(呼値ロード完了の目印)も含まれることを要求。
        # シンボル文字列だけだとタイトルが先行更新され、実際のチャート/ストラテジー
        # 再計算が終わってない状態を「成功」と誤判定するケースがあった
        # （例: title="3687" だけで価格・%が出てない＝前の銘柄のデータが残ったまま）
        await page.wait_for_function(
            f"document.title.includes('{symbol}') && document.title.includes('%')",
            timeout=20000
        )
    except Exception:
        ok = False

    title_after = await page.title()
    debug_info["ok"] = ok
    debug_info["title_after"] = title_after

    if not ok:
        shot_path = OUTPUT_DIR / f"debug_fail_{symbol}_{datetime.now():%H%M%S}.png"
        try:
            await page.screenshot(path=str(shot_path))
            debug_info["screenshot"] = str(shot_path)
        except Exception as e:
            debug_info["screenshot_error"] = str(e)
        print(f"  ⚠ タイトル変化なし（has_focus_before={debug_info['has_focus_before']}, "
              f"search_dialog={debug_info['search_dialog_visible_after_space']}） → この銘柄はスキップ")

    log_debug(debug_info)

    if ok:
        await page.wait_for_timeout(int(WAIT_RECALC * 1000))
    return ok

async def scrape_backtest(page) -> list:
    """
    DOMテキスト構造（確認済み）:
      主要統計: 総損益→+NNN, 最大ドローダウン→NNN, 勝ちトレード→NN.NN%(勝率), プロフィットファクター→N.NNN
      トレード分布: "トレード分布" → "33" → "トレード総数" → "勝ち" → "21トレード" → ...
    """
    texts = await page.evaluate("""
    () => {
        const out = [];
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let node;
        while (node = walker.nextNode()) {
            const t = node.textContent.trim();
            if (t) out.push(t);
        }
        return out;
    }
    """)

    if DEBUG_SCRAPE:
        with open("debug_texts.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(texts))
        print(f"  [DEBUG] テキストノード {len(texts)}件 → debug_texts.txt")

    import re as _re

    def is_num(s):
        c = s.replace(",", "").replace("\u202a", "").replace("\u202c", "").strip()
        return bool(_re.match(r'^[+\-\u2212]?\d+\.?\d*%?$', c))

    def is_int(s):
        """%なし整数のみ"""
        c = s.replace(",", "").replace("\u202a", "").replace("\u202c", "").strip()
        return bool(_re.match(r'^[+\-\u2212]?\d+$', c))

    def next_num(i, ahead=4):
        for j in range(i+1, min(i+1+ahead, len(texts))):
            if is_num(texts[j]):
                return texts[j]
        return None

    result = {}

    for i, t in enumerate(texts):
        # 主要統計ブロック
        if t == "総損益" and "総損益" not in result:
            v = next_num(i)
            if v: result["総損益"] = v

        elif t == "最大ドローダウン" and "最大ドローダウン" not in result:
            v = next_num(i)
            if v: result["最大ドローダウン"] = v

        elif t == "勝ちトレード" and "勝率" not in result:
            v = next_num(i)
            if v: result["勝率"] = v

        elif t == "プロフィットファクター" and "プロフィットファクター" not in result:
            v = next_num(i)
            if v: result["プロフィットファクター"] = v

        # トレード分布ブロック
        # "33" → "トレード総数" なので直前ノードを取る
        elif t == "トレード総数" and "トレード総数" not in result:
            if i > 0 and is_int(texts[i-1]):
                result["トレード総数"] = texts[i-1]

        elif t == "勝ち" and "勝ちトレード" not in result:
            if i+1 < len(texts):
                m = _re.match(r'^(\d+)トレード', texts[i+1])
                if m: result["勝ちトレード"] = m.group(1)

        elif t == "負け" and "負けトレード" not in result:
            if i+1 < len(texts):
                m = _re.match(r'^(\d+)トレード', texts[i+1])
                if m: result["負けトレード"] = m.group(1)

        # データウィンドウ: "GapUp 勝" → 次ノード "12.0"
        elif t == "GapUp 勝" and "GU_勝" not in result:
            if i+1 < len(texts): result["GU_勝"] = texts[i+1].replace(".0","")
        elif t == "GapUp 負" and "GU_負" not in result:
            if i+1 < len(texts): result["GU_負"] = texts[i+1].replace(".0","")
        elif t == "GapUp 勝率%" and "GU_勝率" not in result:
            if i+1 < len(texts): result["GU_勝率"] = texts[i+1].replace(".0","") + "%"

        elif t == "GapDown 勝" and "GD_勝" not in result:
            if i+1 < len(texts): result["GD_勝"] = texts[i+1].replace(".0","")
        elif t == "GapDown 負" and "GD_負" not in result:
            if i+1 < len(texts): result["GD_負"] = texts[i+1].replace(".0","")
        elif t == "GapDown 勝率%" and "GD_勝率" not in result:
            if i+1 < len(texts): result["GD_勝率"] = texts[i+1].replace(".0","") + "%"

        elif t == "Cont 勝" and "Cont_勝" not in result:
            if i+1 < len(texts): result["Cont_勝"] = texts[i+1].replace(".0","")
        elif t == "Cont 負" and "Cont_負" not in result:
            if i+1 < len(texts): result["Cont_負"] = texts[i+1].replace(".0","")
        elif t == "Cont 勝率%" and "Cont_勝率" not in result:
            if i+1 < len(texts): result["Cont_勝率"] = texts[i+1].replace(".0","") + "%"

        # データウィンドウ: スロット自動検出用
        elif t == "Slot開始(分)" and "Slot開始" not in result:
            if i+1 < len(texts): result["Slot開始"] = texts[i+1].replace(".0","")
        elif t == "Slot終了(分)" and "Slot終了" not in result:
            if i+1 < len(texts): result["Slot終了"] = texts[i+1].replace(".0","")

    if DEBUG_SCRAPE:
        print(f"  [DEBUG] 抽出結果: {result}")

    return list(result.items())

async def main():
    symbols = load_symbols()
    print(f"対象 {len(symbols)} 銘柄: {symbols}\n")

    async with async_playwright() as p:
        # セッション維持版: 同じプロファイルを再利用
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA,
            headless=False,
            args=["--start-maximized"],
            no_viewport=True,
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

        # 初回のみログインが必要。2回目以降はスキップされる
        await page.goto(CHART_URL)

        print("=" * 50)
        print("【初回のみ】ログイン + チャート設定が必要")
        print("2回目以降はそのままEnterでOK")
        print("  1. TradingViewにログイン")
        print("  2. ストラテジー適用済みチャートを開く")
        print("  3. ストラテジー設定でslotPresetを希望の時間帯に設定")
        print("     （python側の設定変更は不要。データウィンドウから自動検出する）")
        print("  4. Strategy Testerパネルを表示")
        print("=" * 50)
        input("準備完了 → Enter: ")

        success, failed = [], []

        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] {symbol}")
            try:
                debug_info = await switch_symbol(page, symbol)
                ok = await wait_for_chart_update(page, symbol, debug_info)
                if not ok:
                    print(f"  ↻ リトライ（Escape→再試行）")
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(500)
                    debug_info = await switch_symbol(page, symbol)
                    debug_info["retry"] = True
                    ok = await wait_for_chart_update(page, symbol, debug_info)
                if not ok:
                    failed.append(symbol)
                    continue

                data = await scrape_backtest(page)
                if data:
                    slot = slot_label_from_data(data)
                    if slot is None:
                        print(f"  ⚠ スロット自動検出失敗（pine未更新の可能性）→ タグなしで保存")
                    else:
                        print(f"  検出スロット: {slot}")
                    save_csv(data, symbol, slot)
                    success.append(symbol)
                else:
                    print(f"  ✗ データ取得失敗")
                    failed.append(symbol)

            except Exception as e:
                print(f"  ✗ エラー: {e}")
                failed.append(symbol)

        print(f"\n{'='*50}")
        print(f"完了: 成功 {len(success)} / 失敗 {len(failed)}")
        if failed:
            print(f"失敗銘柄: {failed}")

        input("ブラウザを閉じる → Enter: ")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())