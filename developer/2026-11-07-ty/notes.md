# Type checking with ty

`uv run ty check src tests` checks the Python application and tests. The
initial run reported 78 diagnostics. The cleanup aligns the generation and
HTTP client interfaces with their implementations, checks values read from
storage, and makes test fixtures match the contracts they exercise.

Keep both directories in scope and fix diagnostics at the relevant boundary
without relaxing rules for the whole project.
