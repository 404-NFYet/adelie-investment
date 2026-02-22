"""팀원 전용 서버 어시스턴트 챗봇 — 서버별 컨텍스트 자동 주입"""

import streamlit as st

from config import SERVER_ROLES
from utils.claude_client import stream_response
from utils.context_collector import get_server_context
from utils.ui_components import inject_custom_css

inject_custom_css()

# ── 역할별 핵심 지식 ─────────────────────────────────────────────

_ROLE_KNOWLEDGE = {
    "frontend": """
[담당 영역] React 19, Vite, Tailwind CSS, Playwright E2E
핵심 파일: frontend/src/App.jsx(라우터), api/client.js(fetchJson/postJson)
E2E: frontend/e2e/*.spec.js, TIMEOUT={fast:5000, network:10000, llm:20000}
data-testid 규칙: {도메인}-{역할}-{타입} (예: portfolio-buy-btn)
npm run dev → :3001, nginx /api/v1/* → backend-api:8082
번들 최적화: React.lazy + Suspense 코드 분할 필수
""",
    "backend": """
[담당 영역] FastAPI async, SQLAlchemy mapped_column, Alembic, JWT
핵심: fastapi/app/main.py(21개 라우터 동적 import), app/core/security.py
Alembic: cd ~/adelie-investment/database && ../.venv/bin/alembic upgrade head
마이그레이션 충돌 방지: #migration 채널 알림 후 순차 작성
새 라우터: routes/*.py 추가 시 main.py 자동 감지(importlib)
KST 날짜: from datetime import timezone, timedelta; KST = timezone(timedelta(hours=9))
""",
    "chatbot": """
[담당 영역] LangGraph tutor_agent, 5개 tool(search/briefing/comparison/visualization/glossary), SSE 스트리밍
주의: chatbot/agent/tutor_agent.py = EXPERIMENTAL (프로덕션 미사용)
프로덕션 튜터: fastapi/app/services/tutor_engine.py (직접 OpenAI 호출)
LangSmith: LANGCHAIN_API_KEY, LANGCHAIN_TRACING_V2=true
SSE 스트리밍: EventSource + async generator 패턴
""",
    "pipeline": """
[담당 영역] 18노드 LangGraph DAG, 데이터 수집→내러티브→DB 저장
노드 추가: datapipeline/nodes/ 파일 + graph.py add_node/add_edge
테스트: python -m datapipeline.run --backend mock (LLM 미호출)
DB 저장: datapipeline/db/writer.py, 5테이블(daily_briefings, briefing_stocks, historical_cases, case_matches, case_stock_relations)
에러 라우터: 신규 노드에 check_error 조건 분기 필수
KST 날짜: from datapipeline.config import KST, kst_today
""",
    "infra": """
[담당 영역] Docker, LXD 5대, CI/CD, Terraform AWS, Prometheus/Grafana/AlertManager
핵심 Makefile: make -f lxd/Makefile sync-lxd|health-lxd|deploy-staging|deploy-test
LXD 프로파일: dev-standard(4CPU/8GB), dev-ai(4CPU/12GB)
Terraform: infra/terraform/ (network/compute/database/storage/cdn 모듈)
모니터링: infra/monitoring/ (prometheus.yml, alertmanager, grafana)
Cloudflare Tunnel 재연결: cloudflared tunnel run <name>
""",
}

# ── 작업 포커스 옵션 ─────────────────────────────────────────────

_TASK_OPTIONS = {
    "frontend": ["새 컴포넌트/페이지 개발", "스타일링/반응형", "E2E 테스트 작성", "빌드/번들 최적화", "배포 이슈"],
    "backend":  ["DB/마이그레이션", "새 API 라우터 개발", "테스트 작성", "인증/JWT", "배포 이슈"],
    "chatbot":  ["LangGraph 노드 개발", "SSE 스트리밍", "LangSmith 트레이싱", "프롬프트 튜닝", "배포 이슈"],
    "pipeline": ["새 노드 개발", "DB 저장 디버그", "LLM 호출/retry", "mock 테스트", "배포 이슈"],
    "infra":    ["Docker/컨테이너", "LXD 서버 관리", "배포 자동화", "모니터링/alert", "Terraform/AWS"],
}

# ── 시나리오 버튼 정의 ────────────────────────────────────────────

