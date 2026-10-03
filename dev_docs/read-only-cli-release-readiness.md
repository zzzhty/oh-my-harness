# Read-only public CLI release readiness

## Scope

Candidate against `47799a71424500dc6dea9ca09c0e215fa7cb902b` (VERSION remains 1.0.0).
No release, tag, push, installed-user migration, plugin identity change, or upstream skill-content change is included.

- Public status/version/check/doctor skip mutation locking and runtime bootstrap.
- An existing interpreter is probed without bytecode writes. Missing/unstartable runtime, wrong venv prefix, unsupported Python, or missing imports produces a nonzero error and repair guidance; JSON diagnostic commands produce a structured preflight error.
- Command traces and bootstrap progress use stderr; successful status/version JSON stays parseable.
- Install/refresh/remove previews avoid the creating ManagerLock. Public previews propagate no-bytecode and no-optional-Git-lock settings.
- Concurrent observations are not guaranteed to be an atomic installation snapshot.
- Update `--check` still fetches remote metadata; it is deliberately outside the no-write preview contract.

## Validation

Linux, Python 3.12.14, isolated temporary HOME/USERPROFILE; no network installation required.

- Full command: `HOME="$ISO_HOME" USERPROFILE="$ISO_HOME" PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_*.py' -v`
- 316 tests: 308 passed, 7 Windows-only skips, 1 pre-existing host-sensitive failure.
- Failure: `test_manager_environment.UserEnvironmentTests.test_shell_execution_quotes_paths_and_deduplicates_entries` with zsh and initially empty PATH. The host zsh supplies `/usr/local/bin:/usr/bin:/bin:/usr/games`, violating the test's empty-PATH expectation. The same failure reproduces from a clean `git archive HEAD` baseline running only `test_manager_environment.py` (13 tests, 1 failure).
- All eight new real public-launcher tests pass, including no-write snapshots of the entire isolated user tree (file bytes, mode, mtime, directories and symlinks), help/option abbreviations, absent/held manager locks, valid JSON, explicit runtime failures, and failing harness validation.
- `python -m json.tool` succeeds for marketplace, install manifest, harness registry and registry schema.
- Repository plugin validation passes for watcher, workflow and mattpocock-skills; no packaged content changed.
- `git diff --check` passes.

## Remaining gates

- Independent review of the candidate.
- Windows public-launcher execution still requires Windows CI; Linux skips are not Windows validation.
- Resolve or explicitly accept the baseline host-zsh test limitation before claiming a completely green release suite.
- Publication requires separate authorization. Existing installed launchers only receive the changed bootstrap through the normal managed update/repair distribution process.
