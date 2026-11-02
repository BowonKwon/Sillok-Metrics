# -*- coding: utf-8 -*-
"""Series G — Record and sky: three sources against the computed sky (1.2).

  python src/metrics_g.py

Inputs
  data/derived/articles.parquet + keyword_hits.parquet            Sillok (1.0 tables; KOGL-4 editions excluded from coding)
  data/derived/articles_ext.parquet + keyword_hits_ext.parquet    Goryeosa 天文志, Goryeosa-jeolyo, Seungjeongwon Ilgi
  data/derived/solar_eclipses_sites.csv, lunar_eclipses_sites.csv, venus_inferior_conjunctions_918_1910.csv  (astro_ext.py)
  data/coding/solar_eclipse_v2_coded_*.jsonl, lunar_eclipse_coded_*.jsonl, comet/appulse/meteor _coded_sjw.jsonl (if present)
  data/raw/external/jpl-sbdb/comets_tp_before_1911_*.json        JPL SBDB comets with perihelion before 1911 (not published)

Outputs data/derived/g_*.csv
  g1_solar, g1_solar_articles        G1 typed solar-eclipse articles vs eclipses visible at the source's observing site
  g2_lunar, g2_lunar_articles        G2 same for lunar eclipses
  g3_venus, g3_appulse, g3_appulse_articles   G3 Venus-daytime phase test; angular separation on 犯 dates for named pairs
  g4_comet, g4_comet_articles        G4 comet/guest-star identification against JPL perihelia with a random-date control
  g5_sunspot, g5_sunspot_articles    G5 naked-eye sunspot chronology (counts only); aurora candidates as a footnote count
  g6_overlap                         G6 same-event reporting between sources
  g_coding_agreement.json            type distributions, v1→v2 crosstab, blind agreement where available
Observing site: gaeseong for the two Goryeo sources, seoul for the Joseon sources. Dates: jdn_ganji where the day table
flagged a month shift, else jdn. Window ±1 day everywhere (calendar conversion uncertainty); ±0 is reported alongside.
"""
import glob
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "derived"
C = ROOT / "data" / "coding"
X = ROOT / "data" / "raw" / "external"
SITE = {"sillok": "seoul", "sjw": "seoul", "goryeosa": "gaeseong", "goryeosa_jeolyo": "gaeseong"}
SEED = 20261102


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def read_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def load_articles():
    a = pd.read_parquet(D / "articles.parquet")
    a = a[a.license == "KOGL-1"].copy()
    a["source"] = "sillok"; a["observer_site"] = "seoul"; a["jdn_ganji"] = a.jdn; a["date_flag"] = ""
    e = pd.read_parquet(D / "articles_ext.parquet")
    cols = ["article_id", "source", "edition", "king_no", "king_ko", "year_ce", "lunar_month", "lunar_day", "is_leap", "solar_date", "jdn", "jdn_ganji", "observer_site", "date_flag", "nikh_url", "title"]
    for c in cols:
        if c not in e: e[c] = None
        if c not in a: a[c] = None
    A = pd.concat([a[cols], e[cols]], ignore_index=True)
    A["jdn_use"] = A.jdn_ganji.where(A.jdn_ganji.notna(), A.jdn)
    k1 = pd.read_parquet(D / "keyword_hits.parquet"); k2 = pd.read_parquet(D / "keyword_hits_ext.parquet")
    ks = [k1[["article_id", "pattern", "n_hits"]], k2[["article_id", "pattern", "n_hits"]]]
    if (D / "keyword_hits_sillok_ext.parquet").exists():   # 1.2.1: sunspot / guest_star counted in the Sillok too (extract_keywords_sillok_ext.py)
        ks.append(pd.read_parquet(D / "keyword_hits_sillok_ext.parquet")[["article_id", "pattern", "n_hits"]])
    K = pd.concat(ks, ignore_index=True)
    return A.set_index("article_id"), K


def load_rules():
    p = C / "overrides.json"
    return json.load(open(p, encoding="utf-8")).get("rules", []) if p.exists() else []


