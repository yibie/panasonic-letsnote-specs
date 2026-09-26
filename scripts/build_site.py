"""Build the static site (https://letsnote-specs.github.io/) into docs/.

Pages:
  /             showcase in English (one glass case per model)
  /ja/, /zh/    the showcase in Japanese and Chinese (/en/ repeats /, canonical to /)
  /<lang>/<model>/  full spec page, rendered from the same Markdown as the repo
  sitemap.xml, robots.txt
Publish with scripts/deploy_site.sh.
"""
import html
import json
import re
import shutil
import subprocess
from collections import defaultdict

from common import ROOT
from generate import collect, model_page
from i18n import LANG_NAMES, LANGS, STRINGS, screen

SITE = "https://letsnote-specs.github.io/"
REPO = "https://github.com/yibie/panasonic-letsnote-specs"
DOCS = ROOT / "docs"
ASSETS = ROOT / "scripts" / "site"
THUMB_WIDTH = 480
IMAGE_WIDTH = 900

TEXT = {
    "en": {
        "title": "The Let's note Cabinet",
        "doc": "Let's note Cabinet · every Panasonic Let's note since 1996",
        "desc": "Specifications of every Panasonic Let's note laptop since 1996: {models} models and {parts} part numbers, "
                "with release dates, photos and the full official spec sheet of each.",
        "curator": "Every Let's note since 1996, one case each. Open any of them for the full spec sheet.",
        "count": "{models} models · {parts} part numbers",
        "lost": "No photo survived for this one.",
        "sign": "— compiled by hand from Panasonic's official spec sheets",
        "era": "the {d}0s", "era_count": "{n} models", "now": "now",
        "back": "← The Let's note Cabinet",
        "foot": "Product images © Panasonic · Not affiliated with Panasonic.",
    },
    "ja": {
        "title": "レッツノート陳列棚",
        "doc": "レッツノート陳列棚 · 1996年以降の全機種スペック一覧",
        "desc": "1996年以降のパナソニック レッツノート全{models}機種・{parts}品番のスペック一覧。発売日、写真、公式仕様表を機種ごとに掲載。",
        "curator": "1996年から現在まで、レッツノート全機種を一台ずつ並べました。開けば、その機種のスペックがすべて読めます。",
        "count": "{models} 機種 · {parts} 品番",
        "lost": "この一台の写真は残っていません。",
        "sign": "— パナソニック公式の仕様表から、手作業でまとめました",
        "era": "{d}0年代", "era_count": "{n} 機種", "now": "発売中",
        "back": "← レッツノート陳列棚",
        "foot": "製品画像 © Panasonic · パナソニックとは関係のない非公式サイトです。",
    },
    "zh": {
        "title": "Let's note 陈列柜",
        "doc": "Let's note 陈列柜 · 1996 年以来松下 Let's note 全部机型规格",
        "desc": "1996 年以来松下 Let's note 全部 {models} 个机型、{parts} 个型号的规格参数，含发售日期、图片和官方规格表。",
        "curator": "1996 年至今的每一台 Let's note，都在这里占一格。点开，就是它的完整规格。",
        "count": "{models} 个机型 · {parts} 个型号",
        "lost": "这一台的照片，没能留下来。",
        "sign": "—— 按松下官方规格表整理，一格一格摆好",
        "era": "{d}0 年代", "era_count": "{n} 个机型", "now": "在售",
        "back": "← Let's note 陈列柜",
        "foot": "产品图片 © Panasonic · 本站为非官方整理，与松下公司无关。",
    },
}
OG_LOCALE = {"en": "en_US", "ja": "ja_JP", "zh": "zh_CN"}
HREFLANG = {"en": "en", "ja": "ja", "zh": "zh-Hans"}
BASE = SITE.rstrip("/")


def esc(s):
    return html.escape(s or "", quote=True)


def resize(src, folder, width):
    """Copy a repo image (images/<model>/<file>) into docs/<folder>/, scaled to width."""
    name = src.split("/", 1)[1] if folder == "images" else src.split("/")[-1]
    out = DOCS / folder / name
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["sips", "-Z", str(width), str(ROOT / src), "--out", str(out)], check=True, capture_output=True)
    return "/" + str(out.relative_to(DOCS))


# ---------- Markdown (the subset generate.py writes) -> HTML ----------

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"&lt;(https?://[^\s&]+)&gt;", r'<a href="\1">\1</a>', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return s.replace("\\|", "|")


def cells(line):
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def figure(line, caption):
    alt, src, title = re.match(r'!\[(.*?)\]\((\S+?)(?: "(.*?)")?\)', line).groups()
    src = "/" + re.sub(r"^(\.\./)+", "", src)  # ../../images/... -> /images/...
    cap = f"<figcaption>{inline(caption)}</figcaption>" if caption else ""
    return (f'<figure><div class="vitrine"><canvas class="glass" aria-hidden="true"></canvas>'
            f'<img src="{esc(src)}" alt="{esc(alt)}" title="{esc(title)}" loading="lazy" decoding="async"></div>{cap}</figure>')


