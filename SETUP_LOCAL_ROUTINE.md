# Set up the weekly job scan as a local routine

**For Claude, running on my computer.** This sets up the weekly job scan as a *local routine* in the Claude desktop app, so it runs on this computer every Monday morning. Work through the steps in order and fix what you can; ask me only where a step says to. Finish with the report in step 7.

## What you're setting up

- A local routine (scheduled task) in the Claude desktop app that runs every **Monday at 7:00 AM** in a dedicated clone of `github.com/mishlin123/job-companyhunt`.
- Each run follows [`ROUTINE.md`](ROUTINE.md). It researches every company in [`watchlist.md`](watchlist.md) with parallel subagents, reading careers pages and searching the web. It then updates `tracker/`, writes `reports/<date>.md` and pushes to `main`.
- Local routines only run while the desktop app is open and the computer is awake. If the computer sleeps through 7am, the app does one catch-up run when it wakes.

## 1. Use a dedicated clone

1. If this session isn't already in a clone of the repo, clone it somewhere permanent, for example `git clone https://github.com/mishlin123/job-companyhunt.git ~/job-companyhunt`.
2. Keep this clone for the routine only. Every run checks out `main`, pulls and commits there, so it shouldn't share a folder with my own work in progress.
3. In the clone, run `git checkout main && git pull origin main`.

## 2. Check the prerequisites

Run these in the clone. Fix anything that fails, but ask me before installing software or changing system settings.

1. **Python 3.8 or newer:** `python3 --version` (on Windows, `python --version`).
2. **The scripts run:**
   - `python3 scripts/plan_batches.py` prints a batch plan: about ten batches of up to 20 rows.
   - Create `work/empty.json` containing `{"companies": [], "roles": [], "news": []}`. Then run `python3 scripts/update_tracker.py --dry-run --date <today, YYYY-MM-DD> work/empty.json`. It should print a JSON summary with `"baseline": true` and change no files.
3. **Git can push unattended:** `git push --dry-run origin main` must succeed without asking for a username or password, because an unattended run can't type one. If it prompts or fails, help me sign in with one of:
   - GitHub Desktop;
   - `gh auth login` followed by `gh auth setup-git`;
   - the system credential manager.
4. **Git identity:** `git config user.name` and `git config user.email` both print something.

## 3. Create the routine

If this session has tools for scheduled tasks, use them: Claude Desktop sessions can create and edit routines when asked. Otherwise, walk me through **Code** tab → **Routines** → **New routine** → **Local**. Use exactly these values:

| Field | Value |
|---|---|
| Name | Weekly job hunt scan |
| Description | Scans the job-hunt watchlist for new roles and company news |
| Instructions | the block below, verbatim |
| Permission mode | Auto, if offered; otherwise the mode that auto-accepts file edits |
| Model | the default |
| Folder | the clone from step 1 |
| Isolated worktree | **Off**, because runs must commit to `main` in the clone |
| Schedule | Weekly: Monday, 7:00 AM |

```text
Weekly job-hunt scan. This runs unattended every Monday morning on my computer, in my local clone of mishlin123/job-companyhunt. Nobody is watching, so work through it without asking questions.

1. Read ROUTINE.md in this folder and follow it step by step.
2. You have my explicit permission to commit and push directly to main in this repo, touching only reports/ and tracker/. Don't create a branch or pull request, and don't edit watchlist.md, profile.md, ROUTINE.md, scripts/ or .claude/; suggest changes in the report instead.
3. Finish with the short summary described at the end of ROUTINE.md.
```

If a local routine with this name already exists, update it instead of creating a second one. If the app asks me to trust the folder, that's expected.

## 4. Permissions

The repo's [`.claude/settings.json`](.claude/settings.json) pre-approves what a run needs, so a run doesn't stall on prompts:
- web search and page fetching;
- the git commands that pull, commit and push `main`;
- the two scripts in `scripts/`;
- file writes under `reports/` and `work/`.

It also blocks force-pushes and hard resets. Don't loosen it.

## 5. Keep the computer awake (optional)

Point me to **Settings → Desktop app → General → Keep computer awake**. It stops idle sleep, but closing the lid still puts the computer to sleep.

## 6. Test run, only if I ask

A full scan takes roughly 20–40 minutes and a noticeable share of my weekly usage, and the first scheduled run happens next Monday anyway. So don't start one unless I ask.

If I do ask:
1. Use **Run now** on the routine's page and watch for permission prompts.
2. Approve each prompt with **Always allow**, so later runs don't stall.
3. A good run pushes `reports/<date>.md` and updated `tracker/` files to GitHub.

## 7. Report back

In a few lines, tell me:
- the clone's path;
- the routine's settings (schedule, permission mode, worktree off);
- the result of each check in step 2;
- anything I still need to do.

## Notes

- The first run is a baseline: it lists everything relevant that's currently open. Later runs report only what's new, what's closing soon and what has disappeared.
- An earlier cloud version of this routine is paused in my claude.ai Routines as "Weekly job hunt scan (cloud, paused)". Leave it paused; I'll delete it once the local one works.
