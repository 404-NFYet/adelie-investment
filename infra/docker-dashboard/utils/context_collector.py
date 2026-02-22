"""서버 실시간 컨텍스트 수집 — git/docker 상태를 SSH로 조회"""

import streamlit as st

from config import PROJECT_DIR
from utils.ssh import run_cmd, is_server_online


@st.cache_data(ttl=30)
def get_server_context(ssh_alias: str, host: str) -> dict:
    """git 브랜치/상태 + 실행 중인 Docker 컨테이너 목록 반환 (30초 캐시)"""
    if not is_server_online(host):
        return {"available": False}

    # git 상태 + Docker 컨테이너를 1회 SSH 배치 실행
    script = "; ".join([
        f'echo "BRANCH:$(cd {PROJECT_DIR} && git branch --show-current 2>/dev/null || echo N/A)"',
        f'echo "CHANGES:$(cd {PROJECT_DIR} && git status --short 2>/dev/null | head -5 || echo)"',
        f'echo "COMMITS:$(cd {PROJECT_DIR} && git log --oneline -3 2>/dev/null | tr "\\n" "|" || echo N/A)"',
        'echo "CONTAINERS:$(docker ps --format \'{{.Names}}\\t{{.Status}}\' 2>/dev/null | head -8 || echo)"',
    ])
    result = run_cmd(host, script)

    if result.exit_code != 0:
        return {"available": False}

    ctx: dict = {"available": True}
    for line in result.stdout.strip().splitlines():
        if line.startswith("BRANCH:"):
            ctx["branch"] = line[7:].strip()
        elif line.startswith("CHANGES:"):
            ctx["git_changes"] = line[8:].strip() or "없음"
        elif line.startswith("COMMITS:"):
            raw = line[8:].strip()
            ctx["recent_commits"] = raw.replace("|", "\n").strip()
        elif line.startswith("CONTAINERS:"):
            ctx["containers"] = line[11:].strip()

    return ctx
