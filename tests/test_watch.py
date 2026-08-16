from __future__ import annotations

import unittest
from io import BytesIO

import pandas as pd

from generate_sample import DEMO_HTML, previous_dataframe
from src.diff import diff_listings
from src.excel_io import build_result_xlsx
from src.parse import parse_listing, parse_price
from src.run import InputFormatError, read_previous, run_watch
from src.shop_config import BASE_URL, MAX_ITEMS, MAX_PAGES


def _many_cards_html(count: int) -> str:
    parts = ["<html><body>"]
    for i in range(1, count + 1):
        parts.append(
            f"""
        <article class="item">
          <p class="sku">KM-{i:04d}</p>
          <h3><a href="/items/{i}">商品{i}</a></h3>
          <p class="price">¥1,000</p>
          <p class="stock">在庫あり</p>
        </article>
            """
        )
    parts.append("</body></html>")
    return "".join(parts)


class ParseTests(unittest.TestCase):
    def test_parse_demo_html(self) -> None:
        items, issues = parse_listing(DEMO_HTML, BASE_URL)
        self.assertEqual(len(items), 6)
        self.assertEqual(len(issues), 1)
        self.assertIn("価格", issues[0]["理由"])
        self.assertEqual(issues[0]["商品名"], "漆の箸置き")
        first = items[0]
        self.assertEqual(first["商品コード"], "KM-101")
        self.assertEqual(first["商品名"], "常滑焼の急須")
        self.assertEqual(first["価格"], 3850)
        self.assertEqual(first["在庫"], "在庫あり")
        self.assertEqual(first["通貨"], "JPY")
        self.assertNotIn("評価", first)

    def test_parse_yen_variants(self) -> None:
        self.assertEqual(parse_price("¥3,850"), 3850)
        self.assertEqual(parse_price("3850円"), 3850)
        self.assertEqual(parse_price("税込 ¥1,320"), 1320)

    def test_missing_cards(self) -> None:
        items, issues = parse_listing("<html><body>no products</body></html>", "https://example.com/")
        self.assertEqual(items, [])
        self.assertEqual(len(issues), 1)


class DiffTests(unittest.TestCase):
    def test_price_drop_new_and_gone(self) -> None:
        current_items, _ = parse_listing(DEMO_HTML, BASE_URL)
        current = pd.DataFrame(current_items)
        changes = diff_listings(current, previous_dataframe())
        labels = set(changes["変化"])
        self.assertIn("値下がり", labels)
        self.assertIn("値上がり", labels)
        self.assertIn("新着", labels)
        self.assertIn("掲載終了", labels)
        self.assertIn("売り切れ", labels)
        self.assertIn("再入荷", labels)
        drop = changes.loc[changes["変化"] == "値下がり", "商品名"].tolist()
        self.assertEqual(drop, ["常滑焼の急須"])
        gone = changes.loc[changes["変化"] == "掲載終了", "商品コード"].tolist()
        self.assertEqual(gone, ["KM-199"])
        fresh = changes.loc[changes["変化"] == "新着", "商品コード"].tolist()
        self.assertEqual(fresh, ["KM-105"])

    def test_code_match_ignores_name_change(self) -> None:
        current = pd.DataFrame(
            [
                {
                    "商品コード": "KM-104",
                    "商品名": "藍染風呂敷（大）",
                    "価格": 2750,
                    "通貨": "JPY",
                    "在庫": "在庫あり",
                    "URL": "",
                }
            ]
        )
        previous = pd.DataFrame(
            [
                {
                    "商品コード": "KM-104",
                    "商品名": "藍染の風呂敷",
                    "価格": 2750,
                    "通貨": "JPY",
                    "在庫": "在庫あり",
                    "URL": "",
                }
            ]
        )
        changes = diff_listings(current, previous)
        self.assertTrue(changes.empty)

    def test_duplicate_code_goes_to_issues(self) -> None:
        html = """
        <article class="item">
          <p class="sku">KM-101</p>
          <h3><a href="/items/a">常滑焼の急須</a></h3>
          <p class="price">¥3,850</p>
          <p class="stock">在庫あり</p>
        </article>
        <article class="item">
          <p class="sku">KM-101</p>
          <h3><a href="/items/b">常滑焼の急須（別掲載）</a></h3>
          <p class="price">¥3,850</p>
          <p class="stock">在庫あり</p>
        </article>
        """
        items, issues = parse_listing(html, BASE_URL)
        self.assertEqual(len(items), 1)
        self.assertEqual(len(issues), 1)
        self.assertIn("重複", issues[0]["理由"])

    def test_previous_yen_string_price(self) -> None:
        buf = BytesIO()
        pd.DataFrame(
            {
                "商品コード": ["KM-101"],
                "商品名": ["常滑焼の急須"],
                "価格": ["¥4,400"],
                "在庫": ["在庫あり"],
            }
        ).to_csv(buf, index=False)
        buf.seek(0)
        df = read_previous(buf, filename="先週.csv")
        self.assertEqual(df.iloc[0]["価格"], 4400)


