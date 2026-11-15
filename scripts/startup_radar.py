#!/usr/bin/env python3
"""Daily startup radar: find small companies that will hire before they advertise on job boards.

Usage:
    python3 scripts/startup_radar.py sweep [--days 3]               # discovery -> work/radar/candidates.json
    python3 scripts/startup_radar.py record --date DATE work/radar/leads.json [--hold-outreach]
    python3 scripts/startup_radar.py set "<company>" STATUS [--note "..."]
    python3 scripts/startup_radar.py history "<company>"             # what the trackers already hold
    python3 scripts/startup_radar.py roster                          # print the lead roster

The weekly scans read careers pages and job boards. This one looks for the signals that come
first, so a speculative approach can land before a job is advertised:

- Funding news: Google News searches (startup raises, seed and Series A rounds, spinouts,
  grants) for New Zealand, Australia, the UK and Ireland, plus the RSS feeds of the trade and
  startup outlets that report these rounds (AgFunderNews, Green Queen, SmartCompany, Startup
  Daily, Silicon Republic, EU-Startups and others).
- LinkedIn-only hiring: the LinkedIn guest job feed for every lead in tracker/leads.csv with a
  LinkedIn company id (several ids per request), and a short keyword sweep of the last few days
  in the four countries to catch small employers that post only on LinkedIn.

Nothing here needs a login or uses WebSearch. Every candidate is scored by simple keyword rules
(sector, signal, geography); Claude then judges them (see STARTUP_RADAR.md) and writes
work/radar/leads.json, which `record` merges into tracker/leads.csv. `record` also marks every
swept candidate as seen in tracker/radar_seen.csv, so nothing is shown twice, and adds the
day's outreach drafts to tracker/outreach.csv (the job board's Outreach tab).
"""

import argparse
import html
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from network import OUTREACH_FIELDS, people_search  # noqa: E402
from seek_search import EXCLUDE, INCLUDE  # noqa: E402
from update_tracker import norm_url, read_csv, slug, text, write_csv  # noqa: E402

ROLE_FIELDS = ["id", "company", "role", "location", "url", "fit", "status", "first_seen", "last_seen", "closes",
               "starts", "notes"]

ROOT = Path(__file__).resolve().parent.parent
TRACKER = ROOT / "tracker"
WORK = ROOT / "work" / "radar"
STATS = {"requests": 0, "retries": 0, "failed": 0}
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

LEAD_FIELDS = ["id", "company", "country", "city", "sector", "what", "signal", "trigger", "trigger_date",
               "trigger_url", "hiring_odds", "fit", "linkedin_id", "linkedin_url", "website", "careers_url",
               "move", "status", "first_seen", "last_seen", "li_checked", "last_jobs", "notes"]
LEAD_STATUSES = ("new", "watching", "contacted", "applied", "ignore")
SEEN_FIELDS = ["key", "kind", "first_seen", "title"]
SEEN_KEEP_DAYS = 120

# --- Discovery sources ---------------------------------------------------------------------------

# (Google News edition, query). Short queries: long OR-chains make Google ignore `when:`.
GNEWS = [
    ("NZ", '"New Zealand" startup raises'), ("NZ", '"New Zealand" biotech'),
    ("NZ", 'Kiwi startup "seed round" OR "Series A"'), ("NZ", 'Christchurch OR Canterbury startup funding'),
    ("NZ", '"New Zealand" agritech OR foodtech raises'), ("NZ", '"New Zealand" fermentation OR microbial'),
    ("AU", 'Australian biotech raises'), ("AU", 'Australian startup "seed round"'),
    ("AU", 'Australian agtech OR foodtech raises'), ("AU", 'Australia "precision fermentation" OR biomanufacturing'),
    ("AU", 'CSIRO spinout OR "university spinout" Australia'),
    ("GB", 'UK biotech startup raises'), ("GB", 'spinout raises seed'),
    ("GB", 'UK "synthetic biology" OR biomanufacturing startup'), ("GB", 'UK foodtech OR "alt protein" raises'),
    ("GB", 'Scotland OR Wales biotech startup funding'), ("GB", '"Innovate UK" grant startup'),
    ("IE", 'Irish startup raises'), ("IE", 'Irish biotech OR agritech funding'), ("IE", 'Enterprise Ireland spin-out'),
    ("GB", '"precision fermentation"'), ("GB", 'microalgae OR phycocyanin OR seaweed startup'),
    ("GB", 'fermentation startup raises'), ("GB", 'enzyme OR "strain engineering" startup raises'),
]
FEEDS = [
    "https://agfundernews.com/feed", "https://www.greenqueen.com.hk/feed/", "https://www.labiotech.eu/feed/",
    "https://www.smartcompany.com.au/startupsmart/feed/", "https://www.startupdaily.net/feed/",
    "https://www.siliconrepublic.com/feed", "https://www.eu-startups.com/feed/", "https://vegconomist.com/feed/",
    "https://www.foodnavigator.com/Info/FoodNavigator-RSS", "https://www.nzentrepreneur.co.nz/feed/",
    "https://www.rnz.co.nz/rss/business.xml", "https://sifted.eu/feed",
]
LINKEDIN_PLACES = ["New Zealand", "Australia", "United Kingdom", "Ireland"]
COUNTRY_PLACE = {"nz": "New Zealand", "new zealand": "New Zealand", "au": "Australia", "australia": "Australia",
                 "uk": "United Kingdom", "united kingdom": "United Kingdom", "gb": "United Kingdom",
                 "ie": "Ireland", "ireland": "Ireland"}
