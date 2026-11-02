# -*- coding: utf-8 -*-
"""Build the article-level table of the Veritable Records (Taejo–Cheoljong) from the NIKH XML.

  python src/build_articles.py            # reads data/raw/nikh-2026-joseon-sillok-wonmun.zip
                                          # writes data/derived/articles.parquet + articles.csv

One row per article (biblioData type="T"). Nothing from the article text is stored except
counts; the text itself stays in the raw XML. Dates are the NIKH lunar dates (year CE, lunar
month/day, leap flag); the solar conversion (proleptic Gregorian → Julian Day → Julian calendar
before 1582-10-15) comes from korean_lunar_calendar and is validated separately
(src/check_calendar.py).

Known source quirks handled here (same fixes as the vault converter, 2026-09-26):
  * supplementary CJK written as two surrogate numeric references (&#55381;&#56892;)
  * double-escaped references (&amp;#x26E02;) in 516 files
  * bare CJK tags such as <斯干/> (book titles) in Sejong
"""
import datetime as dt
import re
import sys
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd
from korean_lunar_calendar import KoreanLunarCalendar

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "nikh-2026-joseon-sillok-wonmun.zip"
RAW4 = ROOT / "data" / "raw" / "nikh-2026-joseon-sillok-gojong-sunjong.zip"   # KOGL Type 4 (no derivatives): counts only, no title/text
KOGL4 = {"wza", "wzb", "wzc"}
OUT = ROOT / "data" / "derived"

# edition code -> (king number, Korean name, romanized name, edition label ko/en, is_main)
EDITIONS = {
    "waa": (1, "태조", "Taejo", "태조실록", "Veritable Records of King Taejo", True),
    "wba": (2, "정종", "Jeongjong", "정종실록", "Veritable Records of King Jeongjong", True),
    "wca": (3, "태종", "Taejong", "태종실록", "Veritable Records of King Taejong", True),
    "wda": (4, "세종", "Sejong", "세종실록", "Veritable Records of King Sejong", True),
    "wea": (5, "문종", "Munjong", "문종실록", "Veritable Records of King Munjong", True),
    "wfa": (6, "단종", "Danjong", "단종실록", "Veritable Records of King Danjong", True),
    "wga": (7, "세조", "Sejo", "세조실록", "Veritable Records of King Sejo", True),
    "wha": (8, "예종", "Yejong", "예종실록", "Veritable Records of King Yejong", True),
    "wia": (9, "성종", "Seongjong", "성종실록", "Veritable Records of King Seongjong", True),
    "wja": (10, "연산군", "Yeonsangun", "연산군일기", "Daily Records of Yeonsangun", True),
    "wka": (11, "중종", "Jungjong", "중종실록", "Veritable Records of King Jungjong", True),
    "wla": (12, "인종", "Injong", "인종실록", "Veritable Records of King Injong", True),
    "wma": (13, "명종", "Myeongjong", "명종실록", "Veritable Records of King Myeongjong", True),
    "wna": (14, "선조", "Seonjo", "선조실록", "Veritable Records of King Seonjo", True),
    "wnb": (14, "선조", "Seonjo", "선조수정실록", "Revised Veritable Records of King Seonjo", False),
    "woa": (15, "광해군", "Gwanghaegun", "광해군일기 중초본", "Daily Records of Gwanghaegun, second draft", False),
    "wob": (15, "광해군", "Gwanghaegun", "광해군일기 정초본", "Daily Records of Gwanghaegun, final draft", True),
    "wpa": (16, "인조", "Injo", "인조실록", "Veritable Records of King Injo", True),
    "wqa": (17, "효종", "Hyojong", "효종실록", "Veritable Records of King Hyojong", True),
    "wra": (18, "현종", "Hyeonjong", "현종실록", "Veritable Records of King Hyeonjong", True),
    "wrb": (18, "현종", "Hyeonjong", "현종개수실록", "Supplemented Veritable Records of King Hyeonjong", False),
    "wsa": (19, "숙종", "Sukjong", "숙종실록", "Veritable Records of King Sukjong", True),
    "wsb": (19, "숙종", "Sukjong", "숙종실록보궐정오", "Supplement and Corrections to the Veritable Records of King Sukjong", False),
    "wta": (20, "경종", "Gyeongjong", "경종실록", "Veritable Records of King Gyeongjong", True),
    "wtb": (20, "경종", "Gyeongjong", "경종수정실록", "Revised Veritable Records of King Gyeongjong", False),
    "wua": (21, "영조", "Yeongjo", "영조실록", "Veritable Records of King Yeongjo", True),
    "wva": (22, "정조", "Jeongjo", "정조실록", "Veritable Records of King Jeongjo", True),
    "wwa": (23, "순조", "Sunjo", "순조실록", "Veritable Records of King Sunjo", True),
    "wxa": (24, "헌종", "Heonjong", "헌종실록", "Veritable Records of King Heonjong", True),
    "wya": (25, "철종", "Cheoljong", "철종실록", "Veritable Records of King Cheoljong", True),
    "wza": (26, "고종", "Gojong", "고종실록", "Veritable Records of King Gojong", True),
    "wzb": (27, "순종", "Sunjong", "순종실록", "Veritable Records of King Sunjong", True),
    "wzc": (27, "순종", "Sunjong", "순종실록부록", "Veritable Records of King Sunjong, appendix", False),
}

