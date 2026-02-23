---
name: get_briefing
description: 오늘의 브리핑 보기
slash_command: /briefing
requires_confirmation: false
risk: low
params:
  - name: date
    type: string
    required: false
    description: 특정 날짜 (YYYYMMDD 형식, 기본값 오늘)
---

## 실행 조건
- 해당 날짜의 브리핑 데이터가 존재해야 함

## 실행 흐름
1. 브리핑 데이터 조회 (DB)
2. 키워드별 요약 정리
3. 마크다운 포맷팅

## 응답 템플릿
### 📰 {date} 시장 브리핑

**시장 요약**
{market_summary}

**오늘의 키워드**
{keywords_list}

각 키워드를 클릭하면 상세 분석을 볼 수 있어요!

### 데이터 없음
{date}의 브리핑 데이터가 아직 없어요. 😢

최신 브리핑은 매일 오전에 업데이트됩니다.

## 관련 액션
- 키워드 클릭 → 상세 분석 페이지
- `/quiz` → 브리핑 내용 복습 퀴즈