LINKEDIN_KEYWORDS = ["fermentation", "bioprocess", "microbiologist", "synthetic biology", "biotech startup",
                     "research associate", "laboratory technician"]

# --- Keyword rules -------------------------------------------------------------------------------

CORE = re.compile(r"ferment|synthetic bio|synbio|microb|micro-?alga|algae|algal|phycocyanin|spirulina|galdieria|"
                  r"seaweed|enzyme|bioprocess|bio-?manufactur|strain engineer|metabolic engineer|yeast|fungal|"
                  r"mycoprotein|mycelium|probiotic|microbiome|biofoundry|bioreactor|cultivated meat|"
                  r"precision[- ]ferment|biotherapeutic|biologics|biomaterial|bio-?based|biochemical", re.I)
ADJACENT = re.compile(r"biotech|bioscience|life science|food ?tech|agri-?tech|agtech|alt(ernative)? protein|"
                      r"plant[- ]based|dairy|protein|nutrition|ingredient|biolog|vaccine|diagnostic|genomic|"
                      r"molecular|lab\b|laborator|scien|spin-?out|spin-?off|biosecurity|methane|animal health", re.I)
SIGNAL_FUNDING = re.compile(r"raise[sd]?\b|raising|seed\b|pre-seed|series [a-c]\b|funding|investment|invests?\b|"
                            r"backed|backs\b|closes? .{0,20}round|secures?|lands? \$|bags?|nabs?|grant|capital|"
                            r"crowdfund|\$\d|£\d|€\d|\d ?(m|mn|million)\b", re.I)
SIGNAL_GROWTH = re.compile(r"launch|opens?\b|new (facility|site|lab|plant|hq|headquarters)|pilot plant|scale[- ]up|"
                           r"expan|spin-?out|spin-?off|acquir|partnership|offtake|approval|accelerator|cohort|"
                           r"hiring|recruit|jobs\b|team grows|new hires", re.I)
ROUNDUP = re.compile(r"startups? (that )?raised|funding round-?up|round-?up|deals of the week|weekly funding|"
                     r"funding tracker|signals:|this week in", re.I)
NOISE = re.compile(r"\bAI\b|artificial intelligence|crypto|blockchain|fintech|saas|software|cyber|defen[cs]e|"
                   r"robot|quantum|data cent|mining|lithium|real estate|property|gaming|bank|insurance|"
                   r"payments?|marketing|ad-?tech|esports|fashion|share price|stock|asx:|nasdaq|ipo\b|"
                   r"price target|guidance|vogue|toxic algae|algae bloom|algal bloom|red alert", re.I)
TARGET_GEO = re.compile(r"new zealand|\bnz\b|kiwi|auckland|wellington|christchurch|canterbury|otago|dunedin|"
                        r"hamilton|waikato|palmerston north|nelson|rotorua|tauranga|lincoln|rolleston|"
                        r"australia|aussie|sydney|melbourne|brisbane|adelaide|perth|canberra|hobart|queensland|"
                        r"victoria|new south wales|csiro|\banz\b|"
                        r"\buk\b|united kingdom|britain|british|england|scotland|scottish|wales|welsh|"
                        r"northern ireland|london|cambridge|oxford|manchester|edinburgh|glasgow|bristol|leeds|"
                        r"sheffield|nottingham|norwich|dundee|aberdeen|cardiff|belfast|teesside|"
                        r"ireland|irish|dublin|cork|galway|limerick|waterford|enterprise ireland", re.I)
