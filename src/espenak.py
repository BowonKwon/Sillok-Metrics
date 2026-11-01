# -*- coding: utf-8 -*-
"""Parse the Espenak–Meeus Five Millennium Catalog of Solar Eclipses (NASA) for 1392–1863 and
cross-check it against the new moons computed in astro.py.

  python src/espenak.py      # reads data/raw/espenak/5MCSEcatalog.txt, writes data/derived/espenak_1392_1863.csv

Catalog dates are Julian-calendar before 1582-10-15 and Gregorian after; both are turned into a
Julian Day Number so they can be compared with the DE406 new moons (±1 day).
"""
import datetime as dt
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "derived"
MON = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
LINE = re.compile(r"\s*(\d+)\s+(\d+)\s+(-?\d{4}) (\w{3}) (\d{2})\s+(\d\d:\d\d:\d\d)\s+(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\S+)\s+(-?[\d.]+)\s+([\d.]+)")


def jdn(y, mo, d):
    if (y, mo, d) < (1582, 10, 15):
        a = (14 - mo) // 12
        yy = y + 4800 - a
        mm = mo + 12 * a - 3
        return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - 32083
    return dt.date(y, mo, d).toordinal() + 1721425


def main():
    rows = []
    for l in open(ROOT / "data" / "raw" / "espenak" / "5MCSEcatalog.txt", encoding="utf-8", errors="replace"):
        m = LINE.match(l)
        if m and 1392 <= int(m.group(3)) <= 1863:
            y, mo, d = int(m.group(3)), MON[m.group(4)], int(m.group(5))
            rows.append(dict(cat_no=int(m.group(1)), year=y, month=mo, day=d, td_greatest=m.group(6), etype=m.group(10),
                             gamma=float(m.group(11)), magnitude=float(m.group(12)), jdn=jdn(y, mo, d)))
    e = pd.DataFrame(rows)
    e.to_csv(D / "espenak_1392_1863.csv", index=False)
    se = pd.read_csv(D / "solar_eclipses_seoul.csv")
    se["jdn"] = (se.newmoon_jd + 0.5).astype(int)
    E = set(e.jdn)   # new moons span 1391–1864 so every catalog row of 1392–1863 has a candidate
    se["in_espenak"] = [any(j + k in E for k in (-1, 0, 1)) for j in se.jdn]
    S = set(se.jdn)
    se = se[(se.newmoon_ut >= "1392-01") & (se.newmoon_ut < "1864")].copy()
    print("Espenak 1392-1863:", len(e), e.etype.str[0].value_counts().to_dict())
    print("new moons matched:", int(se.in_espenak.sum()), "| Espenak rows without a new moon ±1d:", sum(not any(j + k in S for k in (-1, 0, 1)) for j in E))
    print("geocentric min sep (deg) — in Espenak: max", round(se[se.in_espenak].geocentric_min_sep_deg.max(), 3), "| not in: min", round(se[~se.in_espenak].geocentric_min_sep_deg.min(), 3))
    print("Seoul-visible not in Espenak:", int((se.seoul_visible & ~se.in_espenak).sum()))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
