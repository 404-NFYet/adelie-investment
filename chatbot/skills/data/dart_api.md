---
name: fetch_dart
description: DART 공시 조회
slash_command: /dart
requires_confirmation: false
risk: low
params:
  - name: stock_code
    type: string
    required: true
    description: 종목 코드 (6자리)
  - name: report_type
    type: string
    required: false
    default: recent
    description: 리포트 유형 (recent, financial, major)
---

## 실행 조건
- 유효한 종목 코드
- DART API 키 설정되어 있어야 함

## 실행 흐름
1. 종목 코드 → 기업 고유번호 변환
2. DART API 호출
3. 공시 목록 파싱
4. 최신 공시 요약

## API 엔드포인트
- 최근 공시: `/api/list.json`
- 재무제표: `/api/fnlttSinglAcnt.json`
- 주요사항: `/api/majorInfoCplt.json`

## 응답 템플릿
### {stock_name} DART 공시 📋

**최근 공시 ({count}건)**
{disclosures_list}

**재무 하이라이트**
- 매출액: {revenue}원
- 영업이익: {operating_profit}원
- 당기순이익: {net_income}원

각 공시를 클릭하면 상세 내용을 볼 수 있어요!

### 데이터 없음
{stock_code}의 DART 공시 데이터를 찾을 수 없어요.
종목 코드를 확인해주세요.

## 시각화
- 기본적으로 재무 추이 차트 생성
- 연도별 매출/이익 비교
