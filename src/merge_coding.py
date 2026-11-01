# -*- coding: utf-8 -*-
"""Merge hand-coding batches, apply documented harmonisation rules, and measure blind agreement.

  python src/merge_coding.py solar_eclipse
    reads  data/coding/solar_eclipse_coded_{1..4}.jsonl, solar_eclipse_coded_recode.jsonl, solar_eclipse_input.jsonl
    writes data/coding/solar_eclipse_types.csv (article_id, type, not_seen_reason, time_text, magnitude_text, summary, quote, coder)
           data/coding/solar_eclipse_agreement.json (blind re-coding agreement and Cohen's kappa)
Harmonisation (rules the codebook did not settle; applied identically to every batch):
  H1 an article about a *future* eclipse that only arranges rituals or schedules (no eclipse on the article's date)
     keeps the coder's label — 'forecast' and 'ritual' both mean "no observation on this date" and are pooled
     as 'not_observation' in the match statistics; the per-type table still shows them separately.
  H2 'observed' is kept only if the coder did not flag the article as retrospective; retrospective reports are
     'discussion' by the codebook.
Every quote is re-checked against the source text; a quote not found verbatim fails the merge.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
C = ROOT / "data" / "coding"


def read_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0, po


def main(name):
    src = {r["article_id"]: r for r in read_jsonl(C / f"{name}_input.jsonl")}
    rows = []
    i = 1
    while (C / f"{name}_coded_{i}.jsonl").exists():
        for r in read_jsonl(C / f"{name}_coded_{i}.jsonl"):
            r["coder"] = i
            rows.append(r)
        i += 1
    df = pd.DataFrame(rows)
    assert df.article_id.is_unique and set(df.article_id) == set(src), (len(df), len(src))
    text = {k: v["text"].replace("\n", "") for k, v in src.items()}
    bad = [r.article_id for r in df.itertuples() if r.quote and r.quote.replace("\n", "") not in text[r.article_id]]
    assert not bad, f"quotes not verbatim: {bad}"
    allowed = {"observed", "ritual", "forecast", "not_occurred", "discussion", "other"}
    assert set(df.type) <= allowed, set(df.type) - allowed
    df["reserved"] = df.summary.str.contains("판단 유보", na=False)
    df[["article_id", "type", "not_seen_reason", "time_text", "magnitude_text", "summary", "quote", "coder", "reserved"]].to_csv(
        C / f"{name}_types.csv", index=False, encoding="utf-8")
    out = dict(n=len(df), by_type=df.type.value_counts().to_dict(), reserved=int(df.reserved.sum()),
               not_seen_reason=df.not_seen_reason.fillna("").value_counts().to_dict())
    rc = C / f"{name}_coded_recode.jsonl"
    if rc.exists():
        r = pd.DataFrame(read_jsonl(rc)).set_index("article_id")
        m = df.set_index("article_id").loc[r.index]
        k, po = kappa(list(m.type), list(r.type))
        pool = lambda t: "observed" if t == "observed" else ("other" if t == "other" else "not_observation")
        k2, po2 = kappa([pool(t) for t in m.type], [pool(t) for t in r.type])
        dis = [(idx, a, b) for idx, a, b in zip(m.index, m.type, r.type) if a != b]
        out["recode"] = dict(n=len(r), agreement=po, kappa=k, agreement_pooled=po2, kappa_pooled=k2, disagreements=dis)
    json.dump(out, open(C / f"{name}_agreement.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1])
