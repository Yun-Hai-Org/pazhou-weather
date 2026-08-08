"""Send WeCom markdown via webhook URL (same transport as weather card)."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request


def first_webhook_url(raw: str) -> str:
    parts = re.split(r"[,;\n]+", raw)
    return next((p.strip() for p in parts if p.strip()), "")


def main() -> int:
    raw = os.environ.get("WECOM_WEBHOOK_URL", "")
    url = first_webhook_url(raw)
    if not url.startswith("https://"):
        print(f"::warning::WECOM_WEBHOOK_URL invalid or missing https:// (len={len(raw)})")
        return 0

    content_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/wecom_content.txt"
    with open(content_path, encoding="utf-8") as f:
        content = f.read()

    payload = json.dumps(
        {"msgtype": "markdown", "markdown": {"content": content}},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"::warning::WeCom HTTP {exc.code}: {body[:300]}")
        return 0
    except Exception as exc:  # noqa: BLE001 — notify must not fail the job
        print(f"::warning::WeCom notify failed: {type(exc).__name__}: {exc}")
        return 0

    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        data = {}
    errcode = data.get("errcode", 0)
    if errcode not in (0, None):
        print(
            f"::warning::WeCom webhook errcode={errcode} "
            f"errmsg={data.get('errmsg')} body={body[:300]}"
        )
        return 0

    title = os.environ.get("TITLE", "")
    print(f"WeCom notification sent: {title} (http={status})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
