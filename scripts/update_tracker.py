#!/usr/bin/env python3
"""Merge one weekly scan's findings into the tracker CSVs.

Usage:
    python3 scripts/update_tracker.py --date YYYY-MM-DD work/findings-*.json > work/summary.json
    (add --partial for a supplementary run that covers only part of the watchlist)
    (the split Monday/Thursday scans add --exact plus --only/--exclude; see ROUTINE.md)

Each findings file is written by one research subagent (schema in ROUTINE.md).
The script updates tracker/roles.csv, tracker/companies.csv and tracker/news.csv
in place and prints a JSON summary that the weekly report is written from.

Role statuses in tracker/roles.csv:
    open       seen in the latest scan
    not-found  missing from the latest scan although its company was checked
    closed     closing date passed, or not seen for 3+ weeks
    applied, interviewing, offer, rejected
               set from tracker/decisions.csv: kept up to date, never flagged as new again
    ineligible, off-path, ignore
               set from tracker/decisions.csv: never reported again

tracker/decisions.csv is where my own calls live (written by scripts/mark.py, or by hand).
Each row names a role id, or only a company to rule out every role there, now and later.
Decisions are re-applied on every run, so they survive the tracker being rebuilt.

tracker/pipeline.csv holds programmes that are NOT open for applications yet but will open
soon, so I can prepare and start talking to people before the window. Findings files list them
under "opening_soon". Statuses: upcoming, open (applications are live; the role is in roles.csv
too), not-running (the company says no intake this cycle), closed, plus the decision statuses
above. A decision can name a pipeline id in role_id, or a company, just like a role.
"""

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

ROLE_FIELDS = ["id", "company", "role", "location", "url", "fit", "status",
               "first_seen", "last_seen", "closes", "starts", "notes"]
COMPANY_FIELDS = ["company", "careers_url", "last_checked", "notes"]
NEWS_FIELDS = ["reported_on", "company", "date", "headline", "url"]
PIPELINE_FIELDS = ["id", "company", "programme", "location", "url", "opens", "closes", "starts",
                   "confidence", "fit", "status", "first_seen", "last_seen", "prep", "notes"]
DECISION_FIELDS = ["date", "status", "role_id", "company", "note"]

FITS = ("strong", "possible", "signal")
APPLIED_STATUSES = ("applied", "interviewing", "offer", "rejected")
HIDDEN_STATUSES = ("ineligible", "off-path", "ignore")
USER_STATUSES = APPLIED_STATUSES + HIDDEN_STATUSES
STATUS_ORDER = {"open": 0, "offer": 1, "interviewing": 1, "applied": 1, "not-found": 2,
                "closed": 3, "rejected": 4, "ineligible": 5, "off-path": 5, "ignore": 5}
FIT_ORDER = {fit: i for i, fit in enumerate(FITS)}
CLOSE_AFTER_DAYS = 21
DEADLINE_WINDOW_DAYS = 42
PIPELINE_STATUSES = ("upcoming", "open", "not-running", "closed")
PREPARE_WINDOW_DAYS = 183  # "prepare now": opens within about six months, or no date yet
CONFIDENCES = ("stated", "inferred", "unverified")


def slug(*parts):
    text = " ".join(p for p in parts if p).lower()
    full = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(full) <= 90:
        return full
    # Long names (e.g. "University research labs (...)") would otherwise truncate to the same id.
    return full[:81].rstrip("-") + "-" + hashlib.sha1(full.encode()).hexdigest()[:8]


def norm_url(url):
    return (url or "").strip().split("#", 1)[0].rstrip("/").lower()


def simple_name(name):
    return " ".join((name or "").lower().replace("–", "-").replace("—", "-").split())


def base_company(name):
    """'Pfizer – Grange Castle' -> 'pfizer', so site rows count as the same employer."""
    return re.split(r" - | \(", simple_name(name), maxsplit=1)[0]


