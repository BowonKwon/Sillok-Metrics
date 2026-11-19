"""Contents navigation shared by the sister sites: stable section ids, a section list on each page, a chapter list.

Section ids are written in the source, after the heading:  ## Dates {#dates}
The same id is used in Korean and English, so a link to a section survives a reworded heading and a change of language.
Everything works without JavaScript (the lists are plain links, the chapter list is <details>/<summary>).
NAV_JS only adds comfort: the "contents" button shows once the section list has scrolled away, the room above a
target is fitted to the measured height of the header, and the section is carried over when the language is switched.
"""
import html
import re

LABEL = {
    "ko": dict(chapters="장 목록", pos="{n}장 가운데 {i}장", here="지금 읽는 장", full="장과 절 전체 목차",
               in_ch="이 장의 절", in_page="이 면의 절", link="‘{t}’ 절로 바로 가는 링크", other="그 밖의 면",
               up="↑ 목차", up_label="이 면의 절 목록으로"),
    "en": dict(chapters="Chapters", pos="Chapter {i} of {n}", here="you are here", full="Full contents: chapters and sections",
               in_ch="In this chapter", in_page="On this page", link="Link to the section ‘{t}’", other="Other pages",
               up="↑ Contents", up_label="Back to the section list of this page"),
}
MIN_SECTIONS = 3  # a page gets a section list when it has at least this many sections
# Per-site settings (the rest of this file is the same on every sister site).
# STICKY_FROM: from this width (px) up the header stays on screen; below it the page scrolls it away. None: never stuck.
#              900 where the header is at most two lines there in both languages; a site with a longer menu starts at 1024.
# STICKY_GAP:  room above a section heading under the stuck header when no script runs — the tallest header from
#              STICKY_FROM up, plus 12px. The script measures the header and fits it.
# CSS_ALIAS:   custom properties for a site whose stylesheet names its colours differently (empty where they match).
STICKY_FROM = 1024
STICKY_GAP = "7.4rem"
CSS_ALIAS = ''
ID_LINE = re.compile(r"^(##)[ \t]+(.+?)[ \t]*\{#([a-z][a-z0-9-]*)\}[ \t]*$", re.M)
H2_LINE = re.compile(r"^##[ \t]+.+$", re.M)
H2_TAG = re.compile(r"<h2>(.*?)</h2>", re.S)
H2_ANY = re.compile(r"<h2\b([^>]*)>(.*?)</h2>", re.S)
ID_ATTR = re.compile(r"""\bid=(["']?)([^"'\s>]+)\1""")


