# ─────────────────────────────────────────────────────────────────────────────
# pages/2_칵테일주문.py  ·  칵테일 주문 내역 페이지
# LLM+RAG가 추천한 칵테일 주문 목록 및 개별 상세 정보를 표시합니다.
# ─────────────────────────────────────────────────────────────────────────────
from datetime import date

import streamlit as st

from utils.data_loader import load_orders, to_csv_bytes
from utils.styles import apply_global_css, render_sidebar, auto_refresh_loop

# ── 페이지 설정 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🍸 칵테일 주문 | 칵테일바",
    page_icon="🍸",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_css()
auto_refresh = render_sidebar()

# ── 헤더 ─────────────────────────────────────────────────────────────────────
st.title("🍸 칵테일 주문 내역")
st.caption("LLM+RAG 추천 칵테일 주문 목록 · 고객 정보 · 서빙 로봇 상태")
st.divider()

# ── 데이터 로드 ────────────────────────────────────────────────────────────────
orders_df = load_orders()
today     = date.today()

# ── 상단 요약 지표 ─────────────────────────────────────────────────────────────
today_orders = (
    len(orders_df[orders_df["datetime"].dt.date == today])
    if not orders_df.empty and "datetime" in orders_df.columns
    else 0
)
completed = (
    len(orders_df[orders_df["로봇 상태"] == "완료"])
    if not orders_df.empty
    else 0
)
pending = (
    len(orders_df[orders_df["로봇 상태"].isin(["대기", "처리중", "이동중", "서빙중"])])
    if not orders_df.empty
    else 0
)

m1, m2, m3 = st.columns(3)
m1.metric("🍸 오늘 주문",   f"{today_orders} 건")
m2.metric("✅ 서빙 완료",   f"{completed} 건")
m3.metric("⏳ 처리 대기",   f"{pending} 건")

st.divider()

# ── 주문 목록 테이블 ──────────────────────────────────────────────────────────
st.subheader("주문 목록 (최근 100건)")

if orders_df.empty:
    st.info("주문 데이터가 없습니다. LLM 시스템이 `/llm/result`를 호출하면 기록됩니다.")
else:
    list_cols = ["datetime", "age", "gender", "emotion", "추천", "로봇 상태"]
    show_df   = orders_df[[c for c in list_cols if c in orders_df.columns]].head(100)
    st.dataframe(show_df, use_container_width=True, height=350)

    st.divider()

    # ── 주문 상세 보기 ─────────────────────────────────────────────────────────
    st.subheader("🔍 주문 상세 보기")

    def _format_order_option(x: int) -> str:
        row = orders_df.iloc[x]
        dt_value = row.get("datetime")

        try:
            dt_label = dt_value.strftime("%m/%d %H:%M")
        except (AttributeError, TypeError, ValueError):
            dt_label = "시간정보없음"

        return (
            f"{dt_label}"
            f"  🍸  {row.get('추천', '')}"
            f"  [{row.get('로봇 상태', '')}]"
        )

    idx = st.selectbox(
        "주문 선택",
        range(len(orders_df)),
        format_func=_format_order_option,
    )
    row = orders_df.iloc[idx]

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**고객 정보**")
        age_val  = row.get("age")
        is_minor = isinstance(age_val, (int, float)) and age_val < 19
        st.json({
            "나이":       f"{age_val}세" if age_val else "-",
            "성별":       row.get("gender"),
            "감정":       row.get("emotion"),
            "미성년자 여부": "⚠️ 예" if is_minor else "아니오",
        })

    with col_b:
        st.markdown("**칵테일 추천 결과**")
        st.json({
            "추천 칵테일":    row.get("추천"),
            "서빙 로봇 상태": row.get("로봇 상태"),
        })

    st.markdown("**LLM 추천 근거**")
    st.text_area("", value=row.get("LLM 응답", ""), height=120, disabled=True)

    st.divider()

    # ── CSV 다운로드 ────────────────────────────────────────────────────────────
    st.download_button(
        label="⬇️ 칵테일 주문 내역 CSV 다운로드",
        data=to_csv_bytes(orders_df),
        file_name=f"cocktail_orders_{today}.csv",
        mime="text/csv",
    )

# ── 자동 새로고침 ──────────────────────────────────────────────────────────────
auto_refresh_loop(auto_refresh)
