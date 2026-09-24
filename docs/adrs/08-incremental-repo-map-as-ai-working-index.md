# ADR 08: Incremental RepoMap as AI Working Index

## Status

Accepted

## Context

The Avalon development workflow deliberately separates refinement, implementation planning,
code modification, execution, and review.

For small and medium-sized work packages, Frieda may prepare implementation changes without
having persistent access to the complete repository.

Repeatedly scanning or transferring the complete repository would create unnecessary context
and token overhead. At the same time, implementation planning requires enough repository
knowledge to identify relevant files and dependencies before requesting their actual contents.

A persistent RepoMap is therefore maintained as a compact working index of the repository.

The RepoMap is explicitly **not repository documentation and not a representation of the full
repository**.

Its sole consumer is Frieda. Its purpose is to provide enough structural and semantic context
for Frieda to:

- identify likely files affected by a change,
- understand relevant dependencies and relationships,
- create an initial implementation plan,
- request the specific source files required for implementation,
- recognize when the available repository context is insufficient.

The RepoMap may contain files, classes, functions, methods, signatures, dependencies,
responsibilities, behavioral notes, or other information useful for these purposes.

Its level of detail is intentionally adaptive:

> As little information as possible, as much as Frieda needs for reliable repository navigation
> and implementation planning.

## Decision

Avalon maintains a human-readable RepoMap as a persistent AI working index.

The concrete serialization format (Markdown, YAML, JSON, or similar) is chosen based on what
works best for Frieda. Human readability is required primarily for transparency and operational
recoverability, not because humans are intended consumers of its contents.

The RepoMap SHALL remain substantially smaller and more abstract than the repository itself.

It SHALL NOT attempt to contain complete implementation details or become a parallel
documentation model of the source code.

### Human-in-the-loop

Human-in-the-loop validation of RepoMap contents is explicitly **not required**.

The RepoMap is written by Frieda for Frieda and is not intended to provide reliable
documentation for Flo or other human developers.

Consequently:

- Flo is not responsible for reviewing its completeness or semantic quality.
- Flo is not responsible for maintaining its internal structure.
- Entries do not need to be optimized for human comprehension.
- Frieda is responsible for determining which information she requires and for recognizing
  when the RepoMap is insufficient or stale.

Human readability remains useful for debugging the workflow, manual recovery, and avoiding
opaque or proprietary state.

### Incremental maintenance

The RepoMap is updated only after an implementation has reached its final accepted state.

The update MUST be derived from the final accepted diff or equivalent final code state, not
from the original implementation plan or intermediate patches.

As part of the final review, Frieda produces the corresponding RepoMap change together with,
or immediately after, approval of the implementation.

This allows the RepoMap to evolve incrementally without requiring a complete repository scan
after every change.

### Re-analysis

Incremental maintenance is not assumed to remain correct indefinitely.

A broader repository re-analysis SHOULD be performed periodically and SHOULD also be triggered
when there is evidence that the RepoMap has become unreliable.

Possible triggers include:

- significant refactoring,
- new modules or architectural layers,
- substantial dependency restructuring,
- repeated incorrect file selection,
- missing dependencies discovered during implementation,
- noticeable divergence between RepoMap assumptions and actual source code,
- several accumulated implementation iterations where a refresh is considered prudent.

The re-analysis reconciles the RepoMap with the actual repository.

## Workflow

For suitable work packages, the intended workflow is:

1. Flo and Frieda refine the change.
2. Frieda uses the RepoMap to create an initial implementation plan.
3. Frieda explicitly requests the source files required for implementation.
4. Flo provides the requested current source snapshot.
5. Frieda creates deterministic replace/diff operations.
6. Flo applies the changes and executes the requested tests and verification.
7. Frieda reviews the resulting diff and test results.
8. The review/fix loop continues until the change is accepted.
9. Frieda derives and provides the final incremental RepoMap update from the accepted change.

The RepoMap therefore supports repository discovery but never replaces inspection of the actual
source files involved in a change.

## Escalation to repository-aware coding agents

Not every work package is suitable for this workflow.

During refinement, a work package may deliberately be escalated to Codex or another
repository-aware coding agent when broad repository exploration, extensive cross-cutting
changes, interactive debugging, or greater implementation autonomy is expected to provide
material benefit.

The objective is not to avoid frontier coding-agent usage entirely. The objective is to use
its more constrained token budget selectively where repository integration and agentic
capabilities provide meaningful leverage.

Regardless of the implementation path, the final implementation review remains with Frieda.

After acceptance, Frieda also determines the required RepoMap update.

## Consequences

### Positive

- Full repository scans are avoided for routine changes.
- Context and token consumption are concentrated on relevant source files.
- Repository knowledge persists across individual feature conversations and implementation
  iterations.
- Frieda can perform initial impact analysis before requesting source code.
- The workflow remains usable without permanent repository access.
- RepoMap maintenance naturally follows accepted repository changes.
- Expensive repository-aware coding agents can be reserved for work packages where their
  capabilities provide meaningful benefit.

### Negative / Risks

- The RepoMap can become stale or incomplete.
- Incorrect RepoMap information can cause incorrect file selection or incomplete impact
  analysis.
- Incremental updates can accumulate errors over time.
- The appropriate level of abstraction cannot be fully specified upfront and must be learned
  empirically.
- Frieda must recognize uncertainty rather than treating the RepoMap as authoritative.

These risks are accepted because the actual source code remains the authoritative source for
implementation and final review, and periodic or trigger-based re-analysis provides a recovery
mechanism.

## Principle

> The RepoMap is not a map for humans to understand Avalon.
> It is Frieda's compact working memory for knowing where to look next.

If it fails at that job, Frieda owns the virtual nose-pulling.