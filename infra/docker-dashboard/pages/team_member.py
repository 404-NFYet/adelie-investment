"""팀원별 서버 관리 페이지 — app.py에서 callable로 호출됨"""

import streamlit as st

from config import SERVERS, PROJECT_DIR
from utils.ssh import run_cmd, is_server_online
from utils.docker_cmd import list_containers
from utils.ui_components import (
    render_server_status,
    render_container_table,
    render_compose_buttons,
    render_log_viewer,
    render_health_checks,
    render_docker_stats,
)


def _collect_server_info(host: str) -> dict:
    """git, env, system 정보를 1회 SSH로 일괄 수집"""
    script = "; ".join([
        f'echo "BRANCH:$(cd {PROJECT_DIR} && git branch --show-current 2>/dev/null || echo N/A)"',
        f'echo "COMMIT:$(cd {PROJECT_DIR} && git log --oneline -1 2>/dev/null || echo N/A)"',
        f'echo "CHANGES:$(cd {PROJECT_DIR} && git status --porcelain 2>/dev/null | wc -l)"',
        f"echo \"ENV_KEYS:$(cd {PROJECT_DIR} && grep -c '=' .env 2>/dev/null || echo 0)\"",
        'echo "PYTHON:$(python3 --version 2>&1 || echo N/A)"',
        'echo "NODE:$(node --version 2>&1 || echo N/A)"',
        "echo \"DISK:$(df -h / | tail -1 | awk '{print $5}' || echo N/A)\"",
    ])
    result = run_cmd(host, script)
    info = {}
    if result.exit_code == 0:
        for line in result.stdout.strip().splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                info[key.strip()] = value.strip()
    return info


def _render_git_info(host: str, key_prefix: str, server_info: dict):
    """Git 상태 + 환경 정보 표시 (사전 수집된 정보 사용)"""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Git**")
        st.text(f"브랜치: {server_info.get('BRANCH', 'N/A')}")
        st.text(f"커밋: {server_info.get('COMMIT', 'N/A')}")
        st.text(f"uncommitted: {server_info.get('CHANGES', '?')}개")

        if st.button("📥 git pull", key=f"{key_prefix}_git_pull"):
            with st.spinner("git pull ..."):
                result = run_cmd(host, f"cd {PROJECT_DIR} && git pull", timeout=30)
            if result.exit_code == 0:
                st.success(result.stdout[:300])
            else:
                st.error(result.stderr[:300])

    with col2:
        st.markdown("**환경 체크**")
        st.text(f".env: {server_info.get('ENV_KEYS', '?')}개 키")
        st.text(f"Python: {server_info.get('PYTHON', 'N/A')}")
        st.text(f"Node: {server_info.get('NODE', 'N/A')}")
        st.text(f"디스크: {server_info.get('DISK', '?')} 사용")


def _render_alembic(host: str, key_prefix: str):
    """Alembic 마이그레이션 상태 + 업그레이드"""
    st.markdown("**Alembic**")
    result = run_cmd(
        host,
        f"cd {PROJECT_DIR}/database && ../.venv/bin/alembic current 2>&1 | head -1",
    )
    rev = result.stdout.strip() if result.exit_code == 0 else "N/A"
    st.text(f"revision: {rev[:40]}")

    if st.button("⬆️ upgrade head", key=f"{key_prefix}_alembic"):
        with st.spinner("alembic upgrade head ..."):
            result = run_cmd(
                host,
                f"cd {PROJECT_DIR}/database && ../.venv/bin/alembic upgrade head 2>&1",
                timeout=60,
            )
        if result.exit_code == 0:
            st.success(result.stdout[:300])
        else:
            st.error(result.stderr[:300] or result.stdout[:300])


