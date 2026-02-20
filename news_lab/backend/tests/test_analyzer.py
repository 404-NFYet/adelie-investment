from app.services.analyzer import _build_marked_text, _normalize_glossary


def test_normalize_glossary_limits_and_filters():
    payload = {
        "glossary": {
            "words": [
                {"term": "금리", "definition": "기준금리", "importance": 5},
                {"term": "시장", "definition": "일반 단어", "importance": 5},
                {"term": "Inflation", "definition": "물가", "importance": 4},
                {"term": "GDP", "definition": "국내총생산", "importance": 4},
                {"term": "CPI", "definition": "소비자물가", "importance": 4},
                {"term": "PER", "definition": "주가수익비율", "importance": 4},
                {"term": "EPS", "definition": "주당순이익", "importance": 4},
                {"term": "ROE", "definition": "자기자본이익률", "importance": 4},
            ],
            "phrases": [
                {"term": "신용카드 결제 비중", "definition": "결제 변화", "importance": 5},
                {"term": "현금 사용 비중 감소", "definition": "소비 행태 변화", "importance": 4},
                {"term": "포인트 적립 혜택", "definition": "소비자 동기", "importance": 4},
                {"term": "", "definition": "bad", "importance": 4},
                {"term": "12345", "definition": "bad", "importance": 4},
                {"term": "물가 상승 압박", "definition": "거시 여건", "importance": 4},
                {"term": "인터넷 쇼핑 확산", "definition": "채널 전환", "importance": 3},
                {"term": "지불 수단 변화", "definition": "핵심 맥락", "importance": 5},
            ],
        }
    }

    glossary = _normalize_glossary(payload, "fallback text")
    words = [g for g in glossary if g["kind"] == "word"]
    phrases = [g for g in glossary if g["kind"] == "phrase"]

    assert len(words) <= 6
    assert len(phrases) <= 6
    assert all(item["term"] != "시장" for item in words)


def test_build_marked_text_phrase_priority_single_occurrence():
    text = "신용카드 결제 비중이 올랐고 신용카드 결제 비중이 다시 언급됐다. 금리는 하락했다."
    glossary = [
        {"term": "신용카드 결제 비중", "definition": "", "kind": "phrase", "importance": 5},
        {"term": "금리", "definition": "", "kind": "word", "importance": 4},
    ]

    marked = _build_marked_text(text, glossary)

    assert marked.count("data-term='신용카드 결제 비중'") == 1
    assert marked.count("data-term='금리'") == 1
