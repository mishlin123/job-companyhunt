# Weekly scan playbook

The Monday routine follows this file step by step. It runs as a local routine in the Claude desktop app, in a clone of this repo on my computer, and commits its results to `main`. Work through everything in one go: your final message is the run's summary, so don't stop until the report is pushed.

Use `python3` in the commands below, or `python` if that's what this computer has.

## 0. Set up

1. `git checkout main && git pull origin main`. If the pull fails because of local edits, carry on with the files as they are and mention it in the final message.
2. The run date is today's local date as `YYYY-MM-DD` (`date +%F`). Below it is called DATE. If `reports/DATE.md` already exists, the scan has already run today: stop and say so.
3. `mkdir -p work` (git-ignored scratch space for this run). If an earlier run left `work/findings-*.json` or `work/summary.json` behind, move them into `work/prev-<their date>/` first, so they aren't mixed into this run.
4. Read `profile.md`, `watchlist.md`, `tracker/roles.csv`, `tracker/companies.csv`, and the newest file in `reports/` if there is one. That report's date is LAST (use "none" if there is no report yet).
5. If `tracker/roles.csv` has no data rows, this is the **baseline run**: every relevant role found counts as new. Say so at the top of the report.

## 1. Research with parallel subagents

Run `python3 scripts/plan_batches.py`. It splits the watchlist's tables into batches of at most 20 rows and prints one line per batch, naming the `watchlist.md` sections that batch covers. A large section can be split into row ranges such as `14a. ... (rows 1–12)`: those count only that section's table rows, header excluded. Rows of "19. Market sweeps" appear as `(row N)` and get batches of their own, at most two sweeps each, because each sweep covers a whole job market.

**Search budget.** WebSearch is capped at about 200 calls per run, shared by all subagents. WebFetch and `curl` (careers pages, ATS job APIs, the LinkedIn guest feed) don't count. Give each company batch a budget of 6 searches and each sweep batch 12. With 24 batches that comes to about 180. If the batch count changes a lot, rescale so the total stays under 180.

Launch one general-purpose subagent per batch, all **in a single message**, each with `run_in_background: false`, so they run concurrently and you wait for all of them. Subagents share this working directory, so point them at files instead of pasting the files into their prompts. Give each one this prompt, filled in:

> You are batch N of the weekly job scan. The repo is at REPO_PATH. Read the "Research brief" section of `ROUTINE.md` and follow it. Then read `profile.md`, these parts of `watchlist.md`: SECTIONS, and the rows for your companies in `tracker/roles.csv` and `tracker/companies.csv`. Today is DATE; the last report was LAST. Your WebSearch budget is BUDGET calls: spend it where WebFetch can't answer, and stop searching once it is used. Research every row in your part of the watchlist and write `work/findings-N.json` exactly as the brief specifies. Reply in at most five lines: companies checked, roles found by fit, anything that went wrong.

When they have all returned, check that each `work/findings-N.json` exists and parses (`python3 -m json.tool work/findings-N.json`). Re-run a failed batch once. If it fails again, carry on without it and say so in the report.

## Research brief (for subagents)

For **each** row in your part of the watchlist:

1. **Careers page.** Use the `careers_url` in `tracker/companies.csv` if there is one. Otherwise find the company's careers page or job board, often hosted on an applicant-tracking system (Greenhouse, Lever, Ashby, Teamtailor, Workable, Personio, Recruitee, SmartRecruiters, Breezy, Rippling, Workday).
2. **Read it.** Fetch the careers page with WebFetch and note the relevant open roles it lists. Pages that load their jobs with JavaScript can come back empty: try the ATS's public job API (e.g. `boards-api.greenhouse.io/v1/boards/<slug>/jobs`, `api.lever.co/v0/postings/<slug>`, `api.smartrecruiters.com/v1/companies/<id>/postings`, Workday's `/wday/cxs/.../jobs`) or the LinkedIn guest feed (`https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?f_C=<numeric company id>&location=Worldwide&start=0`, empty means no postings) before spending a WebSearch. If WebFetch is blocked outright (`EGRESS_BLOCKED`, which only happens in restricted cloud environments), don't use it again this run.
3. **Search for roles.** Within your budget, run WebSearch queries to catch roles the careers page didn't show, built from the company, location and roles to watch. For example: `"<Company>" careers fermentation scientist`, `"<Company>" jobs <city> research associate`, `"<Company>" graduate programme 2027 <country>`. Use `allowed_domains` to aim a query at the company's careers or ATS domain, or at job boards such as linkedin.com, seek.co.nz, seek.com.au, uniroles.com.au, au.gradconnection.com, prosple.com, indeed.com, irishjobs.ie, jobs.ie, gradireland.com, targetjobs.co.uk, prospects.ac.uk, jobteaser.com, thehub.io, jobindex.dk, stepstone.de, welcometothejungle.com, mycareersfuture.gov.sg, foodimpactcareers.com, climatebase.org, wellfound.com and euraxess.ec.europa.eu.
   For big multinationals (Pfizer, Amgen, AstraZeneca, GSK, MSD, Sanofi, Eli Lilly, BMS, Regeneron, Thermo Fisher, Lonza, Takeda, Roche, Gilead, Grifols, Abbott, J&J, Novonesis, ADM, CSL, Kerry, IFF, dsm-firmenich, Corbion, Lesaffre, Lallemand, AB Enzymes, Syngenta, Ferring, Croda, GenScript, Agilent, Accord Healthcare), look only for the programmes, sites and role types named in the watchlist.
