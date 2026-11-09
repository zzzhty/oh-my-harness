---
status: accepted
---

# Status surface and target index

`omh status` is the operator's window. Two changes:

1. **Overview by default.** Without `--skills-root`, status lists every
   installed target the home knows instead of one implied target. The home
   keeps a `targets.json` index (`target → {harness, skillsRoot}`), written by
   `install`/`update` and pruned by `uninstall`; the default harness roots
   (`~/.codex`, `~/.claude`) are probed alongside it so pre-index installs are
   visible. The index is only a hint: every listed target's `.omh-owner.json`
   receipt is read live and classified — `installed` (with drift and recovery
   needs computed from the receipt), `foreign` (another owner), `other-home`
   (omh-owned but managed by a different home) or `missing` (indexed, receipt
   gone). Status never writes; exit code 0 only when every target is clean.
2. **Readable by default, machine on request.** The default output is a short
   human summary (home, launcher, runtimes with versions, per-target state,
   final verdict line). `--json` returns the same information as data; scripts
   and tests consume `--json`. The CLI reconfigures its stdout to UTF-8 on
   every platform, so piped text output is deterministic instead of following
   the Windows ANSI codepage.

`plan` remains a per-target preview and is unchanged. A single explicit
`--skills-root` keeps single-target status, with the same states and exit
semantics.
