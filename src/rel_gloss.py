# -*- coding: utf-8 -*-
"""Plain-language notes for the words of the reliability cards (shared with Munjip Metrics; keep the two copies identical).

A reader who has never met a confidence interval or Cohen's kappa should be able to read a reliability card without leaving
the page. `add_gloss(body, lang)` finds which of the terms below a page uses and puts a short "words used on this page" note at
the end of the card (or, on a page without a card, at the end of the page). Only terms that appear on the page are glossed.
The wording is the same on both sites; tests compare the two copies of this file.
"""
from __future__ import annotations

import re

# (key, Korean trigger, English trigger, Korean note, English note). Order = order of the notes.
GLOSS = [
    ("coding", r"코딩|코더|코드북", r"\bcod(?:ing|ed|er|ers|ebook)\b",
     "<b>코딩 · 코더</b> — 글을 하나씩 읽고 미리 정해 둔 기준(코드북)에 따라 유형이나 해당 여부를 매기는 일. 코더는 그 판정을 맡은 이로, 이 사이트에서는 언어모델(AI)이 맡았다.",
     "<b>Coding, coder</b> — reading the texts one by one and assigning each a type, or a yes or no, by rules written down beforehand (the codebook). The coder is whoever makes those judgments; on this site, a language model (AI)."),
    ("blind", r"블라인드", r"\bblind\b",
     "<b>블라인드</b> — 판정하는 이(코더나 검증자)가 견줄 대상(앞 코더의 판정, 작성자의 판단 등)을 보지 않은 채 판정했다는 뜻. 그래야 두 판정이 맞아도 베껴서 맞은 것이 아니다. 블라인드 재코딩은 다른 코더가 그렇게 같은 글을 다시 매긴 것이다.",
     "<b>Blind</b> — whoever judges (a coder or a verifier) did so without seeing what the judgment would be compared with (the first coder's judgment, the author's reasoning and so on), so agreement cannot come from copying. A blind re-coding is a second coder judging the same texts that way."),
    ("kappa", r"κ", r"κ|\bkappa\b",
     "<b>κ(카파, 코헨 κ)</b> — 두 판정이 얼마나 맞는지를, 우연히 맞을 만큼을 빼고 잰 수. 1 이면 완전히 일치하고, 0 이면 우연히 맞는 정도에 그치며, 0 보다 작으면 우연보다도 덜 맞는다. 0 과 1 사이에서는 클수록 잘 맞는다.",
     "<b>κ (kappa, Cohen's κ)</b> — how well two sets of judgments agree once the agreement expected by chance is taken out. 1 is complete agreement, 0 is no better than chance, and below 0 is worse than chance; between 0 and 1, higher is better."),
    ("interval", r"(?<![\d.])95%|신뢰구간|윌슨", r"(?<![\d.])95%|\bCI\b|confidence interval|Wilson",
     "<b>95% 구간(신뢰구간)</b> — 표본에서 잰 비율을 두고, 전체에서의 참 비율이 있을 법한 범위. 표본을 무작위로 뽑아 같은 방법으로 구간을 거듭 만들면 100번에 95번꼴로 참값이 그 안에 든다. 다른 조건이 같다면 표본이 작을수록 범위가 넓다.",
     "<b>95% interval (confidence interval)</b> — the range in which the true rate for the whole plausibly lies, given the rate measured on a sample. With random samples, ranges built the same way again and again contain the true value about 95 times in 100. Other things equal, the smaller the sample, the wider the range."),
    ("wilson", r"윌슨", r"Wilson",
     "<b>윌슨</b> — 그 범위를 계산하는 방식의 이름. 표본이 작거나 비율이 0%·100%에 가까울 때에도 쓸 수 있다.",
     "<b>Wilson</b> — the name of the method used to compute that range; it still works when the sample is small or the rate is near 0% or 100%."),
    ("precision", r"정밀도", r"\bprecision\b",
     "<b>정밀도</b> — 규칙(키워드나 글자 규칙)이 골라낸 것 가운데 실제로 맞는 것의 비율. 높을수록 헛짚은 것이 적다. 이 사이트에서는 대개 골라낸 것의 표본을 코더가 읽어 판정해 잰다.",
     "<b>Precision</b> — of the items a rule (a keyword or a string rule) picked out, the share that are right. Higher means fewer false hits. On this site it is mostly measured by coders judging a sample of the items picked out."),
    ("recall", r"재현율", r"\brecall\b",
     "<b>재현율</b> — 찾아야 할 것 가운데 실제로 찾아낸 것의 비율. 높을수록 빠뜨린 것이 적다.",
     "<b>Recall</b> — of the items that should have been found, the share that were found. Higher means fewer misses."),
    ("parse", r"파싱|파서", r"\bpars(?:ing|ed|er)\b",
     "<b>파싱 · 파서</b> — 정해 둔 글자 규칙으로 제목 같은 문자열을 잘라 필요한 부분(받는 사람의 이름 등)을 뽑아내는 일. 파서는 그 일을 하는 프로그램이다.",
     "<b>Parsing, parser</b> — cutting a string such as a title by fixed rules to pull out the part needed (an addressee's name, for instance). The parser is the program that does it."),
    ("hhi", r"\bHHI\b", r"\bHHI\b",
     "<b>HHI(허핀달 지수)</b> — 몫(비율)마다 제곱해 더한 집중도. 한 곳에 다 몰리면 1 이고, 여러 곳에 고르게 나뉠수록 0 에 가까워진다.",
     "<b>HHI (Herfindahl index)</b> — a measure of concentration: the sum of the squared shares. It is 1 when everything is in one place and falls toward 0 as the total is spread evenly over more places."),
    ("stratified", r"층화", r"\bstratified\b",
     "<b>층화 표본</b> — 전체를 구간(기간·갈래 등)으로 나누고 구간마다 정해진 수를 무작위로 뽑은 표본. 표본이 한 구간에 몰리지 않게 하려는 것이다. 구간마다 같은 수를 뽑았는데 구간의 크기가 다르면, 표본 전체의 비율을 전체의 비율로 옮길 때 구간 크기로 가중해야 한다.",
     "<b>Stratified sample</b> — the whole is split into groups (periods, classes and so on) and a set number is drawn at random from each, so that the sample does not bunch up in one group. When the same number is drawn from groups of different size, the rate over the whole sample has to be weighted by group size before it stands for the whole."),
]
HEAD = {"ko": "이 면의 낱말", "en": "Words used on this page"}
HEAD_PAGE = {"ko": "낱말 풀이", "en": "Terms used on this page"}

