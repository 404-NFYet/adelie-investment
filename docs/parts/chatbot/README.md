# Chatbot 개발 가이드 — 정지훈

## 환경 정보
| 항목 | 값 |
|------|-----|
| 컨테이너 | dev-j2hoon10 (10.10.10.11) |
| 리소스 | 4 CPU / 12GB RAM / 150GB Disk |
| 브랜치 | `dev/chatbot` |
| Git | J2hoon10 <myhome559755@naver.com> |
| SSH | `ssh dev-j2hoon10` (ProxyJump: hj-server) |

## 환경 확인 체크리스트
- [ ] SSH 접속 확인: `ssh dev-j2hoon10`
- [ ] 브랜치: `git branch --show-current` → `dev/chatbot`
- [ ] .env API 키: `grep OPENAI_API_KEY .env | head -c30`
- [ ] .env Perplexity: `grep PERPLEXITY_API_KEY .env | head -c30`
- [ ] .env LangChain: `grep LANGCHAIN_API_KEY .env | head -c30`
- [ ] Docker: `docker ps` → adelie-postgres, adelie-redis 실행 중
- [ ] venv 활성화: `source .venv/bin/activate`
- [ ] 백엔드 실행: `.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload`
- [ ] 튜터 API 확인: `curl -X POST http://localhost:8082/api/v1/tutor/chat -H "Authorization: Bearer <token>" -d '{"message":"안녕"}'`

## 주요 명령어
| 작업 | 명령어 |
|------|--------|
| 백엔드 실행 (로컬) | `.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload` |
| 전체 스택 (Docker) | `docker compose -f docker-compose.dev.yml up` |
| 단위 테스트 | `pytest tests/unit/ -v -k tutor` |
| 프롬프트 테스트 | `.venv/bin/python -c "from chatbot.agent.prompts import get_system_prompt; print(get_system_prompt('beginner'))"` |
| LangSmith 추적 확인 | 브라우저에서 https://smith.langchain.com 접속 |
| Docker 빌드 | `docker build -t dorae222/adelie-backend-api:dev-$(git rev-parse --short HEAD) -f fastapi/Dockerfile .` |

## 개발 워크플로우
1. `dev/chatbot`에서 작업 → 커밋 (`type: 한글 설명`) → push
2. develop으로 PR → 최소 1명 리뷰 → squash merge
3. 커밋 전: `git config user.name` = `J2hoon10` 확인

## 코드 위치
| 모듈 | 경로 | 설명 |
|------|------|------|
| 튜터 에이전트 | `chatbot/agent/tutor_agent.py` | LangGraph 기반 실험 에이전트 |
| 프로덕션 엔진 | `fastapi/app/services/tutor_engine.py` | SSE 스트리밍 응답 생성 (현재 사용 중) |
| 도구 (tools) | `chatbot/tools/` | LangChain 도구 5종 |
| 프롬프트 | `chatbot/prompts/templates/` | 마크다운 기반 프롬프트 7개 |
| 체크포인터 | `chatbot/agent/checkpointer.py` | PostgreSQL 세션 영속화 |
| 용어 하이라이트 | `chatbot/services/term_highlighter.py` | 텍스트 내 용어 감지 + 하이라이트 |

## 이 폴더의 문서
- [architecture.md](architecture.md) — LangGraph 구조, 도구 목록, SSE 흐름, 프롬프트
- [roadmap.md](roadmap.md) — P0/P1/P2 개선 과제
- [dependencies.md](dependencies.md) — 다른 파트 변경 시 대응법
