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
WAIT_RECALC  = 6      # バックテスト再計算待機（秒）
WAIT_SEARCH  = 1.5    # 検索ダイアログ安定待機（秒）
EXCHANGE     = "TSE"
# ==========================

KEYWORDS = [
    "純利益", "総損益", "最大ドローダウン",
    "トレード総数", "勝ちトレード", "負けトレード",
    "勝率", "プロフィットファクター", "期待値"
]

def load_symbols() -> list[str]:
    lines = URLS_FILE.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lines if l.strip() and not l.startswith("#")]

def save_csv(data: list, symbol: str):
    safe = re.sub(r'[\\/:*?"<>|]', "_", symbol)
    fn = OUTPUT_DIR / f"{safe}_{datetime.now():%Y%m%d}.csv"
    with open(fn, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([symbol])
        writer.writerow(["指標", "値"])
        writer.writerows(data)
    print(f"  ✓ 保存 → {fn}")

async def switch_symbol(page, symbol: str):
    await page.keyboard.press("Space")
    await page.wait_for_timeout(int(WAIT_SEARCH * 1000))
    query = f"{EXCHANGE}:{symbol}"
    await page.keyboard.type(query, delay=80)
    await page.wait_for_timeout(1200)
    await page.keyboard.press("ArrowDown")
    await page.wait_for_timeout(300)
    await page.keyboard.press("Enter")

async def wait_for_chart_update(page, symbol: str):
    try:
        await page.wait_for_function(
            f"document.title.includes('{symbol}')",
            timeout=12000
        )
    except Exception:
        print(f"  ⚠ タイトル変化タイムアウト → sleep継続")
    await page.wait_for_timeout(int(WAIT_RECALC * 1000))

async def scrape_backtest(page) -> list:
    return await page.evaluate("""
    (keywords) => {
        const texts = [];
        const walker = document.createTreeWalker(
            document.body, NodeFilter.SHOW_TEXT
        );
        let node;
        while (node = walker.nextNode()) {
            const t = node.textContent.trim();
            if (t) texts.push(t);
        }
        const result = [];
        const seen = new Set();
        for (let i = 0; i < texts.length - 1; i++) {
            const key = texts[i];
            if (!keywords.some(k => key.includes(k))) continue;
            const val = texts[i + 1];
            if (key.includes("勝ちトレード") && !seen.has("勝ちトレード_first")) {
                seen.add("勝ちトレード_first");
                continue; // 1回目（勝率%）スキップ
            }
            if (!seen.has(key)) {
                seen.add(key);
                result.push([key, val]);
            }
        }
        return result;
    }
    """, KEYWORDS)

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
        print("  3. Strategy Testerパネルを表示")
        print("=" * 50)
        input("準備完了 → Enter: ")

        success, failed = [], []

        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] {symbol}")
            try:
                await switch_symbol(page, symbol)
                await wait_for_chart_update(page, symbol)

                data = await scrape_backtest(page)
                if data:
                    save_csv(data, symbol)
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