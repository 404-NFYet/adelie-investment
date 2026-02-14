"""DB 테이블 브라우저 + 비즈니스 대시보드"""

import streamlit as st
import pandas as pd

from config import DEPLOY_SERVER, PROJECT_DIR
from utils.database import execute_query, get_tables, get_table_schema, get_table_preview
from utils.ssh import run_cmd

HOST = DEPLOY_SERVER["host"]

st.title("🗄️ DB 뷰어")

tab_browser, tab_business, tab_manage = st.tabs(["테이블 브라우저", "비즈니스 대시보드", "데이터 관리"])

# ── 테이블 브라우저 ───────────────────────────────────────

with tab_browser:
    st.subheader("테이블 목록")

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
            width="stretch",
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
                st.dataframe(schema_df, width="stretch")
            except Exception as e:
                st.error(f"스키마 조회 실패: {e}")

            # 데이터 미리보기
            st.markdown(f"**`{selected_table}` 데이터 미리보기**")
            limit = st.slider("행 수", 10, 200, 50, key="preview_limit")
            try:
                preview_df = get_table_preview(selected_table, limit)
                st.dataframe(preview_df, width="stretch")

                # CSV 다운로드
                csv = preview_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📥 CSV 다운로드",
                    csv,
                    f"{selected_table}.csv",
                    "text/csv",
                )
            except Exception as e:
                st.error(f"데이터 조회 실패: {e}")

    # 커스텀 SQL 쿼리
    st.divider()
    st.subheader("🔍 커스텀 SQL 쿼리")
    st.caption("SELECT 쿼리만 실행 가능합니다.")

    sql = st.text_area("SQL 입력", height=100, placeholder="SELECT * FROM users LIMIT 10")
    if st.button("실행", key="run_sql"):
        if sql.strip():
            try:
                result_df = execute_query(sql)
                st.dataframe(result_df, width="stretch")
                st.caption(f"{len(result_df)}행 반환")

                csv = result_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📥 결과 CSV 다운로드",
                    csv,
                    "query_result.csv",
                    "text/csv",
                    key="download_query",
                )
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"쿼리 실행 실패: {e}")

# ── 비즈니스 대시보드 ────────────────────────────────────

with tab_business:
    st.subheader("📊 비즈니스 현황")

    col1, col2, col3, col4 = st.columns(4)

    try:
        # 오늘의 브리핑 수
        with col1:
            try:
                df = execute_query(
                    "SELECT COUNT(*) as cnt FROM daily_briefings WHERE created_at::date = CURRENT_DATE"
                )
                st.metric("오늘 브리핑", f"{df['cnt'].iloc[0]}건")
            except Exception:
                st.metric("오늘 브리핑", "N/A")

        # 전체 브리핑 수
        with col2:
            try:
                df = execute_query("SELECT COUNT(*) as cnt FROM daily_briefings")
                st.metric("전체 브리핑", f"{df['cnt'].iloc[0]}건")
            except Exception:
                st.metric("전체 브리핑", "N/A")

        # 케이스 수
        with col3:
            try:
                df = execute_query("SELECT COUNT(*) as cnt FROM historical_cases")
                st.metric("역사적 케이스", f"{df['cnt'].iloc[0]}건")
            except Exception:
                st.metric("역사적 케이스", "N/A")

        # 사용자 수
        with col4:
            try:
                df = execute_query("SELECT COUNT(*) as cnt FROM users")
                st.metric("가입 사용자", f"{df['cnt'].iloc[0]}명")
            except Exception:
                st.metric("가입 사용자", "N/A")

    except Exception as e:
        st.error(f"대시보드 데이터 조회 실패: {e}")

    st.divider()

    # 최근 브리핑
    st.markdown("**최근 브리핑**")
    try:
        df = execute_query("""
            SELECT id, market_date, title, created_at
            FROM daily_briefings
            ORDER BY created_at DESC
            LIMIT 10
        """)
        if not df.empty:
            st.dataframe(df, width="stretch")
        else:
            st.info("브리핑 데이터 없음")
    except Exception as e:
        st.warning(f"브리핑 조회 실패: {e}")

    # 키워드 현황
    st.markdown("**최근 키워드**")
    try:
        df = execute_query("""
            SELECT id, keyword, category, display_date, created_at
            FROM keywords
            ORDER BY created_at DESC
            LIMIT 20
        """)
        if not df.empty:
            st.dataframe(df, width="stretch")
        else:
            st.info("키워드 데이터 없음")
    except Exception as e:
        st.warning(f"키워드 조회 실패: {e}")

    # 파이프라인 실행 기록 (최근 브리핑 날짜별)
    st.markdown("**파이프라인 실행 기록 (브리핑 날짜별)**")
    try:
        df = execute_query("""
            SELECT market_date, COUNT(*) as briefing_count, MIN(created_at) as first_created
            FROM daily_briefings
            GROUP BY market_date
            ORDER BY market_date DESC
            LIMIT 14
        """)
        if not df.empty:
            st.dataframe(df, width="stretch")
        else:
            st.info("데이터 없음")
    except Exception as e:
        st.warning(f"조회 실패: {e}")

# ── 데이터 관리 ──────────────────────────────────────────

with tab_manage:
    st.subheader("⚠️ 데이터 관리")
    st.warning("주의: 아래 작업은 deploy-test 서버의 데이터에 영향을 줍니다.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**콘텐츠 초기화**")
        st.caption("사용자/스키마는 유지하고 콘텐츠 데이터만 삭제합니다.")
        if st.button("🗑️ reset_db --content-only", type="secondary"):
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
        if st.button("▶️ 파이프라인 실행", type="primary"):
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
