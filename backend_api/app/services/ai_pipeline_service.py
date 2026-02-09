"""AI Pipeline Service - OpenAI/Perplexity/Claude."""
import os
import json
from typing import Dict, List
from dataclasses import dataclass
import httpx
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

@dataclass
class PipelineConfig:
    target_scenario_count: int = 5
    keyword_model: str = "gpt-4o-mini"
    research_model: str = "sonar"
    story_model: str = "claude-sonnet-4-5-20250514"

def get_pipeline_config():
    return PipelineConfig(
        target_scenario_count=int(os.getenv("TARGET_SCENARIO_COUNT", "5")),
    )

class AIPipelineService:
    def __init__(self):
        self.config = get_pipeline_config()
        self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.claude = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.pplx_key = os.getenv("PERPLEXITY_API_KEY")

    async def call_openai(self, messages, model=None, temp=0.7, max_t=4096):
        model = model or self.config.keyword_model
        r = await self.openai.chat.completions.create(
            model=model, messages=messages, temperature=temp, max_tokens=max_t)
        return r.choices[0].message.content

    async def call_claude(self, messages, system=None, model=None, temp=0.7):
        model = model or self.config.story_model
        msgs = [m for m in messages if m["role"] != "system"]
        r = await self.claude.messages.create(
            model=model, messages=msgs, system=system or "", temperature=temp, max_tokens=4096)
        return r.content[0].text

_instance = None
def get_ai_pipeline_service():
    global _instance
    if not _instance:
        _instance = AIPipelineService()
    return _instance

