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


# ── 공통 UI 헬퍼 (H-2) ──────────────────────────────────────


def inject_custom_css():
    """화이트 모드 호환 커스텀 CSS 주입"""
    st.markdown("""
    <style>
    /* ── 카드 공통 ─────────────────────────── */
    .metric-card {
        background: linear-gradient(135deg, #FFFFFF 0%, #F8F9FA 100%);
        border: 1px solid #E9ECEF;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        transition: transform 0.2s, box-shadow 0.2s;
        margin-bottom: 12px;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.10);
    }
    .metric-card .card-icon {
        font-size: 28px;
        margin-bottom: 4px;
    }
    .metric-card .card-title {
        font-size: 13px;
        color: #6C757D;
        margin-bottom: 4px;
        font-weight: 500;
    }
    .metric-card .card-value {
        font-size: 26px;
        font-weight: 700;
        color: #1A1A2E;
    }
    .metric-card .card-delta-pos {
        font-size: 13px;
        color: #28A745;
        font-weight: 600;
    }
    .metric-card .card-delta-neg {
        font-size: 13px;
        color: #DC3545;
        font-weight: 600;
    }

    /* ── 상태 배지 ─────────────────────────── */
    .status-badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    .status-online  { background: #D4EDDA; color: #155724; }
    .status-offline { background: #F8D7DA; color: #721C24; }
    .status-warning { background: #FFF3CD; color: #856404; }

    /* ── 섹션 헤더 ─────────────────────────── */
    .section-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 20px 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #FF6B00;
    }
    .section-header .header-icon {
        font-size: 22px;
    }
    .section-header .header-title {
        font-size: 20px;
        font-weight: 700;
        color: #1A1A2E;
        margin: 0;
    }

    /* ── HTTP 메서드 배지 ───────────────────── */
    .http-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.5px;
        color: #FFFFFF;
    }
    .http-get    { background: #28A745; }
    .http-post   { background: #007BFF; }
    .http-put    { background: #FF6B00; }
    .http-delete { background: #DC3545; }
    .http-patch  { background: #FD7E14; }

    /* ── 프로그레스 스텝 ───────────────────── */
    .deploy-steps {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 16px 0;
        padding: 0;
    }
    .deploy-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 1;
        position: relative;
    }
    .step-circle {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        font-weight: 700;
        z-index: 1;
    }
    .step-done    { background: #28A745; color: #fff; }
    .step-active  { background: #FF6B00; color: #fff; animation: pulse 1.5s infinite; }
    .step-pending { background: #DEE2E6; color: #6C757D; }
    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(255,107,0,0.4); }
        50% { box-shadow: 0 0 0 8px rgba(255,107,0,0); }
    }
    .step-label {
        margin-top: 8px;
        font-size: 12px;
        font-weight: 600;
        color: #495057;
        text-align: center;
    }
    .step-connector {
        flex: 1;
        height: 3px;
        background: #DEE2E6;
        margin: 0 -8px;
        margin-top: -20px;
        z-index: 0;
    }
    .step-connector.done { background: #28A745; }

    /* ── 로고 헤더 ─────────────────────────── */
    .logo-header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 8px;
    }
    .logo-header .logo-icon {
        font-size: 42px;
    }
    .logo-header .logo-text {
        font-size: 28px;
        font-weight: 800;
        color: #1A1A2E;
    }
    .logo-header .logo-sub {
        font-size: 13px;
        color: #6C757D;
        margin-top: -4px;
    }

    /* ── 게이지 차트 (CSS) ─────────────────── */
    .gauge-container {
        text-align: center;
        padding: 12px 8px;
    }
    .gauge-svg {
        width: 120px;
        height: 70px;
    }
    .gauge-label {
        font-size: 12px;
        color: #6C757D;
        margin-top: 4px;
    }
    .gauge-value {
        font-size: 20px;
        font-weight: 700;
        color: #1A1A2E;
    }

    /* ── 탭 스타일 개선 ────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
        font-weight: 600;
    }

    /* ── 사이드바 개선 ─────────────────────── */
    section[data-testid="stSidebar"] {
        background: #F8F9FA;
        border-right: 1px solid #E9ECEF;
    }

    /* ── 데이터프레임 스타일 ─────────────────── */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)


def render_metric_card(title: str, value: str, delta: str | None = None, icon: str | None = None):
    """그라디언트 카드 + 그림자 메트릭 표시"""
    icon_html = f'<div class="card-icon">{icon}</div>' if icon else ""
    delta_html = ""
    if delta is not None:
        is_positive = not str(delta).startswith("-")
        cls = "card-delta-pos" if is_positive else "card-delta-neg"
        arrow = "+" if is_positive and not str(delta).startswith("+") else ""
        delta_html = f'<div class="{cls}">{arrow}{delta}</div>'

    st.markdown(f"""
    <div class="metric-card">
        {icon_html}
        <div class="card-title">{title}</div>
        <div class="card-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def render_status_badge(status: str) -> str:
    """Online/Offline/Warning 배지 HTML 반환"""
    status_lower = status.lower()
    if status_lower in ("online", "running", "healthy", "ok"):
        cls = "status-online"
        label = status
    elif status_lower in ("offline", "exited", "stopped", "error", "fail"):
        cls = "status-offline"
        label = status
    else:
        cls = "status-warning"
        label = status
    return f'<span class="status-badge {cls}">{label}</span>'


def render_section_header(title: str, icon: str | None = None):
    """일관된 섹션 헤더 렌더링"""
    icon_html = f'<span class="header-icon">{icon}</span>' if icon else ""
    st.markdown(f"""
    <div class="section-header">
        {icon_html}
        <span class="header-title">{title}</span>
    </div>
    """, unsafe_allow_html=True)


def render_deploy_steps(current_step: int = 0, total_steps: int = 4,
                        labels: list[str] | None = None):
    """배포 워크플로우 스텝 프로그레스 시각화"""
    if labels is None:
        labels = ["git pull", "docker pull", "compose up", "health check"]

    html_parts = []
    for i in range(total_steps):
        if i < current_step:
            circle_cls = "step-done"
            icon = "&#10003;"
        elif i == current_step:
            circle_cls = "step-active"
            icon = str(i + 1)
        else:
            circle_cls = "step-pending"
            icon = str(i + 1)

        step_html = f"""
        <div class="deploy-step">
            <div class="step-circle {circle_cls}">{icon}</div>
            <div class="step-label">{labels[i] if i < len(labels) else ''}</div>
        </div>
        """
        html_parts.append(step_html)

        # 스텝 사이 커넥터 (마지막 제외)
        if i < total_steps - 1:
            conn_cls = "done" if i < current_step else ""
            html_parts.append(f'<div class="step-connector {conn_cls}"></div>')

    st.markdown(f'<div class="deploy-steps">{"".join(html_parts)}</div>', unsafe_allow_html=True)


def render_http_method_badge(method: str) -> str:
    """HTTP 메서드 색상 배지 HTML 반환"""
    cls = f"http-{method.lower()}"
    return f'<span class="http-badge {cls}">{method}</span>'


def render_gauge_chart(label: str, value: float, max_val: float = 100):
    """CSS 기반 반원 게이지 차트"""
    pct = min(value / max_val, 1.0) if max_val > 0 else 0
    angle = pct * 180
    # 색상 결정
    if pct < 0.6:
        color = "#28A745"
    elif pct < 0.8:
        color = "#FFC107"
    else:
        color = "#DC3545"

    st.markdown(f"""
    <div class="gauge-container">
        <svg class="gauge-svg" viewBox="0 0 120 70">
            <path d="M 10 65 A 50 50 0 0 1 110 65" fill="none" stroke="#E9ECEF" stroke-width="10" stroke-linecap="round"/>
            <path d="M 10 65 A 50 50 0 0 1 110 65" fill="none" stroke="{color}" stroke-width="10" stroke-linecap="round"
                  stroke-dasharray="{pct * 157} 157"/>
        </svg>
        <div class="gauge-value">{value:.1f}%</div>
        <div class="gauge-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


# ── 기존 공통 UI 컴포넌트 (하위 호환 유지) ─────────────────────


def render_server_status(host: str, key_prefix: str) -> bool:
    """서버 온라인/오프라인 상태 표시. Returns True if online."""
    col1, col2 = st.columns([3, 1])
    with col1:
        online = is_server_online(host)
        if online:
            st.markdown(render_status_badge("Online"), unsafe_allow_html=True)
        else:
            st.markdown(render_status_badge("Offline"), unsafe_allow_html=True)
            st.caption("SSH 연결 불가")
    with col2:
        if st.button("새로고침", use_container_width=True, key=f"{key_prefix}_refresh"):
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
            badge = render_status_badge(c["state"].capitalize())
            st.markdown(badge, unsafe_allow_html=True)
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
            if st.button("restart", key=f"{key_prefix}_restart_{c['name']}", help="Restart"):
                ok, msg = container_action(host, c["name"], "restart")
                st.toast(f"{c['name']} 재시작 완료" if ok else f"실패: {msg}")
                st.rerun()
        with cols[4]:
            if c["state"] == "running":
                if st.button("stop", key=f"{key_prefix}_stop_{c['name']}", help="Stop"):
                    ok, msg = container_action(host, c["name"], "stop")
                    st.toast(f"{c['name']} 중지 완료" if ok else f"실패: {msg}")
                    st.rerun()
            else:
                if st.button("start", key=f"{key_prefix}_start_{c['name']}", help="Start"):
                    ok, msg = container_action(host, c["name"], "start")
                    st.toast(f"{c['name']} 시작 완료" if ok else f"실패: {msg}")
                    st.rerun()


def render_compose_buttons(host: str, key_prefix: str, compose_file: str | None = None):
    """Compose Up/Down/Pull 버튼"""
    kwargs = {"compose_file": compose_file} if compose_file else {}
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Compose Up", use_container_width=True, key=f"{key_prefix}_up"):
            with st.spinner("docker compose up -d ..."):
                ok, msg = compose_up(host, **kwargs)
            st.success("Compose Up 완료") if ok else st.error(f"실패: {msg[:500]}")
            st.rerun()
    with col2:
        if st.button("Compose Down", use_container_width=True, key=f"{key_prefix}_down"):
            with st.spinner("docker compose down ..."):
                ok, msg = compose_down(host, **kwargs)
            st.success("Compose Down 완료") if ok else st.error(f"실패: {msg[:500]}")
            st.rerun()
    with col3:
        if st.button("Pull + Up", use_container_width=True, key=f"{key_prefix}_pull"):
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
        ok = code == "200"
        render_metric_card("Backend API", "정상" if ok else f"Error {code}", icon="api")

    with col2:
        result = run_cmd(
            host,
            f"curl -sf http://localhost:{port_front}/"
            f" -o /dev/null -w '%{{http_code}}' 2>/dev/null || echo 000",
        )
        code = result.stdout.strip()
        ok = code in ("200", "304")
        render_metric_card("Frontend", "정상" if ok else f"Error {code}", icon="web")

    with col3:
        result = run_cmd(
            host,
            f'docker exec "$(docker ps -qf {REDIS_CONTAINER_FILTER})" redis-cli ping 2>/dev/null || echo FAIL',
        )
        ok = "PONG" in result.stdout
        render_metric_card("Redis", "PONG" if ok else "FAIL", icon="cache")

    with col4:
        result = run_cmd(
            host,
            f'docker exec "$(docker ps -qf {POSTGRES_CONTAINER_FILTER})" pg_isready 2>/dev/null || echo FAIL',
        )
        ok = "accepting" in result.stdout
        render_metric_card("PostgreSQL", "Ready" if ok else "FAIL", icon="db")


def render_docker_stats(host: str):
    """Docker 리소스 사용량 테이블"""
    stats = docker_stats(host)
    if stats:
        render_section_header("리소스 사용량", "server")
        st.table(stats)
