"""내러티브 섹션 빌더 서비스 (6페이지 골든케이스).

6개 페이지(background, concept_explain, history, application, caution, summary)의
콘텐츠를 구성하는 빌더 함수를 제공한다.

LLM이 생성한 narrative 데이터가 있으면 그대로 사용하고,
없으면 기존 빌더 로직으로 fallback한다.
"""

import re
from typing import Optional

from app.models.historical_case import CaseStockRelation
from app.models.briefing import DailyBriefing, BriefingStock
from app.schemas.narrative import ChartData, ChartDataPoint, NarrativeSection

# --- 유틸 ---

_TERM_PATTERN = re.compile(r"\[\[(.+?)\]\]")

PAGE_KEYS = ["background", "concept_explain", "history", "application", "caution", "summary"]
STEP_TITLES = {
    "background": "왜 지금 중요할까",
    "concept_explain": "핵심 개념 한눈에",
    "history": "과거 패턴 되짚기",
    "application": "지금 시장에 대입",
    "caution": "놓치면 위험한 점",
    "summary": "투자 전 체크포인트",
}

_JARGON_EXPLAINERS: dict[str, str] = {
    "리레이팅": "리레이팅은 같은 실적이어도 시장이 더 높은 가격을 붙여주는 흐름이에요.",
    "밸류에이션": "밸류에이션은 회사 가치를 주가로 얼마나 높게 보는지에 대한 평가예요.",
    "멀티플": "멀티플은 이익이나 매출 대비 주가가 몇 배인지 보여주는 숫자예요.",
    "컨센서스": "컨센서스는 여러 증권사가 모아 본 평균 예상치예요.",
    "펀더멘털": "펀더멘털은 회사가 실제로 돈을 버는 기초 체력을 뜻해요.",
    "CAPEX": "CAPEX는 공장이나 장비에 쓰는 큰 설비투자 비용이에요.",
}

_KOR_SENTENCE_ENDINGS = (
    "요.",
    "다.",
    "니다.",
    "어요.",
    "아요.",
    "예요.",
    "이에요.",
    "였어요.",
    "이었어요.",
    "했습니다.",
    "했다.",
    "됩니다.",
)


def _has_batchim(char: str) -> bool:
    if not char:
        return False
    code = ord(char)
    if 0xAC00 <= code <= 0xD7A3:
        return ((code - 0xAC00) % 28) != 0
    return False


def highlight_terms(content: str) -> str:
    """[[term]] 패턴을 <mark>term</mark> 으로 치환."""
    if not content:
        return content
    return _TERM_PATTERN.sub(r"<mark>\1</mark>", content)


def split_paragraphs(content: str) -> list[str]:
    """본문을 문단(빈 줄 기준)으로 분리."""
    if not content:
        return []
    return [p.strip() for p in content.split("\n\n") if p.strip()]


# --- 6페이지 통합 빌더 ---


def build_all_steps(
    narrative_data: Optional[dict],
    comparison: dict,
    paragraphs: list[str],
    briefing: Optional[DailyBriefing],
    briefing_stocks: list[BriefingStock],
    case_stocks: list[CaseStockRelation],
) -> dict:
    """6페이지 steps를 빌드. LLM narrative가 있으면 우선 사용, 없으면 fallback."""
    if narrative_data and _is_valid_narrative(narrative_data):
        return _build_from_llm(narrative_data)

    # fallback: 기본 빌더 로직
    return _build_fallback(comparison, paragraphs, briefing, briefing_stocks, case_stocks)


def _is_valid_narrative(narrative_data: dict) -> bool:
    """LLM narrative 데이터가 6페이지 구조인지 확인."""
    if not all(key in narrative_data for key in PAGE_KEYS):
        return False

    for key in PAGE_KEYS:
        section = narrative_data.get(key, {})
        if not isinstance(section, dict):
            return False
        content = str(section.get("content", ""))
        if len(content.strip()) < 10:
            return False

    return True


def _inject_glossary_marks(content: str, glossary: list[dict]) -> str:
    """content 내 glossary 용어를 <mark> 태그로 감싸기 (각 용어 첫 등장 1회만)."""
    if not content or not glossary:
        return content
    for item in glossary:
        term = item.get("term", "")
        if not term or len(term) < 2:
            continue
        # 이미 <mark> 안에 있는 것은 건너뛰기
        pattern = re.compile(
            rf'(?<!<mark>)(?<!<mark class="term-highlight">)({re.escape(term)})(?!</mark>)',
            re.IGNORECASE,
        )
        content = pattern.sub(r'<mark class="term-highlight">\1</mark>', content, count=1)
    return content


