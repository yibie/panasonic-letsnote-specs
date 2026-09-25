"""Fetch the official spec page of every part number into data/specs.json.

Spec pages live at https://panasonic.jp/pc/p-db/<part>_spec.html. The list
only links pages for recent models, but older ones often exist too, so every
CF- part number is tried; missing pages are simply skipped.
Output: {part: [[group, item, value], ...]} in page order.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor

from common import DATA, fetch, text

SPEC_URL = "https://panasonic.jp/pc/p-db/{}_spec.html"


def parse_spec(page):
    table = re.search(r'<table class="c-prd007__table">(.*?)</table>', page, re.S)
    if not table:
        return []
    rows, group, group_left = [], "", 0
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table.group(1), re.S):
        ths = re.findall(r"<th([^>]*)>(.*?)</th>", tr, re.S)
        td = re.search(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if not td:
            continue
        item = ""
        for attrs, body in ths:
            if 'scope="rowgroup"' in attrs:
                span = re.search(r'rowspan="(\d+)', attrs)
                group, group_left = text(body), int(span.group(1)) if span else 1
            else:
                item = text(body)
        g = group if group_left > 0 else ""
        rows.append([g, item or g, text(td.group(1))])
        group_left -= 1
    return rows


def main():
    parts = json.loads((DATA / "list.json").read_text())
    todo = [p["part"] for p in parts if p["part"].startswith("CF-")]

    def one(part):
        page = fetch(SPEC_URL.format(part), f"spec-{part}.html")
        return part, parse_spec(page) if page else []

    specs = {}
    with ThreadPoolExecutor(max_workers=3) as pool:  # stay gentle on panasonic.jp
        for i, (part, rows) in enumerate(pool.map(one, todo), 1):
            if rows:
                specs[part] = rows
            if i % 50 == 0:
                print(f"{i}/{len(todo)} fetched, {len(specs)} with specs", flush=True)
    (DATA / "specs.json").write_text(json.dumps(specs, ensure_ascii=False, indent=1) + "\n")
    print(f"done: {len(specs)}/{len(todo)} parts have spec pages")


if __name__ == "__main__":
    main()