def apply_rules(df, bundle):
    """Editor rules from overrides.json (1.2.1): rows whose quote/summary match the regex get type=set_type; the coder's
    type is kept in type_coder and the rule name in rule. Coder files are untouched."""
    if len(df) == 0:
        return df
    df = df.copy(); df["type_coder"] = df["type"]; df["rule"] = ""
    for r in load_rules():
        if bundle not in r["bundles"]:
            continue
        pat = re.compile(r["regex"]) if r.get("regex") else None
        hit = (df["quote"].fillna("") + " " + df["summary"].fillna("")).map(lambda s: bool(pat.search(s))) if pat else pd.Series(False, index=df.index)
        ids = r.get("article_ids", {})          # 1.2.2: explicit ids per bundle, for wording the regex misses (今纔出來, 尙不出來 ...)
        ids = ids.get(bundle, []) if isinstance(ids, dict) else ids
        aid = df["article_id"] if "article_id" in df.columns else pd.Series(df.index, index=df.index)
        hit = hit | aid.isin(ids)
        if r.get("from_types"):                 # 1.2.2: only rows whose coder type is in the list (e.g. forecast -> ritual for 齋戒)
            hit = hit & df["type_coder"].isin(r["from_types"])
        hit = hit & ~aid.isin(r.get("exclude_ids", [])) & (df["type"] != r["set_type"])
        df.loc[hit, "type"] = r["set_type"]; df.loc[hit, "rule"] = r["name"]
    return df


def load_coded(prefix):
    rows = []
    for p in sorted(glob.glob(str(C / f"{prefix}*.jsonl"))):
        name = Path(p).stem
        if "blind" in name:
            continue
        src = "sillok" if "sillok" in name else ("goryeosa_jeolyo" if "jeolyo" in name else ("sjw" if "sjw" in name else "goryeo"))
        for r in read_jsonl(p):
            r["coded_file"] = name; r["src_hint"] = src; rows.append(r)
    return apply_rules(pd.DataFrame(rows), "solar" if prefix.startswith("solar") else "lunar")


def match_table(cod, A, ecl, kind):
    """cod: coded rows with article_id,type,boundary. ecl: eclipse table with {site}_visible and {site}_max_jdn_lmt, earthwide (solar)."""
    rows = []
    cod = cod.merge(A[["source", "observer_site", "jdn_use", "jdn", "solar_date", "year_ce", "king_ko", "nikh_url"]], left_on="article_id", right_index=True, how="left")
    vis = {}
    for site in ("seoul", "gaeseong"):
        vis[site] = set(ecl.loc[ecl[f"{site}_visible"] == True, f"{site}_max_jdn_lmt"].dropna().astype(int))  # noqa: E712
    ew = set(ecl.loc[ecl.earthwide == True, "seoul_max_jdn_lmt"].dropna().astype(int)) if "earthwide" in ecl else set()  # noqa: E712
    allj = set(ecl["seoul_max_jdn_lmt"].dropna().astype(int)) | set(ecl["gaeseong_max_jdn_lmt"].dropna().astype(int))
    def near(j, S, w):
        return any((j + k) in S for k in range(-w, w + 1))
    out = []
    for _, r in cod.iterrows():
        j = r.jdn_use
        site = r.observer_site if isinstance(r.observer_site, str) else "seoul"
        rec = dict(article_id=r.article_id, source=r.source, type=r.type, boundary=r.get("boundary", ""), site=site, solar_date=r.solar_date, year_ce=r.year_ce, king_ko=r.king_ko)
        if j == j and j is not None:
            j = int(j)
            rec.update(match_pm1=near(j, vis[site], 1), match_pm0=near(j, vis[site], 0), any_eclipse_pm1=near(j, allj, 1), earthwide_pm1=near(j, ew, 1) if ew else None, dated=True)
        else:
            rec.update(match_pm1=None, match_pm0=None, any_eclipse_pm1=None, earthwide_pm1=None, dated=False)
        out.append(rec)
    art = pd.DataFrame(out)
    summ = []
    for (src, typ), g in art.groupby(["source", "type"]):
        gd = g[g.dated == True]  # noqa: E712
        n = len(gd); k1 = int(gd.match_pm1.sum()); k0 = int(gd.match_pm0.sum()); lo, hi = wilson(k1, n)
        summ.append(dict(source=src, type=typ, n_articles=len(g), n_dated=n, match_pm1=k1, rate_pm1=k1 / n if n else np.nan, ci_lo=lo, ci_hi=hi,
                         match_pm0=k0, rate_pm0=k0 / n if n else np.nan, any_eclipse_pm1=int(gd.any_eclipse_pm1.sum()),
                         earthwide_pm1=int(gd.earthwide_pm1.fillna(False).sum()) if gd.earthwide_pm1.notna().any() else None))
    # day-level for the Ilgi: a day counts as observed if any article that day is observed
    for src in art.source.dropna().unique():
        g = art[(art.source == src) & (art.type == "observed") & (art.dated == True)]  # noqa: E712
        days = g.groupby("solar_date").match_pm1.max()
        n = len(days); k = int(days.sum()); lo, hi = wilson(k, n)
        summ.append(dict(source=src, type="observed (day level)", n_articles=len(g), n_dated=n, match_pm1=k, rate_pm1=k / n if n else np.nan, ci_lo=lo, ci_hi=hi))
    return pd.DataFrame(summ), art


