# -*- coding: utf-8 -*-
"""1.2 — astronomical reference tables for series G: 918–1910, two observing sites (JPL DE406 via skyfield).

  python src/astro_ext.py            # writes data/derived/solar_eclipses_sites.csv, lunar_eclipses_sites.csv,
                                     #        nasa_lunar_eclipses_918_1910.csv, venus_inferior_conjunctions_918_1910.csv

Same method as astro.py (1.0), extended in time and in place:
  * Gaeseong 37.9667° N 126.55° E (Goryeo capital; the 1232–1270 Ganghwa years are 30 km away, which moves eclipse
    visibility by far less than the ΔT uncertainty of the period) for the Goryeo sources, Seoul 37.5665° N 126.978° E
    for the Joseon sources. Every row carries both sites so a comparison can use either.
  * Solar eclipses: for every new moon 918-01-01 .. 1911-01-01 the topocentric Sun–Moon separation is sampled every
    2 minutes within ±6 h of conjunction; visible when the discs overlap while the Sun is above −0.3° altitude.
  * Lunar eclipses: skyfield.eclipselib (umbral only), visible when the Moon is above −0.5° at maximum.
  * Local dates are UT1 + longitude/360 (Earth-rotation time), written as proleptic-Gregorian ISO and also as the
    Julian-calendar date before 1582-10-15 — the NIKH Goryeo solar dates are Julian.
  * ΔT: skyfield's long-term model (Stephenson, Morrison & Hohenkerk 2016). Before 1392 its 1-σ is of order minutes to
    a quarter of an hour, which matters for the partial-phase boundary cases; the method page says so.
  * The NASA Five Millennium Catalog of Lunar Eclipses (Espenak & Meeus, TP-2009-214173) is parsed for 918–1910 as an
    independent list of umbral eclipses to cross-check the count; its file stays in data/raw/external/ and only the
    comparison is published.
"""
import datetime as dt
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from skyfield import almanac, api, eclipselib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_articles import julian_from_jdn   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EPH = ROOT / "data" / "raw" / "eph"
D = ROOT / "data" / "derived"
NASA = ROOT / "data" / "raw" / "external" / "nasa-5mkle" / "5MKLEcatalog.txt"
SITES = {"gaeseong": (37.9667, 126.55), "seoul": (37.5665, 126.9780)}
R_SUN_KM, R_MOON_KM = 696000.0, 1737.4
Y0, Y1 = 918, 1911
GREG_SWITCH_JDN = 2299161   # 1582-10-15


def local_date(t, lon):
    """Local mean date at longitude lon for a skyfield Time: (iso proleptic Gregorian, jdn, julian-calendar iso)."""
    jdn = int(t.ut1 + 0.5 + lon / 360)
    g = dt.date.fromordinal(jdn - 1721425).isoformat()
    y, m, d = julian_from_jdn(jdn)
    j = f"{y:04d}-{m:02d}-{d:02d}"
    return g, jdn, (j if jdn < GREG_SWITCH_JDN else g)


