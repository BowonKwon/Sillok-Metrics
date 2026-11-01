# -*- coding: utf-8 -*-
"""Consistency checks for data/derived/articles.parquet.

  python src/check_articles.py [--index path/to/sillok-index.sqlite]

1. per-edition article counts vs an independent count (the vault index DB built by a different
   script in 2026-09, optional) and vs Bak & Oh (2015) Table 1 (articles with a date);
2. characters: sum of n_han vs the 2026-09-26 conversion check (49,533,709 CJK + 3,001,739 Hangul
   over the 30 editions, Taejo–Cheoljong);
3. no '&#' residue, every dated article converted to a solar date, lunar day/month ranges sane.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BAK_OH_2015 = {  # Table 1, articles per king (crawled from the NIKH site)
    "waa": 2387, "wba": 624, "wca": 10331, "wda": 30969, "wea": 2670, "wfa": 2534, "wga": 10832,
    "wha": 1503, "wia": 32443, "wja": 12009, "wka": 39653, "wla": 671, "wma": 15044, "wna": 26712,
    "woa": 22121, "wpa": 16046, "wqa": 5431, "wra": 9295, "wsa": 24209, "wta": 2744, "wua": 36731,
    "wva": 17681, "wwa": 15529, "wxa": 3986, "wya": 5771, "wza": 27939,   # Sunjong 4,858 in the paper = wzb + wzc
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="")
    a = ap.parse_args()
    df = pd.read_parquet(ROOT / "data" / "derived" / "articles.parquet")
    print("rows", len(df), "| editions", df.edition.nunique())
    dated = df[df.year_ce.notna()]
    print("dated", len(dated), "| undated", len(df) - len(dated))
    g = df.groupby("edition").agg(n=("article_id", "size"), dated=("year_ce", "count"),
                                  han=("n_han", "sum"), hangul=("n_hangul", "sum"), saron=("n_saron", "sum"))
    g["bak_oh"] = pd.Series(BAK_OH_2015)
    g["diff_dated_vs_bak"] = g["dated"] - g["bak_oh"]
    if a.index:
        c = sqlite3.connect(a.index)
        ix = pd.read_sql("select vol as edition, count(*) n_index, sum(han) han_index from article group by vol", c).set_index("edition")
        g = g.join(ix)
        g["diff_n_vs_index"] = g["n"] - g["n_index"]
        g["diff_han_vs_index"] = g["han"] - g["han_index"]
    pd.set_option("display.width", 200)
    print(g.to_string())
    print("total han", int(df.n_han.sum()), "(2026-09-26 check: 49,533,709 incl. Gojong/Sunjong)")
    print("total hangul", int(df.n_hangul.sum()))
    bad = df[(df.year_ce.notna()) & (df.solar_date.isna())]
    print("dated but no solar conversion:", len(bad))
    if len(bad):
        print(bad[["article_id", "year_ce", "lunar_month", "is_leap", "lunar_day"]].head(20).to_string())
    print("lunar_month range", df.lunar_month.min(), df.lunar_month.max(), "| lunar_day range", df.lunar_day.min(), df.lunar_day.max())
    print("leap articles", int(df.is_leap.sum()))
    print("titles with '&#':", int(df.title.str.contains("&#", regex=False).sum()))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
