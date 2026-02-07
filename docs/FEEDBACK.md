# 피드백 시스템 가이드

## 수집 채널

1. **인앱 피드백 위젯** - 별점 + 카테고리 + 텍스트 (POST /api/v1/feedback)
2. **브리핑 완독 설문** - 평가 + 흥미 섹션 (POST /api/v1/feedback/briefing)
3. **사용 행동 추적** - 자동 이벤트 수집 (POST /api/v1/analytics/events)
4. **Google Form** - 데모 종료 시 종합 설문 (NPS 포함)

## 관리자 API

- GET /api/v1/feedback/stats - 통계 (별점 평균, 카테고리 분포)

## Google Form 설문 구조

1. 기본 정보 (투자 경험, 기기)
2. 전반적 만족도 (1-5 리커트)
3. 기능별 평가 (브리핑, 튜터, 모의투자 등)
4. 유용한 기능 (복수 선택)
5. 아쉬운 점 (서술)
6. NPS 0-10
7. 자유 의견
