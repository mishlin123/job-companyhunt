"""Checks the numbers stated in reports/2026-11-16.md against the run's data.

Run from the repo root: python3 -I reports/2026-11-16-checks.py
The work/ files are git-ignored, so this re-runs only on the computer that made the scan.
"""
import glob
import json
from collections import Counter

s = json.load(open("work/summary.json"))
n = json.load(open("work/network.json"))
rows = []


def check(label, stated, computed):
    rows.append((label, stated, computed, "ok" if stated == computed else "DIFFERS"))


fits = Counter(r["fit"] for r in s["new_roles"])
check("new roles", 80, len(s["new_roles"]))
check("new strong", 6, fits["strong"])
check("new possible", 45, fits["possible"])
check("new signal", 29, fits["signal"])
check("news items", 0, len(s["new_news"]))
a = s["applications"]
check("applications this week", 0, a["this_week"])
check("weekly target", 8, a["weekly_target"])
check("applications last 4 weeks", 41, a["last_4_weeks"])
check("applications total", 41, a["total"])
today = [r for r in s["apply_queue"] if r["closes"] == "2026-11-16"]
check("possible roles closing 16 Nov in queue", 6, len([r for r in today if r["fit"] == "possible"]))
check("companies checked", 397, len(s["companies_checked"]))
check("companies failed", 0, len(s["companies_failed"]))
check("companies not reported", 0, len(s["companies_not_reported"]))
check("deadlines_soon window (max days)", True, max(r["closes"] for r in s["deadlines_soon"]) <= "2026-12-28")
check("new events", 2, len(n["events_new"]))
check("outreach tally sent", 0, n["outreach_counts"]["sent"])
check("older outreach waiting", 13, len([o for o in n["outreach_waiting"] if o["created"] != "2026-11-16"]))
check("board decision records", 96, len(glob.glob("work/board-clicks/decisions/*.json")))
seek_au = sum(1 for l in open("work/seek-AU.txt") if not l.startswith("#"))
seek_nz = sum(1 for l in open("work/seek-NZ.txt") if not l.startswith("#"))
check("SEEK AU listings", 294, seek_au)
check("SEEK NZ listings", 59, seek_nz)
# Strong roles named as new in the TL;DR and actions
names = {r["company"] for r in s["new_roles"] if r["fit"] == "strong"}
for c in ["Thermo Fisher Scientific", "Convatec", "Mars", "University of York", "Evolve Scientific", "Kōrure Limited"]:
    check(f"new strong includes {c}", True, c in names)
# Sweep batches: off-watchlist employers found ("found via sweep" in notes)
for b, stated in [(14, 47), (15, 35), (16, 14), (18, 74)]:
    f = json.load(open(f"work/findings-{b}.json"))
    found = sum(1 for c in f["companies"] if "found via sweep" in (c.get("notes") or "").lower())
    check(f"batch {b} off-watchlist employers", stated, found)
# WebSearch calls as reported by each batch's reply
used = {1: 6, 2: 6, 3: 6, 4: 6, 5: 6, 6: 6, 7: 6, 8: 6, 9: 4, 10: 6, 11: 6, 12: 6, 13: 7,
        14: 8, 15: 6, 16: 12, 17: 3, 18: 2, 19: 12, "events": 8}
budget = 13 * 6 + 6 * 14 + 8
check("WebSearch budget", 170, budget)
check("WebSearch used", 128, sum(used.values()))

for r in rows:
    print(f"{r[3]:8} {r[0]}: stated {r[1]}, computed {r[2]}")
