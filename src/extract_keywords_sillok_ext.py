# -*- coding: utf-8 -*-
"""Count two series-G patterns in the Sillok that the 1.0 keyword set did not have (sunspot, guest_star).

Output: data/derived/keyword_hits_sillok_ext.parquet / .csv — article_id, pattern, n_hits. No context column at all
(so Gojong/Sunjong articles, KOGL Type 4, contribute counts only). Added in 1.2.1 so that the Sillok figures quoted on
the G4 and G5 pages (sunspot articles; guest-star articles of Seonjo's reign around the 1604 supernova) are reproducible
from a published file.
"""
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_articles import EDITIONS, RAW, RAW4, load  # noqa: E402
from build_articles_ext import ASTRO_PATTERNS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "derived"
KEYS = ("sunspot", "guest_star")


def main():
    pats = {k: re.compile(ASTRO_PATTERNS[k]) for k in KEYS}
    rows = []
    for zpath in (RAW, RAW4):
        z = zipfile.ZipFile(zpath)
        for fn in sorted(n for n in z.namelist() if n.endswith(".xml")):
            m = re.search(r"2nd_(w[a-z]{2})_(\d{3})\.xml$", fn)
            if not m or m.group(1) not in EDITIONS:
                continue
            root = load(z.read(fn))
            for lv in root.iter():
                if not lv.tag.startswith("level"):
                    continue
                b = lv.find("front/biblioData")
                if b is None or b.get("type") != "T":
                    continue
                tx = lv.find("text")
                if tx is None:
                    continue
                txt = re.sub(r"\s+", "", "".join(tx.itertext()))
                for k, p in pats.items():
                    n = len(p.findall(txt))
                    if n:
                        rows.append(dict(article_id=lv.get("id"), pattern=k, n_hits=n))
        print(zpath.name, len(rows), flush=True)
    df = pd.DataFrame(rows)
    df.to_parquet(OUT / "keyword_hits_sillok_ext.parquet", index=False)
    df.to_csv(OUT / "keyword_hits_sillok_ext.csv", index=False, encoding="utf-8")
    print(df.groupby("pattern").size())


if __name__ == "__main__":
    main()