def _sanitize_chart(chart_raw) -> dict | None:
    """chart 데이터가 Plotly 렌더링 가능한 구조인지 최소 검증."""
    if not chart_raw or not isinstance(chart_raw, dict):
        return None
    if "data" in chart_raw and not isinstance(chart_raw["data"], list):
        return None
    # layout.title이 객체({font, text})면 문자열로 정규화 (React Error #31 방지)
    layout = chart_raw.get("layout")
    if isinstance(layout, dict):
        title = layout.get("title")
        if isinstance(title, dict):
            layout["title"] = title.get("text", "")
    return chart_raw


def _build_from_llm(narrative_data: dict) -> dict:
    """LLM이 생성한 6페이지 narrative 데이터를 반환 (glossary 하이라이팅 포함)."""
    steps = {}
    for key in PAGE_KEYS:
        section = narrative_data.get(key, {})
        if isinstance(section, str):
            section = {"content": section, "bullets": []}

        content = section.get("content", "")
        glossary = section.get("glossary", [])
        title = str(section.get("title", "") or "").strip() or STEP_TITLES.get(key, "")
        bullets = section.get("bullets", [])

        # glossary 용어를 content에 하이라이팅
        content = _inject_glossary_marks(content, glossary)
        # 기존 [[term]] 패턴도 변환
        content = highlight_terms(content)
        content = _postprocess_content(key, content, bullets)

        step_data = {
            "title": title,
            "bullets": bullets,
            "content": content,
            "chart": None if key == "summary" else _sanitize_chart(section.get("chart")),
            "glossary": glossary,
        }
        # sources/citations 전달 (Perplexity 출처)
        if section.get("sources"):
            step_data["sources"] = section["sources"]
        steps[key] = step_data
    return steps


