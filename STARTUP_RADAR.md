# Daily startup radar playbook

A scheduled routine follows this file every morning. It looks for startups and small companies in New Zealand, Australia, the UK and Ireland that are likely to hire someone like me **before** a job reaches the job boards: companies that have just raised money, won a grant, spun out or opened a site, and small employers that post jobs only on LinkedIn. The Monday and Thursday scans ([`ROUTINE.md`](ROUTINE.md)) cover careers pages and job boards; this run doesn't repeat them.

| | |
|---|---|
| When | Every day, early morning (scheduled task "Daily startup radar") |
| Discovery | [`scripts/startup_radar.py`](scripts/startup_radar.py): Google News, a dozen startup and trade-press RSS feeds, and the LinkedIn guest job feed. No login, no WebSearch |
| Judgement | You, against [`profile.md`](profile.md) |
| Lead roster | `tracker/leads.csv`: every company the radar is watching, with what put it there and what to do next |
| Report | `reports/radar/DATE.md` |
| Outreach drafts | In the report, and in `tracker/outreach.csv`, so they appear on the job board's Outreach tab after the next Monday or Thursday scan republishes it |

Work through everything in one go without asking questions: nobody is watching, and your final message is the run's summary. Use `python3` below, or `python` if that's what this computer has.

## 0. Set up

1. Start `caffeinate -ims -t 3600` with the Bash tool's `run_in_background` (no `&`) so the Mac doesn't sleep mid-run. (Use exactly 3600: the weekly scans use 28800, and the script tells the two apart that way.)
2. `git checkout main && git pull origin main`. If the pull fails because of local edits, carry on and mention it in the final message.
3. DATE is today's local date (`date +%F`). REPORT is `reports/radar/DATE.md`. If REPORT already exists, this run has already happened today: stop and say so.
4. `mkdir -p work/radar`.
5. Read `profile.md` (Timing, While studying, Target countries, Background, Ruled out, How to judge fit), `tracker/leads.csv`, and the rows of `tracker/outreach.csv` from the last six weeks.

## 1. Sweep

```
python3 scripts/startup_radar.py sweep --days 3 > work/radar/sweep.txt 2> work/radar/sweep.err
```

It takes about 5–10 minutes and makes no WebSearch calls. Look-back is 3 days so a missed day or a weekend is covered; anything already shown on an earlier day is skipped (`tracker/radar_seen.csv`). It writes `work/radar/candidates.json` and prints one line per candidate, best score first:

- `news`: funding, grant, spinout, new-site and partnership stories, already filtered by keyword for sector and geography. Scores and tags are a rough sort only; you make the call. `roundup` marks weekly "startups that raised" round-ups.
- `job` with `(lead: …)`: a posting by a company on the roster. Report every one of these.
- `job` without a lead: a recent LinkedIn posting in the four countries from the keyword sweep. Most come from established employers that the weekly scans already cover; you're looking for the small ones.

Lines starting with `!` are warnings (a dead feed, LinkedIn rate-limiting); `work/radar/sweep.err` has the request-level detail. Mention them in the report's Coverage section. If the sweep itself fails, re-run it once; if it fails again, write a short REPORT saying so, commit it and stop.

## 2. Judge

Go through every candidate. Budget for the whole run: **at most 10 WebFetch and 6 WebSearch calls**.

**Check the history first.** Before treating a company as new, run `python3 scripts/startup_radar.py history "<company>"`. It prints what the trackers already hold: roster row, roles the weekly scans found (and whether I applied or turned them down), outreach, decisions and news. Don't report a role that is already in `tracker/roles.csv` (the sweep tags those `in-roles-tracker:<status>` and drops the ones I turned down), and use the history in the move: "You applied on 1 Nov; this raise is a reason to follow up" is better than "Apply".

**Is it a lead?** Keep a company only if all of these hold:
- Its headquarters, a lab or a production site is in NZ, Australia, the UK or Ireland, or it has announced one there. Overseas companies with no site in those countries are out (profile.md, "Outside the target countries").
- Its work fits `profile.md`: fermentation and bioprocess, synthetic biology, strain, protein or enzyme engineering, microalgae and seaweed, natural colours, food, dairy and agri biotech, microbiome and probiotics, biologics and vaccine manufacturing, microbiology testing, or one of the adjacent industries and career routes listed there. Microalgae, phycocyanin, natural-colour and precision-fermentation companies are the closest match to my thesis.
- It's small or young enough that a direct approach could matter: a startup, spinout or scale-up, or a small specialist firm. Big employers are the weekly scans' job.
- It isn't ruled out: no pure software or AI, fintech, energy, mining or hardware companies unless their core is biological; drug-discovery and clinical-stage therapeutics biotechs are at most `possible` (they hire molecular and cell biologists, rarely fermentation); consumer food brands without their own R&D or production science aren't leads.

