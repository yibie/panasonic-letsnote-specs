"""Translate Japanese spec values and summaries into English and Chinese.

Every distinct Japanese string in data/specs.json and data/list.json is sent,
in batches, to parallel `pi` workers (the pi coding agent in print mode).
Results accumulate in data/translations.json as {ja: {"en": ..., "zh": ...}},
so the script can be rerun to fill gaps; nothing already translated is resent.
"""
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from common import DATA

OUT = DATA / "translations.json"
BATCH = 30
WORKERS = 6
JA = re.compile(r"[぀-ヿ一-鿿]")
KANA = re.compile(r"[぀-ヿ]")
JA_ONLY_KANJI = re.compile(r"[対応続転込拡駆択図沢帯読売]")


def looks_untranslated(t):
    # "・" sits in the katakana block but is fine in both languages.
    en, zh = t["en"].replace("・", ""), t["zh"].replace("・", "")
    return bool(JA.search(en) or KANA.search(zh) or JA_ONLY_KANJI.search(zh))

PROMPT = """Translate each Japanese laptop specification string (Panasonic Let's note) into English and Simplified Chinese.
Rules:
- Keep model numbers, part numbers, numbers, units, standards and product names exactly as written (e.g. Windows 11 Pro, IEEE802.11ax, USB Type-C, Thunderbolt™4, W52/W53/W56).
- Keep the " / " separators, "・" bullets and ▼ markers so the structure stays the same.
- インテル = Intel / 英特尔; 搭載されていません = Not equipped / 未配备; 約 = approx. / 约; 型 (screen size) = -inch / 英寸;
  ドット = dots / 像素; 対応 = supported / 支持; 準拠 = compliant / 符合.
- The English must contain no Japanese characters; the Chinese must contain no kana and no Japanese-only kanji (対, 応, 続, 転, 込, 拡, 駆, 択).
- Chinese must be Simplified Chinese.
Reply with ONLY a JSON object {{"en": [...], "zh": [...]}}: both arrays in the same order and with exactly {n} items.

Input:
{items}"""


def pi(prompt):
    res = subprocess.run(
        ["pi", "-p", "--no-tools", "--no-session", "-ne", "-ns", "-np", "-nc", "--no-themes",
         "--offline", "--thinking", "off", prompt],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600,
    )
    m = re.search(r"\{.*\}", res.stdout, re.S)
    if not m:
        raise ValueError(f"no JSON in pi output: {res.stdout[-300:]!r} {res.stderr[-300:]!r}")
    return json.loads(m.group(0))


def translate(batch, depth=0):
    """Return {ja: {"en", "zh"}} for batch; split the batch when pi miscounts."""
    try:
        out = pi(PROMPT.format(n=len(batch), items=json.dumps(batch, ensure_ascii=False)))
        en, zh = out["en"], out["zh"]
        if len(en) == len(batch) == len(zh) and all(isinstance(x, str) for x in en + zh):
            return {ja: {"en": e, "zh": z} for ja, e, z in zip(batch, en, zh)}
        raise ValueError(f"expected {len(batch)} items, got {len(en)}/{len(zh)}")
    except Exception as e:
        if len(batch) == 1 and depth >= 2:
            print(f"  giving up on {batch[0][:40]!r}: {e}", file=sys.stderr, flush=True)
            return {}
        if len(batch) == 1:
            return translate(batch, depth + 1)
        mid = len(batch) // 2
        return {**translate(batch[:mid], depth), **translate(batch[mid:], depth)}


def main():
    specs = json.loads((DATA / "specs.json").read_text())
    rows = json.loads((DATA / "list.json").read_text())
    texts = {v for part in specs.values() for _, _, v in part} | {r["summary"] for r in rows if r["summary"]}
    # Item names without a fixed label, and the short cells of the comparison table.
    from generate import glance, spec_key
    from labels import LABELS
    texts |= {spec_key(row) for part in specs.values() for row in part} - set(LABELS)
    texts |= {cell for part in specs.values() for cell in glance(part)}
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    if "--fix" in sys.argv:  # drop translations that still contain Japanese and redo them
        bad = [k for k, t in done.items() if looks_untranslated(t)]
        print(f"retranslating {len(bad)} entries with leftover Japanese", flush=True)
        for k in bad:
            del done[k]
    todo = sorted(t for t in texts if JA.search(t) and t not in done)
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    print(f"{len(done)} cached, {len(todo)} to translate in {len(batches)} batches", flush=True)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(translate, b) for b in batches]
        for i, f in enumerate(as_completed(futures), 1):
            done.update(f.result())
            OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
            print(f"batch {i}/{len(batches)} done, {len(done)} translated", flush=True)
    missing = [t for t in texts if JA.search(t) and t not in done]
    print(f"finished: {len(done)} translated, {len(missing)} missing", flush=True)


if __name__ == "__main__":
    main()
