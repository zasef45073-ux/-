# ─────────────────────────────────────────────────────────────────────────────
# dashboard.py  ·  메인 홈 페이지
# 전체 운영 현황 요약 지표를 한눈에 보여줍니다.
# 세부 화면은 사이드바의 각 페이지(pages/)를 사용하세요.
# ─────────────────────────────────────────────────────────────────────────────
from datetime import date

import streamlit as st

from utils.data_loader import load_face_results, load_orders
from utils.styles import apply_global_css, render_sidebar, auto_refresh_loop

# ── 페이지 설정 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🍸 칵테일바 관리자 대시보드",
    page_icon="🍸",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_css()
auto_refresh = render_sidebar()

# ── 메인 헤더 ─────────────────────────────────────────────────────────────────
st.title("🍸 AI 칵테일바 모니터링")
st.caption("DeepFace × LLM+RAG × 서빙 로봇 통합 관제 시스템")

face_df = load_face_results()
orders_df = load_orders()

today = date.today()

today_faces = (
    len(face_df[face_df["datetime"].dt.date == today])
    if not face_df.empty and "datetime" in face_df.columns
    else 0
)
today_orders = (
    len(orders_df[orders_df["datetime"].dt.date == today])
    if not orders_df.empty and "datetime" in orders_df.columns
    else 0
)
top_emotion = (
    face_df["emotion"].mode().iloc[0]
    if not face_df.empty and "emotion" in face_df.columns and len(face_df) > 0
    else "-"
)
completed_orders = (
    len(orders_df[orders_df["로봇 상태"] == "완료"])
    if not orders_df.empty
    else 0
)
blocked_count = (
    len(face_df[face_df["age"].fillna(99) < 19])
    if not face_df.empty and "age" in face_df.columns
    else 0
)

# ── 메트릭 카드 ────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("📸 오늘 방문 감지", f"{today_faces} 건")
c2.metric("🍸 오늘 칵테일 주문", f"{today_orders} 건")
c3.metric("🤖 서빙 완료", f"{completed_orders} 건")
c4.metric("😊 오늘 주요 감정", top_emotion)
c5.metric("🔞 미성년 차단", f"{blocked_count} 건")

st.divider()

# ── 페이지 안내 ────────────────────────────────────────────────────────────────
st.markdown("### 📂 세부 화면 바로가기")
st.markdown("""
| 페이지 | 설명 |
|--------|------|
| 📸 **고객 분석** | 실시간 얼굴 인식 결과 및 미성년자 감지 현황 |
| 🍸 **칵테일 주문** | LLM+RAG 추천 주문 내역 및 상세 보기 |
| 📈 **통계** | 감정·성별·시간대별 분석 및 인기 칵테일 차트 |
| 🤖 **로봇 대시보드** | 서빙 로봇 실시간 상태·대기열·작업 이력 |
""")
st.info("👈 왼쪽 사이드바에서 원하는 페이지를 선택하세요.")

# ── 자동 새로고침 ──────────────────────────────────────────────────────────────
auto_refresh_loop(auto_refresh)