**Round-ups.** Open each `roundup` item that covers the target countries (SmartCompany's "ANZ startups that raised…", Dynamic Business, AgFunderNews' "Agrifood Signals") with WebFetch and pull out every deal that passes the test above; each becomes its own lead. EU-Startups article pages refuse automated fetches (HTTP 403), so for its UK and Irish deals use the headlines in the sweep and WebSearch a company only if it looks `strong`.

**Read the story** (WebFetch) for anything likely to be `strong` or `possible`, to get the amount, stage, investors, what the money is for (hiring, a lab, a pilot plant, scale-up), headcount if stated, and where the team is. Google News links (`news.google.com/...`) often won't open: WebSearch the exact headline with `allowed_domains` set to the publisher's domain instead. Never guess a URL.

**LinkedIn hiring posts.** Founders often announce roles only in a LinkedIn post, and the guest feed can't see posts (only job ads). As a long shot, run 1 WebSearch query for them, rotating the wording and cities by weekday, for example `site:linkedin.com/posts hiring "fermentation scientist" (Auckland OR Christchurch OR Sydney OR Melbourne)` or `site:linkedin.com/posts "we're hiring" ("precision fermentation" OR microalgae OR "synthetic biology") (London OR Cambridge OR Edinburgh OR Dublin)`. Only report posts that are clearly recent (dated within about two weeks) and from companies that pass the lead test; search engines mostly return profiles and old ads, so an empty result is normal. LinkedIn company pages (`linkedin.com/company/...`) return HTTP 403 to WebFetch, so don't try them: the sweep finds each company's LinkedIn id from its first posting instead.

**Postings.** For each `job` candidate you keep:
- At a roster lead: report it. A science role I could do goes under "Apply now" with the usual profile.md rules (start dates, `Live ad:` reasoning on whether they might wait until July 2027). Other roles are a hiring signal: one line.
- From the keyword sweep: keep it only if the employer is a startup or small company (not a multinational, a big CRO or testing chain, a hospital, university or government body). A recruiter's ad counts if it describes a startup client. Add the employer as a lead.

**Rate each lead:**
- `fit`: `strong`, `possible` or `watch`, using profile.md's "How to judge fit".
- `hiring_odds`: `high` (raised a seed to Series B round, or a grant of roughly NZ$/A$/£/€2M or more, in the last two months and says the money is for the team, a lab, a pilot plant or scale-up; or it has a live science posting), `medium` (a smaller raise or grant, a new site, a partnership or offtake deal that implies scale-up, or a posting in another function), `low` (news without a growth signal).
- `signal`: `funding`, `grant`, `spinout`, `new-site`, `partnership`, `hiring-post` or `linkedin-job`.
- `move`: one concrete next step, for example "Apply now on LinkedIn (entry level, Auckland)", "Connect with the head of R&D now and ask how they're planning their 2027 team", "Study-time: ask whether they need part-time lab help" (Christchurch and Canterbury companies; see profile.md, "While studying"), or "Watch: contact once the pilot plant opens (mid-2027)". Remember I can't start full-time before 1 July 2027: for most funding leads the right move is to get known now so I'm in mind when they hire next year.

## 3. Record

Write `work/radar/leads.json`:

```json
{
  "leads": [
    {"company": "…", "country": "NZ|AU|UK|IE", "city": "…", "sector": "…", "what": "one line on what they do",
     "signal": "funding", "trigger": "Raised NZ$4M seed led by …", "trigger_date": "YYYY-MM-DD", "trigger_url": "https://…",
     "hiring_odds": "high", "fit": "strong", "linkedin_url": "", "website": "", "careers_url": "",
     "move": "…", "jobs": "titles of postings seen today, if any", "notes": "anything else worth keeping"}
  ],
  "outreach": [
    {"company": "…", "trigger": "…", "trigger_url": "…", "contact": "a founder or the head of R&D",
     "channel": "LinkedIn connection note (under 300 characters)", "draft": "…", "notes": "why now, one or two sentences"}
  ]
}
```

- Use the company name as it appears on LinkedIn or in the story, and the same name each time, so the roster doesn't fill with duplicates (check `tracker/leads.csv` first). Include roster companies that had news or a posting today, so their row is refreshed.
- **Outreach: at most two drafts a day**, only for `strong` leads with `high` or `medium` hiring odds that have no `suggested` or `sent` item in `tracker/outreach.csv` from the last six weeks. Same rules as the weekly scans: in my voice, plain and specific; who I am (Microbiology MSc at the University of Canterbury, thesis on phycocyanin from waste kiwifruit with *Galdieria*, earlier work at Daisy Lab, available full-time from July 2027); one line tying me to the trigger; one small ask (a quick question about their plans or a short call), never a request for a job. Keep LinkedIn connection notes under 300 characters. Describe the contact by role ("a co-founder", "the head of fermentation"), never by name. You only draft: never send anything.

