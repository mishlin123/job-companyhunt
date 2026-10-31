#!/usr/bin/env python3
"""Count the skills that tracked postings ask for, and compare them with mine.

Usage:
    python3 scripts/skills_gap.py > reports/skills-gap.md

Reads every role in tracker/roles.csv (title and notes) except the ones I marked off-path
or ignore, weights them by how much they matter (applied and strong 3, possible 2, signal 1),
and counts which skills from SKILLS below they mention. My own level for each skill comes from
the "Skills" section of profile.md: lines like "- HPLC / UPLC: some". Levels are have, some,
none; anything missing counts as unknown. The output is a Markdown report.
"""

import argparse
import csv
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

# name, pattern, how to close the gap before mid-2027
SKILLS = [
    ("Fermentation / bioreactor operation", r"ferment|bioreactor|fermenter|fed-batch|ambr|biolector",
     "Run or log extra bench-bioreactor batches in the thesis lab; write up a fed-batch optimisation."),
    ("Scale-up / tech transfer / pilot plant", r"scale-?up|tech(nology)? transfer|pilot[- ]plant|pilot[- ]scale|msat",
     "Frame the Daisy Lab 2 L to 20,000 L cost model as scale-up work; NIBRT or BioPharma online scale-up modules."),
    ("Upstream / mammalian cell culture", r"\busp\b|upstream|cell culture|\bcho\b|mammalian",
     "Short practical courses (e.g. NIBRT online); mostly learned on the job, so state willingness."),
    ("Downstream / purification / chromatography", r"\bdsp\b|downstream|purif|chromatograph|\bakta|filtration|\btff\b",
     "Phycocyanin purification in the thesis is DSP: name the steps (extraction, filtration, chromatography) on the CV."),
    ("HPLC / UPLC / LC-MS / GC", r"\bu?hplc\b|\buplc\b|lc-?ms|\bgc\b|mass spec",
     "Ask to run thesis samples on the department HPLC; one validated method is enough to claim it."),
    ("Protein analytics (SDS-PAGE, ELISA, Western)", r"sds-?page|elisa|western blot|protein analytic|protein characteri",
     "Run SDS-PAGE on phycocyanin fractions and report purity ratios alongside A620/A280."),
    ("Molecular biology (PCR, cloning, CRISPR)", r"\bpcr\b|qpcr|cloning|crispr|plasmid|golden gate|molecular biology",
     "Pick up a cloning or qPCR side task in a UC lab; list any coursework practicals."),
    ("Strain / metabolic engineering, synbio", r"strain|metabolic engineer|synthetic biolog|synbio|genetic engineer",
     "Free iGEM and BioBuilder material; a small Galdieria strain-improvement literature review for interviews."),
    ("Microbiology lab techniques / aseptic", r"microbiolog|aseptic|media prep|plating|environmental monitoring|sterility|endotoxin|bioburden",
     "Already core to the MSc: make sure the CV names the techniques."),
    ("Design of experiments / statistics", r"\bdoe\b|design of experiment|statistic|\bjmp\b|minitab|multivariate",
     "Apply a small DoE (e.g. JMP student licence or Python) to one thesis optimisation and report it."),
    ("Python / R / data analysis", r"python|\br\b(?! ?&)|\bsql\b|data analy|bioinformatic|machine learning|\bml\b|coding|programming",
     "Analyse thesis growth and yield data in Python and put the notebook on GitHub."),
    ("Lab automation / liquid handling", r"automat|liquid handl|opentrons|tecan|hamilton|high-throughput|robot",
     "Low-cost: Opentrons protocol tutorials online; mention any plate-reader workflows."),
    ("GMP / GxP", r"\bc?gmp\b|gxp|\bglp\b|\bgcp\b|good manufacturing",
     "A short GMP fundamentals certificate (several free or under NZ$100 online)."),
    ("Quality systems (SOPs, deviations, CAPA, validation)", r"\bsop|deviation|capa\b|validation|qualification|document control|\bqms\b|audit",
     "Write SOPs for the thesis methods and say so; a GMP course covers the vocabulary."),
    ("Regulatory affairs / dossiers", r"regulatory|dossier|submission|novel food|efsa|\bfda\b|fsanz|registration",
     "Map phycocyanin's regulatory status (EU, FDA colour additive, FSANZ) as a one-page brief for interviews."),
    ("Techno-economic / cost modelling", r"techno-?economic|cost model|\btea\b|cogs|business case",
     "Strength already (Daisy Lab media-cost model): lead with it for consulting and process roles."),
    ("Excel modelling / market sizing / slides", r"excel|market siz|forecast|powerpoint|financial model|market research|competitive intelligence",
     "Keep drilling market sizing (DeciBio prep page); build one Excel market model for a natural-colours market."),
    ("Scientific and technical writing", r"writing|writer|report writing|publication|manuscript|grant|proposal|editorial",
     "Strength already (scholarship proposal): add a preprint or poster abstract from the thesis."),
    ("Project management / stakeholders", r"project manag|stakeholder|client[- ]facing|cross-functional|coordinat",
     "Describe the thesis as a project with milestones and budget; any team or club leadership."),
]

# Requirements that are about experience or credentials rather than skills.
BARRIERS = [
    ("Asks for 1–2 years' experience", r"\b1\s*[-–+]\s*2\s*(yrs|years)|\b1\+?\s*(yrs|years)|one year"),
    ("Asks for 2–4 years' experience", r"\b[2-4]\s*\+?\s*(yrs|years)|\b2\s*[-–]\s*[3-5]\s*(yrs|years)"),
    ("Asks for 5+ years", r"\b([5-9]|1[0-5])\s*\+?\s*(yrs|years)"),
    ("Needs a PhD", r"phd (required|needed|essential)|requires? a phd|phd-level|postdoc"),
    ("Needs industry or GMP experience", r"(industry|industrial|gmp|regulated)[- ](lab )?experience"),
    ("Needs a driving licence", r"driv(ing|er'?s) licen[cs]e|own car"),
    ("Needs another language", r"german|dutch|french|danish|swedish|spanish|mandarin|fluent in"),
]

