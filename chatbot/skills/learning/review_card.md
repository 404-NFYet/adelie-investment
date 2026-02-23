---
name: create_review_card
description: 복습 카드 생성
slash_command: /review
requires_confirmation: false
risk: low
params:
  - name: session_id
    type: string
    required: false
    description: 대화 세션 ID (기본값: 현재 세션)
---

## 실행 조건
- 저장할 대화 내용이 있어야 함

## 실행 흐름
1. 대화 내용 수집
2. LLM으로 핵심 내용 추출
3. 복습 카드 HTML 생성
4. DB 저장 + 학습 진도 업데이트

## 응답 템플릿
### 복습 카드 저장 완료! 📚

**제목**: {card_title}

**핵심 개념**
{key_concepts}

**당시 상황**
{context_summary}

복습 카드로 저장했어요! 
홈 화면이나 교육 탭에서 다시 볼 수 있어요.

### 저장 실패
복습 카드 저장에 실패했어요. 😢
다시 시도해주세요.

## 복습 카드 구조
```html
<div class="review-card">
  <header>
    <h2>{title}</h2>
    <span class="date">{date}</span>
  </header>
  <section class="key-concepts">
    <h3>📌 핵심 개념</h3>
    <ul>{concepts}</ul>
  </section>
  <section class="context">
    <h3>📊 당시 상황</h3>
    <p>{context}</p>
  </section>
  <footer>
    <button class="continue-chat">이어서 대화하기</button>
  </footer>
</div>
```
