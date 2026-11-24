# ADR Curation

Reduce the history readers need to load, not the history they can recover. Apply only to the requested subsystem, decision set, or navigation scope. Use the entry skill's mode: audit returns findings without changing the target; explicit implementation permission covers only the requested changes.

## Classify decisions, not filenames

1. Start at the instructions, overview, and current architecture or operations guide people actually follow. Find the owned ADR index or decision folders and inventory in-scope records and their incoming links. Open the relevant decisions and trace explicit replacements. Check released compatibility, migration, and rollback instructions when those are affected.
2. Compare each relevant decision with the current governing contract, representative code, and tests. Record the decision ID/link, evidence, proposed state, and current owner or replacement where applicable:
   - **Current:** still an intentional constraint. Keep it discoverable.
   - **Superseded:** a verified successor owns the decision. Link to it.
   - **Retired:** the decision no longer applies, with no successor. Verify that supported versions, migrations, or rollback do not still need it as live guidance.
   - **Unverified:** evidence conflicts or is missing. Name the gap; do not silently remove it from active navigation.
3. Do not use age or implementation drift alone as proof a decision was overturned. Classify mixed records by decision: keep live constraints reachable and label only the superseded portions. Preserve proposed decisions as pending, not current rules. This pass does not approve new architecture decisions.

## Reduce default reading

- In report-only mode, return the scoped inventory and propose the smallest navigation and wording changes. Write no index, ADR status, or architecture summary into the target.
- In implementation mode, use the existing current architecture or operations owner. Put only the verified constraints a reader needs there. Offer a short topic-based index linking to current owners and relevant ADRs on demand; reuse an existing index. The index is navigation, not a second source of truth. Route root instructions to the relevant current owner rather than making readers load the whole ADR tree.
- Preserve old bodies, IDs, anchors, and published links. When in scope, add a short status or replacement pointer without rewriting the rationale. Do not move or delete records as routine pruning. Treat actual archive moves or deletion as separate choices; inventory links and rollback impact first. Keep compatibility and rollback instructions reachable even if historical background is no longer a default read.

## Verify both paths

Trace one representative current maintenance task from its usual entry point: it should find the governing constraints without opening superseded text. Then trace one historical inquiry, such as a compatibility or rollback question, from the index or replacement pointer to the original rationale. Check all affected relative links, anchors, and replacement chains; flag missing targets, loops, or unresolved evidence. In implementation mode also check the diff and state any paths you did not verify.
