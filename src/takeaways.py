# -*- coding: utf-8 -*-
"""Takeaways — one short paragraph per page saying what the number lets a reader say, and what it does not.
Imported by registry.py and merged into METRICS; kept in its own file so the prose can be edited without
touching definitions. Format shared with the sibling site (Classical Music Metrics): a lead sentence that
states the finding, a second that bounds it.
"""

TAKEAWAYS = {
    "n_articles": dict(
        ko="국편이 공식 기사 수를 내놓지 않은 자리를 이 표가 메운다. 「세종실록 32,281건」처럼 기사 수를 인용하려면 이 표의 값을 쓰되, 날짜 있는 기사(30,948)와 총서·지(志)를 구분해 적어야 한다. 고종·순종실록은 공공누리 4유형이라 건수만 셌고 제목·본문은 싣지 않았다.",
        en="NIKH publishes no official article count; this table fills that gap. Quote counts from here, but say whether front matter and treatises are included (Sejong: 32,281 in all, 30,948 dated). The Gojong and Sunjong records are KOGL Type 4, so only counts were taken; no titles or text are published."),
    "n_han": dict(
        ko="실록의 「양」을 말할 때 쓸 수 있는 유일한 전수 집계다. 5,248만 자는 태조~순종의 판본 33종을 모두 합친 값이고, 태조~철종 본실록만은 4,458만 자다.",
        en="The only complete count on which any statement about the Sillok's size can rest: 52.5 million characters across all 33 editions, 44.6 million in the principal editions of Taejo–Cheoljong alone."),
    "han_per_year": dict(
        ko="「후기로 갈수록 기록이 빈약해졌다」는 통설을 숫자로 바꾼 것이다. 정조 이후의 급감은 10배 규모라 기록 관행의 변화로 읽는 것이 맞고, 사건이 줄어든 것으로 읽어서는 안 된다.",
        en="Turns the commonplace that the record thins toward the end into a number. The tenfold drop after Jeongjo should be read as a change in recording practice, not as a quieter century."),
    "median_len": dict(
        ko="기사 단위 지표를 왕대끼리 비교할 때 먼저 봐야 할 보정 변수다. 기사 수가 같아도 중앙값이 두 배면 기록량은 두 배다.",
        en="The first thing to check before comparing article-based metrics across reigns: equal article counts with twice the median length mean twice as much text."),
    "saron_share": dict(
        ko="사관의 논평이 어느 시기의 실록에 들어 있는지를 보여 준다. 정조실록 이후 0이라는 사실은 「사론을 통한 평가」를 인용할 수 있는 시기가 선조~영조로 한정된다는 뜻이다.",
        en="Shows which editions carry the historians' own judgments at all. Zero from Jeongjo onward means commentary can be cited only for Seonjo to Yeongjo."),
    "empty_month_share": dict(
        ko="기사가 없는 달은 「그때 아무 일도 없었다」가 아니라 「기록이 없다」로 읽어야 한다. 시계열 지표에서 그 달의 0은 결측으로 다루는 것이 안전하다.",
        en="An empty month means no record, not no events. In any time series, treat those zeros as missing rather than as quiet months."),
    "edition_pair_ratio": dict(
        ko="수정본을 인용할 때 그것이 원본의 어느 정도를 다시 쓴 것인지 한 줄로 말할 수 있다. 선조수정실록은 원본의 10분의 1 분량이고, 현종개수실록은 원본보다 길다.",
        en="Lets you say in one line how much of the original a revision rewrites: the Revised Seonjo records are a tenth of the original; the Supplemented Hyeonjong records are longer than the original."),
    "shared_day_share": dict(
        ko="수정본이 원본의 어느 날을 골라 다시 썼는지의 비율이다. 선조수정실록 날짜의 60%만 원본에도 있다는 것은 40%가 원본에 없는 날의 기사라는 뜻으로, 「수정」이 삭제·논평만이 아니라 보충이기도 했음을 보여 준다.",
        en="How much of the revision sits on days the original already covers. Only 60% of the Revised Seonjo days have an original article, so revision meant supplementing as well as cutting and commenting."),
    "gwanghae_deletion": dict(
        ko="국편 해제의 「1/3 축소」를 세 단위로 쪼갠 값이다. 기사 15%, 글자 18%, 산삭 표시 16%는 서로 다른 것을 재므로, 인용할 때 어느 단위인지 적어야 한다.",
        en="Splits NIKH's 'reduced by a third' into three distinct measures (15% of articles, 18% of characters, 16% of characters marked); say which one you are citing."),
    "revised_saron_share": dict(
        ko="국편 태그 기준으로는 수정본에 사론이 거의 없다(선조수정실록 1건). 오항녕이 센 52칙과 다르므로, 수정본의 논평을 셀 때는 태그가 아니라 본문의 「史臣曰」을 직접 세야 한다.",
        en="According to NIKH's tags the revisions carry almost no commentary (a single comment in the Revised Seonjo records), compared with the 52 counted by Oh Hang-nyeong. Count '史臣曰' in the text, not the tags, when working on revised editions."),
    "solar_eclipse_match": dict(
        ko="「실록의 일식 기록은 믿을 만한가」에 유형별로 답한다. 관측 보고로 읽히는 기사의 65%는 서울에서 실제로 보인 일식과 맞고, 95%는 지구 어딘가의 일식과 맞는다. 나머지는 대부분 해 진 뒤의 일식을 계산대로 적은 것이다. 「日食」 기사 전체를 관측 기록으로 세면 일치율은 24%로 떨어진다 — 유형을 가리지 않은 집계는 쓰지 말 것.",
        en="Answers the question 'Can the Sillok's eclipse records be trusted?' type by type: 65% of observation reports match an eclipse visible from Seoul and 95% an eclipse somewhere on Earth; most of the rest are eclipses after sunset that were recorded from calculation. Counting every '日食' article as an observation drops the rate to 24%, so never use the total that ignores type."),
    "lunar_eclipse_match": dict(
        ko="월식 기사 전체의 47%만 ±1일 안에 서울 가시 월식과 맞는다. 유형을 가리지 않은 값이라 하한이며, 유형별 값은 1.2 의 G2 에 있다. 「월식 기사 수」를 관측 횟수로 쓰지 말 것.",
        en="Only 47% of all lunar-eclipse articles match a visible eclipse within ±1 day. Articles were not classified by type here, so this is a lower bound; the values by type are in G2 (1.2). Do not use the article count as an observation count."),
    "venus_phase": dict(
        ko="400년 치 기록이 한 행성의 주기를 0.04% 오차로 재현한다. 「실록의 천문 기록은 실제 관측의 누적」이라는 명제의 가장 강한 계량 근거이며, 증거법으로 옮기면 관찰 기록과 평가 기록의 신빙성을 따로 따져야 한다는 사례다.",
        en="Four centuries of articles reproduce a planet's period to within 0.04%. The strongest quantitative support for treating the Sillok's astronomical articles as accumulated observation — and, by analogy with the law of evidence, a case for weighing observational and evaluative records differently."),
    "comet_years": dict(
        ko="혜성 기사 수는 정밀도 68%를 곱해 읽어야 한다. 셋 중 하나는 혜성을 근거로 든 상소·논의다. 핼리 회귀 연도의 봉우리는 그대로 보인다.",
        en="Multiply comet article counts by the 68% precision; one in three is a memorial or debate citing a comet. The Halley-year peaks survive the correction."),
    "earthquake_articles": dict(
        ko="지진 기사의 76%가 실제 발생 보고라 역사지진 목록의 자료원으로 쓸 만하다. 도 이름이 없는 기사를 서울로 두는 규칙은 지방 지진을 서울로 옮길 수 있으니 지역 비교에는 주의.",
        en="Of earthquake articles, 76% are actual reports, so they are usable as a source for historical seismicity catalogs. Articles without a province are assigned to Seoul, so regional comparisons need care."),
    "summer_cold": dict(
        ko="소빙기 가설을 실록으로 검증할 때의 결론은 「1500~1750년 전체가 아니라 1640~1719년」이다. 다만 키워드 정밀도가 54%라 절대 수치보다 연대 간 비교로만 쓴다.",
        en="Tested against the Sillok, the Little Ice Age hypothesis is supported for 1640–1719 rather than across 1500–1750. Because keyword precision is only 54%, use the series for comparisons between decades, not as absolute counts."),
    "clan_concentration": dict(
        ko="벌열화 통설을 수치로 확인한 것이다. 상위 10개 성관의 고위직 점유율이 17세기부터 19세기 전반까지 계속 올랐고, 본관 결측을 비관적으로 채운 하한에서도 추세가 남는다. 성관은 가문보다 넓은 단위라는 점만 잊지 않으면 논문에 인용할 수 있다.",
        en="Puts a number on the thesis of oligarchic concentration: the top-10 clan share of high office rose from the 17th century to the early 19th, and the rise holds even under a pessimistic lower bound. Citable, provided a clan is understood to be wider than a lineage."),
    "royal_lecture_share": dict(
        ko="경연 기사 비율은 「경연이 열렸다」는 기사의 비율로 읽어도 좋다(정밀도 82%). 왕대 간 차이가 크므로 왕의 통치 양식을 비교하는 변수로 쓸 수 있다.",
        en="Safe to read as the share of articles in which a lecture was actually held (82% precision). The spread between reigns makes it a usable variable for comparing styles of rule."),
    "memorial_share": dict(
        ko="키워드와 국편 분류가 잡는 범위가 다르다는 것을 보여 주는 지표다. 상소 기사의 비율 자체보다, 두 값의 차이가 어느 왕대에 큰지를 보라.",
        en="Shows how keyword hits and NIKH classification capture different things. Look less at the share itself than at where the two diverge."),
    "justice_share": dict(
        ko="실록의 사법 기사 비중은 일상 재판량이 아니라 옥사의 강도를 따른다. 조선 사법의 「양」을 실록으로 재려는 시도는 이 봉우리들을 먼저 설명해야 한다.",
        en="The share of justice articles tracks the intensity of political trials, not routine litigation. Any attempt to measure Joseon's judicial caseload from the Sillok must first explain these peaks."),
    "death_penalty_mention": dict(
        ko="「사형 기사 수」를 사형 집행 수로 인용하면 안 된다는 것을 표본으로 보인 지표다. 세종실록의 정점은 판결 재가 기록이다. 집행 통계는 『심리록』·『일성록』·『추관지』에서 구해야 하고, 실록은 그 가운데 4%만 담고 있다(유승희 2007).",
        en="A sample-based warning against quoting death-penalty articles as executions: the Sejong peak is sentencing paperwork. Execution statistics should be drawn from the Simnirok, Ilseongnok and Chugwanji; the Sillok holds about 4% of those cases (Yu 2007)."),
    "relief_share": dict(
        ko="진휼·흉년 기사는 정밀도 81%로 실제 기근·구휼 조치를 잘 가리킨다. 경신·을병 대기근 연도에 봉우리가 서므로 기근 연표의 1차 후보 목록으로 쓸 수 있다.",
        en="With 81% precision, relief and famine articles point to real crises and relief measures; the peaks in the 1670–71 and 1695–96 famines make the series a first draft of a famine chronology."),
    "eonmun_articles": dict(
        ko="한글이 국정 기록에 언급되는 빈도와 그 자리(공초·옥사와 겹치는 기사 수)를 보여 준다. 「언급」이지 한글 문서 수가 아니므로 문자 사용량으로 옮기지 말 것.",
        en="How often, and where, the vernacular script enters the state record (including overlap with trial records). Mentions, not documents written in the script — do not read it as a measure of how much the script was used."),
    "slave_share": dict(
        ko="노비 기사 비율의 정밀도는 1.2에서 코드북을 좁혀 다시 잰 값이 68%다(블라인드 재코딩 κ 0.86). 키워드 기사의 약 3분의 1은 노비가 주제가 아니므로 건수는 정밀도를 곱해 읽는다.",
        en="Re-coded in 1.2 with a narrower codebook, the slaves keyword has 68% precision (blind re-coding κ 0.86). About a third of keyword articles are not about slaves, so multiply counts by the precision."),
}
