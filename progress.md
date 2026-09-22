# progress.md: TestPioneer

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: X-7, X-14, L-7).

## Open

- **#2** Two Dockerfile sets duplicate each other (`Dockerfile_GUI` / `Dockerfile_NonGUI` and `Test_GUI_DockerFile` / `Test_NonGUI_DockerFile`); keep one.
- **#3** [DECIDE] `je-mail-thunder` is a declared dependency but nothing in `test_pioneer/` uses it: drop it or wire up mailing reports (workspace X-14).
- **#5** [UNVERIFIED] `run_folder` passes a list of `Path`s to the chosen runner, but only `gui-runner` maps to `execute_files`; web, api and load still map to `execute_action` (found by reading the code).
- **#6** `parallel_run` spawns `je_web_runner`, `je_api_testka`, `je_load_density` and `je_auto_control` but not `automation_file`, although file steps exist.
