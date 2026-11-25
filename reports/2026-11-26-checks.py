# Checks the numbers and dates stated in reports/2026-11-26-careers.md.
# Run from the repo root: python3 -I reports/2026-11-26-checks.py
import json, datetime as dt
from collections import Counter

s = json.load(open("work/summary.json"))
board = json.load(open("work/board/roles.json"))
today = dt.date(2026, 11, 26)
window_end = today + dt.timedelta(days=14)

def lines(path):
    return sum(1 for l in open(path) if not l.startswith("#") and l.strip())

fits = Counter(r["fit"] for r in s["new_roles"])
open_fits = Counter(r["fit"] for r in s["still_open"])
in_window = [r for r in s["deadlines_soon"]
             if r["closes"] and today <= dt.date.fromisoformat(r["closes"]) <= window_end]
# WebSearch calls each batch reported using (batches 1-20)
searches = [7, 6, 6, 6, 6, 6, 6, 7, 6, 7, 5, 5, 5, 6, 6, 6, 4, 5, 6, 7]

stated = {
    "new_roles": 27, "strong": 0, "possible": 14, "signal": 13,
    "deadlines_in_2_weeks": 13, "news": 1,
    "still_open_strong": 1, "still_open_possible": 38, "still_open_signal": 32,
    "no_longer_found": 9, "companies_checked": 347, "batches": 20,
    "apps_this_week": 0, "apps_4_weeks": 6, "apps_total": 41, "weekly_target": 8,
    "apply_queue": 25, "board_roles": 1278, "seek_au": 255, "seek_nz": 50,
    "websearch_total": 118, "websearch_min": 4, "websearch_max": 7,
}
computed = {
    "new_roles": len(s["new_roles"]), "strong": fits["strong"], "possible": fits["possible"],
    "signal": fits["signal"], "deadlines_in_2_weeks": len(in_window), "news": len(s["new_news"]),
    "still_open_strong": open_fits["strong"], "still_open_possible": open_fits["possible"],
    "still_open_signal": open_fits["signal"],
    "no_longer_found": len(s["no_longer_found"]),
    "companies_checked": len(s["companies_checked"]) if isinstance(s["companies_checked"], list) else s["companies_checked"],
    "batches": len(searches),
    "apps_this_week": s["applications"]["this_week"], "apps_4_weeks": s["applications"]["last_4_weeks"],
    "apps_total": s["applications"]["total"], "weekly_target": s["applications"]["weekly_target"],
    "apply_queue": len(s["apply_queue"]), "board_roles": len(board["roles"]),
    "seek_au": lines("work/seek-AU.txt"), "seek_nz": lines("work/seek-NZ.txt"),
    "websearch_total": sum(searches), "websearch_min": min(searches),
    "websearch_max": max(searches),
}
bad = 0
for k, v in stated.items():
    flag = "" if computed[k] == v else "   <-- DIFFERS"
    bad += bool(flag)
    print(f"{k:24} stated {v:>5}  computed {computed[k]:>5}{flag}")
print("websearch exact total:", sum(searches))

print("\nWindow:", today, "to", window_end, window_end.strftime("%a %d %b"))
weekdays = {"2026-11-26": "Thu", "2026-11-27": "Fri", "2026-11-28": "Sat", "2026-11-29": "Sun",
            "2026-11-30": "Mon", "2026-12-01": "Tue", "2026-12-03": "Thu", "2026-12-04": "Fri",
            "2026-12-06": "Sun", "2026-12-07": "Mon", "2026-12-08": "Tue", "2026-12-10": "Thu",
            "2026-12-11": "Fri", "2026-12-23": "Wed", "2027-01-11": "Mon", "2027-01-23": "Sat"}
for d, w in weekdays.items():
    got = dt.date.fromisoformat(d).strftime("%a")
    flag = "" if got == w else "   <-- DIFFERS"
    bad += bool(flag)
    print(d, "stated", w, "computed", got, flag)
print("\nwindow deadlines:")
for r in in_window:
    print(" ", r["closes"], r["fit"], r["company"], "|", r["role"][:60])
print("\nMISMATCHES:", bad)
