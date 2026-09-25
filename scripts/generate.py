"""Build one folder per Let's note model and language (e.g. ja/CF-SV8/).

Input:  data/list.json   (fetch_list.py)   every part number, summary, dates
        data/specs.json  (fetch_specs.py)  full official spec sheet per part
        data/images.json (fetch_images.py) product photos per model
Output: <lang>/<model>/README.md, <lang>/README.md and the root README.md
"""
import json
import re
import shutil
from collections import defaultdict

from common import DATA, ROOT
from i18n import LANG_NAMES, LANGS, STRINGS, color, screen, size
from labels import LABELS, LABELS_ZH

LIST_URL = "https://panasonic.jp/pc/support/products/"
SPEC_URL = "https://panasonic.jp/pc/p-db/{}_spec.html"


def model_of(row):
    """CF-SV8RDCVS -> CF-SV8, CF-SV72DFQR -> CF-SV7, CF-S10EWHDS -> CF-S10."""
    m = re.match(r"(CF|AL)-([A-Z]+)(\d+)", row["part"])
    if not m:
        return None
    prefix, letters, digits = m.groups()
    series = row["series"] or ""
    # Two-letter families (SV, LV, RZ...) number generations with one digit;
    # a second digit marks a sub-variant of the same generation.
    if not re.search(r"\d", series) and len(letters) >= 2:
        digits = digits[0]
    return f"{prefix}-{letters}{digits}"


def label(item, lang):
    if lang == "ja":
        return item
    return (LABELS if lang == "en" else LABELS_ZH).get(item) or tr(item, lang)


def spec_key(row):
    group, item, _ = row
    return f"{group} / {item}" if group and group != item else item


def md(s):
    return (s or "—").replace("|", "\\|")


def first(rows, *items):
    for group, item, value in rows:
        if item in items or group in items:
            return value
    return ""


def glance(rows):
    """Short key specs of one part for the comparison table."""
    # Old sheets list the Centrino platform first; pick the actual processor line.
    lines = first(rows, "CPU").split(" / ")
    cpu = next((l for l in lines if re.search(r"Core|Pentium|Celeron|Atom|Crusoe|Ultra", l)), lines[0])
    cpu = re.sub(r"(?:インテル|Intel|モバイル)[®]*(?:\(R\))?\s*|プロセッサー?|™|\(TM\)|TM|\(R\)|®", "", cpu)
    cpu = re.sub(r"\s+", " ", re.split(r"\s*[（(]", cpu)[0]).strip()
    mem = re.split(r"[（(/]", first(rows, "メインメモリー"))[0].replace("標準", "").strip()
    storage = first(rows, "ストレージ", "フラッシュメモリードライブ", "ハードディスクドライブ")
    storage = re.sub(r"フラッシュメモリードライブ|（SSD）|^SSD：", "", storage)
    storage = re.split(r"上記|うち|[（(]", storage)[0].strip(" ：:")
    weight_text = first(rows, "質量(バッテリーを含む）", "質量")
    kg = re.search(r"約\s*([\d.]+)\s*kg", weight_text)
    g = re.search(r"約\s*([\d,]+)\s*g", weight_text)
    weight = f"{kg.group(1)} kg" if kg else f"{int(g.group(1).replace(',', '')) / 1000:g} kg" if g else "—"
    battery = re.search(r"約\s*([\d.]+)\s*時間", first(rows, "駆動／充電時間", "バッテリー駆動時間", "バッテリー"))
    return [cpu[:60], mem[:30], storage[:40], weight, f"{battery.group(1)} h" if battery else "—"]


def fmt_month(m):
    return m or "—"


TRANSLATIONS = json.loads((DATA / "translations.json").read_text()) if (DATA / "translations.json").exists() else {}


def tr(value, lang):
    """Spec text in the page language; falls back to the Japanese original."""
    if lang == "ja" or not value:
        return value
    return TRANSLATIONS.get(value, {}).get(lang, value)


def localize_units(value, lang):
    if lang == "ja":
        return value
    value = value.replace("Mバイト", "MB").replace("Gバイト", "GB")
    return value.replace("超低電圧版", "ULV " if lang == "en" else "超低电压版 ").replace("低電圧版", "LV " if lang == "en" else "低电压版 ")


