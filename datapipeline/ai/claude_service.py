"""Claude API 서비스"""
import os, logging
from typing import Optional

logger = logging.getLogger(__name__)

class ClaudeService:
    def __init__(self):
        self.api_key = os.getenv("CLAUDE_API_KEY", "")
    
    async def generate_code(self, system: str, prompt: str, model: str = "claude-3-5-haiku-20241022") -> Optional[str]:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            response = await client.messages.create(
                model=model, max_tokens=2000,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return response.content[0].text
        except Exception as e:
            logger.error("Claude API 실패: %s", e)
            return None
