# Weekly scan playbook

Two scheduled routines follow this file step by step. Both run as local routines in the Claude desktop app, in a clone of this repo on my computer, and commit their results to `main`.

| Run | When | Watchlist sections | SECTION_FLAGS | Report file (REPORT) | Report title |
|---|---|---|---|---|---|
| **Core scan** | Monday | everything except 20 and 21 (fermentation, bioprocess and biotech employers by country, and the market sweeps) | `--exclude 20,21` | `reports/DATE.md` | Weekly job scan |
| **Career-routes scan** | Thursday | only 20 and 21 (alternative career routes and adjacent industries) | `--only 20,21` | `reports/DATE-careers.md` | Career routes scan |

The scheduled task's prompt says which run it is. If it doesn't, use the core scan on Monday to Wednesday and the career-routes scan on Thursday to Sunday. Below, RUN, SECTION_FLAGS and REPORT mean the values in this table. Work through everything in one go: your final message is the run's summary, so don't stop until the report is pushed.

Use `python3` in the commands below, or `python` if that's what this computer has.

## 0. Set up

1. `git checkout main && git pull origin main`. If the pull fails because of local edits, carry on with the files as they are and mention it in the final message.
2. The run date is today's local date as `YYYY-MM-DD` (`date +%F`). Below it is called DATE. If REPORT already exists, this run has already happened today: stop and say so.
3. `mkdir -p work` (git-ignored scratch space for this run). If an earlier run left `work/findings-*.json` or `work/summary.json` behind, move them into `work/prev-<their date>/` first, so they aren't mixed into this run. Move any `work/seek-*.txt` there too.
4. Read `profile.md`, `watchlist.md`, `tracker/roles.csv`, `tracker/companies.csv`, `tracker/decisions.csv`, and the newest earlier report of the same run type in `reports/` (core: `reports/YYYY-MM-DD.md` or `YYYY-MM-DD-anz.md`; career routes: any `reports/YYYY-MM-DD-careers*.md` or `-desk-careers.md`). That report's date is LAST (use "none" if there is none).
5. **Pull in my clicks from the job board** (https://claude.ai/artifact/8gTgrwWPajJdY8mfDqihFy) before anything reads the tracker: read its database with the `ArtifactData` tool, `action: "list"`, `collection: "decisions"`, `query: {limit: 1000}`, `out_dir: "work/board-clicks"`, then run `python3 scripts/board.py import work/board-clicks/decisions`. It appends only decisions that changed to `tracker/decisions.csv` and updates `tracker/roles.csv`. If the read fails, carry on and mention it in the report's Coverage section.
6. If `tracker/roles.csv` has no data rows, this is the **baseline run**: every relevant role found counts as new. Say so at the top of the report.

## 1. Research with parallel subagents

**SEEK first.** Run `python3 scripts/seek_search.py --site AU > work/seek-AU.txt` and `python3 scripts/seek_search.py --site NZ > work/seek-NZ.txt` (about a minute each; no WebSearch calls). SEEK is where Australian universities, state health and agriculture departments, research institutes and most smaller employers advertise scientist and technician roles. The script pulls every listing from the last 14 days in SEEK's Science & Technology, Research & Fellowships and Clinical/Medical Research categories, adds keyword searches across all categories, filters titles to the role families in `profile.md`, and tags each employer as `university`, `government` or `institute`. Each line reads `listed | type | employer | title | location | url`. If either file comes out empty or with only its header line, re-run it once and mention it in the report's Coverage section.

Run `python3 scripts/plan_batches.py SECTION_FLAGS`. It splits the watchlist's tables into batches of at most 20 rows and prints one line per batch, naming the `watchlist.md` sections that batch covers. A large section can be split into row ranges such as `14a. ... (rows 1–12)`: those count only that section's table rows, header excluded. Rows of "19. Market sweeps" appear as `(row N)` and get batches of their own, at most two sweeps each, because each sweep covers a whole job market.

**Search budget.** WebSearch is capped at about 200 calls per run, shared by all subagents. WebFetch and `curl` (careers pages, ATS job APIs, the LinkedIn guest feed) don't count. Core scan: give each company batch 6 searches and each sweep batch 11; with 24 batches (18 company, 6 sweep) that comes to about 174. Career-routes scan: give each batch 7; with 23 batches that comes to about 161. Batches should lean on careers pages, ATS APIs, the SEEK files and the LinkedIn guest feed, which cost nothing. Many batches hit the LinkedIn guest feed at once, so pause and retry on HTTP 429 rather than giving up. If the batch count changes a lot, rescale so the total stays under 180.

Launch one general-purpose subagent per batch, all **in a single message**, each with `run_in_background: false`, so they run concurrently and you wait for all of them. Subagents share this working directory, so point them at files instead of pasting the files into their prompts. Give each one this prompt, filled in:

> You are batch N of the weekly job scan. The repo is at REPO_PATH. Read the "Research brief" section of `ROUTINE.md` and follow it. Then read `profile.md`, these parts of `watchlist.md`: SECTIONS, and the rows for your companies in `tracker/roles.csv`, `tracker/companies.csv` and `tracker/decisions.csv`. Today is DATE; the last report was LAST. Your WebSearch budget is BUDGET calls: spend it where WebFetch can't answer, and stop searching once it is used. Research every row in your part of the watchlist and write `work/findings-N.json` exactly as the brief specifies. Reply in at most five lines: companies checked, roles found by fit, anything that went wrong.

When they have all returned, check that each `work/findings-N.json` exists and parses (`python3 -m json.tool work/findings-N.json`). Re-run a failed batch once. If it fails again, carry on without it and say so in the report.

## Research brief (for subagents)

For **each** row in your part of the watchlist:

1. **Careers page.** Use the `careers_url` in `tracker/companies.csv` if there is one. Otherwise find the company's careers page or job board, often hosted on an applicant-tracking system (Greenhouse, Lever, Ashby, Teamtailor, Workable, Personio, Recruitee, SmartRecruiters, Breezy, Rippling, Workday).
2. **Read it.** Fetch the careers page with WebFetch and note the relevant open roles it lists. Pages that load their jobs with JavaScript can come back empty: try the ATS's public job API (e.g. `boards-api.greenhouse.io/v1/boards/<slug>/jobs`, `api.lever.co/v0/postings/<slug>`, `api.smartrecruiters.com/v1/companies/<id>/postings`, Workday's `/wday/cxs/.../jobs`) or the LinkedIn guest feed (`https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?f_C=<numeric company id>&location=Worldwide&start=0`, empty means no postings) before spending a WebSearch. If WebFetch is blocked outright (`EGRESS_BLOCKED`, which only happens in restricted cloud environments), don't use it again this run.
3. **SEEK (Australia and NZ rows).** `grep -i "<company>" work/seek-AU.txt work/seek-NZ.txt` (try a short form of the name too, e.g. `treidlia`, `la trobe`). Treat each hit as a posting to judge like any other; the URL is the SEEK job page. Smaller companies often advertise only on SEEK, so an empty careers page doesn't mean no vacancies.
4. **Search for roles.** Within your budget, run WebSearch queries to catch roles the careers page didn't show, built from the company, location and roles to watch. For example: `"<Company>" careers fermentation scientist`, `"<Company>" jobs <city> research associate`, `"<Company>" graduate programme 2027 <country>`. Use `allowed_domains` to aim a query at the company's careers or ATS domain, or at job boards such as linkedin.com, seek.co.nz, seek.com.au, uniroles.com.au, au.gradconnection.com, prosple.com, indeed.com, irishjobs.ie, jobs.ie, gradireland.com, targetjobs.co.uk, prospects.ac.uk, jobteaser.com, thehub.io, jobindex.dk, stepstone.de, welcometothejungle.com, mycareersfuture.gov.sg, foodimpactcareers.com, climatebase.org, wellfound.com and euraxess.ec.europa.eu.
   For big multinationals (Pfizer, Amgen, AstraZeneca, GSK, MSD, Sanofi, Eli Lilly, BMS, Regeneron, Thermo Fisher, Lonza, Takeda, Roche, Gilead, Grifols, Abbott, J&J, Novonesis, ADM, CSL, Kerry, IFF, dsm-firmenich, Corbion, Lesaffre, Lallemand, AB Enzymes, Syngenta, Ferring, Croda, GenScript, Agilent, Accord Healthcare, Zoetis, Boehringer Ingelheim, Elanco, Nestlé, Reckitt, FrieslandCampina, Givaudan, Symrise, Clariant, Evonik, Sartorius, Cytiva, Eppendorf, Merck, Repligen, Jacobs, Arcadis, Deloitte, EY, KPMG, PwC, Grant Thornton, BDO, RSM, IQVIA, ICON, Parexel, Fortrea, Clarivate, Springer Nature, Elsevier, SGS, Bureau Veritas, Intertek, BSI), look only for the programmes, sites and role types named in the watchlist.
   **Career-route rows (watchlist sections 20–21).** Patent firms, patent offices, government schemes and regulators, C&Q and R&D tax consultancies, medcomms agencies, strategy consultancies, publishers and equipment makers often run one yearly trainee or graduate intake rather than standing vacancies. For each, find the current intake page: report it as a role if it is open (with its deadline and start date), and if it isn't open yet, say in that company's `notes` when it usually opens and for which start, so the report can flag it. For government employers, check citizenship or nationality rules (UK Civil Service: UK nationals are fine; Australian Public Service: usually Australian citizens only).
