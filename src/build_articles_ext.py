# -*- coding: utf-8 -*-
"""1.2 — article table for the other two sources of series G, plus the day table of the Seungjeongwon Ilgi.

  python src/build_articles_ext.py goryeo     # Goryeosa 天文志 (all entries) + Goryeosa-jeolyo (astronomy entries)
  python src/build_articles_ext.py sjw        # Seungjeongwon Ilgi: astronomy articles + sjw_days (every day node)
  python src/build_articles_ext.py all

Outputs (data/derived/):
  articles_ext.parquet / .csv      same columns as articles.parquet + source, observer_site, date_flag, solar_note
  keyword_hits_ext.parquet         article_id, pattern, n_hits, context  (ASTRO_PATTERNS below)
  sjw_days.parquet / .csv          one row per day node with the weather string and the R1 judgements

Kept separate from articles.parquet on purpose: the 1.1 metric scripts read that file unfiltered, so adding rows
there would silently change the Sillok counts. Series G reads both tables and selects on `source`.

Dates. Goryeosa entries carry NIKH lunar / Julian solar / day-ganji triplets; the Julian date is used as given and
the ganji recomputed from it (date_flag = ganji_mismatch when they disagree, 1 case in 4,439). Jeolyo entries are
dated to the month; when the first clause of the text names a day ganji (e.g. 八月丙申朔) the day is restored from
the month's first day (korean_lunar_calendar, valid from 1000 CE) — date_flag = day_from_ganji. The Ilgi stays
lunar to the end (the 1896+ days add an 陽曆 note, kept in solar_note); conversion as in build_articles.solar().
"""
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_articles import HAN, HANGUL, load, solar, julian_from_jdn   # noqa: E402
from weather_tokens import judge                                        # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "derived"
GORYEOSA = RAW / "nikh-2022-goryeosa-wonmun.zip"
JEOLYO = RAW / "nikh-2023-goryeosa-jeolyo-wonmun.zip"
SJW = RAW / "nikh-2026-seungjeongwon-ilgi.zip"

# Pre-registered keyword set for series G (same spirit as extract_keywords.PATTERNS; see data/coding/astro_patterns.md)
ASTRO_PATTERNS = {
    "solar_eclipse": r"日食|日蝕",
    "lunar_eclipse": r"月食|月蝕",
    "comet": r"彗星|彗孛|星孛|孛星|客星|長星|妖星|蚩尤旗",
    "guest_star": r"客星",
    "venus_daytime": r"太白晝見|太白經天",
    "venus_any": r"太白",
    "meteor": r"流星|星隕|隕星|天狗|星流",
    "appulse": r"(?:月|太白|熒惑|歲星|鎭星|填星|辰星|五星|星)[^。,]{0,2}犯|犯[^。,]{0,4}(?:星|月|垣|宿)|(?:月|星)掩|掩(?:月|星)|凌犯|月入[^。,]{0,6}(?:星|垣|宿)",
    "sunspot": r"黑子|日中有黑|日有黑|黑氣[^。,]{0,4}日|日[^。,]{0,4}黑氣",
    "halo": r"日暈|月暈|珥",
    "aurora_cand": r"赤氣|白氣|火光|紫氣",
}
_PATS = {k: re.compile(v) for k, v in ASTRO_PATTERNS.items()}
# patterns that by themselves make an article an "astronomy article" for selection (halo/aurora/venus_any alone do not)
SELECT = {"solar_eclipse", "lunar_eclipse", "comet", "guest_star", "venus_daytime", "meteor", "appulse", "sunspot"}

STEMS, BRANCHES = "甲乙丙丁戊己庚辛壬癸", "子丑寅卯辰巳午未申酉戌亥"
HSTEMS, HBRANCHES = "갑을병정무기경신임계", "자축인묘진사오미신유술해"
GANJI60 = [STEMS[i % 10] + BRANCHES[i % 12] for i in range(60)]
GZ_RE = re.compile("[" + STEMS + "][" + BRANCHES + "]")
DAY_JUDGE_KEYS = ("clear_any", "cloudy_any", "rain_any", "snow_any", "hail_any", "fog_any", "thunder_any", "wind_any",
                  "frost_any", "precip_any", "clear_only", "mixed", "provenance_note", "astro_note")


