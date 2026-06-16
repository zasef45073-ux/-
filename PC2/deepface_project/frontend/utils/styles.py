# ─────────────────────────────────────────────────────────────────────────────
# utils/styles.py
# 전역 CSS 적용 및 공통 사이드바 렌더링
# ─────────────────────────────────────────────────────────────────────────────
import time
from datetime import datetime

import streamlit as st


# ── 전역 CSS ───────────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
    [data-testid="stAppViewContainer"] { background-color: #0d0d1a; }
    [data-testid="stSidebar"]          { background-color: #1a1a2e; }
    h1, h2, h3                         { color: #e8c97e !important; }
    .stMetric label                    { color: #c9a84c !important; }
    [data-testid="stMetricValue"]      { color: #ffffff !important; }
    .stTabs [data-baseweb="tab"]       { color: #c9a84c; }
    .stAlert                           { border-radius: 8px; }
</style>
"""


def apply_global_css() -> None:
    """칵테일바 테마 CSS를 현재 페이지에 적용합니다."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ── 공통 사이드바 ───────────────────────────────────────────────────────────────
def render_sidebar() -> bool:
    """
    공통 사이드바를 렌더링합니다.

    Returns:
        auto_refresh (bool): 자동 새로고침 활성화 여부
    """
    with st.sidebar:
        st.title("🍸 칵테일바 대시보드")
        st.caption("AI 칵테일 추천 시스템")
        st.divider()

        # 새로고침 설정
        st.subheader("⚙️ 새로고침 설정")
        auto_refresh = st.toggle("자동 새로고침 (10초)", value=True)
        if st.button("🔄 지금 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()

        # 시스템 연결 상태
        st.subheader("📡 시스템 연결 상태")
        st.success("✅ DeepFace API (포트 8000)")
        st.info("🤖 서빙 로봇 → `/robot/status`")
        st.info("🧠 LLM+RAG 칵테일 추천")
        st.warning("🔞 미성년자 자동 차단 활성")

        st.divider()
        st.caption(f"마지막 업데이트\n{datetime.now().strftime('%H:%M:%S')}")

    return auto_refresh


# ── 자동 새로고침 처리 ──────────────────────────────────────────────────────────
def auto_refresh_loop(enabled: bool) -> None:
    """auto_refresh가 True이면 10초 대기 후 캐시 클리어 및 rerun."""
    if enabled:
        time.sleep(10)
        st.cache_data.clear()
        st.rerun()
