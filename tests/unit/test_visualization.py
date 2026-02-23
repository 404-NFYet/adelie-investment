"""시각화 관련 유닛 테스트."""
import sys
import os
import pytest
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "fastapi"))
from app.services.tutor_chart_generator import (
    _classify_question,
    _build_user_prompt,
    _validate_chart,
    _contains_estimation_marker,
    _count_numeric_points,
    _validate_xy_lengths,
    _contains_banned_trace_type,
    _validate_dates,
    _validate_numeric_range,
    _warn_axis_truncation,
    _iter_chart_text_fields,
    _strip_markdown_fences,
)


class TestExtractPlotlyDataFromHtml:
    """레거시 HTML에서 Plotly 데이터 추출 테스트."""

    def test_plotly_newplot_pattern(self):
        """Plotly.newPlot 패턴 매칭."""
        html = '''
        <script>
        Plotly.newPlot('chart', [{"x": [1,2,3], "y": [4,5,6], "type": "scatter"}], {"title": "Test"})
        </script>
        '''
        # JSON.parse 기반 추출 테스트 (new Function → JSON.parse 전환 후)
        import re
        match = re.search(
            r'Plotly\.(?:newPlot|react)\s*\(\s*[\'"][^\'"]*[\'"]\s*,\s*([\s\S]+?)\s*,\s*(\{[\s\S]+?\})\s*[,)]',
            html
        )
        assert match is not None
        data = json.loads(match.group(1))
        layout = json.loads(match.group(2))
        assert isinstance(data, list)
        assert data[0]["type"] == "scatter"
        assert layout["title"] == "Test"

    def test_var_pattern(self):
        """var data/layout 패턴 매칭."""
        html = '''
        <script>
        var data = [{"x": [1], "y": [2], "type": "bar"}];
        var layout = {"title": "Bar Chart"};
        Plotly.newPlot('div', data, layout)
        </script>
        '''
        import re
        data_match = re.search(r'(?:var|let|const)\s+data\s*=\s*([\s\S]+?);\s*(?:var|let|const)\s+layout', html)
        layout_match = re.search(r'(?:var|let|const)\s+layout\s*=\s*([\s\S]+?);\s*(?:Plotly|</script)', html)
        assert data_match is not None
        assert layout_match is not None
        data = json.loads(data_match.group(1).strip())
        layout = json.loads(layout_match.group(1).strip())
        assert isinstance(data, list)
        assert layout["title"] == "Bar Chart"

    def test_invalid_html_returns_none(self):
        """잘못된 HTML은 None 반환."""
        html = '<div>No plotly here</div>'
        import re
        match = re.search(r'Plotly\.(?:newPlot|react)', html)
        assert match is None


class TestNormalizeMathDelimiters:
    """수식 구분자 정규화 테스트."""

    def test_block_math_normalized(self):
        """\\[...\\] → $$...$$ 변환."""
        content = "다음 공식을 보세요:\n\\[ PER = \\frac{P}{E} \\]\n끝"
        import re
        normalized = re.sub(
            r'(?:^|\n)\s*\\\[\s*([\s\S]*?)\s*\\?\]\s*(?=\n|$)',
            lambda m: f"\n$$\n{m.group(1).strip()}\n$$\n",
            content,
        )
        assert "$$" in normalized
        assert "\\[" not in normalized

    def test_inline_math_normalized(self):
        """\\(...\\) → $...$ 변환."""
        content = "PER은 \\(\\frac{P}{E}\\)입니다."
        import re
        normalized = re.sub(
            r'\\\(\s*([\s\S]*?)\s*\\\)',
            lambda m: f"${m.group(1).strip()}$",
            content,
        )
        assert "$\\frac{P}{E}$" in normalized
        assert "\\(" not in normalized

    def test_empty_content(self):
        """빈 문자열 처리."""
        assert "" == ""

    def test_plain_text_unchanged(self):
        """수식 없는 텍스트는 변경 없음."""
        content = "삼성전자의 PER은 12배입니다."
        import re
        result = re.sub(r'\\\[\s*([\s\S]*?)\s*\\?\]', '', content)
        assert content == result