def covered(company, checked, exact=False):
    if exact:
        return simple_name(company) in checked
    c = base_company(company)
    return any(c == k or c.startswith(k + " ") or k.startswith(c + " ") for k in checked)


def parse_date(text):
    try:
        return date.fromisoformat((text or "").strip()[:10])
    except ValueError:
        return None


def text(value):
    return str(value).strip() if value is not None else ""


def is_checked(entry):
    value = entry.get("checked", True)
    return value.strip().lower() != "false" if isinstance(value, str) else value is not False


def read_csv(path, fields):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [{k: text(row.get(k)) for k in fields} for row in csv.DictReader(f)]


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def watchlist_companies(path, only=frozenset(), exclude=frozenset()):
    """First-column names of every table in watchlist.md, in order, deduplicated.

    only / exclude are sets of section numbers ("20", "21"): a section "20e. ..." has number 20.
    """
    if not path.exists():
        return []
    names, in_table, number = [], False, ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        heading = re.fullmatch(r"#{2,3} (\d+)[a-z]?\. .+", line)
        if heading:
            number = heading.group(1)
        if (only and number not in only) or number in exclude:
            in_table = False
            continue
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not in_table:  # header row
            in_table = True
        elif cells[0] and not set(cells[0]) <= set("-: "):  # skip the separator row
            names.append(cells[0])
    return list(dict.fromkeys(names))


def role_sort(row):
    return (STATUS_ORDER.get(row["status"], 9), FIT_ORDER.get(row["fit"], 9),
            row["company"].lower(), row["role"].lower())


def load_batches(paths):
    batches = []
    for path in paths:
        try:
            batch = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            sys.exit(f"{path}: {e}")
        if not isinstance(batch, dict) or not all(
                isinstance(batch.get(k, []), list) for k in ("companies", "roles", "news", "opening_soon")):
            sys.exit(f"{path}: expected an object with 'companies', 'roles' and 'news' lists "
                     "(and optionally 'opening_soon')")
        batches.append(batch)
    return batches


def merge_roles(rows, batches, run_date, problems):
    """Add or refresh every role in the findings. Returns (new rows, ids seen this run)."""
    by_id = {r["id"]: r for r in rows}
    by_url = {norm_url(r["url"]): r for r in rows if r["url"]}
    new, seen = [], set()
    for batch in batches:
        for item in batch.get("roles", []):
            company, title = text(item.get("company")), text(item.get("role"))
            if not company or not title:
                problems.append(f"skipped a role without company/role: {item}")
                continue
            fit = text(item.get("fit")).lower()
            if fit not in FITS:
                problems.append(f"{company} / {title}: fit {fit!r} is not one of {FITS}; using 'possible'")
                fit = "possible"
            given_id = text(item.get("id"))
            if given_id and given_id not in by_id:
                problems.append(f"{company} / {title}: id {given_id!r} is not in the tracker")
            new_id = slug(company, title, text(item.get("location"))) or f"role-{len(rows) + 1}"
            row = (by_id.get(given_id) or by_id.get(new_id)
                   or by_url.get(norm_url(text(item.get("url"))) or None))
            if row is None:
                row = dict.fromkeys(ROLE_FIELDS, "")
                row.update(id=new_id, company=company, role=title, status="open", first_seen=run_date)
                rows.append(row)
                by_id[new_id] = row
                new.append(row)
            for field in ("location", "url", "closes", "starts", "notes"):
                value = text(item.get(field))
                if value:
                    row[field] = value
            row["fit"] = fit
            row["last_seen"] = run_date
            if row["status"] not in USER_STATUSES:
                row["status"] = "open"
            if row["url"]:
                by_url[norm_url(row["url"])] = row
            seen.add(row["id"])
    return new, seen


