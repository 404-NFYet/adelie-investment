"""AI tools unit tests - isolated."""
import pytest
import sys

sys.path.insert(0, "/home/hj/2026/project/narrative-investment/ai-module")


class TestAgentPrompts:
    def test_difficulty_prompts_exist(self):
        """Test that all difficulty prompts exist."""
        from agent.prompts import DIFFICULTY_PROMPTS
        
        assert "beginner" in DIFFICULTY_PROMPTS
        assert "elementary" in DIFFICULTY_PROMPTS
        assert "intermediate" in DIFFICULTY_PROMPTS
    
    def test_get_system_prompt(self):
        """Test system prompt generation."""
        from agent.prompts import get_system_prompt
        
        prompt = get_system_prompt("beginner")
        assert isinstance(prompt, str)
        assert len(prompt) > 0
    
    def test_beginner_prompt_content(self):
        """Test beginner prompt has appropriate content."""
        from agent.prompts import DIFFICULTY_PROMPTS
        
        beginner = DIFFICULTY_PROMPTS["beginner"]
        # Should contain keywords related to simple explanation
        assert "쉽" in beginner or "초보" in beginner or "간단" in beginner
    
    def test_intermediate_prompt_content(self):
        """Test intermediate prompt has appropriate content."""
        from agent.prompts import DIFFICULTY_PROMPTS
        
        intermediate = DIFFICULTY_PROMPTS["intermediate"]
        # Should allow more technical terms
        assert len(intermediate) > 0


class TestToolDefinitions:
    def test_glossary_tool_exists(self):
        """Test glossary tool is defined."""
        from tools.glossary_tool import get_glossary, lookup_term
        
        # Check tools are callable
        assert callable(get_glossary.invoke)
        assert callable(lookup_term.invoke)
    
    def test_search_tool_exists(self):
        """Test search tool is defined."""
        from tools.search_tool import search_historical_cases
        
        assert callable(search_historical_cases.invoke)
    
    def test_comparison_tool_exists(self):
        """Test comparison tool is defined."""
        from tools.comparison_tool import compare_past_present
        
        assert callable(compare_past_present.invoke)
    
    def test_company_tool_exists(self):
        """Test company tools are defined."""
        from tools.company_tool import get_related_companies, get_supply_chain
        
        assert callable(get_related_companies.invoke)
        assert callable(get_supply_chain.invoke)
    
    def test_briefing_tool_exists(self):
        """Test briefing tool is defined."""
        from tools.briefing_tool import get_today_briefing
        
        assert callable(get_today_briefing.invoke)


class TestAgentStructure:
    def test_tutor_agent_class_exists(self):
        """Test TutorAgent class is defined."""
        from agent.tutor_agent import TutorAgent
        
        assert TutorAgent is not None
    
    def test_create_tutor_agent_function(self):
        """Test create_tutor_agent function exists."""
        from agent.tutor_agent import create_tutor_agent
        
        assert callable(create_tutor_agent)
