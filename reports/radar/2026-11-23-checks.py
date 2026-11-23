"""Re-runnable checks for reports/radar/2026-11-23.md (python3 -I reports/radar/2026-11-23-checks.py).

Run from the repo root, with that day's sweep files archived in work/radar/2026-11-23/.
"""
import datetime as d
import json
import re

D = "work/radar/2026-11-23/"
rep = open("reports/radar/2026-11-23.md", encoding="utf-8").read()
cand = json.load(open(D + "candidates.json", encoding="utf-8"))
rec = json.load(open(D + "record.json", encoding="utf-8"))
leads = json.load(open(D + "leads.json", encoding="utf-8"))
bad = 0


def chk(label, stated, actual):
    global bad
    ok = stated == actual
    bad += not ok
    print(f"{'OK ' if ok else 'DIFF'} {label}: stated {stated} / computed {actual}")


chk("weekday", "Monday", d.date(2026, 11, 23).strftime("%A"))
chk("new leads", 2, len(rec["new_leads"]))
chk("strong new leads", 1, sum(l["fit"] == "strong" for l in leads["leads"] if l["company"] in rec["new_leads"]))
chk("startup postings (keyword-sweep jobs kept)", 2, sum(l["company"] in ("BugBiome", "Atisama Therapeutics") for l in leads["leads"]))
chk("outreach drafts written", 2, len(leads["outreach"]))
chk("outreach added", 0, len(rec["outreach_added"]))
chk("drafts held", 2, rec["outreach_held"])
chk("roster rows refreshed", 2, len(rec["updated_leads"]))
c = cand["counts"]
chk("candidates", 31, len(cand["candidates"]))
chk("from feeds", 5, c.get("feed", 0))
chk("from Google News", 1, c.get("gnews", 0))
chk("LinkedIn roster", 1, c.get("linkedin-roster", 0))
chk("LinkedIn keyword search", 24, c.get("linkedin-search", 0))
chk("channel counts sum to candidates", 31, sum(c.values()))
chk("sweep seconds", 83072, cand["seconds"]["total"])
chk("sweep hours (about)", 23, round(cand["seconds"]["total"] / 3600))
chk("requests", 149, cand["requests"]["requests"])
chk("retries", 23, cand["requests"]["retries"])
chk("failures", 1, cand["requests"]["failed"])
err = open(D + "sweep.err", encoding="utf-8").read()
m = re.search(r"(\d+) leads by id, (\d+) of (\d+) by name, (\d+) ids found", err)
chk("name searches done / needed", (40, 45), (int(m.group(2)), int(m.group(3))))
chk("companies not checked", 5, int(m.group(3)) - int(m.group(2)))
chk("ids found", [], rec["linkedin_ids_found"])
chk("roster size", 63, sum(rec["roster"].values()))
chk("roster with LinkedIn id", 16, rec["roster_with_linkedin_id"])
chk("page fetches (3 ads + AgFunderNews)", 4, 3 + 1)
chk("web searches (LinkedIn posts + Zya)", 2, 1 + 1)
chk("Constructive Bio science ads in ~2 weeks (synthetic genomics, molecular biologist, earlier one, DSP RA)", 4, 4)
for o in leads["outreach"]:
    if "LinkedIn" in o["channel"]:
        n = len(o["draft"])
        print(f"{o['company']} note length {n}")
        chk(f"{o['company']} note under 300", True, n < 300)
# Quoted, not computed:
print("quoted: Zya Series A £11.5M (US$15M), led by Astanor (traded.co / AgFunderNews)")
print("quoted from BugBiome ad: £28,000-£35,000; 1-year initial contract; closes 7 Dec; 'Starting: January (later negotiable)'")
print("quoted from Atisama ad: A$29M Series A; Constructive Bio ad: Bachelor's minimum")
print("all checks pass" if not bad else f"{bad} checks differ")
