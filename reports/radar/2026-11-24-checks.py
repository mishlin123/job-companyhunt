"""Re-runnable checks for reports/radar/2026-11-24.md (python3 -I reports/radar/2026-11-24-checks.py).

Run from the repo root, with that day's sweep files archived in work/radar/2026-11-24/.
"""
import datetime as d
import json
import re

D = "work/radar/2026-11-24/"
rep = open("reports/radar/2026-11-24.md", encoding="utf-8").read()
cand = json.load(open(D + "candidates.json", encoding="utf-8"))
rec = json.load(open(D + "record.json", encoding="utf-8"))
leads = json.load(open(D + "leads.json", encoding="utf-8"))
bad = 0


def chk(label, stated, actual):
    global bad
    ok = stated == actual
    bad += not ok
    print(f"{'OK ' if ok else 'DIFF'} {label}: stated {stated} / computed {actual}")


chk("weekday", "Tuesday", d.date(2026, 11, 24).strftime("%A"))
chk("new leads", 1, len(rec["new_leads"]))
chk("strong new leads", 0, sum(l["fit"] == "strong" for l in leads["leads"] if l["company"] in rec["new_leads"]))
kept = {l["company"] for l in leads["leads"]}
chk("startup postings (keyword-sweep jobs kept)", 0,
    sum(c.get("channel") == "linkedin-search" and c.get("company") in kept for c in cand["candidates"]))
chk("outreach drafts written", 0, len(leads["outreach"]))
chk("held drafts added today (Zya, BugBiome)", ["Zya", "BugBiome"], rec["outreach_added"])
chk("drafts held", 0, rec["outreach_held"])
chk("roster rows refreshed", 2, len(rec["updated_leads"]))
chk("roster job candidates (Atisama, Loam Bio, Constructive Bio)", 3, sum("lead" in c for c in cand["candidates"]))
chk("days to BugBiome close (7 Dec)", 13, (d.date(2026, 12, 7) - d.date(2026, 11, 24)).days)
chk("Head of People days after DSP RA (20 Nov -> 23 Nov)", 3, (d.date(2026, 11, 23) - d.date(2026, 11, 20)).days)
c = cand["counts"]
chk("candidates", 30, len(cand["candidates"]))
chk("from feeds", 6, c.get("feed", 0))
chk("from Google News", 3, c.get("gnews", 0))
chk("LinkedIn roster", 3, c.get("linkedin-roster", 0))
chk("LinkedIn keyword search", 18, c.get("linkedin-search", 0))
chk("channel counts sum to candidates", 30, sum(c.values()))
chk("sweep seconds", 572, cand["seconds"]["total"])
chk("requests", 136, cand["requests"]["requests"])
chk("retries", 10, cand["requests"]["retries"])
chk("failures", 0, cand["requests"]["failed"])
chk("feed warnings", 0, len(cand["warnings"]))
err = open(D + "sweep.err", encoding="utf-8").read()
m = re.search(r"(\d+) leads by id, (\d+) of (\d+) by name, (\d+) ids found", err)
chk("name searches done / needed", (40, 47), (int(m.group(2)), int(m.group(3))))
chk("companies not checked", 7, int(m.group(3)) - int(m.group(2)))
chk("ids found", 2, len(rec["linkedin_ids_found"]))
chk("roster size", 64, sum(rec["roster"].values()))
chk("roster with LinkedIn id", 18, rec["roster_with_linkedin_id"])
chk("page fetches (eXmoor, Atisama, Andfoods)", 3, 1 + 1 + 1)
chk("web searches (LinkedIn posts + Andfoods)", 2, 1 + 1)
chk("title line in report", True, "1 new lead (0 strong) · 0 startup postings · 0 outreach drafts" in rep)
# Quoted, not computed:
print("quoted from eXmoor ad: 'PhD in relevant area + 2 years industry exp.' / 'BSc/MSc 5+ years'; 12-month fixed term")
print("quoted from Atisama ad: PhD, or Masters with relevant experience at Research Scientist level; up to five years")
print("quoted from Tech.eu headline: BBB invests £43M; from web search (Massey/RNZ): Andfoods NZ$2.7M seed, 2024")
print("all checks pass" if not bad else f"{bad} checks differ")
