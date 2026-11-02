#!/usr/bin/env python3
"""Sweep UK job boards for recent science roles, like seek_search.py does for Australia and NZ.

Usage:
    python3 scripts/uk_search.py [--days 14] [--json] [--all] > work/uk-jobs.txt

Three sources answer plain requests and cost no WebSearch calls:
- Reed (reed.co.uk): the search pages carry their results as JSON.
- NHS Jobs (jobs.nhs.uk): NHS labs, the biggest UK employer of entry-level microbiologists.
- The LinkedIn guest feed, location United Kingdom.
Keyword searches cover the role families in profile.md, including QC microbiology and
graduate schemes. Titles are filtered with the same INCLUDE / EXCLUDE rules as seek_search.py,
plus a few UK-specific terms (trainee patent attorney, scientist training programme).
"""

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seek_search import EXCLUDE, INCLUDE  # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

KEYWORDS = ["microbiologist", "microbiology", "qc microbiologist", "microbiology analyst",
            "laboratory analyst", "laboratory technician", "fermentation", "bioprocess",
            "upstream process", "research assistant", "research technician", "graduate scientist",
            "associate scientist", "food technologist", "biotechnology", "molecular biology",
            "trainee patent attorney", "graduate scheme science", "september 2027"]
NHS_KEYWORDS = ["microbiology", "laboratory assistant", "trainee clinical scientist",
                "healthcare science", "biomedical support"]
LINKEDIN_KEYWORDS = ["microbiologist", "QC microbiology", "fermentation scientist", "bioprocess scientist",
                     "research assistant biology", "graduate scientist", "trainee patent attorney",
                     "graduate scheme 2027 science", "laboratory technician microbiology"]

# UK-specific titles the shared INCLUDE rule doesn't catch.
INCLUDE_UK = re.compile(r"trainee patent|patent (scientist|assistant)|scientist training programme|"
                        r"trainee clinical scientist|healthcare science", re.I)
# Graduate titles from fields I'm not targeting, and registered roles I can't take (HCPC biomedical scientist).
EXCLUDE_UK = re.compile(r"actuar|surveying|solicitor|teaching|psycholog|investment|risk analyst|ecolog|"
                        r"geolog|environment|climate|air quality|biomedical scientist(?!.*trainee)|band [5-9]", re.I)
RECENT = {7: "lastweek", 14: "lasttwoweeks"}


def get(url, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-GB"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception as e:  # network errors and 429s: back off and retry
            if attempt == retries - 1:
                print(f"warning: {url}: {e}", file=sys.stderr)
                return ""
            time.sleep(5 * (attempt + 1))


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def reed(keyword, days, pages=2):
    slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")
    for page in range(1, pages + 1):
        url = (f"https://www.reed.co.uk/jobs/{slug}-jobs?dateCreatedOffSet={RECENT.get(days, 'lasttwoweeks')}"
               + (f"&pageno={page}" if page > 1 else ""))
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', get(url), re.S)
        if not m:
            return
        jobs = json.loads(m.group(1)).get("props", {}).get("pageProps", {}).get("searchResults", {}).get("jobs") or []
        for j in jobs:
            d = j.get("jobDetail") or {}
            yield {"source": "reed", "listed": (d.get("dateCreated") or "")[:10], "title": d.get("jobTitle", ""),
                   "employer": d.get("ouName", ""),
                   "location": ", ".join(x for x in (d.get("displayLocationName"), d.get("countyLocation")) if x),
                   "url": "https://www.reed.co.uk" + j.get("url", "")}
        if len(jobs) < 15:
            return
        time.sleep(1)


def nhs(keyword, pages=2):
    for page in range(1, pages + 1):
        url = ("https://www.jobs.nhs.uk/candidate/search/results?"
               + urllib.parse.urlencode({"keyword": keyword, "language": "en", "sort": "publicationDateDesc",
                                         "page": page}))
        blocks = get(url).split('data-test="search-result"')[1:]
        for b in blocks:
            link = re.search(r'href="(/candidate/jobadvert/[^"?]+)[^"]*"[^>]*data-test="search-result-job-title"[^>]*>(.*?)</a>', b, re.S)
            where = re.search(r'data-test="search-result-location".*?<h3[^>]*>(.*?)<div[^>]*>(.*?)</div>', b, re.S)
            posted = re.search(r"Date posted:\s*<strong[^>]*>(.*?)</strong>", b, re.S)
            if link:
                yield {"source": "nhs", "listed": clean(posted.group(1)) if posted else "", "title": clean(link.group(2)),
                       "employer": clean(where.group(1)) if where else "", "location": clean(where.group(2)) if where else "",
                       "url": "https://www.jobs.nhs.uk" + link.group(1)}
        if len(blocks) < 10:
            return
        time.sleep(1)


def linkedin(keyword, days, pages=3):
    for page in range(pages):
        url = ("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
               + urllib.parse.urlencode({"keywords": keyword, "location": "United Kingdom",
                                         "f_TPR": f"r{days * 86400}", "start": page * 10}))
        cards = get(url).split("<li>")[1:]
        for c in cards:
            href = re.search(r'class="base-card__full-link[^"]*"\s+href="([^"?]+)', c)
            title = re.search(r'base-search-card__title">(.*?)</h3>', c, re.S)
            company = re.search(r'base-search-card__subtitle">(.*?)</h4>', c, re.S)
            loc = re.search(r'job-search-card__location">(.*?)</span>', c, re.S)
            when = re.search(r'datetime="([\d-]+)"', c)
            if href and title:
                yield {"source": "linkedin", "listed": when.group(1) if when else "", "title": clean(title.group(1)),
                       "employer": clean(company.group(1)) if company else "", "location": clean(loc.group(1)) if loc else "",
                       "url": href.group(1)}
        if len(cards) < 10:
            return
        time.sleep(3)  # the guest feed rate-limits bursts


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, choices=(7, 14), default=14, help="listed in the last N days")
    parser.add_argument("--all", action="store_true", help="skip the title filters")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = parser.parse_args()

    found = {}
    for k in KEYWORDS:
        for job in reed(k, args.days):
            found.setdefault(job["url"], job)
    for k in NHS_KEYWORDS:
        for job in nhs(k):
            found.setdefault(job["url"], job)
    for k in LINKEDIN_KEYWORDS:
        for job in linkedin(k, args.days):
            found.setdefault(job["url"], job)

    rows = [r for r in found.values()
            if args.all or ((INCLUDE.search(r["title"]) or INCLUDE_UK.search(r["title"]))
                            and not EXCLUDE.search(r["title"]) and not EXCLUDE_UK.search(r["title"]))]
    rows.sort(key=lambda r: (r["employer"].lower(), r["title"].lower()))
    if args.json:
        json.dump(rows, sys.stdout, indent=1, ensure_ascii=False)
        print()
        return
    print(f"# UK: {len(rows)} matching of {len(found)} listings (Reed and LinkedIn: last {args.days} days; NHS Jobs: newest)")
    for r in rows:
        print(" | ".join([r["listed"], r["source"], r["employer"], r["title"], r["location"], r["url"]]))


if __name__ == "__main__":
    main()
