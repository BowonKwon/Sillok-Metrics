# -*- coding: utf-8 -*-
"""Static site builder: derived CSVs + registry -> site/ (ko + en).

  python src/build_site.py [--derived data/derived] [--out site]

No external dependencies beyond pandas. Charts are inline SVG. Every number on the site comes
from a CSV in data/derived (copied to site/data) and every metric text from registry.py.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import shutil
from pathlib import Path

import pandas as pd

from registry import METRICS, PRIOR, SERIES, SITE, SOURCES

VERSION = SITE["version"]
BUILD_DATE = "2026-11-02"
REPO = "https://github.com/BowonKwon/Sillok-Metrics"
NIKH = "https://sillok.history.go.kr"

T = {
    "ko": dict(
        site="실록 메트릭스", tagline=SITE["ko"]["subtitle"],
        nav_home="홈", nav_kings="왕대", nav_metrics="지표", nav_prior="선행 결과", nav_reading="읽기용 판", nav_data="데이터", nav_method="방법·한계", lang_other="English",
        series="계열", definition="정의", formula="공식", reading="읽는 법", caveat="한계", source="자료원", unit="단위", external="외부 대조",
        reliability="신뢰도 카드", rel_exact="집계값 — 원본 XML에서 그대로 센 수", rel_ext="외부 대조값 — 천문 계산과 맞춰 본 비율", rel_samp="표본 정밀도 — 손으로 코딩한 층화 표본에서 잰 「키워드가 지표의 뜻대로 쓰인 비율」",
        table="표", download="CSV 내려받기", search="필터", metric_list="지표 목록", king_list="왕대 목록", all_kings="25대 전체",
        license="라이선스", cite="인용", built="생성일", version="판", hub="공개 자료 전체", nikh_link="국편 원문",
        articles="기사", dated="날짜 있는 기사", chars="글자(한자)", reign="재위", months="개월", per_year="1년당", saron="사론", edition="판본",
        year="연도", decade="연대", period="구간", share="비율", n="건수", prior="선행 결과", ours="이 사이트", prior_vs="선행 수치와 나란히",
        type_names={"observed": "관측 보고", "ritual": "구식 의례", "forecast": "예보·추산", "not_occurred": "불식·구름", "discussion": "논의·회고", "other": "일식 아님", "all": "전체"},
        windows={"match_seoul_w0": "서울 가시 일식, 같은 날", "match_seoul_w1": "서울 가시 일식, ±1일", "match_earth_w1": "지구 어딘가의 일식, ±1일", "match_seoul_prevday": "서울 가시 월식, 같은 날 또는 전날", "match_seoul_w1_l": "서울 가시 월식, ±1일"},
        period_lbl="50년 구간",
    ),
    "en": dict(
        site="Sillok Metrics", tagline=SITE["en"]["subtitle"],
        nav_home="Home", nav_kings="Reigns", nav_metrics="Metrics", nav_prior="Prior results", nav_reading="Reading edition", nav_data="Data", nav_method="Method & limits", lang_other="한국어",
        series="Series", definition="Definition", formula="Formula", reading="How to read it", caveat="Caveats", source="Sources", unit="Unit", external="External check",
        reliability="Reliability card", rel_exact="Exact count — read straight from the source XML", rel_ext="External match — compared with an astronomical computation", rel_samp="Sampled precision — share of keyword hits that mean what the metric says, measured on a hand-coded stratified sample",
        table="Table", download="Download CSV", search="Filter", metric_list="All metrics", king_list="All reigns", all_kings="all 25 reigns",
        license="License", cite="Citation", built="Built", version="Version", hub="All public materials", nikh_link="NIKH source",
        articles="articles", dated="dated articles", chars="characters", reign="reign", months="months", per_year="per year", saron="historians' comments", edition="Edition",
        year="Year", decade="Decade", period="Period", share="share", n="count", prior="Prior result", ours="This site", prior_vs="Next to prior figures",
        type_names={"observed": "observation report", "ritual": "rescue ritual", "forecast": "forecast / computation", "not_occurred": "did not occur / cloud", "discussion": "discussion / retrospect", "other": "not an eclipse", "all": "all"},
        windows={"match_seoul_w0": "eclipse visible from Seoul, same day", "match_seoul_w1": "eclipse visible from Seoul, ±1 day", "match_earth_w1": "eclipse anywhere on Earth, ±1 day", "match_seoul_prevday": "lunar eclipse visible from Seoul, same or previous day", "match_seoul_w1_l": "lunar eclipse visible from Seoul, ±1 day"},
        period_lbl="50-year period",
    ),
}

CSS = """
:root{color-scheme:light;
  --bg:#f7f6f2;--bg2:#edebe4;--card:#ffffff;--line:#dcd9d0;--line2:#e9e6de;
  --fg:#1e2024;--fg2:#5b5f67;--fg3:#8a8e96;
  --accent:#2f5d8a;--accent2:#9a6b2f;
  --s1:#2f5d8a;--s2:#9a6b2f;--s3:#5e6b5e;--s4:#8a4f5c;--grid:#e4e1d9;
  --shadow:0 1px 2px rgba(30,32,40,.05),0 6px 18px rgba(30,32,40,.05);
  --display:"Noto Serif KR","Source Serif 4",Georgia,"Times New Roman",serif;
  --body:"Noto Sans KR",-apple-system,"Segoe UI","Apple SD Gothic Neo",Roboto,sans-serif}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;
  --bg:#1a1c1f;--bg2:#222326;--card:#232428;--line:#34363c;--line2:#2b2d32;
  --fg:#ebe9e4;--fg2:#b3b1aa;--fg3:#80827f;
  --accent:#7ea4d6;--accent2:#d1a35f;
  --s1:#6f9bd0;--s2:#c89a56;--s3:#8fa08f;--s4:#c08595;--grid:#2e3035;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 20px rgba(0,0,0,.25)}}
