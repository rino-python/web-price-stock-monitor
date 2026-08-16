"""公開カタログの HTML から、商品コード・商品名・価格・在庫を抜く。セレクタは shop_config。"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.shop_config import CURRENCY, MAX_ITEMS, SELECTORS


def parse_price(text: str) -> float | int | None:
    cleaned = (
        text.replace("¥", "")
        .replace("￥", "")
        .replace("円", "")
        .replace("税込", "")
        .replace(",", "")
        .replace("，", "")
        .strip()
    )
    cleaned = re.sub(r"\s+", "", cleaned)
    if not cleaned:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if value.is_integer():
        return int(value)
    return value


def parse_listing(
    html: str,
    page_url: str,
    *,
    max_items: int | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """成功した行と、抜けた行の理由を返す。max_items を超えたカードは取らない。"""
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict[str, object]] = []
    issues: list[dict[str, object]] = []

    cards = soup.select(SELECTORS["card"])
    if not cards:
        issues.append({"場所": page_url, "商品名": "", "理由": f"商品カード（{SELECTORS['card']}）が見つかりません"})
        return items, issues

    if max_items is not None and max_items <= 0:
        issues.append(
            {
                "場所": page_url,
                "商品名": "",
                "理由": f"商品数が上限 {MAX_ITEMS} 件に達したため、以降は取得していません",
            }
        )
        return items, issues

    seen_codes: set[str] = set()
    stopped_early = False
    for index, card in enumerate(cards, start=1):
        if max_items is not None and len(items) >= max_items:
            stopped_early = True
            break
        if index > MAX_ITEMS:
            stopped_early = True
            break
        reasons: list[str] = []
        code_el = card.select_one(SELECTORS["code"])
        code = code_el.get_text(strip=True) if code_el else ""
        if not code:
            reasons.append("商品コードが空です")
        elif code in seen_codes:
            reasons.append("商品コードが重複しています")
        else:
            seen_codes.add(code)

        title_el = card.select_one(SELECTORS["name"])
        if title_el is None:
            title = ""
            href = None
        else:
            title = str(title_el.get("title") or title_el.get_text(strip=True)).strip()
            href = title_el.get("href")
        url = urljoin(page_url, str(href)) if href else ""
        if not title:
            reasons.append("商品名が空です")

        price_el = card.select_one(SELECTORS["price"])
        price_text = price_el.get_text(strip=True) if price_el else ""
        price = parse_price(price_text) if price_text else None
        if price is None:
            reasons.append("価格を解釈できません")

        stock_el = card.select_one(SELECTORS["stock"])
        stock = " ".join(stock_el.get_text(" ", strip=True).split()) if stock_el else ""
        if not stock:
            reasons.append("在庫表示が空です")

        if reasons:
            issues.append(
                {
                    "場所": url or f"{page_url}#{index}",
                    "商品名": title or code,
                    "理由": " / ".join(reasons),
                }
            )
            continue

        items.append(
            {
                "商品コード": code,
                "商品名": title,
                "価格": price,
                "通貨": CURRENCY,
                "在庫": stock,
                "URL": url,
            }
        )

    if stopped_early:
        issues.append(
            {
                "場所": page_url,
                "商品名": "",
                "理由": f"商品数が上限 {MAX_ITEMS} 件に達したため、以降は取得していません",
            }
        )
    return items, issues