def main():
    load = api.Loader(str(EPH), verbose=False)
    ts = load.timescale()
    eph = load("de406.bsp")
    earth, sun, moon = eph["earth"], eph["sun"], eph["moon"]
    obs = {k: earth + api.wgs84.latlon(*v) for k, v in SITES.items()}
    t0, t1 = ts.utc(Y0, 1, 1), ts.utc(Y1, 1, 1)
    t, y = almanac.find_discrete(t0, t1, almanac.moon_phases(eph))
    newmoons = [ti for ti, yi in zip(t, y) if yi == 0]
    print("new moons", len(newmoons), flush=True)
    offsets = np.arange(-6 * 60, 6 * 60 + 1, 2) / (24 * 60)
    rows = []
    for n, nm in enumerate(newmoons):
        tt = ts.tt_jd(nm.tt + offsets)
        g = earth.at(tt).observe(sun).apparent().separation_from(earth.at(tt).observe(moon).apparent()).degrees
        row = dict(newmoon_ut=nm.utc_iso(), newmoon_jd=nm.tt, geocentric_min_sep_deg=float(g.min()), earthwide=bool(g.min() < 1.58))
        for site, o in obs.items():
            s = o.at(tt).observe(sun).apparent()
            m = o.at(tt).observe(moon).apparent()
            sep = s.separation_from(m).degrees
            alt = s.altaz()[0].degrees
            r_s = np.degrees(np.arcsin(R_SUN_KM / s.distance().km))
            r_m = np.degrees(np.arcsin(R_MOON_KM / m.distance().km))
            overlap = (r_s + r_m) - sep
            mag = overlap / (2 * r_s)
            vis = (overlap > 0) & (alt > -0.3)
            row[f"{site}_visible"] = bool(vis.any())
            if vis.any():
                i = int(np.argmax(np.where(vis, mag, -1)))
                first, last = np.where(vis)[0][[0, -1]]
                gd, jdn, jd = local_date(tt[i], SITES[site][1])
                row.update({f"{site}_max_magnitude": float(min(mag[i], 1.0) if r_m[i] >= r_s[i] else mag[i]),
                            f"{site}_max_ut": tt[i].utc_iso(), f"{site}_start_ut": tt[first].utc_iso(), f"{site}_end_ut": tt[last].utc_iso(),
                            f"{site}_sun_alt_at_max": float(alt[i]), f"{site}_max_date_lmt": gd, f"{site}_max_jdn_lmt": jdn, f"{site}_max_date_civil": jd})
            elif (overlap > 0).any():
                i = int(np.argmax(overlap))
                row.update({f"{site}_max_magnitude": float(mag[i]), f"{site}_sun_alt_at_max": float(alt[i]), f"{site}_below_horizon": True})
        rows.append(row)
        if n % 500 == 0:
            print("  new moon", n, nm.utc_iso()[:10], flush=True)
    se = pd.DataFrame(rows)
    se.to_csv(D / "solar_eclipses_sites.csv", index=False)
    print("solar: new moons", len(se), "earthwide", int(se.earthwide.sum()),
          "gaeseong visible", int(se.gaeseong_visible.sum()), "seoul visible", int(se.seoul_visible.sum()), flush=True)

    # lunar eclipses
    t, yy, details = eclipselib.lunar_eclipses(t0, t1, eph)
    lrows = []
    for ti, yi in zip(t, yy):
        if yi == 0:
            continue
        row = dict(max_ut=ti.utc_iso(), max_jd=ti.tt, kind=eclipselib.LUNAR_ECLIPSES[yi])
        for site, o in obs.items():
            alt = o.at(ti).observe(moon).apparent().altaz()[0].degrees
            gd, jdn, jd = local_date(ti, SITES[site][1])
            row.update({f"{site}_moon_alt_at_max": float(alt), f"{site}_visible": bool(alt > -0.5),
                        f"{site}_max_date_lmt": gd, f"{site}_max_jdn_lmt": jdn, f"{site}_max_date_civil": jd})
        lrows.append(row)
    le = pd.DataFrame(lrows)
    le.to_csv(D / "lunar_eclipses_sites.csv", index=False)
    print("lunar (umbral)", len(le), "gaeseong visible", int(le.gaeseong_visible.sum()), "seoul visible", int(le.seoul_visible.sum()), flush=True)

    # NASA catalogue cross-check (umbral = type P or T), 918–1910, TD of greatest eclipse
    nasa = []
    mon = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
    for line in NASA.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\s*(\d{5})\s+(-?\d{4}) (\w{3}) (\d{2})\s+(\d{2}):(\d{2}):(\d{2})\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+([NPT][+\-x]?)\s", line)
        if not m:
            continue
        yr = int(m.group(2))
        if yr < Y0 or yr >= Y1 or m.group(11).startswith("N"):
            continue
        # the catalogue dates are Julian before 1582-10-15 (Espenak & Meeus convention)
        nasa.append(dict(cat_num=int(m.group(1)), date_civil=f"{yr:04d}-{mon[m.group(3)]:02d}-{int(m.group(4)):02d}",
                         td_greatest=f"{m.group(5)}:{m.group(6)}:{m.group(7)}", delta_t_s=int(m.group(8)), saros=int(m.group(10)), kind=m.group(11)))
    na = pd.DataFrame(nasa)
    na.to_csv(D / "nasa_lunar_eclipses_918_1910.csv", index=False)
    # match on the day number ±1 (catalogue dates are TD at greatest eclipse; ours are Seoul local civil dates)
    def jdn_civil(dstr):
        y, mo, d = map(int, dstr.split("-"))
        a = (14 - mo) // 12; yy = y + 4800 - a; mm = mo + 12 * a - 3
        jj = d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - 32083            # Julian calendar
        if jj >= GREG_SWITCH_JDN:                                              # Gregorian after the switch
            jj = dt.date(y, mo, d).toordinal() + 1721425
        return jj
    na["jdn"] = na.date_civil.map(jdn_civil)
    ours = set(le.seoul_max_jdn_lmt.astype(int))
    na["matched_pm1"] = na.jdn.map(lambda j: any((j + k) in ours for k in (-1, 0, 1)))
    na.to_csv(D / "nasa_lunar_eclipses_918_1910.csv", index=False)
    print("nasa umbral 918-1910:", len(na), "| skyfield umbral:", len(le), "| matched within ±1 day:", int(na.matched_pm1.sum()), flush=True)

    # Venus inferior conjunctions (phase reference for G3)
    venus = eph["venus"]
    tq = ts.tt_jd(np.arange(t0.tt, t1.tt, 1.0))
    e = earth.at(tq)
    el = e.observe(sun).apparent().separation_from(e.observe(venus).apparent()).degrees
    dv, dsun = e.observe(venus).distance().au, e.observe(sun).distance().au
    idx = [i for i in range(1, len(el) - 1) if el[i] < el[i - 1] and el[i] <= el[i + 1] and dv[i] < dsun[i]]
    vc = pd.DataFrame(dict(inferior_conjunction_ut=[tq[i].utc_iso() for i in idx], jd=[float(tq[i].tt) for i in idx], elongation_deg=[float(el[i]) for i in idx]))
    vc.to_csv(D / "venus_inferior_conjunctions_918_1910.csv", index=False)
    print("venus inferior conjunctions", len(vc))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