def age_out_roles(rows, seen, checked, today, exact=False):
    """Mark roles missing from this scan. Returns (newly not-found, newly closed)."""
    gone, closed = [], []
    for row in rows:
        if row["id"] in seen or row["status"] in USER_STATUSES + ("closed",):
            continue
        if not covered(row["company"], checked, exact):
            continue  # company not searched this run: leave the row alone
        closes, last = parse_date(row["closes"]), parse_date(row["last_seen"])
        if (closes and closes < today) or (last and (today - last).days >= CLOSE_AFTER_DAYS):
            row["status"] = "closed"
            closed.append(row)
        else:
            if row["status"] == "open":
                gone.append(row)
            row["status"] = "not-found"
    return gone, closed


def apply_decisions(rows, decisions, problems, extra=()):
    """Set each decided role's status; a company-only decision covers all that company's roles.

    extra: pipeline rows, which a decision can name by id or by company in the same way.

    Later rows in decisions.csv win, so a role can move applied -> interviewing -> rejected.
    "open" undoes an earlier decision; the next scan then refreshes the role as usual.
    """
    everything = list(rows) + list(extra)
    by_id = {r["id"]: r for r in everything}

    def set_status(row, status):
        if status != "open":
            row["status"] = status
        elif row["status"] in USER_STATUSES:
            row["status"] = "upcoming" if row in extra else "open"

    for d in decisions:
        status = d["status"].lower()
        if status not in USER_STATUSES + ("open",):
            problems.append(f"decisions.csv: status {d['status']!r} is not one of {USER_STATUSES + ('open',)}")
            continue
        if d["role_id"]:
            row = by_id.get(d["role_id"])
            if row is None:
                problems.append(f"decisions.csv: role id {d['role_id']!r} is not in the tracker")
            else:
                set_status(row, status)
        elif d["company"]:
            for row in everything:
                if simple_name(row["company"]) == simple_name(d["company"]):
                    set_status(row, status)


def linkedin_search(company, programme):
    """A LinkedIn people-search link to click. Built here, never fetched."""
    words = f"{company} {programme}".replace("(", " ").replace(")", " ")
    return "https://www.linkedin.com/search/results/people/?keywords=" + quote(" ".join(words.split()[:8]))


def merge_pipeline(rows, batches, run_date, problems):
    """Add or refresh every "opening_soon" entry. Returns the ids seen this run."""
    by_id = {r["id"]: r for r in rows}
    by_url = {norm_url(r["url"]): r for r in rows if r["url"]}
    seen = set()
    for batch in batches:
        for item in batch.get("opening_soon", []):
            company, programme = text(item.get("company")), text(item.get("programme"))
            if not company or not programme:
                problems.append(f"skipped an opening_soon entry without company/programme: {item}")
                continue
            status = text(item.get("status")).lower() or "upcoming"
            if status not in PIPELINE_STATUSES:
                problems.append(f"{company} / {programme}: status {status!r} is not one of "
                                f"{PIPELINE_STATUSES}; using 'upcoming'")
                status = "upcoming"
            new_id = slug(company, programme)
            given_id = text(item.get("id"))
            row = (by_id.get(given_id) or by_id.get(new_id)
                   or by_url.get(norm_url(text(item.get("url"))) or None))
            fit = text(item.get("fit")).lower() or (row or {}).get("fit", "")
            if fit not in FITS:
                problems.append(f"{company} / {programme}: fit {fit!r} is not one of {FITS}; using 'possible'")
                fit = "possible"
            confidence = text(item.get("confidence")).lower() or (row or {}).get("confidence", "")
            if confidence not in CONFIDENCES:
                problems.append(f"{company} / {programme}: confidence {confidence!r} is not one of "
                                f"{CONFIDENCES}; using 'unverified'")
                confidence = "unverified"
            opens = text(item.get("opens"))
            if opens and parse_date(opens) is None:
                problems.append(f"{company} / {programme}: opens {opens!r} is not YYYY-MM-DD; leaving it as it was")
                opens = ""
            if row is None:
                row = dict.fromkeys(PIPELINE_FIELDS, "")
                row.update(id=new_id, company=company, programme=programme, first_seen=run_date)
                rows.append(row)
                by_id[new_id] = row
            for field in ("location", "url", "closes", "starts", "prep", "notes"):
                value = text(item.get(field))
                if value:
                    row[field] = value
            if opens:  # a date given now replaces the old one; leaving it out keeps what we had
                row["opens"] = opens
            row["confidence"], row["fit"], row["last_seen"] = confidence, fit, run_date
            if row["status"] not in USER_STATUSES:
                row["status"] = status
            if row["url"]:
                by_url[norm_url(row["url"])] = row
            seen.add(row["id"])
    return seen