LOCAL = re.compile(r"christchurch|canterbury|lincoln|rolleston|ōtautahi|otautahi", re.I)
OTHER_GEO = re.compile(r"\b(us|u\.s\.|usa|american|california|boston|san francisco|new york|texas|canada|"
                       r"canadian|german|germany|french|france|dutch|netherlands|danish|denmark|swedish|sweden|"
                       r"finnish|finland|swiss|switzerland|spain|spanish|italian|italy|israel|israeli|india|"
                       r"indian|china|chinese|japan|japanese|korea|korean|singapore|mena|uae|saudi|abu dhabi|"
                       r"dubai|brazil|latin america|africa|african|nairobi|nigeria|kenya|lithuania|vilnius|estonia|poland|"
                       r"czech|belgian|belgium|austria|norway|portugal)\b", re.I)
BIG_EMPLOYER = re.compile(r"fonterra|thermo fisher|danone|nestl|cargill|eurofins|idexx|novonesis|lonza|pfizer|"
                          r"astrazeneca|gsk|glaxo|roche|novartis|sanofi|merck|msd\b|csl\b|moderna|abbott|"
                          r"johnson|j&j|amgen|takeda|biogen|genscript|kerry|unilever|mondelez|diageo|heineken|"
                          r"woolworths|coles|tesco|sainsbury|accenture|deloitte|kpmg|pwc|\bey\b|iqvia|icon plc|"
                          r"parexel|fortrea|syneos|labcorp|sgs\b|intertek|bureau veritas|als\b|asurequality|"
                          r"zoetis|elanco|boehringer|bayer|basf|dsm|iff\b|givaudan|ecolab|sealed air|"
                          r"alliance group|silver fern|binance|alignerr|teradyne|rocket lab|wsp\b|beca\b|arup|"
                          r"jacobs|aecom|stantec|cai\b|psc biotech|qscan|telix|sita\b", re.I)
PUBLIC_SECTOR = re.compile(r"universit|council|ministry|department|government|health new zealand|te whatu ora|"
                           r"health pathology|health service|\bnsw health|queensland health|sa pathology|"
                           r"pathology queensland|\bnhs\b|\bhse\b|\bhsc\b|science new zealand|crown|museum|hospital|school|college|"
                           r"institute of technology|polytechnic|tafe|csiro", re.I)
RECRUITER = re.compile(r"recruit|talent|staffing|personnel|\bsearch\b|hays\b|randstad|adecco|robert walters|"
                       r"michael page|hudson|\bpeople\b|resourcing|\bcareers\b|\bjobs\b|tiptopjob", re.I)
NON_SCIENCE_TITLE = re.compile(r"sales|account|marketing|finance|financial|accountant|hr\b|human resources|"
                               r"people|recruit|legal|counsel|software|developer|devops|data engineer|designer|"
                               r"chef|barista|driver|warehouse|customer|office manager|executive assistant|"
                               r"payroll|procurement|buyer", re.I)


def get(url, retries=2, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"})
    for attempt in range(retries + 1):
        STATS["requests"] += 1
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception as e:
            code = getattr(e, "code", None)
            if code in (403, 404, 410) or attempt == retries:
                print(f"warning: {url[:120]}: {e}", file=sys.stderr)
                STATS["failed"] += 1
                return ""
            STATS["retries"] += 1
            print(f"retry {attempt + 1}: {url[:100]}: {e}", file=sys.stderr)
            time.sleep(4 * (attempt + 1))


def clean(value):
    value = re.sub(r"<!\[CDATA\[|\]\]>", "", value or "")
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(value)))).strip()


def norm_title(title):
    title = re.sub(r"\s+-\s+[^-]{2,60}$", "", title or "")  # drop " - Publisher" from Google News titles
    return re.sub(r"[^a-z0-9]+", " ", title.lower())[:90].strip()


