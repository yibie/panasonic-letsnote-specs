"""Build the GitHub Pages showcase in docs/.

One page, one glass case per model. Every case links to the model's spec page
in the repository (github.com/.../tree/main/<lang>/<model>), so the spec
content lives only in the repo and the showcase adds links to it.
Output: docs/index.html, docs/thumbs/*, docs/.nojekyll
"""
import html
import json
import re
import subprocess
from collections import defaultdict

from common import DATA, ROOT
from generate import model_of
from i18n import screen

REPO = "https://github.com/yibie/panasonic-letsnote-specs"
SITE = "https://www.gtdstudy.com/panasonic-letsnote-specs/"
DOCS = ROOT / "docs"
THUMB_WIDTH = 480

def thumbnail(src):
    """Resize src (repo-relative) into docs/thumbs/, keeping PNG alpha."""
    out = DOCS / "thumbs" / src.split("/")[-1]
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["sips", "-Z", str(THUMB_WIDTH), str(ROOT / src), "--out", str(out)],
                       check=True, capture_output=True)
    return f"thumbs/{out.name}"


def main():
    rows = json.loads((DATA / "list.json").read_text())
    images = json.loads((DATA / "images.json").read_text())

    models = defaultdict(list)
    for r in rows:
        m = model_of(r)
        if m:
            models[m].append(r)

    info = {}
    for m, parts in models.items():
        dates = sorted(p["released"] for p in parts if p["released"])
        series = next((p["series"] for p in parts if p["series"]), None) or re.sub(r"\d+$", "", m.split("-")[1])
        scr = next((p["screen"] for p in parts if p["screen"]), None)
        info[m] = {
            "model": m,
            "series": series,
            "year": dates[0][:4] if dates else None,
            "screen": {l: screen(scr, l) if scr else "" for l in ("en", "ja", "zh")},
            "parts": len(parts),
            "thumb": thumbnail(images[m][0]["file"]) if m in images else None,
        }

    # Shelves by decade: most series have a single model, so a shelf per
    # series would leave long empty rows.
    eras = defaultdict(list)
    for m in info.values():
        eras[(m["year"] or "2099")[:3]].append(m)
    ERA_NAME = {"en": "the {d}0s", "ja": "{d}0年代", "zh": "{d}0 年代"}
    ERA_COUNT = {"en": "{n} models", "ja": "{n} 機種", "zh": "{n} 个机型"}

    cases_html = []
    current = eras.pop("209", [])  # models on sale have no release month yet
    eras["202"] += current
    for d in sorted(eras, reverse=True):
        ms = sorted(eras[d], key=lambda m: (m["year"] or "9999", m["model"]), reverse=True)
        cards = []
        for m in ms:
            links = {l: f"{REPO}/tree/main/{l}/{m['model']}" for l in ("en", "ja", "zh")}
            hrefs = " ".join(f'data-href-{l}="{links[l]}"' for l in ("en", "ja", "zh"))
            tilt = (sum(map(ord, m["model"])) % 7 - 3) * 0.8
            year = m["year"] or "now"
            scr = m["screen"]
            year_span = (f'<span class="year">{year}</span>' if m["year"] else
                         '<span class="year" data-en="now" data-ja="発売中" data-zh="在售">now</span>')
            if m["thumb"]:
                alt = f"Panasonic Let's note {m['model']} ({year})"
                exhibit = (f'<canvas class="glass" aria-hidden="true"></canvas>'
                           f'<img src="{m["thumb"]}" alt="{html.escape(alt)}" loading="lazy" decoding="async">')
            else:
                exhibit = '<p class="lost hand" data-i18n="lost"></p>'
            screen_span = (f'<span class="screen hand" data-en="{html.escape(scr["en"])}" data-ja="{html.escape(scr["ja"])}" '
                           f'data-zh="{html.escape(scr["zh"])}">{html.escape(scr["en"])}</span>') if scr["en"] else ""
            cards.append(f'''
      <li class="case">
        <a class="vitrine" href="{links['en']}" {hrefs}>
          {exhibit}
        </a>
        <div class="tag hand" style="--tilt:{tilt:.1f}deg">
          <a href="{links['en']}" {hrefs}>{m['model']}</a>
          {year_span}
          {screen_span}
          <span class="langs"><a href="{links['en']}" lang="en">EN</a><a href="{links['ja']}" lang="ja">日本語</a><a href="{links['zh']}" lang="zh">中文</a></span>
        </div>
      </li>''')
        names = {l: ERA_NAME[l].format(d=d) for l in ERA_NAME}
        counts = {l: ERA_COUNT[l].format(n=len(ms)) for l in ERA_COUNT}
        cases_html.append(f'''
    <section class="shelf">
      <h2><span class="era hand" data-en="{names['en']}" data-ja="{names['ja']}" data-zh="{names['zh']}">{names['en']}</span>
        <span class="note hand" data-en="{counts['en']}" data-ja="{counts['ja']}" data-zh="{counts['zh']}">{counts['en']}</span></h2>
      <ul class="row">{''.join(cards)}
      </ul>
    </section>''')

    n_models = len(info)
    n_parts = sum(m["parts"] for m in info.values())
    page = TEMPLATE.replace("{{CASES}}", "".join(cases_html)) \
        .replace("{{MODELS}}", str(n_models)).replace("{{PARTS}}", str(n_parts)) \
        .replace("{{REPO}}", REPO).replace("{{SITE}}", SITE)
    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(page)
    (DOCS / ".nojekyll").write_text("")
    size = sum(p.stat().st_size for p in DOCS.rglob("*") if p.is_file())
    print(f"docs/index.html: {n_models} cases in {len(cases_html)} shelves, docs/ is {size / 1e6:.1f} MB")


TEMPLATE = (ROOT / "scripts" / "site_template.html").read_text()

if __name__ == "__main__":
    main()
