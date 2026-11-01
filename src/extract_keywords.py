# -*- coding: utf-8 -*-
"""Keyword hits per article for the keyword-based metrics (series C, D, E).

  python src/extract_keywords.py          # writes data/derived/keyword_hits.parquet (+ .csv)

One row per (article, pattern key) with the number of matches and a short context of the first
match. Patterns are tested on the article text only (annotations and historian's comments
included, titles excluded). Which pattern feeds which metric, and the precision measured by
hand-coded samples, is documented in registry.py.
"""
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_articles import EDITIONS, KOGL4, RAW, RAW4, load  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "derived"

# compounds in which 霜/雪 are not weather (clearing a grievance, the solar term, the Censorate, names)
EXCLUDE = re.compile(r"雪冤|伸雪|昭雪|快雪|洗雪|雪恥|雪憤|雪辱|霜降|霜臺|雪寒嶺|履霜|飛霜|雪山|雪嶽")

PATTERNS = {
    "solar_eclipse": r"日食|日蝕",
    "lunar_eclipse": r"月食|月蝕",
    "venus_daytime": r"太白晝見|太白經天",
    "comet": r"彗星|彗孛|星孛|孛星|客星|長星|妖星",
    "earthquake": r"地震",
    "frost": r"隕霜|降霜|霜降(?!節)|有霜|霜",
    "snow": r"雨雪|大雪|降雪|雪",
    "hail": r"雹",
    "royal_lecture": r"經筵|御經筵|晝講|朝講|夕講|夜對",
    "memorial": r"上疏|上箚|箚子|疏曰|箚曰",
    "relief": r"賑恤|賑濟|賑救|設賑|飢饉|饑饉|凶年|大饑|大飢|飢民|饑民",
    "eonmun": r"諺文|諺書|諺解|訓民正音|諺譯",
    "slaves": r"奴婢|公賤|私賤|官奴|私奴|婢子|奴子",
    "death_penalty": r"處斬|斬之|斬刑|梟示|梟首|處絞|絞之|絞刑|凌遲|陵遲|賜死|賜自盡|伏誅|正法|死罪|一罪|棄市|誅之",
}


def main():
    pats = {k: re.compile(v) for k, v in PATTERNS.items()}
    rows = []
    for zpath in (RAW, RAW4):
      z = zipfile.ZipFile(zpath)
      for fn in sorted(n for n in z.namelist() if n.endswith(".xml")):
        m = re.search(r"2nd_(w[a-z]{2})_(\d{3})\.xml$", fn)
        if not m or m.group(1) not in EDITIONS:
            continue
        ed = m.group(1)
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
            txt_w = EXCLUDE.sub("", txt)   # for frost/snow: strip compounds where 霜/雪 do not mean weather
            for k, p in pats.items():
                hits = list(p.finditer(txt_w if k in ("frost", "snow") else txt))
                if hits:
                    h = hits[0]
                    rows.append(dict(article_id=lv.get("id"), pattern=k, n_hits=len(hits),
                                     context="" if ed in KOGL4 else txt[max(0, h.start() - 40): h.end() + 40]))
        print(fn, len(rows), flush=True)
    df = pd.DataFrame(rows)
    df.to_parquet(OUT / "keyword_hits.parquet", index=False)
    df.to_csv(OUT / "keyword_hits.csv", index=False, encoding="utf-8")
    print(df.groupby("pattern").size())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