_SUR = re.compile(r"&#(\d+);&#(\d+);")
_STRAY_TAG = re.compile(r"<([一-鿿㐀-䶿]+)\s*/>")
HAN = re.compile(r"[㐀-䶿一-鿿豈-﫿\U00020000-\U0003134F]")
HANGUL = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})L(\d)")
GREG_SWITCH = dt.date(1582, 10, 15)


def load(b: bytes) -> ET.Element:
    s = b.decode("utf-8")

    def pair(m):
        hi, lo = int(m.group(1)), int(m.group(2))
        if 0xD800 <= hi <= 0xDBFF and 0xDC00 <= lo <= 0xDFFF:
            return chr(0x10000 + ((hi - 0xD800) << 10) + (lo - 0xDC00))
        return m.group(0)

    s = _SUR.sub(pair, s)
    s = re.sub(r"&amp;(#x[0-9A-Fa-f]+|#\d+);", r"&\1;", s)
    s = _STRAY_TAG.sub(lambda m: "〈" + m.group(1) + "〉", s)
    s = re.sub(r"<!DOCTYPE[^>]*>", "", s)
    return ET.fromstring(s)


def jdn_from_gregorian(d: dt.date) -> int:
    return d.toordinal() + 1721425


def julian_from_jdn(jdn: int) -> dt.date:
    c = jdn + 32082
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = d - 4800 + m // 10
    return year, month, day   # Julian-calendar date; not a datetime.date (Feb 29 in 1500 is valid in the Julian calendar)


def solar(year: int, month: int, day: int, leap: bool):
    """-> (civil solar date string, calendar, JDN) or (None, None, None)."""
    cal = KoreanLunarCalendar()
    if not cal.setLunarDate(year, month, day, leap):
        return None, None, None
    g = dt.date.fromisoformat(cal.SolarIsoFormat())   # proleptic Gregorian
    jdn = jdn_from_gregorian(g)
    if g < GREG_SWITCH:
        y, mo, d = julian_from_jdn(jdn)
        return f"{y:04d}-{mo:02d}-{d:02d}", "julian", jdn
    return g.isoformat(), "gregorian", jdn


def text_of(el) -> str:
    return "".join(el.itertext()) if el is not None else ""


