from __future__ import annotations

import unicodedata

import pandas as pd
import streamlit as st

from generate_sample import DEMO_HTML, HTML_NAME, PREVIOUS_NAME, SAMPLES_DIR
from src.colors import CHANGE_HEX, CHANGE_LABELS
from src.excel_io import build_result_xlsx
from src.run import InputFormatError, read_previous, run_watch
from src.shop_config import SHOP_LABEL, SHOP_NAME, SOURCE

SAMPLE_HTML_PATH = SAMPLES_DIR / HTML_NAME
SAMPLE_PREV_PATH = SAMPLES_DIR / PREVIOUS_NAME

CHANGE_ROW_CSS = {label: f"background-color: #{hex_}" for label, hex_ in CHANGE_HEX.items()}


def _format_yen(value: object) -> str:
    if pd.isna(value):
        return ""
    try:
        return f"¥{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return str(value)


def _style_change_rows(row: pd.Series) -> list[str]:
    fill = CHANGE_ROW_CSS.get(str(row.get("変化", "")), "")
    return [fill] * len(row)


def _change_counts(changes: pd.DataFrame) -> dict[str, int]:
    if changes.empty or "変化" not in changes.columns:
        return {label: 0 for label in CHANGE_LABELS}
    counts = changes["変化"].value_counts()
    return {label: int(counts.get(label, 0)) for label in CHANGE_LABELS}


def _display_units(text: object) -> float:
    width = 0.0
    for char in str("" if text is None or (isinstance(text, float) and pd.isna(text)) else text):
        width += 2.0 if unicodedata.east_asian_width(char) in {"W", "F"} else 1.0
    return width


def _fit_column_config(df: pd.DataFrame) -> dict:
    """セルと見出しの文字幅に合わせて列幅を決める。内容・理由は切れない幅にする。"""
    config: dict = {}
    wide = {"内容", "理由", "場所", "URL"}
    for column in df.columns:
        longest = _display_units(column)
        for value in df[column]:
            longest = max(longest, _display_units(value))
        pixels = int(round(longest * 8 + 40))
        cap = 480 if str(column) in wide else 220
        pixels = min(max(pixels, 56), cap)
        config[str(column)] = st.column_config.TextColumn(str(column), width=pixels)
    return config


