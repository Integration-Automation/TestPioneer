# docs/updates: update log index

`progress.md` holds only work that is **not done yet**. Everything that *was* done (what changed, measured numbers, decisions, snapshots) is recorded here: **one batch file per month**, one entry per piece of work, each entry with a fixed-format ID and tags, and one row per entry in the index below.

> No TODOs here. If an entry mentions something still open, it only points to it (e.g. "open item: `progress.md` #3"); the item itself lives in `progress.md`.

## How to query

Run from the repository root:

| To find | Command |
|---|---|
| every entry, one line each | `rg -n "^## U-2" docs/updates` |
| entries of one type | `rg -n "^## U-2.*#done" docs/updates` |
| entries with a topic tag | `rg -n "^## U-2.*#<tag>" docs/updates` |
| one day or one month | `rg -n "^## U-202609" docs/updates` |
| the full text of one entry | `rg -n -A 60 "^## U-20260922-01" docs/updates` |
| any keyword | `rg -n "keyword" docs/updates` |

Without `rg`: `git grep -n "^## U-2" -- docs/updates`, or in PowerShell `Select-String -Path docs/updates/*.md -Pattern '^## U-2'`.

## Entry format

```markdown
## U-YYYYMMDD-NN · YYYY-MM-DD · one-line title · #type #topic

- **What**: ...
- **Result / numbers**: ...
- **Files**: `path` ...
- **Evidence**: commit, file:line, link ...
- **Open items**: none / see `progress.md` ...
```

- **ID**: `U-` + date + two-digit sequence for that day. IDs are never renumbered or reused, so code comments and other documents can cite them.
- **Type tag** (exactly one): `#done` finished `progress.md` item, `#snapshot` measurement or inventory, `#decision`, `#incident`, `#migration`, `#docs`, `#release`.
- Topic tags are free-form (`#mcp`, `#wayland`, ...).
- Keep conclusions, numbers, files and evidence; drop the reasoning trail and dead ends.

## Batch rules

1. One file per month: `docs/updates/YYYY-MM.md`. Append new entries at the end.
2. Over about 800 lines, continue in `YYYY-MM-b.md` (then `-c`) and list it in the batch table below.
3. **Claim the ID under a lock.** Several sessions may write this log at the same time (for example parallel autonomous runs), and without a lock two of them pick the same number:
   1. `mkdir docs/updates/.id-lock`. Creating a directory is atomic, so only one writer succeeds. If it already exists, someone else is claiming: wait a few seconds and retry. A lock older than 10 minutes is stale and may be removed.
   2. Find the day's last number with `rg -n "^## U-YYYYMMDD" docs/updates` and write the heading line and the index row.
   3. `rmdir docs/updates/.id-lock`, then fill in the body. Git never tracks the empty lock directory.
   4. Before committing, `rg -c "^## U-<your ID>" docs/updates` must report one match in total. If not, renumber your entry under the lock and fix its index row. Whoever merges a branch renumbers entries that reuse an ID.
4. **One line per index row**: title only (about 60 characters), no summary.
5. Never rewrite a recorded entry. Correct it with a new `#decision` or `#incident` entry and add "→ corrected in U-..." to the old one.

## When a `progress.md` item is done

In the same commit: delete the item from `progress.md`, add a `#done` entry here that names it, and add its index row.

---

## Index (newest first)

