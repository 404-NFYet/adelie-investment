"""Adelie Investment 인프라 대시보드 -- 메인 엔트리포인트"""

import streamlit as st

from config import SERVERS, DEPLOY_SERVER
from pages.team_member import render_team_page
from utils.ui_components import inject_custom_css, render_metric_card, render_status_badge
from utils.ssh import is_server_online

st.set_page_config(
    page_title="Adelie 인프라 대시보드",
    page_icon="assets/logo.png" if False else None,  # 로고 파일이 없으면 None
    layout="wide",
)

# 커스텀 CSS 주입
inject_custom_css()

# ── 로고 헤더 ─────────────────────────────────────────────────

st.markdown("""
<div class="logo-header">
    <div class="logo-icon">🐧</div>
    <div>
        <div class="logo-text">Adelie Investment</div>
        <div class="logo-sub">인프라 대시보드 | History Repeats Itself</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── 서버 상태 요약 카드 ─────────────────────────────────────────

# deploy-test 서버 + 개발 서버들의 상태를 요약
all_servers = {**SERVERS, "deploy-test (배포)": DEPLOY_SERVER}
server_count = len(all_servers)

# 상태 캐시 (한 번만 체크)
if "server_status_cache" not in st.session_state:
    st.session_state["server_status_cache"] = {}

cols = st.columns(min(server_count, 6))
online_count = 0
for i, (name, info) in enumerate(all_servers.items()):
    host = info["host"]
    col_idx = i % len(cols)
    with cols[col_idx]:
        # 간단한 이름 추출 (괄호 안 역할)
        short_name = name.split("(")[0].strip() if "(" in name else name
        online = is_server_online(host)
        if online:
            online_count += 1
        badge_html = render_status_badge("Online" if online else "Offline")
        st.markdown(f"""
        <div class="metric-card" style="text-align:center; padding:14px;">
            <div class="card-title">{short_name}</div>
            <div style="font-size:13px; color:#6C757D;">{host}</div>
            <div style="margin-top:6px;">{badge_html}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ── 팀원별 페이지 (callable로 서버 정보 전달) ────────────────────

# 아이콘 매핑
ROLE_ICONS = {
    "frontend": "🖥️",
    "chatbot": "🤖",
    "backend": "⚙️",
    "pipeline": "🔄",
    "infra": "🏗️",
}

team_pages = []
for name, info in SERVERS.items():
    role = info.get("role", "")
    icon = ROLE_ICONS.get(role, "👤")

    def make_page(_name=name, _info=info):
        def page_fn():
            render_team_page(_name, _info)
        return page_fn

    team_pages.append(
        st.Page(
            make_page(),
            title=f"{icon} {name}",
            url_path=info["ssh_alias"],
        )
    )

# 운영 페이지
ops_pages = [
    st.Page("pages/deploy.py", title="🚀 배포 관리"),
    st.Page("pages/db_viewer.py", title="🗄️ DB 뷰어"),
    st.Page("pages/api_tester.py", title="🔌 API 테스트"),
    st.Page("pages/monitoring.py", title="📊 모니터링"),
    st.Page("pages/feedback.py", title="📬 피드백 관리"),
]

nav = st.navigation(
    {
        "💬 챗봇": [st.Page("pages/chatbot.py", title="🤖 서버 어시스턴트")],
        "🖥️ 팀원 서버": team_pages,
        "🎯 운영": ops_pages,
    }
)

nav.run()