def pipeline_sort(row):
    opens = parse_date(row["opens"])
    return (opens or date.max, FIT_ORDER.get(row["fit"], 9), row["company"].lower())


def merge_companies(companies, batches, run_date):
    by_name = {r["company"]: r for r in companies}
    for batch in batches:
        for entry in batch.get("companies", []):
            name = text(entry.get("name"))
            if not name:
                continue
            row = by_name.get(name)
            if row is None:
                row = dict.fromkeys(COMPANY_FIELDS, "")
                row["company"] = name
                by_name[name] = row
                companies.append(row)
            if is_checked(entry):
                row["last_checked"] = run_date
            for field, key in (("careers_url", "careers_url"), ("notes", "notes")):
                value = text(entry.get(key))
                if value:
                    row[field] = value


def merge_news(news, batches, run_date):
    known = {norm_url(n["url"]) for n in news if n["url"]}
    fresh = []
    for batch in batches:
        for item in batch.get("news", []):
            url = text(item.get("url"))
            if not url or norm_url(url) in known:
                continue
            known.add(norm_url(url))
            row = {"reported_on": run_date, "company": text(item.get("company")),
                   "date": text(item.get("date")), "headline": text(item.get("headline")), "url": url}
            news.append(row)
            fresh.append({**row, "why": text(item.get("why"))})
    return fresh


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("findings", nargs="+", type=Path, help="work/findings-*.json files")
    parser.add_argument("--date", required=True, help="scan date in NZ, YYYY-MM-DD")
    parser.add_argument("--tracker", type=Path, default=Path("tracker"), help="tracker directory")
    parser.add_argument("--watchlist", type=Path, default=Path("watchlist.md"))
    parser.add_argument("--dry-run", action="store_true", help="print the summary without writing")
    parser.add_argument("--partial", action="store_true",
                        help="supplementary run over part of the watchlist: add and refresh roles, "
                             "but don't mark unseen roles not-found or closed (company names shared "
                             "with unscanned rows would otherwise age them out wrongly)")
    parser.add_argument("--exact", action="store_true",
                        help="age out only roles whose company name exactly matches a company checked "
                             "this run, and limit still-open, applied and deadline lists to those "
                             "companies (used by the split Monday and Thursday scans)")
    parser.add_argument("--only", default="", help="watchlist sections in this run, e.g. 20,21")
    parser.add_argument("--exclude", default="", help="watchlist sections not in this run, e.g. 20,21")
    args = parser.parse_args()
    only = {n.strip() for n in args.only.split(",") if n.strip()}
    exclude = {n.strip() for n in args.exclude.split(",") if n.strip()}

    today = parse_date(args.date)
    if today is None or len(args.date) != 10:
        sys.exit(f"--date must be YYYY-MM-DD, got {args.date!r}")
    run_date = today.isoformat()
    batches = load_batches(args.findings)

    roles_path = args.tracker / "roles.csv"
    companies_path = args.tracker / "companies.csv"
    news_path = args.tracker / "news.csv"
    pipeline_path = args.tracker / "pipeline.csv"
    pipeline = read_csv(pipeline_path, PIPELINE_FIELDS)
    rows = read_csv(roles_path, ROLE_FIELDS)
    companies = read_csv(companies_path, COMPANY_FIELDS)
    news = read_csv(news_path, NEWS_FIELDS)
    decisions = read_csv(args.tracker / "decisions.csv", DECISION_FIELDS)
    baseline = not rows
    problems = []

    entries = [e for b in batches for e in b.get("companies", []) if text(e.get("name"))]
    key = simple_name if args.exact else base_company
    checked = {key(e["name"]) for e in entries if is_checked(e)}
    new, seen = merge_roles(rows, batches, run_date, problems)
    merge_pipeline(pipeline, batches, run_date, problems)
    apply_decisions(rows, decisions, problems, extra=pipeline)
    gone, closed = ([], []) if args.partial else age_out_roles(rows, seen, checked, today, args.exact)
    reported_names = {simple_name(e["name"]) for e in entries}

    def in_run(row):
        return not args.exact or simple_name(row["company"]) in reported_names
    merge_companies(companies, batches, run_date)
    fresh_news = merge_news(news, batches, run_date)

    reported = {simple_name(e["name"]) for e in entries}
    rows.sort(key=role_sort)
    pipeline.sort(key=pipeline_sort)
    companies.sort(key=lambda r: r["company"].lower())
    news.sort(key=lambda r: (r["reported_on"], r["date"]), reverse=True)
    new_ids = {r["id"] for r in new if r["status"] == "open"}

    # Pipeline rows belong to the scan whose watchlist sections hold their company; employers
    # found only by a sweep (not in any section) go with the core scan.
    run_names = {simple_name(n) for n in watchlist_companies(args.watchlist, only, exclude)}
    all_names = {simple_name(n) for n in watchlist_companies(args.watchlist)}

    def pipeline_in_run(row):
        name = simple_name(row["company"])
        return name in run_names or (name not in all_names and not only)

    def with_links(row):
        return {**row, "linkedin_search": linkedin_search(row["company"], row["programme"])}

    waiting = [r for r in pipeline if r["status"] == "upcoming" and pipeline_in_run(r)]

    def days_to_open(row):
        opens = parse_date(row["opens"])
        return (opens - today).days if opens else None

    summary = {
        "date": run_date,
        "baseline": baseline,
        "new_roles": [r for r in rows if r["id"] in new_ids],
        "still_open": [r for r in rows if r["status"] == "open" and r["id"] not in new_ids and in_run(r)],
        "applied": [r for r in rows if r["status"] in APPLIED_STATUSES and in_run(r)],
        "no_longer_found": sorted(gone, key=role_sort),
        "closed": sorted(closed, key=role_sort),
        "deadlines_soon": sorted(
            (r for r in rows
             if r["status"] in ("open", "applied", "interviewing", "not-found") and parse_date(r["closes"]) and in_run(r)
             and 0 <= (parse_date(r["closes"]) - today).days <= DEADLINE_WINDOW_DAYS),
            key=lambda r: r["closes"]),
        "new_news": fresh_news,
        "opening_soon": [with_links(r) for r in waiting
                         if days_to_open(r) is None or days_to_open(r) <= PREPARE_WINDOW_DAYS],
        "later_cycles": [with_links(r) for r in waiting
                         if days_to_open(r) is not None and days_to_open(r) > PREPARE_WINDOW_DAYS],
        "just_opened": [with_links(r) for r in pipeline
                        if r["status"] == "open" and pipeline_in_run(r) and r["last_seen"] == run_date],
        "pipeline_to_recheck": [with_links(r) for r in waiting
                                if days_to_open(r) is not None and days_to_open(r) < -7],
        "companies_checked": sorted({text(e["name"]) for e in entries if is_checked(e)}),
        "companies_failed": sorted({text(e["name"]) for e in entries if not is_checked(e)}),
        "companies_not_reported": [n for n in watchlist_companies(args.watchlist, only, exclude)
                                   if simple_name(n) not in reported],
        "problems": problems,
    }

    if not args.dry_run:
        write_csv(roles_path, ROLE_FIELDS, rows)
        write_csv(companies_path, COMPANY_FIELDS, companies)
        write_csv(news_path, NEWS_FIELDS, news)
        write_csv(pipeline_path, PIPELINE_FIELDS, pipeline)
    for problem in problems:
        print(f"warning: {problem}", file=sys.stderr)
    json.dump(summary, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
