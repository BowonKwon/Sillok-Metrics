# -*- coding: utf-8 -*-
"""Collect precision estimates from the hand-coded samples into data/derived/reliability.json.

  python src/reliability.py

For each bundle in data/coding/{bundle}_coded.jsonl: precision = yes / n, Wilson 95% interval,
reserved judgements ("판단 유보") counted as 'no'. Quotes are re-checked against the input text.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
C = ROOT / "data" / "coding"
CURRENT = {}
BUNDLES = ["comet", "earthquake", "summer_cold", "royal_lecture", "relief", "slaves"]


def wilson(k, n, z=1.96):
    p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


def read(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def main():
    import pandas as pd
    hits = pd.read_parquet(ROOT / "data" / "derived" / "keyword_hits.parquet")
    pats = {"comet": ["comet"], "earthquake": ["earthquake"], "summer_cold": ["frost", "snow", "hail"], "royal_lecture": ["royal_lecture"], "relief": ["relief"], "slaves": ["slaves"]}
    global CURRENT
    CURRENT = {b: set(hits[hits.pattern.isin(ps)].article_id) for b, ps in pats.items()}
    out = {}
    for b in BUNDLES:
        p = C / f"{b}_coded.jsonl"
        if not p.exists():
            continue
        coded = read(p)
        # precision is measured for the *current* keyword rule: sample articles that the current rule no
        # longer selects (e.g. after excluding 雪冤-type compounds) are dropped from the denominator
        cur = CURRENT.get(b)
        if cur is not None:
            coded = [r for r in coded if r["article_id"] in cur]
        src = {r["article_id"]: r["text"].replace("\n", "") for r in read(C / f"{b}_input.jsonl")}
        assert set(r["article_id"] for r in coded) <= set(src), b
        bad = [r["article_id"] for r in coded if r.get("quote") and r["quote"].replace("\n", "") not in src[r["article_id"]]]
        assert not bad, (b, bad)
        ov = json.load(open(C / "overrides.json", encoding="utf-8"))["overrides"].get(b, {}) if (C / "overrides.json").exists() else {}
        for r in coded:
            if r["article_id"] in ov:
                r["relevant"] = ov[r["article_id"]]; r["reason"] = (r.get("reason") or "").replace("(판단 유보)", "") + " [override]"
        yes = sum(1 for r in coded if r["relevant"] == "yes")
        n = len(coded)
        lo, hi = wilson(yes, n)
        out[b] = dict(n=n, yes=yes, precision=yes / n, ci_lo=lo, ci_hi=hi, reserved=sum(1 for r in coded if "판단 유보" in (r.get("reason") or "")))
        print(b, out[b])
    json.dump(out, open(ROOT / "data" / "derived" / "reliability.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
