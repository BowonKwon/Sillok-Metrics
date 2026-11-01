# -*- coding: utf-8 -*-
"""Series D — politics and appointments.

  python src/metrics_d.py

D1 clan concentration: first appointments to high office from the NIKH office table
   (data/raw/nikh-2026-joseon-sillok-persons.zip), clan seat from the person table, gaps filled from
   the AKS civil-examination roster (data/raw/aks-2020-joseon-munkwa-geupjeja.xml).
   Same rules as the 2026-09 analysis: office title judged on its Korean form (the Hanja form has
   typos), form == 현직, first year 1392–1910; roster match = same Hanja name, pass year ≤ first
   appointment ≤ pass year + 60, birth year if both known, unique clan among candidates.
D2 royal lecture, D3 memorials, D4 justice classes: shares per reign from keyword hits / subjects.
Outputs: d_clan.csv, d_clan_munkwa.csv, d_clan_fill.json, d_lecture.csv, d_memorial.csv, d_justice.csv, d_justice_decade.csv
"""
import collections
import csv
import io
import json
import random
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "derived"
RAWP = ROOT / "data" / "raw" / "nikh-2026-joseon-sillok-persons.zip"
RAWB = ROOT / "data" / "raw" / "aks-2020-joseon-munkwa-geupjeja.xml"
HI = re.compile(r"영의정|좌의정|우의정|판서|참판|대사헌|대사간|도승지|관찰사|대제학")
BINS = [(1392, 1450), (1450, 1500), (1500, 1550), (1550, 1600), (1600, 1650), (1650, 1700), (1700, 1750), (1750, 1800), (1800, 1850), (1850, 1911)]
SEED = 20261101


def read_csv_zip(name_part):
    z = zipfile.ZipFile(RAWP, metadata_encoding="cp949")
    for i in z.infolist():
        if i.filename.rsplit("_", 1)[-1][:-4] == name_part:
            raw = z.read(i)
            try:
                txt = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                txt = raw.decode("cp949", "replace")
            return list(csv.DictReader(io.StringIO(txt)))
    raise FileNotFoundError(name_part)


def stats(clans):
    cnt = collections.Counter(clans)
    n = len(clans)
    sh = np.array(sorted(cnt.values(), reverse=True)) / n
    return dict(n=n, n_clans=len(cnt), top10_share=float(sh[:10].sum()), hhi=float((sh ** 2).sum()), effective_clans=float(1 / (sh ** 2).sum()))