def g3_venus(A, K):
    from skyfield import api
    load = api.Loader(str(ROOT / "data" / "raw" / "eph"), verbose=False); ts = load.timescale(); eph = load("de406.bsp")
    earth, sun, venus = eph["earth"], eph["sun"], eph["venus"]
    ids = K[K.pattern == "venus_daytime"].article_id.unique()
    a = A.loc[A.index.intersection(ids)]
    a = a[a.jdn_use.notna()]
    rows = []; arts = []; ctrl_rows = []
    rng = random.Random(SEED)
    for src, g in a.groupby("source"):
        jd = g.jdn_use.astype(int).values - 127 / 360   # local mean noon at 127°E (integer JDN = noon UT; 1.2 had +0.5, i.e. 00h of the next day — fixed in 1.2.1)
        t = ts.ut1_jd(jd)
        e = earth.at(t)
        el = e.observe(sun).apparent().separation_from(e.observe(venus).apparent()).degrees
        # elongation sign: Venus east (evening) or west (morning) of the Sun — via ecliptic longitude difference
        from skyfield.framelib import ecliptic_frame
        lon_v = e.observe(venus).apparent().frame_latlon(ecliptic_frame)[1].degrees; lon_s = e.observe(sun).apparent().frame_latlon(ecliptic_frame)[1].degrees
        east = ((lon_v - lon_s) % 360) < 180
        # control: random days in the same span
        lo, hi = int(g.jdn_use.min()), int(g.jdn_use.max())
        rj_jdn = np.array([rng.randint(lo, hi) for _ in range(2000)]); rj = rj_jdn - 127 / 360
        er = earth.at(ts.ut1_jd(rj)); elr = er.observe(sun).apparent().separation_from(er.observe(venus).apparent()).degrees
        for aid, sd, j, e_, ev in zip(g.index, g.solar_date, g.jdn_use.astype(int), el, east):
            arts.append(dict(article_id=aid, source=src, solar_date=sd, jdn=int(j), elongation_deg=float(e_), evening=bool(ev)))
        for j, e_ in zip(rj_jdn, elr):
            ctrl_rows.append(dict(source=src, jdn=int(j), elongation_deg=float(e_)))
        rows.append(dict(source=src, n_dated=len(g), median_elongation=float(np.median(el)), share_elong_ge30=float((el >= 30).mean()), share_elong_ge40=float((el >= 40).mean()),
                         share_evening=float(east.mean()), control_median_elongation=float(np.median(elr)), control_share_ge30=float((elr >= 30).mean()), control_share_ge40=float((elr >= 40).mean())))
    return pd.DataFrame(rows), pd.DataFrame(arts), pd.DataFrame(ctrl_rows)


STARS = {  # J2000 RA (h), Dec (deg): bright stars that appear in 犯 reports under their Chinese names
    "畢大星": (4.5987, 16.509), "心大星": (16.4901, -26.432), "軒轅大星": (10.1395, 11.967), "角": (13.4199, -11.161), "大角": (14.2610, 19.182),
    "北河": (7.7553, 28.026), "南河": (7.6550, 5.225), "天關": (5.6275, 21.143), "五車": (5.2782, 45.998), "建星": (18.9210, -26.297),
    "牛": (20.2946, -12.508), "房": (16.0056, -22.622), "鉤鈐": (16.0056, -22.622), "太微": None, "井": (6.6286, 16.399), "鬼": (8.7447, 21.469), "氐": (14.8480, -16.042),
}
PLANETS = {"太白": "venus", "歲星": "jupiter barycenter", "熒惑": "mars", "鎭星": "saturn barycenter", "填星": "saturn barycenter", "辰星": "mercury"}
PAIR_RE = re.compile("(月|太白|歲星|熒惑|鎭星|填星|辰星)(?:犯|掩|入)(" + "|".join(sorted([k for k in list(STARS) + list(PLANETS) if STARS.get(k, 1) is not None], key=len, reverse=True)) + ")")


