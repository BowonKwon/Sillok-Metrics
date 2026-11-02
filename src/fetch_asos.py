# -*- coding: utf-8 -*-
"""Fetch KMA ASOS daily data for Seoul (station 108) from data.go.kr (AsosDalyInfoService, KOGL Type 1).

  python src/fetch_asos.py 1907-10-01 1910-12-31

Key: ~/.secrets/datagokr.key.txt  (DATAGOKR_KEY="...")  — never printed, never placed anywhere but the serviceKey field.
Output: data/raw/external/kma-asos108/asos108_daily_{start}_{end}.json (raw item list) + .csv
"""
import csv, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "external" / "kma-asos108"
EP = "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"

def key():
    t = (Path.home() / ".secrets" / "datagokr.key.txt").read_text(encoding="utf-8").strip()
    m = re.search(r'"([^"]+)"', t)
    return m.group(1) if m else t.split("=", 1)[-1].strip()

def fetch(start, end, stn="108"):
    k = key(); items = []; page = 1
    while True:
        q = {"serviceKey": k, "pageNo": page, "numOfRows": 999, "dataType": "JSON", "dataCd": "ASOS", "dateCd": "DAY",
             "startDt": start.replace("-", ""), "endDt": end.replace("-", ""), "stnIds": stn}
        url = EP + "?" + urllib.parse.urlencode(q)
        with urllib.request.urlopen(url, timeout=60) as r:
            body = r.read().decode("utf-8")
        try:
            d = json.loads(body)
        except json.JSONDecodeError:
            print("non-JSON reply:", body[:300].replace(k, "***")); sys.exit(2)
        h = d["response"]["header"]
        if h["resultCode"] != "00":
            print("error", h["resultCode"], h["resultMsg"]); sys.exit(3)
        b = d["response"]["body"]; got = b["items"]["item"] if b.get("items") else []
        items += got; total = int(b["totalCount"])
        print(f"page {page}: {len(got)} rows (total {total})")
        if len(items) >= total or not got: break
        page += 1; time.sleep(0.3)
    return items

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    s, e = sys.argv[1], sys.argv[2]
    it = fetch(s, e); OUT.mkdir(parents=True, exist_ok=True)
    stem = OUT / f"asos108_daily_{s}_{e}"
    stem.with_suffix(".json").write_text(json.dumps(it, ensure_ascii=False, indent=0), encoding="utf-8")
    if it:
        cols = sorted({c for r in it for c in r})
        with open(stem.with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(it)
    print("rows", len(it), "->", stem.with_suffix(".csv"))
