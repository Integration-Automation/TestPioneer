# progress.md: TestPioneer

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: X-13, X-14, L-7).

## Open

- **#9** Platform roadmap, phase 4 (PR #32, `docs/roadmap-platform-improvements.md` §1 and §2): the YAML-aware editor and the run/report workspace. The UI belongs in PyBreeze; this repository offers it `validate --format json`, the schema, the run result and the report files (`architecture.md` §6).
- **#13** The runner packages do not read `TEST_PIONEER_ARTIFACT_DIR` / `TEST_PIONEER_RUN_ID` yet and exit 0 when an action fails (`architecture.md` §6). Native support belongs in each runner's repository: write reports and screenshots into the directory, and exit non-zero on a failed action. Until then a step declares its report files with `artifacts:`. Cross-repository.
