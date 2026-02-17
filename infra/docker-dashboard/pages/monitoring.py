"""시스템 모니터링 -- Prometheus 연동 + Grafana iframe + 게이지 차트"""

import streamlit as st
import requests
import pandas as pd

from config import SERVERS, DEPLOY_SERVER, PROMETHEUS_URL, GRAFANA_URL
from utils.ui_components import (
    inject_custom_css,
    render_section_header,
    render_metric_card,
    render_gauge_chart,
    render_status_badge,
)
from utils.docker_cmd import docker_stats

# plotly 사용 가능 여부
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# CSS 주입
inject_custom_css()


def prom_query(query: str) -> list[dict]:
    """Prometheus instant query 실행"""
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "success":
            return data["data"]["result"]
    except Exception:
        pass
    return []


def get_metric_value(results: list[dict], instance_filter: str) -> str:
    """Prometheus 결과에서 특정 인스턴스의 값 추출"""
    for r in results:
        instance = r["metric"].get("instance", "")
        if instance_filter in instance:
            return r["value"][1]
    return "N/A"


st.title("📊 모니터링")

# ── 자동 새로고침 옵션 ────────────────────────────────────────

col_refresh1, col_refresh2 = st.columns([3, 1])
with col_refresh2:
    auto_refresh = st.checkbox("30초 자동 새로고침", key="auto_refresh_monitoring")

if auto_refresh:
    st.markdown("""
    <meta http-equiv="refresh" content="30">
    <div style="text-align:right; font-size:12px; color:#6C757D;">
        30초마다 자동 새로고침됩니다.
    </div>
    """, unsafe_allow_html=True)

tab_overview, tab_containers, tab_grafana = st.tabs(
    ["🖥️ 서버 현황", "🐳 컨테이너 리소스", "📈 Grafana 대시보드"]
)

# ── 서버 현황 ─────────────────────────────────────────────

with tab_overview:
    render_section_header("전체 서버 리소스", "🖥️")

    # Prometheus에서 CPU, 메모리, 디스크 조회
    cpu_results = prom_query('100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)')
    mem_results = prom_query('(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100')
    disk_results = prom_query('(1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100')

    all_servers = {**SERVERS, "deploy-test": DEPLOY_SERVER}

    rows = []
    alerts = []

    # 게이지 차트로 표시
    for name, info in all_servers.items():
        host = info["host"]
        display_name = name if name == "deploy-test" else name

        cpu = get_metric_value(cpu_results, host)
        mem = get_metric_value(mem_results, host)
        disk = get_metric_value(disk_results, host)

        cpu_val = float(cpu) if cpu != "N/A" else 0
        mem_val = float(mem) if mem != "N/A" else 0
        disk_val = float(disk) if disk != "N/A" else 0

        rows.append({
            "서버": display_name,
            "IP": host,
            "CPU (%)": cpu_val,
            "메모리 (%)": mem_val,
            "디스크 (%)": disk_val,
            "cpu_raw": cpu,
            "mem_raw": mem,
            "disk_raw": disk,
        })

        # 알림 조건
        if disk_val > 80:
            alerts.append(f"{display_name}: 디스크 {disk_val:.0f}% 사용 (80% 초과)")
        if mem_val > 90:
            alerts.append(f"{display_name}: 메모리 {mem_val:.0f}% 사용 (90% 초과)")

    if rows:
        # 게이지 차트 표시
        for row in rows:
            st.markdown(f"**{row['서버']}** ({row['IP']})")
            gcol1, gcol2, gcol3 = st.columns(3)
            with gcol1:
                if row["cpu_raw"] != "N/A":
                    render_gauge_chart("CPU", row["CPU (%)"])
                else:
                    render_metric_card("CPU", "N/A", icon="cpu")
            with gcol2:
                if row["mem_raw"] != "N/A":
                    render_gauge_chart("메모리", row["메모리 (%)"])
                else:
                    render_metric_card("메모리", "N/A", icon="mem")
            with gcol3:
                if row["disk_raw"] != "N/A":
                    render_gauge_chart("디스크", row["디스크 (%)"])
                else:
                    render_metric_card("디스크", "N/A", icon="disk")
            st.divider()

        # 테이블로도 보기
        with st.expander("테이블로 보기"):
            table_df = pd.DataFrame([{
                "서버": r["서버"],
                "IP": r["IP"],
                "CPU (%)": f"{r['CPU (%)']:.1f}" if r["cpu_raw"] != "N/A" else "N/A",
                "메모리 (%)": f"{r['메모리 (%)']:.1f}" if r["mem_raw"] != "N/A" else "N/A",
                "디스크 (%)": f"{r['디스크 (%)']:.1f}" if r["disk_raw"] != "N/A" else "N/A",
            } for r in rows])
            st.dataframe(table_df, use_container_width=True, hide_index=True)
    else:
        st.warning("Prometheus 데이터를 가져올 수 없습니다.")

    # 알림
    if alerts:
        render_section_header("알림", "🚨")
        for alert in alerts:
            st.warning(alert)