_COMMON_SCENARIOS = [
    ("🔌 DB 연결 안 돼", "DB 연결이 안 됩니다. 원인과 해결 방법을 단계별로 알려주세요."),
    ("🔄 develop 반영", "upstream develop 변경사항을 내 브랜치에 반영하는 방법을 알려주세요."),
    ("📌 내 브랜치는?", "현재 내 브랜치 상태와 다음 작업 흐름을 확인해주세요."),
    ("🐳 컨테이너 재시작 반복", "Docker 컨테이너가 계속 재시작됩니다. 원인 진단 방법을 알려주세요."),
]

_ROLE_SCENARIOS = {
    "frontend": [
        ("🖼️ 새 페이지 추가", "React Router에 새 페이지를 추가하는 순서를 알려주세요. (lazy load + route 포함)"),
        ("🧪 E2E 테스트 실패", "Playwright E2E 테스트가 실패할 때 체크해야 할 목록을 알려주세요."),
        ("📦 빌드 용량 최적화", "Vite 번들 크기가 너무 큽니다. 최적화 방법을 알려주세요."),
    ],
    "backend": [
        ("🗄️ Alembic 충돌 해결", "Alembic 마이그레이션 충돌이 났습니다. 해결 방법을 알려주세요."),
        ("📝 새 라우터 추가", "FastAPI 새 라우터를 추가하는 순서를 알려주세요. (router → main.py 등록 포함)"),
        ("🔐 JWT 처리 패턴", "JWT 토큰 만료 처리와 refresh 패턴을 알려주세요."),
    ],
    "chatbot": [
        ("🤖 LangGraph 노드 에러 처리", "LangGraph 노드에서 에러 처리를 추가하는 방법을 알려주세요."),
        ("📡 SSE 스트리밍 끊김", "SSE 스트리밍이 중간에 끊깁니다. 원인과 해결 방법을 알려주세요."),
        ("🔍 LangSmith trace 안됨", "LangSmith에 trace가 찍히지 않습니다. 설정을 확인해주세요."),
    ],
    "pipeline": [
        ("🔧 새 노드 추가 절차", "LangGraph 파이프라인에 새 노드를 추가하는 절차를 알려주세요."),
        ("🧪 mock 테스트 방법", "파이프라인을 mock 모드로 테스트하는 방법을 알려주세요."),
        ("💾 DB 저장 실패", "파이프라인 DB 저장이 실패합니다. writer.py 디버그 방법을 알려주세요."),
        ("⚡ LLM 호출 실패", "LLM 호출 실패 시 retry 처리 방법을 알려주세요."),
    ],
    "infra": [
        ("🚀 deploy-test 배포", "deploy-test 서버에 배포하는 명령을 한 번에 알려주세요."),
        ("🔧 LXD 서버 동기화", "LXD 5대 서버를 develop 최신으로 동기화하는 순서를 알려주세요."),
        ("📊 Prometheus alert 추가", "Prometheus에 새 alert rule을 추가하는 방법을 알려주세요."),
        ("🌐 Cloudflare Tunnel 재연결", "Cloudflare Tunnel이 끊겼을 때 재연결하는 방법을 알려주세요."),
    ],
}


def _build_system_prompt(info: dict, ctx: dict, task: str | None) -> str:
    role_ctx = _ROLE_KNOWLEDGE.get(info["role"], "")
    task_ctx = f"\n[현재 작업 포커스]\n{task}" if task else ""
    containers = ctx.get("containers", "N/A")
    branch = ctx.get("branch", info["branch"])
    git_changes = ctx.get("git_changes", "없음")
    recent_commits = ctx.get("recent_commits", "N/A")

    return f"""Adelie Investment 내부 개발 어시스턴트입니다.

[프로젝트 스택]
React 19+Vite / FastAPI / LangGraph / PostgreSQL(pgvector) / Redis / Docker / LXD

[브랜치 전략]
main ← develop ← dev/frontend|backend|chatbot|pipeline|infra
feature/* → develop PR 머지

[인프라 구성]
- infra-server 10.10.10.10: 공유 dev DB(5432), Redis(6379), Prometheus(9090)
- deploy-test  10.10.10.20: 프로덕션 풀스택
- staging      10.10.10.21: develop 최신
- LXD 5대      10.10.10.11~15: 팀원별 개발 환경

[DB 접속]
공유 dev: postgresql+asyncpg://narative:password@10.10.10.10:5432/narrative_invest
로컬 컨테이너: postgresql+asyncpg://narative:password@postgres:5432/narrative_invest
Alembic HEAD: 20260218_unique_user_portfolio
실행: cd ~/adelie-investment/database && ../.venv/bin/alembic upgrade head

[현재 사용자]
이름: {info['name']}  담당: {info['role']}
서버: {info['server']} ({info['host']})  기본 브랜치: {info['branch']}

[서버 실시간 상태]
현재 브랜치: {branch}
최근 커밋:
{recent_commits}
변경사항: {git_changes}
실행 중 컨테이너:
{containers}
{role_ctx}{task_ctx}

한국어로 답변하세요. 실행 가능한 명령어는 코드블록으로 제공하세요.
경로는 ~/adelie-investment 기준으로 명시하세요.""".strip()


