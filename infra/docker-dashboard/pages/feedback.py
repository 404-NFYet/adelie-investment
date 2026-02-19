"""피드백 관리 -- 일반 피드백 / 브리핑 피드백 / 사용자 행동 분석"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from utils.database import get_engine, execute_query
from utils.ui_components import (
    inject_custom_css,
    render_section_header,
    render_metric_card,
)

# plotly 사용 가능 여부
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# CSS 주입
inject_custom_css()


def _query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """SQL 실행 후 DataFrame 반환."""
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params or {})


st.title("📬 피드백 관리")
st.caption("사용자 문의사항 / 브리핑 평가 / 사용자 행동 분석")

# ── 3탭 구조 ──────────────────────────────────────────────

tab_general, tab_briefing, tab_usage = st.tabs(
    ["💬 일반 피드백", "📰 브리핑 피드백", "📊 사용자 행동"]
)

# ── 탭 1: 일반 피드백 ────────────────────────────────────────

with tab_general:
    render_section_header("일반 피드백", "💬")

    # 요약 메트릭
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
            with c1:
                render_metric_card("전체 피드백", str(int(row["total"])), icon="📋")
            with c2:
                render_metric_card("오늘", str(int(row["today"])), icon="📅")
            with c3:
                render_metric_card("최근 7일", str(int(row["week"])), icon="📆")
            with c4:
                avg_r = str(row['avg_rating']) if row['avg_rating'] else 'N/A'
                render_metric_card("평균 평점", avg_r, icon="rating")
            with c5:
                render_metric_card("카테고리 수", str(int(row["categories"])), icon="📂")
    except Exception as e:
        st.error(f"요약 조회 실패: {e}")

    st.divider()

    # 필터
    col_filter1, col_filter2, col_filter3 = st.columns(3)

    with col_filter1:
        try:
            categories = _query("SELECT DISTINCT category FROM user_feedback WHERE category IS NOT NULL ORDER BY category")
            cat_options = ["전체"] + categories["category"].tolist() if not categories.empty else ["전체"]
        except Exception:
            cat_options = ["전체"]
        selected_cat = st.selectbox("카테고리", cat_options, key="fb_cat")

    with col_filter2:
        try:
            pages = _query("SELECT DISTINCT page FROM user_feedback ORDER BY page")
            page_options = ["전체"] + pages["page"].tolist() if not pages.empty else ["전체"]
        except Exception:
            page_options = ["전체"]
        selected_page = st.selectbox("페이지", page_options, key="fb_page")

    with col_filter3:
        period = st.selectbox("기간", ["전체", "오늘", "최근 7일", "최근 30일"], key="fb_period")

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
        conditions.append("uf.created_at >= now() - interval '1 day'")
    elif period == "최근 7일":
        conditions.append("uf.created_at >= now() - interval '7 days'")
    elif period == "최근 30일":
        conditions.append("uf.created_at >= now() - interval '30 days'")

    where = " AND ".join(conditions) if conditions else "1=1"

    # 피드백 목록
    render_section_header("피드백 목록", "📝")

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
                lambda r: "* " * int(r) if pd.notna(r) else "-"
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

            # CSV 내보내기 버튼
            csv = feedbacks.to_csv(index=False).encode("utf-8")
            st.download_button(
                "CSV 내보내기",
                csv,
                "feedback_export.csv",
                "text/csv",
                key="export_general_fb",
            )

    except Exception as e:
        st.error(f"피드백 조회 실패: {e}")

    st.divider()

    # 통계
    render_section_header("통계", "📊")

    stat_tab1, stat_tab2, stat_tab3 = st.tabs(["카테고리별 분포", "페이지별 분포", "일별 추이"])

    with stat_tab1:
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
                if HAS_PLOTLY:
                    fig = px.bar(
                        cat_stats,
                        x="category",
                        y="count",
                        title="카테고리별 피드백 수",
                        color="avg_rating",
                        color_continuous_scale=["#FF6B00", "#28A745"],
                        labels={"category": "카테고리", "count": "피드백 수", "avg_rating": "평균 평점"},
                    )
                    fig.update_layout(
                        plot_bgcolor="white",
                        paper_bgcolor="white",
                        font=dict(color="#1A1A2E"),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.bar_chart(cat_stats.set_index("category")["count"])
                st.dataframe(cat_stats, hide_index=True, use_container_width=True)
            else:
                st.info("데이터 없음")
        except Exception as e:
            st.error(f"카테고리 통계 실패: {e}")

    with stat_tab2:
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
                if HAS_PLOTLY:
                    fig = px.bar(
                        page_stats,
                        x="page",
                        y="count",
                        title="페이지별 피드백 수",
                        color="avg_rating",
                        color_continuous_scale=["#FF6B00", "#28A745"],
                        labels={"page": "페이지", "count": "피드백 수", "avg_rating": "평균 평점"},
                    )
                    fig.update_layout(
                        plot_bgcolor="white",
                        paper_bgcolor="white",
                        font=dict(color="#1A1A2E"),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.bar_chart(page_stats.set_index("page")["count"])
                st.dataframe(page_stats, hide_index=True, use_container_width=True)
            else:
                st.info("데이터 없음")
        except Exception as e:
            st.error(f"페이지 통계 실패: {e}")

    with stat_tab3:
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
                if HAS_PLOTLY:
                    fig = px.line(
                        daily,
                        x="date",
                        y="count",
                        title="일별 피드백 추이 (30일)",
                        labels={"date": "날짜", "count": "피드백 수"},
                        markers=True,
                    )
                    fig.update_traces(line_color="#FF6B00")
                    fig.update_layout(
                        plot_bgcolor="white",
                        paper_bgcolor="white",
                        font=dict(color="#1A1A2E"),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.line_chart(daily.set_index("date")["count"])
            else:
                st.info("최근 30일간 피드백 없음")
        except Exception as e:
            st.error(f"일별 추이 실패: {e}")


# ── 탭 2: 브리핑 피드백 ──────────────────────────────────────

with tab_briefing:
    render_section_header("브리핑 피드백", "📰")

    try:
        # 요약 메트릭
        bf_summary = _query("""
            SELECT
                count(*) as total,
                count(*) FILTER (WHERE created_at >= now() - interval '7 days') as week,
                count(*) FILTER (WHERE overall_rating = 'good') as good_count,
                count(DISTINCT briefing_id) as briefing_count
            FROM briefing_feedback
        """)

        if not bf_summary.empty:
            row = bf_summary.iloc[0]
            total = int(row["total"])
            good_pct = f"{int(row['good_count']) / total * 100:.0f}%" if total > 0 else "N/A"
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                render_metric_card("전체 평가", str(total), icon="📊")
            with c2:
                render_metric_card("최근 7일", str(int(row["week"])), icon="📆")
            with c3:
                render_metric_card("긍정 비율", good_pct, icon="👍")
            with c4:
                render_metric_card("평가된 브리핑", str(int(row["briefing_count"])), icon="📰")

        st.divider()

        # 최근 브리핑 피드백 목록
        render_section_header("최근 브리핑 피드백", "📝")

        bf_list = _query("""
            SELECT
                bf.id,
                bf.created_at,
                COALESCE(u.username, '비회원') as username,
                bf.briefing_id,
                bf.overall_rating,
                bf.favorite_section,
                db.briefing_date::text as briefing_title
            FROM briefing_feedback bf
            LEFT JOIN users u ON bf.user_id = u.id
            LEFT JOIN daily_briefings db ON bf.briefing_id = db.id
            ORDER BY bf.created_at DESC
            LIMIT 100
        """)

        if not bf_list.empty:
            bf_list["날짜"] = pd.to_datetime(bf_list["created_at"]).dt.strftime("%m/%d %H:%M")
            rating_emoji = {"good": "👍", "neutral": "😐", "bad": "👎"}
            bf_list["평가"] = bf_list["overall_rating"].map(rating_emoji).fillna("-")

            display_df = bf_list[["id", "날짜", "username", "briefing_title", "평가", "favorite_section"]].rename(
                columns={
                    "id": "ID",
                    "username": "사용자",
                    "briefing_title": "브리핑 날짜",
                    "favorite_section": "선호 섹션",
                }
            )
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            st.caption(f"총 {len(bf_list)}건 (최신 100건)")

            # CSV 내보내기
            csv = bf_list.to_csv(index=False).encode("utf-8")
            st.download_button(
                "CSV 내보내기",
                csv,
                "briefing_feedback_export.csv",
                "text/csv",
                key="export_briefing_fb",
            )
        else:
            st.info("브리핑 피드백이 없습니다.")

        st.divider()

        # 브리핑별 평가 분포
        render_section_header("브리핑별 평가 분포", "📊")
        bf_stats = _query("""
            SELECT
                db.briefing_date::text as briefing_title,
                count(*) as feedback_count,
                count(*) FILTER (WHERE bf.overall_rating = 'good') as good,
                count(*) FILTER (WHERE bf.overall_rating = 'neutral') as neutral,
                count(*) FILTER (WHERE bf.overall_rating = 'bad') as bad
            FROM briefing_feedback bf
            JOIN daily_briefings db ON bf.briefing_id = db.id
            GROUP BY db.id, db.briefing_date
            ORDER BY db.briefing_date DESC
            LIMIT 20
        """)

        if not bf_stats.empty:
            if HAS_PLOTLY:
                fig = go.Figure()
                fig.add_trace(go.Bar(name="👍 Good", x=bf_stats["briefing_title"], y=bf_stats["good"], marker_color="#28A745"))
                fig.add_trace(go.Bar(name="😐 Neutral", x=bf_stats["briefing_title"], y=bf_stats["neutral"], marker_color="#FFC107"))
                fig.add_trace(go.Bar(name="👎 Bad", x=bf_stats["briefing_title"], y=bf_stats["bad"], marker_color="#DC3545"))
                fig.update_layout(
                    barmode="stack",
                    title="브리핑별 평가 분포",
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font=dict(color="#1A1A2E"),
                    xaxis_tickangle=-45,
                    xaxis_title="브리핑 날짜",
                    yaxis_title="평가 수",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(bf_stats, use_container_width=True, hide_index=True)
        else:
            st.info("데이터 없음")

    except Exception as e:
        st.error(f"브리핑 피드백 조회 실패: {e}")
        st.info("briefing_feedback 테이블이 존재하지 않을 수 있습니다.")


# ── 탭 3: 사용자 행동 ────────────────────────────────────────

with tab_usage:
    render_section_header("사용자 행동 분석", "📊")

    try:
        # usage_events 테이블 조회
        ue_summary = _query("""
            SELECT
                count(*) as total_events,
                count(DISTINCT user_id) as unique_users,
                count(DISTINCT event_type) as event_types,
                count(*) FILTER (WHERE created_at >= now() - interval '1 day') as today_events
            FROM usage_events
        """)

        if not ue_summary.empty:
            row = ue_summary.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                render_metric_card("전체 이벤트", str(int(row["total_events"])), icon="📈")
            with c2:
                render_metric_card("오늘 이벤트", str(int(row["today_events"])), icon="📅")
            with c3:
                render_metric_card("고유 사용자", str(int(row["unique_users"])), icon="👤")
            with c4:
                render_metric_card("이벤트 종류", str(int(row["event_types"])), icon="🏷️")

        st.divider()

        # 이벤트 유형별 분포
        render_section_header("이벤트 유형별 분포", "🏷️")
        event_stats = _query("""
            SELECT
                event_type,
                count(*) as count,
                count(DISTINCT user_id) as unique_users
            FROM usage_events
            GROUP BY event_type
            ORDER BY count DESC
            LIMIT 20
        """)

        if not event_stats.empty:
            if HAS_PLOTLY:
                fig = px.bar(
                    event_stats,
                    x="event_type",
                    y="count",
                    title="이벤트 유형별 발생 횟수",
                    color="unique_users",
                    labels={"event_type": "이벤트", "count": "발생 횟수", "unique_users": "고유 사용자"},
                    color_continuous_scale=["#E9ECEF", "#FF6B00"],
                )
                fig.update_layout(
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font=dict(color="#1A1A2E"),
                    xaxis_tickangle=-45,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.bar_chart(event_stats.set_index("event_type")["count"])
            st.dataframe(event_stats, use_container_width=True, hide_index=True)
        else:
            st.info("이벤트 데이터 없음")

        st.divider()

        # 일별 이벤트 추이
        render_section_header("일별 이벤트 추이", "📈")
        daily_events = _query("""
            SELECT
                date_trunc('day', created_at)::date as date,
                count(*) as count,
                count(DISTINCT user_id) as unique_users
            FROM usage_events
            WHERE created_at >= now() - interval '30 days'
            GROUP BY 1
            ORDER BY 1
        """)

        if not daily_events.empty:
            if HAS_PLOTLY:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=daily_events["date"],
                    y=daily_events["count"],
                    mode="lines+markers",
                    name="이벤트 수",
                    line=dict(color="#FF6B00"),
                ))
                fig.add_trace(go.Scatter(
                    x=daily_events["date"],
                    y=daily_events["unique_users"],
                    mode="lines+markers",
                    name="고유 사용자",
                    line=dict(color="#007BFF"),
                ))
                fig.update_layout(
                    title="일별 이벤트 추이 (30일)",
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font=dict(color="#1A1A2E"),
                    xaxis_title="날짜",
                    yaxis_title="횟수",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.line_chart(daily_events.set_index("date")[["count", "unique_users"]])
        else:
            st.info("최근 30일간 이벤트 없음")

        st.divider()

        # 최근 이벤트 로그
        render_section_header("최근 이벤트 로그", "📋")
        recent_events = _query("""
            SELECT
                ue.created_at,
                COALESCE(u.username, '비회원') as username,
                ue.event_type,
                ue.event_data::text as event_data
            FROM usage_events ue
            LEFT JOIN users u ON ue.user_id = u.id
            ORDER BY ue.created_at DESC
            LIMIT 50
        """)

        if not recent_events.empty:
            recent_events["시각"] = pd.to_datetime(recent_events["created_at"]).dt.strftime("%m/%d %H:%M:%S")
            display_df = recent_events[["시각", "username", "event_type", "event_data"]].rename(
                columns={
                    "username": "사용자",
                    "event_type": "이벤트",
                    "event_data": "데이터",
                }
            )
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # CSV 내보내기
            csv = recent_events.to_csv(index=False).encode("utf-8")
            st.download_button(
                "CSV 내보내기",
                csv,
                "usage_events_export.csv",
                "text/csv",
                key="export_usage",
            )
        else:
            st.info("이벤트 로그 없음")

    except Exception as e:
        st.error(f"사용자 행동 데이터 조회 실패: {e}")
        st.info("usage_events 테이블이 존재하지 않을 수 있습니다.")
