#!/usr/bin/env python3
"""Sweep SEEK (Australia and New Zealand) for recent science roles.

Usage:
    python3 scripts/seek_search.py --site AU [--days 14] [--state VIC] [--json]
    python3 scripts/seek_search.py --site NZ

SEEK's web pages refuse automated fetches, but the JSON search API behind them
answers plain requests and costs no WebSearch calls. For each site this pulls
every recent listing in SEEK's science and research categories, plus keyword
searches across all categories (universities and government agencies often
file science jobs under Education or Government). It keeps listings whose title
matches the role families in profile.md, drops obviously senior or unrelated
ones, and tags universities, government bodies and research institutes, which
hire most entry-level scientists in Australia.
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://www.seek.com.au/api/jobsearch/v5/search"
SITES = {
    "AU": {"siteKey": "AU-Main", "where": "All Australia", "job_url": "https://www.seek.com.au/job/"},
    "NZ": {"siteKey": "NZ-Main", "where": "All New Zealand", "job_url": "https://www.seek.co.nz/job/"},
}

# Whole categories to pull: Science & Technology; Education & Training > Research & Fellowships;
# Healthcare & Medical > Clinical/Medical Research.
CATEGORIES = [{"classification": "1223"},
              {"classification": "6123", "subclassification": "6129"},
              {"classification": "1211", "subclassification": "1353"}]

# Keyword searches across all categories, to catch listings filed elsewhere.
KEYWORDS = ["microbiologist", "microbiology", "fermentation", "bioprocess", "biotechnology",
            "research assistant", "research officer", "technical officer", "laboratory technician",
            "research technician", "scientist", "molecular biology", "graduate scientist",
            "food technologist", "manufacturing associate", "process development"]

INCLUDE = re.compile(
    r"microbio|ferment|bioprocess|biotech|bio-?manufactur|synthetic bio|synbio|molecular|protein|"
    r"enzyme|algae|microalga|cell culture|upstream|downstream|msat|process development|"
    r"research (assistant|officer|associate|technician|scientist)|technical (officer|assistant|specialist)|"
    r"lab(oratory)? (technician|analyst|assistant|scientist|officer)|scientist|scientific officer|"
    r"food technolog|product development technolog|manufacturing associate|graduate|"
    r"qc analyst|quality control|media prep|brew", re.I)
EXCLUDE = re.compile(
    r"\b(senior|sr\.?|lead|principal|head|manager|director|chief|professor|lecturer|postdoc|"
    r"post-doctoral|postdoctoral|fellow|phd scholarship|nurse|data scientist|software|"
    r"registrar|engineer|geolog|geotech|construction|materials testing|soil|asphalt|concrete|"
    r"environmental scientist|ecolog|hydrolog|school|teacher|sales|account|it support|administrator)\b", re.I)

UNIVERSITY = re.compile(r"universit|institute of technology|\btafe\b", re.I)
SCHOOL = re.compile(r"college|grammar|school|education", re.I)
GOVERNMENT = re.compile(
    r"csiro|department|government|council|health service|health network|local health|sa health|"
    r"nsw health|queensland health|health pathology|"
    r"dpird|dpi\b|agriculture victoria|deeca|ansto|dsto|defence|commonwealth|"
    r"science nz|bioeconomy science|phf science|esr|niwa|agresearch|plant & food|scion|"
    r"te whatu ora|ministry|crown|authority|agency", re.I)
INSTITUTE = re.compile(
    r"institute|research centre|research center|walter and eliza|peter maccallum|garvan|"
    r"florey|baker heart|hudson|murdoch children|qimr|telethon|kids research|awri|"
    r"cawthron|malaghan|liggins", re.I)


def fetch(params, retries=4):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except Exception as e:  # network errors and 429s: back off and retry
            if attempt == retries - 1:
                print(f"warning: {url}: {e}", file=sys.stderr)
                return {"data": [], "totalCount": 0}
            time.sleep(2 ** (attempt + 1))


def search(site, days, where, extra, max_pages=10):
    jobs = []
    for page in range(1, max_pages + 1):
        params = {"siteKey": site["siteKey"], "where": where, "daterange": days,
                  "sortmode": "ListedDate", "pageSize": 100, "page": page, **extra}
        data = fetch(params)
        batch = data.get("data") or []
        jobs.extend(batch)
        if len(batch) < 100:
            break
        time.sleep(0.5)
    return jobs


def employer_type(advertiser):
    if UNIVERSITY.search(advertiser):
        return "university"
    if INSTITUTE.search(advertiser):
        return "institute"
    if GOVERNMENT.search(advertiser):
        return "government"
    return ""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site", choices=SITES, required=True)
    parser.add_argument("--days", type=int, default=14, help="listed in the last N days (default 14)")
    parser.add_argument("--state", help="only keep locations containing this text, e.g. VIC, NSW, Canterbury")
    parser.add_argument("--all", action="store_true", help="skip the title filters")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = parser.parse_args()

    site = SITES[args.site]
    found = {}
    queries = [dict(c) for c in CATEGORIES] + [{"keywords": k} for k in KEYWORDS]
    for extra in queries:
        for job in search(site, args.days, site["where"], extra):
            found.setdefault(str(job["id"]), job)
        time.sleep(0.3)

    rows = []
    for jid, job in found.items():
        title = job.get("title", "")
        advertiser = (job.get("advertiser") or {}).get("description", "")
        locations = job.get("locations") or []
        location = locations[0].get("label", "") if locations else job.get("location", "")
        if args.state and args.state.lower() not in location.lower():
            continue
        if not args.all and (not INCLUDE.search(title) or EXCLUDE.search(title)
                             or (SCHOOL.search(advertiser) and not UNIVERSITY.search(advertiser))):
            continue
        rows.append({"id": jid, "listed": (job.get("listingDate") or "")[:10], "title": title,
                     "employer": advertiser, "type": employer_type(advertiser), "location": location,
                     "teaser": (job.get("teaser") or "").strip(), "url": site["job_url"] + jid})
    rows.sort(key=lambda r: (r["type"] == "", r["employer"].lower(), r["title"].lower()))

    if args.json:
        json.dump(rows, sys.stdout, indent=1, ensure_ascii=False)
        print()
        return
    print(f"# SEEK {args.site}: {len(rows)} matching of {len(found)} listings in the last {args.days} days")
    for r in rows:
        print(" | ".join([r["listed"], r["type"] or "-", r["employer"], r["title"], r["location"], r["url"]]))


if __name__ == "__main__":
    main()
