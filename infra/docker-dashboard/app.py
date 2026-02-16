"""Adelie Investment 인프라 대시보드 — 메인 엔트리포인트"""

import streamlit as st

from config import SERVERS
from pages.team_member import render_team_page

st.set_page_config(
    page_title="Adelie 인프라 대시보드",
    page_icon="🐧",
    layout="wide",
)

# 팀원별 페이지 (callable로 서버 정보 전달)
team_pages = []
for name, info in SERVERS.items():
    def make_page(_name=name, _info=info):
        def page_fn():
            render_team_page(_name, _info)
        return page_fn

    team_pages.append(
        st.Page(
            make_page(),
            title=name,
            url_path=info["ssh_alias"],
        )
    )

# 운영 페이지
ops_pages = [
    st.Page("pages/deploy.py", title="배포 관리", icon="🚀"),
    st.Page("pages/db_viewer.py", title="DB 뷰어", icon="🗄️"),
    st.Page("pages/api_tester.py", title="API 테스트", icon="🔌"),
    st.Page("pages/monitoring.py", title="모니터링", icon="📊"),
    st.Page("pages/feedback.py", title="피드백 관리", icon="📬"),
]

nav = st.navigation(
    {
        "팀원 서버": team_pages,
        "운영": ops_pages,
    }
)

nav.run()
