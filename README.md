# Job company hunt

A watchlist of about 125 biotech and precision-fermentation employers for jobs starting after my MSc (finishing June 2027), plus a weekly Claude routine that scans them.

## The weekly routine

- **When:** every Monday at about 7am New Zealand time. A full scan takes roughly 15–30 minutes.
- **What it does:** checks every company in [`watchlist.md`](watchlist.md) for relevant open roles and recent news, judges fit against [`profile.md`](profile.md), and compares with [`tracker/`](tracker/) so it can tell what's genuinely new.
- **How:** Claude follows [`ROUTINE.md`](ROUTINE.md), splitting the watchlist across ten parallel research agents. [`scripts/update_tracker.py`](scripts/update_tracker.py) does the bookkeeping.
- **Results:**
  - `reports/YYYY-MM-DD.md`: the full weekly report.
  - `tracker/roles.csv`: every relevant role seen so far, with first-seen and last-seen dates and a status.
  - `tracker/news.csv`: news already reported, so it isn't repeated.
  - `tracker/companies.csv`: the careers page found for each company.
  - A short summary by email and phone notification. Each run also appears as a session in Claude Code.

## Changing things

| To... | Do this |
|---|---|
| Add or remove a company | Edit `watchlist.md` |
| Stop hearing about a role | Set its `status` to `ignore` in `tracker/roles.csv` |
| Record an application | Set its `status` to `applied` (still tracked, never re-flagged as new) |
| Change how fit is judged | Edit `profile.md` |
| Change the report or search strategy | Edit `ROUTINE.md` |
| Change the schedule, or run it now | Your Routines in Claude Code, or ask Claude in a session |

## Known limitation

The cloud environment the routine runs in has **Trusted** network access, which blocks opening company careers pages directly. The routine therefore works from web search results. That finds most postings, but can miss roles that appear only on a careers page. To let it read careers pages too, change that environment's **Network access** to Full, or add the careers domains to its allowed list.
