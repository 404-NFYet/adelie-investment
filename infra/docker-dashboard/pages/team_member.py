"""팀원별 서버 관리 페이지 -- app.py에서 callable로 호출됨"""

import streamlit as st

from config import SERVERS, PROJECT_DIR
from utils.ssh import run_cmd, is_server_online
from utils.docker_cmd import list_containers
from utils.ui_components import (
    inject_custom_css,
    render_server_status,
    render_container_table,
    render_compose_buttons,
    render_log_viewer,
    render_health_checks,
    render_docker_stats,
    render_section_header,
    render_metric_card,
    render_status_badge,
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


def _render_status_cards(host: str, containers: list[dict], server_info: dict):
    """상단 상태 요약 카드"""
    running = sum(1 for c in containers if c.get("state") == "running")
    total = len(containers)
    disk = server_info.get("DISK", "N/A")
    branch = server_info.get("BRANCH", "N/A")
    changes = server_info.get("CHANGES", "0")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("컨테이너", f"{running}/{total}", icon="🐳")
    with col2:
        render_metric_card("디스크 사용", disk, icon="💾")
    with col3:
        render_metric_card("브랜치", branch, icon="🔀")
    with col4:
        delta = f"{changes}개 변경" if changes != "0" else "clean"
        render_metric_card("Git 상태", delta, icon="📝")


def _render_docker_tab(host: str, containers: list[dict], key_prefix: str):
    """Docker 탭 내용"""
    render_section_header("컨테이너 목록", "🐳")
    render_container_table(host, containers, key_prefix)

    st.divider()
    render_section_header("Compose 관리", "🔧")
    render_compose_buttons(host, key_prefix)

    render_docker_stats(host)


def _render_git_tab(host: str, key_prefix: str, server_info: dict):
    """Git 탭 내용"""
    render_section_header("Git 정보", "📂")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Git 상태**")
        st.text(f"브랜치: {server_info.get('BRANCH', 'N/A')}")
        st.text(f"커밋: {server_info.get('COMMIT', 'N/A')}")
        st.text(f"uncommitted: {server_info.get('CHANGES', '?')}개")

        if st.button("git pull", key=f"{key_prefix}_git_pull"):
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

    # Alembic
    st.divider()
    render_section_header("Alembic 마이그레이션", "🗄️")
    result = run_cmd(
        host,
        f"cd {PROJECT_DIR}/database && ../.venv/bin/alembic current 2>&1 | head -1",
    )
    rev = result.stdout.strip() if result.exit_code == 0 else "N/A"
    st.text(f"revision: {rev[:40]}")

    if st.button("upgrade head", key=f"{key_prefix}_alembic"):
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


def _render_health_tab(host: str, port_api: int, port_front: int, key_prefix: str):
    """Health 탭 내용"""
    render_section_header("서비스 헬스 체크", "💓")
    render_health_checks(host, port_api, port_front, key_prefix)


def _render_log_tab(host: str, containers: list[dict], key_prefix: str):
    """Logs 탭 내용"""
    render_section_header("컨테이너 로그", "📋")
    render_log_viewer(host, containers, key_prefix)


def _render_role_extras(host: str, role: str, key_prefix: str):
    """역할별 추가 기능"""
    render_section_header("역할별 기능", "🎯")

    if role == "frontend":
        col1, col2 = st.columns(2)
        with col1:
            if st.button("npm install", key=f"{key_prefix}_npm"):
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
        st.markdown(f"[Swagger UI](http://{host}:8082/docs)")

    elif role == "chatbot":
        st.markdown("[LangSmith](https://smith.langchain.com)")
        st.markdown(f"[Swagger UI](http://{host}:8082/docs)")

    elif role == "pipeline":
        st.markdown("[LangSmith](https://smith.langchain.com)")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("파이프라인 실행 (mock)", key=f"{key_prefix}_pipe_mock"):
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
            if st.button("파이프라인 실행 (live)", type="primary", key=f"{key_prefix}_pipe_live"):
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
            badge = render_status_badge("Online" if online else "Offline")
            status_data.append({
                "팀원": sname,
                "IP": sinfo["host"],
                "상태": badge,
            })
        # HTML 테이블로 배지 표시
        html_rows = ""
        for row in status_data:
            html_rows += f"<tr><td>{row['팀원']}</td><td>{row['IP']}</td><td>{row['상태']}</td></tr>"
        st.markdown(f"""
        <table style="width:100%; border-collapse:collapse;">
            <thead><tr style="border-bottom:2px solid #E9ECEF;">
                <th style="text-align:left; padding:8px;">팀원</th>
                <th style="text-align:left; padding:8px;">IP</th>
                <th style="text-align:left; padding:8px;">상태</th>
            </tr></thead>
            <tbody>{html_rows}</tbody>
        </table>
        """, unsafe_allow_html=True)


def render_team_page(name: str, server_info: dict):
    """팀원 서버 관리 페이지 렌더링 -- app.py에서 호출"""
    host = server_info["host"]
    role = server_info["role"]
    key_prefix = server_info["ssh_alias"]
    port_api = server_info["port_api"]
    port_front = server_info["port_front"]

    # CSS 주입
    inject_custom_css()

    st.title(f"🖥️ {name}")
    st.caption(f"{server_info['ssh_alias']} ({host})")

    # 서버 상태 (오프라인이면 안내 카드만 표시)
    online = render_server_status(host, key_prefix, server_name=name)
    if not online:
        st.markdown(f"""
        <div class="metric-card" style="text-align:center; padding:24px; border-left:4px solid #DC3545;">
            <div style="font-size:40px; margin-bottom:8px;">🔌</div>
            <div style="font-size:18px; font-weight:700; color:#721C24;">{name} 서버 오프라인</div>
            <div style="font-size:13px; color:#6C757D; margin-top:6px;">{host} — SSH 연결 불가</div>
            <div style="font-size:12px; color:#ADB5BD; margin-top:4px;">우측 새로고침 버튼으로 재시도하세요</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # 서버 정보 수집 (1회 SSH)
    info = _collect_server_info(host)

    # 컨테이너 (1회만 조회하여 재사용)
    containers = list_containers(host)

    # 상단 상태 카드
    _render_status_cards(host, containers, info)

    st.divider()

    # 탭 기반 레이아웃
    tab_docker, tab_git, tab_health, tab_logs = st.tabs(
        ["🐳 Docker", "📂 Git", "💓 Health", "📋 Logs"]
    )

    with tab_docker:
        _render_docker_tab(host, containers, key_prefix)

    with tab_git:
        _render_git_tab(host, key_prefix, info)

    with tab_health:
        _render_health_tab(host, port_api, port_front, key_prefix)

    with tab_logs:
        _render_log_tab(host, containers, key_prefix)

    # 역할별 기능
    st.divider()
    _render_role_extras(host, role, key_prefix)
