# ADR 09: Deterministic Source Patching via prompt2code

**Status:** Accepted

## Context

Small and well-localized Avalo changes are planned and reviewed by Frieda without requiring a repository-aware coding agent.

To apply such changes safely, Avalo uses `prompt2code.py` (P2C) as a deliberately simple patch executor.

P2C contains no code intelligence. Frieda is responsible for understanding the code and generating the patch; P2C is responsible only for deterministic validation and application.

## Decision

P2C consumes a YAML patch file and applies ordered changes relative to a target repository directory.

Supported operations:

- `string-replace` — replace one exact string
- `string-remove` — remove one exact string
- `create` — create a new file
- `delete` — delete an existing file

For `string-replace` and `string-remove`, the `old` text MUST occur **exactly once**. Zero or multiple matches abort the complete patch.

Changes are simulated sequentially in memory. Later changes therefore see the result of earlier changes.

Only after **all changes in all files have validated successfully** are filesystem changes written.

P2C intentionally provides:

- no fuzzy matching
- no automatic code interpretation
- no intelligent conflict resolution
- no regex patching initially
- no partial writes after semantic validation failure

The source code remains authoritative.

## Workflow

1. Flo and Frieda refine the change.
2. Frieda identifies the required source files.
3. Flo provides their current content.
4. Frieda generates the YAML patch.
5. Flo applies it with P2C.
6. Flo runs the required tests and verification.
7. Frieda reviews the resulting `git diff` and test results.
8. If necessary, repeat with another incremental patch.

Complex or poorly localized changes may instead be escalated to a repository-aware coding agent.

## How-To

Apply a patch:

    python prompt2code.py \
      --input-script patch.yaml \
      --target-dir ~/dev/avalo

Typical patch:

    files:
      - path: backend/app/example.py
        changes:
          - mode: string-replace
            old: |2-
              return "old"
            new: |2-
              return "new"

          - mode: string-remove
            old: |2-
              # obsolete comment

      - path: backend/app/new_file.py
        changes:
          - mode: create
            content: |2
              def hello():
                  return "hello"

### Important

- Always generate patches against the **current source state**.
- Keep patches small and purpose-specific.
- Multiple changes to one file belong in one file entry and execute top-to-bottom.
- Prefer `|2-` for exact snippets where a trailing newline must not be part of the match.
- Use `|2` for complete file content when the final newline should be preserved.
- Never weaken an exact-match failure just to make a patch apply. Re-read the current source and regenerate the patch.
- After every patch, run the relevant tests and inspect `git diff`.
- A successfully applied patch is **not** evidence of correct behavior; tests and Frieda's final review remain required.

## Consequences

P2C trades coding-agent flexibility for predictability and low coordination overhead.

This works well for bounded changes whose affected code can be identified beforehand. It is intentionally unsuitable for changes requiring repository exploration, broad refactoring, or iterative debugging.

> Frieda decides what to change. P2C only proves that the requested textual transformation can be applied exactly.
