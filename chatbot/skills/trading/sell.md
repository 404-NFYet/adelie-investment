---
name: sell_stock
description: 종목 매도 주문
slash_command: /sell
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
    description: 매도 수량
---

## 실행 조건
- stock_code가 유효한 6자리 종목 코드여야 함
- 해당 종목을 보유하고 있어야 함
- 매도 수량이 보유 수량 이하여야 함

## 실행 흐름
1. 종목 코드 유효성 검증
2. 보유 현황 확인
3. 현재 시세 조회
4. **확인 질문 표시** (high risk 액션)
5. 사용자 확인 시 주문 실행
6. 결과 응답 + 손익 계산

## 응답 템플릿
### 성공
{stock_name} {quantity}주를 {price}원에 매도했어요! 📈

실현 손익: {realized_pnl}원 ({pnl_percent}%)
남은 보유: {remaining_quantity}주
현금 잔고: {new_cash}원

### 실패
매도에 실패했어요. 😢
- 원인: {error_reason}
- 현재 보유: {current_holding}주

## 관련 액션
- `check_portfolio`: 보유 현황 확인
- `check_stock_price`: 현재 시세 확인