def _render_role_extras(host: str, role: str, key_prefix: str):
    """역할별 추가 기능"""
    st.subheader("🎯 역할별 기능")

    if role == "frontend":
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📦 npm install", key=f"{key_prefix}_npm"):
                with st.spinner("npm install ..."):
                    result = run_cmd(host, f"cd {PROJECT_DIR}/frontend && npm install 2>&1", timeout=120)
                if result.exit_code == 0:
                    st.success("npm install 완료")
                else:
                    st.error(result.stderr[:500])
        with col2:
            result = run_cmd(host, f"cd {PROJECT_DIR}/frontend && du -sh node_modules 2>/dev/null || echo N/A")
            st.text(f"node_modules: {result.stdout.strip()}")

    elif role == "backend":
        st.markdown(f"📖 [Swagger UI](http://{host}:8082/docs)")

    elif role == "chatbot":
        st.markdown("🔗 [LangSmith](https://smith.langchain.com)")
        st.markdown(f"📖 [Swagger UI](http://{host}:8082/docs)")

    elif role == "pipeline":
        st.markdown("🔗 [LangSmith](https://smith.langchain.com)")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ 파이프라인 실행 (mock)", key=f"{key_prefix}_pipe_mock"):
                with st.spinner("mock 파이프라인 실행 중 ..."):
                    result = run_cmd(
                        host,
                        f"cd {PROJECT_DIR} && .venv/bin/python -m datapipeline.run --backend mock 2>&1",
                        timeout=300,
                    )
                if result.exit_code == 0:
                    st.success("파이프라인 실행 완료")
                    st.code(result.stdout[-1000:])
                else:
                    st.error(result.stderr[:500] or result.stdout[:500])
        with col2:
            if st.button("▶️ 파이프라인 실행 (live)", type="primary", key=f"{key_prefix}_pipe_live"):
                with st.spinner("live 파이프라인 실행 중 ..."):
                    result = run_cmd(
                        host,
                        f"cd {PROJECT_DIR} && .venv/bin/python -m datapipeline.run --backend live --market KR 2>&1",
                        timeout=600,
                    )
                if result.exit_code == 0:
                    st.success("파이프라인 실행 완료")
                    st.code(result.stdout[-1000:])
                else:
                    st.error(result.stderr[:500] or result.stdout[:500])

    elif role == "infra":
        st.markdown("**전체 서버 요약**")
        status_data = []
        for sname, sinfo in SERVERS.items():
            online = is_server_online(sinfo["host"])
            status_data.append({
                "팀원": sname,
                "IP": sinfo["host"],
                "상태": "🟢 Online" if online else "🔴 Offline",
            })
        st.table(status_data)


def render_team_page(name: str, server_info: dict):
    """팀원 서버 관리 페이지 렌더링 — app.py에서 호출"""
    host = server_info["host"]
    role = server_info["role"]
    key_prefix = server_info["ssh_alias"]
    port_api = server_info["port_api"]
    port_front = server_info["port_front"]

    st.title(f"🖥️ {name}")
    st.caption(f"{server_info['ssh_alias']} ({host})")

    # 서버 상태 (오프라인이면 나머지 비표시)
    online = render_server_status(host, key_prefix)
    if not online:
        return

    # 컨테이너 (1회만 조회하여 재사용)
    st.divider()
    st.subheader("🐳 Docker 컨테이너")
    containers = list_containers(host)
    render_container_table(host, containers, key_prefix)

    st.divider()
    render_compose_buttons(host, key_prefix)

    # 리소스 사용량
    render_docker_stats(host)

    # 로그
    st.divider()
    st.subheader("📋 컨테이너 로그")
    render_log_viewer(host, containers, key_prefix)

    # Git + 환경 (1회 SSH로 수집)
    st.divider()
    st.subheader("🔧 유틸리티")
    info = _collect_server_info(host)
    _render_git_info(host, key_prefix, info)

    # Alembic
    st.divider()
    _render_alembic(host, key_prefix)

    # 헬스 체크
    st.divider()
    st.subheader("💓 서비스 헬스 체크")
    render_health_checks(host, port_api, port_front, key_prefix)

    # 역할별 기능
    st.divider()
    _render_role_extras(host, role, key_prefix)