def render():
    st.title("💬 서버 어시스턴트")

    identity_key = st.session_state.get("identity")

    # ── Step 1: 신원 선택 ─────────────────────────────────────────
    if not identity_key:
        st.markdown("**나는 누구인가요?**  _(대화 기록은 이 세션 동안 유지됩니다)_")
        st.caption("신원을 선택하면 해당 서버 컨텍스트가 자동으로 주입됩니다.")
        st.write("")
        cols = st.columns(5)
        for i, (key, info) in enumerate(SERVER_ROLES.items()):
            if cols[i].button(
                f"{info['icon']} {info['name']}",
                use_container_width=True,
                key=f"id_select_{key}",
            ):
                st.session_state["identity"] = key
                st.session_state["identity_ctx_done"] = False
                st.rerun()
        return

    info = {**SERVER_ROLES[identity_key], "server": identity_key}

    # ── Step 2: 작업 컨텍스트 선택 ───────────────────────────────
    if not st.session_state.get("identity_ctx_done"):
        st.subheader(f"{info['icon']} {info['name']} 님 — 작업 컨텍스트 (선택 사항)")
        task_opts = ["(선택 안 함)"] + _TASK_OPTIONS.get(info["role"], [])
        task = st.radio(
            "지금 하는 작업:",
            task_opts,
            horizontal=True,
            key="task_radio",
        )
        c1, c2 = st.columns([1, 5])
        if c1.button("✅ 시작하기", type="primary"):
            st.session_state["current_task"] = None if task == "(선택 안 함)" else task
            st.session_state["identity_ctx_done"] = True
            st.rerun()
        if c2.button("↩️ 다시 선택"):
            st.session_state.pop("identity", None)
            st.rerun()
        return

    # ── Step 3: 채팅 인터페이스 ──────────────────────────────────
    task = st.session_state.get("current_task")
    ctx  = get_server_context(identity_key, info["host"])

    # 헤더 (컴팩트)
    hcol1, hcol2 = st.columns([6, 1])
    branch_display = ctx.get("branch", info["branch"]) if ctx.get("available") else info["branch"]
    task_label = f" | 📋 {task}" if task else ""
    server_status = "🟢" if ctx.get("available") else "🔴"
    hcol1.markdown(
        f"**{info['icon']} {info['name']}** | `{identity_key}` ({info['host']}) | `{branch_display}`{task_label} {server_status}"
    )
    if hcol2.button("↔️ 전환"):
        for k in ("identity", "identity_ctx_done", "current_task"):
            st.session_state.pop(k, None)
        st.rerun()

    if ctx.get("containers"):
        st.caption(f"🐳 {ctx['containers'][:150]}")

    st.divider()

    # 시나리오 버튼
    scenarios = _ROLE_SCENARIOS.get(info["role"], []) + _COMMON_SCENARIOS
    scols = st.columns(3)
    for i, (label, prompt) in enumerate(scenarios):
        if scols[i % 3].button(label, key=f"sc_{i}_{identity_key}"):
            msgs_key = f"msgs_{identity_key}"
            st.session_state.setdefault(msgs_key, []).append(
                {"role": "user", "content": prompt}
            )
            st.rerun()

    st.divider()

    msgs_key = f"msgs_{identity_key}"
    msgs: list[dict] = st.session_state.setdefault(msgs_key, [])

    # 대화 이력 렌더링
    for msg in msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 입력창 + 스트리밍 응답
    if user_input := st.chat_input("질문을 입력하세요...", key=f"inp_{identity_key}"):
        msgs.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        system = _build_system_prompt(info, ctx, task)
        with st.chat_message("assistant"):
            response = st.write_stream(stream_response(msgs, system))
        msgs.append({"role": "assistant", "content": response})
        st.rerun()

    # 대화 초기화
    if msgs and st.button("🗑️ 대화 초기화", key=f"clear_{identity_key}"):
        st.session_state[msgs_key] = []
        st.rerun()


render()
