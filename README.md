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
  - `tracker/companies.csv`: the careers page found for each company.
  - A desktop notification when a run starts. The run's summary is in its session under **Scheduled** in the app's sidebar.

## Changing things

| To... | Do this |
|---|---|
| Add or remove a company | Edit `watchlist.md`; new rows and sections are picked up automatically |
| Stop hearing about a role | Set its `status` to `ignore` in `tracker/roles.csv` |
| Record an application | Set its `status` to `applied` (still tracked, never re-flagged as new) |
| Change how fit is judged | Edit `profile.md` |
| Change the report or search strategy | Edit `ROUTINE.md` |
| Change the schedule, or run it now | The routine's page under **Routines** in the Claude desktop app |