def ganji_of_jdn(jdn):
    return GANJI60[(int(jdn) - 2451545 + 54) % 60]


def jdn_julian(y, m, d):
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - 32083


def hangul_ganji_to_hanja(s):
    s = (s or "").strip()
    if len(s) == 2 and s[0] in HSTEMS and s[1] in HBRANCHES:
        return STEMS[HSTEMS.index(s[0])] + BRANCHES[HBRANCHES.index(s[1])]
    return s


def ganji_candidates(s):
    """The Ilgi ganji field sometimes carries NIKH's own correction in brackets ('경자[경오]'); return all forms in hanja."""
    return [hangul_ganji_to_hanja(x) for x in re.findall("[" + HSTEMS + "][" + HBRANCHES + "]", s or "")]


def pick_ganji(s, jdn):
    """(ganji used, check) — the form that matches the computed day if any, else the first form; check None when undecidable."""
    c = ganji_candidates(s)
    if not c:
        return s or "", None
    if jdn is None:
        return c[0], None
    calc = ganji_of_jdn(jdn)
    return (calc, True) if calc in c else (c[0], False)


def text_of(el):
    return "".join(el.itertext()) if el is not None else ""


def hits(txt):
    out = []
    for k, p in _PATS.items():
        ms = list(p.finditer(txt))
        if ms:
            a, b = ms[0].start(), ms[0].end()
            out.append((k, len(ms), txt[max(0, a - 12):b + 12].replace("\n", " ")))
    return out


LUNAR_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})L(\d)")


def parse_lunar(s):
    m = LUNAR_RE.match(s or "")
    if not m:
        return None
    y, mo, d, lp = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4) == "1"
    if y == 9999 or mo == 99:          # NIKH placeholder for an undated entry (11 Goryeosa entries)
        return None
    return y, mo, (None if d == 99 else d), lp


def base_row(**kw):
    r = dict(article_id=None, edition=None, king_no=None, king_ko="", king_en="", edition_ko="", edition_en="", is_main=True,
             file="", level="", title="", license="KOGL-1", year_ce=None, reign_year=None, lunar_month=None, is_leap=False,
             lunar_day=None, date_system="lunar", ganji="", solar_date=None, solar_calendar=None, jdn=None,
             n_han=0, n_hangul=0, n_chars=0, n_saron=0, n_saron_han=0, n_annot=0, n_person_tags=0, n_del_han=0,
             subjects="", sago="", yeongin="", nikh_url="", source="", observer_site="", date_flag="", solar_note="")
    r.update(kw)
    return r


def title_of(lv):
    t = lv.find("./front/biblioData/title/mainTitle")
    return re.sub(r"\s+", " ", t.text or "").strip() if t is not None else ""


def dates_of(lv):
    d = {}
    for o in lv.findall("./front/biblioData/date/dateOccured"):
        d.setdefault(o.get("type"), (o.get("date") or "", (o.text or "").strip()))
    return d


# ----------------------------------------------------------------------------------------------- Goryeo
KING_VALUE = re.compile(r"^([가-힣]+)\(([^)]+)\)")


