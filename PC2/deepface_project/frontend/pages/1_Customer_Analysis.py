# ─────────────────────────────────────────────────────────────────────────────
# pages/1_고객분석.py  ·  고객 얼굴 분석 페이지
# 실시간 DeepFace 분석 결과 및 미성년자 감지 현황을 표시합니다.
# ─────────────────────────────────────────────────────────────────────────────
from datetime import date

import streamlit as st

from utils.data_loader import load_face_results, to_csv_bytes
from utils.styles import apply_global_css, render_sidebar, auto_refresh_loop

# ── 페이지 설정 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="📸 고객 분석 | 칵테일바",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_css()
auto_refresh = render_sidebar()

# ── 헤더 ─────────────────────────────────────────────────────────────────────
st.title("📸 실시간 고객 얼굴 분석")
st.caption("DeepFace가 분석한 나이 · 성별 · 감정 결과 및 미성년자 감지 현황")
st.divider()

# ── 데이터 로드 ────────────────────────────────────────────────────────────────
face_df = load_face_results()
today   = date.today()

# ── 상단 요약 지표 ─────────────────────────────────────────────────────────────
total_today = (
    len(face_df[face_df["datetime"].dt.date == today])
    if not face_df.empty and "datetime" in face_df.columns
    else 0
)
minor_count = (
    len(face_df[face_df["age"].fillna(99) < 19])
    if not face_df.empty and "age" in face_df.columns
    else 0
)
avg_confidence = (
    round(face_df["face_confidence"].mean(), 2)
    if not face_df.empty and "face_confidence" in face_df.columns
    else 0.0
)

m1, m2, m3 = st.columns(3)
m1.metric("📸 오늘 감지 건수",    f"{total_today} 건")
m2.metric("🔞 미성년자 의심",     f"{minor_count} 건")
m3.metric("🎯 평균 인식 신뢰도",  f"{avg_confidence}")

st.divider()

# ── 미성년자 경보 ──────────────────────────────────────────────────────────────
if not face_df.empty and "age" in face_df.columns:
    minors = face_df[face_df["age"].fillna(99) < 19]
    if not minors.empty:
        st.error(f"🔞 미성년자 의심 고객 **{len(minors)}건** 감지 — 즉시 확인 필요!")

# ── 분석 결과 테이블 ──────────────────────────────────────────────────────────
st.subheader("분석 결과 목록 (최근 100건)")

if face_df.empty:
    st.info("분석 데이터가 없습니다. `/analyze/` 엔드포인트를 호출하세요.")
else:
    cols    = ["datetime", "age", "gender", "emotion", "face_confidence", "face_key"]
    show_df = face_df[[c for c in cols if c in face_df.columns]].head(100)

    def highlight_minor(row):
        """미성년자 의심 행을 붉은 배경으로 강조합니다."""
        age = row.get("age", 99)
        if isinstance(age, (int, float)) and age < 19:
            return ["background-color: #5c1a1a"] * len(row)
        return [""] * len(row)

    st.dataframe(
        show_df.style.apply(highlight_minor, axis=1),
        use_container_width=True,
        height=420,
    )

    st.download_button(
        label="⬇️ 고객 분석 CSV 다운로드",
        data=to_csv_bytes(face_df),
        file_name=f"customers_{today}.csv",
        mime="text/csv",
    )

# ── 자동 새로고침 ──────────────────────────────────────────────────────────────
auto_refresh_loop(auto_refresh)