def main():
    rows = []
    residual = 0
    for zpath in (RAW, RAW4):
      z = zipfile.ZipFile(zpath)
      files = sorted(n for n in z.namelist() if n.endswith(".xml"))
      for fn in files:
          m = re.search(r"2nd_(w[a-z]{2})_(\d{3})\.xml$", fn)
          if not m:
              continue
          ed, nnn = m.group(1), m.group(2)
          if ed not in EDITIONS:
              continue
          root = load(z.read(fn))
          cur = {}
          for lv in root.iter():
              if not lv.tag.startswith("level"):
                  continue
              b = lv.find("front/biblioData")
              if b is None:
                  continue
              kind = b.get("type")
              dates = {}
              for o in b.iter("dateOccured"):
                  dates[o.get("type")] = o.get("date") or (o.text or "").strip()
              if kind == "L" and dates.get("간지"):
                  cur = dates
                  continue
              if kind != "T":
                  continue
              aid = lv.get("id")
              t = b.find("title/mainTitle")
              title = re.sub(r"\s+", " ", (t.text or "")).strip() if t is not None else ""
              ymd = dates.get("서기") or cur.get("서기") or ""
              dm = DATE_RE.match(ymd)
              tx = lv.find("text")
              txt = text_of(tx)
              if "&#" in txt:
                  residual += 1
              sago = yeongin = ""
              for s in b.findall("source"):
                  mt, pg = s.find("mainTitle"), s.find("page")
                  lab = f"{(mt.text or '').strip()} {pg.get('begin') if pg is not None else ''}".strip()
                  if mt.get("type") == "태백산사고본":
                      sago = lab
                  elif mt.get("type") == "국편영인본":
                      yeongin = lab
              subjects = ";".join((x.text or "").strip() for x in b.findall("subjectClass"))
              n_saron = len(tx.findall(".//postScript")) if tx is not None else 0
              saron_txt = "".join(text_of(p) for p in tx.findall(".//postScript")) if tx is not None else ""
              n_annot = len(tx.findall(".//annotation")) if tx is not None else 0
              n_person = sum(1 for ix in tx.iter("index") if ix.get("ref")) if tx is not None else 0
              n_del = 0
              if ed == "woa" and tx is not None:
                  for p in tx.iter("proofreading"):
                      if "산삭" in (p.get("type") or ""):
                          n_del += len(HAN.findall(text_of(p)))
              king_no, king_ko, king_en, ed_ko, ed_en, is_main = EDITIONS[ed]
              idp = aid.split("_")
              reign_year = lunar_month = lunar_day = None
              is_leap = False
              if len(idp) == 3 and len(idp[1]) == 8 and idp[1][0] == "1" and idp[1][1:].replace("?", "").isdigit():
                  # a few IDs carry '??' where the day (or month) is unknown; those fall through to the date string
                  try:
                      reign_year, lunar_month, is_leap, lunar_day = int(idp[1][1:3]), int(idp[1][3:5]), idp[1][5] == "1", int(idp[1][6:8])
                  except ValueError:
                      reign_year = int(idp[1][1:3]) if idp[1][1:3].isdigit() else None
                      lunar_month = lunar_day = None
              year_ce = int(dm.group(1)) if dm else None
              if dm and lunar_month is None:
                  lunar_month, lunar_day, is_leap = int(dm.group(2)), int(dm.group(3)), dm.group(4) == "1"
              sol, calname, jdn = (None, None, None)
              # From 1896-01-01 (Geonyang 1) the court used the Gregorian calendar; NIKH marks those days 陽曆 and the
              # month/day fields are already solar, so they are taken as given instead of being converted
              date_system = "solar" if cur.get("간지", "") == "陽曆" else "lunar"
              if year_ce and lunar_month and lunar_day:
                  if date_system == "solar":
                      try:
                          g = dt.date(year_ce, lunar_month, lunar_day)
                          sol, calname, jdn = g.isoformat(), "gregorian", jdn_from_gregorian(g)
                      except ValueError:
                          pass
                  else:
                      sol, calname, jdn = solar(year_ce, lunar_month, lunar_day, is_leap)
              rows.append(dict(
                  article_id=aid, edition=ed, king_no=king_no, king_ko=king_ko, king_en=king_en,
                  edition_ko=ed_ko, edition_en=ed_en, is_main=is_main, file=fn, level=lv.tag,
                  title="" if ed in KOGL4 else title, license="KOGL-4" if ed in KOGL4 else "KOGL-1", year_ce=year_ce, reign_year=reign_year, lunar_month=lunar_month,
                  is_leap=is_leap, lunar_day=lunar_day, date_system=date_system, ganji=cur.get("간지", "") if dm else "",
                  solar_date=sol, solar_calendar=calname, jdn=jdn,
                  n_han=len(HAN.findall(txt)), n_hangul=len(HANGUL.findall(txt)),
                  n_chars=len(re.sub(r"\s", "", txt)), n_saron=n_saron, n_saron_han=len(HAN.findall(saron_txt)),
                  n_annot=n_annot, n_person_tags=n_person, n_del_han=n_del,
                  subjects=subjects, sago=sago, yeongin=yeongin,
                  nikh_url=f"https://sillok.history.go.kr/id/k{aid[1:]}",
              ))
          print(fn, len(rows), flush=True)
    df = flag_days_sillok(pd.DataFrame(rows))
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT / "articles.parquet", index=False)
    df.to_csv(OUT / "articles.csv", index=False, encoding="utf-8")
    print("articles:", len(df), "residual &# in text:", residual)
    print(df.groupby("edition").size())


