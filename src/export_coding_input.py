# -*- coding: utf-8 -*-
"""Export article texts for hand coding.

  python src/export_coding_input.py --pattern solar_eclipse --out data/coding/solar_eclipse_input.jsonl [--sample N --strata 50]
  python src/export_coding_input.py --ids data/coding/some_ids.txt --out ...

Pulls the plain text (markup collapsed, notes kept inside 【】, historian's comments marked 〔史論〕)
of the selected articles from the raw XML and writes one JSON object per line:
  article_id, edition, date (lunar, with CE year), title, text
When --sample N is given, N articles are drawn per stratum (strata = CE year // --strata) with a fixed seed.
"""
import argparse
import json
import random
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_articles import EDITIONS, RAW, load  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "derived"
SEED = 20261101


def render(el) -> str:
    out = []

    def rec(e):
        tag = e.tag
        if tag == "annotation":
            out.append("【" + "".join(e.itertext()).strip() + "】")
            return
        if tag == "postScript":
            out.append("\n〔史論〕 ")
        elif tag == "paragraph":
            out.append("\n")
        elif tag == "proofreading":
            out.append("⟦" + (e.get("type") or "")[-2:] + " ")
            out.append("".join(e.itertext()))
            out.append("⟧")
            return
        out.append(e.text or "")
        for c in e:
            rec(c)
            out.append(c.tail or "")
    rec(el)
    s = "".join(out)
    s = re.sub(r"[ \t]*\n\s*", "\n", s)
    return s.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pattern")
    ap.add_argument("--ids")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--strata", type=int, default=50)
    ap.add_argument("--main-only", action="store_true")
    a = ap.parse_args()
    if a.pattern:
        hits = pd.read_parquet(D / "keyword_hits.parquet")
        ids = list(hits[hits.pattern == a.pattern].article_id)
    else:
        ids = [l.strip() for l in open(a.ids, encoding="utf-8") if l.strip()]
    want = set(ids)
    z = zipfile.ZipFile(RAW)
    rows = {}
    for fn in sorted(n for n in z.namelist() if n.endswith(".xml")):
        m = re.search(r"2nd_(w[a-z]{2})_(\d{3})\.xml$", fn)
        if not m or m.group(1) not in EDITIONS:
            continue
        ed = m.group(1)
        if a.main_only and not EDITIONS[ed][5]:
            continue
        # cheap skip: IDs carry the edition code
        if not any(i.startswith(ed + "_") for i in want):
            continue
        root = load(z.read(fn))
        cur = {}
        for lv in root.iter():
            if not lv.tag.startswith("level"):
                continue
            b = lv.find("front/biblioData")
            if b is None:
                continue
            dates = {o.get("type"): (o.get("date") or (o.text or "").strip()) for o in b.iter("dateOccured")}
            if b.get("type") == "L" and dates.get("간지"):
                cur = dates
                continue
            if b.get("type") != "T" or lv.get("id") not in want:
                continue
            t = b.find("title/mainTitle")
            tx = lv.find("text")
            ymd = dates.get("서기") or cur.get("서기") or ""
            rows[lv.get("id")] = dict(article_id=lv.get("id"), edition=ed,
                                      date=f"{ymd} ({cur.get('재위연도', '')})", title=re.sub(r"\s+", " ", t.text or "").strip() if t is not None else "",
                                      text=render(tx) if tx is not None else "")
    out = [rows[i] for i in ids if i in rows]
    if a.sample:
        rng = random.Random(SEED)
        by = {}
        for r in out:
            y = re.match(r"(\d{4})", r["date"])
            if not y:
                continue
            by.setdefault(int(y.group(1)) // a.strata * a.strata, []).append(r)
        picked = []
        for k in sorted(by):
            g = by[k]
            picked += rng.sample(g, min(a.sample, len(g)))
        out = picked
    with open(a.out, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("wrote", len(out), "of", len(ids), "->", a.out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
