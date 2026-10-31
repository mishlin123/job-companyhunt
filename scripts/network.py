#!/usr/bin/env python3
"""Events calendar and outreach suggestions: the people side of the job hunt.

Usage:
    python3 scripts/network.py merge-events work/events.json      # add or refresh events
    python3 scripts/network.py add-outreach work/outreach.json    # add this week's drafts
    python3 scripts/network.py summary --date YYYY-MM-DD          # JSON for the weekly report
    python3 scripts/network.py set ID STATUS                      # record a status by hand

tracker/events.csv holds conferences, careers fairs, webinars and open days, each with one
concrete goal. Statuses: upcoming (found by a scan), interested, going, not-going, attended,
past (set automatically once an event I wasn't going to has ended).

tracker/outreach.csv holds outreach suggestions drafted by the scans from news, intakes and
events. Claude only drafts: I send every message myself. Statuses: suggested, sent, replied,
meeting, no-reply, skipped. Contacts are described by role or team, never by name.

Both files are written only by this script (and by scripts/board.py import, which calls
set_statuses with the clicks from the job board).
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from update_tracker import parse_date, read_csv, slug, text, write_csv  # noqa: E402

EVENT_FIELDS = ["id", "name", "start", "end", "location", "format", "type", "url", "register_by",
                "abstract_deadline", "cost", "employers", "goal", "confidence", "status",
                "first_seen", "notes"]
EVENT_STATUSES = ("upcoming", "interested", "going", "not-going", "attended", "past")
OUTREACH_FIELDS = ["id", "created", "company", "trigger", "trigger_url", "contact", "channel",
                   "draft", "status", "updated", "notes"]
OUTREACH_STATUSES = ("suggested", "sent", "replied", "meeting", "no-reply", "skipped")
NO_REPLY_AFTER_DAYS = 21


def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("events") or data.get("outreach") or []


def merge_events(tracker, path, today):
    rows = read_csv(tracker / "events.csv", EVENT_FIELDS)
    by_id = {r["id"]: r for r in rows}
    added = 0
    for item in load(path):
        name, start = text(item.get("name")), text(item.get("start"))
        if not name:
            continue
        eid = slug(name, start[:4])
        row = by_id.get(eid)
        if row is None:
            row = dict.fromkeys(EVENT_FIELDS, "")
            row.update(id=eid, status="upcoming", first_seen=today)
            rows.append(row)
            by_id[eid] = row
            added += 1
        for field in EVENT_FIELDS:
            if field in ("id", "status", "first_seen"):
                continue
            value = text(item.get(field))
            if value:
                row[field] = value
    age_events(rows, today)
    rows.sort(key=lambda r: (r["start"] or "9999", r["name"].lower()))
    write_csv(tracker / "events.csv", EVENT_FIELDS, rows)
    print(f"{added} new events, {len(rows)} in the calendar")


def age_events(rows, today):
    for row in rows:
        end = parse_date(row["end"]) or parse_date(row["start"])
        if end and end < parse_date(today) and row["status"] in ("upcoming", "interested", "not-going"):
            row["status"] = "past"


def add_outreach(tracker, path, today):
    rows = read_csv(tracker / "outreach.csv", OUTREACH_FIELDS)
    ids = {r["id"] for r in rows}
    added = 0
    for item in load(path):
        company, trigger = text(item.get("company")), text(item.get("trigger"))
        if not company or not text(item.get("draft")):
            continue
        oid = slug(company, trigger)[:80].rstrip("-")
        if oid in ids:
            continue
        row = dict.fromkeys(OUTREACH_FIELDS, "")
        row.update({k: text(item.get(k)) for k in OUTREACH_FIELDS if k in item})
        row.update(id=oid, created=today, status="suggested", updated=today)
        rows.append(row)
        ids.add(oid)
        added += 1
    write_csv(tracker / "outreach.csv", OUTREACH_FIELDS, rows)
    print(f"{added} outreach suggestions added")


def set_statuses(tracker, kind, changes, today):
    """changes: {id: status}. Returns the ids actually changed."""
    path, fields, allowed = ((tracker / "events.csv", EVENT_FIELDS, EVENT_STATUSES) if kind == "events"
                             else (tracker / "outreach.csv", OUTREACH_FIELDS, OUTREACH_STATUSES))
    rows = read_csv(path, fields)
    by_id = {r["id"]: r for r in rows}
    changed = []
    for rid, status in changes.items():
        row = by_id.get(rid)
        if row is None or status not in allowed or row["status"] == status:
            continue
        row["status"] = status
        if "updated" in row:
            row["updated"] = today
        changed.append(rid)
    if changed:
        write_csv(path, fields, rows)
    return changed


def people_search(company, contact):
    words = f"{company} {contact}".replace("(", " ").replace(")", " ")
    return "https://www.linkedin.com/search/results/people/?keywords=" + quote(" ".join(words.split()[:8]))


def summary(tracker, today):
    t = parse_date(today)
    events = read_csv(tracker / "events.csv", EVENT_FIELDS)
    outreach = read_csv(tracker / "outreach.csv", OUTREACH_FIELDS)
    age_events(events, today)

    def within(row, field, days):
        d = parse_date(row[field])
        return d is not None and 0 <= (d - t).days <= days

    stale = [r for r in outreach if r["status"] == "sent" and parse_date(r["updated"])
             and (t - parse_date(r["updated"])).days >= NO_REPLY_AFTER_DAYS]
    counts = {s: sum(r["status"] == s for r in outreach) for s in OUTREACH_STATUSES}
    return {
        "events_next_8_weeks": [r for r in events if within(r, "start", 56)
                                and r["status"] not in ("not-going", "past")],
        "event_deadlines_next_4_weeks": [
            {**r, "deadline": min(d for d in (r["register_by"], r["abstract_deadline"]) if d)}
            for r in events if r["status"] in ("upcoming", "interested", "going")
            and (within(r, "register_by", 28) or within(r, "abstract_deadline", 28))],
        "events_new": [r for r in events if r["first_seen"] == today],
        "outreach_waiting": [{**r, "linkedin_search": people_search(r["company"], r["contact"])}
                             for r in outreach if r["status"] == "suggested"],
        "outreach_follow_up": stale,
        "outreach_counts": counts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("merge-events", "add-outreach", "summary", "set"))
    parser.add_argument("args", nargs="*")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--tracker", type=Path, default=Path("tracker"))
    a = parser.parse_args()
    if a.action == "merge-events":
        merge_events(a.tracker, a.args[0], a.date)
    elif a.action == "add-outreach":
        add_outreach(a.tracker, a.args[0], a.date)
    elif a.action == "summary":
        json.dump(summary(a.tracker, a.date), sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        rid, status = a.args
        for kind in ("events", "outreach"):
            if set_statuses(a.tracker, kind, {rid: status}, a.date):
                return print(f"{kind}: {rid} -> {status}")
        sys.exit(f"no event or outreach item {rid!r} with a different status, or status {status!r} not allowed")


if __name__ == "__main__":
    main()
