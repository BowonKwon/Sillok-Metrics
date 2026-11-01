# -*- coding: utf-8 -*-
"""Validate the lunar→solar conversion used in build_articles.py against astronomy.

  python src/check_calendar.py            # writes data/derived/lunar_month_starts.csv

For every lunar month 1392–1863 (leap months included) the package korean_lunar_calendar gives
the solar date of day 1. The true new moon (conjunction) is computed with JPL DE406 via skyfield
and expressed in Seoul local mean time (UT + 8h28m, longitude 126.98° E). The Joseon civil
calendar put day 1 on the day of the computed conjunction, so the two should agree to the day,
with ±1-day differences where the historical calendar's own computation or the midnight boundary
differed. Any difference of two days or more would indicate an error in the package.
"""
import datetime as dt
import sys
from pathlib import Path

import pandas as pd
from korean_lunar_calendar import KoreanLunarCalendar
from skyfield import almanac, api

ROOT = Path(__file__).resolve().parent.parent
EPH = ROOT / "data" / "raw" / "eph"
OUT = ROOT / "data" / "derived" / "lunar_month_starts.csv"
SEOUL_OFFSET = dt.timedelta(hours=8, minutes=28)


def main():
    load = api.Loader(str(EPH), verbose=False)
    ts = load.timescale()
    eph = load("de406.bsp")
    t, y = almanac.find_discrete(ts.utc(1391, 1, 1), ts.utc(1930, 1, 1), almanac.moon_phases(eph))
    newmoons = sorted((ti.utc_datetime() + SEOUL_OFFSET).date() for ti, yi in zip(t, y) if yi == 0)
    nm = set(newmoons)
    rows = []
    for yr in range(1392, 1929):
        for m in range(1, 13):
            for leap in (False, True):
                c = KoreanLunarCalendar()
                if not c.setLunarDate(yr, m, 1, leap):
                    continue
                g = dt.date.fromisoformat(c.SolarIsoFormat())   # proleptic Gregorian
                if g in nm:
                    off = 0
                elif g - dt.timedelta(1) in nm:
                    off = 1      # package day 1 is the day after the conjunction
                elif g + dt.timedelta(1) in nm:
                    off = -1     # package day 1 is the day before the conjunction
                else:
                    off = None
                rows.append(dict(year_ce=yr, lunar_month=m, is_leap=leap, day1_gregorian_proleptic=g.isoformat(),
                                 offset_from_new_moon_days=off))
    df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print("months", len(df))
    print(df.offset_from_new_moon_days.value_counts(dropna=False).sort_index())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