# ---- 1.2.4: ganji-anchored solar date -------------------------------------------------------------------------
STEMS, BRANCHES = "甲乙丙丁戊己庚辛壬癸", "子丑寅卯辰巳午未申酉戌亥"
GANJI60 = [STEMS[i % 10] + BRANCHES[i % 12] for i in range(60)]
GREG_SWITCH_JDN = 2299161


def ganji_of_jdn(jdn):
    return GANJI60[(int(jdn) - 2451545 + 54) % 60]


def iso_from_jdn(j):
    if j is None or j != j:
        return None
    j = int(j)
    if j < GREG_SWITCH_JDN:
        y, m, d = julian_from_jdn(j)
        return f"{y:04d}-{m:02d}-{d:02d}"
    return dt.date.fromordinal(j - 1721425).isoformat()


def flag_days_sillok(df):
    """Post-pass: compare each lunar-dated article's ganji (NIKH 간지) with the ganji of the converted day.
    Where a whole lunar month is off by one day, the contemporaneous calendar started that month a day earlier or
    later than the table behind korean_lunar_calendar (Ahn et al. 2000, JKAS 33, list such months); isolated cases are
    typos. solar_date_ganji follows the ganji for month-shift days and for days the package refused (30th of a
    29-day month, 31st, unknown day 99) when a matching ganji lies within two days of the expected position; it equals
    solar_date otherwise. Metrics keep using solar_date; the method page reports the counts.
    date_flag: '' | ganji_month_shift | ganji_typo | ganji_only (no solar_date, dated by ganji) | ganji_unresolved."""
    df = df.copy()
    lunar = (df.date_system == "lunar") & df.ganji.isin(GANJI60)
    has = lunar & df.jdn.notna()
    off = pd.Series(0, index=df.index, dtype="int64")
    for i in df.index[has]:
        o = (GANJI60.index(df.at[i, "ganji"]) - GANJI60.index(ganji_of_jdn(df.at[i, "jdn"]))) % 60
        off.at[i] = o - 60 if o > 30 else o
    df["ganji_offset"] = off
    ym = df.year_ce.astype("Int64").astype(str) + "-" + df.lunar_month.astype("Int64").astype(str) + df.is_leap.map({True: "L", False: ""})
    flag = pd.Series("", index=df.index, dtype=object)
    nz = has & (off != 0)
    for key, grp in df[nz].groupby(ym[nz]):
        n_month = int((ym == key)[has].sum())
        if len(grp) >= max(3, int(0.9 * n_month)) and grp.ganji_offset.abs().max() == 1 and grp.ganji_offset.nunique() == 1:
            flag[grp.index] = "ganji_month_shift"
        else:
            flag[grp.index] = "ganji_typo"
    jg = df.jdn.copy()
    shift = flag == "ganji_month_shift"
    jg[shift] = df.jdn[shift] + df.ganji_offset[shift]
    # days the package refused: anchor on the 1st of the month and search the ganji nearby
    miss = lunar & df.jdn.isna() & df.year_ce.notna() & df.lunar_month.notna()
    for i in df.index[miss]:
        y, m, lp = int(df.at[i, "year_ce"]), int(df.at[i, "lunar_month"]), bool(df.at[i, "is_leap"])
        _, _, j1 = solar(y, m, 1, lp)
        if j1 is None:
            flag.at[i] = "ganji_unresolved"; continue
        g = df.at[i, "ganji"]; d = df.at[i, "lunar_day"]
        if d == d and d is not None and 1 <= int(d) <= 31:
            cands = sorted(range(-2, 3), key=abs)
            hit = next((j1 + int(d) - 1 + k for k in cands if ganji_of_jdn(j1 + int(d) - 1 + k) == g), None)
        else:
            hit = next((j1 + k for k in range(0, 30) if ganji_of_jdn(j1 + k) == g), None)
        if hit is None:
            flag.at[i] = "ganji_unresolved"
        else:
            jg.at[i] = hit; flag.at[i] = "ganji_only"
    df["date_flag"] = flag
    df["jdn_ganji"] = jg
    df["solar_date_ganji"] = jg.map(iso_from_jdn)
    return df


