"""피드백 관리 — 사용자 문의사항/개선사항 확인 및 관리"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from utils.database import get_engine


def _query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """SQL 실행 후 DataFrame 반환."""
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params or {})


st.header("📬 피드백 관리")
st.caption("사용자 문의사항 · 개선사항 · 평가 확인")

# --- 요약 메트릭 ---
try:
    summary = _query("""
        SELECT
            count(*) as total,
            count(*) FILTER (WHERE created_at >= now() - interval '7 days') as week,
            count(*) FILTER (WHERE created_at >= now() - interval '1 day') as today,
            round(avg(rating)::numeric, 1) as avg_rating,
            count(DISTINCT category) as categories
        FROM user_feedback
    """)

    if not summary.empty:
        row = summary.iloc[0]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("전체 피드백", int(row["total"]))
        c2.metric("오늘", int(row["today"]))
        c3.metric("최근 7일", int(row["week"]))
        c4.metric("평균 평점", f"{'⭐ ' + str(row['avg_rating']) if row['avg_rating'] else 'N/A'}")
        c5.metric("카테고리 수", int(row["categories"]))
except Exception as e:
    st.error(f"요약 조회 실패: {e}")

st.divider()

# --- 필터 ---
col_filter1, col_filter2, col_filter3 = st.columns(3)

with col_filter1:
    categories = _query("SELECT DISTINCT category FROM user_feedback WHERE category IS NOT NULL ORDER BY category")
    cat_options = ["전체"] + categories["category"].tolist() if not categories.empty else ["전체"]
    selected_cat = st.selectbox("카테고리", cat_options)

with col_filter2:
    pages = _query("SELECT DISTINCT page FROM user_feedback ORDER BY page")
    page_options = ["전체"] + pages["page"].tolist() if not pages.empty else ["전체"]
    selected_page = st.selectbox("페이지", page_options)

with col_filter3:
    period = st.selectbox("기간", ["전체", "오늘", "최근 7일", "최근 30일"])

# 쿼리 구성
conditions = []
params = {}

if selected_cat != "전체":
    conditions.append("category = %(cat)s")
    params["cat"] = selected_cat

if selected_page != "전체":
    conditions.append("page = %(page)s")
    params["page"] = selected_page

if period == "오늘":
    conditions.append("created_at >= now() - interval '1 day'")
elif period == "최근 7일":
    conditions.append("created_at >= now() - interval '7 days'")
elif period == "최근 30일":
    conditions.append("created_at >= now() - interval '30 days'")

where = " AND ".join(conditions) if conditions else "1=1"

# --- 피드백 목록 ---
st.subheader("피드백 목록")

try:
    feedbacks = _query(f"""
        SELECT
            uf.id,
            uf.created_at,
            COALESCE(u.username, '비회원') as username,
            uf.page,
            uf.category,
            uf.rating,
            uf.comment,
            uf.device_info
        FROM user_feedback uf
        LEFT JOIN users u ON uf.user_id = u.id
        WHERE {where}
        ORDER BY uf.created_at DESC
        LIMIT 100
    """, params)

    if feedbacks.empty:
        st.info("해당 조건에 맞는 피드백이 없습니다.")
    else:
        # 평점을 별표로 표시
        feedbacks["평점"] = feedbacks["rating"].apply(
            lambda r: "⭐" * int(r) if pd.notna(r) else "-"
        )
        feedbacks["날짜"] = pd.to_datetime(feedbacks["created_at"]).dt.strftime("%m/%d %H:%M")

        display_df = feedbacks[["id", "날짜", "username", "page", "category", "평점", "comment"]].rename(
            columns={
                "id": "ID",
                "username": "사용자",
                "page": "페이지",
                "category": "카테고리",
                "comment": "내용",
            }
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn(width="small"),
                "날짜": st.column_config.TextColumn(width="small"),
                "사용자": st.column_config.TextColumn(width="small"),
                "페이지": st.column_config.TextColumn(width="small"),
                "카테고리": st.column_config.TextColumn(width="small"),
                "평점": st.column_config.TextColumn(width="small"),
                "내용": st.column_config.TextColumn(width="large"),
            },
        )

        st.caption(f"총 {len(feedbacks)}건 표시 (최신 100건)")

except Exception as e:
    st.error(f"피드백 조회 실패: {e}")

st.divider()

# --- 통계 ---
st.subheader("통계")

tab1, tab2 = st.tabs(["카테고리별 분포", "페이지별 분포"])

with tab1:
    try:
        cat_stats = _query("""
            SELECT
                COALESCE(category, '미분류') as category,
                count(*) as count,
                round(avg(rating)::numeric, 1) as avg_rating
            FROM user_feedback
            GROUP BY category
            ORDER BY count DESC
        """)
        if not cat_stats.empty:
            st.bar_chart(cat_stats.set_index("category")["count"])
            st.dataframe(cat_stats, hide_index=True, use_container_width=True)
        else:
            st.info("데이터 없음")
    except Exception as e:
        st.error(f"카테고리 통계 실패: {e}")

with tab2:
    try:
        page_stats = _query("""
            SELECT
                page,
                count(*) as count,
                round(avg(rating)::numeric, 1) as avg_rating
            FROM user_feedback
            GROUP BY page
            ORDER BY count DESC
        """)
        if not page_stats.empty:
            st.bar_chart(page_stats.set_index("page")["count"])
            st.dataframe(page_stats, hide_index=True, use_container_width=True)
        else:
            st.info("데이터 없음")
    except Exception as e:
        st.error(f"페이지 통계 실패: {e}")

# --- 일별 추이 ---
st.subheader("일별 피드백 추이")
try:
    daily = _query("""
        SELECT
            date_trunc('day', created_at)::date as date,
            count(*) as count
        FROM user_feedback
        WHERE created_at >= now() - interval '30 days'
        GROUP BY 1
        ORDER BY 1
    """)
    if not daily.empty:
        st.line_chart(daily.set_index("date")["count"])
    else:
        st.info("최근 30일간 피드백 없음")
except Exception as e:
    st.error(f"일별 추이 실패: {e}")
