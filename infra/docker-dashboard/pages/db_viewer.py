"""DB 테이블 브라우저 + 비즈니스 대시보드 + 파이프라인 상태"""

import streamlit as st
import pandas as pd

from config import DEPLOY_SERVER, PROJECT_DIR
from utils.database import execute_query, get_tables, get_table_schema, get_table_preview
from utils.ssh import run_cmd
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

HOST = DEPLOY_SERVER["host"]

# CSS 주입
inject_custom_css()

st.title("🗄️ DB 뷰어")

tab_browser, tab_pipeline, tab_business, tab_manage = st.tabs(
    ["📋 테이블 브라우저", "🔄 파이프라인 상태", "📊 비즈니스 대시보드", "⚠️ 데이터 관리"]
)

# ── 테이블 브라우저 ───────────────────────────────────────

with tab_browser:
    render_section_header("테이블 목록", "📋")

    try:
        tables_df = get_tables()
    except Exception as e:
        st.error(f"DB 연결 실패: {e}")
        st.stop()

    if tables_df.empty:
        st.warning("테이블 없음")
    else:
        st.dataframe(
            tables_df,
            use_container_width=True,
            column_config={
                "table_name": st.column_config.TextColumn("테이블명"),
                "row_count": st.column_config.NumberColumn("행 수", format="%d"),
            },
        )

        selected_table = st.selectbox(
            "테이블 선택", tables_df["table_name"].tolist(), key="table_select"
        )

        if selected_table:
            # 스키마 표시
            st.markdown(f"**`{selected_table}` 스키마**")
            try:
                schema_df = get_table_schema(selected_table)
                st.dataframe(schema_df, use_container_width=True)
            except Exception as e:
                st.error(f"스키마 조회 실패: {e}")

            # 데이터 미리보기
            st.markdown(f"**`{selected_table}` 데이터 미리보기**")
            limit = st.slider("행 수", 10, 200, 50, key="preview_limit")
            try:
                preview_df = get_table_preview(selected_table, limit)
                st.dataframe(preview_df, use_container_width=True)

                # CSV 다운로드
                csv = preview_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "CSV 다운로드",
                    csv,
                    f"{selected_table}.csv",
                    "text/csv",
                )
            except Exception as e:
                st.error(f"데이터 조회 실패: {e}")

    # 커스텀 SQL 쿼리
    st.divider()
    render_section_header("커스텀 SQL 쿼리", "🔍")
    st.caption("SELECT 쿼리만 실행 가능합니다.")

    sql = st.text_area("SQL 입력", height=100, placeholder="SELECT * FROM users LIMIT 10")
    if st.button("실행", key="run_sql"):
        if sql.strip():
            try:
                result_df = execute_query(sql)
                st.dataframe(result_df, use_container_width=True)
                st.caption(f"{len(result_df)}행 반환")

                csv = result_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "결과 CSV 다운로드",
                    csv,
                    "query_result.csv",
                    "text/csv",
                    key="download_query",
                )
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"쿼리 실행 실패: {e}")

# ── 파이프라인 상태 (H-6 신규) ──────────────────────────────

