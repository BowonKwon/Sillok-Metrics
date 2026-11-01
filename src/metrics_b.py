# -*- coding: utf-8 -*-
"""Series B — editions compared.

  python src/metrics_b.py

Writes data/derived/b_pairs.csv (original vs revised/supplemented editions) and b_gwanghae.csv.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "derived"
PAIRS = [("wna", "wnb"), ("wra", "wrb"), ("wsa", "wsb"), ("wta", "wtb"), ("woa", "wob")]


def main():
    df = pd.read_parquet(D / "articles.parquet")
    rows = []
    for a, b in PAIRS:
        A, B = df[df.edition == a], df[df.edition == b]
        da, db = set(A[A.jdn.notna()].jdn), set(B[B.jdn.notna()].jdn)
        rows.append(dict(
            original=a, revised=b, original_ko=A.edition_ko.iloc[0], revised_ko=B.edition_ko.iloc[0],
            original_en=A.edition_en.iloc[0], revised_en=B.edition_en.iloc[0],
            n_articles_original=len(A), n_articles_revised=len(B), article_ratio=len(B) / len(A),
            n_han_original=int(A.n_han.sum()), n_han_revised=int(B.n_han.sum()), han_ratio=B.n_han.sum() / A.n_han.sum(),
            days_original=len(da), days_revised=len(db), shared_days=len(da & db),
            shared_share_of_revised=len(da & db) / len(db), shared_share_of_original=len(da & db) / len(da),
            saron_share_original=(A.n_saron > 0).mean(), saron_share_revised=(B.n_saron > 0).mean(),
            n_saron_original=int(A.n_saron.sum()), n_saron_revised=int(B.n_saron.sum()),
            median_len_original=A.n_han.median(), median_len_revised=B.n_han.median(),
        ))
    pairs = pd.DataFrame(rows)
    pairs.to_csv(D / "b_pairs.csv", index=False, encoding="utf-8")
    A, B = df[df.edition == "woa"], df[df.edition == "wob"]
    g = pd.DataFrame([dict(
        n_articles_second_draft=len(A), n_articles_final_draft=len(B), article_drop=1 - len(B) / len(A),
        n_han_second_draft=int(A.n_han.sum()), n_han_final_draft=int(B.n_han.sum()), han_drop=1 - B.n_han.sum() / A.n_han.sum(),
        n_han_marked_deleted=int(A.n_del_han.sum()), marked_deleted_share=A.n_del_han.sum() / A.n_han.sum(),
        articles_with_deletion_marks=int((A.n_del_han > 0).sum()),
    )])
    # per reign-year deletion share
    yr = A.groupby("year_ce").agg(n_han=("n_han", "sum"), n_del=("n_del_han", "sum"), n_articles=("article_id", "size"))
    yr["final_articles"] = B.groupby("year_ce").size()
    yr["final_han"] = B.groupby("year_ce").n_han.sum()
    yr["marked_deleted_share"] = yr.n_del / yr.n_han
    yr["han_drop"] = 1 - yr.final_han / yr.n_han
    g.to_csv(D / "b_gwanghae.csv", index=False)
    yr.to_csv(D / "b_gwanghae_yearly.csv")
    pd.set_option("display.width", 220)
    print(pairs[["original", "revised", "n_articles_original", "n_articles_revised", "article_ratio", "han_ratio", "shared_share_of_revised", "saron_share_original", "saron_share_revised"]].to_string())
    print(g.T)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
