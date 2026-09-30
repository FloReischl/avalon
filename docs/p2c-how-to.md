# How to Prompt2Code (P2C) — Syntax & Semantics

Use this reference when generating Prompt2Code patches.

## Core rules

- Format: UTF-8, LF (`\n`).
- Paths are relative to the P2C target directory.
- Syntax, mode names, markers, payload and whitespace are exact.
- No quoting, escaping, comments, fuzzy matching, indentation correction or code interpretation.
- Changes execute sequentially against simulated state.
- A later change to the same file sees all preceding simulated changes.
- Invalid/ambiguous patches fail; never rely on heuristic correction.

## Patch structure

Every change starts with exactly:

    <relative-file-path>
    <mode>

Supported modes:

    string-replace
    string-remove
    file-create
    file-delete

Separate multiple changes with exactly:

    p2c-next-change

Never place `p2c-next-change` at patch start/end or twice consecutively.

---

## string-replace

Exact syntax:

```
path/to/file
string-replace
p2c-old
<exact existing content>
p2c-new
<exact replacement content>
```

`p2c-old` and `p2c-new` must both be non-empty.

Default: `p2c-old` must occur exactly once.

For repeated matches, optionally put exactly one selector directly after
`string-replace`:

```
path/to/file
string-replace
p2c-position: N
p2c-old
<old>
p2c-new
<new>
```

`p2c-position: N`
- N is positive and 1-based.
- Replace only occurrence N.

Or:

```
path/to/file
string-replace
p2c-count: N
p2c-old
<old>
p2c-new
<new>
```

- N is positive.
- Exactly N occurrences must exist.
- Replace all N occurrences.

Never combine `p2c-position` and `p2c-count`.

---

## string-remove

Exact syntax:

```
path/to/file
string-remove
p2c-old
<exact content to remove>
```

`p2c-old` must be non-empty.

Default: it must occur exactly once.

Optional selectors work exactly as for `string-replace`:

```
string-remove
p2c-position: N
p2c-old
<old>
```

or:

```
string-remove
p2c-count: N
p2c-old
<old>
```

There is NO `p2c-new` for `string-remove`.

---

## file-create

Exact syntax:

```
path/to/new-file
file-create
p2c-new
<complete file content>
```

Payload must be non-empty.

Target file must not already exist in the simulated state.

Missing parent directories are created only after complete patch validation.

There is NO `p2c-old`.

---

## file-delete

Exact syntax:

```
path/to/file
file-delete
```

Target must exist as a regular file in simulated state.

There is NO payload and therefore NO `p2c-old` or `p2c-new`.

---

## Payload semantics

Payload is literal.

Preserve exactly:
- indentation
- spaces
- blank lines
- source text

Structural marker lines are:

```
p2c-old
p2c-new
p2c-next-change
```

They cannot occur as literal standalone lines inside payload because P2C has
no escaping mechanism.

### Newline before a following marker

The newline that separates payload from the next structural marker is NOT
part of the payload.

Thus:

    p2c-new
    foo
    p2c-next-change

means payload `foo` without trailing newline.

To include a trailing newline in the payload, add an additional blank line:

```
p2c-new
foo

p2c-next-change
```

At EOF, everything after the payload marker belongs to the payload, including
a final newline if present.

---

## Sequential semantics

For:

```
change 1
p2c-next-change
change 2
```

change 2 operates on the simulated result of change 1.

Therefore, when multiple changes target the same file, every later
`p2c-old` must match the file state AFTER preceding changes.

The complete patch is parsed, validated and simulated before filesystem
writes begin.

A validation failure aborts the complete patch without applying any changes.

---

## Generation checklist

Before emitting a P2C patch, verify:

1. Every change starts with `<path>` then `<mode>`.
2. Mode is exactly one of the four supported modes.
3. `string-replace` has non-empty `p2c-old` AND `p2c-new`.
4. `string-remove` has only non-empty `p2c-old`.
5. `file-create` has only non-empty `p2c-new`.
6. `file-delete` has no payload markers.
7. Selector, if needed, is directly after the mode.
8. Never combine `p2c-position` and `p2c-count`.
9. Without selector, `p2c-old` must match exactly once.
10. `p2c-next-change` occurs only BETWEEN complete changes.
11. Payload whitespace and indentation exactly match intended source.
12. Later changes use the simulated state produced by earlier changes.
13. No reserved marker line occurs literally inside payload.
14. Do not invent source context: exact `p2c-old` must come from known current
    source or known preceding simulated state.