def g3_appulse(A, K):
    from skyfield import api
    from skyfield.api import Star
    load = api.Loader(str(ROOT / "data" / "raw" / "eph"), verbose=False); ts = load.timescale(); eph = load("de406.bsp")
    earth, sun, moon = eph["earth"], eph["sun"], eph["moon"]
    # titles carry the pair for Goryeosa (NIKH Korean title) but not the hanja; use keyword context from keyword_hits_ext/keyword_hits instead
    k2 = pd.read_parquet(D / "keyword_hits_ext.parquet"); k1 = pd.read_parquet(D / "keyword_hits.parquet")
    ctx = pd.concat([k1[k1.pattern == "appulse"][["article_id", "context"]], k2[k2.pattern == "appulse"][["article_id", "context"]]])
    rows = []
    for _, r in ctx.iterrows():
        if r.article_id not in A.index:
            continue
        m = PAIR_RE.search(str(r.context))
        if not m:
            continue
        a = A.loc[r.article_id]
        if a.jdn_use != a.jdn_use or a.jdn_use is None:
            continue
        rows.append(dict(article_id=r.article_id, source=a.source, solar_date=a.solar_date, jdn=int(a.jdn_use), body=m.group(1), target=m.group(2)))
    P = pd.DataFrame(rows)
    if P.empty:
        return pd.DataFrame(), P
    P.attrs["n_appulse_articles"] = int(ctx.article_id.isin(A.index).sum())
    seps = []
    for _, r in P.iterrows():
        # sample the night of that civil date (local 18h to next 6h) every 30 min; minimum separation
        jd0 = r.jdn + 0.25 - 127 / 360   # 18:00 local mean time of the civil date (1.2 had +0.75, i.e. 06:00 of the next day — fixed in 1.2.1)
        t = ts.ut1_jd(jd0 + np.arange(0, 0.5001, 1 / 48))
        obs = earth.at(t)
        b = obs.observe(moon if r.body == "月" else eph[PLANETS[r.body]]).apparent()
        if r.target in PLANETS:
            tg = obs.observe(eph[PLANETS[r.target]]).apparent()
        else:
            ra, dec = STARS[r.target]; tg = obs.observe(Star(ra_hours=ra, dec_degrees=dec)).apparent()
        s = b.separation_from(tg).degrees
        # ±1 day: the same night window on the previous and next civil dates (calendar-conversion uncertainty)
        t3 = ts.ut1_jd(np.concatenate([jd0 - 1 + np.arange(0, 0.5001, 1 / 48), jd0 + 1 + np.arange(0, 0.5001, 1 / 48)]))
        o3 = earth.at(t3)
        b3 = o3.observe(moon if r.body == "月" else eph[PLANETS[r.body]]).apparent()
        tg3 = o3.observe(eph[PLANETS[r.target]]).apparent() if r.target in PLANETS else o3.observe(Star(ra_hours=STARS[r.target][0], dec_degrees=STARS[r.target][1])).apparent()
        seps.append((float(s.min()), float(min(s.min(), b3.separation_from(tg3).degrees.min()))))
    P["min_sep_deg"] = [x[0] for x in seps]; P["min_sep_pm1_deg"] = [x[1] for x in seps]
    summ = []
    for src, g in P.groupby("source"):
        summ.append(dict(source=src, n_pairs=len(g), moon_pairs=int((g.body == "月").sum()), median_sep=float(g.min_sep_deg.median()), share_le1_5=float((g.min_sep_deg <= 1.5).mean()),
                         share_le5=float((g.min_sep_deg <= 5).mean()), share_le10=float((g.min_sep_deg <= 10).mean()),
                         median_sep_pm1=float(g.min_sep_pm1_deg.median()), share_le1_5_pm1=float((g.min_sep_pm1_deg <= 1.5).mean()), share_le5_pm1=float((g.min_sep_pm1_deg <= 5).mean())))
    # control: same pairs on random dates
    rng = random.Random(SEED); ctrl = []; ctrl_rows = []
    for _, r in P.sample(min(400, len(P)), random_state=SEED).iterrows():
        j = rng.randint(int(P.jdn.min()), int(P.jdn.max()))
        t = ts.ut1_jd(j + 0.25 - 127 / 360 + np.arange(0, 0.5001, 1 / 48)); obs = earth.at(t)
        b = obs.observe(moon if r.body == "月" else eph[PLANETS[r.body]]).apparent()
        tg = obs.observe(eph[PLANETS[r.target]]).apparent() if r.target in PLANETS else obs.observe(Star(ra_hours=STARS[r.target][0], dec_degrees=STARS[r.target][1])).apparent()
        ctrl.append(float(b.separation_from(tg).degrees.min())); ctrl_rows.append(dict(body=r.body, target=r.target, jdn=int(j), min_sep_deg=ctrl[-1]))
    ctrl = np.array(ctrl)
    summ.append(dict(source="control (random dates, same pairs)", n_pairs=len(ctrl), median_sep=float(np.median(ctrl)), share_le1_5=float((ctrl <= 1.5).mean()), share_le5=float((ctrl <= 5).mean()), share_le10=float((ctrl <= 10).mean())))
    return pd.DataFrame(summ), P, pd.DataFrame(ctrl_rows)


