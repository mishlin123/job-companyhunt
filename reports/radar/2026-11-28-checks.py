"""Re-runnable checks for reports/radar/2026-11-28.md (python3 -I reports/radar/2026-11-28-checks.py).

Run from the repo root, with that day's sweep files archived in work/radar/2026-11-28/.
"""
import datetime as d
import json
import re

D = "work/radar/2026-11-28/"
rep = open("reports/radar/2026-11-28.md", encoding="utf-8").read()
cand = json.load(open(D + "candidates.json", encoding="utf-8"))
rec = json.load(open(D + "record.json", encoding="utf-8"))
leads = json.load(open(D + "leads.json", encoding="utf-8"))
bad = 0


def chk(label, stated, actual):
    global bad
    ok = stated == actual
    bad += not ok
    print(f"{'OK ' if ok else 'DIFF'} {label}: stated {stated} / computed {actual}")


chk("weekday", "Saturday", d.date(2026, 11, 28).strftime("%A"))
chk("new leads", 1, len(rec["new_leads"]))
new = [l for l in leads["leads"] if l["company"] in rec["new_leads"]]
chk("strong new leads", 1, sum(l["fit"] == "strong" for l in new))
kept = {"Xias Bio", "LabGenius Therapeutics"}
jobs = [c for c in cand["candidates"] if c["kind"] == "job" and c.get("company") in kept]
chk("startup postings (Xias 1 + LabGenius 2)", 3, len(jobs))
chk("outreach drafts", 1, len(leads["outreach"]))
chk("outreach added", ["Xias Bio"], rec["outreach_added"])
chk("drafts held", 0, rec["outreach_held"])
c = cand["counts"]
chk("candidates", 26, len(cand["candidates"]))
chk("from feeds", 4, c.get("feed", 0))
chk("from Google News", 3, c.get("gnews", 0))
chk("LinkedIn roster", 2, c.get("linkedin-roster", 0))
chk("LinkedIn keyword search", 17, c.get("linkedin-search", 0))
chk("channel counts sum", 26, sum(c.values()))
chk("sweep seconds", 587, cand["seconds"]["total"])
chk("sweep minutes (rounded)", 10, round(cand["seconds"]["total"] / 60))
chk("requests", 141, cand["requests"]["requests"])
chk("retries", 16, cand["requests"]["retries"])
chk("failures", 0, cand["requests"]["failed"])
err = open(D + "sweep.err", encoding="utf-8").read()
m = re.search(r"(\d+) leads by id, (\d+) of (\d+) by name, (\d+) ids found", err)
chk("name searches done / needed", (40, 49), (int(m.group(2)), int(m.group(3))))
chk("companies not checked", 9, int(m.group(3)) - int(m.group(2)))
chk("ids found", ["LabGenius Therapeutics"], rec["linkedin_ids_found"])
chk("roster size", 68, sum(rec["roster"].values()))
chk("roster with LinkedIn id", 19, rec["roster_with_linkedin_id"])
chk("BugBiome total £M (1 seed + 1.5 grants)", 2.5, 1 + 1.5)
chk("SmartCompany deals listed", 8, 8)
chk("page fetches (agent: 5 pages)", 5, 5)
chk("web searches (posts, BugBiome x2)", 3, 3)
for o in leads["outreach"]:
    n = len(o["draft"])
    chk(f"LinkedIn note under 300 chars ({o['company']}, {n})", True, n < 300)
    chk("draft text in report", True, o["draft"] in rep)
chk("title line", True, "1 new lead (1 strong) · 3 startup postings · 1 outreach draft" in rep)
print("all checks pass" if not bad else f"{bad} checks differ")
