# CLAUDE.md — TestPioneer

## Project Overview

TestPioneer is a YAML-driven automation test framework for CI/CD pipelines (Python 3.10+).
Supports GUI, Web, API, and Load testing through pluggable runners.

- **Package**: `test_pioneer` (PyPI)
- **Repo**: `Integration-Automation/TestPioneer`
- **Docs**: https://testpioneer.readthedocs.io/

## Architecture

```
test_pioneer/
├── executor/          # Core execution engine (YAML step dispatch)
│   ├── browser/       # URL operations
│   ├── file/          # File processing steps
│   ├── program/       # External program launch
│   ├── run/           # Execution orchestration, parallel runs, process management
│   ├── test_recorder/ # Logging & video recording
│   └── time/          # Wait/delay steps
├── logging/           # Logging singleton
├── process/           # OS process execution & management
├── project/           # Template scaffolding
└── utils/             # Exceptions, package checks
```

## Build & Test

```bash
pip install -e ".[gui]"        # Install with GUI support (dev)
pip install -e .               # Install without GUI
pytest                         # Run tests (testpaths: test/)
```

## Coding Standards

### Design Patterns & Software Engineering

- Apply appropriate design patterns: Strategy for runner dispatch, Factory for step creation, Singleton for shared state (logger).
- Follow SOLID principles — single responsibility per module, open for extension via new runners/steps.
- Prefer composition over inheritance.
- Keep functions small and focused; each function does one thing.
- Use type hints on all public APIs.
- No dead code — remove unused imports, variables, functions, and classes immediately.
- No commented-out code blocks; use version control for history.

### Performance

- Use generators and lazy evaluation for large data sets.
- Avoid unnecessary copies of data structures; prefer in-place operations when safe.
- Use `subprocess` with explicit resource limits; always set timeouts on I/O operations.
- Profile before optimizing — avoid premature optimization, but fix known hot paths.
- Prefer `pathlib.Path` over string concatenation for file paths.
- Use connection pooling and session reuse for HTTP-based runners.

### Security (Mandatory)

- **Never** trust external input: validate and sanitize all YAML content, CLI args, and file paths before use.
- **Never** use `shell=True` in `subprocess` calls — pass argument lists to prevent command injection.
- **Never** use `eval()`, `exec()`, or `pickle.loads()` on untrusted data.
- **Never** log secrets, tokens, or credentials.
- Validate file paths against directory traversal (`../`) before any read/write.
- Pin dependency versions in `requirements.txt`; audit dependencies for known CVEs.
- Apply least-privilege: processes spawned by the framework should not run as root unless absolutely required.
- Use `secrets` module instead of `random` for any security-sensitive value generation.

### Code Hygiene

- Remove all unused code blocks, dead branches, and unreachable logic.
- No `TODO` or `FIXME` comments in committed code — file an issue instead.
- Keep imports organized: stdlib, third-party, local — separated by blank lines.
- All public modules and classes must have docstrings.

## Git Commit Rules

- Write commit messages in English, imperative mood (e.g., "Add parallel runner timeout").
- **Do NOT mention any AI tool, assistant, or model name in commit messages or Co-Authored-By lines.**
- Keep subject line under 72 characters; add body for non-trivial changes.
- Each commit should be a single logical change — do not mix unrelated fixes.

## Dependencies

Core: `je_web_runner`, `je_load_density`, `je_api_testka`, `je-mail-thunder`, `automation-file`, `psutil`, `pyyaml`
Optional GUI: `je_auto_control`
