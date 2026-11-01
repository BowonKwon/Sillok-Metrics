# Sillok Metrics · 실록 메트릭스

**조선왕조실록을 기사 단위로 센 수치와, 그 수치를 얼마나 믿어도 되는지.**
**The Veritable Records of the Joseon Dynasty counted article by article, with a reliability card on every number.**

Site: https://bowonkwon.github.io/Sillok-Metrics/ (한국어 · English) · Hub: https://bowonkwon.github.io/

## 무엇인가 / What it is

**범위 / Scope.** 태조~순종 27대(1392~1910). 고종·순종실록의 원문 데이터는 공공누리 제4유형(변경 금지·비상업)이라 본문을 가공·인용하지 않는 집계(기사 수·글자 수·국편 분류·키워드 건수)에만 쓰고, 기사 제목·본문 발췌·표본 코딩·천문 대조에는 쓰지 않았다. The Gojong and Sunjong records are KOGL Type 4 (no derivatives, non-commercial); they enter only counts that neither alter nor quote the text and are excluded from titles, excerpts, sample coding and the astronomical checks.

국사편찬위원회가 공공데이터포털에 개방한 실록 원문 XML(공공누리 제1유형)을 기사(414,501건, 판본 33종) 단위로 세어 지표 24개를 만들었다. 다섯 계열이다: 기록의 양과 밀도, 판본 비교, 하늘과 기후, 정치·인사, 형정·사회. 숫자마다 신뢰도 카드가 붙는다 — 원본에서 그대로 센 값인지, 천문 계산(JPL DE406)과 맞춰 본 비율인지, 손으로 코딩한 층화 표본에서 잰 정밀도인지. 원문 전문은 싣지 않으며 기사마다 국사편찬위원회 원문으로 연결한다.

24 metrics in five series (volume, editions, sky and weather, politics, justice and society) computed over the 414,501 articles (33 editions) of the NIKH XML releases. Every metric carries a reliability card: exact count, external match against astronomical computation (JPL DE406), or sampled precision from hand-coded stratified samples. No article text is republished; every article links to the NIKH site.

## 저장소 구성 / Layout

| path | content |
|---|---|
| `docs/` | the built site (GitHub Pages source): `ko/`, `en/`, `data/` |
| `data/` | derived CSVs (one per table), `datapackage.json`, `coding/` (codebooks and every hand-coded judgement) |
| `src/` | `registry.py` (every metric's definition, in one place) and `takeaways.py` (page takeaways), `build_articles.py`, `check_articles.py`, `extract_keywords.py`, `export_coding_input.py`, `astro.py`, `espenak.py`, `check_calendar.py`, `metrics_a.py`–`metrics_e.py`, `merge_coding.py`, `reliability.py`, `build_site.py` |

## 공개 자료로 재현되는 범위 / What the public files reproduce

- `data/*.csv` 의 지표 표는 `data/articles.csv.gz`(기사 테이블)·천문 표(`solar_eclipses_seoul.csv` 등)·코딩 표에서 다시 계산할 수 있다. 사이트(`docs/`)는 `python src/build_site.py --derived data --out site` 로 `data/` 에서 다시 만들 수 있다(기사 중앙값은 `articles.csv.gz` 에서 읽는다).
- 기사 테이블과 천문 표 자체를 처음부터 다시 만들려면 원자료(공공데이터포털 XML, JPL DE406, Espenak 목록)를 아래 경로에 내려받아야 한다. 원자료와 작업 중간물(parquet)은 이 저장소에 없다.
- The metric tables in `data/*.csv` can be recomputed from `data/articles.csv.gz`, the astronomy tables and the coding tables; the site can be rebuilt from `data/` with `python src/build_site.py --derived data --out site`. Rebuilding the article table and the astronomy tables from scratch needs the raw sources (data.go.kr XML, JPL DE406, the Espenak catalog), which are not in this repository.

## 다시 만들기 / Rebuild

```
pip install pandas pyarrow numpy scipy skyfield jplephem korean_lunar_calendar
# put the NIKH XML zips (data.go.kr 15053647 and 15053646), the NIKH person zip (15053645), the AKS roster XML (15052752),
# JPL de406.bsp and the Espenak 5MCSEcatalog.txt under data/raw/ as named in the scripts
python src/build_articles.py && python src/check_articles.py
python src/check_calendar.py && python src/astro.py && python src/espenak.py
python src/extract_keywords.py
python src/metrics_a.py && python src/metrics_b.py && python src/metrics_c.py && python src/metrics_d.py && python src/metrics_e.py
python src/reliability.py && python src/build_site.py --out docs
```

## 출처 표시 / Attribution

본 저작물은 '교육부 국사편찬위원회'에서 2022년 작성하여 공공누리 제1유형으로 개방한 '조선왕조실록 정보_실록원문'·'조선왕조실록 정보_부가정보 인물 데이터'를 이용하였으며, 해당 저작물은 '공공데이터포털(https://www.data.go.kr/data/15053647/fileData.do · https://www.data.go.kr/data/15053645/fileData.do)'에서 무료로 다운받으실 수 있습니다. 성관 보충에는 '한국학중앙연구원'이 공공데이터포털(https://www.data.go.kr/data/15052752/fileData.do)에 개방한 '조선조문과급제자'를 이용하였습니다. 천문 계산은 NASA/JPL DE406, 일식 목록은 Espenak & Meeus, *Five Millennium Canon of Solar Eclipses* (NASA/TP-2006-214141)를 썼습니다.

## 라이선스 / License

Code: MIT. Site text and this project's own contributions: CC BY 4.0. Derived tables are derivative works of KOGL Type 1 sources and keep the attribution above. See `LICENSE.md`.

## 인용 / Citation

Kwon, Bowon (2026). *Sillok Metrics* 1.1. https://bowonkwon.github.io/Sillok-Metrics/
