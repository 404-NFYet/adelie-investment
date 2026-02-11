#!/usr/bin/env python3
"""API 키 유효성 검증 스크립트.

각 프로바이더(OpenAI, Perplexity, Anthropic)의 API 키가
정상적으로 동작하는지 최소 비용의 호출로 검증한다.
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트의 .env 로드
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


def check_openai() -> bool:
    """OpenAI API 키 검증 (gpt-4o-mini 간단 호출)."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        print("[FAIL] OPENAI_API_KEY가 .env에 설정되지 않았습니다.")
        return False

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5,
        )
        content = response.choices[0].message.content.strip()
        print(f"[OK] OpenAI (gpt-4o-mini): 응답 = '{content}'")
        return True
    except Exception as exc:
        print(f"[FAIL] OpenAI: {exc}")
        return False


def check_perplexity() -> bool:
    """Perplexity API 키 검증 (sonar 간단 호출)."""
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not api_key:
        print("[FAIL] PERPLEXITY_API_KEY가 .env에 설정되지 않았습니다.")
        return False

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
        response = client.chat.completions.create(
            model="sonar",
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5,
        )
        content = response.choices[0].message.content.strip()[:50]
        print(f"[OK] Perplexity (sonar): 응답 = '{content}'")
        return True
    except Exception as exc:
        print(f"[FAIL] Perplexity: {exc}")
        return False


def check_anthropic() -> bool:
    """Anthropic API 키 검증 (claude-sonnet-4-5 간단 호출)."""
    api_key = os.getenv("CLAUDE_API_KEY", "")
    if not api_key:
        print("[FAIL] CLAUDE_API_KEY가 .env에 설정되지 않았습니다.")
        return False

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say OK"}],
        )
        content = response.content[0].text.strip()
        print(f"[OK] Anthropic (claude-sonnet-4-5): 응답 = '{content}'")
        return True
    except Exception as exc:
        print(f"[FAIL] Anthropic: {exc}")
        return False


def main():
    print("=" * 60)
    print("  API 키 유효성 검증")
    print("=" * 60)
    print()

    results = {
        "OpenAI": check_openai(),
        "Perplexity": check_perplexity(),
        "Anthropic": check_anthropic(),
    }

    print()
    print("-" * 40)
    all_ok = all(results.values())
    for name, ok in results.items():
        status = "OK" if ok else "FAIL"
        print(f"  {name}: {status}")

    print("-" * 40)
    if all_ok:
        print("모든 API 키가 정상입니다. 파이프라인 실행 가능.")
    else:
        failed = [name for name, ok in results.items() if not ok]
        print(f"실패한 프로바이더: {', '.join(failed)}")
        print("해당 API 키를 .env에 올바르게 설정하세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
