"""deploy-test (10.10.10.20) 배포 관리 페이지"""

import streamlit as st

from config import DEPLOY_SERVER, PROJECT_DIR, COMPOSE_FILE_PROD
from utils.ssh import run_cmd
from utils.docker_cmd import list_containers, container_action
from utils.ui_components import (
    inject_custom_css,
    render_server_status,
    render_log_viewer,
    render_health_checks,
    render_docker_stats,
    render_section_header,
    render_metric_card,
    render_status_badge,
    render_deploy_steps,
)

HOST = DEPLOY_SERVER["host"]

# CSS 주입
inject_custom_css()

st.title("🚀 배포 관리 (deploy-test)")
st.caption(f"{DEPLOY_SERVER['ssh_alias']} ({HOST})")

# ── 서버 상태 ─────────────────────────────────────────────

online = render_server_status(HOST, "deploy")
if not online:
    st.stop()

# ── 배포 워크플로우 스텝 시각화 ──────────────────────────────

render_section_header("배포 워크플로우", "📋")

# deploy_step 세션 상태로 진행 상황 추적
if "deploy_step" not in st.session_state:
    st.session_state["deploy_step"] = 0

render_deploy_steps(
    current_step=st.session_state["deploy_step"],
    total_steps=4,
    labels=["git pull", "docker pull", "compose up", "health check"],
)

# 원클릭 배포 버튼
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("1. git pull", use_container_width=True):
        st.session_state["deploy_step"] = 1
        with st.spinner("git pull ..."):
            result = run_cmd(HOST, f"cd {PROJECT_DIR} && git pull 2>&1", timeout=30)
        if result.exit_code == 0:
            st.success(result.stdout[:300])
            st.session_state["deploy_step"] = 1
        else:
            st.error(result.stderr[:300])
            st.session_state["deploy_step"] = 0
        st.rerun()

with col2:
    if st.button("2. docker pull", use_container_width=True):
        st.session_state["deploy_step"] = 2
        with st.spinner("docker compose pull ..."):
            result = run_cmd(
                HOST,
                f'cd {PROJECT_DIR} && docker compose -f "{COMPOSE_FILE_PROD}" pull 2>&1',
                timeout=180,
            )
        if result.exit_code == 0:
            st.success("Pull 완료")
            st.session_state["deploy_step"] = 2
        else:
            st.error(result.stderr[:300] or result.stdout[:300])
        st.rerun()

with col3:
    if st.button("3. compose up", use_container_width=True, type="primary"):
        st.session_state["deploy_step"] = 3
        with st.spinner("docker compose up -d ..."):
            result = run_cmd(
                HOST,
                f'cd {PROJECT_DIR} && docker compose -f "{COMPOSE_FILE_PROD}" up -d 2>&1',
                timeout=120,
            )
        if result.exit_code == 0:
            st.success("배포 완료!")
            st.session_state["deploy_step"] = 4
        else:
            st.error(result.stderr[:500] or result.stdout[:500])
        st.rerun()

with col4:
    if st.button("리셋", use_container_width=True):
        st.session_state["deploy_step"] = 0
        st.rerun()

st.info("배포 순서: git pull -> docker compose pull -> docker compose up -d -> health check")

# ── 현재 배포 상태 ────────────────────────────────────────

st.divider()
render_section_header("현재 배포 상태", "📦")

containers = list_containers(HOST)
if containers:
    for c in containers:
        cols = st.columns([3, 2, 3, 2, 1])
        with cols[0]:
            st.text(c["name"])
        with cols[1]:
            badge = render_status_badge(c["state"].capitalize())
            st.markdown(badge, unsafe_allow_html=True)
        with cols[2]:
            st.text(c.get("image", "")[:40])
        with cols[3]:
            st.text(c.get("status", "")[:30])
        with cols[4]:
            if st.button("restart", key=f"deploy_restart_{c['name']}", help="Restart"):
                ok, msg = container_action(HOST, c["name"], "restart")
                st.toast(f"{c['name']} 재시작 완료" if ok else f"실패: {msg}")
                st.rerun()

    render_docker_stats(HOST)
else:
    st.warning("컨테이너 없음")

# ── 최근 배포 이력 ─────────────────────────────────────────

st.divider()
render_section_header("최근 배포 이력", "📜")

# docker compose의 이미지 태그/빌드 시간을 기반으로 이력 표시
result = run_cmd(
    HOST,
    'docker images --format \'{"repo":"{{.Repository}}","tag":"{{.Tag}}","created":"{{.CreatedSince}}","size":"{{.Size}}"}\' '
    '| grep adelie | head -10',
    timeout=10,
)
if result.exit_code == 0 and result.stdout.strip():
    import json
    images = []
    for line in result.stdout.strip().splitlines():
        try:
            images.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if images:
        import pandas as pd
        df = pd.DataFrame(images)
        df.columns = ["이미지", "태그", "생성 시점", "크기"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("adelie 관련 이미지 없음")
else:
    st.info("이미지 정보를 가져올 수 없습니다.")

# ── Git 상태 ──────────────────────────────────────────────

st.divider()
render_section_header("Git 상태", "📂")

col1, col2 = st.columns(2)
with col1:
    result = run_cmd(HOST, f"cd {PROJECT_DIR} && git branch --show-current")
    st.text(f"브랜치: {result.stdout.strip()}")

    result = run_cmd(HOST, f"cd {PROJECT_DIR} && git log --oneline -3")
    st.code(result.stdout.strip(), language=None)

with col2:
    result = run_cmd(HOST, f"cd {PROJECT_DIR} && git status --porcelain | wc -l")
    changes = result.stdout.strip()
    st.text(f"uncommitted 변경: {changes}개")

    result = run_cmd(HOST, f"cd {PROJECT_DIR} && git remote get-url origin 2>/dev/null || echo N/A")
    st.text(f"remote: {result.stdout.strip()[:50]}")

# ── Alembic ───────────────────────────────────────────────

st.divider()
render_section_header("Alembic 마이그레이션", "🗄️")

col1, col2 = st.columns(2)
with col1:
    result = run_cmd(
        HOST,
        'docker exec adelie-backend-api sh -c "cd /app/database && alembic current 2>&1" 2>/dev/null || echo N/A',
    )
    st.text(f"현재 revision: {result.stdout.strip()[:50]}")

with col2:
    if st.button("alembic upgrade head"):
        with st.spinner("마이그레이션 실행 중 ..."):
            result = run_cmd(
                HOST,
                'docker exec adelie-backend-api sh -c "cd /app/database && alembic upgrade head 2>&1"',
                timeout=60,
            )
        if result.exit_code == 0:
            st.success(result.stdout[:300])
        else:
            st.error(result.stderr[:300] or result.stdout[:300])

# ── 로그 뷰어 ────────────────────────────────────────────

st.divider()
render_section_header("컨테이너 로그", "📋")
render_log_viewer(HOST, containers, "deploy")

# ── 서비스 헬스 ───────────────────────────────────────────

st.divider()
render_section_header("서비스 헬스 체크", "💓")
render_health_checks(HOST, DEPLOY_SERVER["port_api"], DEPLOY_SERVER["port_front"], "deploy_health")