def postpass():
    import json
    df = pd.read_parquet(OUT / "articles.parquet")
    for c in ("ganji_offset", "date_flag", "jdn_ganji", "solar_date_ganji"):
        if c in df.columns:
            df = df.drop(columns=c)
    df = flag_days_sillok(df)
    df.to_parquet(OUT / "articles.parquet", index=False)
    df.to_csv(OUT / "articles.csv", index=False, encoding="utf-8")
    lunar = (df.date_system == "lunar") & df.ganji.isin(GANJI60)
    ym = df.year_ce.astype("Int64").astype(str) + "-" + df.lunar_month.astype("Int64").astype(str) + df.is_leap.map({True: "L", False: ""})
    sh = df.date_flag == "ganji_month_shift"
    st = {"lunar_with_ganji": int(lunar.sum()), "lunar_with_solar": int((lunar & df.jdn.notna()).sum()),
          "offset_nonzero": int(((df.ganji_offset != 0) & lunar & df.jdn.notna()).sum()),
          "month_shift_articles": int(sh.sum()), "month_shift_months": int(ym[sh].nunique()),
          "month_shift_plus1": int((sh & (df.ganji_offset == 1)).sum()), "month_shift_minus1": int((sh & (df.ganji_offset == -1)).sum()),
          "typo_articles": int((df.date_flag == "ganji_typo").sum()),
          "no_solar_lunar_dated": int((lunar & df.jdn.isna() & df.lunar_month.notna()).sum()),
          "ganji_only": int((df.date_flag == "ganji_only").sum()), "ganji_unresolved": int((df.date_flag == "ganji_unresolved").sum()),
          "no_solar_taejo_cheoljong": int((lunar & df.jdn.isna() & df.lunar_month.notna() & (df.king_no.astype(int) <= 25)).sum()),
          "month_shift_months_list": sorted(ym[sh].unique().tolist())}
    (OUT / "date_flags.json").write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(st, ensure_ascii=False))
    print(df[df.date_flag.isin(["ganji_only", "ganji_unresolved"])][["article_id", "year_ce", "lunar_month", "lunar_day", "ganji", "solar_date_ganji", "date_flag"]].to_string(index=False))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--postpass":
        postpass(); raise SystemExit
    sys.stdout.reconfigure(encoding="utf-8")
    main()
