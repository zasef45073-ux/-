# ─────────────────────────────────────────────────────────────────────────────
# pages/4_로봇대시보드.py  ·  서빙 로봇 대시보드 페이지
# 로봇 실시간 상태 배너 · 서빙 대기열 · 작업 이력 · 성능 차트를 표시합니다.
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st

from utils.data_loader import load_orders
from utils.styles import apply_global_css, render_sidebar, auto_refresh_loop

# ── 페이지 설정 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🤖 로봇 대시보드 | 칵테일바",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_css()
auto_refresh = render_sidebar()

# ── 헤더 ─────────────────────────────────────────────────────────────────────
st.title("🤖 서빙 로봇 대시보드")
st.caption("실시간 로봇 상태 · 서빙 대기열 · 작업 이력 · 성능 통계")
st.divider()

# ── 데이터 로드 ────────────────────────────────────────────────────────────────
orders_df = load_orders()

# ── [섹션 1] 요약 지표 카드 ────────────────────────────────────────────────────
st.subheader("📊 요약 지표")

robot_waiting = len(orders_df[orders_df["로봇 상태"] == "대기"])       if not orders_df.empty else 0
robot_active  = len(orders_df[orders_df["로봇 상태"].isin(["처리중", "이동중", "서빙중"])]) if not orders_df.empty else 0
robot_done    = len(orders_df[orders_df["로봇 상태"] == "완료"])       if not orders_df.empty else 0
robot_error   = len(orders_df[orders_df["로봇 상태"] == "오류"])       if not orders_df.empty else 0
total_tasks   = len(orders_df)                                          if not orders_df.empty else 0
success_rate  = round(robot_done / total_tasks * 100, 1)               if total_tasks > 0 else 0.0

rc1, rc2, rc3, rc4, rc5 = st.columns(5)
rc1.metric("⏳ 대기 중",  f"{robot_waiting} 건")
rc2.metric("🚗 작업 중",  f"{robot_active} 건")
rc3.metric("✅ 완료",     f"{robot_done} 건")
rc4.metric("❌ 오류",     f"{robot_error} 건")
rc5.metric("📊 완료율",   f"{success_rate} %")

st.divider()

# ── [섹션 2] 현재 로봇 상태 배너 ──────────────────────────────────────────────
st.subheader("🔴 현재 로봇 상태")

# 현재 상태 결정: 처리중 > 대기 > 없음
if orders_df.empty:
    current_status = "대기"
    current_order  = None
else:
    active_rows = orders_df[orders_df["로봇 상태"].isin(["처리중", "이동중", "서빙중"])]
    if not active_rows.empty:
        current_order  = active_rows.iloc[0]
        current_status = current_order["로봇 상태"]
    else:
        waiting_rows = orders_df[orders_df["로봇 상태"] == "대기"]
        if not waiting_rows.empty:
            current_order  = waiting_rows.iloc[0]
            current_status = "대기"
        else:
            current_order  = None
            current_status = "대기"

# 상태별 배경색 / 아이콘 매핑
STATUS_STYLE: dict[str, tuple[str, str]] = {
    "대기":   ("#1a2a4a", "🟡"),
    "처리중": ("#1a3a1a", "🟢"),
    "이동중": ("#1a3a1a", "🟢"),
    "서빙중": ("#1a3a1a", "🟢"),
    "완료":   ("#1a2a1a", "✅"),
    "오류":   ("#3a1a1a", "🔴"),
}
bg_color, status_icon = STATUS_STYLE.get(current_status, ("#1a1a2e", "⚪"))

st.markdown(
    f"""
    <div style="background:{bg_color}; border-radius:12px; padding:28px;
                text-align:center; margin-bottom:16px;">
        <div style="font-size:52px;">{status_icon}</div>
        <div style="font-size:30px; font-weight:bold; color:#e8c97e; margin-top:10px;">
            {current_status}
        </div>
        <div style="color:#aaa; font-size:14px; margin-top:6px;">서빙 로봇 현재 상태</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 현재 처리 중인 주문 요약
if current_order is not None:
    st.markdown("#### 현재 처리 중인 주문")
    co1, co2, co3 = st.columns(3)
    co1.info(f"**추천 칵테일**\n\n{current_order.get('추천', '-')}")
    co2.info(f"**고객 감정**\n\n{current_order.get('emotion', '-')}")
    dt_val = current_order.get("datetime")
    dt_str = dt_val.strftime("%m/%d %H:%M") if hasattr(dt_val, "strftime") else str(dt_val)
    co3.info(f"**주문 시각**\n\n{dt_str}")

st.divider()

# ── [섹션 3] 서빙 대기열 & 완료 이력 ─────────────────────────────────────────
st.subheader("📋 대기열 & 작업 이력")

rb1, rb2 = st.columns(2)

with rb1:
    st.markdown("#### ⏳ 서빙 대기열")
    if orders_df.empty:
        st.info("대기 중인 주문이 없습니다.")
    else:
        queue_df = orders_df[
            orders_df["로봇 상태"].isin(["대기", "처리중", "이동중", "서빙중"])
        ].copy()

        if queue_df.empty:
            st.success("현재 대기 중인 주문 없음 — 로봇 유휴 상태")
        else:
            q_cols  = ["datetime", "추천", "로봇 상태", "gender", "emotion"]
            show_q  = queue_df[[c for c in q_cols if c in queue_df.columns]].head(20)
            st.dataframe(show_q, use_container_width=True, height=300)

with rb2:
    st.markdown("#### 📋 최근 완료 / 오류 내역")
    if orders_df.empty:
        st.info("작업 이력이 없습니다.")
    else:
        done_df = orders_df[orders_df["로봇 상태"].isin(["완료", "오류"])].copy()

        if done_df.empty:
            st.info("완료된 작업이 없습니다.")
        else:
            def highlight_robot_status(row):
                """완료는 녹색, 오류는 붉은색 배경으로 강조합니다."""
                status = row.get("로봇 상태", "")
                if status == "오류":
                    return ["background-color: #3a1a1a"] * len(row)
                if status == "완료":
                    return ["background-color: #1a3a1a"] * len(row)
                return [""] * len(row)

            d_cols = ["datetime", "추천", "로봇 상태", "gender", "emotion"]
            show_d = done_df[[c for c in d_cols if c in done_df.columns]].head(30)
            st.dataframe(
                show_d.style.apply(highlight_robot_status, axis=1),
                use_container_width=True,
                height=300,
            )

st.divider()

# ── [섹션 4] 성능 통계 차트 ──────────────────────────────────────────────────
st.subheader("📈 성능 통계")

if orders_df.empty or "로봇 상태" not in orders_df.columns:
    st.info("로봇 통계를 표시할 데이터가 없습니다.")
else:
    rs1, rs2 = st.columns(2)

    with rs1:
        st.markdown("**작업 상태 분포**")
        status_counts = (
            orders_df["로봇 상태"]
            .value_counts()
            .rename_axis("상태")
            .reset_index(name="건수")
        )
        st.bar_chart(status_counts.set_index("상태"))

    with rs2:
        st.markdown("**시간대별 서빙 완료 건수**")
        if "datetime" in orders_df.columns:
            done_time = (
                orders_df[orders_df["로봇 상태"] == "완료"]
                .dropna(subset=["datetime"])
                .set_index("datetime")
                .resample("h")
                .size()
                .rename("완료 건수")
            )
            if not done_time.empty:
                st.line_chart(done_time)
            else:
                st.info("완료 데이터가 없습니다.")

# ── 자동 새로고침 ──────────────────────────────────────────────────────────────
auto_refresh_loop(auto_refresh)