5. **News.** Within your budget, search for news, favouring rows tagged High and anything with a live role, published since LAST (the last 14 days on a baseline run): funding, layoffs or closures, new plants or scale-up, regulatory approvals, partnerships or acquisitions, leadership changes, graduate-intake announcements, hiring pushes. Skip older items and evergreen pages.
6. **Sponsorship.** For roles outside NZ, Australia, the UK and Ireland, say in `notes` whether the employer sponsors visas: what the posting says, or the evidence recorded in the watchlist row (e.g. "IND recognised sponsor", "recent H-1B filings for RAs"). If neither says, write "sponsorship unknown". Follow the work-rights rules in `profile.md`.
7. **Fit.** Rate each relevant role `strong`, `possible` or `signal` using "How to judge fit" in `profile.md`. Leave out anything below `signal`.
8. **Tracker.** If a role is already in `tracker/roles.csv`, put that row's `id` in your entry, even if the title or link has changed slightly. Don't list a tracked role you can't find again; the script marks it.
   - **My decisions** (`tracker/decisions.csv`, also shown as the role's `status`). Roles marked `ineligible`, `off-path` or `ignore` are settled: don't re-check, re-rate or list them. A decision with a company but no `role_id` rules out that whole company: list it in `companies` with `checked: true` and the note "ruled out in decisions.csv", and skip it. Roles marked `applied` or `interviewing`: do re-check them and list them (with their `id`) if still open, noting any change such as a new closing date or the posting disappearing.
   - **`off-path` roles teach fit.** They are roles I judged wrong for my skills or direction. Before rating, look at the `off-path` roles in `tracker/roles.csv` (any company): rate new roles that closely resemble them (same kind of work, same seniority) one level lower, and leave them out if they would only be `signal`.
   - **Ruled out in `profile.md`**: leave out any role that hits a rule in its "Ruled out" list.
9. **Accuracy.**
   - Every role needs a URL. Prefer the company's own posting over aggregators.
   - Never invent roles, dates, salaries or requirements. If a detail comes only from a search snippet, keep it but add "(unverified)" to its notes.
   - Leave out postings whose closing date has passed, or that look stale (older than about 60 days with no sign they're still open).
   - If one posting is advertised for several sites, make it one entry and list the locations.

### Sweep rows (section 19 of the watchlist)

Rows in "19. Market sweeps" name a market, not a company. For each one, search the job boards and sources in its row for relevant roles at **any** employer, using the roles in its "What to look for" column. Then:

The LinkedIn guest feed takes role keywords and a location, which is the cheapest way to sweep a market (it doesn't count against the WebSearch budget): `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=microbiologist&location=New%20Zealand&f_TPR=r1209600&start=0` lists postings from the last 14 days; page with `start=10`, `20` and so on. Run it for each role family in your row. For Australia and NZ sweeps, start from `work/seek-AU.txt` / `work/seek-NZ.txt` (filter by state with `grep`, e.g. `grep " VIC |"` or `grep -E "(VIC|TAS) \|"`): read every line for your region, open the promising postings with `curl -s -A "Mozilla/5.0" https://www.seek.com.au/api/jobsearch/v5/search?...` or WebFetch on the job URL if you need detail, and give university, government and institute listings particular attention, since they hire most entry-level scientists. Check whether government posts need Australian citizenship or PR (NZ citizens are eligible when the posting accepts "Australian or New Zealand citizens" or "the right to work in Australia"). For extra SEEK searches beyond the file, the same API takes `keywords`, `where` (e.g. `All Victoria VIC`), `classification` and `daterange`; see `scripts/seek_search.py`. Check each posting's employer against the watchlist before reporting it.

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
python3 scripts/update_tracker.py --date DATE --exact SECTION_FLAGS work/findings-*.json > work/summary.json
```

`--exact` ages out only roles whose company name exactly matches one checked this run, and limits the still-open, applied and deadline lists to those companies. That keeps the two runs from marking each other's roles as gone when employers share a name (e.g. Thermo Fisher's site rows and its field-application row), so batches must use the exact watchlist names.

This updates `tracker/roles.csv`, `tracker/companies.csv` and `tracker/news.csv`. It writes a JSON summary with these keys: `baseline`, `new_roles`, `still_open`, `applied`, `no_longer_found`, `closed`, `deadlines_soon`, `new_news`, `companies_checked`, `companies_failed`, `companies_not_reported` and `problems`.

If it exits with an error, fix the findings JSON (not the script) and run it again. Never hand-edit the CSVs. My own decisions go in `tracker/decisions.csv` through `scripts/mark.py` (see the next section).

### Refresh the job board

Run `python3 scripts/board.py export` (writes `work/board/roles.json`), then republish the board with the `Artifact` tool: `file_path: "board/index.html"`, `url: "https://claude.ai/artifact/8gTgrwWPajJdY8mfDqihFy"`, `files: {"roles.json": "work/board/roles.json"}`, and no `capabilities` or `icon` (both are kept). The board's saved clicks live in its database and survive the republish. If the publish fails, say so in Coverage.

## 3. Write REPORT

Write the report from `work/summary.json` and the subagents' notes. Keep it skimmable on a phone: short lines, and a link on every role and news item.

```markdown
# Weekly job scan — Monday 28 September 2026      <- career-routes scan: "# Career routes scan — Thursday 1 October 2026"

(Baseline run: everything currently open is listed as new.)   <- baseline run only

Mark roles on the [job board](https://claude.ai/artifact/8gTgrwWPajJdY8mfDqihFy)

**TL;DR**: two or three sentences. Counts of new roles by fit, the most urgent deadline, and the single most important thing to do this week.

## Suggested actions
Up to five concrete, prioritised actions, e.g. "Apply to X (closes 30 Nov)" or "Speculative note to Y: just raised a Series B and is scaling fermentation". Omit the section if nothing warrants action.

## New opportunities
One table per fit level, strong first: Company | Role | Location | Starts / closes | Why it fits (caveats) | Link

## Closing in the next 6 weeks
Company | Role | Closes | Link

## Company news
- **Company** (date): headline. Why it matters. [source](url)

## Your applications
From `applied` in the summary (applied, interviewing, offer, rejected): Company: Role (status, since DATE). Flag anything that changed: a posting that disappeared, a closing date, a new role at the same employer. Omit the section if empty.

## Still open from earlier weeks
- Company: Role (fit, first seen DATE) [link](url)

## No longer found or closed
- Company: Role (last seen DATE)

## Watchlist suggestions
Optional, at most five: employers found by the market sweeps that deserve their own row (two or more relevant roles, or a `strong` one), other companies worth adding, or rows that look obsolete (acquired, shut down, programme discontinued).

## Coverage
Companies checked, failed or not reported; which market sweeps ran and how many off-watchlist employers they found; problems such as careers pages that wouldn't load, searches that failed, or batches that ran out of search budget.
```

For the **career-routes scan**, keep the same structure but add an **Intake calendar** section after "Closing in the next 6 weeks": graduate and trainee intakes that aren't open yet, with when they usually open (from the batches' company notes), so nothing is missed between runs.

## Recording my decisions

Usually I'll just tap Applied, Not eligible or Not interested on the job board (link in step 0.5); the next scan imports those clicks. When I say I've applied for something, or that I'm not eligible or not interested, record it with `scripts/mark.py` (in any session, not only scan runs):

```
python3 scripts/mark.py find kerry food safety          # look up the role id
python3 scripts/mark.py applied <id> --note "submitted 27 Oct"
python3 scripts/mark.py ineligible <id> --note "needs fluent German"
python3 scripts/mark.py off-path <id> --note "too far from fermentation"
python3 scripts/mark.py ignore --company "<company>" --note "not interested"
```

Statuses: `applied`, `interviewing`, `offer`, `rejected` stay in the report under "Your applications"; `ineligible`, `off-path` (doesn't fit my skills or direction) and `ignore` are never reported again. A `--company` decision covers every role there, including future ones. If I describe a whole category I can't do ("anything needing Australian PR"), add it to the "Ruled out" list in `profile.md` instead, so the batches stop finding those roles at all. Commit `tracker/decisions.csv`, `tracker/roles.csv` and `profile.md` afterwards.

## 4. Commit and push to `main`

```
git add reports/ tracker/
git commit -m "Weekly job scan DATE"      # career-routes scan: "Career routes scan DATE"
git push origin main
```

- A run changes only `reports/` and `tracker/`. Never edit `watchlist.md`, `profile.md`, `ROUTINE.md`, `scripts/` or `.claude/`; suggest changes in the report instead.
- If the push is rejected because `main` has moved on, run `git pull --rebase origin main` and push again.
- On network errors, retry up to four times, waiting 2, 4, 8 and 16 seconds.
- If the push still fails (for example, GitHub credentials aren't set up on this computer), leave the commit in place and say at the top of your final message that the results are saved on this computer but weren't pushed, and why.

## 5. Final message

Your last message is the run's summary, the first thing I read when I open the run from its notification. Keep it under about 25 lines:

```
Weekly job scan — Mon 28 Sep 2026      (career-routes scan: Career routes scan — Thu 1 Oct 2026)
N new roles (X strong, Y possible, Z signal) · K deadlines in the next 6 weeks · J news items

Top picks
- Company — Role (Location) — closes DATE — link        (up to 5, strongest first)

Closing soon
- Company — Role — DATE — link

News
- Company: headline — link                               (up to 5)

Full report: https://github.com/mishlin123/job-companyhunt/blob/main/REPORT
```

If nothing new turned up, say so in one line, and still list deadlines and news.
