# progress.md: TestPioneer

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: X-7, X-14, L-7).

## Open

- **#3** [DECIDE] `je-mail-thunder` is a declared dependency but nothing in `test_pioneer/` uses it: drop it or wire up mailing reports (workspace X-14).
- **#8** Platform roadmap, phase 3 (PR #32, `docs/roadmap-platform-improvements.md` §5): runner report adapters, the merge into `test_pioneer.models.result`, the consolidated JSON and HTML report, optional JUnit output, and integration tests with several runners.
- **#9** Platform roadmap, phase 4 (§1 and §2): the YAML-aware editor and the run/report workspace. The UI belongs in PyBreeze; this repository offers it `validate --format json`, the schema and the result model (`architecture.md` §6).
- **#10** Platform roadmap, phase 5 (§6): one complete end-to-end README example in all three languages, the artifact and report documentation, and migration notes.
- **#11** [DECIDE] The sample workflows under `test/unit_test/` do not run what they name, so the CI integration jobs pass without executing a script. `python -m test_pioneer validate` reports each case:
  - `download_file/download_file.yml` gives `file_name` where the step reads `file_path`, so the step is rejected. With the key corrected, every CI run would download a 512 MB file from a bare IP address; pick another URL first.
  - `run_multi_time/` and `run_folder/` name their scripts with a leading `/`, which resolves from the filesystem root (the fault fixed for the Docker samples in U-20260923-04).
  - `parallel_run/` names `./test/test1.json`, relative to its own folder, while CI runs it from the repository root.
- **#12** [DECIDE] `process_manager_instance.name_set` is filled by every `execute_yaml` call and never emptied, so a second call in the same Python process with a step name the first one used stops with "job name duplicated" before running anything (the test suite clears the set in `test/conftest.py`). Clearing it per run would also drop the names of programs a previous call left open for a later `close_program`.
- **#13** The runner packages do not read `TEST_PIONEER_ARTIFACT_DIR` / `TEST_PIONEER_RUN_ID` yet and exit 0 when an action fails (`architecture.md` §6). Native support belongs in each runner's repository: write reports and screenshots into the directory, and exit non-zero on a failed action. Cross-repository.
