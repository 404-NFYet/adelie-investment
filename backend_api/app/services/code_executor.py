"""Python 코드 실행 서비스 (Plotly 시각화 전용)"""
import glob as _glob
import os, sys, tempfile, subprocess, time, logging, re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

ALLOWED_IMPORTS = ['plotly', 'pandas', 'numpy', 'json', 'math', 'datetime']
BLOCKED_PATTERNS = [
    'os.system', 'subprocess', 'shutil', '__import__', 'eval(', 'exec(',
    'import socket', 'import http', 'open(', 'import os',
    'globals(', 'locals(', '__builtins__', 'compile(', 'breakpoint(',
    'import signal', 'import ctypes', 'import importlib',
    'getattr(', 'setattr(', 'delattr(', '__class__',
    'import pickle', 'import marshal', 'import code',
]

@dataclass
class ExecutionResult:
    success: bool
    output_html: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: int = 0

class LocalExecutor:
    """로컬 subprocess 기반 코드 실행기"""
    
    def validate_code(self, code: str) -> tuple[bool, str]:
        """코드 안전성 검증"""
        for pattern in BLOCKED_PATTERNS:
            if pattern in code:
                return False, f"차단된 패턴: {pattern}"
        for line in code.split('\n'):
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                module = stripped.split()[1].split('.')[0]
                if module not in ALLOWED_IMPORTS:
                    return False, f"허용되지 않은 모듈: {module}"
        return True, ""
    
    def _prepare_code(self, code: str, output_dir: str) -> str:
        """코드 내 출력 경로를 치환하고, write_html이 없으면 자동 추가."""
        chart_path = os.path.join(output_dir, "chart.html")
        
        # 다양한 경로 패턴 치환 (작은따옴표, 큰따옴표, 상대경로 등)
        modified = code
        for pattern in [
            "/output/chart.html", "./output/chart.html", "output/chart.html",
            "chart.html",
        ]:
            modified = modified.replace(f"'{pattern}'", f"'{chart_path}'")
            modified = modified.replace(f'"{pattern}"', f'"{chart_path}"')
        
        # write_html 호출이 없으면 마지막에 자동 추가
        if "write_html" not in modified and "fig" in modified:
            modified += f"\nfig.write_html('{chart_path}', include_plotlyjs='cdn', full_html=True)\n"
        
        return modified
    
    def _find_html_output(self, output_dir: str, tmpdir: str) -> Optional[str]:
        """output 디렉토리와 tmpdir에서 html 파일을 찾아 내용을 반환."""
        # 1) 지정된 경로
        chart_path = os.path.join(output_dir, "chart.html")
        if os.path.exists(chart_path):
            with open(chart_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        # 2) output 디렉토리 내 아무 html
        for html_file in _glob.glob(os.path.join(output_dir, "*.html")):
            with open(html_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        # 3) tmpdir 루트에 생성된 html
        for html_file in _glob.glob(os.path.join(tmpdir, "*.html")):
            with open(html_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        return None
    
    async def execute(self, code: str, timeout: int = 30) -> ExecutionResult:
        """코드 실행"""
        start = time.time()
        
        is_safe, reason = self.validate_code(code)
        if not is_safe:
            return ExecutionResult(success=False, error=reason)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, 'output')
            os.makedirs(output_dir)
            
            modified = self._prepare_code(code, output_dir)
            
            script_path = os.path.join(tmpdir, 'script.py')
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(modified)
            
            try:
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True, text=True, timeout=timeout,
                    cwd=tmpdir,
                )
                
                if result.returncode != 0:
                    logger.warning("코드 실행 실패 (rc=%d): %s", result.returncode, result.stderr[:300])
                
                elapsed_ms = int((time.time() - start) * 1000)
                
                # html 파일을 유연하게 탐색
                html = self._find_html_output(output_dir, tmpdir)
                
                if result.returncode == 0 and html:
                    return ExecutionResult(
                        success=True, output_html=html, execution_time_ms=elapsed_ms
                    )
                else:
                    error = result.stderr[:500] if result.stderr else "출력 파일이 생성되지 않았습니다"
                    return ExecutionResult(
                        success=False, error=error, execution_time_ms=elapsed_ms
                    )
            except subprocess.TimeoutExpired:
                return ExecutionResult(success=False, error=f"실행 시간 초과 ({timeout}초)")
            except Exception as e:
                return ExecutionResult(success=False, error=str(e)[:500])

_executor = None
def get_executor() -> LocalExecutor:
    global _executor
    if _executor is None:
        _executor = LocalExecutor()
    return _executor
