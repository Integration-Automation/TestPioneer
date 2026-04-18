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

### Static Analysis Compliance (SonarQube / Codacy / Pylint / Bandit)

All code must pass SonarQube Python rules, Codacy quality gates, and equivalent
linters (Pylint, Flake8, Bandit, Ruff) without new issues. Follow these rules:

**Complexity & Size**
- Cognitive Complexity per function ≤ 15 (SonarQube `python:S3776`).
- Cyclomatic complexity ≤ 10; refactor via extraction when exceeded.
- Function length ≤ 50 lines; file length ≤ 750 lines (`python:S104`).
- Max 7 parameters per function (`python:S107`) — use dataclasses / kwargs otherwise.
- Max nesting depth ≤ 4 (`python:S134`).

**Duplication & Dead Code**
- No duplicated blocks ≥ 3 lines (Sonar duplication detector); extract helpers.
- Remove unused imports, variables, parameters, private methods (`python:S1481`, `S1854`).
- No unreachable code after `return`/`raise`/`break`/`continue` (`python:S1763`).
- No commented-out code (`python:S125`).

**Naming & Style (PEP 8)**
- `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE` for constants (`python:S117`, `S100`, `S101`).
- Module names lowercase, no hyphens. Line length ≤ 120 chars.
- No single-letter names except loop counters (`i`, `j`, `k`) or `_`.

**Correctness & Bugs**
- No bare `except:` — always catch specific exceptions (`python:S5754`, Bandit `B110`).
- Do not silently swallow exceptions — log or re-raise (`python:S2737`).
- No mutable default arguments (`python:S5612`).
- No identical expressions on both sides of operators (`python:S1764`).
- No hardcoded credentials, tokens, IPs, or file paths (`python:S2068`, `S1313`, Bandit `B105`/`B106`).
- Use context managers (`with`) for file and resource handling (`python:S5332`).
- Comparisons with `None`, `True`, `False` must use `is` / `is not`.
- String formatting: prefer f-strings; never use `%` with untrusted input.

**Security (Bandit / Sonar hotspots)**
- No `assert` in production code paths (Bandit `B101`) — use explicit checks that raise.
- No `shell=True`, `os.system`, or unsanitized `subprocess` input (`B602`–`B605`).
- No `tempfile.mktemp`; use `tempfile.NamedTemporaryFile` or `mkstemp` (`B306`).
- No weak crypto (`md5`, `sha1`) for security purposes (`B303`, `B324`).
- No `yaml.load` without `SafeLoader` (`B506`).
- No `requests` calls without `timeout=` (`python:S4830` equivalent).
- No SSL verification disabled (`verify=False`) in production.

**Typing & Documentation**
- Type hints on all public function signatures; `mypy --strict` clean for new code.
- Public modules, classes, and functions require docstrings (Pylint `C0114`–`C0116`).
- Avoid `Any`; prefer concrete types or `Protocol`.

**Tests**
- Test files named `test_*.py`; test functions `test_*`.
- Avoid `assertTrue(x == y)` — use `assertEqual` (clearer failure messages).
- No tests that always pass (empty body or tautological assertion) (`python:S2187`).

## Git Commit Rules

- Write commit messages in English, imperative mood (e.g., "Add parallel runner timeout").
- **Do NOT mention any AI tool, assistant, or model name in commit messages or Co-Authored-By lines.**
- Keep subject line under 72 characters; add body for non-trivial changes.
- Each commit should be a single logical change — do not mix unrelated fixes.

## Dependencies

Core: `je_web_runner`, `je_load_density`, `je_api_testka`, `je-mail-thunder`, `automation-file`, `psutil`, `pyyaml`
Optional GUI: `je_auto_control`
