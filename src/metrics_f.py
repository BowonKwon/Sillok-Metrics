# -*- coding: utf-8 -*-
"""Series F — the weather cell of the Seungjeongwon Ilgi (1.2).

  python src/metrics_f.py

Reads data/derived/sjw_days.parquet (R1 judgements from weather_tokens.py) and the external files under
data/raw/external/ (never published):
  zenodo-lyu2024/SJWilgi_Seoul_Weather_YR1623_1910.csv   Lyu et al. 2024, CC BY 4.0 — same NIKH day IDs
  zenodo-lee2024/Seoul_precipitation_1778-1907_Lee_etal_2024.xlsx   Lee, Shin & Hong 2024, CC BY 4.0 — Gregorian dates
  kma-asos108/asos108_daily_*.csv                        KMA ASOS Seoul 108 daily, KOGL 1 — from 1907-10-01

Writes data/derived/f_*.csv:
  f_tokens_reign, f_tokens_month      F1 share of day kinds by reign and by lunar month
  f_compare_lyu, f_compare_lyu_diff   F1 three-way check, part 1: our R1 flags vs Lyu dummies (same day ID)
  f_compare_lee, f_compare_lee_diff   part 2: vs Lee category (swx) by Gregorian date, 1778–1907
  f_routine                           F2 routine-entry index by reign: 晴-only share, run lengths, rainy-season rain days
  f_rain_gauge                        F2 vs the rain gauge: days with measured rain that the cell calls rain, by 50 years
  f_asos                              F3 overlap with KMA daily observations 1907-10 .. 1910-08
  f_missing_reign, f_missing_yearly   F4 missing day nodes, blank cells, note-only cells
Rules fixed before computing (data/coding/weather_tokens.md §3–4); no rule is tuned to the external files.
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "derived"
X = ROOT / "data" / "raw" / "external"
KEYS = ["king_no", "king_ko", "king_en"]
FLAGS = ["clear_any", "cloudy_any", "rain_any", "snow_any", "hail_any", "wind_any"]


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def main():
    d = pd.read_parquet(D / "sjw_days.parquet")
    d["year_ce"] = d.year_ce.astype("Int64")
    w = d[d.kind == "weather"].copy()

    # ---------------- F1 token shares
    def shares(g):
        n = len(g)
        out = dict(n_days_weather=n, clear_only=g.clear_only.mean(), clear_any=g.clear_any.mean(), cloudy_any=g.cloudy_any.mean(),
                   rain_any=g.rain_any.mean(), snow_any=g.snow_any.mean(), precip_any=g.precip_any.mean(), mixed=g.mixed.mean(),
                   wind_any=g.wind_any.mean(), fog_any=g.fog_any.mean(), thunder_any=g.thunder_any.mean())
        return pd.Series(out)
    tr = w.groupby(KEYS).apply(shares).reset_index()
    tot = d.groupby(KEYS).agg(n_days=("day_id", "size"), n_blank=("kind", lambda s: (s == "blank").sum()), n_note_only=("kind", lambda s: (s == "note_only").sum())).reset_index()
    tr = tot.merge(tr, on=KEYS).sort_values("king_no")
    tr.to_csv(D / "f_tokens_reign.csv", index=False)
    tm = w.groupby("lunar_month").apply(shares).reset_index()
    tm.to_csv(D / "f_tokens_month.csv", index=False)
    print("F1 reigns", len(tr), "overall clear_only %.3f rain_any %.3f" % (w.clear_only.mean(), w.rain_any.mean()))

    # ---------------- F1 external check 1: Lyu et al. 2024 (same NIKH day id)
    ly = pd.read_csv(X / "zenodo-lyu2024" / "SJWilgi_Seoul_Weather_YR1623_1910.csv")
    ly = ly.rename(columns={"ID": "day_id", "Weather Text": "lyu_text", "Gregorian calendar": "lyu_greg"})
    m = d.merge(ly[["day_id", "lyu_text", "lyu_greg", "Sunny", "Cloudy", "Rainy", "Snow", "Hail", "Wind"]], on="day_id", how="outer", indicator=True)
    rows = [dict(item="days_in_ours", n=int(len(d))), dict(item="days_in_lyu", n=int(len(ly))), dict(item="days_in_both", n=int((m._merge == "both").sum())),
            dict(item="only_ours", n=int((m._merge == "left_only").sum())), dict(item="only_lyu", n=int((m._merge == "right_only").sum()))]
    both = m[m._merge == "both"].copy()
    pairs = [("clear_any", "Sunny"), ("cloudy_any", "Cloudy"), ("rain_any", "Rainy"), ("snow_any", "Snow"), ("hail_any", "Hail"), ("wind_any", "Wind")]
    diffs = []
    for ours, theirs in pairs:
        a = both[ours].fillna(False).astype(bool)
        b = both[theirs].fillna(0).astype(int).astype(bool)
        agree = int((a == b).sum()); n = int(len(both))
        lo, hi = wilson(agree, n)
        rows.append(dict(item=f"agree_{ours}_vs_{theirs}", n=n, agree=agree, rate=agree / n, ci_lo=lo, ci_hi=hi,
                         ours_only=int((a & ~b).sum()), theirs_only=int((~a & b).sum())))
        dd = both[a != b]
        for _, r in dd.iterrows():
            diffs.append(dict(day_id=r.day_id, variable=ours, ours=bool(r[ours]) if r[ours] == r[ours] else None, lyu=int(r[theirs]) if r[theirs] == r[theirs] else None,
                              weather=r.weather, lyu_text=r.lyu_text))
    # weather-string identity
    same_text = (both.weather.fillna("").str.replace(r"\s", "", regex=True) == both.lyu_text.fillna("").str.replace(r"\s", "", regex=True))
    rows.append(dict(item="same_weather_string", n=int(len(both)), agree=int(same_text.sum()), rate=float(same_text.mean())))
    # date identity: our solar_date (Gregorian from 1583) vs Lyu Gregorian
    lg = pd.to_datetime(both.lyu_greg, errors="coerce").dt.strftime("%Y-%m-%d")
    ok = (lg == both.solar_date)
    rows.append(dict(item="same_gregorian_date", n=int(both.solar_date.notna().sum()), agree=int(ok.sum()), rate=float(ok.sum() / both.solar_date.notna().sum())))
    pd.DataFrame(rows).to_csv(D / "f_compare_lyu.csv", index=False)
    pd.DataFrame(diffs).to_csv(D / "f_compare_lyu_diff.csv", index=False)
    print("Lyu: both", int((m._merge == "both").sum()), "diffs", len(diffs))

    # ---------------- F1 external check 2: Lee et al. 2024 (Gregorian date, 1778–1907)
    lee = pd.read_excel(X / "zenodo-lee2024" / "Seoul_precipitation_1778-1907_Lee_etal_2024.xlsx", sheet_name="daily_data")
    lee["date"] = pd.to_datetime(dict(year=lee.yy, month=lee.mm, day=lee.dd), errors="coerce").dt.strftime("%Y-%m-%d")
    lee = lee.rename(columns={"wx": "lee_text", "swx": "lee_cat", "rrn": "gauge_mm"})
    lm = d[d.solar_date.notna()].merge(lee[["date", "lee_text", "lee_cat", "gauge_mm", "flag_a-d", "flag_e"]], left_on="solar_date", right_on="date", how="inner")
    # Lee categories (weather_code sheet): 1 clear, 3 cloudy/mixed, 7 rain, 8 snow, 0 missing, 'm' no document
    lm["lee_cat"] = lm.lee_cat.astype(str)
    rows = [dict(item="days_matched_1778_1907", n=int(len(lm)))]
    comp = {"clear_any": lm.lee_cat.isin(["1"]), "rain_any": lm.lee_cat.isin(["7"]), "snow_any": lm.lee_cat.isin(["8"])}
    diffs = []
    sub = lm[lm.lee_cat.isin(["1", "3", "7", "8"])]
    for ours, lee_flag in comp.items():
        a = sub[ours].fillna(False).astype(bool); b = lee_flag.loc[sub.index]
        # Lee's single category can only flag one class per day; compare "ours says X" against "Lee's class is X" where
        # Lee's class is the dominant one, so disagreements include mixed days by construction — reported, not judged.
        agree = int((a == b).sum()); n = int(len(sub)); lo, hi = wilson(agree, n)
        rows.append(dict(item=f"agree_{ours}_vs_lee_cat", n=n, agree=agree, rate=agree / n, ci_lo=lo, ci_hi=hi, ours_only=int((a & ~b).sum()), lee_only=int((~a & b).sum())))
        for _, r in sub[a != b].iterrows():
            diffs.append(dict(day_id=r.day_id, date=r.solar_date, variable=ours, ours=bool(r[ours]), lee_cat=r.lee_cat, weather=r.weather, lee_text=r.lee_text))
    same_text = (sub.weather.fillna("").str.replace(r"\s", "", regex=True) == sub.lee_text.fillna("").astype(str).str.replace(r"\s", "", regex=True))
    rows.append(dict(item="same_weather_string", n=int(len(sub)), agree=int(same_text.sum()), rate=float(same_text.mean())))
    pd.DataFrame(rows).to_csv(D / "f_compare_lee.csv", index=False)
    pd.DataFrame(diffs).to_csv(D / "f_compare_lee_diff.csv", index=False)
    print("Lee: matched", len(lm), "diffs", len(diffs))

    # ---------------- F2 routine-entry index
    def runs(flags):
        best = cur = 0; lengths = []
        for f in flags:
            if f:
                cur += 1
            else:
                if cur: lengths.append(cur)
                cur = 0
        if cur: lengths.append(cur)
        return (max(lengths) if lengths else 0, float(np.mean(lengths)) if lengths else 0.0)
    def runs_by_day(g):
        """1.2.1: runs over unique calendar days (duplicate nodes collapsed, a day counts as 晴-only if all its nodes are),
        broken by any calendar gap; 1.2 ran over nodes sorted by JDN, so duplicates could lengthen and gaps could join runs."""
        dd = g[g.jdn_use.notna()].groupby("jdn_use").clear_only.agg(lambda s: bool(len(s)) and bool(s.fillna(False).all())).sort_index()
        best = cur = 0; lengths = []; prev = None
        for j, f in dd.items():
            if prev is not None and j - prev > 1 and cur:
                lengths.append(cur); cur = 0
            if f:
                cur += 1
            else:
                if cur: lengths.append(cur)
                cur = 0
            prev = j
        if cur: lengths.append(cur)
        return (max(lengths) if lengths else 0, float(np.mean(lengths)) if lengths else 0.0)
    d["jdn_use"] = d.jdn_ganji.where(d.jdn_ganji.notna(), d.jdn) if "jdn_ganji" in d else d.jdn
    out = []
    for keys, g in d.sort_values("jdn").groupby(KEYS):
        gw = g[g.kind == "weather"]
        mx, mean_run = runs_by_day(g)
        # rainy season: solar July (Changma) — share of weather days with rain_any
        july = gw[pd.to_datetime(gw.solar_date, errors="coerce").dt.month == 7]
        out.append(dict(zip(KEYS, keys)) | dict(n_days_weather=len(gw), clear_only_share=gw.clear_only.mean(), longest_clear_run=mx, mean_clear_run=mean_run,
                                             july_days=len(july), july_rain_share=july.rain_any.mean() if len(july) else np.nan,
                                             blank_share=(g.kind == "blank").mean()))
    pd.DataFrame(out).sort_values("king_no").to_csv(D / "f_routine.csv", index=False)

    # F2 vs the rain gauge (Lee: gauge_mm > 0 means measured rain that day)
    # Lee's gauge column is filled only on days with a measurement; a blank is a day without measured rain. Both blank and 0
    # count as "no gauge rain" here, so the second rate is the share of gauge-dry days on which the cell still says rain.
    g = lm[lm.kind == "weather"].copy()
    g["half"] = (g.year_ce.astype(int) // 50) * 50
    def gauge_block(period, gg):
        """1.2.1: the 1.2 'false rain' (rain token on days with no gauge amount or 0) mixed two very different sets — days whose
        gauge entry is 0 (flag e: precipitation without measurable depth, almost all with a rain/snow token) and days with no
        gauge entry at all. They are now reported separately, together with any-precipitation recall and the share of Lee's own
        weather string carrying 雨 on measured-rain days (the same gap, so it is a property of the record, not of the token rule)."""
        rainy = gg[gg.gauge_mm > 0]; n = len(rainy)
        k = int(rainy.rain_any.fillna(False).sum()); lo, hi = wilson(k, n)
        kp = int(rainy.precip_any.fillna(False).sum())
        klee = int(rainy.lee_text.astype(str).str.contains("雨").sum())
        dry = gg[~(gg.gauge_mm > 0)]; k2 = int(dry.rain_any.fillna(False).sum()); n2 = len(dry); lo2, hi2 = wilson(k2, n2)
        zero = gg[gg.gauge_mm == 0]; na = gg[gg.gauge_mm.isna()]
        return dict(period=period, gauge_days=len(gg), gauge_rain_days=n, cell_rain_on_gauge_rain=k, recall=k / n if n else np.nan, recall_lo=lo, recall_hi=hi,
                    cell_precip_on_gauge_rain=kp, recall_precip=kp / n if n else np.nan, lee_text_rain_on_gauge_rain=klee, lee_text_rain_share=klee / n if n else np.nan,
                    gauge_dry_days=n2, cell_rain_on_gauge_dry=k2, false_rain=k2 / n2 if n2 else np.nan, false_lo=lo2, false_hi=hi2,
                    gauge_zero_days=len(zero), cell_precip_on_gauge_zero=int(zero.precip_any.fillna(False).sum()), cell_rain_on_gauge_zero=int(zero.rain_any.fillna(False).sum()),
                    gauge_na_days=len(na), cell_rain_on_gauge_na=int(na.rain_any.fillna(False).sum()), cell_precip_on_gauge_na=int(na.precip_any.fillna(False).sum()))
    rg = []
    for h, gg in g.groupby("half"):
        rg.append(gauge_block(f"{h}–{h+49}", gg))
    rg.append(gauge_block("1778–1907", g))
    pd.DataFrame(rg).to_csv(D / "f_rain_gauge.csv", index=False)
    print("rain gauge days", len(g))

    # ---------------- F3 ASOS overlap
    asos = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(str(X / "kma-asos108" / "*.csv")))])
    asos["date"] = asos.tm.astype(str).str[:10]
    am = d[d.solar_date.notna()].merge(asos[["date", "sumRn", "avgTca", "iscs", "ddMes", "ddMefs"]], left_on="solar_date", right_on="date", how="inner")
    am = am[am.kind == "weather"]
    rows = [dict(item="overlap_days", n=int(len(am)), first=am.solar_date.min(), last=am.solar_date.max())]
    obs_rain = (am.sumRn.fillna(0) > 0) | am.iscs.fillna("").str.contains("비")
    obs_snow = am.iscs.fillna("").str.contains("눈")
    obs_clear = am.avgTca.fillna(10) <= 2.5          # mean cloud cover in tenths; "clear" when ≤ 2.5
    obs_cloudy = am.avgTca.fillna(0) >= 7.5
    def agree_row(name, ours, theirs):
        a = am[ours].fillna(False).astype(bool); b = theirs.astype(bool)
        n = len(am); agree = int((a == b).sum()); lo, hi = wilson(agree, n)
        tp = int((a & b).sum()); fn = int((~a & b).sum()); fp = int((a & ~b).sum())
        rec = tp / (tp + fn) if tp + fn else np.nan; prec = tp / (tp + fp) if tp + fp else np.nan
        return dict(item=name, n=n, agree=agree, rate=agree / n, ci_lo=lo, ci_hi=hi, obs_positive=tp + fn, cell_positive=tp + fp, recall=rec, precision=prec)
    rows += [agree_row("rain_any_vs_asos_rain", "rain_any", obs_rain), agree_row("snow_any_vs_asos_snow", "snow_any", obs_snow),
             agree_row("clear_only_vs_asos_cloud_le2.5", "clear_only", obs_clear), agree_row("cloudy_any_vs_asos_cloud_ge7.5", "cloudy_any", obs_cloudy)]
    rows.append(dict(item="asos_snow_depth_columns_empty", n=int(am.ddMes.isna().sum() + am.ddMefs.isna().sum())))
    pd.DataFrame(rows).to_csv(D / "f_asos.csv", index=False)
    print("ASOS overlap", len(am))

    # ---------------- F4 missing (1.2.1: counted on unique calendar days; 1.2 used span − node count, which let duplicate
    # day nodes offset missing days and produced negative values for Yeongjo and Gojong)
    if "jdn_use" not in d:
        d["jdn_use"] = d.jdn_ganji.where(d.jdn_ganji.notna(), d.jdn) if "jdn_ganji" in d else d.jdn
    def missing_block(g):
        j = g.jdn_use.dropna().astype(int)
        span = int(j.max() - j.min() + 1) if len(j) else 0
        uniq = int(j.nunique())
        return dict(calendar_days=span, day_nodes=len(g), unique_days=uniq, duplicate_nodes=int(len(j) - uniq), undated_nodes=int(g.jdn_use.isna().sum()),
                    missing_days=span - uniq, blank_cells=int((g.kind == "blank").sum()), dash_cells=int((g.weather == "-").sum()), note_only=int((g.kind == "note_only").sum()),
                    missing_share=(span - uniq) / span if span else np.nan, blank_share=(g.kind == "blank").mean())
    rows = [dict(zip(KEYS, keys)) | missing_block(g) for keys, g in d.groupby(KEYS)]
    pd.DataFrame(rows).sort_values("king_no").to_csv(D / "f_missing_reign.csv", index=False)
    y = pd.DataFrame([dict(year_ce=int(yr)) | missing_block(g) for yr, g in d.groupby("year_ce")])
    y.to_csv(D / "f_missing_yearly.csv", index=False)
    tot_span = sum(r["calendar_days"] for r in rows)
    print("F4: calendar days", tot_span, "nodes", len(d), "unique days", sum(r["unique_days"] for r in rows), "missing", sum(r["missing_days"] for r in rows),
          "duplicates", sum(r["duplicate_nodes"] for r in rows), "undated", sum(r["undated_nodes"] for r in rows), "blank", int((d.kind == "blank").sum()))

    # reliability snippets for the cards
    rel = {}
    cl = pd.read_csv(D / "f_compare_lyu.csv").set_index("item")
    rel["weather_vs_lyu"] = {r: dict(n=int(cl.loc[r, "n"]), rate=float(cl.loc[r, "rate"])) for r in cl.index if r.startswith("agree_")}
    ce = pd.read_csv(D / "f_compare_lee.csv").set_index("item")
    rel["weather_vs_lee"] = {r: dict(n=int(ce.loc[r, "n"]), rate=float(ce.loc[r, "rate"])) for r in ce.index if r.startswith("agree_")}
    json.dump(rel, open(D / "reliability_f.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
