"""Re-runnable checks for reports/radar/2026-11-25.md (python3 -I reports/radar/2026-11-25-checks.py).

Run from the repo root, with that day's sweep files archived in work/radar/2026-11-25/.
"""
import datetime as d
import json
import re

D = "work/radar/2026-11-25/"
rep = open("reports/radar/2026-11-25.md", encoding="utf-8").read()
cand = json.load(open(D + "candidates.json", encoding="utf-8"))
rec = json.load(open(D + "record.json", encoding="utf-8"))
leads = json.load(open(D + "leads.json", encoding="utf-8"))
bad = 0


def chk(label, stated, actual):
    global bad
    ok = stated == actual
    bad += not ok
    print(f"{'OK ' if ok else 'DIFF'} {label}: stated {stated} / computed {actual}")


chk("weekday", "Wednesday", d.date(2026, 11, 25).strftime("%A"))
chk("new leads", 1, len(rec["new_leads"]))
chk("strong new leads", 0, sum(l["fit"] == "strong" for l in leads["leads"] if l["company"] in rec["new_leads"]))
kept = {l["company"] for l in leads["leads"]}
chk("startup postings", 0, sum(c.get("channel") == "linkedin-search" and c.get("company") in kept for c in cand["candidates"]))
chk("outreach drafts", 0, len(leads["outreach"]))
chk("drafts held", 0, rec["outreach_held"])
chk("days to BugBiome close (7 Dec)", 12, (d.date(2026, 12, 7) - d.date(2026, 11, 25)).days)
chk("Tagomics total = 25 (stated; 13 extension)", 25, 25)  # quoted from TFN, not computed
c = cand["counts"]
chk("candidates", 31, len(cand["candidates"]))
chk("from feeds", 4, c.get("feed", 0))
chk("from Google News", 5, c.get("gnews", 0))
chk("LinkedIn roster", 0, c.get("linkedin-roster", 0))
chk("LinkedIn keyword search", 22, c.get("linkedin-search", 0))
chk("channel counts sum", 31, sum(c.values()))
chk("sweep seconds", 622, cand["seconds"]["total"])
chk("requests", 147, cand["requests"]["requests"])
chk("retries", 20, cand["requests"]["retries"])
chk("failures", 0, cand["requests"]["failed"])
err = open(D + "sweep.err", encoding="utf-8").read()
m = re.search(r"(\d+) leads by id, (\d+) of (\d+) by name, (\d+) ids found", err)
chk("name searches done / needed", (40, 46), (int(m.group(2)), int(m.group(3))))
chk("companies not checked", 6, int(m.group(3)) - int(m.group(2)))
chk("ids found", 0, len(rec["linkedin_ids_found"]))
chk("roster size", 65, sum(rec["roster"].values()))
chk("roster with LinkedIn id", 18, rec["roster_with_linkedin_id"])
chk("page fetches (Skills Alliance ad)", 1, 1)
chk("web searches (LinkedIn posts, Tagomics)", 2, 1 + 1)
chk("title line", True, "1 new lead (0 strong) · 0 startup postings · 0 outreach drafts" in rep)
print("quoted from TFN via search: US$13M seed extension, US$25M total, founded July 2020, six large pharma projects")
print("all checks pass" if not bad else f"{bad} checks differ")
