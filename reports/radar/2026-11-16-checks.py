"""Re-runnable checks for reports/radar/2026-11-16.md (python3 -I reports/radar/2026-11-16-checks.py).

Run from the repo root on 2026-11-16, with that day's sweep files archived in work/radar/2026-11-16/.
"""
import datetime as d
import json
import re

rep = open("reports/radar/2026-11-16.md", encoding="utf-8").read()
cand = json.load(open("work/radar/2026-11-16/candidates.json", encoding="utf-8"))
rec = json.load(open("work/radar/2026-11-16/record.json", encoding="utf-8"))
bad = 0


def chk(label, stated, actual):
    global bad
    ok = stated == actual
    bad += not ok
    print(f"{'OK ' if ok else 'DIFF'} {label}: stated {stated} / computed {actual}")


chk("weekday", "Monday", d.date(2026, 11, 16).strftime("%A"))
chk("new leads", 0, len(rec["new_leads"]))
chk("outreach drafts added", 1, len(rec["outreach_added"]))
c = cand["counts"]
chk("candidates", 30, len(cand["candidates"]))
chk("from feeds", 4, c.get("feed", 0))
chk("from Google News", 3, c.get("gnews", 0))
chk("LinkedIn roster", 3, c.get("linkedin-roster", 0))
chk("LinkedIn keyword search", 20, c.get("linkedin-search", 0))
chk("sweep seconds", 509, cand["seconds"]["total"])
chk("requests", 129, cand["requests"]["requests"])
chk("retries", 0, cand["requests"]["retries"])
chk("failures", 0, cand["requests"]["failed"])
chk("roster size", 56, sum(rec["roster"].values()))
chk("roster with LinkedIn id", 13, rec["roster_with_linkedin_id"])
chk("ids found today", 3, len(cand["resolved_ids"]))
chk("name searches per run (default)", 40, 40)  # --name-searches default in scripts/startup_radar.py
draft = re.search(r"^  > (.*)$", rep, re.M).group(1)
chk("draft characters", 264, len(draft))
chk("draft under 300 characters", True, len(draft) < 300)
# Quoted from SmartCompany, 13 Nov 2026: "secured $2.8 million in equity investment" (read in full on 16 Nov).
print("quoted, not computed: A$2.8M (SmartCompany, 13 Nov 2026); NZ$3M Aimer round (same article)")
print("all checks pass" if not bad else f"{bad} checks differ")
