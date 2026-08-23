---
status: accepted
---

# Establish the oh-my-harness identity and manager home

The current repository, distribution, and Codex marketplace identity is
`oh-my-harness`. Manager-owned runtime state lives under one harness-neutral
`OH_MY_HARNESS_HOME`, defaulting to `~/.oh-my-harness`; product roots such as
`$CODEX_HOME`, `~/.zcode`, and `~/.claude` remain responsible only for their
own distribution and runtime state.

The manager home has one fixed layout:

```text
~/.oh-my-harness/
├── repo/
├── venv/
├── bin/
│   ├── oh-my-harness
│   └── omh
└── state/install.json
```

`repo/` is the one managed installation checkout. `venv/` is the one
manager-owned Python environment; multiple named environments are not a current
seam. The initializer rebuilds this environment rather than copying or moving
an existing venv because Python environments may contain absolute paths.

`oh-my-harness` is the canonical command and `omh` is its short form. The
initializer writes both as ordinary platform launchers with identical content,
not filesystem links. They dispatch to one platform wrapper, which uses the
absolute manager-home tooling interpreter and the same registry-selected
refresh and closure entry points. Users do not activate the venv.

The initializer obtains its Git source from an explicit `--repository` or the
invoking checkout's `remote.origin.url`; it does not embed an obsolete or
unverified repository URL. It records the exact repository, ref, revision,
harness, and owned paths in `state/install.json`. It does not edit shell
profiles or machine-wide `PATH` state.

A first installation clones into `repo/`. The one repository-relocation path is
`--adopt-current-checkout`, which is valid only when the invoking checkout is
already the exact `<manager-home>/repo` directory and every other manager-owned
path is absent. It does not adopt arbitrary repositories or merge existing
manager state.

An initializer failure leaves `state/install.json` at `status: installing`.
Repeating the same adoption may resume only when that state has the exact
current schema, product, repository, ref, revision, harness and owned paths;
the launcher directory must contain only the two ordinary launchers with exact
generated content, and any venv must be an ordinary directory. Ready state,
drift, extra entries and links are not resumable installation inputs.

The harness registry owns the one-time Codex marketplace migration. The former
`my-codex` marketplace name is retained only as a structured retired identity,
not an alias or alternate reader. If retired config or cache state exists, a
normal refresh fails after printing the bounded plan. An explicit
`--migrate-marketplace` plus confirmation installs and verifies the new
marketplace before retiring the old selectors, source, and cache namespace.
Closure rejects any remaining retired state.

The registry keeps an ISO calendar-date `schemaVersion` (`YYYY-MM-DD`), initially
`2026-08-22`. It advances only when the registry schema changes; incremental
labels such as `v1`, `v2`, and `v3` are not used.

Repository relocation has a separate explicit input,
`--migrate-from-repo <absolute-path>`. It permits replacement only when the
existing Codex instructions target is a symlink to that former checkout's exact
`AGENTS.md`. The usual live replacement confirmation remains mandatory;
`--yes` cannot approve it. Unknown links remain hard failures.

If relocation has already made the exact retired local marketplace source
unreadable, the confirmed migration first detaches only that source registration
so Codex discovery can run. Retired plugin selectors and cache remain intact
until the new marketplace has been installed and verified; their later removal
still uses the original bounded inventory. A dry run stops at this breakpoint
because it cannot simulate Codex discovery against an unapplied detachment.

Active environment variables use only `OH_MY_HARNESS_*`. The old manager
variables and script names have no compatibility aliases. A retired managed
header in an already-distributed Codex agent support file is recognized only
long enough to rewrite that file in place with the current marker.

Historical ADRs, research, Git commits, pull-request URLs, the upstream Matt
skill mirror, and the external Git remote slug may retain the former name when
it is an immutable or server-owned identity. A server-side repository rename is
a separate external cutover; it must update `remote.origin.url` only after the
new remote exists and is verified.