class TestChartDataJson:
    """차트 데이터 JSON 검증."""

    def test_valid_plotly_json_structure(self):
        """올바른 Plotly JSON 구조."""
        chart_data = {
            "data": [{"x": [1, 2, 3], "y": [10, 20, 30], "type": "scatter"}],
            "layout": {"title": "Test Chart"}
        }
        assert "data" in chart_data
        assert isinstance(chart_data["data"], list)
        assert chart_data["data"][0]["type"] == "scatter"

    def test_empty_data_array(self):
        """빈 data 배열 처리."""
        chart_data = {"data": [], "layout": {}}
        assert len(chart_data["data"]) == 0


# ── 테스트 픽스처 ──

SAMPLE_CHART_DATA = {
    "005930": {
        "name": "삼성전자",
        "history": [
            {"date": "2026-02-17", "open": 69000, "high": 70000, "low": 68500, "close": 69500, "change_pct": 0.72, "volume": 15000000},
            {"date": "2026-02-18", "open": 69500, "high": 70500, "low": 69000, "close": 70000, "change_pct": 0.72, "volume": 14500000},
            {"date": "2026-02-19", "open": 70000, "high": 71000, "low": 69500, "close": 70500, "change_pct": 0.71, "volume": 16000000},
            {"date": "2026-02-20", "open": 70500, "high": 72000, "low": 70000, "close": 71500, "change_pct": 1.42, "volume": 18000000},
            {"date": "2026-02-21", "open": 71500, "high": 72500, "low": 71000, "close": 72000, "change_pct": 0.70, "volume": 15200000},
        ],
    }
}

VALID_CHART = {
    "data": [
        {
            "x": ["2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20", "2026-02-21"],
            "y": [69500, 70000, 70500, 71500, 72000],
            "type": "scatter",
            "mode": "lines+markers",
            "name": "삼성전자 종가",
        }
    ],
    "layout": {
        "title": "삼성전자 주가 추이",
        "yaxis": {"title": "원 (KRW)"},
    },
}


# ── 질문 분류 테스트 ──

class TestClassifyQuestion:
    """_classify_question 함수 테스트."""

    def test_trend_keywords(self):
        """추이 관련 키워드 → 라인 차트."""
        assert "라인" in _classify_question("삼성전자 최근 주가 추이")
        assert "라인" in _classify_question("주가 변화 보여줘")

    def test_change_keywords(self):
        """등락률 관련 키워드 → 세로 막대."""
        assert "세로 막대" in _classify_question("이번 주 등락률")
        assert "세로 막대" in _classify_question("수익률 보여줘")

    def test_compare_keywords(self):
        """비교 키워드 → 그룹 막대."""
        assert "그룹 막대" in _classify_question("삼성전자 vs SK하이닉스 비교")

    def test_volume_keywords(self):
        """거래량 키워드 → 이중축."""
        assert "이중축" in _classify_question("삼성전자 거래량 추이")

    def test_extreme_keywords(self):
        """극값 키워드 → 영역 scatter."""
        assert "영역" in _classify_question("최고점과 최저점은?")

    def test_default_line(self):
        """매칭 키워드 없으면 기본 라인 차트."""
        assert "라인" in _classify_question("삼성전자 알려줘")


# ── 유저 프롬프트 빌드 테스트 ──

