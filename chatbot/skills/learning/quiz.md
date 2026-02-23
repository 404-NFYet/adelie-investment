---
name: start_quiz
description: 퀴즈 시작
slash_command: /quiz
requires_confirmation: false
risk: low
params:
  - name: topic
    type: string
    required: false
    description: 퀴즈 주제 (기본값: 최근 대화 내용)
  - name: count
    type: number
    required: false
    default: 3
    description: 문제 수
---

## 실행 조건
- 퀴즈 주제 또는 이전 대화 컨텍스트가 있어야 함

## 실행 흐름
1. 주제 결정 (파라미터 또는 최근 대화)
2. LLM으로 퀴즈 생성
3. 문제별 순차 출력
4. 사용자 답변 수집
5. 정답 확인 및 해설

## 응답 템플릿
### 퀴즈 시작! 🎯

**주제**: {topic}

---

**Q1.** {question_1}

1. {option_a}
2. {option_b}
3. {option_c}
4. {option_d}

답변 번호를 입력하세요!

### 정답 확인
{user_answer === correct ? "정답이에요! 🎉" : "아쉽네요 😢"}

**해설**: {explanation}

---

{has_more ? "다음 문제로 넘어갈까요?" : "퀴즈 종료! {score}/{total} 맞췄어요!"}

## 관련 액션
- `/review` → 복습 카드로 저장
