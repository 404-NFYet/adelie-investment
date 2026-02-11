"""
Plotly 시각화 코드 생성 모델 비교 테스트
Claude (claude-3-5-sonnet) vs OpenAI (gpt-4o-mini) vs OpenAI (gpt-4o)

동일한 프롬프트로 3개 모델의 Plotly 코드 생성 품질을 비교한다.
"""

import os
import sys
import json
import time
import asyncio
import subprocess
import tempfile
from pathlib import Path

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# ========================
# 테스트 프롬프트 (디자인 시스템 포함)
# ========================

SYSTEM_PROMPT = """Python Plotly를 사용하여 시각화 코드를 작성하세요.

## 디자인 규칙
- 주 색상: #FF6B00 (오렌지), 보조: #4A90D9 (파랑)
- 배경: 투명 (paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
- 폰트: 'IBM Plex Sans KR', size=12, color='#4E5968'
- 그리드: color='#F2F4F6'
- 축 레이블: color='#8B95A1', size=11
- 마진: dict(t=50, b=60, l=60, r=30)
- Y축에 반드시 단위 괄호 표기 (예: "PER (배)", "금액 (억 원)")
- 데이터 포인트에 값을 직접 표시 (textposition='outside')
- 깔끔하고 미니멀한 스타일, 한글 사용

## 코드 규칙
- import plotly.graph_objects as go (express도 허용)
- import pandas, numpy 허용
- fig.write_html('/output/chart.html', include_plotlyjs='cdn', full_html=True)
- 코드만 출력, 설명 없이"""

TEST_PROMPTS = [
    {
        "id": "bar_comparison",
        "name": "과거-현재 비교 막대 차트",
        "prompt": """2000년 닷컴버블과 2026년 AI 붐의 PER 비교 막대 차트를 만드세요.
데이터:
- 시스코 (2000년): PER 150배
- 오라클 (2000년): PER 100배
- 엔비디아 (2026년): PER 60배
- MS (2026년): PER 35배
과거는 회색(#ADB5BD), 현재는 오렌지(#FF6B00)로 구분하세요.
각 막대 위에 값을 "150배" 형식으로 표시하세요.""",
    },
    {
        "id": "trend_line",
        "name": "시계열 추이 라인 차트",
        "prompt": """글로벌 AI 자본지출 전망 라인 차트를 만드세요.
데이터:
- 2023: 580억 달러
- 2024: 680억 달러
- 2025: 750억 달러
- 2026(E): 870억 달러
- 2027(E): 960억 달러
라인 색상은 #FF6B00, 영역은 반투명 오렌지로 채우세요.
각 포인트에 값을 표시하세요. Y축: "금액 (억 달러)".""",
    },
    {
        "id": "risk_area",
        "name": "리스크 영역 차트",
        "prompt": """나스닥 지수 하락/회복 패턴 영역 차트를 만드세요.
데이터 (2000=100 기준):
- 2000.03: 100
- 2000.09: 65
- 2001.03: 45
- 2001.09: 35
- 2002.10: 25 (최저점)
- 2003.06: 40
- 2004.01: 55
최저점에 "최대 -75% 하락" 주석을 추가하세요.
하락 영역은 연한 빨강, 회복 영역은 연한 초록으로 표시하세요.
Y축: "지수 (2000.03=100)", X축: "시점".""",
    },
]


# ========================
# 모델 호출 함수
# ========================

async def call_openai(model: str, system: str, prompt: str) -> dict:
    """OpenAI API 호출"""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    start = time.time()
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2000,
        temperature=0.2,
    )
    elapsed = time.time() - start
    
    code = response.choices[0].message.content
    # 코드 블록 제거
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()
    
    return {
        "model": model,
        "code": code,
        "tokens": response.usage.total_tokens if response.usage else 0,
        "latency_s": round(elapsed, 2),
    }


