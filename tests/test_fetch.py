from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx

from src.fetch import MAX_RETRIES, fetch_html, page_url


class FakeResponse:
    def __init__(self, status_code: int, text: str = "", url: str = "https://shop.example.jp/items/"):
        self.status_code = status_code
        self.text = text
        self.url = url


class FakeClient:
    def __init__(self, responses: list[object]):
        self._responses = list(responses)
        self.urls: list[str] = []

    def get(self, url: str) -> FakeResponse:
        self.urls.append(url)
        if not self._responses:
            raise httpx.ConnectError("no more responses")
        item = self._responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item  # type: ignore[return-value]


class FetchTests(unittest.TestCase):
    def test_robots_404_then_fetches_page(self) -> None:
        client = FakeClient(
            [
                FakeResponse(404, "", "https://shop.example.jp/robots.txt"),
                FakeResponse(200, "<html>ok</html>", "https://shop.example.jp/items/"),
            ]
        )
        result = fetch_html("https://shop.example.jp/items/", client=client, pause=0)
        self.assertTrue(result.robots_allowed)
        self.assertEqual(result.html, "<html>ok</html>")
        self.assertEqual(client.urls[0], "https://shop.example.jp/robots.txt")
        self.assertEqual(client.urls[1], "https://shop.example.jp/items/")

    def test_robots_403_stops(self) -> None:
        client = FakeClient([FakeResponse(403, "no", "https://shop.example.jp/robots.txt")])
        result = fetch_html("https://shop.example.jp/items/", client=client, pause=0)
        self.assertFalse(result.robots_allowed)
        self.assertIsNone(result.html)
        self.assertEqual(len(client.urls), 1)

    def test_robots_disallow_stops(self) -> None:
        robots = "User-agent: *\nDisallow: /\n"
        client = FakeClient([FakeResponse(200, robots, "https://shop.example.jp/robots.txt")])
        result = fetch_html("https://shop.example.jp/items/", client=client, pause=0)
        self.assertFalse(result.robots_allowed)
        self.assertIn("禁止", result.robots_note or "")
        self.assertEqual(len(client.urls), 1)

    def test_retries_then_gives_up(self) -> None:
        client = FakeClient(
            [
                FakeResponse(404, "", "https://shop.example.jp/robots.txt"),
                FakeResponse(500, "err"),
                FakeResponse(500, "err"),
                FakeResponse(500, "err"),
            ]
        )
        with patch("src.fetch.time.sleep"):
            result = fetch_html("https://shop.example.jp/items/", client=client, pause=0)
        self.assertTrue(result.robots_allowed)
        self.assertIsNone(result.html)
        self.assertIn(str(MAX_RETRIES), result.error or "")
        self.assertEqual(len(client.urls), 1 + MAX_RETRIES)

    def test_page_url_query(self) -> None:
        self.assertEqual(page_url("https://shop.example.jp/items/", 1), "https://shop.example.jp/items/")
        self.assertEqual(page_url("https://shop.example.jp/items/", 2), "https://shop.example.jp/items/?page=2")
        self.assertEqual(
            page_url("https://shop.example.jp/items/?cat=a", 2),
            "https://shop.example.jp/items/?cat=a&page=2",
        )


if __name__ == "__main__":
    unittest.main()
