# Phase 5: Skills 기반 기능 관리

## 문제

에이전트 기능들이 코드에 하드코딩되어 있어 운영자가 쉽게 수정할 수 없었습니다.

## 해결

### 1. 마크다운 기반 스킬 정의
각 스킬을 YAML frontmatter가 포함된 마크다운 파일로 정의:

```markdown
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
  - name: quantity
    type: integer
    required: true
---

# 매수 주문

## 실행 조건
- 시장 개장 시간 내
- 충분한 잔고
...
```

### 2. 스킬 로더 (`_loader.py`)
```python
def load_all_skills() -> list[dict]:
    """모든 스킬을 로드하고 캐시"""

def build_action_catalog_from_skills() -> list[dict]:
    """스킬에서 액션 카탈로그 자동 생성"""
```

### 3. 카테고리 구조
```
chatbot/skills/
├── trading/       # 매수, 매도, 예약주문
├── analysis/      # 포트폴리오, 브리핑
├── navigation/    # 화면 이동
├── learning/      # 퀴즈, 복습카드
└── data/          # DART API
```

### 4. 운영자 편의성
- 마크다운 편집기로 스킬 수정 가능
- 즉시 반영 (캐시 무효화)
- 문서화와 코드가 일체화

## 변경 파일

- `chatbot/skills/_loader.py` (신규)
- `chatbot/skills/trading/buy.md` (신규)
- `chatbot/skills/trading/sell.md` (신규)
- `chatbot/skills/analysis/portfolio.md` (신규)
- `chatbot/skills/analysis/briefing.md` (신규)
- `chatbot/skills/learning/quiz.md` (신규)
- `chatbot/skills/learning/review_card.md` (신규)
- `chatbot/skills/data/dart_api.md` (신규)
