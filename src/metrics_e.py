# -*- coding: utf-8 -*-
"""Series E — justice and society.

  python src/metrics_e.py

E1 death-penalty mentions: 'justice–punishment' articles with a capital-punishment term, per 50-year
   period, with the execution-confirmed correction from the hand-coded sample
   (data/coding/death_penalty_sample.csv: 240 articles, 20 per period, coded 2026-09-26).
E2 relief/famine, E3 vernacular script, E4 slaves: keyword shares (precision from coded samples
   merged at build time from data/coding/*.csv when present).
Outputs: e_death.csv, e_death_sample_summary.csv, e_relief.csv, e_eonmun.csv, e_slave.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "derived"
C = ROOT / "data" / "coding"
BINS = [(1392, 1400), (1400, 1450), (1450, 1500), (1500, 1550), (1550, 1600), (1600, 1650), (1650, 1700), (1700, 1750), (1750, 1800), (1800, 1850), (1850, 1900), (1900, 1911)]


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def period_of(y):
    for a, b in BINS:
        if a <= y < b:
            return f"{a}–{b-1}"
    return None


def main():
    art = pd.read_parquet(D / "articles.parquet")
    hits = pd.read_parquet(D / "keyword_hits.parquet")
    main_ = art[art.is_main & art.year_ce.notna() & (art.year_ce <= 1910)].copy()
    main_["period"] = main_.year_ce.map(period_of)

    # ---- E1
    ids = set(hits[hits.pattern == "death_penalty"].article_id)
    pun = main_[main_.subjects.str.contains("사법-행형", na=False)]
    dp = pun[pun.article_id.isin(ids)]
    e = main_.groupby("period").size().rename("n_articles").to_frame()
    e["n_mentions"] = dp.groupby("period").size()
    e = e.fillna(0)
    e["mentions_per_1000"] = e.n_mentions / e.n_articles * 1000
    samp = C / "death_penalty_sample.csv"
    if samp.exists():
        s = pd.read_csv(samp, encoding="utf-8-sig")
        # sample strata: 1350 = 1392–1399; 1850 and 1900 map to the last two periods
        s["period"] = s.stratum.map(lambda v: "1392–1399" if int(v) == 1350 else period_of(int(v)))
        s = s[s.period.notna()]
        rows = []
        for p, g in s.groupby("period"):
            ev = g[g["범주"] == "사건"]
            k = int((ev.executed == "yes").sum()); n = len(g)   # denominator: every sampled mention article, so the rate applies to all mentions
            lo, hi = wilson(k, n)
            rows.append(dict(period=p, sample=len(g), events=len(ev), executed_confirmed=k, rate=k / n if n else np.nan, ci_lo=lo, ci_hi=hi,
                             event_rate=len(ev) / n, exec_rate_among_events=k / len(ev) if len(ev) else np.nan,
                             not_relevant=int((g["범주"] == "무관").sum()), mention_only=int((g["범주"] == "언급").sum())))
        ss = pd.DataFrame(rows).set_index("period")
        ss.to_csv(D / "e_death_sample_summary.csv")
        e = e.join(ss[["events", "executed_confirmed", "rate", "ci_lo", "ci_hi"]].rename(columns=dict(rate="exec_rate", ci_lo="exec_ci_lo", ci_hi="exec_ci_hi")))
        e["mentions_x_exec_rate_per_1000"] = e.mentions_per_1000 * e.exec_rate
        e["mentions_x_exec_lo_per_1000"] = e.mentions_per_1000 * e.exec_ci_lo
        e["mentions_x_exec_hi_per_1000"] = e.mentions_per_1000 * e.exec_ci_hi
    e.to_csv(D / "e_death.csv", encoding="utf-8")
    # by reign too
    r = main_.groupby(["king_no", "king_ko", "king_en", "edition"]).size().rename("n_articles").to_frame()
    r["n_mentions"] = dp.groupby(["king_no", "king_ko", "king_en", "edition"]).size()
    r = r.fillna(0); r["mentions_per_1000"] = r.n_mentions / r.n_articles * 1000
    r.to_csv(D / "e_death_reign.csv", encoding="utf-8")

    # ---- E2–E4
    def keyword_table(key, name, by_year=False):
        ids = set(hits[hits.pattern == key].article_id)
        g = main_.groupby(["king_no", "king_ko", "king_en", "edition"])
        out = g.size().rename("n_articles").to_frame()
        out["n_keyword"] = g.apply(lambda x: x.article_id.isin(ids).sum())
        out["keyword_share"] = out.n_keyword / out.n_articles
        if key == "eonmun":
            out["n_keyword_justice"] = g.apply(lambda x: (x.article_id.isin(ids) & x.subjects.str.contains("사법", na=False)).sum())
        out.to_csv(D / name, encoding="utf-8")
        if by_year:
            y = main_.groupby("year_ce").size().rename("n_articles").to_frame()
            y["n_keyword"] = main_[main_.article_id.isin(ids)].groupby("year_ce").size()
            y = y.fillna(0); y["keyword_share"] = y.n_keyword / y.n_articles
            y.to_csv(D / name.replace(".csv", "_yearly.csv"), encoding="utf-8")
        return out
    keyword_table("relief", "e_relief.csv", by_year=True)
    keyword_table("eonmun", "e_eonmun.csv")
    keyword_table("slaves", "e_slave.csv")
    print(e.to_string())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
