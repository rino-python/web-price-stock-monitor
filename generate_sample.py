from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.shop_config import BASE_URL, CURRENCY

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
HTML_NAME = "demo_page.html"
PREVIOUS_NAME = "先週取得.csv"

DEMO_HTML = """<!DOCTYPE html>
<html lang="ja">
<body>
<article class="item">
  <p class="sku">KM-101</p>
  <h3><a href="/items/kyusu">常滑焼の急須</a></h3>
  <p class="price">¥3,850</p>
  <p class="stock">在庫あり</p>
</article>
<article class="item">
  <p class="sku">KM-102</p>
  <h3><a href="/items/tenugui">注染手ぬぐい</a></h3>
  <p class="price">¥1,320</p>
  <p class="stock">在庫あり</p>
</article>
<article class="item">
  <p class="sku">KM-103</p>
  <h3><a href="/items/board">山桜のカッティングボード</a></h3>
  <p class="price">¥8,800</p>
  <p class="stock">売り切れ</p>
</article>
<article class="item">
  <p class="sku">KM-104</p>
  <h3><a href="/items/furoshiki">藍染の風呂敷</a></h3>
  <p class="price">¥2,750</p>
  <p class="stock">在庫あり</p>
</article>
<article class="item">
  <p class="sku">KM-105</p>
  <h3><a href="/items/furin">南部鉄器の風鈴</a></h3>
  <p class="price">¥6,600</p>
  <p class="stock">在庫あり</p>
</article>
<article class="item">
  <p class="sku">KM-106</p>
  <h3><a href="/items/letter">越前和紙の便箋</a></h3>
  <p class="price">¥980</p>
  <p class="stock">在庫あり</p>
</article>
<article class="item">
  <p class="sku">KM-107</p>
  <h3><a href="/items/hashioki">漆の箸置き</a></h3>
  <p class="price"></p>
  <p class="stock">在庫あり</p>
</article>
</body>
</html>
"""


def previous_dataframe() -> pd.DataFrame:
    """デモ用の先週。値下がり・売り切れ・再入荷・新着・掲載終了・値上がりが見えるようにずらしてある。"""
    return pd.DataFrame(
        [
            {
                "商品コード": "KM-101",
                "商品名": "常滑焼の急須",
                "価格": 4400,
                "通貨": CURRENCY,
                "在庫": "在庫あり",
                "URL": f"{BASE_URL.rstrip('/')}/kyusu",
            },
            {
                "商品コード": "KM-102",
                "商品名": "注染手ぬぐい",
                "価格": 1320,
                "通貨": CURRENCY,
                "在庫": "売り切れ",
                "URL": f"{BASE_URL.rstrip('/')}/tenugui",
            },
            {
                "商品コード": "KM-103",
                "商品名": "山桜のカッティングボード",
                "価格": 8800,
                "通貨": CURRENCY,
                "在庫": "在庫あり",
                "URL": f"{BASE_URL.rstrip('/')}/board",
            },
            {
                "商品コード": "KM-104",
                "商品名": "藍染の風呂敷",
                "価格": 2750,
                "通貨": CURRENCY,
                "在庫": "在庫あり",
                "URL": f"{BASE_URL.rstrip('/')}/furoshiki",
            },
            {
                "商品コード": "KM-106",
                "商品名": "越前和紙の便箋",
                "価格": 880,
                "通貨": CURRENCY,
                "在庫": "在庫あり",
                "URL": f"{BASE_URL.rstrip('/')}/letter",
            },
            {
                "商品コード": "KM-199",
                "商品名": "旧作の茶托",
                "価格": 1100,
                "通貨": CURRENCY,
                "在庫": "在庫あり",
                "URL": f"{BASE_URL.rstrip('/')}/chataku",
            },
        ]
    )


def main() -> None:
    SAMPLES_DIR.mkdir(exist_ok=True)
    html_path = SAMPLES_DIR / HTML_NAME
    html_path.write_text(DEMO_HTML, encoding="utf-8")
    csv_path = SAMPLES_DIR / PREVIOUS_NAME
    previous_dataframe().to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"wrote {html_path}")
    print(f"wrote {csv_path}")


if __name__ == "__main__":
    main()