_STRIP = [re.compile(p, re.S) for p in (r"<svg\b.*?</svg>", r"<nav\b.*?</nav>", r"<script\b.*?</script>", r"<style\b.*?</style>")]
_TAG = re.compile(r"<[^>]+>")
_REL_END = re.compile(r'(<div class="spec rel">.*?)(</dd></dl></div>)', re.S)


def page_text(body: str) -> str:
    for p in _STRIP:
        body = p.sub(" ", body)
    return _TAG.sub(" ", body)


def terms(text: str, lang: str) -> list[str]:
    """Keys of the glossed terms the text uses, in GLOSS order. English triggers ignore case ('Blind re-coding')."""
    i, fl = (1, 0) if lang == "ko" else (2, re.I)
    return [g[0] for g in GLOSS if re.search(g[i], text, fl)]


_SKIP = re.compile(r"<!--gloss-skip:([a-z,]+)-->")


def note(keys, lang: str) -> str:
    j = 3 if lang == "ko" else 4
    return "<br>".join(g[j] for g in GLOSS if g[0] in keys)


def add_gloss(body: str, lang: str, where: str = "card") -> str:
    """where='card': inside the first reliability card, using the terms of the whole page (cards and limits both use them).
    where='end': a short section at the end of the page (method, reading). Pages without either are returned unchanged."""
    keys = terms(page_text(body), lang)
    for m in _SKIP.finditer(body):   # a page whose own wording explains a term differently (the clan page's resampling range)
        keys = [k for k in keys if k not in m.group(1).split(",")]
    if not keys:
        return body
    if where == "card":
        m = _REL_END.search(body)
        if not m:
            return body
        p = f'<p class="gl"><span class="glh">{HEAD[lang]}</span>{note(keys, lang)}</p>'
        return body[:m.start(2)] + p + body[m.start(2):]
    if where == "end":   # inside the closing </div> of a prose page, so the section keeps the page's text width
        sec = f'<h2 id="terms">{HEAD_PAGE[lang]}</h2><p class="gl">{note(keys, lang)}</p>'
        return body[:-6] + sec + "</div>" if body.endswith("</div>") else body + sec
    return body


GLOSS_CSS = ".gl{color:var(--fg2);font-size:.9rem;line-height:1.6;margin-top:.7rem}.gl b{color:var(--fg);font-weight:600}.gl .glh{display:block;font-size:.78rem;letter-spacing:.04em;color:var(--fg2);margin-bottom:.15rem}"
