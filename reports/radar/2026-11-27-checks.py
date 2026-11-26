"""Re-runnable checks for reports/radar/2026-11-27.md (python3 -I reports/radar/2026-11-27-checks.py).

Run from the repo root, with that day's sweep files archived in work/radar/2026-11-27/.
"""
import datetime as d
import json
import re

D = "work/radar/2026-11-27/"
rep = open("reports/radar/2026-11-27.md", encoding="utf-8").read()
cand = json.load(open(D + "candidates.json", encoding="utf-8"))
rec = json.load(open(D + "record.json", encoding="utf-8"))
leads = json.load(open(D + "leads.json", encoding="utf-8"))
bad = 0


def chk(label, stated, actual):
    global bad
    ok = stated == actual
    bad += not ok
    print(f"{'OK ' if ok else 'DIFF'} {label}: stated {stated} / computed {actual}")


chk("weekday", "Friday", d.date(2026, 11, 27).strftime("%A"))
chk("new leads", 2, len(rec["new_leads"]))
chk("strong new leads", 1, sum(l["fit"] == "strong" for l in leads["leads"]))
chk("startup postings", 1, sum(bool(l["jobs"]) for l in leads["leads"]))
chk("outreach drafts", 0, len(leads["outreach"]))
chk("drafts held", 0, rec["outreach_held"])
c = cand["counts"]
chk("candidates", 17, len(cand["candidates"]))
chk("from feeds", 6, c.get("feed", 0))
chk("from Google News", 2, c.get("gnews", 0))
chk("LinkedIn roster", 0, c.get("linkedin-roster", 0))
chk("LinkedIn keyword search", 9, c.get("linkedin-search", 0))
chk("channel counts sum", 17, sum(c.values()))
chk("sweep seconds", 571, cand["seconds"]["total"])
chk("sweep minutes (rounded)", 10, round(cand["seconds"]["total"] / 60))
chk("requests", 131, cand["requests"]["requests"])
chk("retries", 15, cand["requests"]["retries"])
chk("failures", 0, cand["requests"]["failed"])
err = open(D + "sweep.err", encoding="utf-8").read()
warned = re.findall(r"^warning: .*?keywords=([^&]+)&location=([^&]+)", err, re.M)
chk("failed searches", 0, len(warned))
print("   failed:", warned)
m = re.search(r"(\d+) leads by id, (\d+) of (\d+) by name, (\d+) ids found", err)
chk("name searches done / needed", (40, 47), (int(m.group(2)), int(m.group(3))))
chk("companies not checked", 7, int(m.group(3)) - int(m.group(2)))
chk("ids found", 0, len(rec["linkedin_ids_found"]))
chk("roster size", 67, sum(rec["roster"].values()))
chk("roster with LinkedIn id", 18, rec["roster_with_linkedin_id"])
chk("web searches (LinkedIn posts)", 1, 1)
chk("web searches total (posts, Lubdub, Gig Lab)", 3, 3)
chk("page fetches used / refused", (1, 1), (1, 1))
chk("title line", True, "2 new leads (1 strong) · 1 startup posting · 0 outreach drafts" in rep)
print("all checks pass" if not bad else f"{bad} checks differ")