# ── 컨테이너 리소스 ──────────────────────────────────────────

with tab_containers:
    render_section_header("컨테이너 리소스 (deploy-test)", "🐳")

    container_cpu = prom_query(
        f'rate(container_cpu_usage_seconds_total{{instance=~".*{DEPLOY_SERVER["host"]}.*",name!=""}}[5m]) * 100'
    )
    container_mem = prom_query(
        f'container_memory_usage_bytes{{instance=~".*{DEPLOY_SERVER["host"]}.*",name!=""}}'
    )

    container_rows = []
    seen_names = set()
    for r in container_cpu:
        name = r["metric"].get("name", "unknown")
        if name in seen_names:
            continue
        seen_names.add(name)

        cpu_val = float(r["value"][1])
        # 매칭되는 메모리 찾기
        mem_val = 0
        for mr in container_mem:
            if mr["metric"].get("name") == name:
                mem_val = float(mr["value"][1]) / (1024 * 1024)  # MB
                break

        container_rows.append({
            "컨테이너": name,
            "CPU (%)": cpu_val,
            "메모리 (MB)": mem_val,
        })

    if container_rows:
        # Plotly 바 차트
        if HAS_PLOTLY:
            df = pd.DataFrame(container_rows)

            # CPU 바 차트
            fig_cpu = px.bar(
                df,
                x="컨테이너",
                y="CPU (%)",
                title="컨테이너별 CPU 사용률",
                color="CPU (%)",
                color_continuous_scale=["#28A745", "#FFC107", "#DC3545"],
            )
            fig_cpu.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white",
                font=dict(color="#1A1A2E"),
                showlegend=False,
            )
            st.plotly_chart(fig_cpu, use_container_width=True)

            # 메모리 바 차트
            fig_mem = px.bar(
                df,
                x="컨테이너",
                y="메모리 (MB)",
                title="컨테이너별 메모리 사용량",
                color="메모리 (MB)",
                color_continuous_scale=["#007BFF", "#6610F2", "#DC3545"],
            )
            fig_mem.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white",
                font=dict(color="#1A1A2E"),
                showlegend=False,
            )
            st.plotly_chart(fig_mem, use_container_width=True)
        else:
            # Streamlit 기본 차트
            df = pd.DataFrame(container_rows)
            st.bar_chart(df.set_index("컨테이너")["CPU (%)"])
            st.bar_chart(df.set_index("컨테이너")["메모리 (MB)"])

        # 테이블
        with st.expander("상세 테이블"):
            display_df = pd.DataFrame([{
                "컨테이너": r["컨테이너"],
                "CPU (%)": f"{r['CPU (%)']:.2f}",
                "메모리 (MB)": f"{r['메모리 (MB)']:.0f}",
            } for r in container_rows])
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("cAdvisor 데이터 없음 -- Prometheus에 cAdvisor가 연결되어 있는지 확인하세요.")

    # SSH 기반 docker stats (fallback)
    st.divider()
    render_section_header("Docker Stats (SSH 직접 조회)", "🔧")
    stats = docker_stats(DEPLOY_SERVER["host"])
    if stats:
        st.dataframe(pd.DataFrame(stats), use_container_width=True, hide_index=True)
    else:
        st.info("docker stats 조회 불가")

# ── Grafana 대시보드 ──────────────────────────────────────

with tab_grafana:
    render_section_header("Grafana 대시보드", "📈")
    st.caption(f"외부 URL: {GRAFANA_URL}")

    st.markdown(f"[Grafana 새 탭에서 열기]({GRAFANA_URL})")

    st.info(
        "Grafana 대시보드는 Nginx Basic Auth로 보호되어 있어 iframe 임베딩이 제한될 수 있습니다. "
        "위 링크를 사용해 새 탭에서 열어주세요."
    )

    # iframe 시도 (Basic Auth가 걸려있으면 인증 팝업이 뜸)
    grafana_embed = f"""
    <iframe
        src="{GRAFANA_URL}/d/node-exporter-full/node-exporter-full?orgId=1&refresh=30s&kiosk"
        width="100%"
        height="600"
        frameborder="0"
        style="border-radius: 8px;"
    ></iframe>
    """
    st.components.v1.html(grafana_embed, height=620)