def _postprocess_content(step_key: str, content: str, bullets: list[str] | None = None) -> str:
    text = str(content or "")
    if not text:
        return text

    # 라벨 잔여물 제거
    text = text.replace("### 다른 점\n닮은 점 ", "### 다른 점\n")
    text = re.sub(r"\n?\s*과거\s*사이클\s*흐름\s*$", "", text)
    text = re.sub(r"\b(?:Trigger|Process|Outcome|Variables)\s*:\s*", "", text)
    text = re.sub(r"\[(닮은 점|다른 점|과거 사이클 흐름)\]", r"\1", text)

    def _split_sentences_keep_flow(s: str) -> list[str]:
        return [p.strip() for p in re.split(r"(?<=[.!?。！？])\s+", s) if p.strip()]

    def _smart_linebreak(s: str) -> str:
        """문장마다가 아니라 의미 덩어리(2~3문장) 기준으로 줄바꿈."""
        sentences = _split_sentences_keep_flow(s)
        if len(sentences) <= 2:
            return " ".join(sentences) if sentences else s.strip()

        chunks: list[str] = []
        buf: list[str] = []
        buf_len = 0
        for sent in sentences:
            sent_len = len(sent)
            buf.append(sent)
            buf_len += sent_len + (1 if buf_len else 0)

            # 2문장 이상 쌓였고 길이가 충분하면 한 덩어리로 끊는다.
            if len(buf) >= 2 and (buf_len >= 115 or len(buf) >= 3):
                chunks.append(" ".join(buf).strip())
                buf = []
                buf_len = 0

        if buf:
            chunks.append(" ".join(buf).strip())
        return "\n".join(chunks)

    # 본문은 흐름 덩어리 기준으로만 줄바꿈
    lines = text.splitlines()
    rendered: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            rendered.append("")
            continue
        if s.startswith("### ") or s.startswith("- ") or re.match(r"^\d+[.)]\s+", s):
            rendered.append(s)
            continue
        rendered.append(_smart_linebreak(s))
    text = "\n".join(rendered).strip()

    # history(과거 패턴) 섹션은 미완성 종결을 최소화한다.
    if step_key == "history":
        fixed_lines: list[str] = []
        in_case_block = False
        for line in text.splitlines():
            s = line.strip()
            if not s:
                fixed_lines.append(line)
                continue
            if s.startswith("### "):
                in_case_block = "참고할 과거 사례" in s
                fixed_lines.append(line)
                continue
            if not re.search(r"[.!?。！？]$", s):
                s = f"{s}."
            # '랠리.', '사이클.'처럼 명사형 단문이 남으면 완결 문장으로 보정
            if in_case_block and s.endswith(".") and not s.endswith(_KOR_SENTENCE_ENDINGS):
                core = s[:-1].strip()
                if core:
                    last = core[-1]
                    copula = "이라는" if _has_batchim(last) else "라는"
                    s = f"{core}{copula} 흐름이었어요."
            fixed_lines.append(s)
        text = "\n".join(fixed_lines).strip()

    # caution(놓치면 위험한 점) 섹션의 "대응 포인트"는 "라벨: 설명" 단위로 줄바꿈한다.
    if step_key == "caution":
        lines = text.splitlines()
        in_action_points = False
        action_buf: list[str] = []
        rebuilt: list[str] = []

        def _flush_action() -> None:
            nonlocal action_buf
            if not action_buf:
                return
            merged = " ".join(part.strip() for part in action_buf if part.strip())
            # "문장 끝 + 다음 라벨: 설명" 패턴에서만 줄바꿈
            merged = re.sub(
                r"([.!?。！？])\s+([가-힣A-Za-z0-9·()/\-\s]{2,30}:\s)",
                r"\1\n\2",
                merged,
            )
            rebuilt.extend([ln.strip() for ln in merged.splitlines() if ln.strip()])
            action_buf = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("### "):
                _flush_action()
                rebuilt.append(stripped)
                in_action_points = "대응 포인트" in stripped
                continue
            if in_action_points:
                if not stripped:
                    _flush_action()
                    rebuilt.append("")
                    in_action_points = False
                else:
                    action_buf.append(stripped)
            else:
                rebuilt.append(line)

        _flush_action()
        text = "\n".join(rebuilt).strip()

    # 분량이 너무 짧으면 기존 bullets를 보조 설명으로 붙여 핵심 손실을 줄임
    sentence_count = len([p for p in re.split(r"(?<=[.!?。！？])\s+", text) if p.strip() and not p.strip().startswith("###")])
    if sentence_count < 4 and bullets and step_key != "caution":
        extras: list[str] = []
        for b in bullets:
            btxt = str(b or "").strip().lstrip("- ").strip()
            if not btxt:
                continue
            if not re.search(r"[.!?。！？]$", btxt):
                btxt += "."
            if btxt not in text:
                extras.append(btxt)
            if sentence_count + len(extras) >= 4:
                break
        if extras:
            text = f"{text}\n" + "\n".join(extras)

    # 어려운 용어 문장은 삭제하지 않고 쉬운 설명 문장을 덧붙임
    explain_lines: list[str] = []
    plain_text = re.sub(r"<[^>]+>", "", text)
    for term, explanation in _JARGON_EXPLAINERS.items():
        if term in plain_text and explanation not in plain_text:
            explain_lines.append(explanation)
        if len(explain_lines) >= 2:
            break
    if explain_lines and step_key in {"concept_explain", "history", "application"}:
        text = f"{text}\n" + "\n".join(explain_lines)

    return text.strip()


def _build_fallback(
    comparison: dict,
    paragraphs: list[str],
    briefing: Optional[DailyBriefing],
    briefing_stocks: list[BriefingStock],
    case_stocks: list[CaseStockRelation],
) -> dict:
    """6페이지 fallback 빌더."""
    steps = {
        "background": _build_background(briefing, briefing_stocks),
        "concept_explain": _build_concept_explain(comparison),
        "history": _build_history(comparison, paragraphs),
        "application": _build_application(comparison, paragraphs),
        "caution": _build_caution(comparison, paragraphs),
        "summary": _build_summary(comparison, case_stocks),
    }
    for key in PAGE_KEYS:
        section = steps.get(key, {})
        if isinstance(section, dict):
            section.setdefault("title", STEP_TITLES.get(key, "핵심 포인트"))
            if key == "summary":
                section["chart"] = None
    return steps


# --- 개별 섹션 빌더 (fallback용) ---

def _build_background(briefing: Optional[DailyBriefing], briefing_stocks: list[BriefingStock]) -> dict:
    """background 섹션: 오늘의 시장 브리핑 요약."""
    bullets = []
    if briefing and briefing.top_keywords:
        for kw in briefing.top_keywords.get("keywords", [])[:3]:
            bullets.append(kw.get("title", "") if isinstance(kw, dict) else kw)

    content = highlight_terms(briefing.market_summary or "시장 요약이 없습니다.") if briefing else ""

    gainers = [s for s in briefing_stocks if s.selection_reason == "top_gainer"]
    chart_points = [
        ChartDataPoint(label=s.stock_name, value=float(s.change_rate) if s.change_rate else 0.0, color="#22c55e")
        for s in gainers[:5]
    ]
    chart = ChartData(chart_type="single_bar", title="오늘의 상승 TOP", unit="%", data_points=chart_points) if chart_points else None

    return NarrativeSection(bullets=bullets, content=content, chart=chart).model_dump()


