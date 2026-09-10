# GOOS Test Quality Review

## Review story

As an imagegen maintainer preparing future refactoring, I want the current test
suite assessed against *Growing Object-Oriented Software, Guided by Tests*
principles so that we can preserve tests that describe stable behavior and
identify tests that merely mirror implementation details or relay parameters.

## Questions to answer

- Which tests exercise observable behavior through application, domain, or
  external-service interfaces?
- Which tests verify internal call choreography or values copied from the
  implementation under test?
- Which tests are likely to survive internal moves, renames, decomposition, or
  replacement?
- Where is a thin outside-in walking skeleton missing between otherwise well
  tested layers?
- Which findings are concrete enough to become tickets after maintainer review?

## Acceptance criteria

- Inventory the current Python and browser test suites and record their baseline
  result.
- Assess route, domain, persistence, provider, worker, CLI, template, and browser
  test surfaces.
- Distinguish legitimate boundary protocol assertions from implementation-detail
  interaction assertions.
- Rank findings by impact and include evidence, refactoring risk, and a candidate
  outcome suitable for later ticket writing.
- Record strengths that should be preserved.
- Do not create `tickets.md` or change tests or production code before review.

## Review boundary

This epic produces only the user story and the review in
[`test-quality-review.md`](test-quality-review.md). Accepted findings can be
converted into a separately reviewed `tickets.md` in the next specialization
workflow phase.