Then:

```
python3 scripts/startup_radar.py record --date DATE work/radar/leads.json > work/radar/record.json
```

Then keep the day's working files for the checks script: `mkdir -p work/radar/DATE && cp work/radar/candidates.json work/radar/record.json work/radar/leads.json work/radar/sweep.txt work/radar/DATE/`.

`record` merges the leads into `tracker/leads.csv` (keeping my own statuses), saves LinkedIn company ids found from postings, marks everything in today's sweep as seen, and adds the drafts to `tracker/outreach.csv`. If a weekly scan is running in this folder at the same time, it holds the drafts in `work/radar/pending-outreach.json` and the next run adds them (`outreach_held` in the output). Never hand-edit the CSVs.

Don't republish the job board from this run: the Monday and Thursday scans do that, and the drafts are in today's report in the meantime.

## 4. Write REPORT

Short and skimmable on a phone, with a link on every item. Leave out empty sections.

```markdown
# Startup radar — Monday 16 November 2026

N new leads (X strong) · K startup postings · D outreach drafts

## Act now
Up to five items, best first: postings I could apply for, and `strong` leads with `high` odds.
- **Company** (City, Country): what happened, DATE. Why it fits me. **Move:** the move. [source](url) · [LinkedIn people search](https://www.linkedin.com/search/results/people/?keywords=COMPANY%20founder)

## New leads
- **Company** (City, Country) · signal · fit · hiring odds: one line on what they do and what happened. Move. [source](url)

## Postings at startups
- **Company**: Role (Location, posted DATE). Fit, and for a live ad whether they might wait until July 2027. [ad](url)

## Roster updates
Roster companies with news or a posting today, one line each.

## Outreach drafts
- **Company**: trigger ([source](url)). Contact: role, via channel.
  > draft
  [LinkedIn people search](link). It reaches the job board's Outreach tab at the next Monday or Thursday scan; mark it sent there, or tell Claude.

## Coverage
Sweep counts by channel, warnings, round-ups opened, WebFetch and WebSearch calls used, roster size, LinkedIn ids found (`linkedin_ids_found`), drafts held. Then "Checked and left out": one line per notable item you dropped and why (already tracked, starts too early, outside the target countries, not lab science), so I can see the judgement.
```

If nothing passed the lead test, write just the title, "Nothing new today", and the Coverage section.

**Check the numbers.** Write `reports/radar/DATE-checks.py`, which loads `work/radar/DATE/candidates.json` and `record.json` and prints every count stated in the report next to the value it computes, and the length of each LinkedIn note; run it with `python3 -I`, and fix the report if anything differs. `reports/radar/2026-11-16-checks.py` is a template.

## 5. Commit and push

A weekly scan may be running in this same folder, so stage only this run's files, never `git add .` or whole folders:

```
git add reports/radar/DATE.md reports/radar/DATE-checks.py tracker/leads.csv tracker/radar_seen.csv
git add tracker/outreach.csv        # only if outreach_added isn't empty
git commit -m "Startup radar DATE"
git push origin main
```

If the push is rejected because `main` moved on, `git pull --rebase origin main` and push again; on network errors retry up to four times (2, 4, 8, 16 seconds). If it still fails, leave the commit and say so at the top of the final message. Never edit `watchlist.md`, `profile.md`, the playbooks, `scripts/` or `.claude/`; suggest changes in the report instead (for example, a lead that has earned a row on the watchlist).

## 6. Final message

Under about 15 lines, the first thing I read from the notification:

```
Startup radar — Mon 16 Nov 2026
N new leads (X strong) · K startup postings · D drafts

Act now
- Company — what happened / role — move — link          (up to 5)

New leads
- Company (City) — one line                              (the rest, up to 5)

Report: reports/radar/DATE.md · problems, if any
```

## Recording my decisions

When I say a lead isn't interesting, or that I've contacted or applied to one, record it (in any session):

```
python3 scripts/startup_radar.py set "<company>" ignore --note "not my field"
python3 scripts/startup_radar.py set "<company>" contacted --note "messaged the CTO 18 Nov"
python3 scripts/startup_radar.py roster          # list every lead
```

Statuses: `new` (found today), `watching` (set automatically from the next day), `contacted`, `applied`, `ignore` (never checked or reported again). Marking an outreach draft as sent on the job board also moves its lead to `contacted` on the next run. To watch a company that isn't on the roster yet, ask Claude to add it as a lead.
