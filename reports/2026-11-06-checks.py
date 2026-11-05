"""Checks the numbers stated in reports/2026-11-06.md against the run's data.

Run from the repo root: python3 -I reports/2026-11-06-checks.py
The work/ files are git-ignored, so this re-runs only on the computer that made the scan.
"""
import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone

s = json.load(open("work/summary.json"))
n = json.load(open("work/network.json"))
rows = []


def check(label, stated, computed):
    rows.append((label, stated, computed, "ok" if stated == computed else "DIFFERS"))


fits = Counter(r["fit"] for r in s["new_roles"])
check("new roles", 85, len(s["new_roles"]))
check("new strong", 6, fits["strong"])
check("new possible", 50, fits["possible"])
check("new signal", 29, fits["signal"])
check("deadlines in next 6 weeks", 40, len(s["deadlines_soon"]))
check("news items", 0, len(s["new_news"]))
a = s["applications"]
check("applications this week", 5, a["this_week"])
check("weekly target", 8, a["weekly_target"])
check("applications last 4 weeks", 40, a["last_4_weeks"])
check("applications total", 40, a["total"])
check("apply queue rows", 24, len(s["apply_queue"]) - 1)  # report merges the two Deakin entries (same role)
check("companies checked", 342, len(s["companies_checked"]))
check("companies failed", 0, len(s["companies_failed"]))
check("still-open possible", 52, sum(r["fit"] == "possible" for r in s["still_open"]))
check("still-open strong", 9, sum(r["fit"] == "strong" for r in s["still_open"]))
check("outreach drafts waiting", 10, len(n["outreach_waiting"]))
check("outreach sent", 0, n["outreach_counts"]["sent"])

# Board import and job-board file sizes
import glob
check("board decisions imported", 95, len(glob.glob("work/board-clicks/decisions/*.json")))
check("SEEK AU listings", 287, sum(1 for l in open("work/seek-AU.txt") if not l.startswith("#") and l.strip()))
check("SEEK NZ listings", 63, sum(1 for l in open("work/seek-NZ.txt") if not l.startswith("#") and l.strip()))
check("UK listings", 262, sum(1 for l in open("work/uk-jobs.txt") if not l.startswith("#") and l.strip()))

# Search budget: per-batch WebSearch use as reported by each batch (b18 said "about 5")
used = {1: 7, 2: 7, 3: 7, 4: 7, 5: 7, 6: 7, 7: 7, 8: 7, 9: 7, 10: 6, 11: 7, 12: 6, 13: 7,
        14: 6, 15: 3, 16: 5, 17: 13, 18: 5, 19: 9, "events": 7}
total = sum(used.values())
check("search total under 180", True, total < 180)
print(f"(searches used: about {total})")

# Dates
check("STP 2026 window length, days (6-16 Jan)", 10, (date(2027, 1, 16) - date(2027, 1, 6)).days)
uk_close = datetime(2026, 11, 6, 23, 59, tzinfo=timezone.utc)  # UK is on GMT in November
nzdt = timezone(timedelta(hours=13))
nz = uk_close.astimezone(nzdt)
check("Ingenza close in NZ time is ~1 pm Sat 7 Nov", "Sat 7 Nov 12:59", nz.strftime("%a %-d %b %H:%M"))
check("6 Nov 2026 is a Friday", "Friday", date(2026, 11, 6).strftime("%A"))
check("Pharmaron ad age on 6 Nov (posted 20 Aug), days", 78, (date(2026, 11, 6) - date(2026, 8, 20)).days)

for r in rows:
    print(" | ".join(str(x) for x in r))
bad = [r for r in rows if r[3] != "ok"]
print(f"{len(rows)} checks, {len(bad)} differ")
