"""取得〜差分までを一回分まとめる。"""

from __future__ import annotations

import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pandas as pd

from src.diff import CHANGE_COLUMNS, diff_listings
from src.fetch import FetchResult, fetch_html, new_client, page_url, PAUSE_SECONDS
from src.parse import parse_listing, parse_price
from src.shop_config import BASE_URL, MAX_ITEMS, MAX_PAGES, SOURCE

LIST_COLUMNS = ["商品コード", "商品名", "価格", "通貨", "在庫", "URL"]
ISSUE_COLUMNS = ["場所", "商品名", "理由"]


class InputFormatError(ValueError):
    """前回ファイルなど、ユーザーが直せる入力エラー。"""


@dataclass
class WatchResult:
    listing: pd.DataFrame
    changes: pd.DataFrame
    issues: pd.DataFrame
    source_url: str
    used_sample: bool
    robots_note: str
    robots_allowed: bool
    page_count: int
    item_count: int
    change_count: int
    issue_count: int
    previous_name: str


def _empty_listing() -> pd.DataFrame:
    return pd.DataFrame(columns=LIST_COLUMNS)


def _empty_issues() -> pd.DataFrame:
    return pd.DataFrame(columns=ISSUE_COLUMNS)


def read_previous(source: BytesIO | Path, filename: str) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        raw = source.read() if not isinstance(source, Path) else Path(source).read_bytes()
        for encoding in ("utf-8-sig", "cp932", "utf-8"):
            try:
                df = pd.read_csv(BytesIO(raw), encoding=encoding)
                break
            except UnicodeDecodeError:
                df = None
        else:
            raise InputFormatError("CSVの文字コードを読み取れませんでした。UTF-8 か Shift-JIS で保存してください。")
    elif suffix == ".xlsx":
        df = pd.read_excel(source, engine="openpyxl")
    else:
        raise InputFormatError("先週のファイルは .xlsx または .csv です。")

    df.columns = [str(c).strip() for c in df.columns]
    if "商品名" not in df.columns:
        raise InputFormatError("先週のファイルに「商品名」列がありません。このアプリが出力した Excel を使ってください。")
    if "価格" not in df.columns:
        raise InputFormatError("先週のファイルに「価格」列がありません。")
    if "在庫" not in df.columns:
        df["在庫"] = ""
    if "商品コード" not in df.columns:
        df["商品コード"] = ""
    else:
        df["商品コード"] = df["商品コード"].map(lambda v: "" if pd.isna(v) else str(v).strip())
    df["価格"] = df["価格"].map(_coerce_price)
    return df


def _coerce_price(value: object) -> object:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return int(number) if number.is_integer() else number
    parsed = parse_price(str(value))
    return parsed


def _effective_pages(requested: int) -> tuple[int, str | None]:
    try:
        count = int(requested)
    except (TypeError, ValueError):
        count = 1
    count = max(count, 1)
    if count > MAX_PAGES:
        return MAX_PAGES, f"ページ数の上限は {MAX_PAGES} です。指定 {count} は切り下げました"
    return count, None


def run_watch(
    *,
    pages: int = 1,
    previous: pd.DataFrame | None = None,
    previous_name: str = "（なし）",
    sample_html: str | None = None,
    base_url: str | None = None,
) -> WatchResult:
    items: list[dict[str, object]] = []
    issues: list[dict[str, object]] = []
    robots_note = ""
    robots_allowed = True
    used_sample = False
    fetched_pages = 0
    source_url = base_url or BASE_URL
    page_limit, page_cap_note = _effective_pages(pages)
    if page_cap_note and SOURCE == "http":
        issues.append({"場所": source_url, "商品名": "", "理由": page_cap_note})

    if SOURCE == "http":
        first: FetchResult | None = None
        client = new_client()
        try:
            for page in range(1, page_limit + 1):
                if len(items) >= MAX_ITEMS:
                    break
                target = page_url(source_url, page)
                result = fetch_html(target, client=client)
                if first is None:
                    first = result
                    robots_note = result.robots_note
                    robots_allowed = result.robots_allowed
                if result.error or not result.html:
                    issues.append({"場所": target, "商品名": "", "理由": result.error or "HTMLが空です"})
                    if page == 1:
                        break
                    continue
                fetched_pages += 1
                parsed, parse_issues = parse_listing(
                    result.html,
                    result.url,
                    max_items=MAX_ITEMS - len(items),
                )
                items.extend(parsed)
                issues.extend(parse_issues)
                if page < page_limit and len(items) < MAX_ITEMS:
                    time.sleep(PAUSE_SECONDS)
        finally:
            client.close()
    else:
        if not sample_html:
            raise InputFormatError("サンプルHTMLがありません。")
        used_sample = True
        robots_note = "同梱のデモ店を使いました。案件では御社の公開一覧を取得します。"
        parsed, parse_issues = parse_listing(
            sample_html,
            source_url,
            max_items=MAX_ITEMS,
        )
        items.extend(parsed)
        issues.extend(parse_issues)
        fetched_pages = 1

    listing = pd.DataFrame(items, columns=LIST_COLUMNS) if items else _empty_listing()
    issue_df = pd.DataFrame(issues, columns=ISSUE_COLUMNS) if issues else _empty_issues()
    if previous is None or previous.empty:
        changes = pd.DataFrame(columns=CHANGE_COLUMNS)
    else:
        changes = diff_listings(listing, previous)

    return WatchResult(
        listing=listing,
        changes=changes,
        issues=issue_df,
        source_url=source_url,
        used_sample=used_sample,
        robots_note=robots_note,
        robots_allowed=robots_allowed,
        page_count=fetched_pages,
        item_count=int(len(listing)),
        change_count=int(len(changes)),
        issue_count=int(len(issue_df)),
        previous_name=previous_name,
    )
