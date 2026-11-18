# Checks the numbers and dates stated in reports/2026-11-19-careers.md.
# Run from the repo root: python3 -I reports/2026-11-19-checks.py
import json, datetime as dt
from collections import Counter
from zoneinfo import ZoneInfo

s = json.load(open("work/summary.json"))
today = dt.date(2026, 11, 19)
window_end = today + dt.timedelta(days=14)

stated = {
    "new_roles": 24, "strong": 1, "possible": 13, "signal": 10,
    "deadlines_in_2_weeks": 12, "news": 1, "still_open": 59,
    "no_longer_found": 22, "companies_checked": 348,
    "apps_this_week": 0, "apps_total": 41, "weekly_target": 8,
    "opening_soon": 56, "later_cycles": 26,
}
fits = Counter(r["fit"] for r in s["new_roles"])
in_window = [r for r in s["deadlines_soon"]
             if r["closes"] and today <= dt.date.fromisoformat(r["closes"]) <= window_end]
computed = {
    "new_roles": len(s["new_roles"]), "strong": fits["strong"], "possible": fits["possible"],
    "signal": fits["signal"], "deadlines_in_2_weeks": len(in_window), "news": len(s["new_news"]),
    "still_open": len(s["still_open"]), "no_longer_found": len(s["no_longer_found"]),
    "companies_checked": len(s["companies_checked"]) if isinstance(s["companies_checked"], list) else s["companies_checked"],
    "apps_this_week": s["applications"]["this_week"], "apps_total": s["applications"]["total"],
    "weekly_target": s["applications"]["weekly_target"],
    "opening_soon": len(s["opening_soon"]), "later_cycles": len(s["later_cycles"]),
}
bad = 0
for k, v in stated.items():
    flag = "" if computed[k] == v else "   <-- DIFFERS"
    bad += bool(flag)
    print(f"{k:22} stated {v:>4}  computed {computed[k]:>4}{flag}")

print("\nWindow:", today, "to", window_end, window_end.strftime("%A"))
for d in ["2026-11-22", "2026-11-23", "2026-11-24", "2026-11-26", "2026-11-27", "2026-11-28",
          "2026-11-29", "2026-11-30", "2026-12-03", "2026-12-04", "2026-12-07", "2026-12-11"]:
    print(d, dt.date.fromisoformat(d).strftime("%a %d %b"))

# DeciBio session: Wed 2 Dec 2026 4pm PDT -> NZ time (US is on PST by December, so check both)
la = dt.datetime(2026, 12, 2, 16, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
print("\nDeciBio 4pm Los Angeles on 2 Dec ->", la.astimezone(ZoneInfo("Pacific/Auckland")).strftime("%a %d %b %H:%M %Z"),
      "| LA zone in effect:", la.tzname())
print("\nmismatches:", bad)

# Extra figures stated in Coverage and "Still open"
seek_au = sum(1 for l in open("work/seek-AU.txt") if l.strip() and not l.startswith("#") and not l.startswith("listed"))
seek_nz = sum(1 for l in open("work/seek-NZ.txt") if l.strip() and not l.startswith("#") and not l.startswith("listed"))
uk = sum(1 for l in open("work/uk-jobs.txt") if l.strip() and not l.startswith("#"))
searches = {1: 7, 2: 7, 3: 6, 4: 7, 5: 6, 6: 6, 7: 5, 8: 7, 9: 6, 10: 6, 11: 4, 12: 6, 13: 6, 14: 6,
            15: 6, 16: 4, 17: 6, 18: 5, 19: 7, 20: 7}  # as each batch reported
so = Counter(r["fit"] for r in s["still_open"])
extra = {"seek_au": (287, seek_au), "seek_nz": (40, seek_nz), "uk_listings": (202, uk),
         "searches_total_about": (120, sum(searches.values())),
         "still_open_possible": (28, so["possible"]), "still_open_signal": (30, so["signal"]),
         "still_open_strong": (1, so["strong"]),
         "board_roles": (1239, len(json.load(open("work/board/roles.json"))["roles"]))}
for k, (st, c) in extra.items():
    print(f"{k:22} stated {st:>5}  computed {c:>5}" + ("" if st == c else "   <-- DIFFERS"))
