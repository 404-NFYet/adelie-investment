"""
Skills Loader - 마크다운 기반 스킬 정의 파일 로더

chatbot/skills/ 디렉토리의 .md 파일들을 파싱하여 액션 카탈로그를 자동 생성합니다.
운영자가 마크다운 파일만 수정하면 에이전트 기능을 관리할 수 있습니다.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Any, Optional
from functools import lru_cache

SKILLS_DIR = Path(__file__).parent


def parse_skill_frontmatter(content: str) -> tuple[dict, str]:
    """YAML frontmatter와 본문을 분리합니다."""
    if not content.startswith("---"):
        return {}, content
    
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    
    try:
        frontmatter = yaml.safe_load(parts[1])
        body = parts[2].strip()
        return frontmatter or {}, body
    except yaml.YAMLError:
        return {}, content


def parse_skill_file(filepath: Path) -> Optional[dict]:
    """스킬 마크다운 파일을 파싱합니다."""
    try:
        content = filepath.read_text(encoding="utf-8")
        frontmatter, body = parse_skill_frontmatter(content)
        
        if not frontmatter.get("name"):
            return None
        
        params = []
        for param in frontmatter.get("params", []):
            if isinstance(param, dict):
                params.append({
                    "name": param.get("name", ""),
                    "type": param.get("type", "string"),
                    "required": param.get("required", False),
                    "default": param.get("default"),
                    "description": param.get("description", ""),
                })
            elif isinstance(param, str):
                match = re.match(r"(\w+):\s*(\w+)(?:\s*\((\w+)\))?", param)
                if match:
                    params.append({
                        "name": match.group(1),
                        "type": match.group(2),
                        "required": match.group(3) == "required",
                    })
        
        category = filepath.parent.name
        
        return {
            "id": frontmatter["name"],
            "label": frontmatter.get("description", frontmatter["name"]),
            "description": frontmatter.get("description", ""),
            "slash_command": frontmatter.get("slash_command"),
            "requires_confirmation": frontmatter.get("requires_confirmation", False),
            "risk": frontmatter.get("risk", "low"),
            "params": params,
            "category": category,
            "body": body,
            "source_file": str(filepath.relative_to(SKILLS_DIR)),
        }
    except Exception as e:
        print(f"Warning: Failed to parse skill file {filepath}: {e}")
        return None


@lru_cache(maxsize=1)
def load_all_skills() -> list[dict]:
    """모든 스킬을 로드합니다. 결과는 캐시됩니다."""
    skills = []
    
    for category_dir in SKILLS_DIR.iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith("_"):
            continue
        
        for skill_file in category_dir.glob("*.md"):
            skill = parse_skill_file(skill_file)
            if skill:
                skills.append(skill)
    
    return skills


def get_skill_by_id(skill_id: str) -> Optional[dict]:
    """ID로 스킬을 조회합니다."""
    for skill in load_all_skills():
        if skill["id"] == skill_id:
            return skill
    return None


def get_skill_by_slash_command(command: str) -> Optional[dict]:
    """슬래시 명령어로 스킬을 조회합니다."""
    normalized = command.lower().strip()
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    
    for skill in load_all_skills():
        if skill.get("slash_command") == normalized:
            return skill
    return None


def get_skills_by_category(category: str) -> list[dict]:
    """카테고리별 스킬을 조회합니다."""
    return [s for s in load_all_skills() if s.get("category") == category]


def build_action_catalog_from_skills(
    categories: Optional[list[str]] = None,
    include_high_risk: bool = True,
) -> list[dict]:
    """스킬에서 액션 카탈로그를 생성합니다."""
    skills = load_all_skills()
    
    if categories:
        skills = [s for s in skills if s.get("category") in categories]
    
    if not include_high_risk:
        skills = [s for s in skills if s.get("risk") != "high"]
    
    return [
        {
            "id": s["id"],
            "label": s["label"],
            "description": s.get("description", ""),
            "type": "tool",
            "risk": s.get("risk", "low"),
            "requires_confirmation": s.get("requires_confirmation", False),
            "params": s.get("params", []),
        }
        for s in skills
    ]


def reload_skills():
    """스킬 캐시를 무효화하고 다시 로드합니다."""
    load_all_skills.cache_clear()
    return load_all_skills()


if __name__ == "__main__":
    skills = load_all_skills()
    print(f"Loaded {len(skills)} skills:")
    for skill in skills:
        print(f"  - {skill['id']}: {skill['label']} ({skill['category']})")
        if skill.get("slash_command"):
            print(f"    Command: {skill['slash_command']}")
