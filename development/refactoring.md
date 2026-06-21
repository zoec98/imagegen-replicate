# Refactoring Policy

When asked to refactor, do not change code immediately. First create or update
a focused refactoring note under `development/<todays_date>-refactoring-audit/refactor.md`.

For each module under review:

- State its intended responsibility at the top of the module in a comment
  block.
- State the same intended responsibility in the refactoring note.
- List functions/classes that do not match that responsibility.
- Identify duplicated behavior, near-duplicate code, and concepts implemented
  in multiple places.
- Propose moves, extractions, merges, or renames.
- Do not change code yet.
- For each proposed refactoring, list the behavior tests needed before the
  change.
- These tests must cover observable behavior and must not depend on the current
  internal structure.

Use refactoring notes as planning artifacts. They do not authorize silent
behavior changes.
