# -*- coding: utf-8 -*-
"""Export article texts of the 1.2 sources (Goryeosa 天文志, Goryeosa-jeolyo, Seungjeongwon Ilgi) for hand coding.

  python src/export_coding_input_ext.py --source goryeosa --pattern solar_eclipse --out data/coding/solar_eclipse_input_goryeosa.jsonl
  python src/export_coding_input_ext.py --source sjw --pattern comet --sample 20 --strata 50 --out ...
  python src/export_coding_input_ext.py --source sjw --ids ids.txt --out ...

Same record shape as export_coding_input.py plus `source`:
  article_id, source, edition, date, title, text
Selection uses keyword_hits_ext.parquet (pattern) restricted to articles_ext.parquet rows of that source.
Sampling: N per stratum of CE years (strata width in years), fixed seed 20261102.
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
from build_articles import load                      # noqa: E402
from export_coding_input import render               # noqa: E402
from build_articles_ext import GORYEOSA, JEOLYO, SJW  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "derived"
SEED = 20261102
ZIPS = {"goryeosa": GORYEOSA, "goryeosa_jeolyo": JEOLYO, "sjw": SJW}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, choices=list(ZIPS))
    ap.add_argument("--pattern")
    ap.add_argument("--ids")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--strata", type=int, default=50)
    a = ap.parse_args()
    arts = pd.read_parquet(D / "articles_ext.parquet")
    arts = arts[arts.source == a.source].set_index("article_id")
    if a.pattern:
        hits = pd.read_parquet(D / "keyword_hits_ext.parquet")
        ids = [i for i in hits[hits.pattern == a.pattern].article_id if i in arts.index]
    else:
        ids = [l.strip() for l in open(a.ids, encoding="utf-8") if l.strip()]
    want = set(ids)
    z = zipfile.ZipFile(ZIPS[a.source])
    files = sorted(n for n in z.namelist() if n.endswith(".xml"))
    if a.source == "goryeosa":
        files = ["kr_047.xml", "kr_048.xml", "kr_049.xml"]
    rows = {}
    for fn in files:
        if a.source == "sjw":
            # ids carry the book letter and reign year: SJW-A01030120-00100 -> file 2nd_A01
            stem = re.search(r"2nd_([A-L]\d\d)", fn).group(1)
            if not any(i.startswith("SJW-" + stem) for i in want):
                continue
        elif a.source == "goryeosa_jeolyo":
            stem = fn[:-4]
            if not any(i.startswith(stem) for i in want):
                continue
        root = load(z.read(fn))
        for lv in root.iter():
            if not lv.tag.startswith("level") or lv.get("id") not in want:
                continue
            t = lv.find("./front/biblioData/title/mainTitle")
            tx = lv.find("text")
            r = arts.loc[lv.get("id")]
            lun = f"{int(r.year_ce)}-{int(r.lunar_month):02d}-{int(r.lunar_day) if r.lunar_day == r.lunar_day else '??':>02}{'L1' if r.is_leap else 'L0'}" if r.year_ce == r.year_ce else "미상"
            rows[lv.get("id")] = dict(article_id=lv.get("id"), source=a.source, edition=r.edition,
                                      date=f"{lun} ({r.king_ko}; 양력 {r.solar_date or '미상'})",
                                      title=re.sub(r"\s+", " ", t.text or "").strip() if t is not None else "",
                                      text=render(tx) if tx is not None else "")
    out = [rows[i] for i in ids if i in rows]
    if a.sample:
        rng = random.Random(SEED)
        by = {}
        for r in out:
            y = re.match(r"(\d{4})", r["date"])
            if y:
                by.setdefault(int(y.group(1)) // a.strata * a.strata, []).append(r)
        out = []
        for k in sorted(by):
            out += rng.sample(by[k], min(a.sample, len(by[k])))
    with open(a.out, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("wrote", len(out), "of", len(ids), "->", a.out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