:root[data-theme="dark"]{color-scheme:dark;
  --bg:#1a1c1f;--bg2:#222326;--card:#232428;--line:#34363c;--line2:#2b2d32;
  --fg:#ebe9e4;--fg2:#b3b1aa;--fg3:#80827f;
  --accent:#7ea4d6;--accent2:#d1a35f;
  --s1:#6f9bd0;--s2:#c89a56;--s3:#8fa08f;--s4:#c08595;--grid:#2e3035;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 20px rgba(0,0,0,.25)}
*{box-sizing:border-box}html,body{max-width:100%;overflow-x:hidden}
body{margin:0;font:16px/1.7 var(--body);background:var(--bg);color:var(--fg);overflow-wrap:anywhere;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline;text-underline-offset:3px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
header{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:.55rem 1.1rem;display:flex;gap:1.4rem;align-items:center;flex-wrap:wrap}
header .brand{font-family:var(--display);font-weight:600;font-size:1.05rem;color:var(--fg);letter-spacing:-.01em}
header nav{display:flex;gap:1rem;flex-wrap:wrap}header nav a{color:var(--fg2);font-size:.92rem;padding:.2rem 0;border-bottom:2px solid transparent}
header nav a:hover{text-decoration:none;color:var(--fg)}header nav a.on{color:var(--fg);border-bottom-color:var(--accent2)}
header .right{margin-left:auto;display:flex;gap:.6rem;align-items:center}
header .lang{font-size:.88rem;color:var(--fg2);border:1px solid var(--line);border-radius:999px;padding:.15rem .7rem}header .lang:hover{text-decoration:none;color:var(--fg);border-color:var(--fg3)}
.theme{border:1px solid var(--line);background:transparent;color:var(--fg2);border-radius:999px;width:30px;height:30px;cursor:pointer;font-size:.9rem;line-height:1;padding:0}.theme:hover{color:var(--fg);border-color:var(--fg3)}
main{max-width:1060px;margin:0 auto;padding:1.6rem 1.1rem 4rem;min-width:0}
h1{font-family:var(--display);font-weight:600;font-size:clamp(1.6rem,3.2vw,2.2rem);line-height:1.25;letter-spacing:-.015em;margin:.3rem 0 .5rem;text-wrap:balance}
h2{font-family:var(--display);font-weight:600;font-size:1.3rem;line-height:1.3;margin:2.4rem 0 .8rem;padding-bottom:.35rem;border-bottom:1px solid var(--line);text-wrap:balance}
h3{font-size:1.02rem;margin:1.4rem 0 .4rem}
.eyebrow{display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:.4rem}
.tag{display:inline-block;font-size:.74rem;letter-spacing:.04em;padding:.1rem .55rem;border-radius:999px;color:var(--fg2);background:var(--bg2);border:1px solid var(--line2)}
.tag.layer{color:var(--accent);border-color:color-mix(in srgb,var(--accent) 35%,transparent);background:color-mix(in srgb,var(--accent) 9%,transparent)}
.lead{color:var(--fg2);font-size:1.05rem;max-width:70ch;margin:0 0 1.2rem}
.hero{padding:.6rem 0 1.4rem;border-bottom:1px solid var(--line);margin-bottom:1.4rem}
.hero h1{font-size:clamp(1.9rem,4vw,2.7rem)}.hero .lead{font-size:1.12rem}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(235px,1fr));gap:.8rem;margin:.9rem 0 1.4rem}
.card{display:block;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.85rem 1rem .9rem;box-shadow:var(--shadow);color:var(--fg);transition:transform .15s,border-color .15s}
a.card:hover{text-decoration:none;transform:translateY(-2px);border-color:var(--fg3)}
.card b{display:block;margin-bottom:.25rem;font-size:.98rem;color:var(--accent)}.card small{color:var(--fg2);font-size:.86rem;line-height:1.5;display:block}
.card.s-A{border-top:3px solid var(--s1)}.card.s-B{border-top:3px solid var(--s3)}.card.s-C{border-top:3px solid var(--s2)}.card.s-D{border-top:3px solid var(--s4)}.card.s-E{border-top:3px solid var(--fg3)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:.8rem;margin:1.2rem 0 1.6rem}
.stat{display:block;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:1rem 1.1rem;box-shadow:var(--shadow);color:var(--fg)}
.stat .n{font-family:var(--display);font-size:2rem;font-weight:600;line-height:1.1;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.stat small{display:block;color:var(--fg2);margin-top:.35rem;font-size:.86rem;line-height:1.45}
a.stat:hover{text-decoration:none;border-color:var(--fg3)}
.spec{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:1rem 1.2rem;margin:1rem 0 1.4rem;box-shadow:var(--shadow)}
.rel{border-left:4px solid var(--accent2)}
dl{display:grid;grid-template-columns:max-content 1fr;gap:.55rem 1.4rem;margin:0}dt{color:var(--fg3);font-size:.82rem;letter-spacing:.04em;text-transform:uppercase;padding-top:.15rem}dd{margin:0;min-width:0}
dd.formula{font-family:ui-monospace,"SF Mono",Consolas,"Noto Sans KR",monospace;font-size:.9rem;background:var(--bg2);border-radius:6px;padding:.45rem .65rem;line-height:1.6}
@media(max-width:640px){dl{grid-template-columns:1fr}dt{margin-top:.5rem}}
table{border-collapse:collapse;width:100%;font-size:.9rem;margin:.6rem 0}
th,td{border-bottom:1px solid var(--line2);padding:.42rem .6rem;text-align:left;vertical-align:top}
thead th{color:var(--fg2);font-weight:600;font-size:.82rem;letter-spacing:.02em;cursor:pointer;white-space:nowrap;border-bottom:1px solid var(--line)}
thead th:hover{color:var(--fg)}tbody tr:nth-child(even){background:color-mix(in srgb,var(--bg2) 55%,transparent)}tbody tr:hover{background:var(--bg2)}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}td:first-child{white-space:nowrap}
table.fixed{table-layout:fixed;min-width:900px}table.fixed th{white-space:normal}table.fixed td{white-space:normal;overflow-wrap:normal;word-break:break-all}
.wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--card);padding:0 .3rem;margin:.6rem 0 1rem}.wrap table{margin:0}
figure{margin:1.2rem 0;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:1rem 1rem .8rem;box-shadow:var(--shadow)}
figcaption{font-size:.86rem;color:var(--fg2);margin-top:.5rem;line-height:1.5}
svg{max-width:100%;height:auto;display:block}svg text{font-family:var(--body);fill:var(--fg2);font-size:11px}svg .ax{stroke:var(--line)}svg .grid{stroke:var(--grid)}
.legend{display:flex;gap:1.1rem;font-size:.86rem;color:var(--fg2);flex-wrap:wrap;margin:.2rem 0 .4rem}.legend span::before{content:"";display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:.4rem;vertical-align:-1px;background:var(--c)}
.note{background:color-mix(in srgb,var(--accent) 7%,var(--card));border:1px solid color-mix(in srgb,var(--accent) 25%,var(--line));border-left:4px solid var(--accent);border-radius:8px;padding:.7rem 1rem;margin:1.2rem 0;font-size:.95rem}
.prose p,.prose ul,.prose ol,.prose .note,.prose .lead{max-width:72ch}.prose p{margin:.8rem 0}.prose ul,.prose ol{padding-left:1.2rem}.prose li{margin:.3rem 0}
.src{color:var(--fg2);font-size:.92rem}.files a{display:inline-block;font-size:.85rem;background:var(--bg2);border:1px solid var(--line2);border-radius:6px;padding:.15rem .55rem;margin:.2rem .3rem .2rem 0;color:var(--fg2)}.files a:hover{color:var(--fg);text-decoration:none;border-color:var(--fg3)}
footer{border-top:1px solid var(--line);color:var(--fg3);font-size:.82rem;padding:1.2rem;text-align:center;line-height:1.6}
.filter{margin:.5rem 0}.filter input{padding:.4rem .7rem;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg);width:min(100%,340px);font:inherit;font-size:.9rem}
.filter input:focus{border-color:var(--accent);outline:none;box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 20%,transparent)}
.links{display:flex;gap:1.2rem;flex-wrap:wrap;margin-top:2rem;font-size:.95rem}
@media(prefers-reduced-motion:reduce){.card,a.card:hover{transition:none;transform:none}}
/* --- visual layer: hero band, glyph watermark, key values, takeaways, ribbons --- */
.hero{position:relative;padding:1.4rem 0 1.2rem;margin:-.4rem 0 1.4rem;border-bottom:1px solid var(--line);overflow:hidden}
.hero::before{content:"";position:absolute;inset:0 -1.1rem auto -1.1rem;height:6px;background:linear-gradient(90deg,var(--s1),var(--s2) 50%,var(--s3))}
.hero .glyph{position:absolute;right:-.2rem;top:.6rem;font-family:var(--display);font-size:clamp(5rem,14vw,9rem);line-height:1;color:var(--accent);opacity:.07;pointer-events:none;user-select:none;letter-spacing:-.04em}
.hero .lead{max-width:62ch}
.strip{margin:1.2rem 0 .2rem}.strip svg text{font-size:10.5px}
.take{position:relative;background:color-mix(in srgb,var(--accent2) 9%,var(--card));border:1px solid color-mix(in srgb,var(--accent2) 30%,var(--line));border-left:5px solid var(--accent2);border-radius:10px;padding:.9rem 1.2rem 1rem;margin:1.2rem 0 1.4rem;box-shadow:var(--shadow)}
.take .l{font-family:var(--display);font-weight:600;font-size:.98rem;color:var(--accent2);letter-spacing:-.005em}
.take p{margin:.3rem 0 0;font-size:1.02rem;line-height:1.65;max-width:76ch}
.take.small p{font-size:.95rem}
.card{position:relative}.card .kv{display:block;font-family:var(--display);font-weight:600;font-size:1.55rem;line-height:1.1;letter-spacing:-.02em;font-variant-numeric:tabular-nums;color:var(--fg);margin:.1rem 0 .35rem}
.card .kv small{display:inline;font:inherit;font-family:var(--body);font-weight:400;font-size:.8rem;color:var(--fg3);margin-left:.4rem;letter-spacing:0}
h2.num{counter-increment:sec}h2.num::before{content:attr(data-n);font-family:var(--display);font-weight:600;color:var(--accent2);margin-right:.6rem;font-size:.95rem;vertical-align:.12em;font-variant-numeric:tabular-nums}
.mhero{display:grid;grid-template-columns:1fr auto;gap:1rem 2rem;align-items:end;margin-bottom:.4rem}
.mhero .big{font-family:var(--display);font-weight:600;font-size:clamp(2rem,4.5vw,3.2rem);line-height:1;letter-spacing:-.025em;font-variant-numeric:tabular-nums;color:var(--accent);text-align:right;white-space:nowrap}
.mhero .big small{display:block;font:inherit;font-family:var(--body);font-weight:400;font-size:.82rem;color:var(--fg2);letter-spacing:0;margin-top:.35rem;white-space:normal;max-width:22ch;margin-left:auto}
@media(max-width:720px){.mhero{grid-template-columns:1fr}.mhero .big{text-align:left}.mhero .big small{margin-left:0}}
.ribbon{margin:.8rem 0 1.2rem}.ribbon svg text{font-size:10px}
.rel .badge{display:inline-block;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;padding:.1rem .5rem;border-radius:999px;background:var(--accent2);color:#fff;margin-right:.5rem;vertical-align:.1em}
.stat .n{color:var(--accent)}

"""

JS = """
(function(){var k="skm-theme",r=document.documentElement,b=document.getElementById("theme");function ap(v){if(v)r.setAttribute("data-theme",v);else r.removeAttribute("data-theme");if(b)b.textContent=v==="dark"?"\\u263E":v==="light"?"\\u2600":"\\u25D1"}var cur=localStorage.getItem(k)||"";ap(cur);if(b)b.addEventListener("click",function(){cur=cur===""?"light":cur==="light"?"dark":"";if(cur)localStorage.setItem(k,cur);else localStorage.removeItem(k);ap(cur)})})();
document.querySelectorAll('table.sort').forEach(function(t){
  var ths=t.querySelectorAll('th');ths.forEach(function(th,i){th.addEventListener('click',function(){
    var rows=Array.from(t.tBodies[0].rows),asc=th.dataset.asc!=='1';th.dataset.asc=asc?'1':'0';
    rows.sort(function(a,b){var x=a.cells[i].dataset.v||a.cells[i].textContent,y=b.cells[i].dataset.v||b.cells[i].textContent;
      var nx=parseFloat(x),ny=parseFloat(y);if(!isNaN(nx)&&!isNaN(ny))return asc?nx-ny:ny-nx;return asc?x.localeCompare(y):y.localeCompare(x)});
    rows.forEach(function(r){t.tBodies[0].appendChild(r)})})})});
document.querySelectorAll('.filter input').forEach(function(inp){inp.addEventListener('input',function(){
  var q=inp.value.toLowerCase(),t=document.getElementById(inp.dataset.target);
  Array.from(t.tBodies[0].rows).forEach(function(r){r.style.display=r.textContent.toLowerCase().indexOf(q)>=0?'':'none'})})});
"""


def esc(s) -> str:
    return html.escape("" if s is None or (isinstance(s, float) and math.isnan(s)) else str(s))


def fmt(v, spec) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)) or (isinstance(v, str) and v == ""):
        return ""
    try:
        return format(v, spec)
    except Exception:
        return str(v)


def page(lang: str, title: str, body: str, depth: int = 1, desc: str = "", active: str = "") -> str:
    t = T[lang]
    root = "../" * depth
    other = "en" if lang == "ko" else "ko"
    hub_path = "" if lang == "ko" else "en/"
    nav = [("home", f"{root}{lang}/index.html", t["nav_home"]), ("kings", f"{root}{lang}/kings/index.html", t["nav_kings"]),
           ("metrics", f"{root}{lang}/metrics/index.html", t["nav_metrics"]), ("prior", f"{root}{lang}/prior.html", t["nav_prior"]),
           ("reading", f"{root}{lang}/reading.html", t["nav_reading"]), ("data", f"{root}{lang}/data.html", t["nav_data"]), ("method", f"{root}{lang}/method.html", t["nav_method"])]
    navh = "".join(f'<a href="{h}"{" class=\"on\"" if k == active else ""}>{n}</a>' for k, h, n in nav)
    attribution = ("본 사이트의 집계는 교육부 국사편찬위원회가 공공누리 제1유형으로 개방한 「조선왕조실록 정보_실록원문」·「부가정보 인물 데이터」와 한국학중앙연구원 「조선조문과급제자」(공공데이터포털)를 이용하였습니다."
                   if lang == "ko" else
                   "Counts on this site use the 'Veritable Records — original text' and 'supplementary person data' released by the National Institute of Korean History under KOGL Type 1, and the civil-examination roster of the Academy of Korean Studies (data.go.kr).")
    return f"""<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — {t['site']}</title><meta name="description" content="{esc(desc or t['tagline'])}">
<script>(function(){{var q=new URLSearchParams(location.search).get("theme");if(q==="light"||q==="dark"){{localStorage.setItem("skm-theme",q)}}else if(q==="auto"){{localStorage.removeItem("skm-theme")}}var v=localStorage.getItem("skm-theme");if(v)document.documentElement.setAttribute("data-theme",v)}})();</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=Noto+Serif+KR:wght@600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header><a class="brand" href="{root}{lang}/index.html">{t['site']}</a>
<nav>{navh}</nav>
<div class="right"><button id="theme" class="theme" type="button" aria-label="theme">◑</button><a class="lang" href="{root}{other}/index.html">{t['lang_other']}</a></div></header>
<main>{body}</main>
<footer>{t['site']} · {t['version']} {VERSION} · {t['built']} {BUILD_DATE} · <a href="{REPO}">GitHub</a> · {t['hub']} <a href="https://bowonkwon.github.io/{hub_path}">bowonkwon.github.io</a><br>{attribution}</footer>
<script>{JS}</script></body></html>"""


# ----------------------------------------------------------------- SVG charts
def nice_ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    span = hi - lo
    if span <= 0:
        return [lo]
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10)), key=lambda st: abs(st - raw))
    start = math.floor(lo / step) * step
    ticks, v = [], start
    while v <= hi + step * 1e-9:
        if v >= lo - step * 1e-9:
            ticks.append(round(v, 10))
        v += step
    return ticks


def svg_lines(series, spec, width=900, height=320, ylabel="", xstep=None, bands=None) -> str:
    xs = [p[0] for _, pts, _ in series for p in pts]
    ys = [p[1] for _, pts, _ in series for p in pts if not math.isnan(p[1])]
    if not xs or not ys:
        return ""
    x0, x1, y0, y1 = min(xs), max(xs), 0.0, max(ys) * 1.05 or 1
    L, R, Tp, B = 62, (110 if len(series) > 1 else 20), 16, 36
    pw, ph = width - L - R, height - Tp - B
    X = lambda v: L + (v - x0) / (x1 - x0 or 1) * pw
    Y = lambda v: Tp + ph - (v - y0) / (y1 - y0) * ph
    out = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="line chart">']
    if bands:
        for (a, b, label) in bands:
            out.append(f'<rect x="{X(a):.1f}" y="{Tp}" width="{max(X(b)-X(a),1):.1f}" height="{ph}" fill="var(--accent2)" fill-opacity=".10"><title>{esc(label)}</title></rect>')
    for v in nice_ticks(y0, y1):
        out.append(f'<line class="grid" x1="{L}" y1="{Y(v):.1f}" x2="{width-R}" y2="{Y(v):.1f}"/><text x="{L-6}" y="{Y(v)+4:.1f}" text-anchor="end">{fmt(v, spec)}</text>')
    step = xstep or max(1, int((x1 - x0) / 8 / 10) * 10)
    xv = int(math.ceil(x0 / step) * step)
    while xv <= x1:
        out.append(f'<text x="{X(xv):.1f}" y="{height-12}" text-anchor="middle">{xv}</text>')
        xv += step
    if ylabel:
        out.append(f'<text x="{L}" y="10">{esc(ylabel)}</text>')
    for name, pts, ci in series:
        pts = [p for p in pts if not math.isnan(p[1])]
        if not pts:
            continue
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(x):.1f},{Y(y):.1f}" for i, (x, y) in enumerate(pts))
        out.append(f'<path d="{d}" fill="none" stroke="var(--s{ci+1})" stroke-width="1.8" stroke-linejoin="round"/>')
        for x, y in pts:
            out.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="4" fill="transparent"><title>{esc(name)} · {x}: {fmt(y, spec)}</title></circle>')
        if len(series) > 1:
            lx, ly = pts[-1]
            out.append(f'<text x="{X(lx)+4:.1f}" y="{Y(ly)+4:.1f}">{esc(name)}</text>')
    out.append("</svg>")
    return "".join(out)


def svg_bars(items, spec, width=900, row_h=22, label_w=240, xlabel="", errors=None) -> str:
    vals = [v for _, v, _ in items if not (isinstance(v, float) and math.isnan(v))]
    if not vals:
        return ""
    hi_err = max([e[1] for e in errors.values()] if errors else [0])
    lo, hi = 0.0, max(max(vals), hi_err, 0.0)
    pad = hi * 0.05 or 1
    hi = hi + pad
    pw = width - label_w - 30
    h = row_h * len(items) + 40
    x = lambda v: label_w + (v - lo) / (hi - lo) * pw
    out = [f'<svg viewBox="0 0 {width} {h}" role="img" aria-label="bar chart">']
    for v in nice_ticks(lo, hi):
        out.append(f'<line class="grid" x1="{x(v):.1f}" y1="6" x2="{x(v):.1f}" y2="{h-30}"/><text x="{x(v):.1f}" y="{h-14}" text-anchor="middle">{fmt(v, spec)}</text>')
    if xlabel:
        out.append(f'<text x="{label_w+pw/2:.0f}" y="{h-2}" text-anchor="middle">{esc(xlabel)}</text>')
    for i, (name, v, ci) in enumerate(items):
        y = 8 + i * row_h
        out.append(f'<text x="{label_w-8}" y="{y+row_h*0.68:.1f}" text-anchor="end">{esc(name)}</text>')
        if isinstance(v, float) and math.isnan(v):
            continue
        out.append(f'<rect x="{x(0):.1f}" y="{y+2}" width="{max(x(v)-x(0),1):.1f}" height="{row_h-6}" fill="var(--s{ci+1})" rx="3"><title>{esc(name)}: {fmt(v, spec)}</title></rect>')
        if errors and name in errors:
            lo_e, hi_e = errors[name]
            out.append(f'<line x1="{x(lo_e):.1f}" y1="{y+row_h/2-1:.1f}" x2="{x(hi_e):.1f}" y2="{y+row_h/2-1:.1f}" stroke="var(--fg)" stroke-width="1.5"/>')
    out.append("</svg>")
    return "".join(out)


def legend(entries) -> str:
    return '<div class="legend">' + "".join(f'<span style="--c:var(--s{ci+1})">{esc(n)}</span>' for n, ci in entries) + "</div>"


def table_html(df: pd.DataFrame, cols, tid: str, lang: str, filt=True) -> str:
    t = T[lang]
    out = []
    if filt:
        out.append(f'<div class="filter"><input placeholder="{t["search"]}…" data-target="{tid}"></div>')
    # Chrome's automatic table layout stalls on a few hundred rows of long CJK cells; large tables use a
    # fixed layout with explicit column widths (the context column gets the room, the rest share equally)
    big = len(df) > 100
    if big:   # the full table is in the CSV; the page shows the first rows only
        note = (f"표의 처음 {MAX_ROWS}행만 보인다(전체 {len(df):,}행은 CSV)." if lang == "ko" else f"First {MAX_ROWS} of {len(df):,} rows shown; the CSV has them all.")
        out.append(f'<p class="src">{note}</p>')
        df = df.head(MAX_ROWS)
    out.append(f'<div class="wrap"><table class="sort{" fixed" if big else ""}" id="{tid}"><thead><tr>')
    wide = [c for c, _, _ in cols if c in ("context", "title", "top5")]
    for c, hname, spec in cols:
        style = ""
        if big:
            if c in wide:
                style = f' style="width:{int(50/len(wide))}%"'
            elif c == "nikh_url":
                style = ' style="width:10%"'
        out.append(f'<th class="{"num" if spec else ""}"{style}>{esc(hname)}</th>')
    out.append("</tr></thead><tbody>")
    for _, r in df.iterrows():
        out.append("<tr>")
        for c, hname, spec in cols:
            v = r.get(c)
            if spec:
                out.append(f'<td class="num" data-v="{"" if pd.isna(v) else v}">{fmt(v, spec)}</td>')
            elif c == "nikh_url":
                out.append(f'<td><a href="{esc(v)}">{t["nikh_link"]}</a></td>')
            else:
                out.append(f"<td>{esc(v)}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def fig(svg: str, caption: str) -> str:
    return f"<figure>{svg}<figcaption>{caption}</figcaption></figure>" if svg else ""


# ----------------------------------------------------------------- data
class Data:
    def __init__(self, d: Path):
        self.d = d
        self.ed = pd.read_csv(d / "a_editions.csv")
        self.yearly = pd.read_csv(d / "a_yearly.csv")
        self.yearly_ed = pd.read_csv(d / "a_yearly_by_edition.csv")
        self.length = pd.read_csv(d / "a_length.csv")
        self.pairs = pd.read_csv(d / "b_pairs.csv")
        self.gw = pd.read_csv(d / "b_gwanghae.csv")
        self.gwy = pd.read_csv(d / "b_gwanghae_yearly.csv")
        self.solar = pd.read_csv(d / "c_solar.csv")
        self.solar_art = pd.read_csv(d / "c_solar_articles.csv")
        self.solar_rec = pd.read_csv(d / "c_solar_eclipses_recorded.csv")
        self.lunar = pd.read_csv(d / "c_lunar.csv")
        self.lunar_art = pd.read_csv(d / "c_lunar_articles.csv")
        self.venus = pd.read_csv(d / "c_venus.csv")
        self.venus_days = pd.read_csv(d / "c_venus_days.csv")
        self.venus_pg = pd.read_csv(d / "c_venus_periodogram.csv")
        self.comet = pd.read_csv(d / "c_comet.csv")
        self.quake = pd.read_csv(d / "c_quake.csv")
        self.quake_prov = pd.read_csv(d / "c_quake_province.csv")
        self.weather = pd.read_csv(d / "c_weather.csv")
        self.clan = pd.read_csv(d / "d_clan.csv")
        self.clan_mk = pd.read_csv(d / "d_clan_munkwa.csv")
        self.clan_fill = json.load(open(d / "d_clan_fill.json", encoding="utf-8"))
        self.lecture = pd.read_csv(d / "d_lecture.csv")
        self.memorial = pd.read_csv(d / "d_memorial.csv")
        self.justice = pd.read_csv(d / "d_justice.csv")
        self.justice_dec = pd.read_csv(d / "d_justice_decade.csv")
        self.death = pd.read_csv(d / "e_death.csv")
        self.death_reign = pd.read_csv(d / "e_death_reign.csv")
        self.relief = pd.read_csv(d / "e_relief.csv")
        self.relief_y = pd.read_csv(d / "e_relief_yearly.csv")
        self.eonmun = pd.read_csv(d / "e_eonmun.csv")
        self.slave = pd.read_csv(d / "e_slave.csv")
        self.precision = json.load(open(d / "reliability.json", encoding="utf-8")) if (d / "reliability.json").exists() else {}
        self.agreement = json.load(open(d.parent / "coding" / "solar_eclipse_agreement.json", encoding="utf-8")) if (d.parent / "coding" / "solar_eclipse_agreement.json").exists() else {}
        self.cal = pd.read_csv(d / "lunar_month_starts.csv")
        _ap = d / "articles.parquet"
        _a = pd.read_parquet(_ap, columns=["is_main", "n_han"]) if _ap.exists() else pd.read_csv(d / "articles.csv.gz", usecols=["is_main", "n_han"])
        self.articles_median = float(_a[_a.is_main].n_han.median())

    def main_ed(self):
        return self.ed[self.ed.is_main].sort_values("king_no")

    def king_label(self, r, lang):
        return f"{r.king_ko}" if lang == "ko" else r.king_en

    def ed_label(self, r, lang):
        return r.edition_ko if lang == "ko" else r.edition_en


KING_COL = {"ko": ("king_ko", "edition_ko"), "en": ("king_en", "edition_en")}

PRECISION_KEYS = {"comet_years": "comet", "earthquake_articles": "earthquake", "summer_cold": "summer_cold", "royal_lecture_share": "royal_lecture",
                  "relief_share": "relief", "slave_share": "slaves", "death_penalty_mention": "death_penalty"}


# ----------------------------------------------------------------- reliability card
def reliability_card(m, D: Data, lang) -> str:
    t = T[lang]
    kind = m["reliability"]
    head = {"exact": t["rel_exact"], "external-match": t["rel_ext"], "sampled-precision": t["rel_samp"]}[kind]
    body = []
    mid = m["id"]
    if kind == "exact":
        if "external" in m:
            body.append(f"<p>{esc(m['external'][lang])}</p>")
        if mid == "n_articles":
            body.append("<p>" + ("색인 DB(2026-09, 다른 스크립트)와 30종 전부 기사 수·글자 수 일치. 본문에 남은 문자 참조 코드 0건." if lang == "ko" else
                                 "Agrees with an independent 2026-09 index (different script) on articles and characters for all 30 editions; zero residual character-reference codes in the text.") + "</p>")
    elif kind == "external-match":
        if mid == "solar_eclipse_match":
            s = D.solar
            obs = s[(s.type == "observed")].set_index("window")
            body.append("<p>" + (f"관측 보고 유형 {int(obs.loc['match_seoul_w1','n'])}건 중 서울에서 보이는 계산 일식과 ±1일 안에 맞는 것 {int(obs.loc['match_seoul_w1','matched'])}건 = {obs.loc['match_seoul_w1','rate']:.1%} (윌슨 95% {obs.loc['match_seoul_w1','ci_lo']:.1%}–{obs.loc['match_seoul_w1','ci_hi']:.1%}). 지구 어딘가의 일식(Espenak–Meeus 목록)과는 {obs.loc['match_earth_w1','rate']:.1%} ({int(obs.loc['match_earth_w1','matched'])}건)."
                                 if lang == "ko" else
                                 f"Of {int(obs.loc['match_seoul_w1','n'])} observation-report articles, {int(obs.loc['match_seoul_w1','matched'])} fall within ±1 day of a computed eclipse visible from Seoul = {obs.loc['match_seoul_w1','rate']:.1%} (Wilson 95% {obs.loc['match_seoul_w1','ci_lo']:.1%}–{obs.loc['match_seoul_w1','ci_hi']:.1%}); {obs.loc['match_earth_w1','rate']:.1%} ({int(obs.loc['match_earth_w1','matched'])}) match an eclipse somewhere on Earth (Espenak–Meeus canon).") + "</p>")
            ag = D.agreement.get("recode", {})
            if ag:
                body.append("<p>" + (f"유형 분류: 기사 {D.agreement['n']}건 전수를 코더 4명이 나눠 코딩, 그중 {ag['n']}건을 다른 코더가 블라인드로 다시 코딩 — 일치 {ag['agreement']:.1%}, κ = {ag['kappa']:.2f} (관측 보고/일식 아님/그 밖으로 묶으면 κ = {ag['kappa_pooled']:.2f})."
                                     if lang == "ko" else
                                     f"Typing: all {D.agreement['n']} articles were coded by four coders; {ag['n']} were blind re-coded by a fifth — agreement {ag['agreement']:.1%}, κ = {ag['kappa']:.2f} (κ = {ag['kappa_pooled']:.2f} when pooled into observation / not an eclipse / other).") + "</p>")
        elif mid == "lunar_eclipse_match":
            l = D.lunar.set_index("window")
            body.append("<p>" + (f"「月食」 기사 {int(l.loc['match_seoul_w1','n'])}건(유형 분류 없음) 중 ±1일 일치 {l.loc['match_seoul_w1','rate']:.1%} (95% {l.loc['match_seoul_w1','ci_lo']:.1%}–{l.loc['match_seoul_w1','ci_hi']:.1%}). 논의·회고 기사가 섞여 있어 하한이다 — 1.1에서 유형 분류 예정."
                                 if lang == "ko" else
                                 f"Of {int(l.loc['match_seoul_w1','n'])} '月食' articles (not typed), {l.loc['match_seoul_w1','rate']:.1%} match within ±1 day (95% {l.loc['match_seoul_w1','ci_lo']:.1%}–{l.loc['match_seoul_w1','ci_hi']:.1%}). Discussion and retrospective articles are mixed in, so this is a lower bound; typing is planned for 1.1.") + "</p>")
        elif mid == "venus_phase":
            v = D.venus.iloc[0]
            body.append("<p>" + (f"기록일 {int(v.n_days):,}일. 내합 ±90일 안 {v.within_90d:.1%}(균등이면 {v.within_90d_uniform:.1%}), ±6일 안 {v.within_6d:.2%}(균등이면 {v.within_6d_uniform:.1%}). 300~900일 주기 스캔의 최대 레일리 Z는 {v.best_period_days:.1f}일에서 {v.rayleigh_Z_best:,.0f} — 금성 회합주기 583.92일과 0.04% 차이."
                                 if lang == "ko" else
                                 f"{int(v.n_days):,} record days. {v.within_90d:.1%} fall within ±90 days of inferior conjunction (uniform: {v.within_90d_uniform:.1%}) and {v.within_6d:.2%} within ±6 days (uniform: {v.within_6d_uniform:.1%}). A period scan 300–900 days peaks at {v.best_period_days:.1f} days with Rayleigh Z = {v.rayleigh_Z_best:,.0f}, 0.04% from the 583.92-day synodic period.") + "</p>")
    else:
        key = PRECISION_KEYS.get(mid)
        p = D.precision.get(key) if key else None
        if p:
            body.append("<p>" + (f"층화 표본 {p['n']}건(50년 구간마다 10건, 본실록)을 손으로 코딩한 정밀도 {p['precision']:.1%} (윌슨 95% {p['ci_lo']:.1%}–{p['ci_hi']:.1%}). 판단 유보 {p.get('reserved',0)}건은 no 로 셌다. 코드북과 판정 전체를 데이터 면에서 내려받을 수 있다."
                                 if lang == "ko" else
                                 f"Precision {p['precision']:.1%} (Wilson 95% {p['ci_lo']:.1%}–{p['ci_hi']:.1%}) on a hand-coded stratified sample of {p['n']} articles (10 per 50-year period, principal editions). {p.get('reserved',0)} reserved judgements counted as 'no'. Codebook and every judgement are downloadable on the Data page.") + "</p>")
        elif mid == "death_penalty_mention":
            body.append("<p>" + ("표본 240건(50년 구간마다 20건)을 코딩해 「기사 안에서 집행이 확인되는」 비율을 구간별 윌슨 95% 구간과 함께 보정치로 썼다. 분모는 표본 기사 전체(사건이 아닌 기사 포함)다. 블라인드 재코딩 24건에서 집행 여부 κ = 1.00, 독립 검증자의 1400~1449년 표본 20건 재판정에서도 사건 17·집행 확인 2로 일치. 표본의 마지막 구간(1850~)은 고종 연간까지 뽑은 것이라 1.0 범위 밖 기사가 섞여 있다 — 그 구간의 보정치는 참고값."
                                 if lang == "ko" else
                                 "A sample of 240 (20 per 50-year period) was coded for 'execution confirmed in the article'; the rate, over all sampled articles of the period, with its Wilson 95% interval is the correction. Blind re-coding of 24 gave κ = 1.00 on execution, and an independent coder re-reading the 20 articles of 1400–1449 found the same 17 events and 2 confirmed executions. The last stratum (1850–) was drawn up to the Gojong years, so it contains articles outside the 1.0 range and its corrected value is indicative only.") + "</p>")
        else:
            body.append("<p>" + ("표본 코딩 진행 중 — 이 판에서는 키워드 건수만 싣는다." if lang == "ko" else "Sample coding in progress; this version shows keyword counts only.") + "</p>")
    badge = {"exact": ("집계" if lang == "ko" else "exact"), "external-match": ("외부 대조" if lang == "ko" else "external"), "sampled-precision": ("표본 정밀도" if lang == "ko" else "sampled")}[kind]
    return f'<div class="spec rel"><dl><dt>{t["reliability"]}</dt><dd><span class="badge">{esc(badge)}</span><b>{esc(head)}</b>{"".join(body)}</dd></dl></div>'


# ----------------------------------------------------------------- metric figures
def metric_figure(m, D: Data, lang) -> str:
    t = T[lang]
    kc, ec = KING_COL[lang]
    mid = m["id"]
    ed = D.ed.sort_values(["king_no", "edition"])
    main = D.main_ed()
    out = []
    if mid in ("n_articles", "n_han", "han_per_year", "median_len", "saron_share", "empty_month_share"):
        col = {"n_articles": "n_articles", "n_han": "n_han", "han_per_year": "han_per_year", "median_len": "median_len", "saron_share": "saron_share", "empty_month_share": "empty_month_share"}[mid]
        items = [(r[ec], float(r[col]), 0 if r.is_main else 2) for _, r in ed.iterrows()]
        out.append(fig(svg_bars(items, m["fmt"], row_h=20, label_w=250), ("판본 30종. 옅은 색은 수정·개수·보궐정오·중초본." if lang == "ko" else "All 30 editions; muted colour marks revised, supplemented, corrections and second-draft editions.")))
        if mid in ("n_articles", "n_han"):
            y = D.yearly
            colm = "n_articles" if mid == "n_articles" else "n_han"
            out.append(fig(svg_lines([(t["year"], [(int(r.year_ce), float(r[colm])) for _, r in y.iterrows()], 0)], ",.0f", ylabel=t["year"]),
                           ("연도별(본실록). 임진왜란 전후(1592~)의 골과 정조 이후의 감소가 보인다." if lang == "ko" else "By year, principal editions. Note the trough around the Imjin War (1592–) and the decline after Jeongjo.")))
        cols = [(ec, t["edition"], None), ("n_articles", t["articles"], ",.0f"), ("n_dated", t["dated"], ",.0f"), ("n_han", t["chars"], ",.0f"), ("reign_months", t["reign"] + " (" + t["months"] + ")", ",.0f"),
                ("articles_per_year", t["articles"] + "/" + t["year"], ",.0f"), ("han_per_year", t["chars"] + "/" + t["year"], ",.0f"), ("median_len", ("기사 길이 중앙값" if lang == "ko" else "median length"), ",.0f"),
                ("n_saron", t["saron"], ",.0f"), ("saron_share", t["saron"] + " " + t["share"], ".1%"), ("empty_months", ("기사 없는 달" if lang == "ko" else "empty months"), ",.0f")]
        out.append(table_html(ed, cols, "t_ed", lang))
        if mid == "median_len":
            L = D.length.merge(ed[["edition", ec]], on="edition")
            out.append(table_html(L, [(ec, t["edition"], None), ("count", t["articles"], ",.0f"), ("10%", "p10", ",.0f"), ("25%", "p25", ",.0f"), ("50%", "p50", ",.0f"), ("75%", "p75", ",.0f"), ("90%", "p90", ",.0f"), ("99%", "p99", ",.0f"), ("max", t.get("max", "max"), ",.0f")], "t_len", lang))
        if mid == "saron_share":
            cha = {"wba": 1, "wga": 5, "wha": 2, "wia": 629, "wja": 34, "wka": 1261, "wla": 55, "wma": 1439}
            cmp_ = ed[ed.edition.isin(cha)].copy(); cmp_["cha"] = cmp_.edition.map(cha)
            out.append("<h3>" + t["prior_vs"] + "</h3>" + table_html(cmp_, [(ec, t["edition"], None), ("n_saron_articles", ("사론 태그 기사(이 사이트)" if lang == "ko" else "tagged articles (this site)"), ",.0f"), ("n_saron", ("사론 태그 수(이 사이트)" if lang == "ko" else "tagged comments (this site)"), ",.0f"), ("cha", ("차장섭 표 2 (「史臣曰」 수)" if lang == "ko" else "Cha, Table 2 (count of 史臣曰)"), ",.0f")], "t_cha", lang, filt=False))
    elif mid in ("edition_pair_ratio", "shared_day_share", "revised_saron_share"):
        P = D.pairs
        lab = "original_ko" if lang == "ko" else "original_en"; lab2 = "revised_ko" if lang == "ko" else "revised_en"
        P = P.assign(pair=P[lab] + " → " + P[lab2])
        cols = [("pair", t["edition"], None), ("n_articles_original", t["articles"] + " (A)", ",.0f"), ("n_articles_revised", t["articles"] + " (B)", ",.0f"), ("article_ratio", "B/A", ".3f"),
                ("n_han_original", t["chars"] + " (A)", ",.0f"), ("n_han_revised", t["chars"] + " (B)", ",.0f"), ("han_ratio", "B/A", ".3f"),
                ("shared_days", ("공유 날짜" if lang == "ko" else "shared days"), ",.0f"), ("shared_share_of_revised", ("B 날짜 중" if lang == "ko" else "of B's days"), ".1%"), ("shared_share_of_original", ("A 날짜 중" if lang == "ko" else "of A's days"), ".1%"),
                ("saron_share_original", t["saron"] + " A", ".2%"), ("saron_share_revised", t["saron"] + " B", ".2%")]
        out.append(table_html(P, cols, "t_pairs", lang, filt=False))
        if mid == "edition_pair_ratio":
            items = [(r.pair, float(r.han_ratio), 2) for _, r in P.iterrows()]
            out.append(fig(svg_bars(items, ".2f", label_w=300), ("글자 수 비율 B/A. 1 보다 크면 수정본이 원본보다 길다(현종개수실록)." if lang == "ko" else "Character ratio B/A; above 1 the revision is longer than the original (Supplemented Hyeonjong).")))
    elif mid == "gwanghae_deletion":
        g = D.gw.iloc[0]
        out.append('<div class="stats">' + "".join(f'<div class="stat"><div class="n">{v}</div><small>{k}</small></div>' for k, v in [
            (("기사 수 감소(중초→정초)" if lang == "ko" else "article drop (second→final)"), f"{g.article_drop:.1%}"),
            (("글자 수 감소" if lang == "ko" else "character drop"), f"{g.han_drop:.1%}"),
            (("산삭 표시 글자 비율" if lang == "ko" else "share of characters marked deleted"), f"{g.marked_deleted_share:.1%}"),
            (("산삭 표시가 있는 기사" if lang == "ko" else "articles with deletion marks"), f"{int(g.articles_with_deletion_marks):,}")]) + "</div>")
        Y = D.gwy
        out.append(fig(svg_lines([(("산삭 표시 비율" if lang == "ko" else "marked deleted"), [(int(r.year_ce), float(r.marked_deleted_share)) for _, r in Y.iterrows()], 1),
                                  (("글자 수 감소율" if lang == "ko" else "character drop"), [(int(r.year_ce), float(r.han_drop)) for _, r in Y.iterrows()], 0)], ".0%", xstep=2),
                       ("연도별. 산삭 표시 비율(중초본 안의 削 표지)과 정초본까지의 글자 수 감소율." if lang == "ko" else "By year: share of characters inside deletion marks in the second draft, and the character drop to the final draft.")))
        out.append(table_html(Y, [("year_ce", t["year"], None), ("n_articles", t["articles"] + " (2nd)", ",.0f"), ("final_articles", t["articles"] + " (final)", ",.0f"), ("n_han", t["chars"] + " (2nd)", ",.0f"), ("final_han", t["chars"] + " (final)", ",.0f"), ("marked_deleted_share", ("산삭 표시" if lang == "ko" else "marked deleted"), ".1%"), ("han_drop", ("글자 감소" if lang == "ko" else "char. drop"), ".1%")], "t_gw", lang, filt=False))
    elif mid == "solar_eclipse_match":
        s = D.solar.copy()
        s["type_l"] = s.type.map(t["type_names"]); s["window_l"] = s.window.map(t["windows"])
        w1 = s[s.window == "match_seoul_w1"]
        order = ["observed", "ritual", "not_occurred", "forecast", "discussion", "other", "all"]
        w1 = w1.set_index("type").loc[[o for o in order if o in set(w1.type)]].reset_index()
        items = [(f"{r.type_l} (n={int(r.n)})", float(r.rate), 1 if r.type == "observed" else 2) for _, r in w1.iterrows()]
        errs = {f"{r.type_l} (n={int(r.n)})": (float(r.ci_lo), float(r.ci_hi)) for _, r in w1.iterrows()}
        out.append(fig(svg_bars(items, ".0%", label_w=300, errors=errs), ("유형별 일치율(서울 가시 일식, ±1일)과 윌슨 95% 구간. 관측 보고가 대표 수치다." if lang == "ko" else "Match rate by type (eclipse visible from Seoul, ±1 day) with Wilson 95% intervals. Observation reports are the headline.")))
        out.append(table_html(s, [("type_l", ("유형" if lang == "ko" else "type"), None), ("window_l", ("대조 창" if lang == "ko" else "window"), None), ("n", t["n"], ",.0f"), ("matched", ("일치" if lang == "ko" else "matched"), ",.0f"), ("rate", t["share"], ".1%"), ("ci_lo", "95% lo", ".1%"), ("ci_hi", "95% hi", ".1%")], "t_solar", lang, filt=False))
        rec = D.solar_rec
        out.append("<p>" + (f"거꾸로 보면: 1392~1863년에 서울에서 보였을 계산 일식 {len(rec)}회 가운데 ±1일 안에 「日食」 기사가 있는 것은 {int(rec.has_article_w1.sum())}회({rec.has_article_w1.mean():.0%})다. 식분별 포착률은 이 판에서 따로 내지 않았다."
                             if lang == "ko" else
                             f"Seen the other way round: of the {len(rec)} computed eclipses visible from Seoul in 1392–1863, {int(rec.has_article_w1.sum())} ({rec.has_article_w1.mean():.0%}) have a '日食' article within ±1 day. Capture rates by magnitude are not broken out in this version.") + "</p>")
        A = D.solar_art.copy(); A["type_l"] = A.type.map(t["type_names"])
        out.append("<h3>" + ("기사 전체(322건, 날짜 있는 것)" if lang == "ko" else "All dated articles (322)") + "</h3>" +
                   table_html(A, [("article_id", "ID", None), ("solar_date", ("양력(1582년 전은 율리우스력)" if lang == "ko" else "solar date (Julian before 1582)"), None), ("type_l", ("유형" if lang == "ko" else "type"), None), ("match_seoul_w1", ("서울 ±1일" if lang == "ko" else "Seoul ±1d"), None), ("match_earth_w1", ("지구 ±1일" if lang == "ko" else "Earth ±1d"), None), ("days_to_nearest_seoul_eclipse", ("가장 가까운 서울 일식까지(일)" if lang == "ko" else "days to nearest Seoul eclipse"), ",.0f"), ("nikh_url", t["nikh_link"], None)], "t_solar_art", lang))
    elif mid == "lunar_eclipse_match":
        l = D.lunar.copy(); l["window_l"] = l.window.map(lambda w: t["windows"].get(w if w != "match_seoul_w1" else "match_seoul_w1_l", w))
        out.append(table_html(l, [("window_l", ("대조 창" if lang == "ko" else "window"), None), ("n", t["n"], ",.0f"), ("matched", ("일치" if lang == "ko" else "matched"), ",.0f"), ("rate", t["share"], ".1%"), ("ci_lo", "95% lo", ".1%"), ("ci_hi", "95% hi", ".1%")], "t_lunar", lang, filt=False))
        A = D.lunar_art
        out.append(table_html(A, [("article_id", "ID", None), ("solar_date", ("양력" if lang == "ko" else "solar date"), None), ("match_seoul_w1", ("서울 ±1일" if lang == "ko" else "Seoul ±1d"), None), ("nikh_url", t["nikh_link"], None)], "t_lunar_art", lang))
    elif mid == "venus_phase":
        pg = D.venus_pg
        out.append(fig(svg_lines([("Z", [(float(r.period), float(r.Z)) for _, r in pg.iterrows()], 0)], ",.0f", xstep=100, bands=[(580, 588, "583.92")]),
                       ("300~900일 주기 스캔의 레일리 Z. 띠는 금성 회합주기 583.92일." if lang == "ko" else "Rayleigh Z across trial periods 300–900 days; the band marks the 583.92-day synodic period.")))
        ph = D.venus_days.phase_days
        bins = list(range(-292, 293, 12)); hist = [int(((ph >= a) & (ph < a + 12)).sum()) for a in bins[:-1]]
        items = [(f"{a:+d}…{a+12:+d}", float(h), 1 if abs(a + 6) <= 90 else 2) for a, h in zip(bins[:-1], hist)]
        out.append(fig(svg_bars(items, ",.0f", row_h=14, label_w=110, xlabel=("기록 일수" if lang == "ko" else "record days")), ("내합(0) 기준 위상별 기록 일수. 내합 ±90일(진한 색)에 66%가 몰리고 내합 당일 부근은 비어 있다." if lang == "ko" else "Record days by phase relative to inferior conjunction (0). 66% lie within ±90 days (darker); the conjunction itself is nearly empty.")))
        out.append(table_html(D.venus.T.reset_index().rename(columns={"index": "key", 0: "value"}), [("key", "", None), ("value", "", None)], "t_venus", lang, filt=False))
    elif mid in ("comet_years", "earthquake_articles"):
        Y = D.comet if mid == "comet_years" else D.quake
        bands = [(y - 0.5, y + 0.5, "Halley") for y in (1456, 1531, 1607, 1682, 1759, 1835)] if mid == "comet_years" else None
        out.append(fig(svg_lines([(t["articles"], [(int(r.year_ce), float(r.n_articles)) for _, r in Y.iterrows()], 0)], ",.0f", bands=bands),
                       ("연도별 키워드 기사 수(본실록). 띠는 핼리 혜성 회귀 연도." if lang == "ko" else "Keyword articles per year (principal editions). Bands: Halley apparition years.") if mid == "comet_years" else ("연도별 「地震」 기사 수(본실록)." if lang == "ko" else "'地震' articles per year (principal editions).")))
        out.append(table_html(Y, [("year_ce", t["year"], None), ("n_articles", t["articles"], ",.0f"), ("n_days", ("기록 일수" if lang == "ko" else "days"), ",.0f")], "t_y", lang))
        if mid == "earthquake_articles":
            Q = D.quake_prov.copy(); Q["decade"] = Q.year_ce // 10 * 10
            Qd = Q.drop(columns="year_ce").groupby("decade").sum().reset_index()
            cols = [("decade", t["decade"], None)] + [(c, c, ",.0f") for c in Qd.columns if c != "decade"]
            out.append("<h3>" + ("연대·지역" if lang == "ko" else "By decade and province") + "</h3>" + table_html(Qd, cols, "t_qp", lang, filt=False))
    elif mid == "summer_cold":
        W = D.weather[D.weather.reliable]
        out.append(fig(svg_lines([(("서리·눈" if lang == "ko" else "frost+snow"), [(int(r.decade), float(r.frost_snow_per_1000)) for _, r in W.iterrows()], 0),
                                  (("우박" if lang == "ko" else "hail"), [(int(r.decade), float(r.hail_per_1000)) for _, r in W.iterrows()], 1)], ".0f", xstep=50, bands=[(1640, 1719, "1640–1719")]),
                       ("10년 단위, 천기 분류 기사 1,000건당 기록일. 천기 기사 100건 미만인 연대(1780년대 이후 대부분)는 뺐다. 띠는 1640~1719년." if lang == "ko" else "By decade, record days per 1,000 weather-class articles; decades with fewer than 100 such articles (most after the 1780s) are omitted. Band: 1640–1719.")))
        out.append(table_html(D.weather, [("decade", t["decade"], None), ("weather_class_articles", ("천기 기사" if lang == "ko" else "weather-class articles"), ",.0f"), ("frost_days", ("서리 일" if lang == "ko" else "frost days"), ",.0f"), ("snow_days", ("눈 일" if lang == "ko" else "snow days"), ",.0f"), ("hail_days", ("우박 일" if lang == "ko" else "hail days"), ",.0f"), ("frost_snow_per_1000", ("서리·눈/1,000" if lang == "ko" else "frost+snow/1,000"), ".1f"), ("hail_per_1000", ("우박/1,000" if lang == "ko" else "hail/1,000"), ".1f"), ("reliable", ("그림 포함" if lang == "ko" else "plotted"), None)], "t_w", lang, filt=False))
    elif mid == "clan_concentration":
        C = D.clan; M = D.clan_mk
        out.append(fig(svg_lines([(("고위직 첫 임명자" if lang == "ko" else "high-office appointees"), [(float(r.mid_year), float(r.top10_resampled)) for _, r in C.iterrows()], 0),
                                  (("하한(결측=별개 성관)" if lang == "ko" else "lower bound"), [(float(r.mid_year), float(r.top10_lower_bound)) for _, r in C.iterrows()], 2),
                                  (("문과 급제자" if lang == "ko" else "exam passers"), [(float(r.mid_year), float(r.top10_resampled)) for _, r in M.iterrows()], 1)], ".2f", xstep=50),
                       (f"상위 10개 성관 점유율, 구간마다 {int(C.resample_n.iloc[0])}명 재표집 1,000회 평균. 표에 95% 구간." if lang == "ko" else f"Top-10 clan share, mean of 1,000 resamples of {int(C.resample_n.iloc[0])} per period; 95% intervals in the table.")))
        out.append(table_html(C, [("period", t["period"], None), ("first_appointees", ("첫 임명자" if lang == "ko" else "first appointees"), ",.0f"), ("missing_share_after", ("보충 후 결측" if lang == "ko" else "unmatched after fill"), ".1%"), ("n", "n", ",.0f"), ("n_clans", ("성관 수" if lang == "ko" else "clans"), ",.0f"), ("top10_resampled", ("상위 10 (재표집)" if lang == "ko" else "top-10 (resampled)"), ".3f"), ("top10_ci_lo", "95% lo", ".3f"), ("top10_ci_hi", "95% hi", ".3f"), ("top10_lower_bound", ("하한" if lang == "ko" else "lower bound"), ".3f"), ("hhi", "HHI", ".4f"), ("effective_clans", ("유효 성관 수" if lang == "ko" else "effective clans"), ".1f"), ("top5", ("상위 5" if lang == "ko" else "top 5"), None)], "t_clan", lang, filt=False))
        f = D.clan_fill
        out.append("<p class='src'>" + (f"첫 임명자 {f['first_appointees']:,}명: 인물 데이터에서 성관 확인 {f['fill']['person_table']:,}, 문과방목으로 보충 {f['fill']['roster_fill']:,}, 남은 결측 {f['fill']['still_missing']:,}. 보충 규칙을 성관을 아는 사람에게 적용한 정확도 {f['validation']['accuracy']:.1%}. 구간 순서와 재표집 점유율의 스피어만 ρ = {f['spearman_resampled'][0]:.2f}, 하한 ρ = {f['spearman_lower'][0]:.2f}."
                                        if lang == "ko" else
                                        f"{f['first_appointees']:,} first appointees: clan from the person table {f['fill']['person_table']:,}, filled from the roster {f['fill']['roster_fill']:,}, still unmatched {f['fill']['still_missing']:,}. Fill rule accuracy on people with a known clan {f['validation']['accuracy']:.1%}. Spearman ρ of period order vs resampled share {f['spearman_resampled'][0]:.2f}; lower bound ρ = {f['spearman_lower'][0]:.2f}.") + "</p>")
    elif mid in ("royal_lecture_share", "memorial_share", "justice_share", "relief_share", "eonmun_articles", "slave_share"):
        R = {"royal_lecture_share": D.lecture, "memorial_share": D.memorial, "justice_share": D.justice, "relief_share": D.relief, "eonmun_articles": D.eonmun, "slave_share": D.slave}[mid]
        col = "justice_share" if mid == "justice_share" else ("n_keyword" if mid == "eonmun_articles" else "keyword_share")
        items = [(r[kc], float(r[col]), 0) for _, r in R.sort_values("king_no").iterrows()]
        out.append(fig(svg_bars(items, m["fmt"], row_h=20, label_w=200), ("왕대별(본실록, 날짜 있는 기사)." if lang == "ko" else "By reign (principal editions, dated articles).")))
        cols = [(kc, t["reign"], None), ("n_articles", t["articles"], ",.0f")]
        if mid == "justice_share":
            cols += [("n_justice", ("사법 분류" if lang == "ko" else "justice-classified"), ",.0f"), ("justice_share", t["share"], ".1%")]
        else:
            cols += [("n_keyword", ("키워드 기사" if lang == "ko" else "keyword articles"), ",.0f"), ("keyword_share", t["share"], ".2%")]
            if mid == "memorial_share":
                cols += [("n_classified", ("정론-간쟁 분류" if lang == "ko" else "classified remonstrance"), ",.0f"), ("classified_share", t["share"], ".2%")]
            if mid == "eonmun_articles":
                cols += [("n_keyword_justice", ("사법 분류와 겹침" if lang == "ko" else "also justice-classified"), ",.0f")]
        out.append(table_html(R, cols, "t_r", lang, filt=False))
        if mid == "justice_share":
            Jd = D.justice_dec
            out.append(fig(svg_lines([(t["share"], [(int(r.decade), float(r.justice_share)) for _, r in Jd.iterrows()], 0)], ".0%", xstep=50), ("10년 단위 사법 분류 기사 비율." if lang == "ko" else "Share of justice-classified articles by decade.")))
            out.append(table_html(Jd, [("decade", t["decade"], None), ("n_articles", t["articles"], ",.0f"), ("n_justice", ("사법" if lang == "ko" else "justice"), ",.0f"), ("justice_share", t["share"], ".1%")] + [(c, c, ",.0f") for c in Jd.columns if c.startswith("사법-")], "t_jd", lang, filt=False))
        if mid == "relief_share":
            Yr = D.relief_y
            out.append(fig(svg_lines([(t["share"], [(int(r.year_ce), float(r.keyword_share)) for _, r in Yr.iterrows()], 0)], ".0%", bands=[(1670, 1671, "1670–71"), (1695, 1696, "1695–96")]), ("연도별 비율. 띠는 경신(1670~71)·을병(1695~96) 대기근." if lang == "ko" else "Share by year. Bands: the great famines of 1670–71 and 1695–96.")))
    elif mid == "death_penalty_mention":
        E = D.death
        out.append(fig(svg_lines([(("언급 기사/1,000" if lang == "ko" else "mentions per 1,000"), [(int(r.period[:4]) + 25, float(r.mentions_per_1000)) for _, r in E.iterrows()], 2),
                                  (("집행 확인율 보정" if lang == "ko" else "× execution-confirmed rate"), [(int(r.period[:4]) + 25, float(r.mentions_x_exec_rate_per_1000)) for _, r in E.iterrows()], 0)], ".1f", xstep=50),
                       ("50년 구간(중앙 연도). 보정치는 언급 기사 비율 × 표본에서 잰 집행 확인율." if lang == "ko" else "50-year periods (mid-year). The corrected line multiplies the mention rate by the execution-confirmed rate from the sample.")))
        out.append(table_html(E, [("period", t["period"], None), ("n_articles", t["articles"], ",.0f"), ("n_mentions", ("언급 기사" if lang == "ko" else "mentions"), ",.0f"), ("mentions_per_1000", "/1,000", ".1f"), ("events", ("표본 사건" if lang == "ko" else "sample events"), ",.0f"), ("executed_confirmed", ("집행 확인" if lang == "ko" else "executed"), ",.0f"), ("exec_rate", ("확인율" if lang == "ko" else "rate"), ".2f"), ("exec_ci_lo", "95% lo", ".2f"), ("exec_ci_hi", "95% hi", ".2f"), ("mentions_x_exec_rate_per_1000", ("보정/1,000" if lang == "ko" else "corrected/1,000"), ".2f")], "t_death", lang, filt=False))
        Rg = D.death_reign
        out.append(table_html(Rg, [(kc, t["reign"], None), ("n_articles", t["articles"], ",.0f"), ("n_mentions", ("언급 기사" if lang == "ko" else "mentions"), ",.0f"), ("mentions_per_1000", "/1,000", ".1f")], "t_dr", lang, filt=False))
    return "".join(out)


# ----------------------------------------------------------------- visual helpers
KING_SPANS = None


def king_spans(D):
    """[(king_no, label_ko, label_en, first_year, last_year)] for the 25 principal editions."""
    out = []
    for _, r in D.main_ed().iterrows():
        out.append((int(r.king_no), r.king_ko, r.king_en, int(r.first_solar[:4]), int(r.last_solar[:4])))
    return out


def density_strip(D, lang, width=1000, height=150) -> str:
    """Yearly character counts 1392–1863 as a bar strip, shaded by reign (alternating), reign labels below."""
    y = D.yearly.set_index("year_ce").n_han
    years = list(range(1392, 1911))
    vals = [float(y.get(yr, 0)) for yr in years]
    vmax = max(vals) or 1
    L, R, T, B = 8, 8, 10, 34
    pw, ph = width - L - R, height - T - B
    bw = pw / len(years)
    X = lambda yr: L + (yr - 1392) * bw
    spans = king_spans(D)
    out = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="characters per year, 1392–1863">']
    for i, (kn, ko, en, a, b) in enumerate(spans):
        out.append(f'<rect x="{X(a):.1f}" y="{T}" width="{max(X(b + 1) - X(a), 1):.1f}" height="{ph}" fill="var(--s{1 if i % 2 == 0 else 3})" fill-opacity=".10"/>')
        if b - a >= 14:
            out.append(f'<text x="{(X(a) + X(b + 1)) / 2:.1f}" y="{height - 20}" text-anchor="middle">{esc(ko if lang == "ko" else en)}</text>')
    for yr, v in zip(years, vals):
        h = v / vmax * ph
        out.append(f'<rect x="{X(yr):.2f}" y="{T + ph - h:.1f}" width="{max(bw - 0.4, 0.6):.2f}" height="{h:.1f}" fill="var(--s1)"><title>{yr}: {v:,.0f}</title></rect>')
    for yr in range(1400, 1911, 50):
        out.append(f'<text x="{X(yr):.1f}" y="{height - 4}" text-anchor="middle" fill="var(--fg3)">{yr}</text>')
    out.append("</svg>")
    return "".join(out)


def reign_ribbon(D, king_no, lang, width=1000, height=46) -> str:
    spans = king_spans(D)
    L, R = 8, 8
    pw = width - L - R
    X = lambda yr: L + (yr - 1392) / (1911 - 1392) * pw
    out = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="reign timeline">']
    for i, (kn, ko, en, a, b) in enumerate(spans):
        on = kn == king_no
        out.append(f'<rect x="{X(a):.1f}" y="6" width="{max(X(b + 1) - X(a) - 1, 1):.1f}" height="16" rx="2" fill="var(--s{2 if on else 1})" fill-opacity="{1 if on else .22}"><title>{esc(ko if lang == "ko" else en)} {a}–{b}</title></rect>')
        if on:
            out.append(f'<text x="{(X(a) + X(b + 1)) / 2:.1f}" y="38" text-anchor="middle" fill="var(--fg)">{esc(ko if lang == "ko" else en)} · {a}–{b}</text>')
    hl = [(X(a) + X(b + 1)) / 2 for kn, ko, en, a, b in spans if kn == king_no]
    for yr in (1400, 1500, 1600, 1700, 1800, 1900):
        if hl and abs(X(yr) - hl[0]) < 70:   # keep the axis label from colliding with the highlighted reign's label
            continue
        out.append(f'<text x="{X(yr):.1f}" y="38" text-anchor="middle" fill="var(--fg3)">{yr}</text>')
    out.append("</svg>")
    return "".join(out)


def blurb(text: str, limit: int = 120) -> str:
    """First whole sentence(s) of a takeaway up to about `limit` characters — the same rule in both languages."""
    import re as _re
    parts = _re.split(r"(?<=[.!?。])\s+", text.strip())
    out = ""
    for p in parts:
        if out and len(out) + len(p) > limit:
            break
        out = (out + " " + p).strip()
    return out


def take_block(text: str, lang: str, small=False) -> str:
    lab = "핵심" if lang == "ko" else "Key point"
    return f'<div class="take{" small" if small else ""}"><div class="l">{lab}</div><p>{esc(text)}</p></div>'


def headline(m, D, lang):
    """(value string, short label) shown as the key number of a metric."""
    t = T[lang]; mid = m["id"]; M = D.main_ed(); ko = lang == "ko"
    kc = KING_COL[lang][0]
    def share(tbl, col="keyword_share", num="n_keyword"):
        return tbl[num].sum() / tbl.n_articles.sum()
    if mid == "n_articles":
        return f"{int(D.ed.n_articles.sum()):,}", (f"판본 {len(D.ed)}종" if ko else f"{len(D.ed)} editions")
    if mid == "n_han":
        return f"{D.ed.n_han.sum()/1e6:.1f}M", (f"한자, 판본 {len(D.ed)}종" if ko else f"characters, {len(D.ed)} editions")
    if mid == "han_per_year":
        r = M.sort_values("han_per_year", ascending=False).iloc[0]
        return f"{r.han_per_year:,.0f}", (f"최고: {r[kc]}, 1년당" if ko else f"highest: {r[kc]}, per year")
    if mid == "median_len":
        return f"{D.articles_median:,.0f}", ("본실록 기사 중앙값(자)" if ko else "median article, principal editions")
    if mid == "saron_share":
        r = M.sort_values("saron_share", ascending=False).iloc[0]
        return f"{r.saron_share:.1%}", (f"최고: {r[kc]}" if ko else f"highest: {r[kc]}")
    if mid == "empty_month_share":
        r = M.sort_values("empty_months", ascending=False).iloc[0]
        return f"{int(r.empty_months)}", (f"기사 없는 달 최다: {r[kc]}" if ko else f"most empty months: {r[kc]}")
    if mid == "edition_pair_ratio":
        return f"{D.pairs.iloc[0].han_ratio:.2f}", ("선조수정 / 선조, 글자 수" if ko else "Revised Seonjo / Seonjo, characters")
    if mid == "shared_day_share":
        return f"{D.pairs.iloc[0].shared_share_of_revised:.0%}", ("선조수정실록 날짜 중 원본에도 있는 비율" if ko else "Revised Seonjo days also in the original")
    if mid == "gwanghae_deletion":
        return f"{D.gw.iloc[0].marked_deleted_share:.1%}", ("중초본 글자 중 산삭 표시" if ko else "second-draft characters marked deleted")
    if mid == "revised_saron_share":
        r = D.pairs.iloc[2]
        return f"{r.saron_share_revised:.1%}", ("숙종실록보궐정오의 사론 기사 비율" if ko else "comment share, Sukjong corrections")
    if mid == "solar_eclipse_match":
        r = D.solar[(D.solar.type == "observed") & (D.solar.window == "match_seoul_w1")].iloc[0]
        return f"{r.rate:.1%}", (f"관측 보고 {int(r.n)}건 중 서울 가시 일식 일치" if ko else f"of {int(r.n)} observation reports match a Seoul eclipse")
    if mid == "lunar_eclipse_match":
        r = D.lunar.set_index("window").loc["match_seoul_w1"]
        return f"{r.rate:.1%}", (f"월식 기사 {int(r.n)}건 중 ±1일 일치(유형 미분류)" if ko else f"of {int(r.n)} articles, untyped")
    if mid == "venus_phase":
        return f"{D.venus.iloc[0].best_period_days:.1f}", ("일 — 기록이 재현한 주기(금성 583.92)" if ko else "days recovered (Venus: 583.92)")
    if mid == "comet_years":
        return f"{int(D.comet.n_articles.sum()):,}", ("기사 · 정밀도 0.68" if ko else "articles · precision 0.68")
    if mid == "earthquake_articles":
        return f"{int(D.quake.n_articles.sum()):,}", ("기사 · 정밀도 0.76" if ko else "articles · precision 0.76")
    if mid == "summer_cold":
        W = D.weather[D.weather.reliable]
        a = W[(W.decade >= 1640) & (W.decade <= 1710)]; b = W[(W.decade >= 1500) & (W.decade <= 1630)]
        ra = a.frost_days.sum() + a.snow_days.sum(); rb = b.frost_days.sum() + b.snow_days.sum()
        ratio = (ra / a.weather_class_articles.sum()) / (rb / b.weather_class_articles.sum())
        return f"×{ratio:.1f}", ("1640–1719년 서리·눈 기록률 / 1500–1639년" if ko else "frost+snow rate 1640–1719 vs 1500–1639")
    if mid == "clan_concentration":
        C = D.clan
        return f"{C.top10_resampled.iloc[0]:.2f}→{C.top10_resampled.iloc[8]:.2f}", ("상위 10 성관 점유, 1392–1449 → 1800–1849" if ko else "top-10 clan share, 1392–1449 → 1800–1849")
    if mid == "royal_lecture_share":
        return f"{share(D.lecture):.1%}", ("기사 중 경연 키워드 · 정밀도 0.82" if ko else "of articles · precision 0.82")
    if mid == "memorial_share":
        return f"{share(D.memorial):.1%}", ("기사 중 상소·차자 키워드" if ko else "of articles mention a memorial")
    if mid == "justice_share":
        return f"{D.justice.n_justice.sum() / D.justice.n_articles.sum():.1%}", ("본실록 기사 중 사법 분류" if ko else "of articles classified under justice")
    if mid == "death_penalty_mention":
        r = D.death.loc[D.death.period == "1400–1449"].iloc[0]
        return f"{r.mentions_per_1000:.1f}", ("1400–1449년 언급 기사/1,000 — 정점" if ko else "mentions per 1,000 in 1400–1449, the peak")
    if mid == "relief_share":
        return f"{share(D.relief):.1%}", ("기사 중 진휼·흉년 키워드 · 정밀도 0.81" if ko else "of articles · precision 0.81")
    if mid == "eonmun_articles":
        return f"{int(D.eonmun.n_keyword.sum()):,}", ("언문 언급 기사(본실록)" if ko else "articles mentioning the script")
    if mid == "slave_share":
        return f"{share(D.slave):.1%}", ("기사 중 노비 키워드 · 정밀도 0.54" if ko else "of articles · precision 0.54")
    return "", ""


def king_takeaway(D, r, lang):
    M = D.main_ed().copy()
    kc = KING_COL[lang][0]
    def rank(col, asc=False):
        # (rank, number of editions sharing the value). Ties get the same "min" rank, so the text must say so:
        # two tied -> "joint n", three or more -> no rank, just how many share the value (1.1.1 fix: ten editions
        # with no commentary were each shown as a solitary "18th").
        v = M.loc[M.edition == r.edition, col].iloc[0]
        return int(M[col].rank(ascending=asc, method="min").loc[M.edition == r.edition].iloc[0]), int((M[col] == v).sum())
    (rk_h, tie_h), (rk_a, tie_a), (rk_s, tie_s) = rank("han_per_year"), rank("n_articles"), rank("saron_share")
    def rk_ko(rk, tie):
        return f"{rk}위" if tie == 1 else (f"공동 {rk}위" if tie == 2 else f"{tie}대가 같은 값")
    def rk_en(rk, tie, lead="rank "):
        return f"{lead}{rk}" if tie == 1 else (f"joint {lead}{rk}" if tie == 2 else f"{tie} editions share this value")
    J = D.justice.set_index("edition"); jv = float(J.loc[r.edition, "justice_share"]); jm = float(J.justice_share.median())
    Lc = D.lecture.set_index("edition"); lv = float(Lc.loc[r.edition, "keyword_share"]); lm = float(Lc.keyword_share.median())
    if lang == "ko":
        s = f"{r.edition_ko}은 재위 1년당 글자 수가 {len(M)}대 중 {rk_ko(rk_h, tie_h)}({r.han_per_year:,.0f}자), 기사 수는 {rk_ko(rk_a, tie_a)}다. 사론이 붙은 기사는 {r.saron_share:.1%}({rk_ko(rk_s, tie_s)})"
        s += "로 이 책에는 사관의 논평이 없다. " if r.saron_share == 0 else "다. "
        s += f"사법 분류 기사 비율은 {jv:.1%}로 {len(M)}대 중앙값 {jm:.1%}보다 {'높고' if jv > jm else '낮고'}, 경연 키워드 비율은 {lv:.1%}(중앙값 {lm:.1%})다. 키워드 지표는 모두 기록 관행의 영향을 받으므로 왕대 간 차이는 「무엇을 적었나」의 차이로 먼저 읽는다."
        if r.edition in ("wza", "wzb"):
            s += " 이 실록은 공공누리 4유형이라 건수만 셌고, 기사 제목·본문 발췌는 싣지 않았다."
    else:
        s = f"The {r.edition_en} {rk_en(rk_h, tie_h)} of {len(M)} in characters per reign-year ({r.han_per_year:,.0f}) and {rk_en(rk_a, tie_a, '')} in article count. {r.saron_share:.1%} of articles carry a historian's comment ({rk_en(rk_s, tie_s)})"
        s += ", so this edition has no commentary. " if r.saron_share == 0 else ". "
        s += f"Justice-classified articles are {jv:.1%} against a median of {jm:.1%} across reigns; royal-lecture keywords {lv:.1%} (median {lm:.1%}). Keyword metrics follow recording practice, so read differences between reigns first as differences in what was written down."
        if r.edition in ("wza", "wzb"):
            s += " This edition is KOGL Type 4, so only counts are used; no titles or excerpts are published."
    return s


# ----------------------------------------------------------------- pages
def metric_page(m, D, lang):
    t = T[lang]; L = m[lang]
    hv, hl = headline(m, D, lang)
    body = [f'<div class="eyebrow"><span class="tag layer">{esc(SERIES[m["series"]][lang])}</span><span class="tag">{esc(m["unit"])}</span></div>',
            f'<div class="mhero"><div><h1>{esc(L["name"])}</h1><p class="lead">{esc(L["definition"])}</p></div><div class="big">{esc(hv)}<small>{esc(hl)}</small></div></div>',
            take_block(m["takeaway"][lang], lang),
            '<div class="spec"><dl>', f'<dt>{t["formula"]}</dt><dd class="formula">{esc(L["formula"])}</dd>',
            f'<dt>{t["reading"]}</dt><dd>{esc(L["reading"])}</dd>', f'<dt>{t["caveat"]}</dt><dd>{esc(L["caveat"])}</dd>']
    if "external" in m:
        body.append(f'<dt>{t["external"]}</dt><dd>{esc(m["external"][lang])}</dd>')
    body.append("</dl></div>")
    body.append(reliability_card(m, D, lang))
    body.append(metric_figure(m, D, lang))
    body.append(f'<p class="files"><a href="../../data/{m["table"]}.csv">{t["download"]}: {m["table"]}.csv</a></p>')
    return page(lang, L["name"], "".join(body), depth=2, desc=L["definition"], active="metrics")


def metrics_index(D, lang):
    t = T[lang]
    body = [f"<h1>{t['metric_list']}</h1>"]
    for s, sl in SERIES.items():
        body.append(f"<h2>{esc(sl[lang])}</h2><div class='cards'>")
        for m in METRICS:
            if m["series"] == s:
                hv, hl = headline(m, D, lang)
                body.append(f'<a class="card s-{s}" href="{m["id"]}.html"><b>{esc(m[lang]["name"])}</b><span class="kv">{esc(hv)}<small>{esc(hl)}</small></span><small>{esc(m[lang]["definition"])}</small></a>')
        body.append("</div>")
    return page(lang, t["metric_list"], "".join(body), depth=2, active="metrics")


def king_page(r, D, lang):
    t = T[lang]; kc, ec = KING_COL[lang]
    eds = D.ed[D.ed.king_no == r.king_no]
    body = [f'<div class="eyebrow"><span class="tag">{int(r.king_no)}</span><span class="tag">{r.first_solar[:4]}–{r.last_solar[:4]}</span></div><h1>{esc(r[kc])} — {esc(r[ec])}</h1>',
            f'<div class="ribbon">{reign_ribbon(D, int(r.king_no), lang)}</div>',
            take_block(king_takeaway(D, r, lang), lang)]
    body.append('<div class="stats">' + "".join(f'<div class="stat"><div class="n">{v}</div><small>{k}</small></div>' for k, v in [
        (t["articles"], f"{int(r.n_articles):,}"), (t["chars"], f"{int(r.n_han):,}"), (t["reign"] + " (" + t["months"] + ")", f"{int(r.reign_months):,}"),
        (t["chars"] + " " + t["per_year"], f"{r.han_per_year:,.0f}"), (t["saron"] + " " + t["share"], f"{r.saron_share:.1%}")]) + "</div>")
    if len(eds) > 1:
        body.append("<h2>" + ("판본" if lang == "ko" else "Editions") + "</h2>" + table_html(eds, [(ec, t["edition"], None), ("n_articles", t["articles"], ",.0f"), ("n_han", t["chars"], ",.0f"), ("n_saron", t["saron"], ",.0f"), ("median_len", ("기사 길이 중앙값" if lang == "ko" else "median length"), ",.0f")], "t_k_ed", lang, filt=False))
    y = D.yearly_ed[D.yearly_ed.edition == r.edition]
    body.append(fig(svg_lines([(t["articles"], [(int(x.year_ce), float(x.n_articles)) for _, x in y.iterrows()], 0)], ",.0f", xstep=5 if len(y) < 60 else 10), ("이 판본의 연도별 기사 수. 즉위·승하 해는 앞뒤 왕대와 나뉘어 센다." if lang == "ko" else "Articles per year in this edition; accession and death years are split between adjoining reigns.")))
    # keyword shares vs all-reign median
    rows = []
    for name, tbl, col, mid in [(("경연" if lang == "ko" else "royal lecture"), D.lecture, "keyword_share", "royal_lecture_share"), (("상소·차자" if lang == "ko" else "memorials"), D.memorial, "keyword_share", "memorial_share"),
                                 (("사법 분류" if lang == "ko" else "justice-classified"), D.justice, "justice_share", "justice_share"), (("진휼·흉년" if lang == "ko" else "relief / famine"), D.relief, "keyword_share", "relief_share"),
                                 (("노비" if lang == "ko" else "slaves"), D.slave, "keyword_share", "slave_share"), (("언문(건수)" if lang == "ko" else "vernacular script (count)"), D.eonmun, "n_keyword", "eonmun_articles"),
                                 (("사형 언급/1,000" if lang == "ko" else "death-penalty mentions/1,000"), D.death_reign, "mentions_per_1000", "death_penalty_mention")]:
        me = tbl[tbl.king_no == r.king_no]
        if len(me):
            rows.append(dict(metric=name, value=float(me[col].iloc[0]), med=float(tbl[col].median()), mid=mid, spec=".2%" if col in ("keyword_share", "justice_share") else ",.1f"))
    kw = pd.DataFrame(rows)
    body.append("<h2>" + ("이 왕대의 지표" if lang == "ko" else "Metrics for this reign") + "</h2>")
    body.append('<div class="wrap"><table><thead><tr><th>' + ("지표" if lang == "ko" else "metric") + f'</th><th class="num">{t["ours"]}</th><th class="num">' + (f"{len(D.main_ed())}대 중앙값" if lang == "ko" else f"median of {len(D.main_ed())} reigns") + "</th></tr></thead><tbody>" +
                "".join(f'<tr><td><a href="../metrics/{x.mid}.html">{esc(x.metric)}</a></td><td class="num">{fmt(x.value, x.spec)}</td><td class="num">{fmt(x.med, x.spec)}</td></tr>' for _, x in kw.iterrows()) + "</tbody></table></div>")
    nikh_id = f"k{r.edition[1:]}"
    body.append(f'<p class="links"><a href="{NIKH}/search/inspectionMonthList.do?id={nikh_id}">{t["nikh_link"]}</a></p>')
    return page(lang, r[kc], "".join(body), depth=2, active="kings")


def kings_index(D, lang):
    t = T[lang]; kc, ec = KING_COL[lang]
    M = D.main_ed()
    body = [f"<h1>{t['king_list']}</h1>",
            '<p class="src">' + ("태조~순종 27대. 고종·순종실록은 공공누리 제4유형이라 건수만 셌다(제목·본문 발췌 없음)." if lang == "ko" else "Taejo to Sunjong, 27 reigns. The Gojong and Sunjong records are KOGL Type 4, so only counts are used (no titles or excerpts).") + "</p>",
            take_block(("세로 막대는 연도별 글자 수, 바탕의 띠는 왕대다. 기록은 세종~선조에서 두껍고 정조 이후 얇아진다. 아래 카드에서 왕대마다 기사 수·글자 수와 그 왕대의 지표를 본다." if lang == "ko" else
                        "Bars are characters per year; the shaded bands are reigns. The record is thick from Sejong to Seonjo and thins after Jeongjo. Each card opens a reign page with its counts and metrics."), lang, small=True),
            f'<div class="strip"><figure>{density_strip(D, lang)}<figcaption>' + ("연도별 한자 수(본실록), 1392–1910. 띠는 왕대." if lang == "ko" else "Characters per year (principal editions), 1392–1910; bands mark reigns.") + "</figcaption></figure></div>",
            fig(svg_bars([(r[kc], float(r.han_per_year), 0) for _, r in M.iterrows()], ",.0f", row_h=20, label_w=160, xlabel=(t["chars"] + " " + t["per_year"])), ("재위 1년당 글자 수(본실록)." if lang == "ko" else "Characters per reign-year (principal editions).")),
            "<div class='cards'>"]
    for _, r in M.iterrows():
        body.append(f'<a class="card s-A" href="{r.edition}.html"><b>{int(r.king_no)}. {esc(r[kc])}</b><small>{esc(r[ec])} · {int(r.n_articles):,} {t["articles"]} · {int(r.n_han):,} {t["chars"]}</small></a>')
    body.append("</div>")
    return page(lang, t["king_list"], "".join(body), depth=2, active="kings")


def home(D, lang):
    t = T[lang]
    M = D.main_ed()
    obs = D.solar[(D.solar.type == "observed") & (D.solar.window == "match_seoul_w1")].iloc[0]
    obsE = D.solar[(D.solar.type == "observed") & (D.solar.window == "match_earth_w1")].iloc[0]
    stats = [(f"{int(D.ed.n_articles.sum()):,}", (f"기사 · 판본 {len(D.ed)}종" if lang == "ko" else f"articles · {len(D.ed)} editions"), "metrics/n_articles.html"),
             (f"{D.ed.n_han.sum()/1e6:.1f}M", ("한자 글자" if lang == "ko" else "Chinese characters"), "metrics/n_han.html"),
             (f"{obs.rate:.0%}", ("일식 관측 보고가 서울 가시 일식과 맞는 비율" if lang == "ko" else "eclipse reports matching an eclipse visible from Seoul"), "metrics/solar_eclipse_match.html"),
             (f"{obsE.rate:.0%}", ("지구 어딘가의 일식과 맞는 비율" if lang == "ko" else "matching an eclipse anywhere on Earth"), "metrics/solar_eclipse_match.html"),
             (f"{D.venus.iloc[0].best_period_days:.1f}", ("태백주현 기록이 재현한 금성 주기(일)" if lang == "ko" else "Venus period (days) recovered from daytime sightings"), "metrics/venus_phase.html")]
    five = (["실록은 생각보다 고르지 않다 — 재위 1년당 글자 수가 세종~숙종의 10만 자에서 헌종·철종의 1만 자대로 떨어진다.",
             "일식 「관측 보고」 기사의 65%는 서울에서 실제로 보인 일식과, 95%는 지구 어딘가의 일식과 맞는다. 기사 유형을 가리지 않으면 24%다.",
             "낮에 금성을 보았다는 기록 2,937일은 금성 회합주기를 0.04% 오차로 재현한다 — 관측 기록은 관측이다.",
             "고위직 첫 임명자의 상위 10개 성관 점유율은 0.28에서 0.45로 올랐다. 벌열화는 수치로 남는다.",
             "「사형」 기사의 정점(세종)은 판결 재가 기록이다. 실록은 형정 통계의 자료가 아니다."]
            if lang == "ko" else
            ["The record is uneven: characters per reign-year fall from over 100,000 (Sejong–Sukjong) to the low ten-thousands (Heonjong, Cheoljong).",
             "65% of eclipse observation reports match an eclipse visible from Seoul and 95% one somewhere on Earth; untyped, the rate is 24%.",
             "2,937 days of daytime Venus sightings reproduce the planet's synodic period to 0.04%: observation records are observations.",
             "The top-10 clan share among first appointees to high office rose from 0.28 to 0.45 — concentration left a number.",
             "The Sejong peak in death-penalty articles is sentencing paperwork; the Sillok is not a source of penal statistics."])
    scope = ("범위는 태조~순종 27대(1392~1910)다. 다만 고종·순종실록의 원문 데이터는 공공누리 제4유형(변경 금지·비상업)이라, 본문을 가공·인용하지 않는 집계(기사 수·글자 수·국편 분류·키워드 건수)에만 쓰고, 기사 제목·본문 발췌·천문 대조에는 쓰지 않았다. 공개하는 표본 코딩 표에서도 이 두 실록 기사의 제목·인용문·요약은 비웠다(판정만 남김). 태조~철종 25대의 원문은 제1유형(출처 표시)이다."
             if lang == "ko" else
             "Scope: the 27 reigns from Taejo to Sunjong (1392–1910). The Gojong and Sunjong records are released under KOGL Type 4 (no derivatives, non-commercial), so they enter only counts that neither alter nor quote the text (articles, characters, NIKH classification, keyword hits); titles, text excerpts and the astronomical checks exclude them, and in the published coding tables their rows keep the judgement but have title, quote and summary blanked. The 25 reigns Taejo–Cheoljong are Type 1 (attribution).")
    body = [f'<div class="hero"><div class="glyph" aria-hidden="true">實錄</div><h1>{t["site"]}</h1><p class="lead">{esc(t["tagline"])}</p><p class="src" style="max-width:70ch">{esc(scope)}</p>'
            f'<div class="strip">{density_strip(D, lang)}<p class="src">' + ("연도별 한자 수 1392–1910(본실록). 띠는 왕대." if lang == "ko" else "Characters per year 1392–1910 (principal editions); bands mark reigns.") + '</p></div></div>',
            '<div class="take"><div class="l">' + ("핵심" if lang == "ko" else "Key points") + '</div><p>' + "<br>".join(f"{i+1}. {esc(x)}" for i, x in enumerate(five)) + "</p></div>",
            '<div class="stats">' + "".join(f'<a class="stat" href="{h}"><div class="n">{n}</div><small>{l}</small></a>' for n, l, h in stats) + "</div>",
            '<div class="note">' + ("숫자마다 <b>신뢰도 카드</b>가 붙어 있다. 원본에서 그대로 센 값인지, 천문 계산과 맞춰 본 비율인지, 손으로 코딩한 표본에서 잰 정밀도인지를 지표 면마다 적었다. 원문 전문은 싣지 않고 기사마다 국사편찬위원회 원문으로 연결한다."
                                   if lang == "ko" else
                                   "Every number carries a <b>reliability card</b>: whether it was counted straight from the source, compared with an astronomical computation, or measured on a hand-coded sample. The site carries no full text; each article links to the National Institute of Korean History.") + "</div>"]
    NUM = {"A": "1", "B": "2", "C": "3", "D": "4", "E": "5"}
    for s, sl in SERIES.items():
        body.append(f"<h2 class='num' data-n='{NUM[s]}'>{esc(sl[lang])}</h2><div class='cards'>")
        for m in METRICS:
            if m["series"] == s:
                hv, hl = headline(m, D, lang)
                body.append(f'<a class="card s-{s}" href="metrics/{m["id"]}.html"><b>{esc(m[lang]["name"])}</b><span class="kv">{esc(hv)}<small>{esc(hl)}</small></span><small>{esc(blurb(m["takeaway"][lang]))}</small></a>')
        body.append("</div>")
    body.append("<h2>" + t["king_list"] + "</h2>" + fig(svg_bars([(r[KING_COL[lang][0]], float(r.n_articles), 0) for _, r in M.iterrows()], ",.0f", row_h=18, label_w=150), ("왕대별 기사 수(본실록). 각 왕대 면으로 가려면 「왕대」 메뉴." if lang == "ko" else "Articles per reign (principal editions); see the Reigns menu for each reign's page.")))
    return page(lang, t["site"], "".join(body), depth=1, active="home")


def prior_page(D, lang):
    t = T[lang]; kc, ec = KING_COL[lang]
    body = [f"<h1>{t['nav_prior']}</h1>", take_block(("새로 보탠 것과 모아 정리한 것을 가른다. 왕별 기사 수(Bak & Oh), 조선 일식 기록 집계(안영숙·이용삼), 조선 전기 사론 수(차장섭), 실록의 형옥 기사 수(유승희)는 이미 있던 수치라 우리 재계산과 나란히 둔다. 어긋나면 둘 다 보인다." if lang == "ko" else
                                                        "Separates what is new here from what was already measured. Articles per reign (Bak & Oh), Joseon eclipse records (Ahn & Lee), early-Joseon historians' comments (Cha) and Sillok criminal cases (Yu) existed before; they sit next to our recount, and disagreements are shown rather than resolved."), lang, small=True), '<p class="lead">' + ("기존 연구가 이미 낸 수치는 이 사이트의 재계산과 나란히 보인다. 원문에서 직접 읽은 값만 실었다." if lang == "ko" else "Figures that earlier studies already produced are shown next to this site's recount. Only values read from the original publications are included.") + "</p>"]
    for k, p in PRIOR.items():
        body.append(f'<div class="spec"><p>{esc(p[lang])}</p><p class="src">{esc(p["cite"])}</p></div>')
    from check_articles import BAK_OH_2015
    M = D.ed[D.ed.edition.isin(BAK_OH_2015)].copy(); M["bak"] = M.edition.map(BAK_OH_2015); M["diff"] = M.n_dated - M.bak
    body.append("<h2>" + ("왕별 기사 수 — Bak & Oh (2015) 대 이 사이트" if lang == "ko" else "Articles per reign — Bak & Oh (2015) vs this site") + "</h2>" +
                table_html(M, [(ec, t["edition"], None), ("n_dated", t["dated"] + " (" + t["ours"] + ")", ",.0f"), ("bak", "Bak & Oh", ",.0f"), ("diff", ("차" if lang == "ko" else "diff"), ",.0f")], "t_bak", lang, filt=False))
    return page(lang, t["nav_prior"], "".join(body), depth=1, active="prior")


def data_page(D, lang, files):
    t = T[lang]
    body = [f"<h1>{t['nav_data']}</h1>", take_block(("기사 테이블 한 장(articles.csv.gz, 38만 행)이 이 사이트의 뼈대다. 지표는 전부 그 표와 천문 표에서 다시 만들 수 있고, 손으로 코딩한 판정도 전부 들어 있다. 원문은 없고 기사 ID로 국편에 간다." if lang == "ko" else
                                                       "One article table (articles.csv.gz, 380k rows) is the backbone; every metric can be rebuilt from it and the astronomical tables, and every hand-coded judgement is included. No text — article IDs link to NIKH."), lang, small=True), '<p class="lead">' + ("모든 표를 CSV로 내려받을 수 있다. datapackage.json 에 파일마다 라이선스와 원자료를 적었다. 기사 테이블(articles.csv)은 기사마다 한 행이며 본문은 들어 있지 않다." if lang == "ko" else "Every table is downloadable as CSV; datapackage.json lists the licence and sources of each file. The article table (articles.csv) has one row per article and no text.") + "</p>",
            '<div class="files">' + "".join(f'<a href="../data/{f}">{f}</a>' for f in files) + "</div>",
            '<p class="files"><a href="../data/datapackage.json">datapackage.json</a></p>',
            "<h2>" + t["license"] + "</h2><p>" + ("파생 표: 공공누리 제1유형 원자료의 2차 저작물로, 원자료 출처 표시를 유지하는 한 자유롭게 쓸 수 있다(이 사이트의 자체 저작 부분은 CC BY 4.0). 고종·순종실록(제4유형) 행은 본문을 담지 않은 건수·메타데이터만이며 `license` 열에 KOGL-4 로 표시했다 — 상업적 이용은 삼가 달라. 코드: MIT. 원문·인물 데이터는 국사편찬위원회, 문과방목은 한국학중앙연구원의 것이다." if lang == "ko" else "Derived tables are derivative works of KOGL Type 1 sources and may be used freely as long as the source attribution is kept (this site's own contributions: CC BY 4.0). Rows from the Gojong and Sunjong records (Type 4) carry counts and metadata only, no text, and are marked KOGL-4 in the `license` column; please refrain from commercial use of those rows. Code: MIT. Original text and person data belong to the National Institute of Korean History; the examination roster to the Academy of Korean Studies.") + "</p>"]
    return page(lang, t["nav_data"], "".join(body), depth=1, active="data")


def method_page(D, lang):
    t = T[lang]
    cal = D.cal.offset_from_new_moon_days.value_counts(dropna=False)
    n0, n1 = int(cal.get(0, 0)), int(cal.get(-1, 0) + cal.get(1, 0))
    ko = f"""
<h1>방법·한계</h1>
TAKE_METHOD_KO
<h2>자료</h2>
<p>{esc(SOURCES['nikh_xml']['ko'])} 그래서 범위는 태조부터 순종까지 1392~1910년이고, 고종·순종실록은 기사 테이블에 제목 없이(ID·날짜·글자 수·분류·링크만) 들어 있으며 키워드 표에도 문맥 발췌가 없다. 천문 대조(계열 C)는 태조~철종에서만 했다. 표본 코딩에는 두 실록의 기사도 들어가지만, 공개 코딩 표에서 그 기사의 제목·인용문·요약은 비웠다. 재위 햇수는 첫·마지막 날짜 기사의 JDN 차이로 재어 1896년 양력 전환 전후를 같은 잣대로 센다.</p>
<p>{esc(SOURCES['nikh_persons']['ko'])} {esc(SOURCES['aks_munkwa']['ko'])}</p>
<h2>세는 단위</h2>
<p>모든 수는 <b>기사</b> 단위다. 국편 XML에서 biblioData type="T" 인 요소 하나가 기사 하나이고, 전체 {int(D.ed.n_articles.sum()):,}건 가운데 {int(D.ed.n_dated.sum()):,}건에 날짜가 있다. 시계열은 본실록(광해군은 정초본)만 쓰고 수정·개수·보궐정오본은 판본 비교 계열에서만 다룬다. 글자 수는 기사 본문의 한자 수다.</p>
<h2>날짜</h2>
<p>실록의 날짜는 음력이다. 서기 연도와 음력 월일을 그대로 두고, 양력은 korean_lunar_calendar 로 환산했다. 1582년 10월 15일 이전은 율리우스력으로 표시한다. 1896년(건양 1) 1월 1일부터 조정은 양력을 썼고 국편 XML 도 그날부터 간지 자리에 「陽曆」을 적으므로, 그 기사들의 월일은 변환하지 않고 양력 그대로 둔다(`date_system` 열). 환산의 정확도는 천문으로 확인했다: 1392~1928년의 음력 매월 초하루 {len(D.cal):,}개를 DE406으로 계산한 합삭의 서울 지방평균시(UT1 + 동경 126.978°, ΔT 는 Stephenson–Morrison–Hohenkerk 2016 모형) 날짜와 대조하니 {n0:,}개({n0/len(D.cal):.1%})가 같은 날이고 {n1}개가 하루 차이, 이틀 이상 어긋난 달은 없었다. 그래서 일식·월식 대조 창을 ±1일로 두고 같은 날 기준 값도 함께 보인다. 날짜 있는 기사 가운데 26건은 변환 패키지가 거부한 날이라 양력이 비어 있다 — 패키지가 29일까지로 보는 달의 30일 23건, 31일 2건, 날짜 미상(99일) 1건. 원전 날짜의 오류인지 역서 차이인지는 KASI 연력표와 대조하기 전에는 확정하지 않는다. 그 밖에 일(日) 자리가 「??」인 기사 38건은 날짜 없는 기사로 셌다.</p>
<h2>천문 계산</h2>
<p>{esc(SOURCES['de406']['ko'])} 일식은 합삭마다 서울(37.57°N, 126.98°E)에서 태양과 달의 겉보기 원반이 겹치는지, 태양이 지평선 위에 있는지를 2분 간격으로 검사했다. 겉보기 반지름은 태양 696,000km·달 1,737.4km 로 두었고(695,700km 로 바꾸면 1528-11-22의 극미한 접촉 한 건이 빠져 184회가 된다), 표의 `newmoon_jd`·`jd` 열은 TT 율리우스일이다. 그렇게 얻은 1392~1863년 서울 가시 일식 {len(D.solar_rec)}회는 모두 Espenak–Meeus 목록에 있고, 목록의 1,125회는 전부 같은 날(±1일)의 합삭과 맞았다. 월식은 skyfield 의 월식 탐색 함수로 구하고 식 최대 때 달이 지평선 위에 있는지로 서울 가시 여부를 정했다. 시각 비교는 당시 백각법·경점법 때문에 이 판에서는 하지 않았다.</p>
<h2>키워드와 표본 코딩</h2>
<p>계열 C·D·E의 많은 지표는 한문 키워드로 기사를 고른다. 키워드는 뜻이 다른 자리에도 걸리므로(「日食一升」은 하루 한 되를 먹는다는 뜻이다) 지표마다 층화 표본을 손으로 코딩해 정밀도와 윌슨 95% 구간을 신뢰도 카드에 적었다. 일식 기사 332건은 전수를 유형 분류했고 34건을 다른 코더가 블라인드로 다시 코딩했다. 코딩은 코드북에 따라 복수의 언어모델 코더가 했고, 인용문은 모두 원문과 문자열로 대조했다. 코드북과 판정 전체를 공개한다.</p>
<h2>신뢰도 카드</h2>
<p>세 종류다. <b>집계값</b>은 원본에서 그대로 센 수이며 외부 수치(Bak & Oh 2015, 2026-09 색인)와 대조했다. <b>외부 대조값</b>은 천문 계산과 맞춰 본 비율이다. <b>표본 정밀도</b>는 키워드가 지표의 뜻대로 쓰인 비율이다. 키워드 지표의 건수는 정밀도를 곱해 읽어야 한다.</p>
<h2>한계</h2>
<ul><li>실록은 「일어난 일」이 아니라 「적은 일」의 기록이다. 빈도형 지표(재이·사형 언급·진휼)는 기록 관행의 영향을 받는다. 세종실록의 사형 언급 정점이 판결 재가 기록이었던 것이 그 예다.</li>
<li>국편의 분류·사론 태그·인물 연결은 현대 편집진의 것이고 책마다 세밀함이 다르다. 인물별 등장 건수는 오연결 때문에 지표로 쓰지 않았다.</li>
<li>성관 집중도의 방목 보충은 정확도 91%이고 1850년 이후는 결측 20%가 남는다.</li>
<li>월식 기사는 유형 분류를 하지 않아 일치율이 하한이다.</li></ul>
<h2>선행 연구</h2>
<p>이 사이트가 새로 보태는 것은 기사 단위 메타 테이블, 키워드 지표의 정밀도, 일식 기사의 유형별 일치율, 판본 쌍의 같은 잣대 비교, 광해군일기 산삭의 글자 단위 계량이다. 왕별 기사 수(Bak & Oh 2015), 조선 일식 기록 집계(안영숙·이용삼 2004), 조선 전기 사론 수(차장섭), 실록의 형옥 기사 수(유승희 2007)는 이미 있는 수치이므로 「선행 결과」 면에서 재계산과 나란히 보인다.</p>
<h2>출처 표시</h2>
<p>본 저작물은 '교육부 국사편찬위원회'에서 2022년 작성하여 공공누리 제1유형으로 개방한 '조선왕조실록 정보_실록원문'·'조선왕조실록 정보_부가정보 인물 데이터'를 이용하였으며, 해당 저작물은 '공공데이터포털(https://www.data.go.kr/data/15053647/fileData.do · /15053645/fileData.do)'에서 무료로 다운받으실 수 있습니다. 성관 보충에는 '한국학중앙연구원'이 공공데이터포털(https://www.data.go.kr/data/15052752/fileData.do)에 개방한 '조선조문과급제자'를 이용하였습니다. 천문 계산은 NASA/JPL DE406, 일식 목록은 Espenak & Meeus (NASA/TP-2006-214141)를 썼다.</p>
<h2>판</h2><p>1.0 (2026-11-02) — 첫 공개. 지표 24개, 판본 30종, 왕대 25.<br>1.1 ({BUILD_DATE}) — 고종·순종실록을 건수 집계에 포함(판본 33종, 왕대 27). 계열 C 와 표본 코딩은 태조~철종 그대로.<br>1.1.1 ({BUILD_DATE}) — 왕대 요약문의 동률 순위 표기 정정: 사론 비율이 0 인 왕대 10 을 각각 「18위」로 적던 것을 「10대가 같은 값」으로 바꿨다. 수치·표·데이터 파일은 그대로.</p>
"""
    en = f"""
<h1>Method and limits</h1>
TAKE_METHOD_EN
<h2>Sources</h2>
<p>{esc(SOURCES['nikh_xml']['en'])} The range is therefore Taejo to Sunjong, 1392–1910; the Gojong and Sunjong records appear in the article table without titles (ID, date, character count, classification and link only) and without context excerpts in the keyword table. The sky series (C) covers Taejo–Cheoljong only. Sample coding does include articles from the two records, but in the published coding tables their title, quote and summary are blanked. Reign length is measured as the JDN span between first and last dated article, the same rule before and after the 1896 calendar switch.</p>
<p>{esc(SOURCES['nikh_persons']['en'])} {esc(SOURCES['aks_munkwa']['en'])}</p>
<h2>Counting unit</h2>
<p>Everything is counted per <b>article</b>: one biblioData type="T" element in the NIKH XML. Of {int(D.ed.n_articles.sum()):,} articles, {int(D.ed.n_dated.sum()):,} carry a date. Time series use the principal editions only (the final draft for Gwanghaegun); revised and supplemented editions appear only in the editions series. Characters are the Chinese characters of the article text.</p>
<h2>Dates</h2>
<p>Sillok dates are lunar. The CE year and lunar month/day are kept as given; solar dates come from korean_lunar_calendar, shown in the Julian calendar before 15 October 1582. From 1 January 1896 (Geonyang 1) the court used the Gregorian calendar and the NIKH XML marks those days 陽曆, so their month and day are taken as given rather than converted (`date_system` column). The conversion was checked astronomically: the {len(D.cal):,} lunar month-starts of 1392–1928 were compared with DE406 new moons in Seoul local mean time (UT1 + 126.978° E; ΔT from the Stephenson–Morrison–Hohenkerk 2016 model) — {n0:,} ({n0/len(D.cal):.1%}) fall on the same day, {n1} one day off, none two or more. Eclipse matching therefore uses a ±1-day window, with the same-day value shown alongside. 26 dated articles have no solar date because the conversion package rejected the day: 23 are a 30th in a month the package gives 29 days, 2 are a 31st, 1 has an unknown day (99). Whether these are errors in the source or differences between calendars is left open until a check against the KASI chronological tables. A further 38 articles whose day reads '??' are counted as undated.</p>
<h2>Astronomy</h2>
<p>{esc(SOURCES['de406']['en'])} For every new moon the apparent discs of Sun and Moon were tested for overlap above the Seoul horizon (37.57° N, 126.98° E) at 2-minute steps. Apparent radii use 696,000 km for the Sun and 1,737.4 km for the Moon (with 695,700 km one grazing contact on 1528-11-22 drops out, giving 184); the `newmoon_jd` and `jd` columns are TT Julian dates. The {len(D.solar_rec)} eclipses visible from Seoul in 1392–1863 so obtained all appear in the Espenak–Meeus canon, and all 1,125 of its eclipses match a new moon within ±1 day. Lunar eclipses come from skyfield's eclipse finder; visibility is the Moon's altitude at maximum. Times of day were not compared in this version because of the period's hour systems.</p>
<h2>Keywords and sample coding</h2>
<p>Many metrics in series C, D and E select articles by Chinese-character keywords. Keywords also hit other meanings ('日食一升' is a daily ration of rice), so each keyword metric was hand-coded on a stratified sample and its precision with a Wilson 95% interval sits on the reliability card. All 332 eclipse articles were typed, and 34 were blind re-coded by another coder. Coding followed a codebook and was done by several language-model coders; every quotation was string-checked against the source. Codebooks and all judgements are published.</p>
<h2>Reliability cards</h2>
<p>Three kinds. <b>Exact counts</b> are read straight from the source and checked against external figures (Bak & Oh 2015; an independent 2026-09 index). <b>External matches</b> are rates of agreement with astronomical computation. <b>Sampled precision</b> is the share of keyword hits that mean what the metric says; keyword counts should be read multiplied by it.</p>
<h2>Limits</h2>
<ul><li>The Sillok records what was written down, not what happened. Frequency metrics (omens, death-penalty mentions, relief) reflect recording practice — the Sejong peak in death-penalty mentions turned out to be sentencing paperwork.</li>
<li>NIKH's classification, comment tags and person links are modern editorial work of varying granularity. Person appearance counts are not used as metrics because of mislinks.</li>
<li>The roster fill for clan concentration is 91% accurate, and 20% of seats remain unmatched after 1850.</li>
<li>Lunar-eclipse articles are not typed, so their match rate is a lower bound.</li></ul>
<h2>Prior work</h2>
<p>New here: the article-level table, precision for keyword metrics, eclipse match rates by article type, like-for-like comparison of edition pairs, and character-level deletion counts for the Gwanghaegun diary. Articles per reign (Bak & Oh 2015), Joseon eclipse records (Ahn & Lee 2004), early-Joseon historians' comments (Cha) and Sillok criminal cases (Yu 2007) already existed and are shown next to the recount on the Prior results page.</p>
<h2>Attribution</h2>
<p>This work uses the 'Veritable Records of the Joseon Dynasty — original text' and '— supplementary person data' created by the National Institute of Korean History (Ministry of Education) in 2022 and released under KOGL Type 1 at the Korean public data portal (https://www.data.go.kr/data/15053647/fileData.do · /15053645/fileData.do), and the 'Successful candidates of the civil service examination' released by the Academy of Korean Studies (https://www.data.go.kr/data/15052752/fileData.do). Astronomy: NASA/JPL DE406; eclipse canon: Espenak & Meeus (NASA/TP-2006-214141).</p>
<h2>Versions</h2><p>1.0 (2026-11-02) — first release: 24 metrics, 30 editions, 25 reigns.<br>1.1 ({BUILD_DATE}) — Gojong and Sunjong added to the counts (33 editions, 27 reigns); series C and sample coding unchanged (Taejo–Cheoljong).<br>1.1.1 ({BUILD_DATE}) — tie wording fixed in the reign summaries: the ten reigns with no historian's comment were each shown as a solitary "rank 18"; they now read "10 editions share this value". No number, table or data file changed.</p>
"""
    ko = ko.replace("TAKE_METHOD_KO", take_block("세는 단위는 기사, 날짜는 음력 원문 그대로에 양력 환산을 더한 것, 천문은 DE406 직접 계산이다. 키워드 지표는 손으로 코딩한 표본의 정밀도를 곱해 읽는다. 실록은 「일어난 일」이 아니라 「적은 일」의 기록이라는 한계가 모든 빈도형 지표에 걸린다.", "ko", small=True))
    en = en.replace("TAKE_METHOD_EN", take_block("Articles are the unit; dates are the lunar originals plus a solar conversion; astronomy is computed directly from DE406. Keyword metrics are read multiplied by the precision of hand-coded samples. The Sillok records what was written, not what happened — a limit that applies to every frequency metric.", "en", small=True))
    return page(lang, t["nav_method"], f'<div class="prose">{ko if lang == "ko" else en}</div>', depth=1, active="method")


def reading_page(D, lang):
    t = T[lang]
    obs = D.solar[(D.solar.type == "observed") & (D.solar.window == "match_seoul_w1")].iloc[0]
    obsE = D.solar[(D.solar.type == "observed") & (D.solar.window == "match_earth_w1")].iloc[0]
    v = D.venus.iloc[0]; g = D.gw.iloc[0]; C = D.clan
    M = D.main_ed()
    top = M.sort_values("han_per_year", ascending=False).iloc[0]; low = M.sort_values("han_per_year").iloc[0]
    ko = f"""
<h1>읽기용 판</h1>
<p class="lead">표와 그림 대신 산문으로 읽는 1.0의 결과다. 수치는 모두 지표 면에 있고, 여기서는 무엇이 보였는지만 적는다. 고종·순종실록은 공공누리 제4유형(변경 금지·비상업)이라 건수 집계에만 넣고 본문 발췌는 싣지 않았다(공개 코딩 표에서도 그 기사의 제목·인용문은 비웠다).</p>
TAKE_READ_KO
<h2>얼마나 적었나</h2>
<p>태조부터 순종까지 27대의 본실록은 기사 {int(M.n_articles.sum()):,}건, 한자 {M.n_han.sum()/1e6:.1f}백만 자다(고종·순종은 건수만 셌다). 재위 1년당 글자 수로 보면 {top.king_ko}실록이 {top.han_per_year:,.0f}자로 가장 촘촘하고 {low.king_ko}실록이 {low.han_per_year:,.0f}자로 가장 성글다. 성종·중종·선조·숙종이 10만 자를 넘고 정조 이후 급히 줄어든다. 국편이 「후기로 갈수록 기록이 빈약하다」고 적은 것이 이 수치다.</p>
<p>사론(史臣曰)은 성종실록에서 처음 2%를 넘고 중종·명종·선조에서 가장 많다가 정조실록부터 하나도 없다. 조선 전기의 사론을 손으로 센 차장섭의 표와 국편 태그 수는 왕대마다 수십 건 안에서 맞는다.</p>
<h2>판본이 갈린 곳</h2>
<p>선조수정실록은 원본의 기사 수로 7%, 글자 수로 10%다. 국편 해제의 「1/5」은 권수 인상이다. 수정본 기사가 있는 날의 60%는 원본에도 기사가 있다. 현종개수실록은 원본보다 기사가 13%, 글자가 34% 많다 — 개수는 삭감이 아니라 다시 쓰기였다. 광해군일기는 중초본에서 정초본으로 가며 기사가 {g.article_drop:.0%}, 글자가 {g.han_drop:.0%} 줄었고, 중초본 글자의 {g.marked_deleted_share:.0%}가 산삭 표시 안에 있다.</p>
<h2>하늘은 맞았나</h2>
<p>「日食」이 나오는 기사 332건을 읽어 유형을 나누니 셋 중 하나는 일식을 논의의 소재로 끌어온 상소·전교였고, 일곱 중 하나는 일식이 아니었다(「日食一升」은 하루 한 되를 먹는다는 뜻이다). 그날 일식이 있었다는 보고로 읽히는 84건 가운데 서울에서 실제로 보이는 계산 일식과 ±1일 안에 맞는 것은 {obs.rate:.0%}, 지구 어딘가에서 일어난 일식과 맞는 것은 {obsE.rate:.0%}다. 맞지 않는 쪽의 대부분은 「地下日食」처럼 해가 진 뒤의 일식을 계산대로 적은 것이다. 거꾸로 서울에서 보였을 일식 {len(D.solar_rec)}회 중 기사가 있는 것은 {D.solar_rec.has_article_w1.mean():.0%}다.</p>
<p>금성이 낮에 보였다는 太白晝見 기록 {int(v.n_days):,}일은 더 뚜렷하다. 기록일의 주기를 찾으면 {v.best_period_days:.1f}일이 나오고, 이것은 금성의 회합주기 583.92일과 0.04% 차이다. 기록의 {v.within_90d:.0%}가 내합 앞뒤 90일에 몰리고 내합 당일 부근은 비어 있다. 적어도 이 유형의 기록에는 실제 관측의 신호가 남아 있다.</p>
<h2>누가 벼슬을 했나</h2>
<p>정승·판서·참판·대사헌·대사간·도승지·관찰사·대제학에 처음 오른 사람의 성관을 50년마다 모으면 상위 10개 성관의 점유율이 {C.top10_resampled.iloc[0]:.2f}에서 {C.top10_resampled.iloc[8]:.2f}로 오른다. 같은 기간 문과 급제자 집단의 집중은 그보다 작다. 두 집단은 구성이 달라 이 차이를 승진 단계의 효과로 단정하지는 않는다.</p>
<h2>사형 기사는 사형이 아니다</h2>
<p>사형 표현이 나오는 행형 기사는 세종 대에 가장 많지만, 표본을 읽으면 그 대부분이 형조가 율을 적용해 아뢴 판결 보고이고 집행이 확인되는 것은 20건 중 2건이다. 표본에서는 16세기 후반~18세기 전반 구간의 집행 확인율이 높지만, 구간당 20건이라 분포를 확정하지는 않는다. 유승희가 『일성록』에서 센 정조~철종의 사죄 2,853건 가운데 실록에서 확인되는 사건은 111건뿐이다. 실록은 형정 통계의 자료가 아니다.</p>
"""
    en = f"""
<h1>Reading edition</h1>
<p class="lead">The 1.0 results in prose rather than tables. Every number is on a metric page; here is only what was seen. The Gojong and Sunjong records (KOGL Type 4, no derivatives) enter the counts only; no excerpts are published, and their rows in the coding tables carry judgements without title or quote.</p>
TAKE_READ_EN
<h2>How much was written</h2>
<p>The principal editions for the 27 reigns from Taejo to Sunjong hold {int(M.n_articles.sum()):,} articles and {M.n_han.sum()/1e6:.1f} million Chinese characters (Gojong and Sunjong counted only). Per reign-year the {top.king_en} records are the densest at {top.han_per_year:,.0f} characters and the {low.king_en} records the thinnest at {low.han_per_year:,.0f}. Seongjong, Jungjong, Seonjo and Sukjong exceed 100,000; after Jeongjo the density collapses. This is the number behind NIKH's remark that the record thins toward the end.</p>
<p>Historians' comments first exceed 2% of articles under Seongjong, peak under Jungjong, Myeongjong and Seonjo, and vanish from Jeongjo onward. Cha Jang-seop's hand count for early Joseon and the NIKH tags agree to within a few dozen per reign.</p>
<h2>Where the editions diverge</h2>
<p>The Revised Seonjo records are 7% of the original by articles and 10% by characters; NIKH's 'one fifth' is an impression by fascicle count. 60% of the revised edition's days also have an article in the original. The Supplemented Hyeonjong records have 13% more articles and 34% more characters than the original — a rewrite, not a cut. The Gwanghaegun diary lost {g.article_drop:.0%} of its articles and {g.han_drop:.0%} of its characters between drafts, and {g.marked_deleted_share:.0%} of the second draft's characters sit inside deletion marks.</p>
<h2>Was the sky right?</h2>
<p>Reading all 332 articles containing '日食', one in three turned out to be a memorial or edict using an eclipse as an argument, and one in seven was not an eclipse at all ('日食一升' is a daily ration of rice). Of the 84 read as a report that an eclipse occurred that day, {obs.rate:.0%} fall within ±1 day of a computed eclipse visible from Seoul and {obsE.rate:.0%} match an eclipse somewhere on Earth. Most of the rest are '地下日食' — eclipses after sunset entered as computed. Seen the other way, {D.solar_rec.has_article_w1.mean():.0%} of the {len(D.solar_rec)} eclipses visible from Seoul have an article.</p>
<p>The {int(v.n_days):,} days on which Venus was reported visible in daylight are sharper still. A period search returns {v.best_period_days:.1f} days, 0.04% from the synodic period of 583.92; {v.within_90d:.0%} of the records fall within 90 days of inferior conjunction and the conjunction itself is empty. At least this kind of record carries the signal of real observation.</p>
<h2>Who held office</h2>
<p>Grouping first appointees to the highest offices by 50-year period, the share of the top ten clans rises from {C.top10_resampled.iloc[0]:.2f} to {C.top10_resampled.iloc[8]:.2f}; concentration among examination passers over the same period is smaller. The two groups differ in composition, so the gap is not read as a promotion effect.</p>
<h2>A death-penalty article is not an execution</h2>
<p>Articles with capital-punishment terms are most frequent under Sejong, but the sample shows most of them are sentencing reports applying the code; execution is confirmed in 2 of 20. In the sample the confirmation rate is higher in the late 16th to early 18th century, but with 20 articles per period the distribution is not settled. Of the 2,853 capital cases Yu Seung-hui counted in the Ilseongnok for Jeongjo–Cheoljong, only 111 can be found in the Sillok. The Sillok is not a source of penal statistics.</p>
"""
    ko = ko.replace("TAKE_READ_KO", take_block("실록의 관측 기록은 계량에 쓸 수 있을 만큼 정확하고, 빈도형 기록은 기록 관행을 탄다. 이 둘을 갈라 읽는 것이 이 사이트의 한 문장 요약이다.", "ko"))
    en = en.replace("TAKE_READ_EN", take_block("The Sillok's observational entries are accurate enough for quantitative use; its frequency entries follow recording practice. Reading the two apart is this site in one sentence.", "en"))
    return page(lang, t["nav_reading"], f'<div class="prose">{ko if lang == "ko" else en}</div>', depth=1, active="reading")


DATA_FILES = ["articles.csv", "a_editions.csv", "a_yearly.csv", "a_monthly.csv", "a_length.csv", "b_pairs.csv", "b_gwanghae.csv", "b_gwanghae_yearly.csv",
              "c_solar.csv", "c_solar_articles.csv", "c_solar_eclipses_recorded.csv", "solar_eclipses_seoul.csv", "espenak_1392_1863.csv", "c_lunar.csv", "c_lunar_articles.csv", "lunar_eclipses_seoul.csv",
              "c_venus.csv", "c_venus_days.csv", "c_venus_periodogram.csv", "venus_inferior_conjunctions.csv", "c_comet.csv", "c_quake.csv", "c_quake_province.csv", "c_quake_articles.csv", "c_weather.csv",
              "d_clan.csv", "d_clan_munkwa.csv", "d_clan_fill.json", "a_yearly_by_edition.csv", "d_lecture.csv", "d_memorial.csv", "d_justice.csv", "d_justice_decade.csv",
              "e_death.csv", "e_death_reign.csv", "e_death_sample_summary.csv", "e_relief.csv", "e_relief_yearly.csv", "e_eonmun.csv", "e_slave.csv", "lunar_month_starts.csv", "keyword_hits.csv"]
MAX_ROWS = 60
GZIP_FILES = {"articles.csv", "keyword_hits.csv"}
CODING_FILES = ["solar_eclipse_codebook.md", "solar_eclipse_types.csv", "solar_eclipse_agreement.json", "precision_codebook.md", "death_penalty_codebook.md", "death_penalty_sample.csv"]


def write_datapackage(data_dir: Path, files) -> None:
    resources = []
    for f in files:
        if f in GZIP_FILES:
            f = f + ".gz"
        p = data_dir / f
        if not p.exists():
            continue
        df = pd.read_csv(p) if f.endswith(".csv") or f.endswith(".csv.gz") else None
        src = ["nikh_xml"]
        if f.startswith("d_clan"):
            src = ["nikh_persons", "aks_munkwa"]
        if f in ("solar_eclipses_seoul.csv", "lunar_eclipses_seoul.csv", "venus_inferior_conjunctions.csv", "lunar_month_starts.csv"):
            src = ["de406", "klc"] if f == "lunar_month_starts.csv" else ["de406"]
        if f == "espenak_1392_1863.csv":
            src = ["espenak"]
        desc = None
        if f.startswith(("d_lecture", "d_memorial", "d_justice.csv", "e_relief.csv", "e_eonmun", "e_slave", "e_death_reign")):
            desc = "n_articles here is the number of dated articles of the principal edition (equals a_editions.n_dated), the denominator of the shares; a_editions.n_articles counts all articles including undated front matter."
        resources.append({**({"description": desc} if desc else {}), "name": f.split(".")[0].lower().replace("/", "-"), "path": f, "format": "csv" + (" (gzip)" if f.endswith(".gz") else "") if ".csv" in f else f.rsplit(".", 1)[1], "encoding": "utf-8",
                          "rows": int(len(df)) if df is not None else None,
                          "licenses": [{"name": "KOGL-1-derivative + CC-BY-4.0", "path": "https://www.kogl.or.kr/info/license.do"}],
                          "sources": [{"title": SOURCES[k]["en"].split(". ")[0][:160], "path": SOURCES[k]["url"], "license": SOURCES[k]["license"]} for k in src]})
    pkg = {"profile": "data-package", "name": "sillok-metrics", "title": "Sillok Metrics — derived data", "version": VERSION, "created": BUILD_DATE,
           "homepage": "https://bowonkwon.github.io/Sillok-Metrics/", "contributors": [{"title": "Bowon Kwon", "role": "author"}],
           "description": "Article-level counts and metrics for the Veritable Records of the Joseon Dynasty (Taejo–Cheoljong). No article text is included; each article ID links to the NIKH site. Source data: NIKH (KOGL Type 1), AKS; astronomy from JPL DE406 and the Espenak–Meeus canon.",
           "resources": resources}
    (data_dir / "datapackage.json").write_text(json.dumps(pkg, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--derived", default="data/derived")
    ap.add_argument("--out", default="site")
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    D = Data(root / a.derived)
    out = root / a.out
    out.mkdir(exist_ok=True)   # a preview server may hold the folder open: clear its children, keep the folder
    for child in out.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    (out / "data" / "coding").mkdir(parents=True)
    files = []
    import gzip
    for f in DATA_FILES:
        p = root / a.derived / f
        if not p.exists():
            continue
        if f in GZIP_FILES:   # the two large tables ship gzipped (GitHub's 100 MB file limit; browsers and pandas read .gz directly)
            with open(p, "rb") as fi, gzip.open(out / "data" / (f + ".gz"), "wb", compresslevel=6) as fo:
                shutil.copyfileobj(fi, fo)
            files.append(f + ".gz")
        else:
            shutil.copy(p, out / "data" / f); files.append(f)
    for f in CODING_FILES:
        p = root / "data" / "coding" / f
        if not p.exists():
            continue
        if f.endswith(".csv"):
            # KOGL Type 4 editions (wza, wzb, wzc): judgements are kept, but any text taken from the records
            # (title, quote, summary) is blanked in the published copy
            c = pd.read_csv(p, encoding="utf-8-sig", dtype=str, keep_default_na=False)
            idcol = "id" if "id" in c.columns else "article_id"
            k4 = c[idcol].str[:3].isin(["wza", "wzb", "wzc"])
            for col in ("title", "quote", "summary", "time_text", "magnitude_text", "context"):
                if col in c.columns:
                    c.loc[k4, col] = ""
            c.to_csv(out / "data" / "coding" / f, index=False, encoding="utf-8")
        else:
            shutil.copy(p, out / "data" / "coding" / f)
        files.append("coding/" + f)
    write_datapackage(out / "data", DATA_FILES)
    (out / "index.html").write_text('<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0; url=ko/index.html"><title>Sillok Metrics</title></head><body><a href="ko/index.html">한국어</a> · <a href="en/index.html">English</a></body></html>', encoding="utf-8")
    n = 0
    for lang in ("ko", "en"):
        (out / lang / "metrics").mkdir(parents=True); (out / lang / "kings").mkdir(parents=True)
        (out / lang / "index.html").write_text(home(D, lang), encoding="utf-8"); n += 1
        (out / lang / "metrics" / "index.html").write_text(metrics_index(D, lang), encoding="utf-8"); n += 1
        for m in METRICS:
            (out / lang / "metrics" / f"{m['id']}.html").write_text(metric_page(m, D, lang), encoding="utf-8"); n += 1
        (out / lang / "kings" / "index.html").write_text(kings_index(D, lang), encoding="utf-8"); n += 1
        for _, r in D.main_ed().iterrows():
            (out / lang / "kings" / f"{r.edition}.html").write_text(king_page(r, D, lang), encoding="utf-8"); n += 1
        (out / lang / "prior.html").write_text(prior_page(D, lang), encoding="utf-8"); n += 1
        (out / lang / "data.html").write_text(data_page(D, lang, files), encoding="utf-8"); n += 1
        (out / lang / "method.html").write_text(method_page(D, lang), encoding="utf-8"); n += 1
        (out / lang / "reading.html").write_text(reading_page(D, lang), encoding="utf-8"); n += 1
    print("pages", n, "data files", len(files))


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    main()