async def call_claude(model: str, system: str, prompt: str) -> dict:
    """Claude API 호출"""
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))
    
    start = time.time()
    response = await client.messages.create(
        model=model,
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    elapsed = time.time() - start
    
    code = response.content[0].text
    # 코드 블록 제거
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()
    
    input_tokens = response.usage.input_tokens if response.usage else 0
    output_tokens = response.usage.output_tokens if response.usage else 0
    
    return {
        "model": model,
        "code": code,
        "tokens": input_tokens + output_tokens,
        "latency_s": round(elapsed, 2),
    }


# ========================
# 코드 실행 및 평가
# ========================

def execute_plotly_code(code: str, output_dir: str) -> dict:
    """Plotly 코드를 실행하고 결과 확인"""
    output_path = os.path.join(output_dir, "chart.html")
    os.makedirs(os.path.join(output_dir), exist_ok=True)
    
    # /output/ 경로를 실제 경로로 치환
    modified_code = code.replace("/output/chart.html", output_path)
    modified_code = modified_code.replace("'/output/", f"'{output_dir}/")
    
    # 임시 파일에 코드 작성
    script_path = os.path.join(output_dir, "script.py")
    with open(script_path, "w") as f:
        f.write(modified_code)
    
    # 실행
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=30,
            cwd=output_dir,
        )
        elapsed = time.time() - start
        
        success = result.returncode == 0 and os.path.exists(output_path)
        html_size = os.path.getsize(output_path) if success else 0
        
        return {
            "success": success,
            "execution_time_s": round(elapsed, 2),
            "html_size_kb": round(html_size / 1024, 1) if success else 0,
            "html_path": output_path if success else None,
            "error": result.stderr[:500] if not success else None,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout (30s)", "execution_time_s": 30}
    except Exception as e:
        return {"success": False, "error": str(e)[:500]}


def evaluate_code_quality(code: str) -> dict:
    """코드 품질 평가 (정적 분석)"""
    checks = {
        "has_write_html": "write_html" in code,
        "has_transparent_bg": "rgba(0,0,0,0)" in code or "transparent" in code.lower(),
        "has_korean_font": "IBM Plex" in code or "Noto Sans" in code or "font" in code.lower(),
        "has_yaxis_unit": any(u in code for u in ["(배)", "(억", "(%)", "(원)", "(달러)", "(포인트)"]),
        "has_text_on_data": "text=" in code or "textposition" in code,
        "has_color_ff6b00": "#FF6B00" in code or "#ff6b00" in code,
        "has_margin": "margin" in code,
        "line_count": code.count("\n") + 1,
    }
    
    score = sum([
        checks["has_write_html"] * 2,
        checks["has_transparent_bg"] * 1,
        checks["has_korean_font"] * 1,
        checks["has_yaxis_unit"] * 2,
        checks["has_text_on_data"] * 2,
        checks["has_color_ff6b00"] * 1,
        checks["has_margin"] * 1,
    ])
    
    return {"checks": checks, "quality_score": score, "max_score": 10}


# ========================
# 메인 테스트
# ========================

async def run_tests():
    """모든 모델 × 모든 프롬프트 조합 테스트"""
    
    models = [
        ("openai", "gpt-4o-mini"),
        ("openai", "gpt-4o"),
        ("claude", "claude-3-5-sonnet-20241022"),
        ("claude", "claude-3-5-haiku-20241022"),
        ("claude", "claude-sonnet-4-20250514"),
    ]
    
    results = []
    output_base = os.path.join(PROJECT_ROOT, "tests", "viz_test_output")
    os.makedirs(output_base, exist_ok=True)
    
    for provider, model in models:
        for test in TEST_PROMPTS:
            print(f"\n{'='*60}")
            print(f"모델: {model} | 테스트: {test['name']}")
            print(f"{'='*60}")
            
            # 1. 코드 생성
            try:
                if provider == "openai":
                    gen_result = await call_openai(model, SYSTEM_PROMPT, test["prompt"])
                else:
                    gen_result = await call_claude(model, SYSTEM_PROMPT, test["prompt"])
            except Exception as e:
                print(f"  ❌ API 호출 실패: {e}")
                results.append({
                    "model": model, "test": test["id"], "test_name": test["name"],
                    "api_error": str(e),
                })
                continue
            
            print(f"  생성 시간: {gen_result['latency_s']}s | 토큰: {gen_result['tokens']}")
            
            # 2. 코드 품질 평가
            quality = evaluate_code_quality(gen_result["code"])
            print(f"  품질 점수: {quality['quality_score']}/{quality['max_score']}")
            for k, v in quality["checks"].items():
                if k != "line_count":
                    status = "✅" if v else "❌"
                    print(f"    {status} {k}")
            
            # 3. 코드 실행
            output_dir = os.path.join(output_base, f"{model.replace('/', '_')}_{test['id']}")
            exec_result = execute_plotly_code(gen_result["code"], output_dir)
            
            if exec_result["success"]:
                print(f"  ✅ 실행 성공: {exec_result['execution_time_s']}s | HTML: {exec_result['html_size_kb']}KB")
                print(f"  📄 파일: {exec_result['html_path']}")
            else:
                print(f"  ❌ 실행 실패: {exec_result.get('error', 'Unknown')[:200]}")
            
            # 결과 저장
            results.append({
                "model": model,
                "test": test["id"],
                "test_name": test["name"],
                "latency_s": gen_result["latency_s"],
                "tokens": gen_result["tokens"],
                "quality_score": quality["quality_score"],
                "quality_max": quality["max_score"],
                "checks": quality["checks"],
                "exec_success": exec_result["success"],
                "exec_time_s": exec_result.get("execution_time_s"),
                "html_size_kb": exec_result.get("html_size_kb"),
                "html_path": exec_result.get("html_path"),
                "exec_error": exec_result.get("error"),
                "code": gen_result["code"],
            })
    
    # ========================
    # 요약 리포트
    # ========================
    print("\n\n" + "=" * 80)
    print("📊 모델 비교 요약 리포트")
    print("=" * 80)
    
    # 모델별 집계
    model_summary = {}
    for r in results:
        m = r["model"]
        if m not in model_summary:
            model_summary[m] = {
                "total": 0, "exec_success": 0, 
                "total_quality": 0, "total_latency": 0, "total_tokens": 0,
            }
        model_summary[m]["total"] += 1
        model_summary[m]["exec_success"] += 1 if r.get("exec_success") else 0
        model_summary[m]["total_quality"] += r.get("quality_score", 0)
        model_summary[m]["total_latency"] += r.get("latency_s", 0)
        model_summary[m]["total_tokens"] += r.get("tokens", 0)
    
    print(f"\n{'모델':<35} {'실행성공':<10} {'품질평균':<10} {'응답시간':<10} {'토큰합계':<10}")
    print("-" * 75)
    for m, s in model_summary.items():
        avg_quality = s["total_quality"] / max(s["total"], 1)
        avg_latency = s["total_latency"] / max(s["total"], 1)
        print(f"{m:<35} {s['exec_success']}/{s['total']:<8} {avg_quality:.1f}/10    {avg_latency:.1f}s      {s['total_tokens']}")
    
    # 결과 JSON 저장
    report_path = os.path.join(output_base, "comparison_report.json")
    with open(report_path, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n상세 리포트: {report_path}")
    
    # 생성된 HTML 파일 목록
    print("\n📄 생성된 시각화 파일:")
    for r in results:
        if r.get("html_path"):
            print(f"  {r['model']} / {r['test_name']}: {r['html_path']}")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_tests())
