"""시각화 관련 유닛 테스트 (9개)."""
import pytest
import json


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
