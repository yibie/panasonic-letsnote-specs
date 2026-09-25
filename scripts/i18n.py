"""Page text for each language. Spec values stay as quoted from Panasonic."""
import re

LANGS = ("en", "ja", "zh")
LANG_NAMES = {"en": "English", "ja": "日本語", "zh": "中文"}

STRINGS = {
    "en": {
        "title": "Panasonic Let's note {model} Specifications",
        "intro": "**{model}** is a Panasonic Let's note laptop{series}{screen}. "
                 "This page lists all {n} part numbers{released}.",
        "series": " in the {series} series",
        "screen": " with a {screen}",
        "released": ", released {span}",
        "has_sheets": " Each part number links to its official spec sheet.",
        "parts": "Part numbers",
        "part": "Part number", "rel": "Released", "disc": "Discontinued", "summary": "Summary",
        "on_sale": "On sale",
        "specs_one": "Specifications",
        "specs_common": "Common specifications",
        "item": "Item", "value": "Value",
        "diff": "Differences by part number",
        "cpu": "CPU", "mem": "Memory", "storage": "Storage", "weight": "Weight", "battery": "Battery life",
        "full_diff": "{part}: all differing specifications",
        "sheet": "Official spec sheet",
        "no_sheet": "Panasonic no longer publishes a detailed spec sheet for this model; "
                    "the summaries above come from the official discontinued-models list.",
        "photos": "Photos",
        "related": "Related models",
        "newer": "Newer model in the series", "older": "Older model in the series",
        "all": "All Let's note models",
        "source": "Source: Panasonic's official [discontinued-models list]({list}) and spec sheets "
                  "(panasonic.jp), translated from Japanese; see the official sheets for the authoritative wording. Product images © Panasonic. "
                  "This is an unofficial compilation, not affiliated with Panasonic.",
        "alt": "Panasonic Let's note {model} {size} laptop{color}{year}",
        "alt_part": ", part number {part}",
        "caption": "Panasonic Let's note {model}{parts_note}{color_note}. Image © Panasonic.",
        "caption_parts": " ({parts})",
        "img_title": "Panasonic Let's note {model} specifications",
        "index_title": "Panasonic Let's note Specifications Database",
        "index_intro": "Specifications of every Panasonic Let's note model since 1996: {models} models and "
                       "{parts} part numbers. Each model has its own page with all part numbers, release and "
                       "discontinuation dates, photos and the full official spec sheet.",
        "index_series": "Series", "index_models": "Models (newest first)",
    },
    "ja": {
        "title": "レッツノート {model} スペック・仕様一覧",
        "intro": "パナソニック レッツノート **{model}**{series}{screen}の全{n}品番{released}のスペック・仕様をまとめたページです。",
        "series": "（{series}シリーズ",
        "screen": "・{screen}）",
        "released": "（{span}発売）",
        "has_sheets": "各品番の公式仕様表へのリンクも掲載しています。",
        "parts": "品番一覧",
        "part": "品番", "rel": "発売", "disc": "生産終了", "summary": "主な仕様",
        "on_sale": "発売中",
        "specs_one": "仕様",
        "specs_common": "共通仕様",
        "item": "項目", "value": "仕様",
        "diff": "品番別の違い",
        "cpu": "CPU", "mem": "メモリー", "storage": "ストレージ", "weight": "質量", "battery": "駆動時間",
        "full_diff": "{part} の仕様の違い（すべて）",
        "sheet": "公式仕様表",
        "no_sheet": "この機種の詳細な仕様表はパナソニック公式サイトで公開されていません。上記は公式の生産終了品一覧に基づく情報です。",
        "photos": "写真",
        "related": "関連機種",
        "newer": "同シリーズの後継機種", "older": "同シリーズの前機種",
        "all": "レッツノート全機種一覧",
        "source": "出典：パナソニック公式[生産終了品一覧]({list})および各品番の仕様表（panasonic.jp）。"
                  "製品画像 © Panasonic。本ページは非公式のまとめであり、パナソニックとは関係ありません。",
        "alt": "パナソニック レッツノート {model}（{size}ノートパソコン{color}{year}）",
        "alt_part": "、品番 {part}",
        "caption": "レッツノート {model}{parts_note}{color_note}。画像 © Panasonic",
        "caption_parts": "（{parts}）",
        "img_title": "レッツノート {model} スペック",
        "index_title": "レッツノート 歴代全機種 スペック一覧",
        "index_intro": "1996年以降のパナソニック レッツノート全{models}機種・{parts}品番のスペックを機種ごとにまとめています。"
                       "各機種のページに品番一覧、発売日・生産終了日、写真、公式仕様表を掲載しています。",
        "index_series": "シリーズ", "index_models": "機種（新しい順）",
    },
    "zh": {
        "title": "松下 Let's note {model} 规格参数",
        "intro": "**{model}** 是松下 Let's note 笔记本电脑{series}{screen}。本页收录其全部 {n} 个型号{released}的规格参数。",
        "series": "，属于 {series} 系列",
        "screen": "，配备 {screen}",
        "released": "（{span} 发售）",
        "has_sheets": "每个型号均附官方规格表链接。",
        "parts": "型号列表",
        "part": "型号（品番）", "rel": "发售", "disc": "停产", "summary": "主要规格",
        "on_sale": "在售",
        "specs_one": "规格",
        "specs_common": "通用规格",
        "item": "项目", "value": "规格",
        "diff": "各型号差异",
        "cpu": "处理器", "mem": "内存", "storage": "存储", "weight": "重量", "battery": "续航",
        "full_diff": "{part} 的全部差异规格",
        "sheet": "官方规格表",
        "no_sheet": "松下官网已不再提供该机型的详细规格表，以上信息来自官方停产产品列表。",
        "photos": "图片",
        "related": "相关机型",
        "newer": "同系列新一代", "older": "同系列上一代",
        "all": "Let's note 全部机型",
        "source": "来源：松下官方[停产产品列表]({list})及各型号规格表（panasonic.jp），由日文翻译，准确措辞以官方规格表为准。"
                  "产品图片 © Panasonic。本页为非官方整理，与松下公司无关。",
        "alt": "松下 Let's note {model} {size}笔记本电脑{color}{year}",
        "alt_part": "，型号 {part}",
        "caption": "松下 Let's note {model}{parts_note}{color_note}。图片 © Panasonic",
        "caption_parts": "（{parts}）",
        "img_title": "松下 Let's note {model} 规格参数",
        "index_title": "松下 Let's note 历代机型规格数据库",
        "index_intro": "收录 1996 年以来松下 Let's note 全部 {models} 个机型、{parts} 个型号的规格。"
                       "每个机型一页，包含型号列表、发售与停产日期、图片和完整的官方规格表。",
        "index_series": "系列", "index_models": "机型（从新到旧）",
    },
}

