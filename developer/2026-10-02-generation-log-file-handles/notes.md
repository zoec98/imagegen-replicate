# Generation log file descriptor exhaustion

The reported long-running web server failed when Werkzeug attempted to create a
request selector: `OSError: [Errno 24] Too many open files`. The supplied snapshots
showed four open SQLite database handles after one generation and eight after
another.

## Reproduction and cause

An isolated temporary `SQLiteGenerationLog` reproduced the exact selector error
by repeatedly calling `get_result("missing")` and opening/closing a
`selectors.DefaultSelector`. Disabling cyclic garbage collection and lowering
the subprocess soft file limit to 64 made descriptor accumulation deterministic.
No provider calls or user database access were involved.

Ranked hypotheses were unclosed SQLite connections, accumulating provider HTTP
connections, and unclosed request selectors. Closing only the SQLite connections
made the same 100-iteration reproduction pass.

SQLite connection context managers commit or roll back transactions; they do
not close the connection. All generation-log operations used that context and
relied on eventual garbage collection for closure. The shared `_connect`
context now wraps the transaction in `contextlib.closing`, preserving transaction
behavior and closing on both normal and exceptional exits.

## Regression coverage

`uv run pytest tests/test_generation_log.py -k 'close_connections or rolls_back'`
failed for both new tests before the fix. Tests retain real connections to
prevent garbage collection from hiding missing closure, exercise repeated
generation lifecycle writes and history reads, and check rollback and closure
when the second request insert fails.

This establishes a concrete SQLite resource leak and fixes it. The original
long-running process was not available at its failure point, so the snapshots
do not rule out other sources of descriptor growth.
