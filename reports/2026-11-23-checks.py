"""Checks every computed number stated in reports/2026-11-23.md against work/summary.json,
work/network.json, the board files and the subagents' reported search use.
Run from the repo root: python3 -I reports/2026-11-23-checks.py"""
import json, collections

S = json.load(open("work/summary.json"))
N = json.load(open("work/network.json"))
bad = 0


def check(label, stated, actual):
    global bad
    ok = stated == actual
    bad += not ok
    print(f"{'ok  ' if ok else 'DIFF'} {label}: stated {stated}, computed {actual}")


fits = collections.Counter(r["fit"] for r in S["new_roles"])
check("new roles", 60, len(S["new_roles"]))
check("new strong", 8, fits["strong"])
check("new possible", 38, fits["possible"])
check("new signal", 14, fits["signal"])
check("queue roles closing today 23 Nov", 5, sum(r["closes"] == "2026-11-23" for r in S["apply_queue"]))
a = S["applications"]
check("applications this week", 0, a["this_week"])
check("weekly target", 8, a["weekly_target"])
check("applications last 4 weeks", 6, a["last_4_weeks"])
check("applications total", 41, a["total"])
check("news items", 5, len(S["new_news"]))
check("deadlines in next 6 weeks", 50, len(S["deadlines_soon"]))
check("companies checked", 405, len(S["companies_checked"]))
check("companies failed", 0, len(S["companies_failed"]))
check("companies not reported", 0, len(S["companies_not_reported"]))
check("tracker problems", 0, len(S["problems"]))
check("new outreach drafts", 3, sum(o["created"] == "2026-11-23" for o in N["outreach_waiting"]))
check("new events", 3, len(N["events_new"]))

# Board files: first line is a header in each.
seek_au = sum(1 for _ in open("work/seek-AU.txt")) - 1
seek_nz = sum(1 for _ in open("work/seek-NZ.txt")) - 1
uk = sum(1 for _ in open("work/uk-jobs.txt")) - 1
check("SEEK AU listings", 268, seek_au)
check("SEEK NZ listings", 41, seek_nz)
check("UK listings", 240, uk)
head = open("work/uk-jobs.txt").readline()
check("UK nation counts in header", True, all(s in head for s in ("of 1310", "England 159", "Scotland 40", "Wales 17", "Northern Ireland 24")))
check("England+Scotland+Wales+NI = UK total", 240, 159 + 40 + 17 + 24)

# WebSearch use as reported by each batch (events batch last); budgets 7 company, 13 sweep, 8 events.
used = {1: 7, 2: 7, 3: 7, 4: 7, 5: 7, 6: 7, 7: 7, 8: 6, 9: 6, 10: 7, 11: 7, 12: 7, 13: 7,
        14: 4, 15: 6, 16: 9, 17: 10, 18: 6, 19: 11, "events": 8}
budget = {**{i: 7 for i in range(1, 14)}, **{i: 13 for i in range(14, 20)}, "events": 8}
check("WebSearch budget total", 177, sum(budget.values()))
check("WebSearch calls used", 143, sum(used.values()))
check("sweep batch search use range", (4, 11), (min(used[i] for i in range(14, 20)), max(used[i] for i in range(14, 20))))
check("company batches that used their full 7", 11, sum(used[i] == 7 for i in range(1, 14)))

# Salary arithmetic quoted from postings is quoted, not computed, so it is not re-derived here.
print("\nall numbers match" if not bad else f"\n{bad} number(s) differ")

import datetime
wd = datetime.date(2026, 12, 4).strftime("%a")
print(("ok  " if wd == "Fri" else "DIFF") + f" 4 Dec 2026 weekday: stated Fri, computed {wd}")