def goryeo():
    rows, khits = [], []
    # --- Goryeosa 天文志: every entry
    z = zipfile.ZipFile(GORYEOSA)
    for fn in ("kr_047.xml", "kr_048.xml", "kr_049.xml"):
        root = load(z.read(fn))
        king = ""
        for lv in root.iter():
            if not lv.tag.startswith("level"):
                continue
            m = KING_VALUE.match(lv.get("value") or "")
            if m and lv.find("text") is None:
                king = m.group(1)
            if lv.find("text") is None:
                continue
            d = dates_of(lv)
            txt = text_of(lv.find("text"))
            lun = parse_lunar(d.get("음", ("", ""))[0])
            sol = d.get("양", ("", ""))[0]
            gz = d.get("일간지", ("", ""))[1]
            gzm = GZ_RE.search(gz)
            r = base_row(article_id=lv.get("id"), edition="goryeosa_cheonmun", king_ko=king, edition_ko="고려사 천문지",
                         edition_en="Goryeosa, Treatise on Astronomy", file=fn, level=lv.tag, title=title_of(lv),
                         license="free", source="goryeosa", observer_site="gaeseong",
                         n_han=len(HAN.findall(txt)), n_hangul=len(HANGUL.findall(txt)), n_chars=len(re.sub(r"\s", "", txt)),
                         nikh_url="https://db.history.go.kr/id/" + lv.get("id"))
            if lun:
                r.update(year_ce=lun[0], lunar_month=lun[1], lunar_day=lun[2], is_leap=lun[3])
            sm = re.match(r"(\d{4})-(\d{2})-(\d{2})$", sol)
            if sm and lun and lun[2] is not None:
                y, mo, dd = map(int, sm.groups())
                j = jdn_julian(y, mo, dd)
                r.update(solar_date=sol, solar_calendar="julian", jdn=j, ganji=gzm.group(0) if gzm else gz)
                if gzm and ganji_of_jdn(j) != gzm.group(0):
                    r["date_flag"] = "ganji_mismatch"
                # independent check of korean_lunar_calendar against the NIKH Julian date (valid from 1000)
                if lun[0] >= 1000:
                    s2, c2, j2 = solar(lun[0], lun[1], lun[2], lun[3])
                    if j2 is not None and j2 != j:
                        if gzm and ganji_of_jdn(j2) == gzm.group(0):
                            # the NIKH lunar date, its day ganji and the calendar library agree; the NIKH solar date is a typo
                            # (1 case: 高宗 36 = 1249, solar given as 1246-05-14)
                            r.update(solar_date=s2, solar_calendar=c2, jdn=j2, date_flag="nikh_solar_corrected", solar_note="nikh:" + sol)
                        else:
                            r["solar_note"] = "klc:" + str(s2)
            elif lun and lun[2] is None:
                r["date_flag"] = "day_unknown"
            elif not lun:
                r["date_flag"] = "no_date"
            rows.append(r)
            for k, n, ctx in hits(txt):
                khits.append(dict(article_id=r["article_id"], pattern=k, n_hits=n, context=ctx))
    n1 = len(rows)
    # --- Jeolyo: astronomy entries only
    z = zipfile.ZipFile(JEOLYO)
    for fn in sorted(n for n in z.namelist() if n.endswith(".xml")):
        root = load(z.read(fn))
        king = ""
        for lv in root.iter():
            if not lv.tag.startswith("level"):
                continue
            m = KING_VALUE.match(lv.get("value") or "")
            if m:
                king = m.group(1)
            tx = lv.find("text")
            if tx is None:
                continue
            txt = text_of(tx)
            h = hits(txt)
            if not any(k in SELECT for k, _, _ in h):
                continue
            d = dates_of(lv)
            lun = parse_lunar(d.get("음", ("", ""))[0])
            r = base_row(article_id=lv.get("id"), edition="goryeosa_jeolyo", king_ko=king, edition_ko="고려사절요", edition_en="Goryeosa jeolyo",
                         file=fn, level=lv.tag, title=title_of(lv), license="KOGL-1", source="goryeosa_jeolyo", observer_site="gaeseong",
                         n_han=len(HAN.findall(txt)), n_hangul=len(HANGUL.findall(txt)), n_chars=len(re.sub(r"\s", "", txt)),
                         nikh_url="https://db.history.go.kr/id/" + lv.get("id"))
            if lun:
                r.update(year_ce=lun[0], lunar_month=lun[1], lunar_day=lun[2], is_leap=lun[3])
                if lun[2] is None:
                    # first clause may name the day ganji: "○八月丙申朔. 日食." / "○乙未, 太白晝見."
                    first = re.split(r"[.。,]", txt.strip().lstrip("○ "), maxsplit=1)[0]
                    gm = GZ_RE.search(first[:14])
                    restored = False
                    if gm and lun[0] >= 1000:
                        s1, c1, j1 = solar(lun[0], lun[1], 1, lun[3])
                        if j1 is not None:
                            off = (GANJI60.index(gm.group(0)) - GANJI60.index(ganji_of_jdn(j1))) % 60
                            if off < 30:
                                j = j1 + off
                                y, mo, dd = julian_from_jdn(j)
                                r.update(lunar_day=off + 1, ganji=gm.group(0), jdn=j, solar_date=f"{y:04d}-{mo:02d}-{dd:02d}",
                                         solar_calendar="julian", date_flag="day_from_ganji")
                                restored = True
                    if not restored:
                        r["date_flag"] = "day_unknown"
                else:
                    s1, c1, j1 = solar(lun[0], lun[1], lun[2], lun[3]) if lun[0] >= 1000 else (None, None, None)
                    if j1:
                        r.update(solar_date=s1, solar_calendar=c1, jdn=j1, ganji=ganji_of_jdn(j1))
                    else:
                        r["date_flag"] = "before_1000"
            else:
                r["date_flag"] = "no_date"
            rows.append(r)
            for k, n, ctx in h:
                khits.append(dict(article_id=r["article_id"], pattern=k, n_hits=n, context=ctx))
    print("goryeosa cheonmun", n1, "jeolyo astro", len(rows) - n1)
    return rows, khits