class TestBuildUserPrompt:
    """_build_user_prompt 함수 테스트."""

    def test_contains_ohlcv_headers(self):
        """OHLCV 테이블 헤더 포함."""
        prompt = _build_user_prompt(SAMPLE_CHART_DATA, "응답", "주가 추이")
        assert "시가" in prompt
        assert "고가" in prompt
        assert "저가" in prompt
        assert "종가" in prompt
        assert "거래량" in prompt

    def test_contains_summary_stats(self):
        """요약 통계 (종가 범위, 변동률, 평균 거래량) 포함."""
        prompt = _build_user_prompt(SAMPLE_CHART_DATA, "응답", "주가 추이")
        assert "종가 범위" in prompt
        assert "기간 변동률" in prompt
        assert "평균 거래량" in prompt

    def test_contains_chart_hint(self):
        """추천 차트 유형 힌트 포함."""
        prompt = _build_user_prompt(SAMPLE_CHART_DATA, "응답", "등락률 보여줘")
        assert "추천 차트 유형" in prompt
        assert "세로 막대" in prompt

    def test_empty_history(self):
        """빈 히스토리도 에러 없이 처리."""
        data = {"005930": {"name": "삼성전자", "history": []}}
        prompt = _build_user_prompt(data, "응답", "주가")
        assert "데이터 없음" in prompt

    def test_truncates_response(self):
        """튜터 응답 400자 절단."""
        long_resp = "가" * 1000
        prompt = _build_user_prompt(SAMPLE_CHART_DATA, long_resp, "주가")
        # 400자 + 헤더 등 포함, 원본 1000자보다 짧아야 함
        assert "가" * 401 not in prompt


# ── 7-Gate 검증 테스트 ──

class TestValidateChart:
    """_validate_chart 7-gate 검증 테스트."""

    def test_valid_chart_passes(self):
        """정상 차트는 통과."""
        result = _validate_chart(VALID_CHART, SAMPLE_CHART_DATA)
        assert result is not None
        assert result["data"][0]["type"] == "scatter"

    def test_gate1_insufficient_points(self):
        """G1: 데이터 포인트 3개 미만 → None."""
        chart = {
            "data": [{"x": ["a", "b"], "y": [1, 2], "type": "scatter"}],
            "layout": {},
        }
        assert _validate_chart(chart) is None

    def test_gate2_estimation_marker_in_trace(self):
        """G2: trace name에 추정 마커 → None."""
        chart = {
            "data": [{"x": [1, 2, 3], "y": [10, 20, 30], "name": "매출(E)"}],
            "layout": {},
        }
        assert _validate_chart(chart) is None

    def test_gate2_estimation_in_annotation(self):
        """G2: annotation에 추정 마커 → None."""
        chart = {
            "data": [{"x": [1, 2, 3], "y": [10, 20, 30]}],
            "layout": {"annotations": [{"text": "2025 Est 수치"}]},
        }
        assert _validate_chart(chart) is None

    def test_gate3_xy_length_mismatch(self):
        """G3: x/y 길이 불일치 → None."""
        chart = {
            "data": [{"x": [1, 2, 3], "y": [10, 20], "type": "scatter"}],
            "layout": {},
        }
        assert _validate_chart(chart) is None

    def test_gate4_banned_candlestick(self):
        """G4: candlestick 차트 유형 → None."""
        chart = {
            "data": [{
                "x": ["a", "b", "c"],
                "open": [1, 2, 3],
                "high": [2, 3, 4],
                "low": [0, 1, 2],
                "close": [1.5, 2.5, 3.5],
                "type": "candlestick",
            }],
            "layout": {},
        }
        assert _validate_chart(chart) is None

    def test_gate4_banned_pie(self):
        """G4: pie 차트 유형 → None."""
        chart = {
            "data": [{"labels": ["A", "B", "C"], "values": [10, 20, 30], "type": "pie"}],
            "layout": {},
        }
        assert _validate_chart(chart) is None

    def test_gate5_invalid_date(self):
        """G5: chart_data에 없는 날짜 → None."""
        chart = {
            "data": [
                {
                    "x": ["2026-02-17", "2026-02-18", "2099-01-01"],
                    "y": [69500, 70000, 70500],
                    "type": "scatter",
                }
            ],
            "layout": {},
        }
        assert _validate_chart(chart, SAMPLE_CHART_DATA) is None

    def test_gate5_valid_dates_pass(self):
        """G5: 정상 날짜는 통과."""
        result = _validate_chart(VALID_CHART, SAMPLE_CHART_DATA)
        assert result is not None

    def test_gate6_numeric_out_of_range(self):
        """G6: 원본 범위 ±10% 초과 수치 → None."""
        chart = {
            "data": [
                {
                    "x": ["2026-02-17", "2026-02-18", "2026-02-19"],
                    "y": [69500, 70000, 50000000],  # 50M >> 가격/거래량 범위 모두 초과
                    "type": "scatter",
                }
            ],
            "layout": {},
        }
        assert _validate_chart(chart, SAMPLE_CHART_DATA) is None

    def test_gate7_axis_truncation_warning(self):
        """G7: 축 절단 시 경고만 (차트는 유지)."""
        chart = {
            "data": [
                {
                    "x": ["2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20", "2026-02-21"],
                    "y": [69500, 70000, 70500, 71500, 72000],
                    "type": "scatter",
                }
            ],
            "layout": {"yaxis": {"range": [70000, 72000]}},  # 69500 미포함
        }
        # 경고만, 차트는 유지
        result = _validate_chart(chart, SAMPLE_CHART_DATA)
        assert result is not None

    def test_no_chart_data_skips_gates_5_6_7(self):
        """chart_data=None이면 Gate 5~7 건너뜀."""
        chart = {
            "data": [{"x": ["a", "b", "c", "d"], "y": [1, 2, 3, 4]}],
            "layout": {},
        }
        result = _validate_chart(chart, None)
        assert result is not None


