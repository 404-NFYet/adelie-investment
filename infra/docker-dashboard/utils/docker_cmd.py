"""SSH 경유 Docker CLI 래퍼"""

import json

import streamlit as st

from config import PROJECT_DIR, COMPOSE_FILE_DEV
from utils.ssh import run_cmd


@st.cache_data(ttl=10)
def list_containers(host: str) -> list[dict]:
    """docker ps -a → 컨테이너 리스트 반환 (10초 캐시)"""
    fmt = '{"name":"{{.Names}}","image":"{{.Image}}","status":"{{.Status}}","ports":"{{.Ports}}","state":"{{.State}}"}'
    result = run_cmd(host, f'docker ps -a --format \'{fmt}\'')
    if result.exit_code != 0:
        return []

    containers = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        try:
            containers.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return containers


def container_action(host: str, container: str, action: str) -> tuple[bool, str]:
    """컨테이너 start/stop/restart"""
    if action not in ("start", "stop", "restart"):
        return False, f"지원하지 않는 액션: {action}"
    result = run_cmd(host, f'docker {action} "{container}"', timeout=60)
    if result.exit_code == 0:
        list_containers.clear()
        return True, f"{container} {action} 완료"
    return False, result.stderr or result.stdout


def container_logs(host: str, container: str, lines: int = 100) -> str:
    """컨테이너 최근 로그"""
    result = run_cmd(host, f'docker logs --tail {lines} "{container}" 2>&1', timeout=15)
    return result.stdout if result.exit_code == 0 else f"로그 조회 실패: {result.stderr}"


def compose_up(
    host: str, compose_file: str = COMPOSE_FILE_DEV, project_dir: str = PROJECT_DIR
) -> tuple[bool, str]:
    """docker compose up -d"""
    cmd = f'cd {project_dir} && docker compose -f "{compose_file}" up -d 2>&1'
    result = run_cmd(host, cmd, timeout=120)
    if result.exit_code == 0:
        list_containers.clear()
    return result.exit_code == 0, result.stdout + result.stderr


def compose_down(
    host: str, compose_file: str = COMPOSE_FILE_DEV, project_dir: str = PROJECT_DIR
) -> tuple[bool, str]:
    """docker compose down"""
    cmd = f'cd {project_dir} && docker compose -f "{compose_file}" down 2>&1'
    result = run_cmd(host, cmd, timeout=60)
    if result.exit_code == 0:
        list_containers.clear()
    return result.exit_code == 0, result.stdout + result.stderr


def compose_pull(
    host: str, compose_file: str = COMPOSE_FILE_DEV, project_dir: str = PROJECT_DIR
) -> tuple[bool, str]:
    """docker compose pull → up -d"""
    cmd = (
        f'cd {project_dir} && docker compose -f "{compose_file}" pull 2>&1'
        f' && docker compose -f "{compose_file}" up -d 2>&1'
    )
    result = run_cmd(host, cmd, timeout=180)
    if result.exit_code == 0:
        list_containers.clear()
    return result.exit_code == 0, result.stdout + result.stderr


@st.cache_data(ttl=10)
def docker_stats(host: str) -> list[dict]:
    """docker stats --no-stream → CPU/메모리 사용량 (10초 캐시)"""
    fmt = '{"name":"{{.Name}}","cpu":"{{.CPUPerc}}","mem":"{{.MemUsage}}","mem_perc":"{{.MemPerc}}","net":"{{.NetIO}}"}'
    result = run_cmd(host, f'docker stats --no-stream --format \'{fmt}\'', timeout=15)
    if result.exit_code != 0:
        return []

    stats = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        try:
            stats.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return stats
