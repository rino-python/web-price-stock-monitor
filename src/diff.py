"""先週の一覧と今回の一覧を突き合わせ、変化だけ残す。"""

from __future__ import annotations

import pandas as pd

from src.shop_config import STOCK_IN, STOCK_OUT

PRICE_CHANGE_YEN = 1  # 1円以上の差を価格変化とみなす
CHANGE_COLUMNS = ["商品コード", "商品名", "変化", "今回価格", "前回価格", "今回在庫", "前回在庫", "内容"]


def _row_key(row: pd.Series) -> str:
    code = str(row.get("商品コード", "") or "").strip()
    if code:
        return f"code:{code}"
    name = str(row.get("商品名", "") or "").strip()
    return f"name:{name}" if name else ""


def _index_rows(df: pd.DataFrame) -> dict[str, pd.Series]:
    mapping: dict[str, pd.Series] = {}
    if df.empty:
        return mapping
    for _, row in df.iterrows():
        key = _row_key(row)
        if key:
            if key not in mapping:
                mapping[key] = row
    return mapping


def _stock_change_label(old_stock: str, new_stock: str) -> str | None:
    if not old_stock or not new_stock or old_stock == new_stock:
        return None
    if old_stock == STOCK_IN and new_stock == STOCK_OUT:
        return "売り切れ"
    if old_stock == STOCK_OUT and new_stock == STOCK_IN:
        return "再入荷"
    return "在庫変化"


def _change_row(
    *,
    code: object,
    name: object,
    label: str,
    price_now: object,
    price_prev: object,
    stock_now: str,
    stock_prev: str,
    detail: str,
) -> dict[str, object]:
    return {
        "商品コード": code or "",
        "商品名": name,
        "変化": label,
        "今回価格": price_now,
        "前回価格": price_prev,
        "今回在庫": stock_now,
        "前回在庫": stock_prev,
        "内容": detail,
    }


def diff_listings(current: pd.DataFrame, previous: pd.DataFrame) -> pd.DataFrame:
    now = _index_rows(current)
    before = _index_rows(previous)
    rows: list[dict[str, object]] = []

    for key, row in now.items():
        name = row.get("商品名")
        code = row.get("商品コード", "")
        price = row.get("価格")
        stock = str(row.get("在庫", "") or "")
        if key not in before:
            rows.append(
                _change_row(
                    code=code,
                    name=name,
                    label="新着",
                    price_now=price,
                    price_prev=None,
                    stock_now=stock,
                    stock_prev="",
                    detail="先週の一覧に無い商品です",
                )
            )
            continue
        old = before[key]
        old_price = old.get("価格")
        old_stock = str(old.get("在庫", "") or "")
        if pd.notna(price) and pd.notna(old_price) and abs(float(price) - float(old_price)) >= PRICE_CHANGE_YEN:
            if float(price) < float(old_price):
                label = "値下がり"
            else:
                label = "値上がり"
            rows.append(
                _change_row(
                    code=code,
                    name=name,
                    label=label,
                    price_now=price,
                    price_prev=old_price,
                    stock_now=stock,
                    stock_prev=old_stock,
                    detail=f"{old_price} → {price}",
                )
            )
        stock_label = _stock_change_label(old_stock, stock)
        if stock_label:
            rows.append(
                _change_row(
                    code=code,
                    name=name,
                    label=stock_label,
                    price_now=price,
                    price_prev=old_price,
                    stock_now=stock,
                    stock_prev=old_stock,
                    detail=f"{old_stock} → {stock}",
                )
            )

    for key, old in before.items():
        if key not in now:
            rows.append(
                _change_row(
                    code=old.get("商品コード", ""),
                    name=old.get("商品名"),
                    label="掲載終了",
                    price_now=None,
                    price_prev=old.get("価格"),
                    stock_now="",
                    stock_prev=str(old.get("在庫", "") or ""),
                    detail="今回の一覧にありません",
                )
            )

    if not rows:
        return pd.DataFrame(columns=CHANGE_COLUMNS)
    return pd.DataFrame(rows)