ROUTES = [
    ("Consulting and market analysis", r"consult|analyst|strategy|insights|market"),
    ("Patent and IP", r"patent|\bip\b|intellectual property"),
    ("R&D tax and funding", r"\btax\b|r&d incentive|innovation relief|grant"),
    ("Regulatory and quality", r"regulator|quality|\bqa\b|\bqc\b|compliance|validation"),
    ("Writing and publishing", r"writer|editor|editorial|publishing|communications"),
]
WEIGHT = {"strong": 3, "possible": 2, "signal": 1}
LEVELS = ("have", "some", "none")


def my_levels(profile):
    """{skill name: level} from '- Name: level' lines in profile.md's Skills section."""
    text = profile.read_text(encoding="utf-8") if profile.exists() else ""
    match = re.search(r"^## Skills\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    levels = {}
    for line in (match.group(1) if match else "").splitlines():
        m = re.match(r"\s*-\s*(.+?):\s*(have|some|none)\b", line, re.I)
        if m:
            levels[m.group(1).strip().lower()] = m.group(2).lower()
    return levels


# Scan notes mix the posting's requirements with comments on my fit; drop the latter.
ABOUT_ME = re.compile(r"\bmsc\b|thesis|\bhis\b|\bhe\b|\byour?\b|\bfits?\b|interest|adjacent|profile|"
                      r"galdieria|daisy lab|speculative|worth (an )?approach", re.I)


def requirement_text(notes):
    return " ".join(s for s in re.split(r"(?<=[.;])\s+", notes) if not ABOUT_ME.search(s))


def route(role):
    for name, pattern in ROUTES:
        if re.search(pattern, role, re.I):
            return name
    return "Science, bioprocess and R&D"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tracker", type=Path, default=Path("tracker"))
    parser.add_argument("--profile", type=Path, default=Path("profile.md"))
    args = parser.parse_args()

    rows = [r for r in csv.DictReader(open(args.tracker / "roles.csv", encoding="utf-8"))
            if r["status"] not in ("off-path", "ignore")]
    mine = my_levels(args.profile)
    score, roles_with, examples = Counter(), Counter(), defaultdict(list)
    by_route = defaultdict(Counter)
    route_size = Counter()
    barrier = Counter()
    total_weight = 0
    for r in rows:
        w = 3 if r["status"] in ("applied", "interviewing", "offer") else WEIGHT.get(r["fit"], 1)
        total_weight += w
        text = f"{r['role']} {requirement_text(r['notes'])}"
        rt = route(r["role"])
        route_size[rt] += 1
        for name, pattern, _ in SKILLS:
            if re.search(pattern, text, re.I):
                score[name] += w
                roles_with[name] += 1
                by_route[rt][name] += 1
                if r["fit"] in ("strong", "possible") or r["status"] == "applied":
                    if len(examples[name]) < 3:
                        examples[name].append(f"{r['company']} – {r['role'][:60]}")
        for name, pattern in BARRIERS:
            if re.search(pattern, requirement_text(r["notes"]), re.I):
                barrier[name] += 1

    advice = {name: tip for name, _, tip in SKILLS}

    def level(name):
        return mine.get(name.lower(), "unknown")

    ranked = score.most_common()
    gaps = [(n, s) for n, s in ranked if level(n) in ("none", "unknown", "some")]
    out = []
    out.append(f"# Skills gap — {date.today():%-d %B %Y}\n")
    out.append(f"From {len(rows)} tracked postings (titles and scan notes; off-path and ignored roles excluded), "
               "weighted 3 for strong or applied, 2 for possible, 1 for signal. Your level comes from the "
               "Skills section of `profile.md`; *unknown* means it isn't filled in yet.\n")
    out.append("Scan notes are short summaries, so counts show relative demand, not exact frequencies.\n")
    out.append("## Close these first\n")
    out.append("The most-demanded skills where you're not yet at *have*:\n")
    for i, (name, s) in enumerate(gaps[:6], 1):
        out.append(f"{i}. **{name}** (your level: {level(name)}; in {roles_with[name]} postings). {advice[name]}")
    out.append("\n## Demand by skill\n")
    out.append("| Skill | Weighted demand | Postings | Your level | Example roles you'd want |")
    out.append("|---|---|---|---|---|")
    for name, s in ranked:
        share = round(100 * s / total_weight)
        out.append(f"| {name} | {s} ({share}%) | {roles_with[name]} | {level(name)} | "
                   f"{'; '.join(examples[name]) or '—'} |")
    out.append("\n## What each route asks for\n")
    for rt, n in route_size.most_common():
        top = ", ".join(f"{k} ({v})" for k, v in by_route[rt].most_common(5)) or "—"
        out.append(f"- **{rt}** ({n} postings): {top}")
    out.append("\n## Barriers that aren't skills\n")
    out.append("How often postings set a bar you can't train for before July 2027:\n")
    for name, _ in BARRIERS:
        out.append(f"- {name}: {barrier[name]} postings")
    missing = [n for n, _, _ in SKILLS if n.lower() not in mine]
    if missing:
        out.append("\n## Fill in your levels\n")
        out.append("Add these to the Skills section of `profile.md` as `- Name: have`, `some` or `none`, "
                   "and the next report will rank your gaps properly:\n")
        out.extend(f"- {n}" for n in missing)
    print("\n".join(out))


if __name__ == "__main__":
    main()
