---
name: buy_stock
description: 종목 매수 주문
slash_command: /buy
requires_confirmation: true
risk: high
params:
  - name: stock_code
    type: string
    required: true
    description: 종목 코드 (6자리)
  - name: quantity
    type: number
    required: false
    default: 1
    description: 매수 수량
---

## 실행 조건
- stock_code가 유효한 6자리 종목 코드여야 함
- 사용자 잔고가 충분해야 함 (현재가 × 수량)
- 장 운영 시간 여부는 시스템에서 자동 체크

## 실행 흐름
1. 종목 코드 유효성 검증
2. 현재 시세 조회
3. 잔고 확인
4. **확인 질문 표시** (high risk 액션)
5. 사용자 확인 시 주문 실행
6. 결과 응답 + 포트폴리오 업데이트

## 응답 템플릿
### 성공
{stock_name} {quantity}주를 {price}원에 매수했어요! 💰

현재 보유: {total_quantity}주 (평균 단가: {avg_price}원)
남은 현금: {remaining_cash}원

### 실패
매수에 실패했어요. 😢
- 원인: {error_reason}
- 현재 잔고: {current_cash}원

## 관련 액션
- `check_stock_price`: 매수 전 시세 확인
- `check_portfolio`: 보유 현황 확인