# ----------------------------------------------------------------------------------------------- Seungjeongwon Ilgi
SJW_KINGS = {"A": (16, "인조", "Injo"), "B": (17, "효종", "Hyojong"), "C": (18, "현종", "Hyeonjong"), "D": (19, "숙종", "Sukjong"),
             "E": (20, "경종", "Gyeongjong"), "F": (21, "영조", "Yeongjo"), "G": (22, "정조", "Jeongjo"), "H": (23, "순조", "Sunjo"),
             "I": (24, "헌종", "Heonjong"), "J": (25, "철종", "Cheoljong"), "K": (26, "고종", "Gojong"), "L": (27, "순종", "Sunjong")}


def sjw():
    rows, khits, days = [], [], []
    z = zipfile.ZipFile(SJW)
    files = sorted(n for n in z.namelist() if n.endswith(".xml"))
    for fn in files:
        letter = re.search(r"2nd_([A-L])\d\d", fn).group(1)
        kno, kko, ken = SJW_KINGS[letter]
        root = load(z.read(fn))
        for day in root.iter("level4"):
            if day.get("type") != "일":
                continue
            d = {k: (v[0] or v[1]) for k, v in dates_of(day).items()}
            lun = parse_lunar(d.get("서기", ""))
            w = day.find("./front/description/weather")
            wtxt = (w.text or "").strip() if w is not None else None
            sol = cal = j = None
            if lun and lun[2] is not None:
                sol, cal, j = solar(lun[0], lun[1], lun[2], lun[3])
            gz, gz_ok = pick_ganji(d.get("간지", ""), j)
            arts = [a for a in day.findall("level5") if a.get("type") == "기사"]
            jd = judge(wtxt) if wtxt is not None else None
            row = dict(day_id=day.get("id"), book=letter, king_no=kno, king_ko=kko, king_en=ken,
                       year_ce=lun[0] if lun else None, lunar_month=lun[1] if lun else None, lunar_day=lun[2] if lun else None,
                       is_leap=lun[3] if lun else False, ganji=gz, solar_date=sol, solar_calendar=cal, jdn=j, solar_note=d.get("양력", ""),
                       weather=wtxt, has_weather=wtxt is not None, n_articles=len(arts), kind=jd["kind"] if jd else None,
                       ganji_raw=d.get("간지", ""), ganji_check=gz_ok)
            for k in DAY_JUDGE_KEYS:
                row[k] = jd[k] if jd else None
            days.append(row)
            for a in arts:
                txt = text_of(a.find("text"))
                h = hits(txt)
                if not any(k in SELECT for k, _, _ in h):
                    continue
                r = base_row(article_id=a.get("id"), edition="sjw", king_no=kno, king_ko=kko, king_en=ken, edition_ko="승정원일기",
                             edition_en="Seungjeongwon Ilgi", file=fn, level="level5", title=title_of(a), license="KOGL-1", source="sjw",
                             observer_site="seoul", year_ce=lun[0] if lun else None, lunar_month=lun[1] if lun else None,
                             lunar_day=lun[2] if lun else None, is_leap=lun[3] if lun else False, ganji=gz, solar_date=sol,
                             solar_calendar=cal, jdn=j, solar_note=d.get("양력", ""),
                             n_han=len(HAN.findall(txt)), n_hangul=len(HANGUL.findall(txt)), n_chars=len(re.sub(r"\s", "", txt)),
                             n_person_tags=sum(1 for ix in a.iter("index") if ix.get("type") == "이름"),
                             nikh_url="https://sjw.history.go.kr/id/" + a.get("id"))
                if not lun or lun[2] is None:
                    r["date_flag"] = "day_unknown"
                rows.append(r)
                for k, n, ctx in h:
                    khits.append(dict(article_id=r["article_id"], pattern=k, n_hits=n, context=ctx))
        print(fn, "days", len(days), "astro articles", len(rows), flush=True)
    return rows, khits, days


