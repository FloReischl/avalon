## Prompt2Code (P2C) – Patch Format

P2C is Avalon's deterministic source-code transport layer. It does not interpret code and must not use fuzzy matching or implicit corrections.

Patch format:
- UTF-8, LF only.
- One or more sequential changes.
- Change header:
  1. relative file path
  2. exact mode
- Changes separated by exact line `p2c-next-change`.
- Syntax/markers are case-sensitive and whitespace-exact.
- No comments or escaping in structural syntax.

Supported operations:

### string-replace
<path>
string-replace
[optional: p2c-position: N | p2c-count: N]
p2c-old
<exact non-empty old>
p2c-new
<exact non-empty new>

Default: `old` must occur exactly once in the current simulated content.

Optional selectors:
- `p2c-position: N` selects exactly the N-th occurrence, 1-based.
- `p2c-count: N` requires exactly N occurrences and replaces all of them.
- `p2c-position` and `p2c-count` are mutually exclusive.
- `N` must be a positive integer.

### string-remove
<path>
string-remove
[optional: p2c-position: N | p2c-count: N]
p2c-old
<exact non-empty old>

Default: `old` must occur exactly once.

Optional selectors:
- `p2c-position: N` removes exactly the N-th occurrence, 1-based.
- `p2c-count: N` requires exactly N occurrences and removes all of them.
- `p2c-position` and `p2c-count` are mutually exclusive.
- `N` must be a positive integer.

### file-create
<path>
file-create
p2c-new
<complete non-empty file content>

Target must not exist. Missing parent directories are created during write.

### file-delete
<path>
file-delete

Target must exist and be a regular file. No payload.

Payload/newline semantics:
- Payload is preserved exactly.
- The LF directly separating payload from a following marker is structural and excluded from payload.
- Additional LF before the marker belongs to payload.
- At EOF, remaining content including any final LF belongs to payload.
- Exact marker lines are reserved; no escaping exists.

Execution:
- Paths resolve relative to `--target-dir`.
- Resolved paths, including symlinks, must remain inside target-dir.
- Parse, validate and simulate ALL changes before filesystem writes.
- Changes execute sequentially in memory; later changes see earlier results.
- Multiple changes may target the same file.
- Each affected file is written once using its final simulated state.
- No filesystem changes occur if parsing/simulation fails.
- No rollback/compensation after write phase begins.

Diagnostics:
- Errors use relative path + global change number.
- Failed string match also prints exact `p2c-old`.
- Success reports each affected file once with relative path.

Design principle:
P2C is intentionally a minimal deterministic code transport layer. Do not add syntax, intelligence, tolerance, escaping, or convenience behavior without a demonstrated requirement.