def image_block(model, img, T, lang, screen_text, color_text, year, rel):
    """Markdown image with descriptive alt text, title and caption in the page language."""
    parts = img["parts"]
    alt = T["alt"].format(
        model=model, size=size(screen_text, lang),
        color=(f", {color_text}" if lang == "en" else f"、{color_text}" if lang == "ja" else f"，{color_text}") if color_text else "",
        year=(f", {year}" if lang == "en" else f"、{year}年発売" if lang == "ja" else f"，{year} 年") if year else "",
    )
    if len(parts) == 1:
        alt += T["alt_part"].format(part=parts[0])
    shown = ", ".join(parts[:4]) + (" …" if len(parts) > 4 else "")
    caption = T["caption"].format(model=model, parts_note=T["caption_parts"].format(parts=shown),
                                  color_note=(f", {color_text}" if lang == "en" else f"・{color_text}" if lang == "ja" else f"，{color_text}") if color_text else "")
    return [f'![{alt}]({rel}{img["file"]} "{T["img_title"].format(model=model)}")', "", f"*{caption}*", ""]


def model_page(model, parts, specs, images, prev_m, next_m, lang):
    T = STRINGS[lang]
    series = next((p["series"] for p in parts if p["series"]), None)
    screen_ja = next((p["screen"] for p in parts if p["screen"]), None)
    released = sorted(p["released"] for p in parts if p["released"])
    first_r, last_r = (released[0], released[-1]) if released else (None, None)
    span = first_r if first_r == last_r else f"{first_r} – {last_r}"
    rel = "../../"  # from <lang>/<model>/ back to the repo root

    switch = " · ".join(f"**{LANG_NAMES[l]}**" if l == lang else f"[{LANG_NAMES[l]}](../../{l}/{model}/)" for l in LANGS)
    lines = [f"# {T['title'].format(model=model)}", "", switch, ""]
    intro = T["intro"].format(
        model=model, n=len(parts),
        series=T["series"].format(series=series) if series else "",
        screen=T["screen"].format(screen=screen(screen_ja, lang)) if screen_ja else ("）" if lang == "ja" and series else ""),
        released=T["released"].format(span=span) if first_r else "",
    )
    if any(p["part"] in specs for p in parts):
        intro += T["has_sheets"]
    lines += [intro, ""]

    imgs = images.get(model, [])
    def color_of(img):
        return color(first(specs.get(img["parts"][0], []), "本体カラー"), lang)
    year = first_r[:4] if first_r else ""
    if imgs:
        lines += image_block(model, imgs[0], T, lang, screen_ja, color_of(imgs[0]), year, rel)

    lines += [f"## {T['parts']}", "",
              f"| {T['part']} | {T['rel']} | {T['disc']} | {T['summary']} |", "| :-- | :-- | :-- | :-- |"]
    for p in parts:
        name = f"[{p['part']}]({SPEC_URL.format(p['part'])})" if p["part"] in specs else p["part"]
        status = T["on_sale"] if p["current"] else fmt_month(p["discontinued"])
        lines.append(f"| {name} | {fmt_month(p['released'])} | {status} | {md(tr(p['summary'], lang))} |")
    lines.append("")

    with_specs = [p["part"] for p in parts if p["part"] in specs]
    if with_specs:
        values = defaultdict(dict)  # key -> part -> value
        order = []
        for part in with_specs:
            for row in specs[part]:
                k = spec_key(row)
                if k not in values:
                    order.append(k)
                values[k][part] = row[2]
        common = [k for k in order if len(values[k]) == len(with_specs) and len(set(values[k].values())) == 1]
        differing = [k for k in order if k not in common]

        heading = T["specs_one"] if len(with_specs) == 1 else T["specs_common"]
        lines += [f"## {heading}", "", f"| {T['item']} | {T['value']} |", "| :-- | :-- |"]
        for k in common:
            lines.append(f"| {md(label(k, lang))} | {md(tr(next(iter(values[k].values())), lang))} |")
        lines.append("")
        if differing and len(with_specs) > 1:
            lines += [f"## {T['diff']}", "",
                      f"| {T['part']} | {T['cpu']} | {T['mem']} | {T['storage']} | {T['weight']} | {T['battery']} |",
                      "| :-- | :-- | :-- | :-- | :-- | :-- |"]
            for part in with_specs:
                cells = [localize_units(tr(v, lang), lang) for v in glance(specs[part])]
                lines.append(f"| {part} | " + " | ".join(md(v or "—") for v in cells) + " |")
            lines.append("")
            for part in with_specs:
                lines += ["<details>", f"<summary>{T['full_diff'].format(part=part)}</summary>", "",
                          f"| {T['item']} | {T['value']} |", "| :-- | :-- |"]
                for k in differing:
                    if part in values[k]:
                        lines.append(f"| {md(label(k, lang))} | {md(tr(values[k][part], lang))} |")
                lines += ["", f"{T['sheet']}: <{SPEC_URL.format(part)}>", "", "</details>", ""]
    else:
        lines += [T["no_sheet"], ""]

    if len(imgs) > 1:
        lines += [f"## {T['photos']}", ""]
        for img in imgs[1:7]:
            lines += image_block(model, img, T, lang, screen_ja, color_of(img), year, rel)

    lines += [f"## {T['related']}", ""]
    if next_m:
        lines.append(f"- {T['newer']}: [{next_m}](../{next_m}/)")
    if prev_m:
        lines.append(f"- {T['older']}: [{prev_m}](../{prev_m}/)")
    lines += [f"- [{T['all']}](../)", "", "---", "", T["source"].format(list=LIST_URL), ""]
    return "\n".join(lines)