def _build_concept_explain(comparison: dict) -> dict:
    """concept_explain 섹션: 금융 개념 설명 (fallback)."""
    title = comparison.get("title", "이 테마")
    return NarrativeSection(
        bullets=[
            f"{title}의 핵심 금융 개념을 설명해요.",
            "초보 투자자도 이해할 수 있도록 쉽게 풀어볼게요.",
        ],
        content=f"{title} 관련 금융 개념의 상세 설명을 준비 중이에요.",
    ).model_dump()


def _build_history(comparison: dict, paragraphs: list[str]) -> dict:
    """history 섹션: 과거 비슷한 사례."""
    past_metric = comparison.get("past_metric", {})
    present_metric = comparison.get("present_metric", {})

    bullets = []
    if comparison.get("title"):
        bullets.append(comparison["title"])
    if comparison.get("subtitle"):
        bullets.append(comparison["subtitle"])
    if past_metric:
        bullets.append(
            f"{past_metric.get('company', '')} ({past_metric.get('year', '')}) "
            f"{past_metric.get('name', '')}: {past_metric.get('value', '')}"
        )

    content = highlight_terms(paragraphs[0]) if paragraphs else ""

    chart_points = []
    if past_metric.get("value") is not None:
        chart_points.append(ChartDataPoint(
            label=f"{past_metric.get('company', '')} ({past_metric.get('year', '')})",
            value=float(past_metric.get("value", 0)), color="#ef4444",
        ))
    if present_metric.get("value") is not None:
        chart_points.append(ChartDataPoint(
            label=f"{present_metric.get('company', '')} ({present_metric.get('year', '')})",
            value=float(present_metric.get("value", 0)), color="#3b82f6",
        ))

    chart = ChartData(
        chart_type="comparison_bar",
        title=f"{past_metric.get('name', '')} 비교",
        unit=past_metric.get("name", ""),
        data_points=chart_points,
    ) if chart_points else None

    return NarrativeSection(bullets=bullets, content=content, chart=chart).model_dump()


def _build_application(comparison: dict, paragraphs: list[str]) -> dict:
    """application 섹션: 현재 상황에 적용."""
    analysis = comparison.get("analysis", [])
    bullets = analysis[:3] if analysis else ["과거 사례를 현재에 적용해 볼게요."]
    content = highlight_terms(paragraphs[1]) if len(paragraphs) > 1 else ""
    # fallback 모드에서는 근거 수치가 명확할 때만 차트를 노출한다.
    return NarrativeSection(bullets=bullets, content=content, chart=None).model_dump()


def _build_caution(comparison: dict, paragraphs: list[str]) -> dict:
    """caution 섹션: 주의해야 할 점."""
    title = comparison.get("title", "이 테마")
    bullets = [
        f"{title}의 예상과 다른 전개가 나올 수 있어요.",
        f"외부 변수(금리, 환율, 규제)가 {title} 흐름을 바꿀 수 있어요.",
        f"단기 모멘텀에 과도하게 베팅하면 손실 위험이 있어요.",
    ]
    content = highlight_terms(paragraphs[2]) if len(paragraphs) > 2 else f"{title} 관련 주의사항을 꼭 체크해야 해요."
    return NarrativeSection(bullets=bullets, content=content, chart=None).model_dump()


def _build_summary(comparison: dict, case_stocks: list[CaseStockRelation]) -> dict:
    """summary 섹션: 최종 정리."""
    bullets = [
        "핵심 지표가 같은 방향으로 움직이는지 확인해요.",
        "실적 가이던스가 실제 수치로 이어지는지 체크해요.",
        "규제·일정 변화 뉴스를 짧게라도 매일 확인해요.",
    ]
    if case_stocks:
        stock_names = [r.stock_name for r in case_stocks[:3]]
        bullets[2] = f"관련 종목({', '.join(stock_names)}) 뉴스 변화를 매일 확인해요."

    return NarrativeSection(
        title=STEP_TITLES["summary"],
        bullets=bullets,
        content=(
            "### 투자 전에 꼭 확인할 포인트\n"
            f"- {bullets[0]}\n"
            f"- {bullets[1]}\n"
            f"- {bullets[2]}"
        ),
        chart=None,
    ).model_dump()
