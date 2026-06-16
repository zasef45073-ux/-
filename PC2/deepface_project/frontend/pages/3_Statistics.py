# ─────────────────────────────────────────────────────────────────────────────
# pages/3_통계.py  ·  운영 통계 페이지
# 감정·성별·시간대별 분석 차트 및 인기 칵테일 순위를 표시합니다.
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st

from utils.data_loader import load_face_results, load_orders
from utils.styles import apply_global_css, render_sidebar, auto_refresh_loop

# ── 페이지 설정 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="📈 통계 | 칵테일바",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_css()
auto_refresh = render_sidebar()

# ── 헤더 ─────────────────────────────────────────────────────────────────────
st.title("📊 칵테일바 운영 통계")
st.caption("감정 · 성별 · 시간대별 고객 분포 및 인기 칵테일 차트")
st.divider()

# ── 데이터 로드 ────────────────────────────────────────────────────────────────
face_df   = load_face_results()
orders_df = load_orders()

# ── 고객 분석 통계 ─────────────────────────────────────────────────────────────
st.subheader("👥 고객 분석 통계")

if face_df.empty:
    st.info("통계를 표시할 얼굴 분석 데이터가 없습니다.")
else:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**감정 분포**")
        if "emotion" in face_df.columns:
            emotion_counts = (
                face_df["emotion"]
                .value_counts()
                .rename_axis("감정")
                .reset_index(name="건수")
            )
            st.bar_chart(emotion_counts.set_index("감정"))

    with col2:
        st.markdown("**성별 분포**")
        if "gender" in face_df.columns:
            gender_counts = (
                face_df["gender"]
                .value_counts()
                .rename_axis("성별")
                .reset_index(name="건수")
            )
            st.bar_chart(gender_counts.set_index("성별"))

    st.markdown("**시간대별 분석 건수**")
    if "datetime" in face_df.columns:
        hourly = (
            face_df.dropna(subset=["datetime"])
            .set_index("datetime")
            .resample("h")
            .size()
            .rename("건수")
        )
        if not hourly.empty:
            st.line_chart(hourly)

st.divider()

# ── 칵테일 주문 통계 ───────────────────────────────────────────────────────────
st.subheader("🍸 칵테일 주문 통계")

if orders_df.empty:
    st.info("통계를 표시할 주문 데이터가 없습니다.")
else:
    col3, col4 = st.columns(2)

    with col3:
        if "추천" in orders_df.columns:
            st.markdown("**🍹 인기 칵테일 TOP**")
            cocktail_counts = (
                orders_df["추천"]
                .value_counts()
                .rename_axis("칵테일")
                .reset_index(name="주문수")
            )
            st.bar_chart(cocktail_counts.set_index("칵테일"))

    with col4:
        if "로봇 상태" in orders_df.columns:
            st.markdown("**🤖 서빙 로봇 처리 상태**")
            robot_counts = (
                orders_df["로봇 상태"]
                .value_counts()
                .rename_axis("상태")
                .reset_index(name="건수")
            )
            st.bar_chart(robot_counts.set_index("상태"))

# ── 자동 새로고침 ──────────────────────────────────────────────────────────────
auto_refresh_loop(auto_refresh)
