# -*- coding: utf-8 -*-
"""Pre-registered token dictionary and day-level rules for the Seungjeongwon Ilgi weather cell (series F).

Registered 2026-11-02 before any series-F number was computed (data/coding/weather_tokens.md is the human-readable
copy). The rules are frozen: a string that does not decompose into known tokens is reported as a residual and the
build check requires residual == 0 over the full inventory of distinct strings, but the rules are not tuned to
match any external dataset.

    tokens(s)  -> list of (token, class)
    judge(s)   -> dict of day-level booleans (rain_any, snow_any, ... ) plus 'kind'
"""
import re

# ---- phenomenon tokens (class -> surface forms; longest surface form wins) --------------------------------------
PHENOMENA = {
    "clear":   ["晴", "淸", "睛", "陽", "霽", "爽", "明", "照"],        # 淸·睛 are copyist variants of 晴 in the cell
    "cloudy":  ["陰", "隂", "雲", "曇", "蔭", "密雲", "暗", "晦"],
    "rain":    ["雨", "灑雨", "洒雨", "灑", "洒", "霡霂", "霧雨", "霏", "注", "雨水"],   # bare 灑/洒 = a sprinkle of rain (或灑或雨)
    "snow":    ["雪", "霰", "宿雪", "灑雪", "洒雪"],
    "hail":    ["雹"],
    "fog":     ["霧", "霧氣", "沈霧", "蒙", "塵", "霾"],
    "thunder": ["雷", "電", "雷電", "雷震", "雷動", "震"],
    "wind":    ["風", "大吹", "吹"],
    "frost":   ["霜"],
    "optical": ["暈", "日暈", "月暈", "珥", "兩珥", "虹", "氣如火光", "火光", "白氣", "赤氣", "有氣"],
    "astro":   ["日食", "月食", "太白", "歲星", "金星", "星", "犯", "見於", "流星", "太微", "太薇", "月入"],
}
# ---- modifiers (do not change the phenomenon; kept so that every character is accounted for) ---------------------
TIME = ["朝", "晝", "午", "夕", "暮", "夜", "晩", "晚", "曉", "晨", "晡", "昏", "初昏", "平明", "昧爽", "終日", "終夜", "達夜", "達曙",
        "午前", "午後", "午后", "前", "後", "后", "終", "曙", "早", "朝後", "夕後", "日", "時", "更", "刻", "初", "末", "半",
        "子", "丑", "寅", "卯", "辰", "巳", "未", "申", "酉", "戌", "亥", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
        "自", "至", "向", "今", "晦日", "罷漏", "漏", "晏"]
ALTERN = ["或", "乍", "且", "又", "旋", "仍", "復", "乃", "卽", "暫", "而", "與", "相", "及", "皆", "只", "不", "無", "始", "止", "下", "出", "入", "落", "動", "飛", "交下", "交", "多", "延", "許", "尺", "長", "尾", "餘"]
DEGREE = ["大", "小", "微", "細", "少", "深", "重", "密", "驟", "甚", "沈", "涼", "寒", "暖", "如", "狀", "豆", "拳", "鉢", "榛", "色"]
DIRECTION = ["東", "西", "南", "北", "東南", "西南", "東北", "西北", "南東", "方", "地", "際", "天", "左", "右", "上", "內", "外", "巽", "艮", "坤", "乾", "極", "垣", "井", "鬼", "氐", "房", "角", "畢", "軒轅", "牛", "宿", "木", "金", "水", "火", "土", "于", "於", "以"]
# ---- provenance notes: the cell carries a copyist's note instead of (or beside) weather -------------------------
PROVENANCE = ["燼餘", "謄書", "謄錄", "朝報", "缺落", "缺", "朽缺", "日記", "內日記", "記", "報", "書", "錄", "以下", "第", "歲", "年", "月", "元", "敬", "王", "忌", "齋戒", "戒", "車", "輿", "坐", "直", "測器", "測", "器", "分", "情", "黃", "靑", "赤", "白", "平", "兩", "重", "廻", "迴", "有", "見", "光", "氣"]
BLANK = ["-"]
PUNCT = set(" ,。、·〈〉[]()○◆")

