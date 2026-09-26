#!/usr/bin/env python3
"""Merge one weekly scan's findings into the tracker CSVs.

Usage:
    python3 scripts/update_tracker.py --date YYYY-MM-DD work/findings-*.json > work/summary.json

Each findings file is written by one research subagent (schema in ROUTINE.md).
The script updates tracker/roles.csv, tracker/companies.csv and tracker/news.csv
in place and prints a JSON summary that the weekly report is written from.

Role statuses in tracker/roles.csv:
    open       seen in the latest scan
    not-found  missing from the latest scan although its company was checked
    closed     closing date passed, or not seen for 3+ weeks
    applied    set by hand: kept up to date, never flagged as new again
    ignore     set by hand: never reported again
"""

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

ROLE_FIELDS = ["id", "company", "role", "location", "url", "fit", "status",
               "first_seen", "last_seen", "closes", "starts", "notes"]
COMPANY_FIELDS = ["company", "careers_url", "last_checked", "notes"]
NEWS_FIELDS = ["reported_on", "company", "date", "headline", "url"]

FITS = ("strong", "possible", "signal")
USER_STATUSES = ("applied", "ignore")
STATUS_ORDER = {"open": 0, "applied": 1, "not-found": 2, "closed": 3, "ignore": 4}
FIT_ORDER = {fit: i for i, fit in enumerate(FITS)}
CLOSE_AFTER_DAYS = 21
DEADLINE_WINDOW_DAYS = 42


def slug(*parts):
    text = " ".join(p for p in parts if p).lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:90]


def norm_url(url):
    return (url or "").strip().split("#", 1)[0].rstrip("/").lower()


def simple_name(name):
    return " ".join((name or "").lower().replace("–", "-").replace("—", "-").split())


def base_company(name):
    """'Pfizer – Grange Castle' -> 'pfizer', so site rows count as the same employer."""
    return re.split(r" - | \(", simple_name(name), maxsplit=1)[0]


def covered(company, checked):
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


def watchlist_companies(path):
    """First-column names of every table in watchlist.md, in order, deduplicated."""
    if not path.exists():
        return []
    names, in_table = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
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
                isinstance(batch.get(k, []), list) for k in ("companies", "roles", "news")):
            sys.exit(f"{path}: expected an object with 'companies', 'roles' and 'news' lists")
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


def age_out_roles(rows, seen, checked, today):
    """Mark roles missing from this scan. Returns (newly not-found, newly closed)."""
    gone, closed = [], []
    for row in rows:
        if row["id"] in seen or row["status"] in USER_STATUSES + ("closed",):
            continue
        if not covered(row["company"], checked):
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
    args = parser.parse_args()

    today = parse_date(args.date)
    if today is None or len(args.date) != 10:
        sys.exit(f"--date must be YYYY-MM-DD, got {args.date!r}")
    run_date = today.isoformat()
    batches = load_batches(args.findings)

    roles_path = args.tracker / "roles.csv"
    companies_path = args.tracker / "companies.csv"
    news_path = args.tracker / "news.csv"
    rows = read_csv(roles_path, ROLE_FIELDS)
    companies = read_csv(companies_path, COMPANY_FIELDS)
    news = read_csv(news_path, NEWS_FIELDS)
    baseline = not rows
    problems = []

    entries = [e for b in batches for e in b.get("companies", []) if text(e.get("name"))]
    checked = {base_company(e["name"]) for e in entries if is_checked(e)}
    new, seen = merge_roles(rows, batches, run_date, problems)
    gone, closed = age_out_roles(rows, seen, checked, today)
    merge_companies(companies, batches, run_date)
    fresh_news = merge_news(news, batches, run_date)

    reported = {simple_name(e["name"]) for e in entries}
    rows.sort(key=role_sort)
    companies.sort(key=lambda r: r["company"].lower())
    news.sort(key=lambda r: (r["reported_on"], r["date"]), reverse=True)
    new_ids = {r["id"] for r in new}
    summary = {
        "date": run_date,
        "baseline": baseline,
        "new_roles": [r for r in rows if r["id"] in new_ids],
        "still_open": [r for r in rows if r["status"] == "open" and r["id"] not in new_ids],
        "applied": [r for r in rows if r["status"] == "applied"],
        "no_longer_found": sorted(gone, key=role_sort),
        "closed": sorted(closed, key=role_sort),
        "deadlines_soon": sorted(
            (r for r in rows
             if r["status"] in ("open", "applied", "not-found") and parse_date(r["closes"])
             and 0 <= (parse_date(r["closes"]) - today).days <= DEADLINE_WINDOW_DAYS),
            key=lambda r: r["closes"]),
        "new_news": fresh_news,
        "companies_checked": sorted({text(e["name"]) for e in entries if is_checked(e)}),
        "companies_failed": sorted({text(e["name"]) for e in entries if not is_checked(e)}),
        "companies_not_reported": [n for n in watchlist_companies(args.watchlist)
                                   if simple_name(n) not in reported],
        "problems": problems,
    }

    if not args.dry_run:
        write_csv(roles_path, ROLE_FIELDS, rows)
        write_csv(companies_path, COMPANY_FIELDS, companies)
        write_csv(news_path, NEWS_FIELDS, news)
    for problem in problems:
        print(f"warning: {problem}", file=sys.stderr)
    json.dump(summary, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