st.set_page_config(
    page_title="自社サイトの価格・在庫チェック",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.html(
    """
<style>
[data-testid="stFileUploaderDropzoneInstructions"] > div > span,
[data-testid="stFileDropzoneInstructions"] > div > span {
  visibility: hidden;
}
[data-testid="stFileUploaderDropzoneInstructions"] > div > span::after,
[data-testid="stFileDropzoneInstructions"] > div > span::after {
  content: "ファイルをここにドラッグ＆ドロップ";
  visibility: visible;
  display: block;
}
[data-testid="stFileUploaderDropzoneInstructions"] > div > small,
[data-testid="stFileDropzoneInstructions"] > div > small {
  visibility: hidden;
}
[data-testid="stFileUploaderDropzoneInstructions"] > div > small::after,
[data-testid="stFileDropzoneInstructions"] > div > small::after {
  content: "1ファイルあたり上限 200MB ・ XLSX, CSV";
  visibility: visible;
  display: block;
}
[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
  text-indent: -9999px;
  line-height: 0;
}
[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"]::after {
  content: "ファイルを選択";
  text-indent: 0;
  line-height: initial;
  display: inline-block;
}
.stAppDeployButton, [data-testid="stAppDeployButton"] {
  display: none !important;
}
[data-testid="stSidebar"] {
  border-right: 3px solid #0D7377;
}
.watch-hero {
  background: linear-gradient(120deg, #0D7377 0%, #14919B 52%, #2A9D8F 100%);
  color: #F7FFFE;
  padding: 1.35rem 1.5rem 1.2rem;
  border-radius: 18px;
  margin-bottom: 0.4rem;
}
.watch-hero .kicker {
  display: inline-block;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  background: rgba(255,255,255,0.16);
  border: 1px solid rgba(255,255,255,0.28);
  padding: 0.18rem 0.55rem;
  border-radius: 999px;
  margin-bottom: 0.55rem;
}
.watch-hero h1 {
  font-size: 1.7rem;
  margin: 0 0 0.35rem 0;
  font-weight: 700;
}
.watch-hero p {
  margin: 0;
  opacity: 0.92;
  font-size: 0.95rem;
}
.scope-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 0.6rem 0 0.9rem;
}
.scope-card {
  background: #FFFCF7;
  border: 1px solid #D5E3DE;
  border-radius: 14px;
  padding: 0.9rem 1rem;
}
.scope-card h3 {
  margin: 0 0 0.4rem 0;
  font-size: 0.92rem;
}
.scope-card ul {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.88rem;
  line-height: 1.55;
}
.scope-card.out {
  background: #F7F3EC;
  border-color: #E4D9C8;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0.2rem 0 0.8rem;
}
.pill {
  font-size: 0.78rem;
  padding: 0.22rem 0.7rem;
  border-radius: 999px;
  border: 1px solid transparent;
}
.pill.drop { background: #F6C7B0; }
.pill.rise { background: #C5E6EA; }
.pill.fresh { background: #B8E0D0; }
.pill.sold { background: #E8A88A; }
.pill.restock { background: #D4E8C8; }
.pill.gone { background: #E2D4CE; }
.idle-card {
  background: #FFFCF7;
  border: 1px dashed #0D7377;
  border-radius: 16px;
  padding: 1.4rem 1.3rem;
  text-align: center;
}
.idle-card .label {
  color: #0D7377;
  font-weight: 700;
  letter-spacing: 0.06em;
  font-size: 0.78rem;
  margin-bottom: 0.4rem;
}
.idle-card p {
  margin: 0;
  color: #3A4A48;
}
@media (max-width: 900px) {
  .scope-grid { grid-template-columns: 1fr; }
}
</style>
"""
)

with st.sidebar:
    st.markdown("### 監視パネル")
    st.caption("先週の一覧を上げてから「取得して比較する」を押すと、差が出ます。")
    if SAMPLE_PREV_PATH.exists():
        prev_bytes = SAMPLE_PREV_PATH.read_bytes()
    else:
        prev_bytes = b""
    st.download_button(
        label="先週サンプル（CSV）",
        data=prev_bytes,
        file_name=PREVIOUS_NAME,
        mime="text/csv",
        disabled=not prev_bytes,
        use_container_width=True,
    )
    uploaded = st.file_uploader(
        "先週の一覧",
        type=["xlsx", "csv"],
        help="このアプリが以前出した Excel か、同じ列の CSV を上げてください。手元に無いときは、上の先週サンプルを使います。",
    )
    run = st.button("取得して比較する", type="primary", use_container_width=True)
    st.caption(f"対象は架空店「{SHOP_NAME}」です。案件では御社の公開一覧に差し替えます。他社URLは入力できません。")

st.html(
    f"""
<div class="watch-hero">
  <div class="kicker">DEMO · {SHOP_LABEL}</div>
  <h1>自社サイトの価格・在庫チェック</h1>
  <p>先週出した一覧を上げて、自社の公開カタログを取り、変わった行だけを Excel に残します。案件ではこのデモ店が御社サイトに置き換わります。</p>
</div>
<div class="scope-grid">
  <div class="scope-card">
    <h3>このデモで見られること</h3>
    <ul>
      <li>自社の公開カタログの価格・在庫</li>
      <li>値下げの反映、売り切れ、再入荷</li>
      <li>新着と掲載終了</li>
      <li>取れなかった行は失敗ログへ</li>
    </ul>
  </div>
  <div class="scope-card out">
    <h3>このデモの範囲外</h3>
    <ul>
      <li>他社URLの入力（他人のサイトを叩けてしまうため）</li>
      <li>ログインが必要なページ、大手モール</li>
      <li>Slack / メール通知、常時起動の定期実行</li>
    </ul>
  </div>
</div>
"""
)

if run:
    if uploaded is None:
        st.session_state.watch_result = None
        st.session_state.watch_xlsx = None
        st.warning(
            "先週の一覧を上げてください。手元に無いときは、左の「先週サンプル」をダウンロードしてから上げてください。"
        )
    else:
        sample_html = SAMPLE_HTML_PATH.read_text(encoding="utf-8") if SAMPLE_HTML_PATH.exists() else DEMO_HTML
        try:
            previous_df = read_previous(uploaded, filename=uploaded.name)
        except InputFormatError as exc:
            st.error(str(exc))
            st.stop()

        try:
            result = run_watch(
                previous=previous_df,
                previous_name=uploaded.name,
                sample_html=sample_html,
            )
        except Exception as exc:  # noqa: BLE001
            if SOURCE == "http":
                st.error(f"処理に失敗しました。ネット接続か対象サイトを確認してください。（{exc}）")
            else:
                st.error(f"処理に失敗しました。同梱のデモ店データを確認してください。（{exc}）")
            st.stop()

        if not result.robots_allowed:
            st.error(result.robots_note)
            st.stop()

        st.session_state.watch_result = result
        st.session_state.watch_xlsx = build_result_xlsx(result)

result = st.session_state.get("watch_result")
xlsx_bytes = st.session_state.get("watch_xlsx")
if result is None or xlsx_bytes is None:
    st.html(
        """
<div class="idle-card">
  <div class="label">待機中</div>
  <p>左で先週の一覧を上げてから、「取得して比較する」を押すと、ここに差が出ます。</p>
</div>
"""
    )
    st.stop()

counts = _change_counts(result.changes)

with st.container(border=True):
    head_l, head_r = st.columns([3.2, 1.2])
    with head_l:
        st.markdown("#### 今回の取得結果")
        st.caption(f"対象：{SHOP_NAME}")
    with head_r:
        st.download_button(
            label="結果Excelを保存",
            data=xlsx_bytes,
            file_name="価格在庫_ウォッチ結果.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )
    st.caption(result.robots_note)

    m1, m2, m3 = st.columns(3)
    m1.metric("取得", f"{result.item_count} 件")
    m2.metric("変化", f"{result.change_count} 件")
    m3.metric("失敗", f"{result.issue_count} 件")

    if result.issue_count:
        st.warning(
            f"取れなかった行が {result.issue_count} 件あります。"
            "失敗ログを確認してください。この行は今回一覧と変化に含めていません。"
        )

    st.html(
        f"""
<div class="legend">
  <span class="pill drop">値下がり {counts['値下がり']}</span>
  <span class="pill rise">値上がり {counts['値上がり']}</span>
  <span class="pill fresh">新着 {counts['新着']}</span>
  <span class="pill sold">売り切れ {counts['売り切れ']}</span>
  <span class="pill restock">再入荷 {counts['再入荷']}</span>
  <span class="pill gone">掲載終了 {counts['掲載終了']}</span>
</div>
"""
    )

    tab_chg, tab_fail, tab_list = st.tabs(["変化", "失敗ログ", "今回一覧"])
    with tab_chg:
        if result.changes.empty:
            st.success("先週と比べた変化はありません。")
        else:
            chg = result.changes.copy()
            for col in ("今回価格", "前回価格"):
                if col in chg.columns:
                    chg[col] = chg[col].map(_format_yen)
            st.dataframe(
                chg.style.apply(_style_change_rows, axis=1),
                use_container_width=False,
                hide_index=True,
                column_config=_fit_column_config(chg),
            )
    with tab_list:
        view = result.listing.copy()
        if "価格" in view.columns:
            view["価格"] = view["価格"].map(_format_yen)
        st.dataframe(
            view,
            use_container_width=False,
            hide_index=True,
            column_config=_fit_column_config(view),
        )
    with tab_fail:
        if result.issues.empty:
            st.success("失敗はありません。")
        else:
            st.dataframe(
                result.issues,
                use_container_width=False,
                hide_index=True,
                column_config=_fit_column_config(result.issues),
            )
