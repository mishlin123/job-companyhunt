# Job company hunt

A watchlist of about 160 biotech and precision-fermentation employers for jobs starting after my MSc (finishing June 2027), plus a weekly Claude routine that scans them.

**To set the routine up on a computer**, ask Claude in the Claude desktop app to follow [`SETUP_LOCAL_ROUTINE.md`](SETUP_LOCAL_ROUTINE.md).

## The weekly routine

- **When:** every Monday at 7am, as a local routine in the Claude desktop app. It only runs while the app is open and the computer is awake. If the computer was asleep at 7am, the app does one catch-up run when it wakes.
- **What it does:**
  - checks every company in [`watchlist.md`](watchlist.md) for relevant open roles and recent news, reading careers pages and searching the web;
  - judges fit against [`profile.md`](profile.md);
  - compares with [`tracker/`](tracker/) so it can tell what's genuinely new.
- **How:**
  - Claude follows [`ROUTINE.md`](ROUTINE.md).
  - [`scripts/plan_batches.py`](scripts/plan_batches.py) splits the watchlist into batches of up to 20 rows for parallel research agents.
  - [`scripts/update_tracker.py`](scripts/update_tracker.py) does the bookkeeping.
  - [`.claude/settings.json`](.claude/settings.json) pre-approves the web, git and Python commands a run uses, so it doesn't stop to ask.
- **Results:**
  - `reports/YYYY-MM-DD.md`: the full weekly report.
  - `tracker/roles.csv`: every relevant role seen so far, with first-seen and last-seen dates and a status.
  - `tracker/news.csv`: news already reported, so it isn't repeated.
  - `tracker/pipeline.csv`: programmes that aren't open yet but will be (graduate intakes, open days), with when they open, how to prepare, and who to connect with on LinkedIn. The report's "Opening soon: prepare now" section comes from it.
  - `tracker/companies.csv`: the careers page found for each company.
  - A desktop notification when a run starts. The run's summary is in its session under **Scheduled** in the app's sidebar.

## The daily startup radar

- **When:** every morning at about 6:15–6:25 (the app adds a few minutes of jitter), as a local scheduled task ("Daily startup radar"), before the 7am scans. Like the other routines it runs only while the app is open and the Mac is awake, with one catch-up run on wake.
- **What it does:** looks for startups and small companies in NZ, Australia, the UK and Ireland that are likely to hire before they advertise: funding rounds, grants, spinouts and new sites (Google News and a dozen startup and trade-press feeds), and jobs posted only on LinkedIn (the LinkedIn guest feed for every company on the roster, plus a short keyword sweep). Claude judges each against [`profile.md`](profile.md), suggests a next move and drafts at most two outreach notes a day.
- **How:** Claude follows [`STARTUP_RADAR.md`](STARTUP_RADAR.md); [`scripts/startup_radar.py`](scripts/startup_radar.py) does the discovery and bookkeeping.
- **Results:** `reports/radar/YYYY-MM-DD.md`; `tracker/leads.csv` (the roster of companies being watched, seeded from the watchlist's startups); `tracker/radar_seen.csv` (so nothing is shown twice); drafts in `tracker/outreach.csv`.
- **Decisions:** `python3 scripts/startup_radar.py set "<company>" ignore|contacted|applied --note "..."`, or just tell Claude.

## Changing things

| To... | Do this |
|---|---|
| Add or remove a company | Edit `watchlist.md`; new rows and sections are picked up automatically |
| Add a programme to prepare for | Ask Claude, or add an `opening_soon` entry (or a row in `tracker/pipeline.csv`); the weekly scans then keep its dates fresh |
| Stop hearing about a role | Set its `status` to `ignore` in `tracker/roles.csv` |
| Record an application | Set its `status` to `applied` (still tracked, never re-flagged as new) |
| Change how fit is judged | Edit `profile.md` |
| Change the report or search strategy | Edit `ROUTINE.md` |
| Change the schedule, or run it now | The routine's page under **Routines** in the Claude desktop app |
