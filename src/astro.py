# -*- coding: utf-8 -*-
"""Astronomical reference tables for series C (JPL DE406 via skyfield).

  python src/astro.py       # writes data/derived/solar_eclipses_seoul.csv, lunar_eclipses_seoul.csv,
                            #        venus_inferior_conjunctions.csv

Solar eclipses. For every new moon 1391–1865 the topocentric separation of Sun and Moon as
seen from Seoul (37.57° N, 126.98° E) is sampled every 2 minutes within ±6 h of conjunction.
An eclipse is "visible from Seoul" when the separation drops below the sum of the apparent
radii while the Sun's centre is above the horizon (altitude > −0.3°, i.e. allowing refraction).
Magnitude is the fraction of the solar diameter covered at maximum. "Earth-wide" eclipses
(any part of the Earth) are flagged when the geocentric separation at minimum is below 1.58°;
that flag is only used to cross-check the count against the Espenak–Meeus canon.

Lunar eclipses come from skyfield.eclipselib.lunar_eclipses (penumbral ones excluded) and are
"visible from Seoul" when the Moon is above the horizon at the moment of maximum.

Times are UT; Seoul local mean dates use UT1 + 126.978°/360 day (Earth-rotation time, not UTC). ΔT is skyfield's built-in long-term model
(Stephenson, Morrison & Hohenkerk 2016 before telescopic times).
"""
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from skyfield import almanac, api, eclipselib

ROOT = Path(__file__).resolve().parent.parent
EPH = ROOT / "data" / "raw" / "eph"
D = ROOT / "data" / "derived"
SEOUL = api.wgs84.latlon(37.5665, 126.9780)
R_SUN_KM, R_MOON_KM = 696000.0, 1737.4


def main():
    load = api.Loader(str(EPH), verbose=False)
    ts = load.timescale()
    eph = load("de406.bsp")
    earth, sun, moon = eph["earth"], eph["sun"], eph["moon"]
    obs = earth + SEOUL
    t0, t1 = ts.utc(1391, 1, 1), ts.utc(1865, 1, 1)
    t, y = almanac.find_discrete(t0, t1, almanac.moon_phases(eph))
    newmoons = [ti for ti, yi in zip(t, y) if yi == 0]
    rows = []
    offsets = np.arange(-6 * 60, 6 * 60 + 1, 2) / (24 * 60)   # days
    for nm in newmoons:
        tt = ts.tt_jd(nm.tt + offsets)
        s = obs.at(tt).observe(sun).apparent()
        m = obs.at(tt).observe(moon).apparent()
        sep = s.separation_from(m).degrees
        alt = s.altaz()[0].degrees
        ds = s.distance().km
        dm = m.distance().km
        r_s = np.degrees(np.arcsin(R_SUN_KM / ds))
        r_m = np.degrees(np.arcsin(R_MOON_KM / dm))
        overlap = (r_s + r_m) - sep
        mag = overlap / (2 * r_s)
        up = alt > -0.3
        vis = (overlap > 0) & up
        # geocentric check for earth-wide eclipse
        g = earth.at(tt).observe(sun).apparent().separation_from(earth.at(tt).observe(moon).apparent()).degrees
        row = dict(newmoon_ut=nm.utc_iso(), newmoon_jd=nm.tt, geocentric_min_sep_deg=float(g.min()),
                   earthwide=bool(g.min() < 1.58), seoul_visible=bool(vis.any()))
        if vis.any():
            i = np.argmax(np.where(vis, mag, -1))
            first, last = np.where(vis)[0][[0, -1]]
            row.update(seoul_max_magnitude=float(min(mag[i], 1.0) if r_m[i] >= r_s[i] else mag[i]),
                       seoul_max_ut=tt[i].utc_iso(), seoul_start_ut=tt[first].utc_iso(), seoul_end_ut=tt[last].utc_iso(),
                       sun_alt_at_max=float(alt[i]),
                       seoul_max_lmt=dt.date.fromordinal(int(tt[i].ut1 + 0.5 + 126.978 / 360) - 1721425).isoformat())
        elif (overlap > 0).any():
            i = np.argmax(overlap)
            row.update(seoul_max_magnitude=float(mag[i]), sun_alt_at_max=float(alt[i]), below_horizon=True)
        rows.append(row)
    se = pd.DataFrame(rows)
    se["seoul_max_date_lmt"] = se.seoul_max_lmt.str[:10]
    se.to_csv(D / "solar_eclipses_seoul.csv", index=False)
    print("new moons", len(se), "earthwide", int(se.earthwide.sum()), "seoul visible", int(se.seoul_visible.sum()))

    # lunar eclipses
    t, yy, details = eclipselib.lunar_eclipses(t0, t1, eph)
    lrows = []
    for ti, yi in zip(t, yy):
        if yi == 0:   # penumbral
            continue
        m = obs.at(ti).observe(moon).apparent()
        alt = m.altaz()[0].degrees
        lrows.append(dict(max_ut=ti.utc_iso(), max_jd=ti.tt, kind=eclipselib.LUNAR_ECLIPSES[yi],
                          moon_alt_at_max=float(alt), seoul_visible=bool(alt > -0.5),
                          max_lmt=dt.date.fromordinal(int(ti.ut1 + 0.5 + 126.978 / 360) - 1721425).isoformat()))
    le = pd.DataFrame(lrows)
    le["max_date_lmt"] = le.max_lmt.str[:10]
    le.to_csv(D / "lunar_eclipses_seoul.csv", index=False)
    print("lunar eclipses (umbral)", len(le), "seoul visible", int(le.seoul_visible.sum()))

    # Venus inferior conjunctions (phase reference for C3)
    venus = eph["venus"]
    def elong(tq):
        e = earth.at(tq)
        return e.observe(sun).apparent().separation_from(e.observe(venus).apparent()).degrees
    # inferior conjunction = minimum elongation with Venus closer than Sun
    tq = ts.tt_jd(np.arange(t0.tt, t1.tt, 1.0))
    el = elong(tq)
    dist_v = earth.at(tq).observe(venus).distance().au
    dist_s = earth.at(tq).observe(sun).distance().au
    idx = [i for i in range(1, len(el) - 1) if el[i] < el[i - 1] and el[i] <= el[i + 1] and dist_v[i] < dist_s[i]]
    vc = pd.DataFrame(dict(inferior_conjunction_ut=[tq[i].utc_iso() for i in idx], jd=[tq[i].tt for i in idx], elongation_deg=[float(el[i]) for i in idx]))
    vc.to_csv(D / "venus_inferior_conjunctions.csv", index=False)
    print("venus inferior conjunctions", len(vc))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
