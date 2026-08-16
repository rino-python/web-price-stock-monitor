"""変化ラベルの色。画面と Excel で同じ値を使う。"""

from __future__ import annotations

CHANGE_HEX = {
    "値下がり": "F6C7B0",
    "値上がり": "C5E6EA",
    "新着": "B8E0D0",
    "売り切れ": "E8A88A",
    "再入荷": "D4E8C8",
    "在庫変化": "F6E2A8",
    "掲載終了": "E2D4CE",
}

CHANGE_LABELS = ("値下がり", "値上がり", "新着", "売り切れ", "再入荷", "掲載終了")
