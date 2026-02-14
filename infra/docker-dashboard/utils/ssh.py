"""Paramiko SSH 연결 풀 + 명령 실행 유틸리티"""

import threading
from dataclasses import dataclass

import paramiko

from config import SSH_USER, SSH_KEY_PATH


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int


class SSHManager:
    """서버별 SSH 연결을 관리하는 싱글턴 매니저"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._connections: dict[str, paramiko.SSHClient] = {}
                    cls._instance._conn_lock = threading.Lock()
        return cls._instance

    def _create_client(self, host: str) -> paramiko.SSHClient:
        """새 SSH 클라이언트 생성"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            pkey = paramiko.Ed25519Key.from_private_key_file(SSH_KEY_PATH)
            client.connect(
                hostname=host,
                username=SSH_USER,
                pkey=pkey,
                timeout=10,
                banner_timeout=10,
            )
        except Exception as e:
            raise ConnectionError(f"SSH 연결 실패 ({host}): {e}")
        return client

    def get_connection(self, host: str) -> paramiko.SSHClient:
        """기존 연결 재사용 또는 새 연결 생성"""
        with self._conn_lock:
            client = self._connections.get(host)
            if client is not None:
                # 연결 유효성 검사
                transport = client.get_transport()
                if transport is not None and transport.is_active():
                    return client
                # 연결 끊김 — 재생성
                try:
                    client.close()
                except Exception:
                    pass

            client = self._create_client(host)
            self._connections[host] = client
            return client

    def run_command(self, host: str, cmd: str, timeout: int = 30) -> CommandResult:
        """SSH로 명령 실행 후 결과 반환"""
        try:
            client = self.get_connection(host)
            _, stdout_ch, stderr_ch = client.exec_command(cmd, timeout=timeout)
            exit_code = stdout_ch.channel.recv_exit_status()
            stdout = stdout_ch.read().decode("utf-8", errors="replace")
            stderr = stderr_ch.read().decode("utf-8", errors="replace")
            return CommandResult(stdout=stdout, stderr=stderr, exit_code=exit_code)
        except ConnectionError:
            raise
        except Exception as e:
            # 연결이 끊어졌을 수 있으므로 캐시에서 제거
            with self._conn_lock:
                self._connections.pop(host, None)
            return CommandResult(stdout="", stderr=f"명령 실행 실패: {e}", exit_code=-1)

    def check_server_alive(self, host: str) -> bool:
        """서버 SSH 접속 가능 여부 확인"""
        try:
            result = self.run_command(host, "echo ok", timeout=5)
            return result.exit_code == 0 and "ok" in result.stdout
        except Exception:
            return False

    def close_all(self):
        """모든 연결 종료"""
        with self._conn_lock:
            for client in self._connections.values():
                try:
                    client.close()
                except Exception:
                    pass
            self._connections.clear()


# 전역 인스턴스
ssh_manager = SSHManager()


def run_cmd(host: str, cmd: str, timeout: int = 30) -> CommandResult:
    """편의 함수: SSH 명령 실행"""
    return ssh_manager.run_command(host, cmd, timeout)


def is_server_online(host: str) -> bool:
    """편의 함수: 서버 온라인 여부"""
    return ssh_manager.check_server_alive(host)
