"""納品時に差し替える店の設定。デモは同梱HTML、案件では SOURCE と URL を御社向けに変える。"""

from __future__ import annotations

# local = 同梱HTML（デモ）。http = 御社の公開一覧を取得する（納品時）。
SOURCE = "local"
SHOP_NAME = "和洋雑貨 かもめ堂"
SHOP_LABEL = "和洋雑貨 かもめ堂（デモ）"
BASE_URL = "https://kamome-demo.example.jp/items/"
CURRENCY = "JPY"
CURRENCY_SYMBOL = "¥"
PAGE_QUERY = "page"

SELECTORS = {
    "card": "article.item",
    "code": ".sku",
    "name": "h3 a",
    "price": ".price",
    "stock": ".stock",
}

STOCK_IN = "在庫あり"
STOCK_OUT = "売り切れ"

# 1回の実行で取れる上限。pages 引数ではこれ以上にできない。
MAX_PAGES = 10
MAX_ITEMS = 500
