# Weekly scan playbook

The Monday routine follows this file step by step. It runs in a fresh Claude Code session with this repo checked out, and commits its results to `main`. Work through everything in one go: the run's final message is emailed, so don't stop until the report is pushed.

## 0. Set up

1. `git checkout main && git pull origin main`
2. The run date is today's date in New Zealand: `TZ=Pacific/Auckland date +%F`. Below it is called DATE.
3. `mkdir -p work` (git-ignored scratch space for this run).
4. Read `profile.md`, `watchlist.md`, `tracker/roles.csv`, `tracker/companies.csv`, and the newest file in `reports/` if there is one. That report's date is LAST (use "none" if there is no report yet).
5. If `tracker/roles.csv` has no data rows, this is the **baseline run**: every relevant role found counts as new. Say so at the top of the report.

## 1. Research with ten parallel subagents

Launch ten general-purpose subagents **in a single message**, each with `run_in_background: false`, so they run concurrently and you wait for all of them. Each one covers these `watchlist.md` sections:

| Batch | Sections |
|---|---|
| 1 | 1. New Zealand |
| 2 | 2. Australia |
| 3 | 3. Ireland |
| 4 | 4. United Kingdom, 5. Belgium, 17. Switzerland and Spain |
| 5 | 6. Netherlands, 7. Germany, 11. France |
| 6 | 8. Denmark, 9. Sweden, 10. Finland |
| 7 | 12. Israel, 14a. United States: precision fermentation and fermentation platforms |
| 8 | 13. Canada, 14b. United States: synbio, strain/enzyme engineering and industrial chemicals |
| 9 | 14c. United States: large companies and graduate programmes, 16. Other international 2027 graduate programmes |
| 10 | 15. Singapore |

Subagents share this working directory, so point them at files instead of pasting the files into their prompts. Give each one this prompt, filled in:

> You are batch N of the weekly job scan. The repo is at REPO_PATH. Read the "Research brief" section of `ROUTINE.md` and follow it. Then read `profile.md`, sections SECTIONS of `watchlist.md`, and the rows for your companies in `tracker/roles.csv` and `tracker/companies.csv`. Today is DATE; the last report was LAST. Research every row in your sections and write `work/findings-N.json` exactly as the brief specifies. Reply in at most five lines: companies checked, roles found by fit, anything that went wrong.

When they have all returned, check that each `work/findings-N.json` exists and parses (`python3 -m json.tool work/findings-N.json`). Re-run a failed batch once. If it fails again, carry on without it and say so in the report.

## Research brief (for subagents)

For **each** row in your sections:

1. **Careers page.** Use the `careers_url` in `tracker/companies.csv` if there is one. Otherwise find the company's careers page or job board, often hosted on an applicant-tracking system (Greenhouse, Lever, Ashby, Teamtailor, Workable, Personio, Recruitee, SmartRecruiters, Workday).
2. **WebFetch, once.** Try WebFetch on your first careers page. The environment's network policy may block it (`EGRESS_BLOCKED`). If it does, don't use WebFetch again this run; work from WebSearch alone.
3. **Open roles.** Run one to three WebSearch queries per row, built from the company, location and roles to watch. For example: `"<Company>" careers fermentation scientist`, `"<Company>" jobs <city> research associate`, `"<Company>" graduate programme 2027 <country>`. Use `allowed_domains` to aim a query at the company's careers or ATS domain, or at job boards such as linkedin.com, seek.co.nz, seek.com.au, indeed.com, irishjobs.ie, jobs.ie, gradireland.com, targetjobs.co.uk, prospects.ac.uk, jobteaser.com, thehub.io, jobindex.dk, stepstone.de, welcometothejungle.com, mycareersfuture.gov.sg, foodimpactcareers.com, climatebase.org, wellfound.com and euraxess.ec.europa.eu.
   For big multinationals (Pfizer, Amgen, AstraZeneca, GSK, MSD, Sanofi, Eli Lilly, BMS, Regeneron, Thermo Fisher, Lonza, Takeda, Roche, Gilead, Grifols, Abbott, J&J, Novonesis, ADM, CSL, Kerry, IFF, dsm-firmenich, Corbion, Lesaffre, Lallemand, AB Enzymes, Syngenta, Ferring), look only for the programmes, sites and role types named in the watchlist.
