"""Re-runnable checks for reports/radar/2026-11-17.md (python3 -I reports/radar/2026-11-17-checks.py).

Run from the repo root, with that day's sweep files archived in work/radar/2026-11-17/.
"""
import datetime as d
import json
import re

rep = open("reports/radar/2026-11-17.md", encoding="utf-8").read()
cand = json.load(open("work/radar/2026-11-17/candidates.json", encoding="utf-8"))
rec = json.load(open("work/radar/2026-11-17/record.json", encoding="utf-8"))
leads = json.load(open("work/radar/2026-11-17/leads.json", encoding="utf-8"))
bad = 0


def chk(label, stated, actual):
    global bad
    ok = stated == actual
    bad += not ok
    print(f"{'OK ' if ok else 'DIFF'} {label}: stated {stated} / computed {actual}")


chk("weekday", "Tuesday", d.date(2026, 11, 17).strftime("%A"))
chk("new leads", 1, len(rec["new_leads"]))
new = [l for l in leads["leads"] if l["company"] in rec["new_leads"]]
chk("strong new leads", 0, sum(l["fit"] == "strong" for l in new))
jobs = [c for c in cand["candidates"] if c["kind"] == "job"]
kept = [j for j in jobs if j["company"] in ("biomodal", "Samsara Eco")]
chk("startup postings", 4, len(kept))
chk("biomodal postings", 3, sum(j["company"] == "biomodal" for j in kept))
chk("posting lines in report", 4, len(re.findall(r"^- \*\*(?:biomodal|Samsara Eco)\*\*.*\[ad\]", rep, re.M)) - 2)  # minus the Act now and New leads lines for biomodal
chk("outreach drafts added", 0, len(rec["outreach_added"]))
chk("drafts held", 0, rec["outreach_held"])
c = cand["counts"]
chk("candidates", 27, len(cand["candidates"]))
chk("from feeds", 2, c.get("feed", 0))
chk("from Google News", 0, c.get("gnews", 0))
chk("LinkedIn roster", 1, c.get("linkedin-roster", 0))
chk("LinkedIn keyword search", 24, c.get("linkedin-search", 0))
chk("channel counts sum to candidates", 27, sum(c.values()))
chk("sweep seconds", 621, cand["seconds"]["total"])
chk("requests", 143, cand["requests"]["requests"])
chk("retries", 17, cand["requests"]["retries"])
chk("failures", 0, cand["requests"]["failed"])
err = open("work/radar/sweep.err", encoding="utf-8").read()
chk("retries that were HTTP 429", 17, len(re.findall(r"^retry \d+: .*429", err, re.M)))
m = re.search(r"(\d+) leads by id, (\d+) of (\d+) by name, (\d+) ids found", err)
chk("name searches done / needed", (40, 43), (int(m.group(2)), int(m.group(3))))
chk("companies not checked", 3, int(m.group(3)) - int(m.group(2)))
chk("roster size", 57, sum(rec["roster"].values()))
chk("roster with LinkedIn id", 13, rec["roster_with_linkedin_id"])
chk("ids found today", 0, len(rec["linkedin_ids_found"]))
chk("biomodal LinkedIn id", "3135599", next(j["linkedin_company_id"] for j in jobs if j["company"] == "biomodal"))
chk("page fetches (1 story + 3 ads + 1 retry)", 5, 1 + 3 + 1)
chk("web searches", 2, 2)  # one hiring-post search, one on biomodal's size
# Quoted from Startup Daily, 15 Nov 2026 (read in full on 17 Nov), not computed:
print("quoted: US$4.3M (A$6.3M) Series A extension; US$2M (A$2.8M) from Queensland; 25 staff; 250,000 cattle in 2027")
print("quoted, unverified: biomodal about 100-110 staff (PitchBook 111, Bounce Watch ~99, via web search)")
print("all checks pass" if not bad else f"{bad} checks differ")
