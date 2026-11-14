---
name: blast-radius
description: Find what a change can break outside the diff, name the one fact its safety depends on, and prove that fact by running real code. Use only when the user explicitly invokes blast-radius or explicitly asks for the blast radius of a change or what that change could break. Ordinary review is not a trigger.
---

# Blast Radius

Find breakage the diff does not show. Use only when the user explicitly invokes `blast-radius` or explicitly asks for the blast radius of a change, or what that change could break. Ordinary review is not a trigger.

`mattpocock-skills:code-review` checks the change against repository standards and the requested behavior. This skill checks what else breaks if the change ships. Load `mattpocock-skills:research` only when the safety fact depends on a primary source you cannot read in the checkout. If that skill is unavailable, continue from the sources you can read and say what remains unverified. Do not start extra reviewers unless the user already requested them.

Listing callers is not the job. The job is the breakage a symbol search misses.

## Prove the fact

A writeup that sounds right is not evidence. Find the one fact the change's safety depends on and prove it by running code.

For that fact, go as far down this list as is cheap, and record the level you reached:

1. **Said.** You asserted it. On its own, the fact is unproven.
2. **Cited.** A real `file:line` in this repository, or in library source you opened.
3. **Walked.** You stepped through the failure and it does not reach.
4. **Ran.** A script or test calls the real code and fails loudly if the fact is wrong.
5. **Reproduced.** You observed it in the running application.

Level 4 is usually one small script that imports the same code the application ships and calls the function under concern.

## Steps

1. Read the change. Include the diff, the symbols it adds, changes, and deletes, and the behavior the diff does not spell out. Read the commits that produced it, plus review comments that are already in the checkout or that the user supplied. Use the version control already available. Do not require a particular hosting client.
2. Find the one fact safety depends on. A change that looks risky is often safe because of a single fact, such as "this call only drops cache entries that are already dead, and it does nothing else." When that fact holds, most risky cases clear at once.
3. Look where search stops. Read the source of a library you call, including its pinned version and any local patch. Work out when the code runs: microtasks, unmount, teardown, and framework-specific timing. Follow what a symbol search misses: JSON an API returns, a database column, a wire format, another language reading the same bytes, a feature flag, and code three hops downstream.
4. Keep a risk only when it has a real chance of happening and a real cost. Cite a real `file:line`. A search that finds nothing is still an answer. Do not invent a caller or an API.
5. Prove the one fact. Write a script or test that runs the real code, run it, and keep the command and the output. If you cannot run it, mark the fact unproven and name what blocked the run.

## Report

- **What it does.** What changed, including the part that is not obvious from the diff.
- **The key fact.** The one fact safety depends on, the proof level reached, and the command plus output when you ran code. If you could not prove it, write unproven.
- **Risks.** For each risk: how it breaks, the `file:line`, how likely it is, how bad it is, and the check that would catch it. Include the run output for the risks that matter.
- **Cleared.** What you checked, and the evidence that it is fine.

Cite code you opened. Strip secrets and private data before the report leaves the workspace.