4. **News.** Run one or two searches for news published since LAST (the last 14 days on a baseline run): funding, layoffs or closures, new plants or scale-up, regulatory approvals, partnerships or acquisitions, leadership changes, graduate-intake announcements, hiring pushes. Skip older items and evergreen pages.
5. **Fit.** Rate each relevant role `strong`, `possible` or `signal` using "How to judge fit" in `profile.md`. Leave out anything below `signal`.
6. **Tracker.** If a role is already in `tracker/roles.csv`, put that row's `id` in your entry, even if the title or link has changed slightly. Don't list a tracked role you can't find again; the script marks it.
7. **Accuracy.**
   - Every role needs a URL. Prefer the company's own posting over aggregators.
   - Never invent roles, dates, salaries or requirements. If a detail comes only from a search snippet, keep it but add "(unverified)" to its notes.
   - Leave out postings whose closing date has passed, or that look stale (older than about 60 days with no sign they're still open).
   - If one posting is advertised for several sites, make it one entry and list the locations.

Write `work/findings-N.json`:

```json
{
  "batch": 3,
  "companies": [
    {"name": "Kerry", "careers_url": "https://...", "checked": true,
     "notes": "optional one-liner, e.g. speculative CV route open"}
  ],
  "roles": [
    {"id": "", "company": "Kerry", "role": "Graduate Programme 2027 – R&D (Biotech Solutions)",
     "location": "Naas / Carrigaline, Ireland", "url": "https://...", "fit": "strong",
     "closes": "2026-11-30", "starts": "Sep 2027", "notes": "why it fits; caveats"}
  ],
  "news": [
    {"company": "Vivici", "date": "2026-09-21", "headline": "...", "url": "https://...",
     "why": "one line on why it matters for the job hunt"}
  ]
}
```

- `companies`: one entry for every row name in your sections, including rows where nothing was found. Use the name exactly as it appears in the first column of `watchlist.md`. Set `checked: false` only if you couldn't search that company at all.
- `roles[].company`: use the same watchlist name.
- `closes`: `YYYY-MM-DD` if known, otherwise `""`. `starts`: free text, or `""`.

## 2. Update the tracker

```
python3 scripts/update_tracker.py --date DATE work/findings-*.json > work/summary.json
```

This updates `tracker/roles.csv`, `tracker/companies.csv` and `tracker/news.csv`. It writes a JSON summary with these keys: `baseline`, `new_roles`, `still_open`, `applied`, `no_longer_found`, `closed`, `deadlines_soon`, `new_news`, `companies_checked`, `companies_failed`, `companies_not_reported` and `problems`.

If it exits with an error, fix the findings JSON (not the script) and run it again. Never hand-edit the CSVs.

## 3. Write `reports/DATE.md`

Write the report from `work/summary.json` and the subagents' notes. Keep it skimmable on a phone: short lines, and a link on every role and news item.

```markdown
# Weekly job scan — Monday 28 September 2026

(Baseline run: everything currently open is listed as new.)   <- baseline run only

**TL;DR**: two or three sentences. Counts of new roles by fit, the most urgent deadline, and the single most important thing to do this week.

## Suggested actions
Up to five concrete, prioritised actions, e.g. "Apply to X (closes 30 Nov)" or "Speculative note to Y: just raised a Series B and is scaling fermentation". Omit the section if nothing warrants action.

## New opportunities
One table per fit level, strong first: Company | Role | Location | Starts / closes | Why it fits (caveats) | Link

## Closing in the next 6 weeks
Company | Role | Closes | Link

## Company news
- **Company** (date): headline. Why it matters. [source](url)

## Still open from earlier weeks
- Company: Role (fit, first seen DATE) [link](url)

## No longer found or closed
- Company: Role (last seen DATE)

## Watchlist suggestions
Optional, at most three: companies worth adding (e.g. found while searching), or rows that look obsolete (acquired, shut down, programme discontinued).

## Coverage
Companies checked, failed or not reported; problems such as WebFetch being blocked or searches failing.
```

## 4. Commit and push to `main`

```
git add reports/ tracker/
git commit -m "Weekly job scan DATE"
git push origin main
```

- A run changes only `reports/` and `tracker/`. Never edit `watchlist.md`, `profile.md`, `ROUTINE.md` or `scripts/`; suggest changes in the report instead.
- If the push is rejected because `main` has moved on, run `git pull --rebase origin main` and push again.
- On network errors, retry up to four times, waiting 2, 4, 8 and 16 seconds.
- If pushing to `main` is refused for permission reasons, push the commit to your session's own branch instead, open a draft pull request titled "Weekly job scan DATE", and say so in the final message.

## 5. Final message

Your last message is emailed and sent as a phone notification, so keep it under about 25 lines:

```
Weekly job scan — Mon 28 Sep 2026
N new roles (X strong, Y possible, Z signal) · K deadlines in the next 6 weeks · J news items

Top picks
- Company — Role (Location) — closes DATE — link        (up to 5, strongest first)

Closing soon
- Company — Role — DATE — link

News
- Company: headline — link                               (up to 5)

Full report: https://github.com/mishlin123/job-companyhunt/blob/main/reports/DATE.md
```

If nothing new turned up, say so in one line, and still list deadlines and news.
