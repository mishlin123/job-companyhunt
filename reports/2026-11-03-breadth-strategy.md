# More applications, more industries: a plan for a job in the UK, Australia or NZ by July 2027

Written 3 Nov 2026 from the tracker (`roles.csv`, `pipeline.csv`, `decisions.csv`, `outreach.csv`) and the watchlist.

## Where things stand

- **34 real applications in 5 weeks** (plus 4 talent-pool sign-ups). By country: UK 22 (incl. the Fast Stream), Ireland 10, NZ 1, Singapore 1, Australia 0 (3 talent pools only).
- **By route**: graduate R&D, food and pharma schemes 14, life-science consulting or analyst 12 (5 of them Veeva), R&D tax 3, and one each of medcomms, regulatory, patent attorney, civil service and Enterprise Ireland.
- **The tracker has no strong-fit role open right now.** Of 1,038 roles found, 801 were marked ineligible, 517 of them because an ordinary vacancy with no start date counts as "starts now".
- **About half the scan budget goes to countries you're no longer targeting** (watchlist sections 5 to 17: Belgium, Netherlands, Germany, Denmark, Sweden, Finland, France, Israel, Canada, US, other Europe).
- **Outreach is thin**: 12 rows in `outreach.csv`, all in the last week.

## The numbers you're up against

UK graduate schemes averaged **140 applications per vacancy** in 2024/25 (ISE Student Recruitment Survey 2025), and **290** in retail/FMCG. Public-sector and charity roles were the least crowded at 74.

Working assumption (not a measured rate): if 1 in 25 to 40 well-targeted applications turns into an offer, you need **about 80 to 120 applications** to have a fair shot at 2 or 3 offers. You're at 34. The target below gets you to about 150 by June, spread over more industries so one bad sector doesn't sink the year.

## The timing problem, by market

| Market | What starts by July 2027 or soon after | When to apply |
|---|---|---|
| **UK** | September 2027 graduate schemes and trainee intakes | **Now to February**. Most close Nov to Jan. This is the volume window today |
| **Australia / NZ** | Ordinary direct-hire vacancies (they hire 4 to 8 weeks before the start) and a few mid-year intakes (BDO R&D tax, AUT Ventures) | **April to June 2027** |
| **Australia / NZ graduate programmes** | February 2028 starts, so a backstop rather than a July job | Feb to Aug 2027 |

So: pile applications into the UK now, prepare AU/NZ in Jan to March, then switch to high-volume AU/NZ direct applications from April.

## Industries to add (within reason)

Each line fits your MSc or skills, and almost none are applied to yet.

**UK, apply Nov 2026 to Feb 2027**
1. **Patent trainee, the rest of the firms (~15 applications).** You applied to 1 of 12 UK firms on the watchlist. Add Mewburn Ellis, J A Kemp, HGF, Marks & Clerk, Withers & Rogers, Dehns, Potter Clarkson, Kilburn & Strode, D Young, plus Abel & Imray, Boult Wade Tennant, Mathys & Squire, Venner Shipley, Appleyard Lees, Haseltine Lake Kempner. One strong cover letter adapts across all of them. The single best block for effort.
2. **NHS Scientist Training Programme, Clinical Microbiology** (also Genomics). Three-year salaried clinical-scientist training, made for a microbiology MSc. The window is about 2 weeks in Dec to Jan and opens with little warning (2026 entry closed 16 Jan 2026).
3. **UK public-sector science**: UKHSA (Porton Down, Colindale), APHA, Food Standards Agency, Defra, Cefas and Fera graduate or scientist intakes. Only 74 applications per vacancy in this sector.
4. **Food and drink R&D/technical graduate schemes beyond Kerry, Mars and Greencore**: Unilever, Nestlé UK, PepsiCo, Mondelez, Diageo, Heineken UK, Carlsberg Britvic, AB Mauri, Tate & Lyle, Arla, Müller, Quorn. None of these are on the watchlist except Nestlé and Quorn. Crowded (290 per vacancy), so volume matters here.
5. **Bioprocess and CDMO**: Fujifilm Diosynth (Billingham), Lonza (Slough), CPI (Centre for Process Innovation), Oxford Biomedica, AstraZeneca and GSK UK process-development schemes, Ipsen.
6. **More analyst and consulting**: the Big Four's generalist UK graduate schemes take any degree (Sept 2027 start); plus L.E.K., Putnam, IQVIA, Clarivate, Trinity, Health Advances.
7. **Medcomms, more agencies** (rolling): Helios, Adelphi, Oxford PharmaGenesis, OPEN Health, Avalere. You've only applied to Costello.
8. **Water-industry graduate scientist schemes** (Thames, Severn Trent, Anglian, United Utilities, Scottish Water): microbiology-heavy labs. Borderline with your QC rule-out, so only if you're happy with it.

