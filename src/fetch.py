"""HTML の取得。間隔・リトライ・robots.txt をここで守る。"""

from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from src.shop_config import PAGE_QUERY

USER_AGENT = "PriceStockWatch/1.0 (portfolio demo; polite crawl)"
REQUEST_TIMEOUT = 15.0
MAX_RETRIES = 3
PAUSE_SECONDS = 1.2


@dataclass
class FetchResult:
    url: str
    html: str | None
    status_code: int | None
    error: str | None
    robots_note: str
    robots_allowed: bool


def new_client() -> httpx.Client:
    return httpx.Client(
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )


def check_robots(url: str, client: httpx.Client | None = None) -> tuple[bool, str]:
    """robots.txt を見て、取得してよいかと説明文を返す。"""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    own = client is None
    client = client or new_client()
    parser = RobotFileParser()
    try:
        response = client.get(robots_url)
        if response.status_code == 404:
            return True, "robots.txt はありませんでした。公開ページのみ、間隔を空けて取得します。"
        if response.status_code >= 400:
            return False, f"robots.txt を確認できませんでした（HTTP {response.status_code}）。取得を止めます。"
        parser.parse(response.text.splitlines())
        allowed = parser.can_fetch(USER_AGENT, url)
        if allowed:
            return True, f"robots.txt を確認しました。取得してよいパスです（{robots_url}）。"
        return False, f"robots.txt がこのパスの取得を禁止しています（{robots_url}）。"
    except httpx.HTTPError as exc:
        return False, f"robots.txt に接続できませんでした。取得を止めます。（{exc}）"
    finally:
        if own:
            client.close()


def fetch_html(
    url: str,
    *,
    client: httpx.Client | None = None,
    pause: float = PAUSE_SECONDS,
) -> FetchResult:
    """1ページ取得する。失敗したらリトライする。"""
    own = client is None
    client = client or new_client()
    try:
        allowed, robots_note = check_robots(url, client=client)
        if not allowed:
            return FetchResult(
                url=url,
                html=None,
                status_code=None,
                error=robots_note,
                robots_note=robots_note,
                robots_allowed=False,
            )

        last_error = None
        last_status = None
        for attempt in range(1, MAX_RETRIES + 1):
            if attempt > 1:
                time.sleep(pause * attempt)
            try:
                response = client.get(url)
            except httpx.HTTPError as exc:
                last_error = str(exc)
                continue
            last_status = response.status_code
            if response.status_code >= 400:
                last_error = f"HTTP {response.status_code}"
                continue
            return FetchResult(
                url=str(response.url),
                html=response.text,
                status_code=response.status_code,
                error=None,
                robots_note=robots_note,
                robots_allowed=True,
            )
        return FetchResult(
            url=url,
            html=None,
            status_code=last_status,
            error=f"{MAX_RETRIES} 回試しても取得できませんでした（{last_error}）。",
            robots_note=robots_note,
            robots_allowed=True,
        )
    finally:
        if own:
            client.close()


def page_url(base: str, page: int) -> str:
    """納品時の一覧URL。2ページ目以降は PAGE_QUERY を付ける。"""
    if page <= 1 or not PAGE_QUERY:
        return base
    joiner = "&" if "?" in base else "?"
    return f"{base}{joiner}{PAGE_QUERY}={page}"
