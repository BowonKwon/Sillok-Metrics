# -*- coding: utf-8 -*-
"""Series A — volume and density of the record.

  python src/metrics_a.py

Reads data/derived/articles.parquet, writes
  data/derived/a_editions.csv   one row per edition (30): counts, characters, reign span, density, saron
  data/derived/a_yearly.csv     one row per year CE (main editions only): articles, characters, saron
  data/derived/a_monthly.csv    one row per (edition, year CE, lunar month, leap): articles — for gap counting
  data/derived/a_length.csv     article-length quantiles per edition
All definitions are documented in registry.py; this file only computes.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "derived"


def month_index(y, m, leap):
    """Serial lunar month index for span counting (leap month counted as its own month)."""
    return y * 13 + m + (0.5 if leap else 0)


def main():
    global CAL, JDN_1896
    CAL = pd.read_csv(D / "lunar_month_starts.csv")
    CAL["jdn"] = pd.to_datetime(CAL.day1_gregorian_proleptic).map(lambda d: d.toordinal() + 1721425)
    CAL = CAL.sort_values("jdn").reset_index(drop=True)
    JDN_1896 = pd.Timestamp("1896-01-01").toordinal() + 1721425
    df = pd.read_parquet(D / "articles.parquet")
    dated = df[df.year_ce.notna()].copy()
    # reign span in lunar months: distinct (year, month, leap) between first and last dated article
    span = {}
    for ed, g in dated.groupby("edition"):
        months = g[["year_ce", "lunar_month", "is_leap"]].drop_duplicates()
        first = g.loc[g.jdn.idxmin()]
        last = g.loc[g.jdn.idxmax()]
        # reign span: days from the first to the last dated article (JDN), the same rule before and after the 1896
        # switch to the solar calendar. Reign months = calendar months touched by that span: lunar months (from
        # the validated month-start table, leap months included) up to 1895-12, solar months from 1896-01.
        days = int(last.jdn - first.jdn) + 1
        cal = CAL[(CAL.jdn <= last.jdn)]
        start_idx = cal[cal.jdn <= first.jdn].index.max()
        lunar_months = int(((cal.index >= start_idx) & (cal.jdn < JDN_1896)).sum()) if start_idx == start_idx else 0
        solar_months = 0
        if last.jdn >= JDN_1896:
            y0, m0 = (1896, 1) if first.jdn < JDN_1896 else (int(first.solar_date[:4]), int(first.solar_date[5:7]))
            y1, m1 = int(last.solar_date[:4]), int(last.solar_date[5:7])
            solar_months = (y1 - y0) * 12 + (m1 - m0) + 1
        span[ed] = dict(first_solar=first.solar_date, last_solar=last.solar_date, reign_days=days, reign_months=lunar_months + solar_months,
                        months_with_articles=len(months), days_with_articles=g.jdn.nunique())
    ed = df.groupby("edition").agg(
        king_no=("king_no", "first"), king_ko=("king_ko", "first"), king_en=("king_en", "first"),
        edition_ko=("edition_ko", "first"), edition_en=("edition_en", "first"), is_main=("is_main", "first"),
        n_articles=("article_id", "size"), n_dated=("year_ce", "count"),
        n_han=("n_han", "sum"), n_hangul=("n_hangul", "sum"), n_chars=("n_chars", "sum"),
        n_saron_articles=("n_saron", lambda s: int((s > 0).sum())), n_saron=("n_saron", "sum"),
        n_saron_han=("n_saron_han", "sum"), n_annot=("n_annot", "sum"), n_del_han=("n_del_han", "sum"),
        median_len=("n_han", "median"), mean_len=("n_han", "mean"),
    )
    sp = pd.DataFrame(span).T
    ed = ed.join(sp)
    ed["reign_years"] = ed.reign_days / 365.2422
    ed["articles_per_year"] = ed.n_dated / ed.reign_years
    ed["han_per_year"] = ed.n_han / ed.reign_years
    ed["saron_share"] = ed.n_saron_articles / ed.n_articles
    ed["saron_han_share"] = ed.n_saron_han / ed.n_han
    ed["empty_months"] = ed.reign_months - ed.months_with_articles
    ed["empty_month_share"] = ed.empty_months / ed.reign_months
    ed = ed.sort_values(["king_no", "edition"])
    ed.to_csv(D / "a_editions.csv", encoding="utf-8")

    main_ = dated[dated.is_main & (dated.year_ce <= 1910)]
    ye = main_.groupby(["edition", "year_ce"]).agg(n_articles=("article_id", "size"), n_han=("n_han", "sum"))
    ye.to_csv(D / "a_yearly_by_edition.csv", encoding="utf-8")
    yr = main_.groupby("year_ce").agg(n_articles=("article_id", "size"), n_han=("n_han", "sum"),
                                      n_saron_articles=("n_saron", lambda s: int((s > 0).sum())),
                                      days_with_articles=("jdn", "nunique"), editions=("edition", lambda s: ";".join(sorted(set(s)))))
    yr.to_csv(D / "a_yearly.csv", encoding="utf-8")

    mo = dated.groupby(["edition", "year_ce", "lunar_month", "is_leap"]).agg(n_articles=("article_id", "size"), n_han=("n_han", "sum"))
    mo.to_csv(D / "a_monthly.csv", encoding="utf-8")

    q = df.groupby("edition").n_han.describe(percentiles=[.1, .25, .5, .75, .9, .99])
    q.to_csv(D / "a_length.csv", encoding="utf-8")
    pd.set_option("display.width", 220)
    print(ed[["edition_ko", "n_articles", "n_dated", "n_han", "reign_months", "articles_per_year", "han_per_year", "saron_share", "empty_months"]].to_string())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