def index_page(models, series_of, first_release, lang, prefix=""):
    T = STRINGS[lang]
    n_parts = sum(len(v) for v in models.values())
    switch = " · ".join(f"[{LANG_NAMES[l]}]({'' if prefix else '../'}{l}/)" for l in LANGS)
    lines = [f"# {T['index_title']}", "", switch, "",
             T["index_intro"].format(models=len(models), parts=n_parts), ""]
    by_series = defaultdict(list)
    for m in models:
        by_series[series_of[m]].append(m)
    # Current models have no release month in the list; sort them first.
    ordered = sorted(by_series, key=lambda s: max(first_release[m] or "9999" for m in by_series[s]), reverse=True)
    lines += [f"| {T['index_series']} | {T['index_models']} |", "| :-- | :-- |"]
    for s in ordered:
        ms = sorted(by_series[s], key=lambda m: first_release[m] or "9999", reverse=True)
        cells = ", ".join(f"[{m}](./{prefix}{m}/) ({first_release[m][:4] if first_release[m] else T['on_sale']})" for m in ms)
        lines.append(f"| {s} | {cells} |")
    lines += ["", "---", "", T["source"].format(list=LIST_URL), ""]
    return "\n".join(lines)


def main():
    rows = json.loads((DATA / "list.json").read_text())
    specs = json.loads((DATA / "specs.json").read_text()) if (DATA / "specs.json").exists() else {}
    images = json.loads((DATA / "images.json").read_text()) if (DATA / "images.json").exists() else {}

    models = defaultdict(list)
    for r in rows:
        m = model_of(r)
        if m:
            models[m].append(r)

    series_of, first_release = {}, {}
    for m, parts in models.items():
        parts.sort(key=lambda p: p["released"] or "9999", reverse=True)
        series_of[m] = next((p["series"] for p in parts if p["series"]), None) or re.sub(r"\d+$", "", m.split("-")[1])
        dates = [p["released"] for p in parts if p["released"]]
        first_release[m] = min(dates) if dates else None

    by_series = defaultdict(list)
    for m in models:
        by_series[series_of[m]].append(m)
    for lang in LANGS:
        base = ROOT / lang
        base.mkdir(exist_ok=True)
        for d in base.iterdir():
            if d.is_dir() and d.name not in models:
                shutil.rmtree(d)
        for s, ms in by_series.items():
            ms.sort(key=lambda m: first_release[m] or "9999")
            for i, m in enumerate(ms):
                prev_m = ms[i - 1] if i > 0 else None
                next_m = ms[i + 1] if i + 1 < len(ms) else None
                (base / m).mkdir(exist_ok=True)
                (base / m / "README.md").write_text(model_page(m, models[m], specs, images, prev_m, next_m, lang))
        (base / "README.md").write_text(index_page(models, series_of, first_release, lang))

    (ROOT / "README.md").write_text(index_page(models, series_of, first_release, "en", prefix="en/"))
    print(f"generated {len(models)} models x {len(LANGS)} languages; "
          f"{sum(p['part'] in specs for ps in models.values() for p in ps)} parts with full specs, "
          f"{sum(m in images for m in models)} models with images")


if __name__ == "__main__":
    main()
