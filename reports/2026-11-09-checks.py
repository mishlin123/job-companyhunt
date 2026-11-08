"""Checks the numbers stated in reports/2026-11-09.md against the run's data.

Run from the repo root: python3 -I reports/2026-11-09-checks.py
The work/ files are git-ignored, so this re-runs only on the computer that made the scan.
"""
import csv
import glob
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone

s = json.load(open("work/summary.json"))
n = json.load(open("work/network.json"))
report = open("reports/2026-11-09.md").read()
rows = []


def check(label, stated, computed):
    rows.append((label, stated, computed, "ok" if stated == computed else "DIFFERS"))


DUP = "University and institute research labs"
CHEM = ("Thames Water Utilities Limited", "Agri-Food and Biosciences Institute")

# New roles: tracker totals, then distinct roles after dropping the two RMIT duplicates
fits = Counter(r["fit"] for r in s["new_roles"])
check("new roles, tracker", 44, len(s["new_roles"]))
distinct = [r for r in s["new_roles"] if not r["company"].startswith(DUP)]
df = Counter(r["fit"] for r in distinct)
check("new roles, distinct", 42, len(distinct))
check("new strong", 5, df["strong"])
check("new possible", 19, df["possible"])
check("new signal", 18, df["signal"])
check("duplicates removed", 2, len(s["new_roles"]) - len(distinct))
check("news items", 0, len(s["new_news"]))

# Applications
a = s["applications"]
check("applications this week", 1, a["this_week"])
check("weekly target", 8, a["weekly_target"])
check("applications last 4 weeks", 41, a["last_4_weeks"])
check("applications total", 41, a["total"])

# Queue and deadlines as shown in the report
queue = [r for r in s["apply_queue"] if not r["company"].startswith(DUP) and r["company"] not in CHEM]
check("apply queue rows shown", 22, len(queue))
gone = {r["id"] for r in s["no_longer_found"]} | {r["id"] for r in s["closed"]}
applied = {r["id"] for r in s["applied"]}
dl = [r for r in s["deadlines_soon"] if r["id"] not in gone and r["id"] not in applied
      and not r["company"].startswith(DUP) and r["company"] not in CHEM and "Gent" not in r["url"]]
check("deadlines shown, next 6 weeks", 46, len(dl))
check("all shown deadlines within 6 weeks", True, all(r["closes"] <= str(date(2026, 11, 9) + timedelta(weeks=6)) for r in dl))
strong_this_week = [r["company"] for r in dl if r["fit"] == "strong" and r["closes"] <= "2026-11-15"]
check("only strong role closing this week is Leeds", ["University of Leeds"], strong_this_week)

# Coverage
check("companies checked", 349, len(s["companies_checked"]))
check("companies failed", 0, len(s["companies_failed"]))
check("companies not reported", 0, len(s["companies_not_reported"]))
check("board decisions read", 96, len(glob.glob("work/board-clicks/decisions/*.json")))
count = lambda f: sum(1 for l in open(f) if not l.startswith("#") and l.strip())
check("SEEK AU listings", 285, count("work/seek-AU.txt"))
check("SEEK NZ listings", 62, count("work/seek-NZ.txt"))
check("UK listings", 238, count("work/uk-jobs.txt"))
hdr = open("work/uk-jobs.txt").readline()
for nation, val in [("England", 166), ("Scotland", 34), ("Wales", 18), ("Northern Ireland", 20)]:
    check(f"UK {nation}", val, int(re.search(nation + r" (\d+)", hdr).group(1)))

# Search budget: per-batch WebSearch use as reported by each batch
used = {1: 7, 2: 6, 3: 7, 4: 7, 5: 7, 6: 7, 7: 7, 8: 6, 9: 6, 10: 7, 11: 7, 12: 7, 13: 7,
        14: 9, 15: 6, 16: 8, 17: 11, 18: 3, 19: 12, "events": 8}
check("WebSearch calls", 145, sum(used.values()))
check("under cap of 180", True, sum(used.values()) < 180)

# Outreach
outreach = {o["company"]: o for o in json.load(open("work/outreach.json"))}
check("drafts added", 3, len(outreach))
for c, o in outreach.items():
    check(f"{c} note under 300 chars", True, len(o["draft"]) < 300)
check("outreach drafts waiting", 13, len(n["outreach_waiting"]))
check("outreach sent", 0, n["outreach_counts"]["sent"])

# Dates and times (UK is on GMT in November; NZ is on NZDT, UTC+13)
nzdt = timezone(timedelta(hours=13))
ab = datetime(2026, 11, 10, 23, 59, tzinfo=timezone.utc).astimezone(nzdt)
check("abstract deadline in NZ", "Wed 11 Nov 12:59", ab.strftime("%a %-d %b %H:%M"))
web = datetime(2026, 11, 23, 11, 30, tzinfo=timezone.utc).astimezone(nzdt)
check("AMR webinar in NZ", "Tue 24 Nov 00:30", web.strftime("%a %-d %b %H:%M"))
check("9 Nov 2026 is a Monday", "Monday", date(2026, 11, 9).strftime("%A"))
check("12 Nov 2026 is a Thursday", "Thursday", date(2026, 11, 12).strftime("%A"))

# Five live ads still hidden by the 27 Oct clean-up
roles = list(csv.DictReader(open("tracker/roles.csv")))
for url in ["95288648", "95446156", "95244199", "95248714", "95426237"]:
    st = [r["status"] for r in roles if r["url"].endswith(url)]
    check(f"seek {url} is ineligible", ["ineligible"], st)
    check(f"seek {url} linked in report", True, url in report)

bad = [r for r in rows if r[3] != "ok"]
for r in rows:
    print(f"{r[3]:8} {r[0]}: stated {r[1]} / computed {r[2]}")
print(f"\n{len(rows)} checks, {len(bad)} differ")