with tab_pipeline:
    render_section_header("파이프라인 상태", "🔄")

    # 최근 브리핑 날짜 / 성공 여부
    col1, col2, col3, col4 = st.columns(4)

    try:
        with col1:
            df = execute_query("""
                SELECT MAX(market_date) as last_date
                FROM daily_briefings
            """)
            last_date = df["last_date"].iloc[0] if not df.empty and df["last_date"].iloc[0] else "N/A"
            render_metric_card("최근 브리핑 날짜", str(last_date), icon="📅")

        with col2:
            df = execute_query("""
                SELECT COUNT(*) as cnt
                FROM daily_briefings
                WHERE created_at::date = CURRENT_DATE
            """)
            today_count = int(df["cnt"].iloc[0]) if not df.empty else 0
            status = "성공" if today_count > 0 else "미실행"
            render_metric_card("오늘 파이프라인", status, delta=f"{today_count}건", icon="🔄")

        with col3:
            df = execute_query("""
                SELECT COUNT(DISTINCT market_date) as dates
                FROM daily_briefings
            """)
            total_dates = int(df["dates"].iloc[0]) if not df.empty else 0
            render_metric_card("총 실행 일수", str(total_dates), icon="📊")

        with col4:
            df = execute_query("""
                SELECT COUNT(*) as cnt
                FROM daily_briefings
                WHERE created_at >= now() - interval '7 days'
            """)
            week_count = int(df["cnt"].iloc[0]) if not df.empty else 0
            render_metric_card("최근 7일 브리핑", f"{week_count}건", icon="📈")

    except Exception as e:
        st.error(f"파이프라인 상태 조회 실패: {e}")

    st.divider()

    # 파이프라인 실행 기록 (날짜별)
    render_section_header("일별 파이프라인 실행 기록", "📜")
    try:
        df = execute_query("""
            SELECT
                market_date,
                COUNT(*) as briefing_count,
                COUNT(DISTINCT id) as unique_briefings,
                MIN(created_at) as first_created,
                MAX(created_at) as last_created
            FROM daily_briefings
            GROUP BY market_date
            ORDER BY market_date DESC
            LIMIT 14
        """)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)

            # 차트
            if HAS_PLOTLY:
                chart_df = df.sort_values("market_date")
                fig = px.bar(
                    chart_df,
                    x="market_date",
                    y="briefing_count",
                    title="일별 브리핑 생성 수",
                    labels={"market_date": "날짜", "briefing_count": "브리핑 수"},
                    color_discrete_sequence=["#FF6B00"],
                )
                fig.update_layout(
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font=dict(color="#1A1A2E"),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                chart_df = df.sort_values("market_date").set_index("market_date")
                st.bar_chart(chart_df["briefing_count"])
        else:
            st.info("데이터 없음")
    except Exception as e:
        st.warning(f"조회 실패: {e}")

    # 키워드 현황
    st.divider()
    render_section_header("최근 키워드 현황", "🔑")
    try:
        df = execute_query("""
            SELECT display_date, COUNT(*) as keyword_count
            FROM keywords
            WHERE display_date IS NOT NULL
            GROUP BY display_date
            ORDER BY display_date DESC
            LIMIT 14
        """)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("키워드 데이터 없음")
    except Exception as e:
        st.warning(f"키워드 조회 실패: {e}")

# ── 비즈니스 대시보드 ────────────────────────────────────

with tab_business:
    render_section_header("비즈니스 현황", "📊")

    col1, col2, col3, col4 = st.columns(4)

    try:
        # 오늘의 브리핑 수
        with col1:
            try:
                df = execute_query(
                    "SELECT COUNT(*) as cnt FROM daily_briefings WHERE created_at::date = CURRENT_DATE"
                )
                render_metric_card("오늘 브리핑", f"{df['cnt'].iloc[0]}건", icon="📰")
            except Exception:
                render_metric_card("오늘 브리핑", "N/A", icon="📰")

        # 전체 브리핑 수
        with col2:
            try:
                df = execute_query("SELECT COUNT(*) as cnt FROM daily_briefings")
                render_metric_card("전체 브리핑", f"{df['cnt'].iloc[0]}건", icon="📚")
            except Exception:
                render_metric_card("전체 브리핑", "N/A", icon="📚")

        # 케이스 수
        with col3:
            try:
                df = execute_query("SELECT COUNT(*) as cnt FROM historical_cases")
                render_metric_card("역사적 케이스", f"{df['cnt'].iloc[0]}건", icon="📖")
            except Exception:
                render_metric_card("역사적 케이스", "N/A", icon="📖")

        # 사용자 수
        with col4:
            try:
                df = execute_query("SELECT COUNT(*) as cnt FROM users")
                render_metric_card("가입 사용자", f"{df['cnt'].iloc[0]}명", icon="👤")
            except Exception:
                render_metric_card("가입 사용자", "N/A", icon="👤")

    except Exception as e:
        st.error(f"대시보드 데이터 조회 실패: {e}")

    st.divider()

    # 최근 브리핑
    render_section_header("최근 브리핑", "📰")
    try:
        df = execute_query("""
            SELECT id, market_date, title, created_at
            FROM daily_briefings
            ORDER BY created_at DESC
            LIMIT 10
        """)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("브리핑 데이터 없음")
    except Exception as e:
        st.warning(f"브리핑 조회 실패: {e}")

    # 키워드 현황
    render_section_header("최근 키워드", "🔑")
    try:
        df = execute_query("""
            SELECT id, keyword, category, display_date, created_at
            FROM keywords
            ORDER BY created_at DESC
            LIMIT 20
        """)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)

            # 카테고리별 분포 차트
            if HAS_PLOTLY:
                cat_df = df.groupby("category").size().reset_index(name="count")
                fig = px.pie(
                    cat_df,
                    values="count",
                    names="category",
                    title="키워드 카테고리 분포",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig.update_layout(
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font=dict(color="#1A1A2E"),
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("키워드 데이터 없음")
    except Exception as e:
        st.warning(f"키워드 조회 실패: {e}")

# ── 데이터 관리 ──────────────────────────────────────────

with tab_manage:
    render_section_header("데이터 관리", "⚠️")
    st.warning("주의: 아래 작업은 deploy-test 서버의 데이터에 영향을 줍니다.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**콘텐츠 초기화**")
        st.caption("사용자/스키마는 유지하고 콘텐츠 데이터만 삭제합니다.")
        if st.button("reset_db --content-only", type="secondary"):
            with st.spinner("reset_db 실행 중 ..."):
                result = run_cmd(
                    HOST,
                    f"cd {PROJECT_DIR} && .venv/bin/python database/scripts/reset_db.py --content-only 2>&1",
                    timeout=60,
                )
            if result.exit_code == 0:
                st.success("콘텐츠 초기화 완료")
                st.code(result.stdout[:500])
            else:
                st.error(result.stderr[:500] or result.stdout[:500])

    with col2:
        st.markdown("**파이프라인 재실행**")
        mode = st.radio("모드", ["mock", "live"], key="pipeline_mode", horizontal=True)
        if st.button("파이프라인 실행", type="primary"):
            extra = "--market KR" if mode == "live" else ""
            with st.spinner(f"파이프라인 ({mode}) 실행 중 ..."):
                result = run_cmd(
                    HOST,
                    f"cd {PROJECT_DIR} && .venv/bin/python -m datapipeline.run --backend {mode} {extra} 2>&1",
                    timeout=600,
                )
            if result.exit_code == 0:
                st.success("파이프라인 실행 완료")
                st.code(result.stdout[-1000:])
            else:
                st.error(result.stderr[:500] or result.stdout[:500])
