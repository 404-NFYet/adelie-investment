# 리더보드 기능

> 대상 독자: 프론트엔드/백엔드 개발자
> 포트폴리오 수익률 기반 전체 사용자 랭킹 시스템입니다.

---

## API 스펙

### `GET /api/v1/portfolio/leaderboard/ranking`

수익률 기반 리더보드 조회.

**Query Parameters**

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `user_id` | int | 0 | 현재 사용자 ID (내 순위 표시용) |
| `limit` | int | 20 | 조회할 상위 사용자 수 (1~100) |

**응답 예시**

```json
{
  "my_rank": 3,
  "my_entry": {
    "rank": 3,
    "user_id": 42,
    "username": "홍길동",
    "total_value": 10850000,
    "profit_loss": 850000,
    "profit_loss_pct": 8.5,
    "is_me": true
  },
  "rankings": [
    {
      "rank": 1,
      "user_id": 7,
      "username": "투자왕",
      "total_value": 12300000,
      "profit_loss": 2300000,
      "profit_loss_pct": 23.0,
      "is_me": false
    }
  ],
  "total_users": 15
}
```

## 응답 스키마

### `LeaderboardResponse`

| 필드 | 타입 | 설명 |
|------|------|------|
| `my_rank` | int \| null | 현재 사용자의 순위 (미참여 시 null) |
| `my_entry` | LeaderboardEntry \| null | 현재 사용자의 상세 정보 |
| `rankings` | LeaderboardEntry[] | 상위 N명 랭킹 리스트 |
| `total_users` | int | 전체 참여 사용자 수 |

### `LeaderboardEntry`

| 필드 | 타입 | 설명 |
|------|------|------|
| `rank` | int | 순위 |
| `user_id` | int | 사용자 ID |
| `username` | str | 사용자명 |
| `total_value` | float | 총 평가금액 (현금 + 보유 종목) |
| `profit_loss` | float | 총 손익 금액 |
| `profit_loss_pct` | float | 수익률 (%, 소수점 2자리) |
| `is_me` | bool | 현재 사용자 여부 |

## 수익률 계산 로직

```
총 평가금액 = 보유 현금 + Σ(종목별 현재가 × 보유 수량)
총 손익     = 총 평가금액 - 초기 자본금
수익률(%)   = (총 손익 / 초기 자본금) × 100
```

- 초기 자본금: 포트폴리오 생성 시 지급된 금액 (`initial_cash`)
- 현재가 조회 실패 시: 매입 단가(`avg_buy_price`)로 폴백
- 정렬: 수익률 내림차순

## 프론트엔드 구조

### 컴포넌트

```
frontend/src/components/trading/Leaderboard.jsx
```

| Props | 타입 | 설명 |
|-------|------|------|
| `userId` | number | 현재 사용자 ID |

### API 호출

```js
// frontend/src/api/portfolio.js
portfolioApi.getLeaderboard(userId, limit)
// → GET /api/v1/portfolio/leaderboard/ranking?user_id={userId}&limit={limit}
```

### UI 구성

1. **내 순위 카드** — 프라이머리 보더, 현재 순위 + 수익률 표시
2. **전체 순위 리스트** — 상위 N명, 1~3위 메달 이모지 표시
3. **수익률 색상** — 양수: 빨간색(+), 음수: 파란색(-), 0: 회색
4. **애니메이션** — Framer Motion 진입 애니메이션 (fade + slide)

### 금액 포맷

```js
// 한국 원화 포맷: "1,234,567원"
new Intl.NumberFormat('ko-KR').format(Math.round(value)) + '원';
```
