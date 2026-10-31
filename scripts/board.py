#!/usr/bin/env python3
"""Bridge between the tracker and the job board page (board/index.html).

Usage:
    python3 scripts/board.py export                 # write work/board/roles.json for publishing
    python3 scripts/board.py import DIR_OR_JSON      # record clicks made on the page
    python3 scripts/board.py import work/board-clicks # ...or the folder holding all three collections

The page lists every role that isn't closed and saves each click to its own database
collection "decisions" (one document per role id, or "company:<name>" for a whole company).
`import` takes that collection as the folder ArtifactData `list` writes with `out_dir`
(one <doc_id>.json per document), or as a JSON list of {id, data} or plain bodies, and appends each changed decision to
tracker/decisions.csv through the same rules as scripts/mark.py.

The page also has Outreach and Events tabs, fed from tracker/outreach.csv and tracker/events.csv;
their clicks go to the collections "outreach" and "events" ({status, at} per item id), and
`import` given the parent folder (work/board-clicks) records those through scripts/network.py.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from network import (EVENT_FIELDS, OUTREACH_FIELDS, age_events, people_search,  # noqa: E402
                     set_statuses)
from update_tracker import (DECISION_FIELDS, ROLE_FIELDS, apply_decisions, read_csv,  # noqa: E402
                            role_sort, simple_name, write_csv)

NOTE_CHARS = 280


def export(tracker, out):
    rows = [r for r in read_csv(tracker / "roles.csv", ROLE_FIELDS) if r["status"] != "closed"]
    keep = ("id", "company", "role", "location", "url", "fit", "status", "first_seen", "closes", "starts")
    roles = []
    for r in sorted(rows, key=role_sort):
        item = {k: r[k] for k in keep if r[k]}
        if r["notes"]:
            item["notes"] = r["notes"][:NOTE_CHARS] + ("…" if len(r["notes"]) > NOTE_CHARS else "")
        roles.append(item)
    out.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    events = read_csv(tracker / "events.csv", EVENT_FIELDS)
    age_events(events, today)
    events = [e for e in events if e["status"] != "past"]
    outreach = [{**o, "linkedin_search": people_search(o["company"], o["contact"])}
                for o in read_csv(tracker / "outreach.csv", OUTREACH_FIELDS)]
    payload = {"exported": today, "roles": roles, "events": events, "outreach": outreach}
    (out / "roles.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                                    encoding="utf-8")
    print(f"{len(roles)} roles, {len(events)} events, {len(outreach)} outreach items -> {out / 'roles.json'}")


def latest(decisions):
    """Most recent decision per role id or company."""
    last = {}
    for d in decisions:
        last[d["role_id"] or "company:" + simple_name(d["company"])] = d["status"]
    return last


def import_all(tracker, path):
    """path is either one collection's folder or a folder holding decisions/, outreach/, events/."""
    subdirs = [path / k for k in ("decisions", "outreach", "events") if (path / k).is_dir()]
    if not subdirs:
        return import_clicks(tracker, path)
    for sub in subdirs:
        if sub.name == "decisions":
            import_clicks(tracker, sub)
            continue
        changes = {}
        for f in sorted(sub.glob("*.json")):
            body = json.loads(f.read_text(encoding="utf-8"))
            if body.get("status"):
                changes[f.stem] = str(body["status"]).lower()
        changed = set_statuses(tracker, sub.name, changes, date.today().isoformat())
        print(f"{len(changed)} {sub.name} status changes from the board" + (f": {', '.join(changed)}" if changed else ""))


def import_clicks(tracker, path):
    if path.is_dir():  # ArtifactData list with out_dir: one <doc_id>.json body per file
        docs = [dict(json.loads(p.read_text(encoding="utf-8")), _id=p.stem)
                for p in sorted(path.glob("*.json"))]
    else:
        docs = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(docs, dict):
            docs = docs.get("documents") or docs.get("docs") or list(docs.values())
    rows = read_csv(tracker / "roles.csv", ROLE_FIELDS)
    by_id = {r["id"]: r for r in rows}
    decisions = read_csv(tracker / "decisions.csv", DECISION_FIELDS)
    last = latest(decisions)
    today, added, skipped = date.today().isoformat(), [], []
    for doc in docs:
        body = doc.get("data", doc) if isinstance(doc, dict) else {}
        status, note = str(body.get("status", "")).lower(), str(body.get("note", ""))
        if body.get("scope") == "company":
            company = str(body.get("company", ""))
            key, role_id = "company:" + simple_name(company), ""
        else:
            role_id = str(body.get("role_id") or doc.get("id") or doc.get("_id", ""))
            company, key = by_id.get(role_id, {}).get("company", str(body.get("company", ""))), role_id
            if role_id not in by_id:
                skipped.append(role_id)
                continue
        current = last.get(key) or (by_id[role_id]["status"] if role_id else "open")
        if status == current or (status == "open" and key not in last):
            continue
        added.append(dict(date=str(body.get("at", today))[:10], status=status, role_id=role_id,
                          company=company, note=note))
    problems = []
    apply_decisions(rows, added, problems)
    if problems:
        sys.exit("\n".join(problems))
    if added:
        write_csv(tracker / "decisions.csv", DECISION_FIELDS, decisions + added)
        write_csv(tracker / "roles.csv", ROLE_FIELDS, sorted(rows, key=role_sort))
    for d in added:
        print(f"{d['status']}: {d['role_id'] or 'all roles at ' + d['company']}")
    print(f"{len(added)} new decisions from the board"
          + (f"; {len(skipped)} unknown role ids skipped: {', '.join(skipped)}" if skipped else ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("export", "import"))
    parser.add_argument("file", nargs="?", type=Path, help="import: the decisions JSON")
    parser.add_argument("--tracker", type=Path, default=Path("tracker"))
    parser.add_argument("--out", type=Path, default=Path("work/board"))
    args = parser.parse_args()
    if args.action == "export":
        export(args.tracker, args.out)
    elif not args.file:
        sys.exit("import needs the decisions JSON file")
    else:
        import_all(args.tracker, args.file)


if __name__ == "__main__":
    main()
