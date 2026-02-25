# 변경 이력 (Changelog)

> 대상 독자: 전체 팀원
> 날짜별 변경 사항을 카테고리별로 정리합니다.

> **브랜딩 변경 (2026-02)**: "아델리에 투자" → "아델리에", 교육 중심 메시징 강화
> 이후 항목 작성 시: "포트폴리오" (모의투자 대신), "금융 학습" (투자 교육 대신)

---

## prod-final (2026-02-24~25)

### 인프라
- Docker 이미지 태그 정책 변경: `:latest` 제거, `prod-YYYYMMDD` 명시적 태그 (afa4721)
- 로그 네임스페이스 통일: `narrative_api.*` → `narrative.*` 전체 13파일 (0a9c492)
- deploy-test → LXD 콘텐츠 데이터 동기화 스크립트 추가 (f75d752)
- lxd/Makefile 싱크 타겟 브랜치명 `dev-final/*` 전환 (77921fe)
- 브랜치 전략 & 워크플로우 문서 전면 재작성 (7464814)

### 파이프라인
- datapipeline 최신 코드 반영 (147ad7a)
- interface2/3 텍스트 포맷팅 개선 (4fc6a05)

---

## v1.2.1-stable-feb20 (2026-02-20)

### 기능 추가
- AI 튜터 FAB 활성화 + `/tutor` 자동 오픈 (091a1bb)

### 인프라
- CI/CD 재설계 + Makefile 섹션 정리 (41cd8e0)
- frontend-dev 이미지 태그 관리 개선 (87fd2c4, 5897ddd)
- LXD 개인 로컬 DB 환경 전환 (a5379e7, dev-local-db-setup)
- DB 동기화 범위 확장 — 7개 → 31개 테이블 (9915edb)
- Alembic migration 동기화 (db79485)

### 프론트엔드
- Agent Canvas v3: canvas API + UI 컴포넌트 (3a0789b, 91eb89e, 1c7b91c)
- AgentDock 채팅 모드 분리 및 잔여 참조 제거 (b2476bd, 74d400f)

---

## v1.2 (2026-02-22)

### 인프라
- AWS Terraform 인프라 초기 구성: VPC, ECS, RDS, CloudFront, ECR (6cfa989)
- AWS IAM 권한 요청서 추가 (1e04722)

### 테스트
- Playwright 모바일 9종 project 추가 (d59715c)
- Landing/Quiz/AgentCanvas 모바일 E2E 테스트 (5928f14, 4fc10aa)

### UI/UX
- Landing 반응형 리팩토링: clamp 타이포, 이미지 위치 (69b5831)
- DailyQuizModal sticky 헤더, 터치 영역 최적화 (b3c88ae)
- Agent Canvas 컴포넌트 반응형 최적화 360-440px (6d2be94)

### 문서
- 프로젝트 소개 및 기능 목록 최신화 (7706080)
- 인프라 운영 이력 및 LXD 자동화 가이드 (1fb2af3)

---

## v1.1 (2026-02-19~20)

### 기능 추가
- Agent Canvas v3 머지: 에이전트 채팅 시스템, UX v5 (a0b03b2)
- 피드백 설문 페이지 및 반응 컴포넌트 (521ae1b, e19be0d, f11f188)
- 사용 로그 트래킹 및 대시보드 피드백 통계 (f11f188)
- Agent Canvas v7 통합 및 Alembic 체인 머지 (7942e1b)
- staging 서버(10.10.10.21) 인프라 제거 (2b3d7b9)

### 테스트
- E2E 테스트 표준화 및 리네임 (53be685, 4d57ef3)
- 교육/케이스/포트폴리오/프로필/알림 E2E 추가 (313d2bc, 790c181)
- E2E 테스트 ID 매핑 가이드 문서 (aded113)

### 인프라
- LXD git 점검 + dev DB 동기화 자동화 (f9b6e82)

---

## v1.0 (2026-02-13~18)

### 기능 추가
- LangGraph 기반 튜터 에이전트 구현 (v1.0 태그)
- 챗봇 서비스 복원: 세션 API, 프롬프트, glossary 비동기 (e28f33e)
- 슬래시 명령어 시스템 + `/buy` `/sell` `/history` (269738e, 00ffa4e)
- 복습 카드 시스템 (aa7c37d)
- 가드레일 CoT 고도화 (2ecc819)
- 질문 의도 분류 + DB 쿼리 사전 세팅 (e7bb87a)
- 호가창 시뮬레이션 모듈 (91bddd1)
- 지정가 확률적 체결 + 24시간 만료 (cb3c29c)
- Redis 키 네임스페이스 통일 + 슬라이딩 윈도우 레이트리밋 (0fcb554)

### 버그 수정
- JWT 설정 통일, 커넥션 풀 최적화 (6d13858)
- JWT_SECRET startup 검증 및 토큰 로그 보안 패치 (711db04)
- authFetch 10초 타임아웃 + AbortError (317179e)
- 멀티턴 중복 응답 방지 (57d8de5)

