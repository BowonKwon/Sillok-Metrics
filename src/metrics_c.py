# -*- coding: utf-8 -*-
"""Series C — sky and weather.

  python src/metrics_c.py

Inputs: articles.parquet, keyword_hits.parquet, solar_eclipses_seoul.csv, lunar_eclipses_seoul.csv,
        venus_inferior_conjunctions.csv, and (optional) data/coding/solar_eclipse_types.csv
        (article_id, type) from the hand-coding step.
Outputs: c_solar_articles.csv, c_solar.csv, c_lunar_articles.csv, c_lunar.csv, c_venus.csv,
         c_venus_days.csv, c_comet.csv, c_quake.csv, c_weather.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "derived"
CODING = ROOT / "data" / "coding"
VENUS_SYNODIC = 583.92
PROVINCES = ["京畿", "江原", "黃海", "忠淸", "全羅", "慶尙", "平安", "咸鏡", "咸吉", "永安"]


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def main():
    art = pd.read_parquet(D / "articles.parquet").set_index("article_id")
    hits = pd.read_parquet(D / "keyword_hits.parquet")
    main_ = art[art.is_main & (art.license == "KOGL-1")]   # sky series: Taejo–Cheoljong only (KOGL-4 editions are not text-coded)
    art = art[art.license == "KOGL-1"]

    # ---- C1 solar eclipses
    se = pd.read_csv(D / "solar_eclipses_seoul.csv")
    # Seoul local-date JDN for each visible eclipse maximum
    se_vis = se[se.seoul_visible].copy()
    se_vis["jdn_lmt"] = se_vis.seoul_max_date_lmt.map(lambda s: int(pd.Timestamp(s).to_julian_date() + 0.5))
    vis_set = set(se_vis.jdn_lmt)
    earth_set = set(pd.read_csv(D / "espenak_1392_1863.csv").jdn)   # any eclipse on Earth (Espenak–Meeus catalog)
    sol = hits[hits.pattern == "solar_eclipse"].merge(art, left_on="article_id", right_index=True)
    sol = sol[sol.jdn.notna()].copy()
    sol["jdn"] = sol.jdn.astype(int)

    def match(jset, jdn, w):
        return any((jdn + k) in jset for k in range(-w, w + 1))
    sol["match_seoul_w0"] = [match(vis_set, j, 0) for j in sol.jdn]
    sol["match_seoul_w1"] = [match(vis_set, j, 1) for j in sol.jdn]
    sol["match_earth_w1"] = [match(earth_set, j, 1) for j in sol.jdn]
    # nearest visible eclipse (days)
    vis_arr = np.array(sorted(vis_set))
    sol["days_to_nearest_seoul_eclipse"] = [int(np.min(np.abs(vis_arr - j))) for j in sol.jdn]
    cod = CODING / "solar_eclipse_types.csv"
    if cod.exists():
        c = pd.read_csv(cod)
        sol = sol.merge(c[["article_id", "type"]], on="article_id", how="left")
    else:
        sol["type"] = "uncoded"
    cols = ["article_id", "edition", "king_ko", "year_ce", "lunar_month", "is_leap", "lunar_day", "solar_date", "solar_calendar", "jdn",
            "type", "match_seoul_w0", "match_seoul_w1", "match_earth_w1", "days_to_nearest_seoul_eclipse", "n_hits", "context", "nikh_url"]
    sol[cols].to_csv(D / "c_solar_articles.csv", index=False, encoding="utf-8")
    rows = []
    for t, g in sol.groupby("type"):
        for w in ("match_seoul_w0", "match_seoul_w1", "match_earth_w1"):
            k, n = int(g[w].sum()), len(g)
            lo, hi = wilson(k, n)
            rows.append(dict(type=t, window=w, n=n, matched=k, rate=k / n if n else np.nan, ci_lo=lo, ci_hi=hi))
    for w in ("match_seoul_w0", "match_seoul_w1", "match_earth_w1"):
        k, n = int(sol[w].sum()), len(sol)
        lo, hi = wilson(k, n)
        rows.append(dict(type="all", window=w, n=n, matched=k, rate=k / n, ci_lo=lo, ci_hi=hi))
    pd.DataFrame(rows).to_csv(D / "c_solar.csv", index=False)
    # reverse: visible eclipses 1392-1863 with/without an article within ±1 day
    rng = se_vis[(se_vis.seoul_max_date_lmt >= "1392-08") & (se_vis.seoul_max_date_lmt < "1864-01")].copy()
    art_jd = set(sol.jdn)
    rng["has_article_w1"] = [match(art_jd, j, 1) for j in rng.jdn_lmt]
    rng.to_csv(D / "c_solar_eclipses_recorded.csv", index=False)

    # ---- C2 lunar eclipses
    le = pd.read_csv(D / "lunar_eclipses_seoul.csv")
    le_vis = le[le.seoul_visible].copy()
    le_vis["jdn_lmt"] = le_vis.max_date_lmt.map(lambda s: int(pd.Timestamp(s).to_julian_date() + 0.5))
    lset = set(le_vis.jdn_lmt)
    lun = hits[hits.pattern == "lunar_eclipse"].merge(art, left_on="article_id", right_index=True)
    lun = lun[lun.jdn.notna()].copy(); lun["jdn"] = lun.jdn.astype(int)
    lun["match_seoul_w0"] = [match(lset, j, 0) for j in lun.jdn]
    lun["match_seoul_w1"] = [match(lset, j, 1) for j in lun.jdn]
    lun["match_seoul_prevday"] = [(j in lset) or ((j + 1) in lset) for j in lun.jdn]   # eclipse after midnight recorded under previous date
    lun[["article_id", "edition", "king_ko", "year_ce", "lunar_month", "is_leap", "lunar_day", "solar_date", "jdn",
         "match_seoul_w0", "match_seoul_w1", "match_seoul_prevday", "n_hits", "context", "nikh_url"]].to_csv(D / "c_lunar_articles.csv", index=False, encoding="utf-8")
    rows = []
    for w in ("match_seoul_w0", "match_seoul_prevday", "match_seoul_w1"):
        k, n = int(lun[w].sum()), len(lun); lo, hi = wilson(k, n)
        rows.append(dict(window=w, n=n, matched=k, rate=k / n, ci_lo=lo, ci_hi=hi))
    pd.DataFrame(rows).to_csv(D / "c_lunar.csv", index=False)

    # ---- C3 Venus
    vc = pd.read_csv(D / "venus_inferior_conjunctions.csv")
    ven = hits[hits.pattern == "venus_daytime"].merge(main_, left_on="article_id", right_index=True)
    ven = ven[ven.jdn.notna()]
    days = np.array(sorted(set(ven.jdn.astype(int))), dtype=float)
    ic = vc.jd.values
    # phase relative to the nearest inferior conjunction (days, negative = before)
    phase = np.array([d - ic[np.argmin(np.abs(ic - d))] for d in days])
    within90 = float(np.mean(np.abs(phase) <= 90)); within6 = float(np.mean(np.abs(phase) <= 6))
    ph = 2 * np.pi * (days % VENUS_SYNODIC) / VENUS_SYNODIC
    Z = float((np.cos(ph).sum() ** 2 + np.sin(ph).sum() ** 2) / len(days))
    periods = np.linspace(300, 900, 6001)
    Zs = [(np.cos(2 * np.pi * (days % P) / P).sum() ** 2 + np.sin(2 * np.pi * (days % P) / P).sum() ** 2) / len(days) for P in periods]
    best = float(periods[int(np.argmax(Zs))])
    pd.DataFrame([dict(n_days=len(days), n_articles=len(ven), first=ven.solar_date.min(), last=ven.solar_date.max(),
                       within_90d=within90, within_90d_uniform=180 / VENUS_SYNODIC, within_6d=within6, within_6d_uniform=12 / VENUS_SYNODIC,
                       rayleigh_Z_at_583_92=Z, best_period_days=best, rayleigh_Z_best=float(max(Zs)))]).to_csv(D / "c_venus.csv", index=False)
    pd.DataFrame(dict(jdn=days.astype(int), phase_days=phase)).to_csv(D / "c_venus_days.csv", index=False)
    pd.DataFrame(dict(period=periods[::10], Z=np.array(Zs)[::10])).to_csv(D / "c_venus_periodogram.csv", index=False)

    # ---- C4 comets, C5 earthquakes: yearly counts (coding adds precision later)
    for key, name in (("comet", "c_comet"), ("earthquake", "c_quake")):
        h = hits[hits.pattern == key].merge(main_, left_on="article_id", right_index=True)
        h = h[h.year_ce.notna()]
        y = h.groupby("year_ce").agg(n_articles=("article_id", "size"), n_days=("jdn", "nunique"))
        y.to_csv(D / f"{name}.csv")
        if key == "earthquake":
            def prov(ctx):
                for p in PROVINCES:
                    if p in ctx:
                        return p
                return "서울(도명 없음)"
            h["province"] = h.context.map(prov)
            h.groupby(["year_ce", "province"]).size().unstack(fill_value=0).to_csv(D / "c_quake_province.csv")
            h[["article_id", "year_ce", "solar_date", "province", "context", "nikh_url"]].to_csv(D / "c_quake_articles.csv", index=False, encoding="utf-8")

    # ---- C6 summer frost/snow/hail per 1,000 weather-class articles, by decade
    w = main_[main_.year_ce.notna()].copy()
    w["decade"] = (w.year_ce // 10 * 10).astype(int)
    weather_cls = w[w.subjects.str.contains("과학-천기", na=False)].groupby("decade").size()
    summer = w[w.lunar_month.between(5, 7)]
    out = pd.DataFrame(dict(weather_class_articles=weather_cls))
    for key in ("frost", "snow", "hail"):
        ids = set(hits[hits.pattern == key].article_id)
        s = summer[summer.index.isin(ids)]
        if key == "frost":   # drop the solar term 霜降 and pure name/figurative hits are left to coding
            s = s[~s.title.str.contains("상강", na=False)]
        out[f"{key}_days"] = s.groupby("decade").jdn.nunique()
    out = out.fillna(0)
    for key in ("frost", "snow", "hail"):
        out[f"{key}_per_1000"] = out[f"{key}_days"] / out.weather_class_articles * 1000
    out["frost_snow_per_1000"] = (out.frost_days + out.snow_days) / out.weather_class_articles * 1000
    out["reliable"] = out.weather_class_articles >= 100   # decades with fewer weather-class articles are not plotted
    out.to_csv(D / "c_weather.csv")
    print("solar articles", len(sol), "| lunar", len(lun), "| venus days", len(days), "within90", round(within90, 3), "Z", round(Z, 1), "best", best)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
