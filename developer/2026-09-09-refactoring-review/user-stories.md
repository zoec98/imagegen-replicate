# Refactoring Review User Story

## Maintainer story

As an imagegen maintainer, I want an evidence-backed, severity-ordered review
of the current repository so that refactoring work removes real duplication and
unsafe change boundaries without changing observable behavior or introducing
speculative abstractions.

## Acceptance criteria

- Review current Python, editable browser JavaScript, templates, CSS, and tests.
- Identify duplicated or nearly duplicated behavior, oversized modules and
  functions, misplaced responsibilities, and code that is difficult to test.
- Give file and line evidence for every finding.
- Recommend the smallest remedy that removes the underlying cause.
- Name the observable behavior tests required before each refactor.
- Distinguish actionable findings from intentionally repetitive provider data
  and small duplication that is cheaper to keep.
- Define one image-card size, density, layout, and interaction contract for the
  main gallery, upload browser, and trash instead of preserving incidental
  differences among them.
- Do not change application behavior as part of the review.

## Non-goals

- Implementing the findings.
- Reformatting or reorganizing files only to reduce line counts.
- Replacing explicit provider differences with a generic framework.
- Treating generated `src/imagegen/static/app.js` as source code.
