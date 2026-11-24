---
name: create-verification-skill
description: Generate a project-local verification skill that launches the real app, drives one user path, and keeps the evidence. Use only when the user explicitly invokes create-verification-skill or explicitly asks for a control skill or a scripted way to prove this project's UI, CLI, or service behavior. Ordinary testing is not a trigger.
---

# Create a Verification Skill

Generate a project-local skill that drives the real app the way a user does, in whatever language, framework, or platform the project uses. Use only when the user explicitly invokes `create-verification-skill` or explicitly asks for a control skill, or for a scripted way to prove this project's UI, CLI, or service behavior. Ordinary testing is not a trigger.

Write the generated skill for the next agent. It will be read cold, mid-task, by an agent that has never seen the app.

## 1. Interview the repository

Answer these from the codebase. Ask the user only what you cannot observe:

- **Surface.** What a user actually touches: a web UI, a CLI or TUI, a desktop app, an API, a mobile app, or a library. A repository can have several. Pick the primary one and note the rest.
- **Run.** How the app starts locally. Prefer the project's own documented dev command. Note ports, environment variables, seed data, and auth.
- **Drive.** How an agent can interact programmatically. Prefer a driver the repository already has. Otherwise use a browser automation protocol for a web or desktop UI, an isolated terminal session for a CLI or TUI, or plain HTTP for a service.
- **Observe.** What evidence can be captured: screenshots, terminal transcripts, response bodies, logs, exit codes, or database state.
- **Isolate.** Whether two instances can run side by side, including ports, data directories, and profiles. If they cannot, say so in the generated skill. Refusing to drive a shared instance is safer than corrupting the user's session.

If the checkout does not build or start as-is, report the exact failure before generating. Creating or proving a verification skill does not authorize repairing the application, shared configuration, or service; make those repairs only if already in scope. A skill written against a broken base teaches the wrong steps. When an irrelevant missing asset blocks startup, such as a static directory the API never serves or a sample config, the generated skill may create it, mark it as verification scaffolding, and remove it during cleanup. Keep scaffolding within the isolated run and do not overwrite existing files.

## 2. Choose where the skill is written

Use the target project's existing skill location: the directory its own instructions name, or the single directory that already contains its `SKILL.md` files. If more than one location exists, ask which one to use. If none exists, ask for a directory before writing any file. Do not invent a product-specific default path.

Create `verify-<slug>/SKILL.md` in that location. `<slug>` is a short name for the app. The frontmatter must include `name: verify-<slug>` and a `description` that names the app, the surface, and when to use the skill. Without frontmatter the skill does not register.

Ground every section in what the interview found. Leave no placeholders:

- **Launch.** The exact command that starts the app for verification, and how to tell it is ready, such as a log line or a prompt. Launch must reach a usable state from an empty data directory, including migrations and seed data. Ready means usable, not merely that a process answers. A database health check can pass while its init scripts are still running. Include teardown. For a short-lived CLI or TUI there is no server to keep alive: build or install once, then start each drive in its own isolated terminal session.
- **Doctor.** One read-only check that answers whether this instance is worth driving: the process is up, the version or build is the one you started, the port is owned by this run, and auth is valid. Run this first whenever anything looks off.
- **Drive.** The recipe with real selectors or commands from this repository. Prefer stable handles, such as accessible names, data attributes, prompt strings, and route paths, over coordinates and tab order.
- **Evidence.** What to capture and where it goes. Exercise the real user path, not an internal setter or a test-only endpoint. Capture the action and the resulting state, not only the final screen. Use test identities where possible and redact credentials, personal data, and sensitive request or response content before retaining or sharing evidence. Verify side effects, such as files written, rows inserted, or messages sent, beside what is visible. Use stand-ins only where a production boundary already isolates an external system. When the safe path is a dry-run or test mode, observe files, network activity, and version-control refs to see what it actually skips. A dry-run can still touch the network or open a window.
- **Cleanup.** Tear down instances this run created. Stop the processes you started. Do not kill by process name. Cleanup removes instances and scratch state, and it leaves the evidence in the location the skill names.
- **Helpers.** Any script the skill ships is executable, and the skill body shows the command that runs it. A helper the reader has to reverse-engineer is not a helper.

## 3. Seed the feature map

Inside the generated skill, create `features/README.md` and one file per user-facing feature you can identify. Start with the top three to five, taken from routes, commands, menus, or docs. Follow the shape in [references/feature-map-example/](references/feature-map-example/): an index README and one file per feature.

Each feature file answers, from the user's point of view, what the feature is, how to reach it, how to drive it, and which observable end state proves it works. Use these four H2 headings, in order: `Sub-features`, `How to get to it (user POV)`, `Driving it with <driver>`, and `Gotchas`. Replace `<driver>` with the name of the driver from the interview. If the seed data lacks a precondition a journey needs, the journey reports a failure and the reason goes in that feature's `Gotchas`. Do not weaken the journey to make it pass. The map is the project's maintained verification source. A proof that drives one convenient entry point is incomplete when the map lists others.

Keep the map inside the generated skill and update it in place when behavior changes.

## 4. Prove the generated skill once

Run the generated instructions end to end once: launch, doctor, drive one mapped feature, capture evidence, and clean up. One feature is enough. The map exists so later runs can cover the rest. After cleanup, confirm the evidence still exists at the named location. A cleanup that deletes the proof fails this step. Fix failures in the generated skill within scope; report application or shared-environment failures unless repair is authorized. Run the generated cleanup after every failed attempt so a broken run does not leave processes or ports behind. A generated skill that was never executed is a draft, not a deliverable.

If you proved it in a stand-in for the real target, such as a container instead of a fresh machine or a local stack instead of a remote one, list every setup step the stand-in performed that the target will not. Those steps stay unverified until a run on the real target covers them.

## Report

Name the skill path, the feature you drove, the evidence path that survived cleanup, and any stand-in steps that remain unverified.