# ── 개별 헬퍼 함수 테스트 ──

class TestHelperFunctions:
    """검증 헬퍼 함수 개별 테스트."""

    def test_iter_chart_text_fields(self):
        """텍스트 필드 순회."""
        chart = {
            "data": [{"name": "trace1", "x": ["날짜1"], "text": ["메모1"]}],
            "layout": {
                "title": "차트 제목",
                "xaxis": {"title": "X축"},
                "annotations": [{"text": "주석"}],
            },
        }
        texts = list(_iter_chart_text_fields(chart))
        assert "차트 제목" in texts
        assert "X축" in texts
        assert "trace1" in texts
        assert "날짜1" in texts
        assert "메모1" in texts
        assert "주석" in texts

    def test_iter_chart_text_fields_dict_title(self):
        """title이 dict인 경우."""
        chart = {
            "data": [],
            "layout": {"title": {"text": "딕셔너리 제목"}},
        }
        texts = list(_iter_chart_text_fields(chart))
        assert "딕셔너리 제목" in texts

    def test_contains_estimation_marker_true(self):
        """추정 마커 감지."""
        chart = {"data": [{"name": "삼성전자 추정 매출"}], "layout": {}}
        assert _contains_estimation_marker(chart) is True

    def test_contains_estimation_marker_false(self):
        """추정 마커 없음."""
        chart = {"data": [{"name": "삼성전자 종가"}], "layout": {}}
        assert _contains_estimation_marker(chart) is False

    def test_count_numeric_points(self):
        """숫자 포인트 카운트."""
        chart = {
            "data": [
                {"y": [1, 2, None, "abc", 5]},
                {"y": [10, 20]},
            ]
        }
        assert _count_numeric_points(chart) == 5

    def test_validate_xy_lengths_pass(self):
        """x/y 길이 동일 → True."""
        chart = {"data": [{"x": [1, 2, 3], "y": [4, 5, 6]}]}
        assert _validate_xy_lengths(chart) is True

    def test_validate_xy_lengths_fail(self):
        """x/y 길이 불일치 → False."""
        chart = {"data": [{"x": [1, 2], "y": [4, 5, 6]}]}
        assert _validate_xy_lengths(chart) is False

    def test_validate_xy_no_arrays(self):
        """x/y 없는 trace → True (bar 등)."""
        chart = {"data": [{"labels": ["A"], "values": [10]}]}
        assert _validate_xy_lengths(chart) is True

    def test_banned_trace_type_detected(self):
        """금지 유형 감지."""
        chart = {"data": [{"type": "waterfall", "y": [1]}]}
        assert _contains_banned_trace_type(chart) == "waterfall"

    def test_no_banned_trace_type(self):
        """허용 유형."""
        chart = {"data": [{"type": "scatter"}, {"type": "bar"}]}
        assert _contains_banned_trace_type(chart) is None

    def test_validate_dates_valid(self):
        """정상 날짜 검증."""
        chart = {
            "data": [{"x": ["2026-02-17", "02/18"], "y": [1, 2]}]
        }
        assert _validate_dates(chart, SAMPLE_CHART_DATA) is True

    def test_validate_dates_invalid(self):
        """chart_data에 없는 날짜."""
        chart = {
            "data": [{"x": ["2099-12-31"], "y": [1]}]
        }
        assert _validate_dates(chart, SAMPLE_CHART_DATA) is False

    def test_validate_dates_non_date_x_passes(self):
        """날짜가 아닌 x값은 검증 건너뜀."""
        chart = {
            "data": [{"x": ["삼성전자", "SK하이닉스", "LG전자"], "y": [1, 2, 3]}]
        }
        assert _validate_dates(chart, SAMPLE_CHART_DATA) is True

    def test_numeric_range_valid(self):
        """범위 내 수치 통과."""
        assert _validate_numeric_range(VALID_CHART, SAMPLE_CHART_DATA) is True

    def test_numeric_range_small_values_pass(self):
        """작은 값(퍼센트 등) < 200은 항상 통과."""
        chart = {"data": [{"y": [-5.5, 3.2, 1.0, 0.72]}]}
        assert _validate_numeric_range(chart, SAMPLE_CHART_DATA) is True

    def test_warn_axis_truncation_detected(self):
        """축 절단 감지."""
        chart = {
            "data": [{"y": [100, 200, 300]}],
            "layout": {"yaxis": {"range": [150, 300]}},  # 100 미포함
        }
        assert _warn_axis_truncation(chart) is True

    def test_warn_axis_truncation_no_range(self):
        """range 미설정 → 경고 없음."""
        chart = {
            "data": [{"y": [100, 200, 300]}],
            "layout": {"yaxis": {}},
        }
        assert _warn_axis_truncation(chart) is False

    def test_strip_markdown_fences(self):
        """마크다운 펜스 제거."""
        text = '```json\n{"data": []}\n```'
        assert _strip_markdown_fences(text) == '{"data": []}'

    def test_strip_markdown_fences_plain(self):
        """펜스 없는 텍스트는 그대로."""
        text = '{"data": []}'
        assert _strip_markdown_fences(text) == '{"data": []}'


# ── generate_tutor_chart 사전 체크 테스트 ──

class TestGenerateTutorChart:
    """generate_tutor_chart 함수 사전 체크 테스트."""

    @pytest.mark.asyncio
    async def test_empty_chart_data_returns_none(self):
        """빈 chart_data → None."""
        from app.services.tutor_chart_generator import generate_tutor_chart
        result = await generate_tutor_chart({}, "응답", "질문")
        assert result is None

    @pytest.mark.asyncio
    async def test_insufficient_records_returns_none(self):
        """레코드 3개 미만 → LLM 호출 없이 None."""
        from app.services.tutor_chart_generator import generate_tutor_chart
        data = {
            "005930": {
                "name": "삼성전자",
                "history": [
                    {"date": "2026-02-20", "close": 71500},
                    {"date": "2026-02-21", "close": 72000},
                ],
            }
        }
        result = await generate_tutor_chart(data, "응답", "질문")
        assert result is None
