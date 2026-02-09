"""파이프라인 설정 - 실험용."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class PipelineConfig:
    """파이프라인 설정."""
    # 시나리오 생성 개수 (최대 5개)
    target_scenario_count: int = int(os.getenv("TARGET_SCENARIO_COUNT", "5"))
    
    # 키워드 후보 개수
    keyword_candidate_count: int = int(os.getenv("KEYWORD_CANDIDATE_COUNT", "10"))
    
    # 모델 설정
    keyword_model: str = os.getenv("KEYWORD_MODEL", "gpt-4o-mini")
    research_model: str = os.getenv("RESEARCH_MODEL", "sonar")
    story_model: str = os.getenv("STORY_MODEL", "claude-sonnet-4-5-20250514")
    
    # API 키
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    perplexity_api_key: str = os.getenv("PERPLEXITY_API_KEY", "")
    
    # 출력 설정
    output_dir: str = os.getenv("OUTPUT_DIR", "/app/data")
    
    def validate(self) -> bool:
        """설정 유효성 검사."""
        if not self.openai_api_key:
            print("⚠️ OPENAI_API_KEY가 설정되지 않았습니다.")
            return False
        if self.target_scenario_count < 1 or self.target_scenario_count > 5:
            print("⚠️ TARGET_SCENARIO_COUNT는 1~5 사이여야 합니다.")
            return False
        return True


def get_config() -> PipelineConfig:
    """설정 인스턴스 반환."""
    return PipelineConfig()