### 인프라
- `POST /api/v1/pipeline/run` 수동 트리거 + 스케줄러 개선 (f7ceb76)
- Alertmanager 통합, staging 서버 인프라 (149f942)
- bcrypt<4.0.0 핀 (5d5fda2)
- 인프라 전용 Makefile 분리 (lxd/Makefile) (1382b32)
- CI/CD 파이프라인: pre-commit + GitHub Actions (079a9b0)

### 리팩토링
- TutorContext 3개 Context 분리 + SSE startTransition 배칭 (aa28cbe)
- sys.path 해킹 → PYTHONPATH 전환 8곳 (c102aed)
- 중복 라우트 통합 + broad exception 정리 + JWT 보안 강화 (b6834d8)

### 성능
- penguin-3d 8.2MB → 330KB WebP + nginx 보안 헤더 (32e99f4)
- keywords N+1 쿼리 → 배치 조인 (4f56280)

---

## 2026-02-08 (v0.9.0)

### Git/인프라 정비
- 머지 완료된 feature 브랜치 8개 삭제 (로컬 + 리모트)
- `.github/CODEOWNERS` 경로 오류 수정 (`backend-api` → `backend_api` 등)
- Git 브랜치 전략 수립: 간소화된 Git Flow + 담당자 이니셜 네이밍
- 커밋 컨벤션 정비: `[type] 한글 설명` (brackets) 기준으로 통일
- 릴리스 프로세스 문서화
- 모노레포 구조 + 모듈별 소유권 명시

### 버그 수정
- 이중 로그인 버그 수정 (게스트 → 로그인 전환 시 상태 충돌)
- 챗봇 시각화 SSE 파싱 안정화 (`empty content` 가드, `iframe sandbox=allow-same-origin`)
- `generate_cases` 스크립트 안정화: 재시도 로직 + 에러 처리 강화

### 기능 추가
- **리더보드**: `GET /api/v1/portfolio/leaderboard/ranking` — 수익률 기반 전체 순위 + 내 순위 표시
- **데일리 스케줄러**: APScheduler 기반 자동 파이프라인 (KST 08:00, 일-목)
- **체류 보상**: 3분 이상 학습 시 5만원 보상 (`POST /{user_id}/dwell-reward`)
- **알림 시스템**: 보상/거래 알림 페이지 + 미니 차트
- **챗봇 출처 표기**: Source Citation 기능 연결
- **7단계 내러티브 캐러셀**: 시각화 모바일 최적화
- 키워드 API `stocks` 정규화: `{stock_code, stock_name, reason}[]` 형식
- 매칭 페이지 관련 기업 섹션 + 모의투자(TradeModal) 연동
- `useCountUp` 훅: requestAnimationFrame 기반 숫자 카운트업 애니메이션

### UI/UX 개선
- **온보딩 리디자인**: 흰색 배경, 회색 텍스트, 프라이머리 버튼 (그래디언트 제거)
- **스플래시 스크린**: 모션 그래픽 적용 (Framer Motion)
- **로고**: Jua/Gaegu 폰트 (한국 귀여운 둥근체), 펭귄 이모지
- 용어 하이라이트: 점선 밑줄 제거, 배경색만 사용 (`.term-highlight`)
- 키워드 타이틀: 일반 텍스트 (mark 태그 제거), `HighlightedText`는 설명에만 적용
- 게스트 로그아웃: "게스트 모드 나가기" 버튼 (Profile.jsx)
- 차트 컴포넌트: 하드코딩 색상 → CSS 변수 전환
- BottomNav 포트폴리오 뱃지 (수익률 표시)
- 알림 뱃지, 매수 버튼 스타일 개선

### 인프라
- CI/CD 실패 워크플로우 제거
- `.gitignore`에 Claude Code 관련 파일 추가
- 문서 체계 개편: 번호 순서 리네이밍 (01~06)

---

## 2026-02-07

### 기능 추가
- 투자 탭 전면 구현 + 챗봇 시각화 파이프라인 복구
- LLM 기반 `historical_cases` 데이터 자동 생성 스크립트 (`generate_cases.py`)
- 동적 용어 생성 + 챗봇 개선
- 자유매매 KIS API + 게스트 인증 유도

### 인프라
- Terraform IaC 모듈 (AWS 배포 준비)
- 테스트 인프라 + Locust 부하 테스트
- Spring Security CORS 환경변수 동적 설정

### 문서
- 팀 개발 문서 + AWS 인프라 문서 작성
- 데이터 파이프라인 및 배포 가이드

---

## 작성 규칙

```
## 버전 또는 브랜치명 (날짜)

### 기능 추가
- 설명 (커밋 해시)

### 버그 수정
- 설명 (커밋 해시)

### UI/UX
- 설명

### 인프라
- 설명

### 리팩토링 / 성능 / 테스트 / 문서
- 설명
```
