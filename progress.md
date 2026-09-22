# progress.md: TestPioneer

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: X-7, X-14, L-7).

## Open

- **#2** Two Dockerfile sets duplicate each other (`Dockerfile_GUI` / `Dockerfile_NonGUI` and `Test_GUI_DockerFile` / `Test_NonGUI_DockerFile`); keep one.
- **#3** [DECIDE] `je-mail-thunder` is a declared dependency but nothing in `test_pioneer/` uses it: drop it or wire up mailing reports (workspace X-14).
