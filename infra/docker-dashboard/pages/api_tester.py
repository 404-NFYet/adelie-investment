"""OpenAPI 기반 API 테스트 페이지"""

import json

import requests
import streamlit as st

from config import SERVERS, DEPLOY_SERVER
from utils.ui_components import (
    inject_custom_css,
    render_section_header,
    render_http_method_badge,
    render_metric_card,
)

# CSS 주입
inject_custom_css()

# 테스트 대상 서버 목록
TARGET_SERVERS = {}
for name, info in SERVERS.items():
    TARGET_SERVERS[f"{name} ({info['host']})"] = f"http://{info['host']}:{info['port_api']}"
TARGET_SERVERS[f"deploy-test ({DEPLOY_SERVER['host']})"] = f"http://{DEPLOY_SERVER['host']}:{DEPLOY_SERVER['port_api']}"


def fetch_openapi_spec(base_url: str) -> dict | None:
    """서버의 OpenAPI 스펙 가져오기"""
    try:
        resp = requests.get(f"{base_url}/openapi.json", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def extract_endpoints(spec: dict) -> list[dict]:
    """OpenAPI 스펙에서 엔드포인트 목록 추출"""
    endpoints = []
    for path, methods in spec.get("paths", {}).items():
        for method, detail in methods.items():
            if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                endpoints.append({
                    "method": method.upper(),
                    "path": path,
                    "summary": detail.get("summary", ""),
                    "tags": ", ".join(detail.get("tags", [])),
                    "parameters": detail.get("parameters", []),
                    "request_body": detail.get("requestBody"),
                })
    return endpoints


st.title("🔌 API 테스트")

# ── 서버 선택 ─────────────────────────────────────────────

col1, col2 = st.columns([2, 1])
with col1:
    selected_server = st.selectbox("서버 선택", list(TARGET_SERVERS.keys()))
with col2:
    base_url = TARGET_SERVERS[selected_server]
    st.text(f"URL: {base_url}")

# ── JWT 토큰 ─────────────────────────────────────────────

with st.expander("인증 설정"):
    st.caption("JWT 토큰을 입력하면 Authorization 헤더에 자동 포함됩니다.")

    auth_tab_login, auth_tab_manual = st.tabs(["로그인으로 발급", "수동 입력"])

    with auth_tab_login:
        lcol1, lcol2 = st.columns(2)
        with lcol1:
            login_email = st.text_input("이메일", value="test@test.com", key="login_email")
        with lcol2:
            login_password = st.text_input("비밀번호", type="password", value="test1234", key="login_pw")

        if st.button("로그인 -> 토큰 발급"):
            try:
                resp = requests.post(
                    f"{base_url}/api/v1/auth/login",
                    json={"email": login_email, "password": login_password},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    token = data.get("access_token", data.get("token", ""))
                    if token:
                        st.session_state["jwt_token"] = token
                        st.success(f"토큰 발급 완료 (길이: {len(token)})")
                    else:
                        st.warning(f"토큰을 찾을 수 없습니다. 응답: {json.dumps(data, indent=2)[:300]}")
                else:
                    st.error(f"로그인 실패: {resp.status_code} - {resp.text[:300]}")
            except Exception as e:
                st.error(f"요청 실패: {e}")

    with auth_tab_manual:
        manual_token = st.text_input("JWT 토큰", key="manual_token")
        if st.button("저장"):
            st.session_state["jwt_token"] = manual_token
            st.success("토큰 저장 완료")

    if st.session_state.get("jwt_token"):
        st.info(f"현재 토큰: {st.session_state['jwt_token'][:20]}...")

# ── OpenAPI 엔드포인트 목록 ───────────────────────────────

st.divider()

spec = fetch_openapi_spec(base_url)
if spec is None:
    st.error(f"OpenAPI 스펙을 가져올 수 없습니다 ({base_url}/openapi.json)")
    st.stop()

st.success(f"API: {spec.get('info', {}).get('title', 'Unknown')} v{spec.get('info', {}).get('version', '?')}")

endpoints = extract_endpoints(spec)

# 태그별 필터
all_tags = sorted(set(ep["tags"] for ep in endpoints if ep["tags"]))
selected_tags = st.multiselect("태그 필터", all_tags, key="tag_filter")

# 필터링
if selected_tags:
    filtered = [ep for ep in endpoints if ep["tags"] in selected_tags]
else:
    filtered = endpoints

# 엔드포인트 목록 (HTTP 메서드 배지 포함)
render_section_header(f"엔드포인트 ({len(filtered)}개)", "🔗")

# 엔드포인트 선택 리스트 (배지 포함)
endpoint_labels = [
    f"{ep['method']} {ep['path']} -- {ep['summary']}" for ep in filtered
]
selected_idx = st.selectbox(
    "엔드포인트 선택",
    range(len(filtered)),
    format_func=lambda i: endpoint_labels[i],
    key="endpoint_select",
)

if selected_idx is not None and filtered:
    ep = filtered[selected_idx]

    # 메서드 배지 + 경로 표시
    badge_html = render_http_method_badge(ep["method"])
    st.markdown(f"### {badge_html} `{ep['path']}`", unsafe_allow_html=True)
    if ep["summary"]:
        st.caption(ep["summary"])

    # ── 파라미터 입력 ─────────────────────────────────

    # Path/Query 파라미터
    param_values = {}
    if ep["parameters"]:
        st.markdown("**파라미터**")
        for param in ep["parameters"]:
            pname = param.get("name", "")
            pin = param.get("in", "query")
            required = param.get("required", False)
            schema = param.get("schema", {})
            ptype = schema.get("type", "string")
            default = schema.get("default", "")

            label = f"{pname} ({pin})" + (" *" if required else "")
            if ptype == "integer":
                param_values[pname] = {
                    "in": pin,
                    "value": st.number_input(label, value=int(default) if default else 0, key=f"param_{pname}"),
                }
            elif ptype == "boolean":
                param_values[pname] = {
                    "in": pin,
                    "value": st.checkbox(label, value=bool(default), key=f"param_{pname}"),
                }
            else:
                param_values[pname] = {
                    "in": pin,
                    "value": st.text_input(label, value=str(default), key=f"param_{pname}"),
                }

    # Request Body
    body_str = ""
    if ep["request_body"]:
        st.markdown("**Request Body**")
        content = ep["request_body"].get("content", {})
        json_schema = content.get("application/json", {}).get("schema", {})

        # 스키마에서 기본 JSON 템플릿 생성
        template = {}
        properties = json_schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            ptype = prop_schema.get("type", "string")
            if ptype == "string":
                template[prop_name] = ""
            elif ptype == "integer":
                template[prop_name] = 0
            elif ptype == "number":
                template[prop_name] = 0.0
            elif ptype == "boolean":
                template[prop_name] = False
            elif ptype == "array":
                template[prop_name] = []
            else:
                template[prop_name] = None

        body_str = st.text_area(
            "JSON Body",
            value=json.dumps(template, indent=2, ensure_ascii=False),
            height=200,
            key="request_body",
        )

    # ── 요청 전송 ─────────────────────────────────────

    if st.button("요청 전송", type="primary"):
        # URL 조립
        url = base_url + ep["path"]

        # Path 파라미터 치환
        query_params = {}
        for pname, pinfo in param_values.items():
            if pinfo["in"] == "path":
                url = url.replace(f"{{{pname}}}", str(pinfo["value"]))
            elif pinfo["in"] == "query" and pinfo["value"]:
                query_params[pname] = pinfo["value"]

        # 헤더
        headers = {"Content-Type": "application/json"}
        if st.session_state.get("jwt_token"):
            headers["Authorization"] = f"Bearer {st.session_state['jwt_token']}"

        # 요청 전송
        try:
            method = ep["method"]
            kwargs = {
                "headers": headers,
                "params": query_params if query_params else None,
                "timeout": 30,
            }

            if body_str and method in ("POST", "PUT", "PATCH"):
                kwargs["json"] = json.loads(body_str)

            resp = requests.request(method, url, **kwargs)

            # 응답 표시
            st.divider()
            render_section_header("응답 결과", "📨")

            col1, col2 = st.columns(2)
            with col1:
                # 상태 코드 색상
                if resp.status_code < 300:
                    st.markdown(f'<span style="font-size:24px; font-weight:700; color:#28A745;">{resp.status_code}</span> '
                                f'<span style="color:#6C757D;">{resp.reason}</span>',
                                unsafe_allow_html=True)
                elif resp.status_code < 400:
                    st.markdown(f'<span style="font-size:24px; font-weight:700; color:#FFC107;">{resp.status_code}</span> '
                                f'<span style="color:#6C757D;">{resp.reason}</span>',
                                unsafe_allow_html=True)
                else:
                    st.markdown(f'<span style="font-size:24px; font-weight:700; color:#DC3545;">{resp.status_code}</span> '
                                f'<span style="color:#6C757D;">{resp.reason}</span>',
                                unsafe_allow_html=True)
            with col2:
                st.text(f"소요 시간: {resp.elapsed.total_seconds():.3f}s")

            # 응답 헤더
            with st.expander("응답 헤더"):
                st.json(dict(resp.headers))

            # 응답 바디
            st.markdown("**응답 바디**")
            try:
                body = resp.json()
                # JSON 하이라이팅
                st.code(json.dumps(body, indent=2, ensure_ascii=False), language="json")
            except Exception:
                st.code(resp.text[:5000])

        except json.JSONDecodeError:
            st.error("JSON Body 파싱 실패 -- 올바른 JSON을 입력해주세요.")
        except Exception as e:
            st.error(f"요청 실패: {e}")

# ── 프리셋 시나리오 ───────────────────────────────────────

st.divider()
render_section_header("프리셋 시나리오", "🎯")

with st.expander("로그인 -> 키워드 조회 -> 케이스 조회"):
    st.caption("순차적으로 API를 호출하여 전체 플로우를 테스트합니다.")

    preset_email = st.text_input("이메일", value="test@test.com", key="preset_email")
    preset_password = st.text_input("비밀번호", type="password", value="test1234", key="preset_pw")

    if st.button("시나리오 실행"):
        # 1. 로그인
        st.markdown(f"**1. 로그인** {render_http_method_badge('POST')}", unsafe_allow_html=True)
        try:
            resp = requests.post(
                f"{base_url}/api/v1/auth/login",
                json={"email": preset_email, "password": preset_password},
                timeout=10,
            )
            st.code(json.dumps({"status": resp.status_code, "body": resp.json() if resp.status_code == 200 else resp.text[:200]}, indent=2, ensure_ascii=False), language="json")

            if resp.status_code != 200:
                st.error("로그인 실패 -- 시나리오 중단")
                st.stop()

            token = resp.json().get("access_token", resp.json().get("token", ""))
            auth_headers = {"Authorization": f"Bearer {token}"}
        except Exception as e:
            st.error(f"로그인 요청 실패: {e}")
            st.stop()

        # 2. 오늘의 키워드
        st.markdown(f"**2. 오늘의 키워드** {render_http_method_badge('GET')}", unsafe_allow_html=True)
        try:
            resp = requests.get(
                f"{base_url}/api/v1/keywords/today",
                headers=auth_headers,
                timeout=10,
            )
            data = resp.json() if resp.status_code == 200 else resp.text[:300]
            st.code(json.dumps({"status": resp.status_code, "body": data}, indent=2, ensure_ascii=False), language="json")
        except Exception as e:
            st.warning(f"키워드 조회 실패: {e}")

        # 3. 케이스 조회
        st.markdown(f"**3. 케이스 조회** {render_http_method_badge('GET')}", unsafe_allow_html=True)
        try:
            resp = requests.get(
                f"{base_url}/api/v1/cases",
                headers=auth_headers,
                params={"limit": 3},
                timeout=10,
            )
            data = resp.json() if resp.status_code == 200 else resp.text[:300]
            st.code(json.dumps({"status": resp.status_code, "body": data}, indent=2, ensure_ascii=False), language="json")
        except Exception as e:
            st.warning(f"케이스 조회 실패: {e}")