def parse_when(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def rss_items(xml):
    for block in re.findall(r"<item[ >](.*?)</item>", xml, re.S) or re.findall(r"<entry[ >](.*?)</entry>", xml, re.S):
        def tag(name):
            m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", block, re.S)
            return m.group(1) if m else ""
        link = clean(tag("link")) or (re.search(r'<link[^>]*href="([^"]+)"', block) or [None, ""])[1]
        source = re.search(r'<source[^>]*url="([^"]+)"[^>]*>(.*?)</source>', block, re.S)
        yield {"title": clean(tag("title")), "url": link.strip(),
               "published": tag("pubDate") or tag("published") or tag("updated") or tag("dc:date"),
               "snippet": clean(tag("description") or tag("summary"))[:400],
               "source": clean(source.group(2)) if source else "",
               "source_url": source.group(1) if source else ""}


# --- Channels ------------------------------------------------------------------------------------

def gnews(cutoff, warnings):
    for edition, query in GNEWS:
        url = ("https://news.google.com/rss/search?" + urllib.parse.urlencode(
            {"q": f"{query} when:{max(1, (datetime.now(timezone.utc) - cutoff).days + 1)}d",
             "hl": f"en-{edition}", "gl": edition, "ceid": f"{edition}:en"}))
        xml = get(url)
        if not xml:
            warnings.append(f"google news failed: {query}")
        for item in rss_items(xml):
            item.update(channel="gnews", query=query)
            yield item
        time.sleep(1)


def feeds(warnings):
    for url in FEEDS:
        xml = get(url)
        items = list(rss_items(xml))
        if not items:
            warnings.append(f"feed empty or failed: {url}")
        host = urllib.parse.urlparse(url).netloc.replace("www.", "")
        for item in items:
            item.update(channel="feed", source=item["source"] or host, source_url=item["source_url"] or url)
            yield item


def linkedin_cards(params, pages=1):
    for page in range(pages):
        query = dict(params, start=page * 10)
        xml = get("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
                  + urllib.parse.urlencode(query))
        cards = xml.split("<li>")[1:]
        for c in cards:
            href = re.search(r'class="base-card__full-link[^"]*"\s+href="([^"?]+)', c)
            title = re.search(r'base-search-card__title">(.*?)</h3>', c, re.S)
            company = re.search(r'base-search-card__subtitle">(.*?)</h4>', c, re.S)
            company_url = re.search(r'href="(https://[a-z]+\.linkedin\.com/company/[^"?]+)', c)
            loc = re.search(r'job-search-card__location">(.*?)</span>', c, re.S)
            when = re.search(r'datetime="([\d-]+)"', c)
            job_id = re.search(r"jobPosting:(\d+)", c)
            if href and title:
                yield {"title": clean(title.group(1)), "company": clean(company.group(1)) if company else "",
                       "company_url": company_url.group(1) if company_url else "",
                       "location": clean(loc.group(1)) if loc else "", "published": when.group(1) if when else "",
                       "url": href.group(1), "job_id": job_id.group(1) if job_id else ""}
        if len(cards) < 10:
            return
        time.sleep(3)


def company_id_from_job(job_id):
    """The guest job page carries the employer's numeric id in its sign-in link."""
    page = get(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}", retries=1)
    m = re.search(r"facetCurrentCompany%3D(\d+)", page)
    return m.group(1) if m else ""


def name_key(name):
    name = re.sub(r"\(.*?\)", " ", (name or "").lower())
    name = re.sub(r"\b(ltd|limited|inc|llc|plc|pty|group|holdings|nz|uk|australia|ireland)\b", " ", name)
    return re.sub(r"[^a-z0-9]+", "", name)


def same_company(lead_name, card_name):
    a, b = name_key(lead_name), name_key(card_name)
    return len(a) >= 4 and len(b) >= 4 and (a == b or a in b or b in a)


def linkedin_roster(leads, ctx):
    """Postings by the companies in tracker/leads.csv, whatever the job title.

    Leads with a LinkedIn id are read eight ids per request. Leads without one are searched by
    name in their country (the guest feed's keyword search is fuzzy, so only cards whose employer
    matches the lead's name count); a match also gives the id, which `record` saves, so each
    lead moves to the precise id check once it has posted anything. No time filter: postings
    already seen are skipped through tracker/radar_seen.csv.
    """
    watched = [r for r in leads if r["status"] != "ignore"]
    with_id = {r["linkedin_id"]: r for r in watched if r["linkedin_id"]}
    ids = list(with_id)
    for i in range(0, len(ids), 8):
        chunk = [with_id[x] for x in ids[i:i + 8]]
        for card in linkedin_cards({"f_C": ",".join(r["linkedin_id"] for r in chunk), "location": "Worldwide"},
                                   pages=2):
            lead = next((r for r in chunk if same_company(r["company"], card["company"])), None)
            card.update(channel="linkedin-roster", lead=lead["company"] if lead else "")
            yield card
        ctx["roster_checked"] += [r["id"] for r in chunk]
        time.sleep(3)
    no_id = sorted((r for r in watched if not r["linkedin_id"]), key=lambda r: r["li_checked"])
    for r in no_id[:ctx["name_searches"]]:
        place = COUNTRY_PLACE.get(r["country"].strip().lower(), "Worldwide")
        matched = [c for c in linkedin_cards({"keywords": r["company"], "location": place})
                   if same_company(r["company"], c["company"])]
        ctx["roster_checked"].append(r["id"])
        if matched and matched[0]["job_id"]:
            cid = company_id_from_job(matched[0]["job_id"])
            if cid:
                ctx["resolved_ids"][r["id"]] = cid
        for card in matched:
            card.update(channel="linkedin-roster", lead=r["company"])
            yield card
        time.sleep(2.5)
    print(f"linkedin roster: {len(ids)} leads by id, {min(len(no_id), ctx['name_searches'])} of {len(no_id)} "
          f"by name, {len(ctx['resolved_ids'])} ids found", file=sys.stderr)


def linkedin_keywords(days, warnings):
    for place in LINKEDIN_PLACES:
        for kw in LINKEDIN_KEYWORDS:
            for card in linkedin_cards({"keywords": kw, "location": place, "f_TPR": f"r{days * 86400}"}):
                card.update(channel="linkedin-search", query=f"{kw} @ {place}")
                yield card
            time.sleep(2.5)


# --- Scoring -------------------------------------------------------------------------------------

def score_news(item):
    blob = f"{item['title']} {item['snippet']}"
    title = item["title"]
    core, adj = bool(CORE.search(blob)), bool(ADJACENT.search(blob))
    roundup = bool(ROUNDUP.search(title))
    geo, other = bool(TARGET_GEO.search(blob)), bool(OTHER_GEO.search(title))
    s = 0
    s += 3 if core else (1 if adj else 0)
    s += 3 if SIGNAL_FUNDING.search(title) else (1 if SIGNAL_FUNDING.search(blob) else 0)
    s += 2 if SIGNAL_GROWTH.search(blob) else 0
    s += 2 if geo else 0
    s += 2 if LOCAL.search(blob) else 0
    s += 3 if roundup else 0
    if NOISE.search(title) and not core:
        s -= 4
    if other and not TARGET_GEO.search(title):
        s -= 3
    tags = [t for t, ok in (("core", core), ("adjacent", adj and not core), ("roundup", roundup),
                            ("target-geo", geo), ("local", bool(LOCAL.search(blob))),
                            ("other-geo", other and not geo)) if ok]
    keep = (roundup and not (other and not geo) and not NOISE.search(title)) or ((core or adj) and s >= 5)
    return s, tags, keep


def score_job(item, watch_names):
    title, company = item["title"], item["company"]
    tags = []
    s = 0
    science = bool(INCLUDE.search(title)) or bool(CORE.search(title))
    if science:
        s += 3
    if EXCLUDE.search(title):
        s -= 2
        tags.append("senior-or-off-family")
    if NON_SCIENCE_TITLE.search(title):
        s -= 4
        tags.append("non-science")
    if item["channel"] == "linkedin-roster":
        s += 4
        tags.append("roster")
    if BIG_EMPLOYER.search(company):
        s -= 4
        tags.append("big-employer")
    if PUBLIC_SECTOR.search(company):
        s -= 3
        tags.append("public-sector")
    if RECRUITER.search(company):
        tags.append("recruiter")
    if LOCAL.search(item["location"]):
        s += 2
        tags.append("local")
    if company.lower() in watch_names:
        tags.append("on-watchlist")
    keep = item["channel"] == "linkedin-roster" or (science and s >= 3 and "non-science" not in tags)
    return s, tags, keep


def watchlist_names():
    path = ROOT / "watchlist.md"
    if not path.exists():
        return set()
    return {m.group(1).strip().lower() for m in re.finditer(r"^\|\s*([^|]+?)\s*\|", path.read_text(encoding="utf-8"), re.M)}


# --- Commands ------------------------------------------------------------------------------------

def sweep(args):
    WORK.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    seen = {r["key"] for r in read_csv(TRACKER / "radar_seen.csv", SEEN_FIELDS)}
    leads = read_csv(TRACKER / "leads.csv", LEAD_FIELDS)
    watch = watchlist_names()
    tracked = {norm_url(r["url"]): r["status"] for r in read_csv(TRACKER / "roles.csv", ROLE_FIELDS)}
    warnings = []
    candidates, run_keys = [], set()
    counts = {}

    def add(item, kind, keys, score, tags):
        if any(k in seen or k in run_keys for k in keys):
            return
        run_keys.update(keys)
        item.update(kind=kind, keys=sorted(keys), score=score, tags=tags)
        candidates.append(item)
        counts[item["channel"]] = counts.get(item["channel"], 0) + 1

    started = time.time()
    # Feeds first: their links go straight to the publisher, so they win over Google News copies.
    news = [] if args.no_news else list(feeds(warnings)) + list(gnews(cutoff, warnings))
    timing = {"news": round(time.time() - started)}
    for item in news:
        when = parse_when(item["published"])
        if when and when < cutoff:
            continue
        item["published"] = when.date().isoformat() if when else ""
        score, tags, keep = score_news(item)
        if keep:
            add(item, "news", {"news:" + norm_url(item["url"]), "title:" + norm_title(item["title"])}, score, tags)

    ctx = {"name_searches": args.name_searches, "roster_checked": [], "resolved_ids": {}}
    jobs = list(linkedin_roster(leads, ctx)) if not args.no_linkedin else []
    if not args.no_linkedin:
        jobs += list(linkedin_keywords(args.days, warnings))
    lead_by_li = {r["linkedin_id"]: r["company"] for r in leads if r["linkedin_id"]}
    timing["linkedin"] = round(time.time() - started) - timing["news"]
    lookups = 0
    for item in jobs:
        score, tags, keep = score_job(item, watch)
        if not keep:
            continue
        key = "job:" + (item["job_id"] or norm_url(item["url"]))
        if key in seen or key in run_keys:
            continue
        status = tracked.get(norm_url(item["url"]))
        if status in ("ineligible", "off-path", "ignore"):  # I've already turned it down
            continue
        if status:  # the weekly scans already report it
            tags.append(f"in-roles-tracker:{status}")
        if (item["channel"] == "linkedin-search" and item["job_id"] and lookups < args.id_lookups
                and not ({"big-employer", "public-sector"} & set(tags))):
            item["linkedin_company_id"] = company_id_from_job(item["job_id"])
            lookups += 1
            time.sleep(1.5)
            if item["linkedin_company_id"] in lead_by_li:
                tags.append("roster")
                item["lead"] = lead_by_li[item["linkedin_company_id"]]
        add(item, "job", {key}, score, tags)

    timing["total"] = round(time.time() - started)
    if not news and not args.no_news:
        warnings.append("no news items at all: every news source failed (network down?)")
    if not args.no_linkedin and not jobs:
        warnings.append("no LinkedIn cards at all: the guest feed may be rate-limiting (HTTP 429) or changed")
    candidates.sort(key=lambda c: (-c["score"], c["kind"], c.get("published") or ""))
    if STATS["retries"] > 10:
        warnings.append(f"{STATS['retries']} retries (LinkedIn rate-limiting?); some channels may be thin")
    out = {"swept": date.today().isoformat(), "days": args.days, "warnings": warnings, "counts": counts,
           "seconds": timing, "requests": STATS, "roster_checked": ctx.get("roster_checked", []) if not
           args.no_linkedin else [], "resolved_ids": ctx.get("resolved_ids", {}) if not args.no_linkedin else {},
           "candidates": candidates}
    (WORK / "candidates.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"# Startup radar sweep {out['swept']} (last {args.days} days): {len(candidates)} new candidates · "
          + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
          + f" · {timing['total']}s, {STATS['requests']} requests, {STATS['retries']} retries, {STATS['failed']} failed")
    for w in warnings:
        print(f"! {w}")
    for i, c in enumerate(candidates):
        if c["kind"] == "news":
            print(f"{i:3d} news {c['score']:2d} [{','.join(c['tags'])}] {c['published']} | {c['title'][:150]}"
                  f" | {c.get('source', '')}")
        else:
            lead = f" (lead: {c['lead']})" if c.get("lead") else ""
            print(f"{i:3d} job  {c['score']:2d} [{','.join(c['tags'])}] {c['published']} | {c['company']}{lead} | "
                  f"{c['title'][:90]} | {c['location']}")


def merge_lead(row, item, today):
    for field in ("country", "city", "sector", "what", "linkedin_id", "linkedin_url", "website", "careers_url"):
        if text(item.get(field)):
            row[field] = text(item[field])
    new_trigger = text(item.get("trigger"))
    if new_trigger and new_trigger != row["trigger"]:
        if row["trigger"]:
            row["notes"] = f"{row['trigger_date'] or row['last_seen']}: {row['trigger']}" + (
                f" · {row['notes']}" if row["notes"] else "")
        for field in ("signal", "trigger", "trigger_date", "trigger_url"):
            row[field] = text(item.get(field))
    for field in ("hiring_odds", "fit", "move"):
        if text(item.get(field)):
            row[field] = text(item[field])
    if text(item.get("jobs")):
        row["last_jobs"] = f"{today}: {text(item['jobs'])}"
    if text(item.get("notes")):
        extra = text(item["notes"])
        if extra not in row["notes"]:
            row["notes"] = (extra + " · " + row["notes"]).strip(" ·")[:1500]
    row["last_seen"] = today


def scan_running():
    """True while a Monday or Thursday scan is working in this folder.

    Those scans keep the Mac awake with exactly this caffeinate command, which outlives the scan
    by hours, so a scan that has already committed today counts as finished.
    """
    try:
        awake = subprocess.run(["pgrep", "-f", "caffeinate -ims -t 28800"], capture_output=True, text=True)
        if not awake.stdout.strip():
            return False
        done = subprocess.run(["git", "-C", str(ROOT), "log", "--since=midnight", "--format=%s"],
                              capture_output=True, text=True)
        return not re.search(r"^(Weekly job scan|Career routes scan) ", done.stdout, re.M)
    except OSError:
        return False


def add_outreach(items, today):
    rows = read_csv(TRACKER / "outreach.csv", OUTREACH_FIELDS)
    ids = {r["id"] for r in rows}
    recent = {r["company"].lower() for r in rows
              if r["status"] in ("suggested", "sent", "replied", "meeting") and r["created"] >= (
                  date.fromisoformat(today) - timedelta(days=42)).isoformat()}
    added = []
    for item in items:
        company, trigger = text(item.get("company")), text(item.get("trigger"))
        if not company or not text(item.get("draft")) or company.lower() in recent:
            continue
        oid = slug(company, trigger)[:80].rstrip("-")
        if oid in ids:
            continue
        row = dict.fromkeys(OUTREACH_FIELDS, "")
        row.update({k: text(item.get(k)) for k in OUTREACH_FIELDS if k in item})
        row.update(id=oid, created=today, status="suggested", updated=today,
                   notes=("Startup radar. " + text(item.get("notes"))).strip())
        rows.append(row)
        ids.add(oid)
        recent.add(company.lower())
        added.append(company)
    if added:
        write_csv(TRACKER / "outreach.csv", OUTREACH_FIELDS, rows)
    return added


def record(args):
    today = args.date
    data = json.loads(Path(args.leads).read_text(encoding="utf-8"))
    leads = read_csv(TRACKER / "leads.csv", LEAD_FIELDS)
    by_id = {r["id"]: r for r in leads}
    new, updated = [], []
    for item in data.get("leads") or []:
        company = text(item.get("company"))
        if not company:
            continue
        lid = slug(company)
        row = by_id.get(lid)
        if row is None:
            row = dict.fromkeys(LEAD_FIELDS, "")
            row.update(id=lid, company=company, status="new", first_seen=today)
            leads.append(row)
            by_id[lid] = row
            new.append(company)
        else:
            updated.append(company)
        merge_lead(row, item, today)
        if row["status"] == "new" and row["first_seen"] < today:
            row["status"] = "watching"

    # LinkedIn bookkeeping from the sweep: ids found from postings, and when each lead was checked.
    cand_path = WORK / "candidates.json"
    swept = json.loads(cand_path.read_text(encoding="utf-8")) if cand_path.exists() else {}
    for lid in swept.get("roster_checked", []):
        if lid in by_id:
            by_id[lid]["li_checked"] = today
    ids_found = []
    for lid, cid in (swept.get("resolved_ids") or {}).items():
        if lid in by_id and not by_id[lid]["linkedin_id"]:
            by_id[lid]["linkedin_id"] = cid
            ids_found.append(by_id[lid]["company"])
    by_name = {r["company"].lower(): r for r in leads}
    for c in swept.get("candidates", []):
        lead = by_name.get((c.get("lead") or "").lower())
        if lead and c["kind"] == "job":
            seen_job = f"{c['title']} ({c.get('published') or today})"
            if seen_job not in lead["last_jobs"]:
                lead["last_jobs"] = (f"{today}: {seen_job}" + (" · " + lead["last_jobs"] if lead["last_jobs"] else ""))[:600]

    # Statuses from the outreach tracker (board clicks land there): sent or replied -> contacted.
    contacted = {r["company"].lower() for r in read_csv(TRACKER / "outreach.csv", OUTREACH_FIELDS)
                 if r["status"] in ("sent", "replied", "meeting")}
    for row in leads:
        if row["company"].lower() in contacted and row["status"] in ("new", "watching"):
            row["status"] = "contacted"
    leads.sort(key=lambda r: (r["status"] == "ignore", r["company"].lower()))
    write_csv(TRACKER / "leads.csv", LEAD_FIELDS, leads)

    # Everything this sweep showed is now seen, whether or not it became a lead.
    seen = read_csv(TRACKER / "radar_seen.csv", SEEN_FIELDS)
    keys = {r["key"] for r in seen}
    marked = 0
    if swept:
        for c in swept.get("candidates", []):
            for k in c.get("keys", []):
                if k not in keys:
                    seen.append({"key": k, "kind": c["kind"], "first_seen": today, "title": c["title"][:120]})
                    keys.add(k)
                    marked += 1
    cutoff = (date.fromisoformat(today) - timedelta(days=SEEN_KEEP_DAYS)).isoformat()
    seen = [r for r in seen if r["first_seen"] >= cutoff]
    write_csv(TRACKER / "radar_seen.csv", SEEN_FIELDS, seen)

    # Outreach drafts: held while a weekly scan is running in this folder, flushed by the next run.
    pending_path = WORK / "pending-outreach.json"
    pending = json.loads(pending_path.read_text(encoding="utf-8")) if pending_path.exists() else []
    drafts = pending + list(data.get("outreach") or [])
    held = args.hold_outreach or scan_running()
    added = []
    if held:
        pending_path.write_text(json.dumps(drafts, indent=1, ensure_ascii=False), encoding="utf-8")
    else:
        added = add_outreach(drafts, today)
        if pending_path.exists():
            pending_path.unlink()
    summary = {"date": today, "new_leads": new, "updated_leads": updated, "seen_marked": marked,
               "linkedin_ids_found": ids_found,
               "outreach_added": added, "outreach_held": len(drafts) if held else 0,
               "roster": {s: sum(1 for r in leads if r["status"] == s) for s in LEAD_STATUSES},
               "roster_with_linkedin_id": sum(1 for r in leads if r["linkedin_id"]),
               "missing_linkedin_id": [r["company"] for r in leads
                                       if not r["linkedin_id"] and r["status"] in ("new", "watching")][:10]}
    print(json.dumps(summary, indent=1, ensure_ascii=False))


def history(args):
    """Everything the trackers already hold about a company, so a lead isn't reported as new by mistake."""
    q = args.company.lower()
    sources = [("leads", "leads.csv", LEAD_FIELDS, ("status", "fit", "trigger_date", "trigger", "move")),
               ("roles", "roles.csv", ROLE_FIELDS, ("status", "fit", "role", "location", "first_seen", "url")),
               ("outreach", "outreach.csv", OUTREACH_FIELDS, ("status", "created", "trigger")),
               ("decisions", "decisions.csv", ["date", "status", "role_id", "company", "note"],
                ("date", "status", "role_id", "note")),
               ("news", "news.csv", ["reported_on", "company", "date", "headline", "url"], ("date", "headline")),
               ("companies", "companies.csv", ["company", "careers_url", "last_checked", "notes"],
                ("last_checked", "careers_url", "notes"))]
    found = 0
    for label, name, fields, show in sources:
        for r in read_csv(TRACKER / name, fields):
            if q in r["company"].lower() or name_key(args.company) == name_key(r["company"]):
                print(f"{label}: {r['company']} | " + " | ".join(r[f][:160] for f in show))
                found += 1
    print(f"{found} rows" if found else "nothing on file")


def set_status(args):
    leads = read_csv(TRACKER / "leads.csv", LEAD_FIELDS)
    hits = [r for r in leads if r["company"].lower() == args.company.lower() or r["id"] == slug(args.company)]
    if not hits:
        hits = [r for r in leads if args.company.lower() in r["company"].lower()]
    if len(hits) != 1:
        sys.exit(f"{len(hits)} leads match {args.company!r}: " + ", ".join(r["company"] for r in hits))
    row = hits[0]
    row["status"] = args.status
    if args.note:
        row["notes"] = (f"{date.today().isoformat()}: {args.note}" + (" · " + row["notes"] if row["notes"] else ""))
    write_csv(TRACKER / "leads.csv", LEAD_FIELDS, leads)
    print(f"{row['company']}: {args.status}")


def roster(args):
    leads = read_csv(TRACKER / "leads.csv", LEAD_FIELDS)
    for r in leads:
        print(" | ".join([r["status"], r["fit"], r["hiring_odds"], r["company"], r["country"],
                          r["trigger_date"], r["trigger"][:90], "li:" + (r["linkedin_id"] or "-"),
                          people_search(r["company"], "founder")]))
    print(f"{len(leads)} leads")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("sweep")
    p.add_argument("--days", type=int, default=3, help="look back N days (seen items are skipped anyway)")
    p.add_argument("--id-lookups", type=int, default=20, help="max LinkedIn job pages fetched for company ids")
    p.add_argument("--name-searches", type=int, default=40,
                   help="max roster leads without a LinkedIn id searched by name (least recently checked first)")
    p.add_argument("--no-linkedin", action="store_true")
    p.add_argument("--no-news", action="store_true", help="for testing the LinkedIn channels")
    p.set_defaults(func=sweep)
    p = sub.add_parser("record")
    p.add_argument("leads")
    p.add_argument("--date", default=date.today().isoformat())
    p.add_argument("--hold-outreach", action="store_true")
    p.set_defaults(func=record)
    p = sub.add_parser("set")
    p.add_argument("company")
    p.add_argument("status", choices=LEAD_STATUSES)
    p.add_argument("--note", default="")
    p.set_defaults(func=set_status)
    p = sub.add_parser("history", help="what the trackers already hold about a company")
    p.add_argument("company")
    p.set_defaults(func=history)
    p = sub.add_parser("roster")
    p.set_defaults(func=roster)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
