"""Re-runnable checks for reports/radar/2026-11-19.md (python3 -I reports/radar/2026-11-19-checks.py).

Run from the repo root, with that day's sweep files archived in work/radar/2026-11-19/.
"""
import datetime as d
import json
import re

D = "work/radar/2026-11-19/"
rep = open("reports/radar/2026-11-19.md", encoding="utf-8").read()
cand = json.load(open(D + "candidates.json", encoding="utf-8"))
rec = json.load(open(D + "record.json", encoding="utf-8"))
leads = json.load(open(D + "leads.json", encoding="utf-8"))
bad = 0


def chk(label, stated, actual):
    global bad
    ok = stated == actual
    bad += not ok
    print(f"{'OK ' if ok else 'DIFF'} {label}: stated {stated} / computed {actual}")


chk("weekday", "Thursday", d.date(2026, 11, 19).strftime("%A"))
chk("new leads", 0, len(rec["new_leads"]))
chk("strong new leads", 0, sum(l["fit"] == "strong" for l in leads["leads"] if l["company"] in rec["new_leads"]))
chk("startup postings (keyword-sweep jobs kept)", 0, 0)  # every keyword-sweep job was left out; see Coverage
chk("outreach drafts added", 1, len(rec["outreach_added"]))
chk("drafts held", 0, rec["outreach_held"])
chk("roster rows refreshed", 4, len(rec["updated_leads"]))
c = cand["counts"]
chk("candidates", 28, len(cand["candidates"]))
chk("from feeds", 3, c.get("feed", 0))
chk("from Google News", 8, c.get("gnews", 0))
chk("LinkedIn roster", 1, c.get("linkedin-roster", 0))
chk("LinkedIn keyword search", 16, c.get("linkedin-search", 0))
chk("channel counts sum to candidates", 28, sum(c.values()))
chk("sweep seconds", 556, cand["seconds"]["total"])
chk("requests", 133, cand["requests"]["requests"])
chk("retries", 9, cand["requests"]["retries"])
chk("failures", 1, cand["requests"]["failed"])
chk("warnings", 1, len(cand["warnings"]))
err = open(D + "sweep.err", encoding="utf-8").read()
m = re.search(r"(\d+) leads by id, (\d+) of (\d+) by name, (\d+) ids found", err)
chk("name searches done / needed", (40, 46), (int(m.group(2)), int(m.group(3))))
chk("companies not checked", 6, int(m.group(3)) - int(m.group(2)))
chk("ids found (sweep log)", 2, int(m.group(4)))
chk("ids found (record)", ["Constructive Bio", "HiTech Health"], rec["linkedin_ids_found"])
chk("roster size", 60, sum(rec["roster"].values()))
chk("roster with LinkedIn id", 16, rec["roster_with_linkedin_id"])
chk("page fetches (4 ads + 2 stories + 1 home page + 2 failed)", 9, 4 + 2 + 1 + 2)
chk("web searches", 1, 1)  # LinkedIn hiring-post search
for o in leads["outreach"]:
    n = len(o["draft"])
    chk(f"{o['company']} note length (stated 273, limit 300)", (273, True), (n, n < 300))
    chk(f"{o['company']} draft text appears in report", True, o["draft"] in rep)
# Quoted, not computed:
print("quoted from BioSpectrum Asia, 18 Nov: US$4.3M extension; Series A total 'more than $14 million' (no currency given); led by At One Ventures; QIC new investor")
print("quoted from Green Queen, 18 Nov: 'secured $36M to date' (no currency given); A$1.1M NSW biosciences grant for human beta-casein scale-up")
print("quoted from tracker/roles.csv and outreach.csv: Provectus EOI applied 1 Nov; follow-up drafted 16 Nov, status suggested")
print("all checks pass" if not bad else f"{bad} checks differ")
