"""Parse Panasonic's official discontinued-models list into data/list.json.

Source: https://panasonic.jp/pc/support/products/ (生産終了品一覧), which lists
every Let's note part number since 1999 with a short spec summary, release
month and end-of-production month. Current models come from the lineup page.
"""
import json
import re

from common import DATA, fetch, text

LIST_URL = "https://panasonic.jp/pc/support/products/"
LINEUP_URL = "https://panasonic.jp/cns/pc/products/"


def parse_month(s):
    m = re.search(r"(\d{4})年\s*(\d{1,2})月", s)
    return f"{m.group(1)}-{int(m.group(2)):02d}" if m else None


def parse_list(page):
    rows = []
    sections = re.split(r'<div class="title_box2">', page)[1:]
    for sec in sections:
        heading = text(re.search(r"<h2[^>]*>(.*?)</h2>", sec, re.S).group(1))
        m = re.match(r"Let'?\s*snote\s+(.+?)シリーズ\s*[（(](.+?)[）)]", heading)
        if not m:
            continue
        series, screen = m.group(1).strip(), m.group(2).strip()
        table = re.search(r"<th[^>]*>.*?品番.*?</table>", sec, re.S)
        if not table:
            continue
        carry = None  # release cell shared by several rows via rowspan
        carry_left = 0
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table.group(0), re.S):
            tds = re.findall(r"<td([^>]*)>(.*?)</td>", tr, re.S)
            if len(tds) < 2:
                continue
            # Cells may carry a note after the part number, e.g. "CF-R8GWJCJR / （ブラックモデル）".
            part, _, note = text(tds[0][1]).partition(" / ")
            summary = text(tds[1][1])
            if note:
                summary = f"{note.strip('（）()')}：{summary}"
            if len(tds) >= 3:
                date_cell = text(tds[2][1])
                span = re.search(r'rowspan="(\d+)', tds[2][0])  # source has typos like rowspan="4ｌ"
                carry, carry_left = date_cell, (int(span.group(1)) - 1 if span else 0)
            elif carry_left > 0:
                date_cell = carry
                carry_left -= 1
            else:
                date_cell = ""
            months = re.findall(r"\d{4}年\s*\d{1,2}月", date_cell)
            spec_link = re.search(r'href="([^"]*p-db/[^"]*_spec\.html)"', tds[0][1])
            rows.append({
                "part": part,
                "series": series,
                "screen": screen,
                "summary": summary,
                "released": parse_month(months[0]) if months else None,
                "discontinued": parse_month(months[1]) if len(months) > 1 else None,
                "spec_url": spec_link.group(1) if spec_link else None,
                "current": False,
            })
    return rows


def parse_lineup(page, known):
    rows = []
    for url, part in sorted(set(re.findall(r'(https://panasonic\.jp/pc/p-db/(CF-[A-Z0-9]+)_spec\.html)', page))):
        if part not in known:
            rows.append({"part": part, "series": None, "screen": None, "summary": None,
                         "released": None, "discontinued": None, "spec_url": url, "current": True})
    return rows


def main():
    rows = parse_list(fetch(LIST_URL, "list.html"))
    # The source occasionally repeats a part number under the wrong series
    # (CF-N9JYCADR also appears under N8); keep the first occurrence.
    seen = set()
    rows = [r for r in rows if not (r["part"] in seen or seen.add(r["part"]))]
    rows += parse_lineup(fetch(LINEUP_URL, "lineup.html"), seen)
    (DATA / "list.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(rows)} rows, {len({r['series'] for r in rows})} series, "
          f"{sum(r['spec_url'] is not None for r in rows)} with spec links, "
          f"{sum(r['current'] for r in rows)} current")


if __name__ == "__main__":
    main()
