"""deploy-test (10.10.10.20) 배포 관리 페이지"""

import streamlit as st

from config import DEPLOY_SERVER, PROJECT_DIR, COMPOSE_FILE_PROD
from utils.ssh import run_cmd
from utils.docker_cmd import list_containers, container_action
from utils.ui_components import (
    render_server_status,
    render_log_viewer,
    render_health_checks,
    render_docker_stats,
)

HOST = DEPLOY_SERVER["host"]

st.title("🚀 배포 관리 (deploy-test)")
st.caption(f"{DEPLOY_SERVER['ssh_alias']} ({HOST})")

# ── 서버 상태 ─────────────────────────────────────────────

online = render_server_status(HOST, "deploy")
if not online:
    st.stop()

# ── 현재 배포 상태 ────────────────────────────────────────

st.subheader("📦 현재 배포 상태")

containers = list_containers(HOST)
if containers:
    for c in containers:
        cols = st.columns([3, 2, 3, 2, 1])
        with cols[0]:
            st.text(c["name"])
        with cols[1]:
            if c["state"] == "running":
                st.markdown("🟢 **Running**")
            else:
                st.markdown(f"🔴 **{c['state']}**")
        with cols[2]:
            st.text(c.get("image", "")[:40])
        with cols[3]:
            st.text(c.get("status", "")[:30])
        with cols[4]:
            if st.button("⟳", key=f"deploy_restart_{c['name']}", help="Restart"):
                ok, msg = container_action(HOST, c["name"], "restart")
                st.toast(f"✅ {c['name']} 재시작 완료" if ok else f"❌ {msg}")
                st.rerun()

    render_docker_stats(HOST)
else:
    st.warning("컨테이너 없음")

# ── Git 상태 ──────────────────────────────────────────────

st.divider()
st.subheader("📂 Git 상태")

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

# ── 원클릭 배포 ──────────────────────────────────────────

st.divider()
st.subheader("⚡ 원클릭 배포")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📥 git pull", use_container_width=True):
        with st.spinner("git pull ..."):
            result = run_cmd(HOST, f"cd {PROJECT_DIR} && git pull 2>&1", timeout=30)
        if result.exit_code == 0:
            st.success(result.stdout[:300])
        else:
            st.error(result.stderr[:300])

with col2:
    if st.button("📥 docker compose pull", use_container_width=True):
        with st.spinner("docker compose pull ..."):
            result = run_cmd(
                HOST,
                f'cd {PROJECT_DIR} && docker compose -f "{COMPOSE_FILE_PROD}" pull 2>&1',
                timeout=180,
            )
        if result.exit_code == 0:
            st.success("Pull 완료")
        else:
            st.error(result.stderr[:300] or result.stdout[:300])

with col3:
    if st.button("🚀 docker compose up -d", use_container_width=True, type="primary"):
        with st.spinner("docker compose up -d ..."):
            result = run_cmd(
                HOST,
                f'cd {PROJECT_DIR} && docker compose -f "{COMPOSE_FILE_PROD}" up -d 2>&1',
                timeout=120,
            )
        if result.exit_code == 0:
            st.success("배포 완료!")
        else:
            st.error(result.stderr[:500] or result.stdout[:500])
        st.rerun()

st.info("💡 전체 배포 순서: git pull → docker compose pull → docker compose up -d")

# ── Alembic ───────────────────────────────────────────────

st.divider()
st.subheader("🗄️ Alembic 마이그레이션")

col1, col2 = st.columns(2)
with col1:
    result = run_cmd(
        HOST,
        'docker exec adelie-backend-api sh -c "cd /app/database && alembic current 2>&1" 2>/dev/null || echo N/A',
    )
    st.text(f"현재 revision: {result.stdout.strip()[:50]}")

with col2:
    if st.button("⬆️ alembic upgrade head"):
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
st.subheader("📋 컨테이너 로그")
render_log_viewer(HOST, containers, "deploy")

# ── 서비스 헬스 ───────────────────────────────────────────

st.divider()
st.subheader("💓 서비스 헬스 체크")
render_health_checks(HOST, DEPLOY_SERVER["port_api"], DEPLOY_SERVER["port_front"], "deploy_health")