def text(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def split_ids(src, where=""):
    """Take the {#id} off every second-level heading. Returns (source without ids, [id, ...]).
    Every second-level heading must carry an id, and ids must be unique on the page."""
    ids = [m.group(3) for m in ID_LINE.finditer(src)]
    n = len(H2_LINE.findall(src))
    if n != len(ids):
        bare = [l for l in H2_LINE.findall(src) if not ID_LINE.match(l)]
        raise ValueError(f"{where}: second-level heading without {{#id}}: {bare[:3]}")
    if len(set(ids)) != len(ids):
        raise ValueError(f"{where}: duplicate section id in {ids}")
    return ID_LINE.sub(lambda m: f"{m.group(1)} {m.group(2)}", src), ids


def anchor(body, ids, lang, where=""):
    """Give the <h2> elements of rendered html their ids and a link to themselves.
    Returns (html, [(id, heading html), ...])."""
    heads = H2_TAG.findall(body)
    if len(heads) != len(ids):
        raise ValueError(f"{where}: {len(heads)} <h2> in the html, {len(ids)} ids in the source")
    it = iter(ids)

    def sub(m):
        i = next(it)
        lab = html.escape(LABEL[lang]["link"].format(t=text(m.group(1))), quote=True)
        return f'<h2 id="{i}">{m.group(1)}<a class="hx" href="#{i}" aria-label="{lab}">#</a></h2>'
    return H2_TAG.sub(sub, body), list(zip(ids, heads))


H_ANY = re.compile(r"<h([23])\b([^>]*)>(.*?)</h\1>", re.S)
TOC_MARK = "<!--toc-->"  # where the section list goes, on pages that say so; otherwise just before the first section


def anchor_html(body, lang, where="", skip=(), with_h3=False):
    """For pages whose headings are written in code, ids included: add the link to itself to every <h2 ... id="...">.
    Every <h2> must carry an id (those listed in skip are left as they are and kept out of the section list).
    with_h3: third-level headings that carry an id are sections too (those without one are left alone).
    Returns (html, [(id, heading html without links), ...])."""
    items, seen = [], set()

    def sub(m):
        lv, attrs, inner = m.group(1), m.group(2), m.group(3)
        mi = ID_ATTR.search(attrs)
        if lv == "3" and not (with_h3 and mi):
            return m.group(0)
        if not mi:
            raise ValueError(f"{where}: <h2> without an id: {text(inner)[:40]!r}")
        i = mi.group(2)
        if i in seen:
            raise ValueError(f"{where}: duplicate section id {i}")
        seen.add(i)
        if i in skip:
            return m.group(0)
        items.append((i, re.sub(r"</?a\b[^>]*>", "", inner)))
        lab = html.escape(LABEL[lang]["link"].format(t=text(inner)), quote=True)
        return f'<h{lv}{attrs}>{inner}<a class="hx" href="#{i}" aria-label="{lab}">#</a></h{lv}>'
    return H_ANY.sub(sub, body), items


def page_toc(lang, items, chapter=False):
    """Section list for the head of a page; empty when the page has fewer than MIN_SECTIONS sections."""
    if len(items) < MIN_SECTIONS:
        return ""
    lab = LABEL[lang]["in_ch" if chapter else "in_page"]
    li = "".join(f'<li><a href="#{i}">{h}</a></li>' for i, h in items)
    return f'<nav class="toc" id="toc" aria-label="{lab}"><b>{lab}</b><ul>{li}</ul></nav>'


def with_toc(body, toc, lang):
    """Put the section list after the lead of the page, just before the first section,
    and a small fixed button at the end that leads back to it."""
    if not toc:
        return body.replace(TOC_MARK, "")
    t = LABEL[lang]
    up = f'<a class="totoc" href="#toc" aria-label="{t["up_label"]}">{t["up"]}</a>'
    if TOC_MARK in body:
        return body.replace(TOC_MARK, toc, 1) + up
    at = body.find("<h2 ")
    if at >= 0:  # a heading that opens a figure: the list goes before the figure, not inside it
        fig = re.search(r"<figure\b[^>]*>\s*$", body[:at])
        if fig:
            at = fig.start()
    return (toc + body if at < 0 else body[:at] + toc + body[at:]) + up


def chapter_list(lang, chapters, current, full_href, pos=None, label=None, here=None, full=None):
    """Collapsible list of all chapters for the head of a chapter page. chapters: [(href, title html), ...].
    pos: the small note beside the label; by default "Chapter i of n" (give it where chapters do not count from 1).
    label, here, full: other words for "Chapters", "you are here" and the link to the full contents."""
    t = LABEL[lang]
    li = []
    for k, (href, title) in enumerate(chapters):
        if k == current:
            li.append(f'<li><a href="{href}" aria-current="page">{title}</a> <small>{here or t["here"]}</small></li>')
        else:
            li.append(f'<li><a href="{href}">{title}</a></li>')
    if pos is None:
        pos = t["pos"].format(i=current + 1, n=len(chapters))
    return (f'<details class="chlist"><summary>{label or t["chapters"]} <small>{pos}</small></summary><ol>{"".join(li)}</ol>'
            f'<p><a href="{full_href}">{full or t["full"]}</a></p></details>')


def full_contents(lang, chapters, others, label=None):
    """Collapsible contents of the whole site for the home page.
    chapters, others: [(href, title html, [(id, heading html), ...]), ...]."""
    t = LABEL[lang]

    def tree(pages):
        out = []
        for href, title, items in pages:
            sub = "".join(f'<li><a href="{href}#{i}">{h}</a></li>' for i, h in items)
            out.append(f'<li><a href="{href}">{title}</a>{"<ul>" + sub + "</ul>" if sub else ""}</li>')
        return f'<ul class="tree">{"".join(out)}</ul>'
    rest = f'<b>{t["other"]}</b>{tree(others)}' if others else ""
    return f'<details class="chlist full"><summary>{label or t["full"]}</summary><div class="box">{tree(chapters)}{rest}</div></details>'


# .sibs is the side list of the metric sites, which follows the scroll: it has to start below the stuck header.
_STICKY = ("@media(min-width:%dpx){body{overflow-x:clip}h2[id],h3[id],figure[id],nav.toc{scroll-margin-top:var(--hh,%s)}"
           ".sibs{top:var(--hh,%s);max-height:calc(100vh - var(--hh,%s) - .8rem)}}\n"
           % (STICKY_FROM, STICKY_GAP, STICKY_GAP, STICKY_GAP)) if STICKY_FROM else ""
NAV_CSS = CSS_ALIAS + """
h2[id],h3[id],figure[id],nav.toc{scroll-margin-top:var(--hh,.9rem)}
@STICKY@
.hx{margin-left:.45rem;font-family:var(--body);font-size:.8em;font-weight:400;color:var(--fg3);opacity:0;transition:opacity .15s}.hx:hover{text-decoration:none;color:var(--accent)}
h2:hover .hx,h3:hover .hx,.hx:focus-visible{opacity:1}@media(hover:none){.hx{opacity:.6}}
nav.toc{border:1px solid var(--line);border-radius:10px;background:var(--card);padding:.7rem 1rem .8rem;margin:1.3rem 0 .2rem;font-size:.92rem;max-width:72ch}
nav.toc b{display:block;font-size:.84rem;font-weight:600;color:var(--fg2);margin-bottom:.3rem}
nav.toc ul{list-style:none;margin:0;padding:0;columns:2;column-gap:1.8rem;max-width:none}nav.toc li{margin:0;padding:.14rem 0;break-inside:avoid;line-height:1.5}
@media(max-width:640px){nav.toc ul{columns:1}}
.chlist{margin:.1rem 0 1rem;font-size:.92rem}.chlist summary{font-size:.92rem}.chlist summary small{color:var(--fg3);margin-left:.4rem}
.chlist ol,.chlist .box{list-style:none;margin:.5rem 0 .4rem;padding:.6rem 1rem .7rem;border:1px solid var(--line);border-radius:10px;background:var(--card);max-width:72ch}
.chlist li{margin:0;padding:.16rem 0;line-height:1.5}.chlist li small{color:var(--fg3);margin-left:.35rem;white-space:nowrap}
.chlist a[aria-current]{color:var(--fg);font-weight:600}.chlist p{margin:.3rem 0 0;font-size:.88rem}
.chlist .tree,.chlist .tree ul{list-style:none;margin:0;padding:0}.chlist .tree>li{padding:.3rem 0}.chlist .tree>li>a{font-weight:600}
.chlist .tree ul{padding-left:1rem;font-size:.95em}.chlist .box b{display:block;margin:.7rem 0 .1rem;font-size:.84rem;font-weight:600;color:var(--fg2);border-top:1px solid var(--line2);padding-top:.6rem}
.totoc{position:fixed;right:.9rem;bottom:.9rem;z-index:6;font-size:.84rem;font-weight:600;line-height:1;color:var(--fg);background:var(--card);border:1px solid var(--line);border-radius:999px;padding:.55rem .85rem;box-shadow:var(--shadow)}
.tolang{position:fixed;bottom:.9rem;right:calc(.9rem + var(--tocw,0px));z-index:6;font-size:.84rem;font-weight:600;line-height:1;color:var(--fg);background:var(--card);border:1px solid var(--line);border-radius:999px;padding:.55rem .85rem;box-shadow:var(--shadow);opacity:0;visibility:hidden;transition:opacity .15s,visibility .15s}.tolang.show{opacity:1;visibility:visible}.tolang:hover{text-decoration:none;border-color:var(--accent);color:var(--accent)}
.totoc:hover{text-decoration:none;border-color:var(--accent);color:var(--accent)}
.navjs .totoc{opacity:0;visibility:hidden;transition:opacity .15s,visibility .15s}.navjs .totoc.show{opacity:1;visibility:visible}
@media print{.totoc,.tolang,.hx{display:none}}
""".replace("@STICKY@\n", _STICKY)
NAV_JS = """(function(){var d=document,r=d.documentElement,h=d.querySelector("header"),SF=@SF@,m=SF&&window.matchMedia?matchMedia("(min-width:"+SF+"px)"):null;r.classList.add("navjs");function gap(){var on=h&&m&&m.matches&&window.CSS&&CSS.supports&&CSS.supports("overflow-x","clip");r.style.setProperty("--hh",on?(h.offsetHeight+12)+"px":".9rem")}gap();addEventListener("resize",gap);addEventListener("load",gap);var c=d.querySelector("nav.toc"),p=d.querySelector(".totoc");function pill(){p.classList.toggle("show",c.getBoundingClientRect().bottom<0)}if(c&&p){addEventListener("scroll",pill,{passive:true});addEventListener("resize",pill);pill()}var hl=d.querySelector("header a.lang,header .lang a");if(h&&hl){var fl=d.createElement("a");fl.className="tolang";fl.href=hl.getAttribute("href");fl.textContent=hl.textContent;d.body.appendChild(fl);function lp(){var off=h.getBoundingClientRect().bottom<0;fl.classList.toggle("show",off);r.style.setProperty("--tocw",p&&p.classList.contains("show")?(p.offsetWidth+8)+"px":"0px")}addEventListener("scroll",lp,{passive:true});addEventListener("resize",lp);lp()}var ls=d.querySelectorAll("header a.lang,header .lang a,a.tolang");for(var i=0;i<ls.length;i++)(function(l){l.addEventListener("click",function(){if(location.hash&&(l.getAttribute("href")||"").indexOf("http")!==0)l.href=l.href.split("#")[0]+location.hash})})(ls[i])})();""".replace("@SF@", str(STICKY_FROM or 0))
