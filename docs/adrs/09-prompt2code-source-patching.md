# ADR 09: Deterministic Source Patching via Prompt2Code

**Status:** Accepted  
**Date:** 2026-09-01

## Context

Avalon uses frontier-model-assisted planning and local implementation workflows.

For some implementation tasks, the generated source changes are sufficiently small and deterministic that a coding agent is unnecessary. In these cases, the required operation is primarily the reliable transport of explicitly specified source changes into the local repository.

Prompt2Code (`prompt2code.py`) provides this transport layer.

An earlier version used YAML patch files. Source snippets were embedded as YAML block scalars and then applied through deterministic operations.

While functional, YAML introduced unnecessary complexity for exact source transport:

- YAML indentation and source-code indentation interacted.
- Block scalar semantics affected trailing newlines.
- Exact source snippets required YAML-specific formatting such as `|2-`.
- LLM-generated patches therefore had to satisfy both YAML syntax and source-code whitespace requirements.

Prompt2Code does not require a general-purpose serialization format. Its patch format only needs to express a small set of deterministic source operations.

## Decision

Prompt2Code uses a minimal custom text format designed specifically for exact source transport.

It intentionally provides no general-purpose syntax, quoting, escaping, comments, indentation handling, fuzzy matching, or code intelligence.

### Patch Structure

A patch contains one or more sequential changes.

Each change starts with exactly two header lines:

```text
<relative-file-path>
<mode>
```

Supported modes are:

```text
string-replace
string-remove
file-create
file-delete
```

Mode names are case-sensitive and whitespace-exact.

Changes are separated by the exact marker line:

```text
p2c-next-change
```

The separator must occur between two complete changes. It is invalid at the beginning or end of a patch, and consecutive separators are invalid.

### string-replace

```text
backend/app/main.py
string-replace
p2c-old
<exact old payload>
p2c-new
<exact new payload>
```

Both payloads are required and must be non-empty.

By default, the `p2c-old` payload must occur exactly once in the current simulated file content.

For repeated identical matches, an optional selector may be specified directly after `string-replace` and before `p2c-old`:

```text
p2c-position: N
```

selects exactly the N-th occurrence, using 1-based indexing.

Alternatively:

```text
p2c-count: N
```

requires exactly N occurrences and replaces all of them.

`p2c-position` and `p2c-count` are mutually exclusive. Both values must be positive integers.

If neither selector is present, the existing exactly-once behavior applies.

Any selector or match-count validation failure aborts the complete patch before any filesystem changes are made.

### string-remove

```text
backend/app/main.py
string-remove
p2c-old
<exact old payload>
```

The payload is required and must be non-empty.

By default, the payload must occur exactly once in the current simulated file content.

The same optional selectors as for `string-replace` are supported directly after `string-remove` and before `p2c-old`:

- `p2c-position: N` removes exactly the N-th occurrence, using 1-based indexing.
- `p2c-count: N` requires exactly N occurrences and removes all of them.

`p2c-position` and `p2c-count` are mutually exclusive. Both values must be positive integers.

If neither selector is present, the existing exactly-once behavior applies.

### file-create

```text
backend/app/new_module.py
file-create
p2c-new
<complete file content>
```

The payload is required and must be non-empty.

The target file must not already exist in the current simulated state.

Missing parent directories are created during the write phase.

### file-delete

```text
backend/app/obsolete.py
file-delete
```

The target must exist as a regular file in the current simulated state.

`file-delete` has no payload.

### Payload Semantics

Payload is transported without interpretation.

Indentation, blank lines, and other whitespace are significant.

The newline immediately separating a payload from a following marker is structural and is not part of the payload. Additional newlines before the marker are payload.

At EOF, all remaining content after the payload marker belongs to the payload, including a final newline when present.

For example:

```text
p2c-new
def foo():
    return 2
p2c-next-change
```

does not include a newline after `return 2`.

To include one:

```text
p2c-new
def foo():
    return 2

p2c-next-change
```

The patch format uses UTF-8 and LF (`\n`) line endings.

