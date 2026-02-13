"""프롬프트 로더 유닛 테스트."""

import pytest
from pathlib import Path

# 프로젝트 루트 설정
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestChatbotPromptLoader:
    """chatbot 프롬프트 로더 테스트."""

    def test_load_existing_prompt(self):
        """존재하는 프롬프트 로드 성공."""
        from chatbot.prompts import load_prompt
        spec = load_prompt("tutor_system", difficulty="beginner")
        assert spec.body
        assert spec.provider == "openai"
        assert spec.model == "gpt-4o-mini"

    def test_load_nonexistent_prompt_raises(self):
        """존재하지 않는 프롬프트 로드 시 FileNotFoundError."""
        from chatbot.prompts import load_prompt
        with pytest.raises(FileNotFoundError):
            load_prompt("nonexistent_prompt")

    def test_variable_substitution(self):
        """변수 치환이 정상 작동."""
        from chatbot.prompts import load_prompt
        spec = load_prompt("term_explanation", term="PER", difficulty="beginner")
        assert "PER" in spec.body
        assert "beginner" in spec.body

    def test_include_directive(self):
        """{{include:_tone_guide}} 지시자가 정상 해결."""
        from chatbot.prompts import load_prompt
        spec = load_prompt("tutor_system", difficulty="beginner")
        assert "아델리에 톤" in spec.body

    def test_all_chatbot_templates_loadable(self):
        """모든 chatbot 템플릿 파일이 로드 가능한지 확인."""
        from chatbot.prompts.prompt_loader import _DEFAULT_DIR
        for md_file in _DEFAULT_DIR.glob("*.md"):
            if md_file.name.startswith("_"):
                continue  # include 전용 파일 건너뜀
            from chatbot.prompts import load_prompt
            spec = load_prompt(md_file.stem, **{
                "difficulty": "beginner", "count": "8", "rss_text": "test",
                "keyword": "test", "mirroring_hint": "test", "theme": "test",
                "plan": "{}", "context_research": "test", "simulation_research": "test",
                "draft": "{}", "sections_text": "test", "terms": "test",
                "query": "test", "term": "test", "avoid_section": "",
            })
            assert spec.body, f"{md_file.name} body가 비어있음"


class TestDatapipelinePromptLoader:
    """datapipeline 프롬프트 로더 테스트."""

    def test_frontmatter_parsing(self):
        """frontmatter에서 provider, model, temperature 등 파싱."""
        from datapipeline.prompts import load_prompt
        spec = load_prompt("page_purpose", curated_context="{}")
        assert spec.provider == "anthropic"
        assert "claude" in spec.model
        assert spec.response_format == "json_object"

    def test_narrative_body_uses_anthropic(self):
        """narrative_body 프롬프트가 anthropic 프로바이더를 사용."""
        from datapipeline.prompts import load_prompt
        spec = load_prompt("narrative_body",
                          curated_context="{}", page_purpose="{}", historical_case="{}")
        assert spec.provider == "anthropic"

    def test_all_datapipeline_templates_loadable(self):
        """모든 datapipeline 템플릿 파일이 로드 가능한지 확인."""
        from datapipeline.prompts.prompt_loader import _DEFAULT_DIR
        for md_file in _DEFAULT_DIR.glob("*.md"):
            if md_file.name.startswith("_"):
                continue
            from datapipeline.prompts import load_prompt
            spec = load_prompt(md_file.stem, **{
                "curated_context": "{}",
                "page_purpose": "{}",
                "historical_case": "{}",
                "narrative_json": "{}",
                "raw_narrative": "{}",
                "charts": "[]",
                "glossaries": "[]",
                "final_briefing": "{}",
            })
            assert spec.body, f"{md_file.name} body가 비어있음"
