from __future__ import annotations

import json
import re
import subprocess
from html import unescape
from urllib.parse import parse_qs, urlparse

import requests
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi

from app.core.config import settings
from app.services.article_service import ArticleData, ArticleExtractionError, evaluate_content_quality

_YT_HOSTNAMES = {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}
_OEMBED_URL = "https://www.youtube.com/oembed"


def is_youtube_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return (parsed.hostname or "") in _YT_HOSTNAMES
    except Exception:
        return False


def _is_valid_video_id(video_id: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{10,15}", video_id or ""))


def extract_video_id(url: str) -> str | None:
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        path = parsed.path.strip("/")

        if hostname == "youtu.be":
            candidate = path.split("/")[0]
            return candidate if _is_valid_video_id(candidate) else None

        if hostname in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
            qs = parse_qs(parsed.query)
            candidate = (qs.get("v") or [""])[0]
            if _is_valid_video_id(candidate):
                return candidate

            segments = [segment for segment in path.split("/") if segment]
            if len(segments) >= 2 and segments[0] in {"shorts", "embed", "live", "v"}:
                candidate = segments[1]
                return candidate if _is_valid_video_id(candidate) else None

        return None
    except Exception:
        return None


def _normalize_transcript_text(text: str) -> str:
    value = unescape(str(text or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _ensure_length(text: str, max_chars: int) -> str:
    normalized = _normalize_transcript_text(text)
    if len(normalized) < 200:
        raise ArticleExtractionError(
            "자막이 너무 짧아 분석할 수 없습니다 (200자 미만).",
            code="YOUTUBE_TRANSCRIPT_TOO_SHORT",
        )
    return normalized[:max_chars]


def _extract_entries_text(entries: list) -> str:
    chunks: list[str] = []
    for entry in entries:
        if isinstance(entry, dict):
            text = entry.get("text", "")
        else:
            text = getattr(entry, "text", "")
        text = str(text).strip()
        if text:
            chunks.append(text)
    return " ".join(chunks)


def _iter_transcripts(transcript_list: object) -> list:
    try:
        return list(transcript_list)  # type: ignore[arg-type]
    except Exception:
        pass

    bucket: list = []
    for attr in ("manually_created_transcripts", "generated_transcripts"):
        value = getattr(transcript_list, attr, None)
        if isinstance(value, dict):
            bucket.extend(value.values())
        elif isinstance(value, list):
            bucket.extend(value)
    return bucket


def _fetch_transcript_primary(video_id: str, max_chars: int = 12000) -> tuple[str, str]:
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    except TranscriptsDisabled as exc:
        raise ArticleExtractionError(
            "이 영상은 자막이 비활성화되어 있습니다.",
            code="YOUTUBE_NO_TRANSCRIPT",
        ) from exc
    except Exception as exc:
        raise ArticleExtractionError(
            f"1차 자막 조회 실패: {exc}",
            code="YOUTUBE_TRANSCRIPT_FAILED",
        ) from exc

    transcript = None
    detected_lang = "unknown"

    for langs in (["ko", "ko-KR", "ko-US"], ["en", "en-US", "en-GB"]):
        try:
            transcript = transcript_list.find_transcript(langs)
            detected_lang = langs[0]
            break
        except Exception:
            continue

    if transcript is None:
        for langs in (["ko", "ko-KR", "ko-US"], ["en", "en-US", "en-GB"]):
            try:
                transcript = transcript_list.find_generated_transcript(langs)
                detected_lang = f"auto:{langs[0]}"
                break
            except Exception:
                continue

    if transcript is None:
        candidates = _iter_transcripts(transcript_list)
        if candidates:
            transcript = candidates[0]
            detected_lang = str(getattr(transcript, "language_code", "unknown"))

    if transcript is None:
        raise ArticleExtractionError(
            "사용 가능한 자막이 없습니다.",
            code="YOUTUBE_NO_TRANSCRIPT",
        )

    try:
        entries = transcript.fetch()
    except Exception as exc:
        raise ArticleExtractionError(
            f"1차 자막 fetch 실패: {exc}",
            code="YOUTUBE_TRANSCRIPT_FAILED",
        ) from exc

    if not entries:
        raise ArticleExtractionError(
            "사용 가능한 자막이 없습니다.",
            code="YOUTUBE_NO_TRANSCRIPT",
        )

    return _ensure_length(_extract_entries_text(entries), max_chars), detected_lang


def _run_ytdlp_dump(url: str) -> dict:
    command = [
        settings.ytdlp_binary,
        "--dump-single-json",
        "--skip-download",
        "--no-playlist",
        "--no-warnings",
        "--no-call-home",
    ]
    if settings.youtube_cookies_file:
        command.extend(["--cookies", settings.youtube_cookies_file])
    command.extend(["--", url])

    try:
        proc = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=settings.ytdlp_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise ArticleExtractionError(
            "yt-dlp 자막 조회 시간이 초과되었습니다.",
            code="YOUTUBE_TRANSCRIPT_FAILED",
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        if "Private video" in stderr or "Sign in" in stderr:
            raise ArticleExtractionError(
                "접근 권한 문제로 자막을 가져오지 못했습니다.",
                code="YOUTUBE_TRANSCRIPT_FAILED",
            ) from exc
        raise ArticleExtractionError(
            f"yt-dlp 실행 실패: {stderr or 'unknown error'}",
            code="YOUTUBE_TRANSCRIPT_FAILED",
        ) from exc

    payload = (proc.stdout or "").strip()
    if not payload:
        raise ArticleExtractionError(
            "yt-dlp 결과가 비어 있습니다.",
            code="YOUTUBE_TRANSCRIPT_FAILED",
        )

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ArticleExtractionError(
            f"yt-dlp JSON 파싱 실패: {exc}",
            code="YOUTUBE_TRANSCRIPT_FAILED",
        ) from exc


def _track_priority(lang: str, ext: str) -> tuple[int, int]:
    lang_l = lang.lower()
    if lang_l == "ko":
        lang_rank = 0
    elif lang_l.startswith("ko-"):
        lang_rank = 1
    elif lang_l == "en":
        lang_rank = 2
    elif lang_l.startswith("en-"):
        lang_rank = 3
    else:
        lang_rank = 9

    ext_l = ext.lower()
    if ext_l == "json3":
        ext_rank = 0
    elif ext_l == "vtt":
        ext_rank = 1
    else:
        ext_rank = 2

    return (lang_rank, ext_rank)


def _extract_tracks(info: dict) -> list[dict]:
    tracks: list[dict] = []

    for source_name in ("subtitles", "automatic_captions"):
        source = info.get(source_name) or {}
        if not isinstance(source, dict):
            continue
        for lang, items in source.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                url = str(item.get("url") or "").strip()
                if not url:
                    continue
                ext = str(item.get("ext") or "").strip().lower() or "unknown"
                tracks.append(
                    {
                        "lang": str(lang),
                        "url": url,
                        "ext": ext,
                        "source": source_name,
                    }
                )

    tracks.sort(key=lambda x: _track_priority(x["lang"], x["ext"]))
    return tracks


def _parse_json3(text: str) -> str:
    data = json.loads(text)
    chunks: list[str] = []
    for event in data.get("events", []) or []:
        if not isinstance(event, dict):
            continue
        segs = event.get("segs") or []
        if not isinstance(segs, list):
            continue
        line = "".join(str(seg.get("utf8") or "") for seg in segs if isinstance(seg, dict))
        line = line.strip()
        if line:
            chunks.append(line)
    return " ".join(chunks)


def _parse_text_subtitle(text: str) -> str:
    lines = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.upper().startswith("WEBVTT"):
            continue
        if re.match(r"^\d+$", line):
            continue
        if "-->" in line:
            continue
        line = re.sub(r"<[^>]+>", " ", line)
        line = unescape(line).strip()
        if line:
            lines.append(line)
    return " ".join(lines)


def _fetch_track_text(track: dict) -> str:
    try:
        response = requests.get(track["url"], timeout=settings.request_timeout_seconds)
        response.raise_for_status()
        raw = response.text
    except Exception as exc:
        raise ArticleExtractionError(
            f"자막 트랙 다운로드 실패 ({track.get('lang')}/{track.get('ext')}): {exc}",
            code="YOUTUBE_TRANSCRIPT_FAILED",
        ) from exc

    ext = str(track.get("ext") or "").lower()
    if ext == "json3":
        try:
            return _parse_json3(raw)
        except Exception:
            return _parse_text_subtitle(raw)
    return _parse_text_subtitle(raw)


def _fetch_transcript_via_ytdlp(url: str, max_chars: int = 12000) -> tuple[str, str]:
    info = _run_ytdlp_dump(url)
    tracks = _extract_tracks(info)
    if not tracks:
        raise ArticleExtractionError(
            "yt-dlp에서 사용 가능한 자막 트랙을 찾지 못했습니다.",
            code="YOUTUBE_NO_TRANSCRIPT",
        )

    errors: list[str] = []
    for track in tracks:
        try:
            text = _fetch_track_text(track)
            cleaned = _ensure_length(text, max_chars)
            return cleaned, f"{track['source']}:{track['lang']}:{track['ext']}"
        except ArticleExtractionError as exc:
            errors.append(str(exc))
            continue

    raise ArticleExtractionError(
        f"yt-dlp 자막 트랙 파싱 실패: {' | '.join(errors[:3])}",
        code="YOUTUBE_TRANSCRIPT_FAILED",
    )


def _fetch_transcript_text(video_id: str, url: str, max_chars: int = 12000) -> tuple[str, str]:
    if not _is_valid_video_id(video_id):
        raise ArticleExtractionError(
            "유효하지 않은 YouTube 영상 ID입니다.",
            code="YOUTUBE_INVALID_URL",
        )

    primary_error: ArticleExtractionError | None = None
    try:
        return _fetch_transcript_primary(video_id, max_chars)
    except ArticleExtractionError as exc:
        primary_error = exc

    fallback_error: ArticleExtractionError | None = None
    try:
        return _fetch_transcript_via_ytdlp(url, max_chars)
    except ArticleExtractionError as exc:
        fallback_error = exc

    code = "YOUTUBE_TRANSCRIPT_FAILED"
    if primary_error and fallback_error:
        primary_code = primary_error.code
        fallback_code = fallback_error.code
        if "YOUTUBE_INVALID_URL" in {primary_code, fallback_code}:
            code = "YOUTUBE_INVALID_URL"
        elif primary_code == "YOUTUBE_NO_TRANSCRIPT" and fallback_code == "YOUTUBE_NO_TRANSCRIPT":
            code = "YOUTUBE_NO_TRANSCRIPT"

    raise ArticleExtractionError(
        (
            "자막 데이터를 가져오지 못했습니다: "
            f"primary={primary_error}; fallback={fallback_error}"
        ),
        code=code,
    )


def _fetch_youtube_metadata(video_id: str, timeout: int = 10) -> dict:
    try:
        resp = requests.get(
            _OEMBED_URL,
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def fetch_youtube(url: str, max_chars: int = 12000) -> ArticleData:
    video_id = extract_video_id(url)
    if not video_id:
        raise ArticleExtractionError(
            "유효한 YouTube 영상 URL이 아닙니다.",
            code="YOUTUBE_INVALID_URL",
        )

    transcript_text, _ = _fetch_transcript_text(video_id, url, max_chars)

    meta = _fetch_youtube_metadata(video_id)
    title = meta.get("title") or f"YouTube 영상 ({video_id})"
    channel = meta.get("author_name") or "YouTube"
    thumbnail = meta.get("thumbnail_url") or f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

    quality_score, quality_flags = evaluate_content_quality(transcript_text)

    return ArticleData(
        title=title,
        url=url,
        source=channel,
        published_at=None,
        content=transcript_text,
        image_url=thumbnail,
        article_domain="youtube.com",
        content_quality_score=quality_score,
        quality_flags=quality_flags,
    )