def flag_days(dd):
    """Post-pass over sjw_days: where the day ganji disagrees with the ganji of the converted date, measure the offset.
    A whole lunar month shifted by ±1 day is the contemporaneous calendar (時憲曆) starting the month a day earlier or
    later than the modern table behind korean_lunar_calendar (Lee, Ahn & Mihn 2012 list such days); isolated cases are
    copyist/NIKH typos. solar_date_ganji follows the ganji for the month-shift days and equals solar_date otherwise —
    series G uses solar_date_ganji, and the method page shows both."""
    import numpy as np
    dd = dd.copy()
    off = []
    for g, j, ok in zip(dd.ganji, dd.jdn, dd.ganji_check):
        if ok is False and isinstance(g, str) and g in GANJI60 and j == j and j is not None:
            o = (GANJI60.index(g) - GANJI60.index(ganji_of_jdn(int(j)))) % 60
            off.append(o - 60 if o > 30 else o)
        else:
            off.append(0)
    dd["ganji_offset"] = off
    ym = dd.year_ce.astype("Int64").astype(str) + "-" + dd.lunar_month.astype("Int64").astype(str) + dd.is_leap.map({True: "L", False: ""})
    dd["date_flag"] = ""
    for key, grp in dd[dd.ganji_offset != 0].groupby(ym[dd.ganji_offset != 0]):
        n_month = int((ym == key).sum())
        if len(grp) >= max(3, n_month - 2) and grp.ganji_offset.abs().max() == 1 and grp.ganji_offset.nunique() == 1:
            dd.loc[grp.index, "date_flag"] = "ganji_month_shift"
        else:
            dd.loc[grp.index, "date_flag"] = "ganji_typo"
    shift = dd.date_flag == "ganji_month_shift"
    dd["jdn_ganji"] = dd.jdn
    dd.loc[shift, "jdn_ganji"] = dd.loc[shift, "jdn"] + dd.loc[shift, "ganji_offset"]
    def iso(j):
        if j != j or j is None:
            return None
        j = int(j)
        if j < GREG_SWITCH_JDN:
            y, m, d = julian_from_jdn(j)
            return f"{y:04d}-{m:02d}-{d:02d}"
        import datetime as _dt
        return _dt.date.fromordinal(j - 1721425).isoformat()
    dd["solar_date_ganji"] = dd.jdn_ganji.map(iso)
    return dd


GREG_SWITCH_JDN = 2299161


def write(rows, khits, days=None, merge=True):
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    kh = pd.DataFrame(khits)
    pa, pk = OUT / "articles_ext.parquet", OUT / "keyword_hits_ext.parquet"
    if merge and pa.exists():
        old = pd.read_parquet(pa)
        old = old[~old.source.isin(df.source.unique())]
        df = pd.concat([old, df], ignore_index=True)
        oldk = pd.read_parquet(pk)
        kh = pd.concat([oldk, kh], ignore_index=True)
        kh = kh[kh.article_id.isin(df.article_id)].drop_duplicates(["article_id", "pattern"], keep="last")
    df.to_parquet(pa, index=False)
    df.to_csv(OUT / "articles_ext.csv", index=False, encoding="utf-8")
    kh.to_parquet(pk, index=False)
    print("articles_ext", len(df), df.groupby("source").size().to_dict(), "hits", len(kh))
    print("date_flag", df.groupby(["source", "date_flag"]).size().to_dict())
    if days is not None:
        dd = flag_days(pd.DataFrame(days))
        print("sjw_days date_flag", dd.date_flag.value_counts().to_dict())
        dd.to_parquet(OUT / "sjw_days.parquet", index=False)
        dd.to_csv(OUT / "sjw_days.csv", index=False, encoding="utf-8")
        print("sjw_days", len(dd), "weather", int(dd.has_weather.sum()), "ganji_check false", int((dd.ganji_check == False).sum()))  # noqa: E712


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("goryeo", "all"):
        r, k = goryeo()
        write(r, k)
    if what in ("sjw", "all"):
        r, k, d = sjw()
        write(r, k, d)