_FORMS = []
for cls, forms in PHENOMENA.items():
    _FORMS += [(f, cls) for f in forms]
_FORMS += [(f, "time") for f in TIME] + [(f, "altern") for f in ALTERN] + [(f, "degree") for f in DEGREE] \
        + [(f, "direction") for f in DIRECTION] + [(f, "provenance") for f in PROVENANCE] + [(f, "blank") for f in BLANK]
_FORMS.sort(key=lambda x: -len(x[0]))
_TABLE = {}
for f, c in _FORMS:
    _TABLE.setdefault(f, c)      # first (longest list order already) — phenomena are listed before modifiers


def tokens(s):
    """Greedy longest-match decomposition. Unknown characters come back as ('x', 'residual')."""
    out, i = [], 0
    s = s.strip()
    while i < len(s):
        ch = s[i]
        if ch in PUNCT:
            i += 1
            continue
        for L in (4, 3, 2, 1):
            seg = s[i:i + L]
            if seg in _TABLE:
                out.append((seg, _TABLE[seg]))
                i += L
                break
        else:
            out.append((ch, "residual"))
            i += 1
    return out


PHEN = set(PHENOMENA)


def judge(s):
    """Day-level judgement from the token classes (pre-registered rule set R1).

    kind:  blank      the cell is '-' or empty
           note_only  only provenance / astronomical / optical tokens, no weather phenomenon -> treated as missing
           weather    at least one of clear/cloudy/rain/snow/hail/fog/thunder/wind/frost
    *_any: that phenomenon appears anywhere in the string (time of day ignored; 或/乍 count as present).
    clear_only: the only phenomenon classes present are 'clear' (and modifiers).
    precip_any: rain or snow or hail.
    """
    tk = tokens(s)
    cls = {c for _, c in tk}
    weather_cls = cls & {"clear", "cloudy", "rain", "snow", "hail", "fog", "thunder", "wind", "frost"}
    if not s.strip() or cls <= {"blank"}:
        kind = "blank"
    elif not weather_cls:
        kind = "note_only"
    else:
        kind = "weather"
    r = {"kind": kind, "residual": [t for t, c in tk if c == "residual"]}
    for c in ("clear", "cloudy", "rain", "snow", "hail", "fog", "thunder", "wind", "frost"):
        r[c + "_any"] = c in cls
    r["precip_any"] = bool(cls & {"rain", "snow", "hail"})
    r["clear_only"] = weather_cls == {"clear"}
    r["mixed"] = len(weather_cls - {"wind", "fog", "thunder", "frost"}) >= 2 or ("altern" in cls and kind == "weather")
    r["provenance_note"] = "provenance" in cls
    r["astro_note"] = bool(cls & {"astro", "optical"})
    return r


if __name__ == "__main__":
    import sys, json, io, collections
    sys.stdout.reconfigure(encoding="utf-8")
    inv = json.load(io.open(sys.argv[1], encoding="utf-8"))     # [[string, count], ...]
    resid = collections.Counter(); kinds = collections.Counter(); flags = collections.Counter()
    bad = []
    for s, n in inv:
        j = judge(s)
        kinds[j["kind"]] += n
        for k, v in j.items():
            if k.endswith("_any") or k in ("clear_only", "mixed", "provenance_note", "astro_note"):
                if v: flags[k] += n
        if j["residual"]:
            bad.append((s, n, j["residual"]))
            for t in j["residual"]: resid[t] += n
    print("strings", len(inv), "days", sum(n for _, n in inv))
    print("kinds", dict(kinds)); print("flags", dict(flags))
    print("residual strings", len(bad), "residual chars", dict(resid))
    for b in bad[:60]: print("  ", b)
