# Development Artifacts

This directory holds internal working material for `imagegen`.

Use it for progressive refinement:

```text
observation -> user story -> tickets -> tests -> code -> audit -> follow-up tickets
```

## Map

- `security-boundary.md`: security boundaries and audit inputs.
- `decisions/`: architecture and product decisions.
- `epics/`: feature workstreams with user stories, tickets, notes, and audits.
- `audits/`: cross-cutting audits not owned by one epic.
- `refactors/`: refactoring reviews and proposed behavior tests.

## Conventions

- Keep `README.md` focused on end users.
- Keep `AGENTS.md` focused on project-wide agent and contributor instructions.
- Put future `user-stories.md`, `tickets.md`, `audit.md`, and `notes.md` files inside an epic directory under `development/epics/`.
- Add `Open Questions`, `Risks`, and `Gaps` sections when useful.
- Prefer behavior-focused tickets and tests that should survive internal remodeling.