def md_to_html(md):
    lines, out, i = md.split("\n"), [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            out.append(f"<h{level}>{inline(line[level:].strip())}</h{level}>")
            i += 1
        elif line.strip() == "---":
            out.append("<hr>")
            i += 1
        elif line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            head = "".join(f"<th>{inline(c)}</th>" for c in cells(block[0]))
            body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells(r)) + "</tr>" for r in block[2:])
            cls = f' class="cols-{len(cells(block[0]))}"'
            out.append(f'<div class="table-wrap"><table{cls}><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
        elif line.startswith(("<details>", "</details>", "<summary>")):
            out.append(line)
            i += 1
        elif line.startswith("!["):
            figs = []
            while i < len(lines) and lines[i].startswith("!["):
                img, i = lines[i], i + 1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                caption = None
                if i < len(lines) and lines[i].startswith("*") and lines[i].rstrip().endswith("*"):
                    caption, i = lines[i].strip()[1:-1], i + 1
                    while i < len(lines) and not lines[i].strip():
                        i += 1
                figs.append(figure(img, caption))
            out.append(f'<div class="{"photos" if len(figs) > 1 else "hero"}">{"".join(figs)}</div>')
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{inline(lines[i][2:])}</li>")
                i += 1
            out.append(f"<ul>{''.join(items)}</ul>")
        else:
            out.append(f"<p>{inline(line)}</p>")
            i += 1
    return "\n".join(out)


# ---------- Page shell ----------

def shell(lang, title, desc, canonical, alternates, body, body_class, jsonld, image=None):
    alt_links = "\n".join(f'<link rel="alternate" hreflang="{HREFLANG[l]}" href="{BASE}{u}">' for l, u in alternates.items())
    alt_links += f'\n<link rel="alternate" hreflang="x-default" href="{BASE}{alternates["en"]}">'
    og_image = f'<meta property="og:image" content="{BASE}{image}">\n' if image else ""
    return f"""<!doctype html>
<html lang="{HREFLANG[lang]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{BASE}{canonical}">
{alt_links}
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:locale" content="{OG_LOCALE[lang]}">
<meta property="og:url" content="{BASE}{canonical}">
{og_image}<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&family=Klee+One:wght@400;600&display=swap" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/lxgw-wenkai-webfont@1.7.0/style.css" rel="stylesheet" media="print" onload="this.media='all'">
<link rel="stylesheet" href="/site.css">
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
</head>
<body class="{body_class}">
{body}
<script src="/shader.js" defer></script>
</body>
</html>
"""


def lang_switch(lang, urls):
    links = "".join(f'<a href="{u}" hreflang="{HREFLANG[l]}"{" aria-current=page" if l == lang else ""}>{LANG_NAMES[l]}</a>'
                    for l, u in urls.items())
    return f'<nav class="lang-switch" aria-label="Language">{links}</nav>'


# ---------- Showcase ----------

def showcase(lang, info, n_parts):
    X = TEXT[lang]
    eras = defaultdict(list)
    for m in info.values():
        eras[(m["year"] or "2099")[:3]].append(m)
    eras["202"] += eras.pop("209", [])  # models on sale have no release month yet
    shelves = []
    for d in sorted(eras, reverse=True):
        ms = sorted(eras[d], key=lambda m: (m["year"] or "9999", m["model"]), reverse=True)
        cards = []
        for m in ms:
            href = f"/{lang}/{m['model']}/"
            tilt = (sum(map(ord, m["model"])) % 7 - 3) * 0.8
            year = m["year"] or X["now"]
            if m["thumb"]:
                alt = f"Panasonic Let's note {m['model']} ({year})"
                exhibit = (f'<canvas class="glass" aria-hidden="true"></canvas>'
                           f'<img src="{m["thumb"]}" alt="{esc(alt)}" loading="lazy" decoding="async">')
            else:
                exhibit = f'<p class="lost hand">{esc(X["lost"])}</p>'
            scr = f'<span class="screen hand">{esc(m["screen"][lang])}</span>' if m["screen"][lang] else ""
            langs = "".join(f'<a href="/{l}/{m["model"]}/" hreflang="{HREFLANG[l]}">{"EN" if l == "en" else LANG_NAMES[l]}</a>'
                            for l in LANGS)
            cards.append(f"""
      <li class="case">
        <a class="vitrine" href="{href}">{exhibit}</a>
        <div class="tag hand" style="--tilt:{tilt:.1f}deg">
          <a href="{href}">{m['model']}</a>
          <span class="year">{esc(year)}</span>
          {scr}
          <span class="langs">{langs}</span>
        </div>
      </li>""")
        shelves.append(f"""
    <section class="shelf">
      <h2><span class="era hand">{esc(X['era'].format(d=d))}</span>
        <span class="note hand">{esc(X['era_count'].format(n=len(ms)))}</span></h2>
      <ul class="row">{''.join(cards)}
      </ul>
    </section>""")
    urls = {"en": "/", "ja": "/ja/", "zh": "/zh/"}
    body = f"""<header>
  {lang_switch(lang, urls)}
  <h1>{esc(X['title'])}</h1>
  <p class="curator">{esc(X['curator'])}</p>
  <span class="count">{esc(X['count'].format(models=len(info), parts=n_parts))}</span>
</header>
<main>{''.join(shelves)}
</main>
<footer>
  <span class="sign">{esc(X['sign'])}</span>
  <small><a href="{REPO}">{REPO}</a> · {esc(X['foot'])}</small>
</footer>"""
    jsonld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": X["title"],
              "url": BASE + urls[lang], "inLanguage": HREFLANG[lang]}
    desc = X["desc"].format(models=len(info), parts=n_parts)
    return shell(lang, X["doc"], desc, urls[lang], urls, body, "showcase", jsonld), urls


