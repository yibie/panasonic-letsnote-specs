"""Shared helpers: polite cached HTTP fetches and small HTML utilities."""
import html
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / ".cache"
UA = "Mozilla/5.0 (letsnote-specs; +https://github.com)"


def fetch(url, cache_name, delay=0.5):
    """GET url once with curl and cache the body; returns None on 404.

    curl rather than urllib: Python's TLS handshake fails intermittently
    behind some local proxies, while curl does not.
    """
    path = CACHE / cache_name
    if path.exists():
        body = path.read_text(encoding="utf-8")
        return None if body == "404" else body
    for attempt in range(3):
        res = subprocess.run(
            ["curl", "-sL", "-m", "60", "-A", UA, "-H", "Accept-Language: ja",
             "-w", "\n%{http_code}", url],
            capture_output=True,
        )
        out = res.stdout.decode("utf-8", errors="replace")
        body, _, code = out.rpartition("\n")
        if code == "404":
            body = "404"
            break
        if res.returncode == 0 and code == "200":
            break
        time.sleep(5 * (attempt + 1))
    else:
        raise RuntimeError(f"{url}: curl exit {res.returncode}, HTTP {code}")
    time.sleep(delay)
    CACHE.mkdir(exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return None if body == "404" else body


def text(fragment):
    """HTML fragment -> clean single-line text; drops footnote marks like ★3."""
    s = re.sub(r"(?is)<sup>\s*★?\d*\s*</sup>", "", fragment)
    s = re.sub(r"(?i)<br\s*/?>", " / ", s)
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    s = s.replace("★", "")
    s = re.sub(r"\s+", " ", s).strip(" /")
    return s
