# -*- coding: utf-8 -*-
"""Validate a coded JSONL against its input: same count and order of article_id, schema, quote verbatim in text.
  python src/check_coding.py INPUT CODED [--schema solar|lunar|precision]"""
import json, sys
def read(p): return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
SCHEMAS = {"solar": ["article_id","type","boundary","time_text","magnitude_text","not_seen_reason","summary","quote"],
           "lunar": ["article_id","type","boundary","time_text","magnitude_text","not_seen_reason","summary","quote"],
           "precision": ["article_id","relevant","reason","quote"]}
def main(inp, cod, schema):
    I, C = read(inp), read(cod); keys = SCHEMAS[schema]; probs = []
    if len(I) != len(C): probs.append(f"count {len(I)} vs {len(C)}")
    for i, (a, b) in enumerate(zip(I, C)):
        if a["article_id"] != b.get("article_id"): probs.append(f"order@{i}: {a['article_id']} vs {b.get('article_id')}")
        miss = [k for k in keys if k not in b]; extra = [k for k in b if k not in keys]
        if miss or extra: probs.append(f"schema@{b.get('article_id')}: missing {miss} extra {extra}")
        q = b.get("quote", "")
        if q and q not in a["text"]: probs.append(f"quote@{b.get('article_id')}: not verbatim")
    print(cod.split("\\")[-1].split("/")[-1], "OK" if not probs else f"{len(probs)} problems"); [print("  ", p) for p in probs[:12]]
    return not probs
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8"); a = sys.argv
    schema = a[a.index("--schema") + 1] if "--schema" in a else "solar"
    sys.exit(0 if main(a[1], a[2], schema) else 1)
