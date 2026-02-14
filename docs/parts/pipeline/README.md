# Data Pipeline 개발 가이드 — 안례진

## 환경 정보
| 항목 | 값 |
|------|-----|
| 컨테이너 | dev-ryejinn (10.10.10.13) |
| 리소스 | 4 CPU / 12GB RAM / 150GB Disk |
| 브랜치 | `dev/pipeline` |
| Git | ryejinn <arj1018@ewhain.net> |
| SSH | `ssh dev-ryejinn` (ProxyJump: hj-server) |

## 환경 확인 체크리스트
- [ ] SSH 접속 확인: `ssh dev-ryejinn`
- [ ] 브랜치: `git branch --show-current` → `dev/pipeline`
- [ ] .env API 키: `grep OPENAI_API_KEY .env | head -c30`
- [ ] Docker: `docker ps` → adelie-postgres, adelie-redis 실행 중
- [ ] Mock 테스트: `.venv/bin/python -m datapipeline.run --backend mock`
- [ ] LangSmith: https://smith.langchain.com

## 주요 명령어
| 작업 | 명령어 |
|------|--------|
| 테스트 실행 (LLM 미호출) | `.venv/bin/python -m datapipeline.run --backend mock` |
| 실서비스 실행 | `.venv/bin/python -m datapipeline.run --backend live --market KR` |
| 단위 테스트 | `.venv/bin/pytest datapipeline/tests/ -v` |
| LangSmith | https://smith.langchain.com |

## 개발 워크플로우
1. `dev/pipeline`에서 작업 → 커밋 (`type: 한글 설명`) → push
2. develop으로 PR → 최소 1명 리뷰 → squash merge
3. 커밋 전: `git config user.name` = `ryejinn` 확인

## 이 폴더의 문서
- [architecture.md](architecture.md) — 18노드 LangGraph 그래프, 데이터 수집, LLM 클라이언트
- [roadmap.md](roadmap.md) — P0/P1/P2 개선 과제
- [dependencies.md](dependencies.md) — 다른 파트 변경 시 대응법