4. **News.** Within your budget, search for news, favouring rows tagged High and anything with a live role, published since LAST (the last 14 days on a baseline run): funding, layoffs or closures, new plants or scale-up, regulatory approvals, partnerships or acquisitions, leadership changes, graduate-intake announcements, hiring pushes. Skip older items and evergreen pages.
5. **Sponsorship.** For roles outside NZ, Australia, the UK and Ireland, say in `notes` whether the employer sponsors visas: what the posting says, or the evidence recorded in the watchlist row (e.g. "IND recognised sponsor", "recent H-1B filings for RAs"). If neither says, write "sponsorship unknown". Follow the work-rights rules in `profile.md`.
6. **Fit.** Rate each relevant role `strong`, `possible` or `signal` using "How to judge fit" in `profile.md`. Leave out anything below `signal`.
7. **Tracker.** If a role is already in `tracker/roles.csv`, put that row's `id` in your entry, even if the title or link has changed slightly. Don't list a tracked role you can't find again; the script marks it.
8. **Accuracy.**
   - Every role needs a URL. Prefer the company's own posting over aggregators.
   - Never invent roles, dates, salaries or requirements. If a detail comes only from a search snippet, keep it but add "(unverified)" to its notes.
   - Leave out postings whose closing date has passed, or that look stale (older than about 60 days with no sign they're still open).
   - If one posting is advertised for several sites, make it one entry and list the locations.

### Sweep rows (section 19 of the watchlist)

Rows in "19. Market sweeps" name a market, not a company. For each one, search the job boards and sources in its row for relevant roles at **any** employer, using the roles in its "What to look for" column. Then:

The LinkedIn guest feed takes role keywords and a location, which is the cheapest way to sweep a market (it doesn't count against the WebSearch budget): `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=microbiologist&location=New%20Zealand&f_TPR=r1209600&start=0` lists postings from the last 14 days; page with `start=10`, `20` and so on. Run it for each role family in your row. SEEK often refuses automated fetches, so reach it through WebSearch with `allowed_domains` when the budget allows. Check each posting's employer against the watchlist before reporting it.

- Report every relevant role at an employer that is **not** a first-column name anywhere in `watchlist.md`; that employer's own row already covers it otherwise. Use the employer's real name as `roles[].company` and add it to `companies` with `checked: true` and a note such as "found via sweep: Australia – Victoria and Tasmania".
- Re-check the open roles in `tracker/roles.csv` whose company isn't a watchlist name and whose location falls in your sweep. This command lists them:
  `python3 -c "import csv,re;w={l.split('|')[1].strip() for l in open('watchlist.md') if l.startswith('|')};[print(r['id'],'|',r['company'],'|',r['role'],'|',r['location'],'|',r['url']) for r in csv.DictReader(open('tracker/roles.csv')) if r['status']=='open' and r['company'] not in w]"`
  Include each one that is still open, with its `id`. List its company in `companies` either way, so the tracker can age out roles that have gone.
- Add the sweep row's own name to `companies` too (`checked: true`, with a one-line note on the boards covered).
- Use `news` only for news about employers you report roles for.
- In your reply, name any employer with two or more relevant roles, or a `strong` one, as a candidate for the watchlist.

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

- `companies`: one entry for every row name in your part of the watchlist, including rows where nothing was found. Use the name exactly as it appears in the first column of `watchlist.md`. Set `checked: false` only if you couldn't search that company at all.
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
Optional, at most five: employers found by the market sweeps that deserve their own row (two or more relevant roles, or a `strong` one), other companies worth adding, or rows that look obsolete (acquired, shut down, programme discontinued).

## Coverage
Companies checked, failed or not reported; which market sweeps ran and how many off-watchlist employers they found; problems such as careers pages that wouldn't load, searches that failed, or batches that ran out of search budget.
```

## 4. Commit and push to `main`

```
git add reports/ tracker/
git commit -m "Weekly job scan DATE"
git push origin main
```

- A run changes only `reports/` and `tracker/`. Never edit `watchlist.md`, `profile.md`, `ROUTINE.md`, `scripts/` or `.claude/`; suggest changes in the report instead.
- If the push is rejected because `main` has moved on, run `git pull --rebase origin main` and push again.
- On network errors, retry up to four times, waiting 2, 4, 8 and 16 seconds.
- If the push still fails (for example, GitHub credentials aren't set up on this computer), leave the commit in place and say at the top of your final message that the results are saved on this computer but weren't pushed, and why.

## 5. Final message

Your last message is the run's summary, the first thing I read when I open the run from its notification. Keep it under about 25 lines:

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