COLORS = {
    "シルバー": ("silver", "银色"), "ブラック": ("black", "黑色"), "カームグレイ": ("calm gray", "灰色"),
    "ブラック＆シルバー": ("black & silver", "黑银"), "ブラック&シルバー": ("black & silver", "黑银"),
    "シルバー&ブラック": ("silver & black", "银黑"), "ブルー&カッパー": ("blue & copper", "蓝铜"),
    "ブルー＆カッパー": ("blue & copper", "蓝铜"), "ウォームゴールド＆カッパー": ("warm gold & copper", "暖金铜"),
    "ブラック＆カームグレイ": ("black & calm gray", "黑灰"), "ゴールド&シルバー": ("gold & silver", "金银"),
    "シルバーｘブルー": ("silver & blue", "银蓝"),
}


def color(value, lang):
    if not value:
        return ""
    if lang == "ja":
        return value
    pair = COLORS.get(value)
    return pair[0 if lang == "en" else 1] if pair else ""


def screen(value, lang):
    """'12.1型WUXGA液晶・光学式ドライブ内蔵' -> '12.1-inch WUXGA display' / '12.1英寸 WUXGA 屏幕'."""
    if not value or lang == "ja":
        return value or ""
    s = value.split("・")[0]
    s = re.sub(r"(\d+(?:\.\d+)?)型\s*", r"\1<in> ", s).replace("液晶", "").strip()
    s = s.replace("<in>", "-inch" if lang == "en" else "英寸")
    return f"{s} display" if lang == "en" else f"{s} 屏幕"


def size(value, lang):
    """Screen size only, for alt text: '12.1-inch' / '12.1型' / '12.1英寸'."""
    m = re.search(r"(\d+(?:\.\d+)?)型", value or "")
    if not m:
        return ""
    return {"en": f"{m.group(1)}-inch", "ja": f"{m.group(1)}型", "zh": f"{m.group(1)} 英寸"}[lang]
