#!/usr/bin/env python3
"""
# [2026-02-04] OpenDART Batch API 제출 및 결과 수집
OpenAI Batch API에 JSONL 입력을 제출하고, 완료 후 결과 파일을 다운로드합니다.

Usage:
  # 1. Batch 제출 (입력 JSONL 업로드 후 배치 생성)
  OPENAI_API_KEY=... python3 run_opendart_batch_extract.py \
    --input data/opendart_batch_input.jsonl --submit

  # 2. 배치 상태 확인
  python3 run_opendart_batch_extract.py --batch-id batch_xxx --status

  # 3. 결과 다운로드
  python3 run_opendart_batch_extract.py --batch-id batch_xxx \
    --output data/opendart_batch_output.jsonl --retrieve
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def _get_client():
    try:
        from openai import OpenAI
    except ImportError:
        print("Install openai: pip install openai", file=sys.stderr)
        sys.exit(1)
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("Set OPENAI_API_KEY", file=sys.stderr)
        sys.exit(1)
    return OpenAI(api_key=key)


def submit_batch(client, input_path: str, completion_window: str = "24h") -> str:
    """Upload JSONL and create batch; return batch id."""
    with open(input_path, "rb") as f:
        batch_file = client.files.create(file=f, purpose="batch")
    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window=completion_window,
    )
    return batch.id


def get_batch_status(client, batch_id: str) -> dict:
    """Retrieve batch object (status, output_file_id when completed)."""
    batch = client.batches.retrieve(batch_id)
    counts = getattr(batch, "request_counts", None)
    return {
        "id": batch.id,
        "status": getattr(batch, "status", None),
        "output_file_id": getattr(batch, "output_file_id", None),
        "failed_count": getattr(counts, "failed", 0) if counts else 0,
        "completed_count": getattr(counts, "completed", 0) if counts else 0,
        "total": getattr(counts, "total", 0) if counts else 0,
    }


def retrieve_results(client, batch_id: str, output_path: str) -> None:
    """Download batch output file and save as JSONL."""
    batch = client.batches.retrieve(batch_id)
    out_id = getattr(batch, "output_file_id", None)
    if not out_id:
        print(f"Batch {batch_id} has no output yet (status: {getattr(batch, 'status')})", file=sys.stderr)
        sys.exit(1)
    content = client.files.content(out_id).content
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(content)
    print(f"Saved {len(content)} bytes to {output_path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenAI Batch API submit and retrieve for OpenDART extract")
    parser.add_argument("--input", help="Input JSONL path (for --submit)")
    parser.add_argument("--output", help="Output JSONL path (for --retrieve)")
    parser.add_argument("--batch-id", help="Batch ID (for --status or --retrieve)")
    parser.add_argument("--submit", action="store_true", help="Upload input and create batch")
    parser.add_argument("--status", action="store_true", help="Print batch status")
    parser.add_argument("--retrieve", action="store_true", help="Download batch results to --output")
    parser.add_argument("--completion-window", default="24h", help="Batch completion window (e.g. 24h)")
    args = parser.parse_args()

    client = _get_client()

    if args.submit:
        if not args.input or not os.path.isfile(args.input):
            print("--submit requires --input with existing JSONL file", file=sys.stderr)
            sys.exit(1)
        batch_id = submit_batch(client, args.input, args.completion_window)
        print(batch_id)
        # Save batch id next to input for convenience
        id_file = args.input.replace(".jsonl", ".batch_id")
        with open(id_file, "w") as f:
            f.write(batch_id)
        print(f"Batch ID saved to {id_file}", file=sys.stderr)
        return

    if args.status:
        if not args.batch_id:
            print("--status requires --batch-id", file=sys.stderr)
            sys.exit(1)
        info = get_batch_status(client, args.batch_id)
        print(json.dumps(info, indent=2))
        return

    if args.retrieve:
        if not args.batch_id or not args.output:
            print("--retrieve requires --batch-id and --output", file=sys.stderr)
            sys.exit(1)
        retrieve_results(client, args.batch_id, args.output)
        return

    print("Use --submit, --status, or --retrieve", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
