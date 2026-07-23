# Development Notes

This directory holds contributor-facing planning, audits, and focused internal
guidance. End-user setup and usage belong in `README.md`.

## Focused Guidance

- `provider-models.md`: provider/model registry behavior.
- `generated-images.md`: generated image storage and metadata.
- `prompt-palettes.md`: prompt palette behavior.
- `ui-guidance.md`: browser JavaScript source layout, build/test workflow, and
  UI implementation conventions.
- `refactoring.md`: refactoring review guidance.
- `security-boundary.md`: security-sensitive route, file, and browser
  boundaries.

## Workstreams

Create one date-prefixed directory per feature or workstream.

Suggested structure:

```text
YYYY-MM-DD-short-name/
|-- user-stories.md
|-- tickets.md
|-- audit.md
`-- notes.md
```

Use `user-stories.md` for user-visible needs, `tickets.md` for actionable work,
`audit.md` for review findings, and `notes.md` for observations that are not
ready to become tickets.
