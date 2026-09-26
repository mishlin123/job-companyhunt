#!/usr/bin/env python3
"""Split watchlist.md into research batches for the weekly scan.

Usage:
    python3 scripts/plan_batches.py [--max-rows 20] [--watchlist watchlist.md]

Every table in watchlist.md sits under a numbered heading ("## 4. United
Kingdom", "### 14a. ..."). Sections are packed into as few batches as possible
with at most --max-rows table rows each, largest first, and a section bigger
than that is split into row ranges. Prints one line per batch, so new sections
and rows are picked up without editing ROUTINE.md.
"""

import argparse
import math
import re
import sys
from pathlib import Path

HEADING = re.compile(r"#{2,3} (\d+[a-z]?)\. (.+)")


def sections(path):
    """[(index, label, rows)] for every numbered section that contains table rows."""
    found, current, in_table = [], None, False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        match = HEADING.fullmatch(line)
        if match:
            current = [len(found), f"{match.group(1)}. {match.group(2).strip()}", 0]
            found.append(current)
            in_table = False
        elif line.startswith("|") and current is not None:
            first = line.strip("|").split("|")[0].strip()
            if not in_table:
                in_table = True  # header row
            elif first and not set(first) <= set("-: "):  # skip the separator row
                current[2] += 1
        else:
            in_table = False
    return [tuple(s) for s in found if s[2]]


def pieces(secs, max_rows):
    """Split any section with more than max_rows rows into near-equal row ranges."""
    for index, label, rows in secs:
        parts = math.ceil(rows / max_rows)
        if parts == 1:
            yield index, label, rows
            continue
        size = math.ceil(rows / parts)
        for start in range(1, rows + 1, size):
            end = min(start + size - 1, rows)
            yield index, f"{label} (rows {start}–{end})", end - start + 1


def pack(items, max_rows):
    """First-fit decreasing: biggest pieces first, each into the first batch with room."""
    batches = []
    for item in sorted(items, key=lambda i: (-i[2], i[0])):
        batch = next((b for b in batches if sum(i[2] for i in b) + item[2] <= max_rows), None)
        if batch is None:
            batch = []
            batches.append(batch)
        batch.append(item)
    for batch in batches:
        batch.sort(key=lambda i: i[0])  # file order within a batch
    return sorted(batches, key=lambda b: b[0][0])


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-rows", type=int, default=20, help="table rows per batch")
    parser.add_argument("--watchlist", type=Path, default=Path("watchlist.md"))
    args = parser.parse_args()
    if args.max_rows < 1:
        sys.exit("--max-rows must be at least 1")
    if not args.watchlist.exists():
        sys.exit(f"{args.watchlist} not found")

    batches = pack(pieces(sections(args.watchlist), args.max_rows), args.max_rows)
    total = sum(i[2] for b in batches for i in b)
    print(f"{len(batches)} batches, {total} rows, at most {args.max_rows} rows each")
    for n, batch in enumerate(batches, 1):
        rows = sum(i[2] for i in batch)
        print(f"batch {n} ({rows} rows): " + "; ".join(i[1] for i in batch))


if __name__ == "__main__":
    main()
