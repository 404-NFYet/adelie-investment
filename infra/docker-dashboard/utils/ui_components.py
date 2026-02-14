"""공통 UI 컴포넌트 — deploy.py와 team_member.py에서 공유"""

import streamlit as st

from config import HEALTH_CHECK_ENDPOINT, REDIS_CONTAINER_FILTER, POSTGRES_CONTAINER_FILTER
from utils.ssh import run_cmd, is_server_online
from utils.docker_cmd import (
    container_action,
    container_logs,
    compose_up,
    compose_down,
    compose_pull,
    docker_stats,
)


def render_server_status(host: str, key_prefix: str) -> bool:
    """서버 온라인/오프라인 상태 표시. Returns True if online."""
    col1, col2 = st.columns([3, 1])
    with col1:
        online = is_server_online(host)
        if online:
            st.success("🟢 서버 상태: Online")
        else:
            st.error("🔴 서버 상태: Offline — SSH 연결 불가")
    with col2:
        if st.button("🔄 새로고침", use_container_width=True, key=f"{key_prefix}_refresh"):
            st.rerun()
    return online


def render_container_table(host: str, containers: list[dict], key_prefix: str):
    """컨테이너 목록 + 재시작/시작/정지 버튼"""
    if not containers:
        st.warning("컨테이너 없음 또는 Docker 미설치")
        return

    for c in containers:
        cols = st.columns([3, 2, 2, 2, 2])
        with cols[0]:
            st.text(c["name"])
        with cols[1]:
            if c["state"] == "running":
                st.markdown("🟢 **Running**")
            elif c["state"] == "exited":
                st.markdown("🔴 **Exited**")
            else:
                st.markdown(f"🟡 **{c['state']}**")
        with cols[2]:
            ports = c.get("ports", "")
            if ports:
                port_parts = []
                for p in ports.split(", "):
                    if "->" in p:
                        port_parts.append(p.split("->")[0].split(":")[-1])
                st.text(", ".join(port_parts) if port_parts else ports[:30])
            else:
                st.text("-")
        with cols[3]:
            if st.button("⟳", key=f"{key_prefix}_restart_{c['name']}", help="Restart"):
                ok, msg = container_action(host, c["name"], "restart")
                st.toast(f"✅ {c['name']} 재시작 완료" if ok else f"❌ {msg}")
                st.rerun()
        with cols[4]:
            if c["state"] == "running":
                if st.button("🛑", key=f"{key_prefix}_stop_{c['name']}", help="Stop"):
                    ok, msg = container_action(host, c["name"], "stop")
                    st.toast(f"✅ {c['name']} 중지 완료" if ok else f"❌ {msg}")
                    st.rerun()
            else:
                if st.button("▶️", key=f"{key_prefix}_start_{c['name']}", help="Start"):
                    ok, msg = container_action(host, c["name"], "start")
                    st.toast(f"✅ {c['name']} 시작 완료" if ok else f"❌ {msg}")
                    st.rerun()


def render_compose_buttons(host: str, key_prefix: str, compose_file: str | None = None):
    """Compose Up/Down/Pull 버튼"""
    kwargs = {"compose_file": compose_file} if compose_file else {}
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🚀 Compose Up", use_container_width=True, key=f"{key_prefix}_up"):
            with st.spinner("docker compose up -d ..."):
                ok, msg = compose_up(host, **kwargs)
            st.success("Compose Up 완료") if ok else st.error(f"실패: {msg[:500]}")
            st.rerun()
    with col2:
        if st.button("⏹️ Compose Down", use_container_width=True, key=f"{key_prefix}_down"):
            with st.spinner("docker compose down ..."):
                ok, msg = compose_down(host, **kwargs)
            st.success("Compose Down 완료") if ok else st.error(f"실패: {msg[:500]}")
            st.rerun()
    with col3:
        if st.button("📥 Pull + Up", use_container_width=True, key=f"{key_prefix}_pull"):
            with st.spinner("docker compose pull && up -d ..."):
                ok, msg = compose_pull(host, **kwargs)
            st.success("Pull + Up 완료") if ok else st.error(f"실패: {msg[:500]}")
            st.rerun()


def render_log_viewer(host: str, containers: list[dict], key_prefix: str):
    """컨테이너 로그 뷰어"""
    if not containers:
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        names = [c["name"] for c in containers]
        selected = st.selectbox("컨테이너 선택", names, key=f"{key_prefix}_log_container")
    with col2:
        lines = st.selectbox("줄 수", [50, 100, 200, 500], index=1, key=f"{key_prefix}_log_lines")

    if selected and st.button("로그 조회", key=f"{key_prefix}_show_log"):
        logs = container_logs(host, selected, lines)
        st.code(logs, language="log")


def render_health_checks(host: str, port_api: int, port_front: int, key_prefix: str):
    """API/Frontend/Redis/PostgreSQL 헬스 체크"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        result = run_cmd(
            host,
            f"curl -sf http://localhost:{port_api}{HEALTH_CHECK_ENDPOINT}"
            f" -o /dev/null -w '%{{http_code}}' 2>/dev/null || echo 000",
        )
        code = result.stdout.strip()
        st.metric("Backend API", "✅ 정상" if code == "200" else f"❌ {code}")

    with col2:
        result = run_cmd(
            host,
            f"curl -sf http://localhost:{port_front}/"
            f" -o /dev/null -w '%{{http_code}}' 2>/dev/null || echo 000",
        )
        code = result.stdout.strip()
        st.metric("Frontend", "✅ 정상" if code in ("200", "304") else f"❌ {code}")

    with col3:
        result = run_cmd(
            host,
            f'docker exec "$(docker ps -qf {REDIS_CONTAINER_FILTER})" redis-cli ping 2>/dev/null || echo FAIL',
        )
        ok = "PONG" in result.stdout
        st.metric("Redis", "✅ PONG" if ok else "❌ FAIL")

    with col4:
        result = run_cmd(
            host,
            f'docker exec "$(docker ps -qf {POSTGRES_CONTAINER_FILTER})" pg_isready 2>/dev/null || echo FAIL',
        )
        ok = "accepting" in result.stdout
        st.metric("PostgreSQL", "✅ ready" if ok else "❌ FAIL")


def render_docker_stats(host: str):
    """Docker 리소스 사용량 테이블"""
    stats = docker_stats(host)
    if stats:
        st.markdown("**리소스 사용량**")
        st.table(stats)