# ---------- Model page ----------

def detail(lang, m, d, info):
    T, X = STRINGS[lang], TEXT[lang]
    prev_m, next_m = d["neighbours"][m]
    md = model_page(m, d["models"][m], d["specs"], d["images"], prev_m, next_m, lang, target="site")
    # The intro paragraph after the H1 doubles as the meta description.
    intro = next(l for l in md.split("\n")[1:] if l.strip() and not l.startswith(("#", "!", "|")))
    desc = re.sub(r"\*\*|\[([^\]]+)\]\([^)]+\)", lambda x: x.group(1) or "", intro)
    title = T["title"].format(model=m)
    urls = {l: f"/{l}/{m}/" for l in LANGS}
    home = "/" if lang == "en" else f"/{lang}/"
    hero = info[m]["image"]
    body = f"""<header>
  <div class="top"><a class="crumbs" href="{home}">{esc(X['back'])}</a>{lang_switch(lang, urls)}</div>
</header>
<article>
{md_to_html(md)}
</article>
<footer>
  <span class="sign">{esc(X['sign'])}</span>
  <small>{esc(X['foot'])}</small>
</footer>"""
    rel = d["first_release"][m]
    product = {"@context": "https://schema.org", "@type": "Product", "name": f"Panasonic Let's note {m}",
               "model": m, "brand": {"@type": "Brand", "name": "Panasonic"}, "category": "Laptop",
               "description": desc, "url": BASE + urls[lang]}
    if hero:
        product["image"] = BASE + hero
    if rel:
        product["releaseDate"] = rel
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": X["title"], "item": BASE + home},
        {"@type": "ListItem", "position": 2, "name": m, "item": BASE + urls[lang]}]}
    return shell(lang, f"{title} | {X['title']}", desc, urls[lang], urls, body, "detail", [product, crumbs], hero)


def main():
    d = collect()
    models, images = d["models"], d["images"]
    for sub in LANGS:
        if (DOCS / sub).exists():
            shutil.rmtree(DOCS / sub)
    DOCS.mkdir(exist_ok=True)

    info = {}
    for m, parts in models.items():
        scr = next((p["screen"] for p in parts if p["screen"]), None)
        imgs = images.get(m, [])
        paths = [resize(img["file"], "images", IMAGE_WIDTH) for img in imgs[:7]]  # hero + gallery on the page
        info[m] = {
            "model": m,
            "year": d["first_release"][m][:4] if d["first_release"][m] else None,
            "screen": {l: screen(scr, l) if scr else "" for l in LANGS},
            "thumb": resize(imgs[0]["file"], "thumbs", THUMB_WIDTH) if imgs else None,
            "image": paths[0] if paths else None,
        }
    n_parts = sum(len(p) for p in models.values())

    pages = []  # alternates per page, for the sitemap
    for lang in LANGS:
        page, urls = showcase(lang, info, n_parts)
        out = DOCS / ("index.html" if lang == "en" else f"{lang}/index.html")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page)
    pages.append(urls)
    # /en/ is where the model pages' "all models" link points: same page as /, canonical to /.
    (DOCS / "en").mkdir(exist_ok=True)
    (DOCS / "en" / "index.html").write_text((DOCS / "index.html").read_text())

    for m in models:
        for lang in LANGS:
            out = DOCS / lang / m / "index.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(detail(lang, m, d, info))
        pages.append({l: f"/{l}/{m}/" for l in LANGS})

    shutil.copy(ASSETS / "site.css", DOCS / "site.css")
    shutil.copy(ASSETS / "shader.js", DOCS / "shader.js")
    (DOCS / ".nojekyll").write_text("")
    (DOCS / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}sitemap.xml\n")
    entries = []
    for urls in pages:
        alts = "".join(f'<xhtml:link rel="alternate" hreflang="{HREFLANG[l]}" href="{BASE}{u}"/>' for l, u in urls.items())
        entries += [f"<url><loc>{BASE}{u}</loc>{alts}</url>" for u in urls.values()]
    (DOCS / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(entries) + "\n</urlset>\n")

    size = sum(p.stat().st_size for p in DOCS.rglob("*") if p.is_file())
    print(f"docs/: 3 showcases + {len(models) * 3} model pages, {len(entries)} sitemap URLs, {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
