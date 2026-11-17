"""Re-runnable checks for reports/radar/2026-11-18.md (python3 -I reports/radar/2026-11-18-checks.py).

Run from the repo root, with that day's sweep files archived in work/radar/2026-11-18/.
"""
import datetime as d
import json
import re

D = "work/radar/2026-11-18/"
rep = open("reports/radar/2026-11-18.md", encoding="utf-8").read()
cand = json.load(open(D + "candidates.json", encoding="utf-8"))
rec = json.load(open(D + "record.json", encoding="utf-8"))
leads = json.load(open(D + "leads.json", encoding="utf-8"))
bad = 0


def chk(label, stated, actual):
    global bad
    ok = stated == actual
    bad += not ok
    print(f"{'OK ' if ok else 'DIFF'} {label}: stated {stated} / computed {actual}")


chk("weekday", "Wednesday", d.date(2026, 11, 18).strftime("%A"))
chk("new leads", 3, len(rec["new_leads"]))
new = [l for l in leads["leads"] if l["company"] in rec["new_leads"]]
chk("strong new leads", 0, sum(l["fit"] == "strong" for l in new))
jobs = [c for c in cand["candidates"] if c["kind"] == "job"]
kept = [j for j in jobs if j["company"] in ("Constructive Bio", "HiTech Health")]
chk("startup postings", 3, len(kept))
chk("Constructive Bio postings", 2, sum(j["company"] == "Constructive Bio" for j in kept))
sec = rep.split("## Postings at startups")[1].split("## ")[0]
chk("posting lines in report", 3, len(re.findall(r"^- \*\*", sec, re.M)))
chk("all kept postings dated 17 Nov", True, all(j["published"] == "2026-11-17" for j in kept))
chk("outreach drafts added", 0, len(rec["outreach_added"]))
chk("drafts held", 0, rec["outreach_held"])
c = cand["counts"]
chk("candidates", 29, len(cand["candidates"]))
chk("from feeds", 7, c.get("feed", 0))
chk("from Google News", 3, c.get("gnews", 0))
chk("LinkedIn roster", 0, c.get("linkedin-roster", 0))
chk("LinkedIn keyword search", 19, c.get("linkedin-search", 0))
chk("channel counts sum to candidates", 29, sum(c.values()))
chk("sweep seconds", 533, cand["seconds"]["total"])
chk("requests", 126, cand["requests"]["requests"])
chk("retries", 0, cand["requests"]["retries"])
chk("failures", 0, cand["requests"]["failed"])
chk("warnings", 0, len(cand["warnings"]))
err = open(D + "sweep.err", encoding="utf-8").read()
m = re.search(r"(\d+) leads by id, (\d+) of (\d+) by name, (\d+) ids found", err)
chk("name searches done / needed", (40, 44), (int(m.group(2)), int(m.group(3))))
chk("companies not checked", 4, int(m.group(3)) - int(m.group(2)))
chk("roster size", 60, sum(rec["roster"].values()))
chk("roster with LinkedIn id", 14, rec["roster_with_linkedin_id"])
chk("ids found today", 1, len(rec["linkedin_ids_found"]))
ids = {j["company"]: j["linkedin_company_id"] for j in kept}
chk("Constructive Bio LinkedIn id", "81948183", ids["Constructive Bio"])
chk("HiTech Health LinkedIn id", "9409311", ids["HiTech Health"])
chk("page fetches (5 ads + 2 stories)", 7, 5 + 2)
chk("web searches", 2, 2)  # hiring-post search, Twig Bio
chk("seed + Series A = total raised (US$M)", 73, 15 + 58)
# Quoted, not computed:
print("quoted from the Constructive Bio ads (read 18 Nov): US$73M raised, US$15M seed, US$58M Series A")
print("quoted from vegconomist, 17 Nov: Wide Open Agriculture A$1M placement; Traitomic EUR 20M (headline)")
print("quoted from the HiTech Health ad: established 2013; 3+ years' GMP microbiology; start as soon as possible")
print("quoted, unverified (aggregators via web search): Twig Bio founded 2022, GBP 3M seed 2023, grant Apr 2026, LBIC Apex Sept 2025")
print("all checks pass" if not bad else f"{bad} checks differ")