| ID | Date | Title | Tags | Batch |
|---|---|---|---|---|
| U-20261008-15 | 2026-10-08 | What native artifact support means for a runner | #decision #artifacts #docs | [2026-10](2026-10.md) |
| U-20261008-14 | 2026-10-08 | validate reads a workflow from standard input | #feature #cli #validation | [2026-10](2026-10.md) |
| U-20261008-13 | 2026-10-08 | Run output stays on by default | #decision #artifacts #report | [2026-10](2026-10.md) |
| U-20261008-12 | 2026-10-08 | JUnit timestamps are plain UTC date-times | #feature #report | [2026-10](2026-10.md) |
| U-20261008-11 | 2026-10-08 | An artifacts pattern the runner satisfied itself is not a warning | #feature #artifacts | [2026-10](2026-10.md) |
| U-20261008-10 | 2026-10-08 | je-mail-thunder is no longer a dependency | #done #decision #deps | [2026-10](2026-10.md) |
| U-20261008-09 | 2026-10-08 | A record is counted only for the in-process call that produced it | #done #bugfix #report | [2026-10](2026-10.md) |
| U-20261008-08 | 2026-10-08 | A workflow can run twice in one process: step names are unique per run | #done #bugfix | [2026-10](2026-10.md) |
| U-20261008-07 | 2026-10-08 | The sample workflows run real scripts and CI fails when they fail | #done #ci #tests | [2026-10](2026-10.md) |
| U-20261008-06 | 2026-10-08 | A download that fails now fails its step | #bugfix #steps | [2026-10](2026-10.md) |
| U-20261008-05 | 2026-10-08 | README and Getting Started are one complete, tested example | #done #docs | [2026-10](2026-10.md) |
| U-20261008-04 | 2026-10-08 | SonarCloud and Codacy findings of PR #32 resolved | #ci #security | [2026-10](2026-10.md) |
| U-20261008-03 | 2026-10-08 | Runner reports are read and merged into one report | #done #feature #report | [2026-10](2026-10.md) |
| U-20261008-02 | 2026-10-08 | Runs have an ID, a result and kept failure artifacts | #done #feature #artifacts | [2026-10](2026-10.md) |
| U-20261008-01 | 2026-10-08 | Workflows are validated without running: schema, lint rules, CLI | #done #feature #validation | [2026-10](2026-10.md) |
| U-20261001-05 | 2026-10-01 | The publish jobs build with the locked setuptools instead of downloading the newest | #ci #security #X-13 | [2026-10](2026-10.md) |
| U-20261001-04 | 2026-10-01 | Dependabot watches the hash-locked requirements; a guard keeps the publish jobs on them | #ci #security #X-13 | [2026-10](2026-10.md) |
| U-20261001-03 | 2026-10-01 | The sdist carries no tests | #done #packaging #X-13 | [2026-10](2026-10.md) |
| U-20261001-02 | 2026-10-01 | CI publishes test_pioneer_dev from the dev branch | #release #ci #X-13 | [2026-10](2026-10.md) |
| U-20261001-01 | 2026-10-01 | Every workflow job has a timeout | #ci #tests | [2026-10](2026-10.md) |
| U-20260925-02 | 2026-09-25 | CI and classifiers cover Python 3.13 and 3.14 | #ci #packaging #tests | [2026-09](2026-09.md) |
| U-20260925-01 | 2026-09-25 | Dependabot waits 7 days before proposing a new release | #ci #security #deps | [2026-09](2026-09.md) |
| U-20260924-02 | 2026-09-24 | Keep checkout credentials only in the job that pushes | #ci #security | [2026-09](2026-09.md) |
| U-20260924-01 | 2026-09-24 | Move CI to Node 24 actions pinned by commit | #ci #security #deps | [2026-09](2026-09.md) |
| U-20260923-06 | 2026-09-23 | Release 0.1.34 | #done #release | [2026-09](2026-09.md) |
| U-20260923-05 | 2026-09-23 | Publish lock, no-redirect downloads, matching ChromeDriver | #done #ci #docker #security | [2026-09](2026-09.md) |
| U-20260923-04 | 2026-09-23 | One Dockerfile per image, with a selftest stage that runs | #done #docker | [2026-09](2026-09.md) |
| U-20260923-03 | 2026-09-23 | file-runner: FileAutomation joins run, run_folder and parallel_run | #done #feature | [2026-09](2026-09.md) |
| U-20260923-02 | 2026-09-23 | run_folder works for the web, api and load runners | #done #bugfix | [2026-09](2026-09.md) |
| U-20260923-01 | 2026-09-23 | The step log is written as UTF-8 | #done #logging | [2026-09](2026-09.md) |
| U-20260922-03 | 2026-09-22 | Commit the PyPI publish workflow and setuptools bump | #done #release | [2026-09](2026-09.md) |
| U-20260922-02 | 2026-09-22 | Stop tracking .idea/ | #done #housekeeping | [2026-09](2026-09.md) |
| U-20260922-01 | 2026-09-22 | Adopt progress/architecture/docs-updates rules | #docs #migration | [2026-09](2026-09.md) |

## Batches

| File | Period | Entries |
|---|---|---:|
| [2026-10.md](2026-10.md) | 2026-10 | 20 |
| [2026-09.md](2026-09.md) | 2026-09 | 13 |
