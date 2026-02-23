---
name: check_portfolio
description: 내 포트폴리오 확인
slash_command: /portfolio
requires_confirmation: false
risk: low
params: []
---

## 실행 조건
- 로그인된 사용자여야 함

## 실행 흐름
1. 사용자 포트폴리오 조회
2. 보유 종목별 현재가 조회
3. 손익 계산
4. 결과 마크다운으로 포맷팅

## 응답 템플릿
### 포트폴리오 요약 📊

**총 자산**: {total_asset}원
**수익률**: {total_return}% ({pnl_amount}원)

| 종목 | 보유 | 평단가 | 현재가 | 손익률 |
|------|------|--------|--------|--------|
{holdings_table}

**현금**: {cash}원

### 빈 포트폴리오
아직 보유 종목이 없어요! 🐧

시작하려면:
- "삼성전자 분석해줘" 라고 물어보세요
- `/buy 005930 1` 로 매수해보세요

## 시각화
- 자동으로 파이 차트 생성 (보유 비중)
- 총 자산 추이 라인 차트 (선택적)