**Australia / NZ, prepare Jan to March, apply April to June**
1. **Direct hire, Apr to Jun 2027**: research assistant and technician roles at universities and research institutes, R&D technologist, technical officer and analyst roles. Aim for 10 or more a week from April; the SEEK sweep already finds them.
2. **Agribusiness and agtech**: Rabobank, Elders, Nufarm, Corteva, Bayer, Syngenta, LIC, Ravensdown, Ballance, Zespri. Mostly not on the watchlist.
3. **Dairy and food R&D**: Fonterra, Synlait, Tatua, a2, Open Country, Westland, Goodman Fielder, Sanitarium.
4. **Generalist graduate programmes that take science graduates**: Big Four, NZ and Australian government, banks' agri teams (Feb 2028 backstop).
5. **Speculative "available from July 2027" notes** in Jan to Feb to about 30 AU/NZ employers on the watchlist that don't run intakes.

**A backstop to decide on later**: QC microbiology is the biggest employer of entry-level microbiologists in AU and NZ, and you ruled it out on 27 Oct. If you have fewer than 2 AU/NZ interviews by mid-May, consider reopening it for AU/NZ only. Your call, not a recommendation to do it now.

## Targets

| Period | Applications | Mostly |
|---|---|---|
| Nov 2026 | 25 | UK patent firms, food/drink schemes, public-sector science, consulting |
| Dec 2026 to Jan 2027 | 30 | UK schemes closing, NHS STP, medcomms |
| Feb to Mar 2027 | 20 | AU/NZ graduate programmes (backstop), speculative AU/NZ notes, late UK rounds |
| Apr to Jun 2027 | 70+ | AU/NZ and UK direct hire, 10 or more a week |

Plus **5 outreach messages a week** (current graduates or trainees at target employers, team members, recruiters). A referral or a warm contact lifts the response rate far more than another cold application.

## Changes to the job-hunt machinery

1. **Narrow the scans to the UK, Australia and NZ (and Ireland, where you already have 10 applications).** Stop scanning watchlist sections 5 to 17 (EU, Israel, Canada, US). That frees about half the scan budget for the industries above.
2. **Add the new employers above to the watchlist** (about 60 rows), so the Monday scan checks them.
3. **A UK board sweep** like `seek_search.py`, using free job APIs (Adzuna or Reed) for "graduate 2027", "September 2027", "trainee" in science categories. The scan is employer-by-employer, so it misses anyone not on the list.
4. **An automatic April switch**: write into `profile.md` now that from **1 April 2027** ordinary UK, AU and NZ vacancies count (they'd start about July). Otherwise the "starts now" rule keeps hiding the roles you need most.
5. **An "apply this week" queue at the top of each report**: every open role or intake, sorted by deadline, plus a counter of applications this week against the target (from `decisions.csv`).
6. **An application kit**, kept **outside this repo because the repo is public**: five CV variants (bioprocess R&D; analyst/consulting; patent/writing; policy/regulatory; lab/quality) and an answer bank for the usual graduate-scheme questions. That gets each application down to about 30 to 45 minutes.

Sources: [ISE Student Recruitment Survey 2025](https://ise.org.uk/_userfiles/pages/files/reports/student_recruitment_survey_2025.pdf), [ISE: apprenticeships rise as graduate vacancies drop](https://ise.org.uk/knowledge/insights/492/apprenticeships_rise_as_graduate_vacancies_drop_8), [NSHCS STP advert](https://nshcs.hee.nhs.uk/publications/scientist-training-programme-trainee-clinical-scientist-advert/html/).
