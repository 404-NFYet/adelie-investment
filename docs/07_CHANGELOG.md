# 변경 이력 (Changelog)

> 대상 독자: 전체 팀원
> 날짜별 변경 사항을 카테고리별로 정리합니다.

---

## 2026-02-08

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

## 향후 업데이트 시 작성 규칙

```
## YYYY-MM-DD

### 버그 수정
- [간단한 설명] (관련 파일 또는 이슈)

### 기능 추가
- **기능명**: 설명

### UI/UX 개선
- 설명

### 인프라
- 설명
```
