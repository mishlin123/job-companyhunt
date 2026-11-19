"""Re-runnable checks for reports/radar/2026-11-20.md (python3 -I reports/radar/2026-11-20-checks.py).

Run from the repo root, with that day's sweep files archived in work/radar/2026-11-20/.
"""
import datetime as d
import json
import re

D = "work/radar/2026-11-20/"
rep = open("reports/radar/2026-11-20.md", encoding="utf-8").read()
cand = json.load(open(D + "candidates.json", encoding="utf-8"))
rec = json.load(open(D + "record.json", encoding="utf-8"))
leads = json.load(open(D + "leads.json", encoding="utf-8"))
bad = 0


def chk(label, stated, actual):
    global bad
    ok = stated == actual
    bad += not ok
    print(f"{'OK ' if ok else 'DIFF'} {label}: stated {stated} / computed {actual}")


chk("weekday", "Friday", d.date(2026, 11, 20).strftime("%A"))
chk("new leads", 1, len(rec["new_leads"]))
chk("strong new leads", 0, sum(l["fit"] == "strong" for l in leads["leads"] if l["company"] in rec["new_leads"]))
chk("startup postings (keyword-sweep jobs kept)", 1, sum(1 for l in leads["leads"] if l["company"] == "Zya"))
chk("outreach drafts added", 0, len(rec["outreach_added"]))
chk("drafts held", 0, rec["outreach_held"])
chk("roster rows refreshed", 2, len(rec["updated_leads"]))
c = cand["counts"]
chk("candidates", 26, len(cand["candidates"]))
chk("from feeds", 0, c.get("feed", 0))
chk("from Google News", 7, c.get("gnews", 0))
chk("LinkedIn roster", 1, c.get("linkedin-roster", 0))
chk("LinkedIn keyword search", 18, c.get("linkedin-search", 0))
chk("channel counts sum to candidates", 26, sum(c.values()))
chk("sweep seconds", 594, cand["seconds"]["total"])
chk("requests", 142, cand["requests"]["requests"])
chk("retries", 18, cand["requests"]["retries"])
chk("failures", 1, cand["requests"]["failed"])
chk("warnings", 2, len(cand["warnings"]))
err = open(D + "sweep.err", encoding="utf-8").read()
m = re.search(r"(\d+) leads by id, (\d+) of (\d+) by name, (\d+) ids found", err)
chk("name searches done / needed", (40, 44), (int(m.group(2)), int(m.group(3))))
chk("companies not checked", 4, int(m.group(3)) - int(m.group(2)))
chk("ids found (sweep log)", 0, int(m.group(4)))
chk("ids found (record)", [], rec["linkedin_ids_found"])
chk("roster size", 61, sum(rec["roster"].values()))
chk("roster with LinkedIn id", 16, rec["roster_with_linkedin_id"])
chk("page fetches (Better Dairy x2 + Zya + Constructive Bio)", 4, 2 + 1 + 1)
chk("web searches (LinkedIn posts + Sunshiki)", 2, 1 + 1)
for o in leads["outreach"]:
    n = len(o["draft"])
    chk(f"{o['company']} note under 300", True, n < 300)
# Quoted, not computed:
print("quoted from Zya's LinkedIn ad, 20 Nov: Masters or PhD; £45,000-£60,000; London on-site")
print("quoted from The Bridge / FundedIQ: Sunshiki pre-seed ¥80M, listed as US$500K")
print("all checks pass" if not bad else f"{bad} checks differ")