def g4_comet(A, K):
    f = sorted(glob.glob(str(X / "jpl-sbdb" / "comets_tp_before_1911_*.json")))[-1]
    d = json.load(open(f, encoding="utf-8")); fields = d["fields"]
    J = pd.DataFrame(d["data"], columns=fields); J["tp"] = pd.to_numeric(J.tp, errors="coerce"); J = J[J.tp.notna()]
    tps = np.sort(J.tp.values)
    def ident(jdn, w=90):
        i = np.searchsorted(tps, jdn)
        cands = [tps[k] for k in (i - 1, i) if 0 <= k < len(tps)]
        return any(abs(jdn - c) <= w for c in cands)
    sets = {}
    ids = K[K.pattern == "comet"].article_id.unique()
    a = A.loc[A.index.intersection(ids)]; a = a[a.jdn_use.notna()]
    for src, g in a.groupby("source"):
        sets[f"{src}: all comet-keyword articles"] = g
    # Sillok 1.0 precision sample: coded observation reports
    try:
        pc = pd.DataFrame(read_jsonl(C / "comet_coded.jsonl"))
        ov = json.load(open(C / "overrides.json", encoding="utf-8")).get("overrides", {}).get("comet", {}) if (C / "overrides.json").exists() else {}
        pc["relevant_final"] = [ov.get(i, r) for i, r in zip(pc.article_id, pc.relevant)]   # 1.2.2: the published final judgment (1.2.1 used the coder column only: 64 instead of 69)
        yes = pc[pc.relevant_final == "yes"].article_id
        sets["sillok: precision-sample observation reports"] = a.loc[a.index.intersection(yes)]
    except FileNotFoundError:
        pass
    # Ilgi sample coded in 1.2 (if present)
    p = C / "comet_coded_sjw.jsonl"
    if p.exists():
        pc = pd.DataFrame(read_jsonl(p)); yes = pc[pc.relevant == "yes"].article_id
        sets["sjw: sample observation reports"] = a.loc[a.index.intersection(yes)]
    rng = random.Random(SEED); rows = []; arts = []
    for name, g in sets.items():
        if len(g) == 0:
            continue
        jd = g.jdn_use.astype(int).values
        hit = np.array([ident(j) for j in jd]); k = int(hit.sum()); n = len(jd); lo, hi = wilson(k, n)
        span_lo, span_hi = int(jd.min()), int(jd.max())
        ctrl = []
        for _ in range(1000):
            rj = [rng.randint(span_lo, span_hi) for _ in range(n)]
            ctrl.append(np.mean([ident(j) for j in rj]))
        ctrl = np.array(ctrl)
        rows.append(dict(set=name, n=n, identified_pm90=k, rate=k / n, ci_lo=lo, ci_hi=hi, control_mean=float(ctrl.mean()), control_p025=float(np.quantile(ctrl, .025)), control_p975=float(np.quantile(ctrl, .975)),
                         excess=k / n - float(ctrl.mean())))
        for aid, j, h in zip(g.index, jd, hit):
            arts.append(dict(set=name, article_id=aid, source=g.loc[aid, "source"], solar_date=g.loc[aid, "solar_date"], identified_pm90=bool(h)))
    return pd.DataFrame(rows), pd.DataFrame(arts), len(J)


