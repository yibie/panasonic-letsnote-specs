"""Download the official product image of every part into images/<model>/.

The image URL is the og:image of each cached spec page. Identical images
(same bytes) are stored once. Output: data/images.json
  {model: [{"file", "sha256", "parts": [...], "url"}], ...}
ordered by how many parts use the image (the first one is the hero).
"""
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from common import CACHE, DATA, ROOT
from generate import model_of

IMAGES = ROOT / "images"
# Cap the stored size; scene7 resizes on the fly.
SIZE_PARAMS = "wid=1200&qlt=85"


def og_image(part):
    path = CACHE / f"spec-{part}.html"
    if not path.exists():
        return None
    m = re.search(r'<meta property="og:image" content="([^"]+)"', path.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def download(url):
    """Return (bytes, extension) for url, cached under .cache/img/."""
    key = hashlib.sha1(url.encode()).hexdigest()
    cached = list((CACHE / "img").glob(key + ".*"))
    if cached:
        return cached[0].read_bytes(), cached[0].suffix
    sized = url + ("&" if "?" in url else "?") + SIZE_PARAMS
    res = subprocess.run(["curl", "-sfL", "-m", "60", "-w", "\n%{content_type}", sized], capture_output=True)
    if res.returncode != 0:
        return None, None
    body, _, ctype = res.stdout.rpartition(b"\n")
    ext = ".png" if b"png" in ctype else ".jpg"
    (CACHE / "img").mkdir(parents=True, exist_ok=True)
    (CACHE / "img" / (key + ext)).write_bytes(body)
    return body, ext


def main():
    rows = [r for r in json.loads((DATA / "list.json").read_text()) if r["part"].startswith("CF-")]
    url_of = {r["part"]: og_image(r["part"]) for r in rows}
    urls = sorted({u for u in url_of.values() if u})
    with ThreadPoolExecutor(max_workers=4) as pool:
        got = dict(zip(urls, pool.map(download, urls)))

    # model -> sha -> {parts, url, bytes, ext}
    by_model = defaultdict(dict)
    models_of_sha = defaultdict(set)
    for r in rows:
        url = url_of[r["part"]]
        body, ext = got.get(url, (None, None)) if url else (None, None)
        if not body:
            continue
        sha = hashlib.sha256(body).hexdigest()
        model = model_of(r)
        entry = by_model[model].setdefault(sha, {"parts": [], "url": url, "body": body, "ext": ext})
        entry["parts"].append(r["part"])
        models_of_sha[sha].add(model)

    shared = {sha for sha, ms in models_of_sha.items() if len(ms) > 1}
    out = {}
    for model, entries in sorted(by_model.items()):
        folder = IMAGES / model
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.iterdir():
            old.unlink()
        ranked = sorted(entries.items(), key=lambda kv: (kv[0] in shared, -len(kv[1]["parts"])))
        out[model] = []
        for sha, e in ranked:
            name = f"panasonic-letsnote-{model.lower()}-{e['parts'][0].lower()}{e['ext']}"
            (folder / name).write_bytes(e["body"])
            out[model].append({"file": f"images/{model}/{name}", "sha256": sha, "parts": e["parts"],
                               "url": e["url"], "shared_with_other_models": sha in shared})
    (DATA / "images.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    total = sum(p.stat().st_size for p in IMAGES.rglob("*") if p.is_file())
    print(f"{len(urls)} urls, {sum(len(v) for v in out.values())} distinct images for {len(out)} models, "
          f"{total / 1e6:.1f} MB; shared across models: {len(shared)}")
    for model, v in out.items():
        if all(e["shared_with_other_models"] for e in v):
            print("  only generic image:", model)


if __name__ == "__main__":
    main()