### Reserved Marker Lines

The following exact lines have structural meaning:

```text
p2c-old
p2c-new
p2c-next-change
```

There is intentionally no escaping or quoting mechanism for representing conflicting marker lines inside payload.

If such a collision becomes a real use case, the format can be extended then.

### Path Safety

All patch paths are interpreted relative to `--target-dir`.

Paths are resolved using `pathlib`, including symlink resolution.

The resolved target must remain inside the resolved `--target-dir`.

Any path escaping the target directory aborts the patch.

This applies to direct traversal such as:

```text
../outside.py
```

and to paths escaping through symlinks.

Prompt2Code operates only on regular files. `file-delete` never deletes directories.

### Simulation and Write Model

Changes are processed sequentially.

Multiple changes may target the same file. Each change sees the simulated result of all preceding changes.

Prompt2Code performs two phases:

1. Parse, validate, and simulate the complete patch in memory.
2. Write the final state of each affected file to disk.

No filesystem changes, including creation of parent directories, occur before the complete patch has successfully passed simulation.

Each affected file is written at most once using its final simulated state.

This provides deterministic pre-write validation without implementing a transactional filesystem.

If an I/O error occurs after the write phase has started, Prompt2Code aborts but does not attempt rollback or compensation. Already written changes remain.

### Diagnostics

Errors identify the relative path and global change number:

```text
❌ Patch aborted: [backend/app/main.py] change #3: <reason>
```

For failed exact-match validation, the complete `p2c-old` payload is included unchanged:

```text
❌ Patch aborted: [frontend/src/App.vue] change #1: string-remove expected p2c-old to occur exactly once, found 7

p2c-old:
<span
```

Successful execution reports the final result once per affected file using relative paths:

```text
✅ Modified: frontend/src/App.vue
✅ Created: backend/app/foo.py
✅ Deleted: backend/app/obsolete.py

🎉 Done! 3 file(s) processed successfully.
```

## Guardrails

Prompt2Code deliberately does not provide:

- fuzzy source matching,
- automatic indentation adjustment,
- code or AST interpretation,
- implicit mode correction,
- case-insensitive syntax,
- comments in the patch structure,
- partial application after validation failure,
- filesystem rollback after write failure,
- marker escaping,
- binary-file support.

Invalid or ambiguous input fails instead of being interpreted heuristically.

## Verification

The implementation is covered by a small regression suite for the behavior that is critical to the transport layer:

- multiline `string-replace`,
- `string-remove`,
- positional selection of repeated matches,
- exact-count replacement/removal of repeated matches,
- rejection of combined `p2c-position` and `p2c-count`,
- preservation of default exactly-once behavior,
- `file-create` including parent-directory creation,
- `file-delete`,
- sequential changes to the same file,
- no writes when a later change fails validation,
- target-directory escape protection.

The suite is intentionally small. Prompt2Code is a development helper, not an operational application component.

## Consequences

### Positive

- Source indentation and whitespace no longer interact with YAML syntax.
- Patch generation requires very little formatting knowledge from an LLM.
- Exact source changes remain deterministic and fail fast.
- Sequential changes allow later operations to depend on earlier simulated changes.
- Complete pre-write simulation prevents partially applied patches caused by validation failures.
- `--target-dir` forms a filesystem safety boundary.
- The implementation has no YAML dependency.

### Negative

- The format is intentionally specialized and not compatible with generic YAML/JSON tooling.
- Exact reserved marker lines cannot currently be represented inside payload.
- Exact-match operations remain sensitive to stale source context.
- Filesystem errors during the write phase can leave a partially written patch because rollback is intentionally not implemented.

## Rationale

Prompt2Code is not intended to understand or edit source code intelligently.

Its responsibility is narrower:

> Transport explicitly specified source changes into a repository as deterministically and transparently as possible.

Keeping the patch language minimal reduces both implementation complexity and the probability that an LLM-generated patch fails because of transport-format details unrelated to the source change itself.

Additional syntax or intelligence should only be introduced in response to demonstrated requirements.