def main():
    office = read_csv_zip("관직")
    person = {r["인물아이디"]: r for r in read_csv_zip("인물")}
    first = {}
    for r in office:
        title = (r.get("관력") or "").split("(")[0]
        y = r.get("년") or ""
        if r.get("형태") != "현직" or not HI.search(title) or not y.isdigit():
            continue
        y = int(y)
        pid = r["인물아이디"]
        if 1392 <= y <= 1910 and (pid not in first or y < first[pid]):
            first[pid] = y
    # roster
    hanja = lambda s: (re.search(r"\(([^)]+)\)", s or "") or [None, ""])[1]
    def normbg(s):
        s = re.sub(r"\[[^\]]*\]", "", s or "").strip()
        return "" if "未詳" in s else s
    root = ET.parse(RAWB).getroot()
    BM = []
    for g in root.findall("급제자"):
        f = {e.tag: (e.text or "").strip() for e in g}
        BM.append(dict(name=hanja(f.get("급제자")), year=int(f["시험년"]) if f.get("시험년", "").isdigit() else None,
                       birth=f.get("생년") if f.get("생년", "").isdigit() else None, bg=normbg(hanja(f.get("본관")))))
    byname = collections.defaultdict(list)
    for b in BM:
        if b["name"]:
            byname[b["name"]].append(b)

    def match(p, y):
        cands = [b for b in byname.get(p["name"], []) if b["year"] and b["year"] <= y and y - b["year"] <= 60]
        if p["birth"].isdigit():
            c2 = [b for b in cands if b["birth"] == p["birth"]]
            if c2:
                cands = c2
        bgs = set(b["bg"] for b in cands if b["bg"])
        return (bgs.pop() if len(bgs) == 1 else None), len(cands)

    P = {k: dict(name=(v.get("한자_명") or "").lstrip("﻿"), sur=v.get("한자_성") or "", bg=v.get("한자_본관") or "", birth=v.get("생년") or "") for k, v in person.items()}
    ok = bad = nomatch = amb = 0
    for pid, y in first.items():
        p = P.get(pid)
        if not p or not p["bg"] or not p["sur"]:
            continue
        bg, n = match(p, y)
        if n == 0: nomatch += 1
        elif bg is None: amb += 1
        elif bg == p["bg"]: ok += 1
        else: bad += 1
    clans = collections.defaultdict(list); tot = collections.Counter(); miss = collections.Counter(); miss0 = collections.Counter()
    src = collections.Counter()
    for pid, y in first.items():
        b = next(b for b in BINS if b[0] <= y < b[1]); tot[b] += 1
        p = P.get(pid)
        if p and p["bg"] and p["sur"]:
            clans[b].append(p["bg"] + p["sur"]); src["person_table"] += 1; continue
        miss0[b] += 1
        if p:
            bg, n = match(p, y)
            if bg and p["name"]:
                clans[b].append(bg + p["name"][0]); src["roster_fill"] += 1; continue
        miss[b] += 1; src["still_missing"] += 1
    nmin = min(len(v) for v in clans.values())
    rng = random.Random(SEED)
    rows = []
    for b in BINS:
        g = clans[b]; s = stats(g)
        boot = [stats(rng.sample(g, nmin))["top10_share"] for _ in range(1000)]
        lb = sum(v for _, v in collections.Counter(g).most_common(10)) / tot[b]
        rows.append(dict(period=f"{b[0]}–{b[1]-1}", mid_year=(b[0] + b[1]) / 2, first_appointees=tot[b],
                         missing_before_fill=miss0[b], missing_after_fill=miss[b], missing_share_after=miss[b] / tot[b], **s,
                         top10_resampled=float(np.mean(boot)), top10_ci_lo=float(np.percentile(boot, 2.5)), top10_ci_hi=float(np.percentile(boot, 97.5)),
                         top10_lower_bound=lb, resample_n=nmin,
                         top5=" · ".join(f"{k}{v}" for k, v in collections.Counter(g).most_common(5))))
    clan = pd.DataFrame(rows)
    clan.to_csv(D / "d_clan.csv", index=False, encoding="utf-8")
    # roster itself
    bm_bins = collections.defaultdict(list)
    for b in BM:
        if b["year"] and b["bg"] and b["name"]:
            bb = next((x for x in BINS if x[0] <= b["year"] < x[1]), None)
            if bb:
                bm_bins[bb].append(b["bg"] + b["name"][0])
    rows2 = []
    for b in BINS:
        g = bm_bins[b]; s = stats(g)
        boot = [stats(rng.sample(g, nmin))["top10_share"] for _ in range(1000)]
        rows2.append(dict(period=f"{b[0]}–{b[1]-1}", mid_year=(b[0] + b[1]) / 2, passers=len(g), **s,
                          top10_resampled=float(np.mean(boot)), top10_ci_lo=float(np.percentile(boot, 2.5)), top10_ci_hi=float(np.percentile(boot, 97.5)), resample_n=nmin,
                          top5=" · ".join(f"{k}{v}" for k, v in collections.Counter(g).most_common(5))))
    pd.DataFrame(rows2).to_csv(D / "d_clan_munkwa.csv", index=False, encoding="utf-8")
    from scipy.stats import spearmanr
    mid = [r["mid_year"] for r in rows]
    rs = spearmanr(mid, [r["top10_resampled"] for r in rows]); rl = spearmanr(mid, [r["top10_lower_bound"] for r in rows]); rb = spearmanr(mid, [r["top10_resampled"] for r in rows2])
    json.dump(dict(first_appointees=len(first), fill=dict(src), validation=dict(ok=ok, bad=bad, nomatch=nomatch, ambiguous=amb, accuracy=ok / (ok + bad)),
                   resample_n=nmin, spearman_resampled=[rs.statistic, rs.pvalue], spearman_lower=[rl.statistic, rl.pvalue], spearman_munkwa=[rb.statistic, rb.pvalue],
                   roster_size=len(BM)), open(D / "d_clan_fill.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(clan[["period", "first_appointees", "missing_share_after", "top10_resampled", "top10_ci_lo", "top10_ci_hi", "top10_lower_bound"]].to_string())
    print("fill", dict(src), "accuracy", round(ok / (ok + bad), 3), "rho", rs)

    # ---- D2–D4 from articles
    art = pd.read_parquet(D / "articles.parquet")
    hits = pd.read_parquet(D / "keyword_hits.parquet")
    main_ = art[art.is_main & art.year_ce.notna() & (art.year_ce <= 1910)].copy()
    def share_by_reign(key, name, extra_cls=None):
        ids = set(hits[hits.pattern == key].article_id)
        g = main_.groupby(["king_no", "king_ko", "king_en", "edition"])
        out = g.size().rename("n_articles").to_frame()
        out["n_keyword"] = g.apply(lambda x: x.article_id.isin(ids).sum())
        out["keyword_share"] = out.n_keyword / out.n_articles
        if extra_cls:
            out["n_classified"] = g.apply(lambda x: x.subjects.str.contains(extra_cls, na=False).sum())
            out["classified_share"] = out.n_classified / out.n_articles
        out.to_csv(D / name, encoding="utf-8")
        return out
    share_by_reign("royal_lecture", "d_lecture.csv")
    share_by_reign("memorial", "d_memorial.csv", extra_cls="정론-간쟁")
    just = main_.subjects.str.contains("사법", na=False)
    g = main_.assign(just=just).groupby(["king_no", "king_ko", "king_en", "edition"])
    dj = g.size().rename("n_articles").to_frame(); dj["n_justice"] = g.just.sum(); dj["justice_share"] = dj.n_justice / dj.n_articles
    dj.to_csv(D / "d_justice.csv", encoding="utf-8")
    main_["decade"] = (main_.year_ce // 10 * 10).astype(int)
    g = main_.assign(just=just).groupby("decade")
    dd = g.size().rename("n_articles").to_frame(); dd["n_justice"] = g.just.sum(); dd["justice_share"] = dd.n_justice / dd.n_articles
    for cls in ("사법-탄핵", "사법-행형", "사법-재판", "사법-치안", "사법-법제", "사법-사법"):
        dd[cls] = g.apply(lambda x: x.subjects.str.contains(cls, na=False).sum())
    dd.to_csv(D / "d_justice_decade.csv", encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