class RunTests(unittest.TestCase):
    def test_offline_watch(self) -> None:
        result = run_watch(
            sample_html=DEMO_HTML,
            previous=previous_dataframe(),
            previous_name="先週取得.csv",
        )
        self.assertTrue(result.used_sample)
        self.assertEqual(result.item_count, 6)
        self.assertEqual(result.issue_count, 1)
        self.assertGreater(result.change_count, 0)
        xlsx = build_result_xlsx(result)
        self.assertGreater(len(xlsx), 1000)

    def test_previous_missing_column(self) -> None:
        buf = BytesIO()
        pd.DataFrame({"名前": ["A"]}).to_csv(buf, index=False)
        buf.seek(0)
        with self.assertRaises(InputFormatError):
            read_previous(buf, filename="bad.csv")


    def test_http_source_calls_fetch(self) -> None:
        from unittest.mock import MagicMock, patch

        from src.fetch import FetchResult

        fake = FetchResult(
            url=BASE_URL,
            html=DEMO_HTML,
            status_code=200,
            error=None,
            robots_note="ok",
            robots_allowed=True,
        )
        client = MagicMock()
        with patch("src.run.SOURCE", "http"), patch("src.run.new_client", return_value=client), patch(
            "src.run.fetch_html", return_value=fake
        ) as mocked:
            result = run_watch(previous=previous_dataframe())
        mocked.assert_called()
        client.close.assert_called_once()
        self.assertFalse(result.used_sample)
        self.assertEqual(result.item_count, 6)

    def test_http_pages_cannot_exceed_max(self) -> None:
        from unittest.mock import MagicMock, patch

        from src.fetch import FetchResult

        fake = FetchResult(
            url=BASE_URL,
            html=DEMO_HTML,
            status_code=200,
            error=None,
            robots_note="ok",
            robots_allowed=True,
        )
        client = MagicMock()
        with (
            patch("src.run.SOURCE", "http"),
            patch("src.run.new_client", return_value=client),
            patch("src.run.fetch_html", return_value=fake) as mocked,
            patch("src.run.time.sleep"),
        ):
            result = run_watch(pages=99, previous=previous_dataframe())
        self.assertEqual(mocked.call_count, MAX_PAGES)
        reasons = " ".join(result.issues["理由"].astype(str))
        self.assertIn(str(MAX_PAGES), reasons)
        self.assertIn("切り下げ", reasons)

    def test_item_cap_stops_and_logs(self) -> None:
        html = _many_cards_html(MAX_ITEMS + 3)
        items, issues = parse_listing(html, BASE_URL, max_items=MAX_ITEMS)
        self.assertEqual(len(items), MAX_ITEMS)
        self.assertTrue(any("上限" in str(row["理由"]) for row in issues))


if __name__ == "__main__":
    unittest.main()
