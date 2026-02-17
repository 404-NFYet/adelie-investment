"""시스템 모니터링 — Prometheus 연동 + Grafana iframe"""

import streamlit as st
import requests
import pandas as pd

from config import SERVERS, DEPLOY_SERVER, PROMETHEUS_URL, GRAFANA_URL


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

tab_overview, tab_grafana = st.tabs(["서버 현황", "Grafana 대시보드"])

# ── 서버 현황 ─────────────────────────────────────────────

with tab_overview:
    st.subheader("전체 서버 리소스")

    # Prometheus에서 CPU, 메모리, 디스크 조회
    cpu_results = prom_query('100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)')
    mem_results = prom_query('(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100')
    disk_results = prom_query('(1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100')

    all_servers = {**SERVERS, "deploy-test": DEPLOY_SERVER}

    rows = []
    alerts = []

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
            "CPU (%)": f"{cpu_val:.1f}" if cpu != "N/A" else "N/A",
            "메모리 (%)": f"{mem_val:.1f}" if mem != "N/A" else "N/A",
            "디스크 (%)": f"{disk_val:.1f}" if disk != "N/A" else "N/A",
        })

        # 알림 조건
        if disk_val > 80:
            alerts.append(f"⚠️ {display_name}: 디스크 {disk_val:.0f}% 사용 (80% 초과)")
        if mem_val > 90:
            alerts.append(f"⚠️ {display_name}: 메모리 {mem_val:.0f}% 사용 (90% 초과)")

    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.warning("Prometheus 데이터를 가져올 수 없습니다.")

    # 알림
    if alerts:
        st.divider()
        st.subheader("🚨 알림")
        for alert in alerts:
            st.warning(alert)

    # 컨테이너별 리소스 (cAdvisor)
    st.divider()
    st.subheader("🐳 컨테이너 리소스 (deploy-test)")

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
            "CPU (%)": f"{cpu_val:.2f}",
            "메모리 (MB)": f"{mem_val:.0f}",
        })

    if container_rows:
        st.dataframe(pd.DataFrame(container_rows), width="stretch", hide_index=True)
    else:
        st.info("cAdvisor 데이터 없음 — Prometheus에 cAdvisor가 연결되어 있는지 확인하세요.")

# ── Grafana 대시보드 ──────────────────────────────────────

with tab_grafana:
    st.subheader("Grafana 대시보드")
    st.caption(f"외부 URL: {GRAFANA_URL}")

    st.markdown(f"🔗 [Grafana 새 탭에서 열기]({GRAFANA_URL})")

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
