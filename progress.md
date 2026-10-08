# progress.md: TestPioneer

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: X-13, X-14, L-7).

## Open

- **#9** [BLOCKED] Platform roadmap, phase 4 (PR #32, `docs/roadmap-platform-improvements.md` §1 and §2): the YAML-aware editor and the run/report workspace, in PyBreeze. Everything it needs from here exists: `validate --format json` (also on standard input, for an unsaved buffer), the schema, `run` with its exit status, and the report files (`architecture.md` §6). It waits on two things outside this repository, as found on 2026-10-08:
  - PyBreeze's report viewer, language service and tool table exist only on a local stack of 15 commits that is not pushed (`core/shared-contracts` … `docs/tutorials`, on `origin/dev`). The TestPioneer actions have to be built on that stack once it lands.
  - `run`, `validate` and `schema` are not in a released `test_pioneer`; PyBreeze's item #106 gives `test_pioneer` a floor of 0.1.34, and the floor these actions need is the first release that carries this PR. The PR has to be merged and released first.
  - Then, in PyBreeze: two actions in the TestPioneer menu, "Validate" (`validate --format json`, shown as problems) and "Run with report" (`run --report_formats json,html,junit` with absolute `--report_path` and `--artifacts_path`), opening `testpioneer-junit.xml` in its viewer, which reads that file as it is; its hand-kept list of workflow keys replaced by the published schema; diagnostics for `.yml` in its language server.
- **#13** [BLOCKED] Native support in the runner packages (`docs/artifacts.rst`, "Native Support"; `architecture.md` §6) is written and waits to be merged and released. One draft pull request to `dev` per runner, opened 2026-10-08:
  - APITestka #149: exit status of `python -m je_api_testka` and `apitestka run`; reports below `TEST_PIONEER_ARTIFACT_DIR`.
  - WebRunner #115: exit status of `python -m je_web_runner`; reports below the directory.
  - AutoControlGUI #500: exit status of the legacy flags; reports below the directory.
  - FileAutomation #108: exit status of the legacy flags (it writes no report).
  - LoadDensity #120: reports below the directory (its exit status has been on `dev` since its PR #118).
  - The exit status does not depend on who started the runner, as in LoadDensity. Each pull request names that as a behaviour change.
  - Once they are released: say so in `docs/artifacts.rst`, `docs/reports.rst` and `architecture.md` §6 instead of "the released runner packages exit with status 0", raise the dependency floors in `pyproject.toml` and `dev.toml` if the README example is to rely on it, and drop the `artifacts:` lines from that example.
