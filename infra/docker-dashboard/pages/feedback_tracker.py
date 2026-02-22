"""피드백 트래커 -- 설문 통계 + 콘텐츠 반응 + 에러 스크린샷"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text

from utils.database import get_engine
from utils.ui_components import (
    inject_custom_css,
    render_section_header,
    render_metric_card,
)

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

inject_custom_css()


def _query(sql: str, params: dict | None = None) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params or {})


st.title("📊 피드백 트래커")
st.caption("설문 통계 · 콘텐츠 반응 · 에러 스크린샷")

tab_survey, tab_reactions, tab_screenshots = st.tabs(
    ["📋 설문 통계", "👍 콘텐츠 반응", "📸 에러 스크린샷"]
)

# ── 탭 1: 설문 통계 ──
with tab_survey:
    render_section_header("피드백 설문 통계", "📋")

    try:
        survey_summary = _query("""
            SELECT
                count(*) as total,
                count(*) FILTER (WHERE created_at >= now() - interval '7 days') as week,
                round(avg(overall_rating)::numeric, 1) as avg_overall,
                round(avg(ui_rating)::numeric, 1) as avg_ui,
                round(avg(feature_rating)::numeric, 1) as avg_feature,
                round(avg(content_rating)::numeric, 1) as avg_content,
                round(avg(speed_rating)::numeric, 1) as avg_speed
            FROM feedback_surveys
        """)

        if not survey_summary.empty:
            row = survey_summary.iloc[0]
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                render_metric_card("전체 설문", str(int(row["total"])), icon="📋")
            with c2:
                render_metric_card("최근 7일", str(int(row["week"])), icon="📆")
            with c3:
                render_metric_card("전체 만족도", str(row["avg_overall"] or "N/A"), icon="rating")
            with c4:
                render_metric_card("UI 평균", str(row["avg_ui"] or "N/A"), icon="🎨")
            with c5:
                render_metric_card("속도 평균", str(row["avg_speed"] or "N/A"), icon="⚡")

        st.divider()

        # 항목별 평균 점수 비교 차트
        render_section_header("항목별 평균 점수", "📊")
        if not survey_summary.empty:
            row = survey_summary.iloc[0]
            categories = ["UI/디자인", "기능 편의성", "학습 콘텐츠", "속도/안정성", "전체 만족도"]
            values = [
                float(row["avg_ui"] or 0),
                float(row["avg_feature"] or 0),
                float(row["avg_content"] or 0),
                float(row["avg_speed"] or 0),
                float(row["avg_overall"] or 0),
            ]

            if HAS_PLOTLY:
                fig = go.Figure(go.Bar(
                    x=categories,
                    y=values,
                    marker_color=["#FF6B00", "#FF8C3A", "#FFA462", "#FFC08A", "#FFD6B2"],
                    text=[f"{v:.1f}" for v in values],
                    textposition="outside",
                ))
                fig.update_layout(
                    title="항목별 평균 점수 (1~5점)",
                    yaxis_range=[0, 5.5],
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font=dict(color="#1A1A2E"),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                chart_df = pd.DataFrame({"항목": categories, "평균 점수": values})
                st.bar_chart(chart_df.set_index("항목"))

        st.divider()

        # 일별 설문 추이
        render_section_header("일별 설문 추이", "📈")
        daily_surveys = _query("""
            SELECT
                date_trunc('day', created_at)::date as date,
                count(*) as count,
                round(avg(overall_rating)::numeric, 1) as avg_rating
            FROM feedback_surveys
            WHERE created_at >= now() - interval '30 days'
            GROUP BY 1
            ORDER BY 1
        """)

        if not daily_surveys.empty:
            if HAS_PLOTLY:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=daily_surveys["date"], y=daily_surveys["count"],
                    mode="lines+markers", name="설문 수", line=dict(color="#FF6B00"),
                ))
                fig.add_trace(go.Scatter(
                    x=daily_surveys["date"], y=daily_surveys["avg_rating"],
                    mode="lines+markers", name="평균 평점", line=dict(color="#007BFF"),
                    yaxis="y2",
                ))
                fig.update_layout(
                    title="일별 설문 추이 (30일)",
                    yaxis=dict(title="설문 수"),
                    yaxis2=dict(title="평균 평점", overlaying="y", side="right", range=[0, 5.5]),
                    plot_bgcolor="white", paper_bgcolor="white",
                    font=dict(color="#1A1A2E"),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.line_chart(daily_surveys.set_index("date")["count"])
        else:
            st.info("최근 30일간 설문 데이터 없음")

        st.divider()

        # 최근 설문 코멘트
        render_section_header("최근 설문 코멘트", "💬")
        recent_surveys = _query("""
            SELECT
                to_char(created_at AT TIME ZONE 'Asia/Seoul', 'MM-DD HH24:MI') as 접수일시,
                overall_rating as 전체,
                ui_rating as UI,
                feature_rating as 기능,
                content_rating as 콘텐츠,
                speed_rating as 속도,
                COALESCE(comment, '-') as 코멘트,
                COALESCE(screenshot_url, '-') as 스크린샷
            FROM feedback_surveys
            ORDER BY created_at DESC
            LIMIT 50
        """)

        if not recent_surveys.empty:
            st.dataframe(recent_surveys, use_container_width=True, hide_index=True)
        else:
            st.info("설문 데이터 없음")

    except Exception as e:
        st.warning(f"설문 데이터 조회 실패: {e}")
        st.info("feedback_surveys 테이블이 존재하지 않을 수 있습니다. Alembic 마이그레이션을 실행해주세요.")


# ── 탭 2: 콘텐츠 반응 ──
with tab_reactions:
    render_section_header("콘텐츠 반응 분석", "👍")

    try:
        # 반응 요약
        reaction_summary = _query("""
            SELECT
                content_type,
                reaction,
                count(*) as cnt
            FROM content_reactions
            GROUP BY content_type, reaction
            ORDER BY content_type, reaction
        """)

        if not reaction_summary.empty:
            # 피벗 테이블
            pivot = reaction_summary.pivot_table(
                index="content_type", columns="reaction", values="cnt", fill_value=0
            ).reset_index()
            pivot.columns.name = None

            if "like" not in pivot.columns:
                pivot["like"] = 0
            if "dislike" not in pivot.columns:
                pivot["dislike"] = 0

            pivot["total"] = pivot["like"] + pivot["dislike"]
            pivot["like_ratio"] = (pivot["like"] / pivot["total"] * 100).round(1)

            st.dataframe(
                pivot.rename(columns={
                    "content_type": "콘텐츠 유형",
                    "like": "좋아요",
                    "dislike": "싫어요",
                    "total": "합계",
                    "like_ratio": "긍정률(%)",
                }),
                use_container_width=True,
                hide_index=True,
            )

            # 바 차트
            if HAS_PLOTLY:
                fig = go.Figure()
                fig.add_trace(go.Bar(name="👍 좋아요", x=pivot["content_type"], y=pivot["like"], marker_color="#28A745"))
                fig.add_trace(go.Bar(name="👎 싫어요", x=pivot["content_type"], y=pivot["dislike"], marker_color="#DC3545"))
                fig.update_layout(
                    barmode="group",
                    title="콘텐츠 유형별 반응",
                    plot_bgcolor="white", paper_bgcolor="white",
                    font=dict(color="#1A1A2E"),
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("콘텐츠 반응 데이터 없음")

        st.divider()

        # 최근 반응 로그
        render_section_header("최근 반응 로그", "📋")
        recent_reactions = _query("""
            SELECT
                to_char(created_at AT TIME ZONE 'Asia/Seoul', 'MM-DD HH24:MI') as 시각,
                content_type as 유형,
                content_id as 콘텐츠ID,
                reaction as 반응
            FROM content_reactions
            ORDER BY created_at DESC
            LIMIT 50
        """)

        if not recent_reactions.empty:
            st.dataframe(recent_reactions, use_container_width=True, hide_index=True)
        else:
            st.info("반응 데이터 없음")

    except Exception as e:
        st.warning(f"콘텐츠 반응 조회 실패: {e}")
        st.info("content_reactions 테이블이 존재하지 않을 수 있습니다.")


# ── 탭 3: 에러 스크린샷 ──
with tab_screenshots:
    render_section_header("에러 스크린샷", "📸")

    try:
        screenshots = _query("""
            SELECT
                to_char(created_at AT TIME ZONE 'Asia/Seoul', 'MM-DD HH24:MI') as 접수일시,
                overall_rating as 전체평점,
                COALESCE(comment, '-') as 코멘트,
                screenshot_url as 스크린샷URL
            FROM feedback_surveys
            WHERE screenshot_url IS NOT NULL AND screenshot_url != ''
            ORDER BY created_at DESC
            LIMIT 30
        """)

        if not screenshots.empty:
            st.metric("스크린샷 첨부 설문", len(screenshots))
            st.dataframe(screenshots, use_container_width=True, hide_index=True)
        else:
            st.info("스크린샷이 첨부된 설문이 없습니다.")

    except Exception as e:
        st.warning(f"스크린샷 조회 실패: {e}")
