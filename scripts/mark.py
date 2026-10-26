#!/usr/bin/env python3
"""Record what I've applied for, or ruled out, so the weekly scans stop re-reporting it.

Usage:
    python3 scripts/mark.py find kerry food safety        # search the tracker for role ids
    python3 scripts/mark.py applied ID [ID ...] [--note "submitted 27 Oct"]
    python3 scripts/mark.py ineligible ID [ID ...] --note "needs fluent German"
    python3 scripts/mark.py off-path ID --note "too analytical-chemistry"
    python3 scripts/mark.py ignore --company "Richter BioLogics" --note "not interested"
    python3 scripts/mark.py list                          # show every decision so far

Statuses: applied, interviewing, offer, rejected (tracked and shown in the report),
ineligible, off-path (doesn't fit my skills or direction), ignore (never reported again). With --company and no ids, the decision covers
every role at that company, including ones found in later scans.

Each decision is appended to tracker/decisions.csv and applied to tracker/roles.csv at once;
scripts/update_tracker.py re-applies them on every run.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from update_tracker import (DECISION_FIELDS, ROLE_FIELDS, USER_STATUSES, apply_decisions,  # noqa: E402
                            read_csv, role_sort, simple_name, write_csv)


def find(rows, words):
    words = [w.lower() for w in words]
    hits = [r for r in rows
            if all(w in " ".join((r["id"], r["company"], r["role"], r["location"])).lower() for w in words)]
    for r in sorted(hits, key=role_sort):
        closes = f" · closes {r['closes']}" if r["closes"] else ""
        print(f"{r['id']}\n    {r['company']} — {r['role']} ({r['location']}) [{r['status']}, {r['fit']}{closes}]")
    if not hits:
        print("no matching roles")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("find", "list") + USER_STATUSES)
    parser.add_argument("args", nargs="*", help="search words (find) or role ids")
    parser.add_argument("--company", help="apply to every role at this company instead of listed ids")
    parser.add_argument("--note", default="", help="why, e.g. 'needs Australian PR'")
    parser.add_argument("--tracker", type=Path, default=Path("tracker"))
    args = parser.parse_args()

    roles_path, decisions_path = args.tracker / "roles.csv", args.tracker / "decisions.csv"
    rows = read_csv(roles_path, ROLE_FIELDS)
    decisions = read_csv(decisions_path, DECISION_FIELDS)

    if args.action == "find":
        return find(rows, args.args)
    if args.action == "list":
        for d in decisions:
            print(f"{d['date']}  {d['status']:<12} {d['role_id'] or 'ALL ROLES AT ' + d['company']}"
                  f"{'  — ' + d['note'] if d['note'] else ''}")
        return

    today = date.today().isoformat()
    if args.company:
        if args.args:
            sys.exit("give role ids or --company, not both")
        names = {simple_name(r["company"]) for r in rows}
        if simple_name(args.company) not in names:
            print(f"note: no tracked roles at {args.company!r} yet; the rule will apply when one appears")
        added = [dict(date=today, status=args.action, role_id="", company=args.company, note=args.note)]
    else:
        if not args.args:
            sys.exit("give at least one role id (use 'find' to look them up) or --company")
        by_id = {r["id"]: r for r in rows}
        unknown = [i for i in args.args if i not in by_id]
        if unknown:
            sys.exit("not in the tracker: " + ", ".join(unknown) + " (use 'find' to look up ids)")
        added = [dict(date=today, status=args.action, role_id=i, company=by_id[i]["company"], note=args.note)
                 for i in args.args]

    problems = []
    apply_decisions(rows, added, problems)
    if problems:
        sys.exit("\n".join(problems))
    write_csv(decisions_path, DECISION_FIELDS, decisions + added)
    write_csv(roles_path, ROLE_FIELDS, sorted(rows, key=role_sort))
    for d in added:
        print(f"{d['status']}: {d['role_id'] or 'all roles at ' + d['company']}")


if __name__ == "__main__":
    main()