def main():
    A, K = load_articles()
    agreement = {}
    # ---------------- G1 solar
    sol = load_coded("solar_eclipse_v2_coded_")
    se = pd.read_csv(D / "solar_eclipses_sites.csv")
    if len(sol):
        s1, a1 = match_table(sol, A, se, "solar")
        s1.to_csv(D / "g1_solar.csv", index=False); a1.to_csv(D / "g1_solar_articles.csv", index=False)
        agreement["solar_v2_types"] = {src: dict(Counter(g.type)) for src, g in a1.groupby("source")}
        try:
            v1 = pd.read_csv(C / "solar_eclipse_types.csv").set_index("article_id").type
            s = a1[a1.source == "sillok"].set_index("article_id")
            ct = Counter((v1.get(i), t) for i, t in s.type.items())
            agreement["solar_sillok_v1_to_v2"] = {f"{k[0]}->{k[1]}": v for k, v in ct.items()}
            agreement["solar_sillok_v1_v2_same"] = sum(v for (x, y), v in ct.items() if x == y) / len(s)
        except FileNotFoundError:
            pass
        print("G1", s1[s1.type == "observed"][["source", "n_dated", "match_pm1", "rate_pm1"]].to_string(index=False))
    # ---------------- G2 lunar
    lun = load_coded("lunar_eclipse_coded_")
    le = pd.read_csv(D / "lunar_eclipses_sites.csv")
    if len(lun):
        s2, a2 = match_table(lun, A, le, "lunar")
        s2.to_csv(D / "g2_lunar.csv", index=False); a2.to_csv(D / "g2_lunar_articles.csv", index=False)
        agreement["lunar_types"] = {src: dict(Counter(g.type)) for src, g in a2.groupby("source")}
        print("G2", s2[s2.type == "observed"][["source", "n_dated", "match_pm1", "rate_pm1"]].to_string(index=False))
    # ---------------- G3
    gv, gva, gvc = g3_venus(A, K); gv.to_csv(D / "g3_venus.csv", index=False); gva.to_csv(D / "g3_venus_articles.csv", index=False); gvc.to_csv(D / "g3_venus_control.csv", index=False)
    print("G3 venus\n", gv.to_string(index=False))
    ga, gap, gac = g3_appulse(A, K); ga.to_csv(D / "g3_appulse.csv", index=False); gap.to_csv(D / "g3_appulse_articles.csv", index=False); gac.to_csv(D / "g3_appulse_control.csv", index=False)
    print("G3 appulse\n", ga.to_string(index=False) if len(ga) else "none")
    # ---------------- G4
    g4, g4a, ncomets = g4_comet(A, K); g4.to_csv(D / "g4_comet.csv", index=False); g4a.to_csv(D / "g4_comet_articles.csv", index=False)
    print("G4 (JPL comets", ncomets, ")\n", g4[["set", "n", "identified_pm90", "rate", "control_mean", "control_p975"]].to_string(index=False))
    # ---------------- G5
    ids = K[K.pattern == "sunspot"].article_id.unique(); s5 = A.loc[A.index.intersection(ids)].reset_index()
    s5 = s5[["article_id", "source", "solar_date", "year_ce", "king_ko", "nikh_url"]].sort_values(["year_ce", "source"])
    s5.to_csv(D / "g5_sunspot_articles.csv", index=False)
    s5["half"] = (s5.year_ce // 50 * 50).astype("Int64")
    t5 = s5.pivot_table(index="half", columns="source", values="article_id", aggfunc="count", fill_value=0).reset_index()
    t5["period"] = t5.half.astype(str) + "–" + (t5.half + 49).astype(str)
    au = K[K.pattern == "aurora_cand"].article_id.unique(); au = A.loc[A.index.intersection(au)]
    t5.to_csv(D / "g5_sunspot.csv", index=False)
    agreement["aurora_candidate_articles"] = {src: int(n) for src, n in au.groupby("source").size().items()}
    print("G5 sunspot articles", len(s5), dict(s5.groupby("source").size()))
    # ---------------- G6 overlap (keyword-day level + observed-coded where available)
    def days(src, pattern, coded=None):
        ids = K[K.pattern == pattern].article_id.unique()
        g = A.loc[A.index.intersection(ids)]; g = g[(g.source == src) & g.jdn_use.notna()]
        if coded is not None:
            obs = set(coded[(coded.source == src) & (coded.type == "observed")].article_id)
            g = g.loc[g.index.intersection(obs)]
        return set(g.jdn_use.astype(int))
    def overlap(S1, S2, w=1):
        if not S1: return (0, 0, np.nan)
        k = sum(any((j + d) in S2 for d in range(-w, w + 1)) for j in S1); return (len(S1), k, k / len(S1))
    rows = []
    for pattern in ("solar_eclipse", "lunar_eclipse", "comet"):
        coded = a1 if (pattern == "solar_eclipse" and len(sol)) else (a2 if (pattern == "lunar_eclipse" and len(lun)) else None)
        for lab, (s1_, s2_) in {"goryeosa→jeolyo": ("goryeosa", "goryeosa_jeolyo"), "jeolyo→goryeosa": ("goryeosa_jeolyo", "goryeosa"), "sillok→sjw (1623–1863)": ("sillok", "sjw"), "sjw→sillok (1623–1863)": ("sjw", "sillok")}.items():
            S1, S2 = days(s1_, pattern, coded), days(s2_, pattern, coded)
            if "1623" in lab:
                lo, hi = 2313849, 2401871   # JDN of 1623-01-01 and 1863-12-31 (Gregorian); 1.2 used 2313900..2401900 (1623-02-21..1864-01-29), same counts
                S1 = {j for j in S1 if lo <= j <= hi}; S2 = {j for j in S2 if lo <= j <= hi}
            n, k, r = overlap(S1, S2)
            rows.append(dict(phenomenon=pattern, direction=lab, basis="observed-coded days" if coded is not None else "keyword days", n_days=n, also_in_other=k, share=r))
    pd.DataFrame(rows).to_csv(D / "g6_overlap.csv", index=False)
    print("G6\n", pd.DataFrame(rows).to_string(index=False))
    blind_pairs = []
    def kappa(a, b):
        n = len(a); po = sum(x == y for x, y in zip(a, b)) / n; ca, cb = Counter(a), Counter(b)
        pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n); return ((po - pe) / (1 - pe) if pe < 1 else 1.0), po
    for name, main_df, blind_file in (("solar_v2", sol if len(sol) else None, "solar_eclipse_v2_coded_blind150.jsonl"), ("lunar", lun if len(lun) else None, "lunar_eclipse_coded_blind150.jsonl")):
        p = C / blind_file
        if main_df is None or not p.exists():
            continue
        bdf = apply_rules(pd.DataFrame(read_jsonl(p)), "solar" if name.startswith("solar") else "lunar").set_index("article_id")
        m = main_df[~main_df.coded_file.str.contains("blind")].drop_duplicates("article_id").set_index("article_id")
        ids = [i for i in bdf.index if i in m.index]
        if not ids:
            continue
        pool = lambda x: "observation" if x == "observed" else ("other" if x == "other" else "not_observation")
        res = {}
        for tag, col in (("coder", "type_coder"), ("after_rule", "type")):
            a1_, b1_ = [m.loc[i, col] for i in ids], [bdf.loc[i, col] for i in ids]
            k, po = kappa(a1_, b1_); kp, pop = kappa([pool(x) for x in a1_], [pool(x) for x in b1_])
            res[tag] = dict(n=len(ids), agreement=po, kappa=k, agreement_pooled=pop, kappa_pooled=kp)
        agreement[f"{name}_blind"] = dict(res["coder"], after_rule=res["after_rule"])
        print(name, "blind n", len(ids), "coder: agreement %.3f kappa %.3f pooled %.3f" % (res["coder"]["agreement"], res["coder"]["kappa"], res["coder"]["kappa_pooled"]),
              "| after rule: %.3f %.3f %.3f" % (res["after_rule"]["agreement"], res["after_rule"]["kappa"], res["after_rule"]["kappa_pooled"]))
        for i in ids:
            blind_pairs.append(dict(bundle=name, article_id=i, type_main_coder=m.loc[i, "type_coder"], type_blind_coder=bdf.loc[i, "type_coder"], type_main=m.loc[i, "type"], type_blind=bdf.loc[i, "type"], main_coder=m.loc[i, "coded_file"]))
    for name, df_ in (("solar_v2", sol), ("lunar", lun)):
        if len(df_):
            agreement[f"{name}_rule_changes"] = {k: int(v) for k, v in Counter(f"{a}->{b}" for a, b, r_ in zip(df_.type_coder, df_.type, df_.rule) if r_).items()}
    gs = K[K.pattern == "guest_star"].article_id.unique(); gs = A.loc[A.index.intersection(gs)]; gs = gs[gs.source == "sillok"]
    if len(gs):
        se_ = gs[gs.king_no == 14]
        agreement["guest_star_sillok"] = dict(all=int(len(gs)), seonjo=int(len(se_)), seonjo_1604_1605=int(se_.year_ce.isin([1604, 1605]).sum()), y1604=int((gs.year_ce == 1604).sum()))
        print("guest star (Sillok)", agreement["guest_star_sillok"])
    if len(ga):
        agreement["appulse_pairs_parsed"] = dict(parsed=int(len(gap)), of_articles=int(gap.attrs.get("n_appulse_articles", 0)))
    json.dump(agreement, open(D / "g_coding_agreement.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # publishable coding tables (all 1.2 sources are KOGL-1 or unrestricted; Sillok rows are Taejo–Cheoljong only)
    cols = ["article_id", "source", "type", "type_coder", "rule", "boundary", "time_text", "magnitude_text", "not_seen_reason", "summary", "quote", "coder"]
    if len(sol):
        s = sol.copy(); s["source"] = s.article_id.map(A.source); s["coder"] = s.coded_file
        s[cols].to_csv(C / "solar_eclipse_types_v2.csv", index=False, encoding="utf-8")
    if len(lun):
        s = lun.copy(); s["source"] = s.article_id.map(A.source); s["coder"] = s.coded_file
        s[cols].to_csv(C / "lunar_eclipse_types.csv", index=False, encoding="utf-8")
    rows = []
    for b in ("comet", "appulse", "meteor"):
        p = C / f"{b}_coded_sjw.jsonl"
        if p.exists():
            for r in read_jsonl(p):
                rows.append(dict(bundle=b, **{k: r.get(k, "") for k in ("article_id", "relevant", "reason", "quote")}))
    if rows:
        pd.DataFrame(rows).to_csv(C / "precision_sjw_samples.csv", index=False, encoding="utf-8")
    v2 = [r for f in sorted(glob.glob(str(C / "slaves_v2_coded_[0-9].jsonl"))) for r in read_jsonl(f)]
    if v2:
        pd.DataFrame(v2)[["article_id", "relevant", "reason", "quote"]].to_csv(C / "slaves_v2_judgements.csv", index=False, encoding="utf-8")
    # 1.2.1: blind pairs (solar v2, lunar, slaves v2) and the 1.0 precision samples (Taejo–Cheoljong only) so that κ and v1 values can be re-derived
    pb = C / "slaves_v2_coded_blind30.jsonl"
    if v2 and pb.exists():
        mv = {r["article_id"]: r["relevant"] for r in v2}
        for r in read_jsonl(pb):
            if r["article_id"] in mv:
                blind_pairs.append(dict(bundle="slaves_v2", article_id=r["article_id"], type_main_coder=mv[r["article_id"]], type_blind_coder=r["relevant"], type_main=mv[r["article_id"]], type_blind=r["relevant"], main_coder=""))
    if blind_pairs:
        pd.DataFrame(blind_pairs).to_csv(C / "blind_recoding_pairs.csv", index=False, encoding="utf-8")
    ov = json.load(open(C / "overrides.json", encoding="utf-8")).get("overrides", {}) if (C / "overrides.json").exists() else {}
    rows = []
    for b in ("comet", "slaves", "earthquake", "relief", "royal_lecture", "summer_cold"):
        p = C / f"{b}_coded.jsonl"
        if p.exists():
            for r in read_jsonl(p):
                if r["article_id"][:3] in ("wza", "wzb", "wzc"):
                    continue
                rel = ov.get(b, {}).get(r["article_id"], r.get("relevant", ""))
                rows.append(dict(bundle=("slaves_v1" if b == "slaves" else b), article_id=r["article_id"], relevant=rel, relevant_coder=r.get("relevant", ""), reason=r.get("reason", ""), quote=r.get("quote", "")))
    if rows:
        pd.DataFrame(rows).to_csv(C / "precision_sillok_samples.csv", index=False, encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
