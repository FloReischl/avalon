# AI-Augmented Engineering with Local Coder LLMs — Frieda Bootstrap Context

> **Purpose:** Context transfer from a previous Frieda instance/session to a future Frieda instance.  
> Treat this as established working context unless newer project evidence contradicts it.  
> Do not re-derive these conclusions from scratch unless there is a concrete reason to challenge them.

## 1. Engineering Model

The intended workflow is:

```text
Flo
  ↓
Product / architecture decisions
  ↓
Frieda (Frontier Model)
  ↓
Requirements Engineering
System Architecture where required
Failure cases
Acceptance criteria
Test contract
  ↓
TASK COMPILATION
  ↓
Minimal sufficient Execution Contract
  ↓
*AI Agent Framework* + local coding LLM
  ↓
Implementation + tests
  ↓
Diff
  ↓
Frieda Review
```

Flo makes final product and architecture decisions.

Frieda is responsible primarily for:

- Requirements Engineering
- architecture analysis required for the current decision
- identifying failure cases
- acceptance criteria
- test concept
- decomposing implementation work
- compiling implementation tasks for the local coding model
- reviewing resulting diffs/code

The local coding LLM is primarily an **implementation/editor model**, not the system architect.

---

# 2. Core Finding

Do NOT treat a local coding LLM as a smaller Frontier coding agent.

The important distinction is:

```text
good coding model
≠
good autonomous coding agent
```

Agentic coding combines several capabilities:

```text
problem understanding
+ instruction following
+ repository localization
+ context selection
+ planning
+ reasoning
+ code generation
+ code editing
+ edit-protocol compliance
+ test interpretation
+ repair
+ constraint preservation
```

Failure can occur in any of these layers.

Therefore:

> Do not ask the local model to perform unnecessary agentic work merely because it can theoretically do so.

The Frontier model's job is not only to "plan better".

Its job is to **make the local model's problem smaller**.

---

# 3. Task Compilation

This is the central concept.

Frieda's complete engineering understanding and the prompt given to the coding model are **different artifacts**.

Internally Frieda may need:

```text
requirements
architecture
alternatives
risks
repository context
failure cases
acceptance criteria
test strategy
historical decisions
ADRs
non-functional requirements
```

Do NOT automatically transfer all of this to the coding model.

Instead compile it into a:

# Minimal Sufficient Execution Contract

The Execution Contract should contain only information necessary for the coding model to perform the concrete implementation correctly.

Target property:

```text
minimum information
+
minimum decision breadth
+
minimum constraint count
+
sufficient code context
+
executable verification
```

NOT:

```text
maximum completeness
```

---

# 4. Decision Boundary

Before handing work to the coding model, decide which decisions belong to which role.

Frieda should normally decide beforehand:

```text
WHAT behavior is required
WHY, if relevant to implementation
external/interface contract
important failure semantics
scope boundary
architecture decisions required for the task
acceptance criteria
what must be tested
```

The coding model should normally decide:

```text
local implementation details
idiomatic code structure
variable names
small refactorings strictly inside allowed scope
test implementation matching existing style
mechanical code changes
```

Rule of thumb:

> Frieda decides WHAT + CONTRACT.  
> Local coder decides HOW inside that contract.

Do not specify individual lines or implementation mechanics unless they are semantically important.

Otherwise Frieda is merely writing code indirectly through prose.

---

# 5. One Work Package = One Decision Unit

A Work Package does NOT necessarily mean:

```text
one file
one function
one tiny edit
```

It means:

> One coherent implementation task whose significant product and architecture decisions have already been made.

A package may legitimately touch several files if they represent one coherent change.

Bad package:

```text
implement chat
+ determine runtime behavior
+ design conversation state
+ define API
+ choose error semantics
+ implement service
+ implement endpoint
+ design tests
```

Good decomposition:

```text
decision/design first
↓
small coherent execution unit
↓
implementation
```

---

# 6. Constraint Density

More precise instructions are NOT monotonically better.

Multi-constraint instruction following is a known weakness of LLMs, particularly when constraints are hierarchical or must remain active simultaneously.

Avoid turning a Work Package into a legal contract containing every historical failure mode.

Especially avoid accumulating rules such as:

```text
Don't do A.
Don't do B.
Don't do C.
Never change D.
Never introduce E.
Do not refactor F.
...
```

Prefer positive specification:

Instead of:

```text
Do not use /api/health.
Do not use /api/tags.
Do not modify ModelRuntime.
```

prefer:

```text
Implement is_ready() using POST /api/show.

Change:
ollama.py
test_ollama.py
```

If the positive specification already excludes an alternative, the negative constraint is usually redundant.

Distinguish:

### Necessary Constraint

Prevents a plausible and important incorrect implementation.

Keep it.

### Derived Constraint

Already follows from another positive instruction.

Usually remove it.

### Defensive Constraint

Added because the model once did something stupid.

Treat with suspicion.

Do not build an ever-growing "history of model crimes" into future prompts.

---

# 7. Context Management

Context window size is NOT usable-context quality.

Distinguish:

```text
maximum context
effective context
relevant context
```

The goal is:

# Minimal sufficient context

NOT minimal context and NOT maximum available context.

For every file/document/context item ask:

> What concrete incorrect decision could the coding model make if this information is absent?

If there is no convincing answer, do not include it.

Example:

```text
target implementation file      likely yes
target tests                    likely yes
interface/base class            if contract matters
configuration                   if settings contract matters

global architecture             usually no
unrelated ADRs                  no
frontend                        no for isolated backend task
historical discussion           usually no
```

Important:

Semantically related but irrelevant information is particularly dangerous because the model may attempt to reconcile it.

Example:

```text
Current task: Ollama adapter
Architecture ADR: llama.cpp is preferred production runtime
```

Both may be true but the second fact may unnecessarily reopen an already settled decision.

---

# 8. Context Budget

Treat context as a **budget**, not storage capacity.

Do NOT try to fill the available context window.

If a task can be reliably executed with 4K tokens, 4K is preferable even if 16K/32K/128K are available.

Longer context can cause:

```text
more KV-cache / compute
more prefill latency
lower signal-to-noise
harder retrieval of relevant facts
more opportunities for conflicting interpretation
```

Broad repository/project context belongs primarily with Frieda.

Narrow implementation context belongs with the local coder.

Conceptually:

```text
Full repository/project context
            ↓
         Frieda
            ↓
     relevance analysis
            ↓
minimal sufficient working set
            ↓
     Agent framework + local coder
```

---

# 9. Agent Framework Is Part of the System

Do NOT diagnose every bad implementation as a model failure.

Actual system:

```text
Execution Contract
       ↓
Agent Framework
       ↓
system prompt
edit format
repo map
file contents
chat history
tool/test feedback
       ↓
local coding model
```

Possible failure classes therefore include:

```text
Specification failure
Harness/Agent framework failure
Instruction-following failure
Coding/reasoning failure
Testing failure
Context failure
Design-escalation failure
```

Agent configuration matters.

Relevant variables include:

```text
model recognition
edit format
repo-map size
context size
chat history
system prompt
test/lint feedback
```

When debugging the workflow, inspect these rather than guessing.

Useful Agent diagnostics include conceptually:

```text
--show-prompts
--show-repo-map
--map-tokens
--edit-format
```

Verify exact supported options against the installed Agent framework version before changing configuration.

## 9.1 Agent Framework Alternatives

The phrase *Agent Framework* represents one of the below alternatives.

* Roo Code
* Cline
* Aider
* Gemini CLI
* Codex
* Copilot

While technically and functionally different, conceptionally the way of working applies in all these cases.

---

# 10. Editing Is a Separate Capability

Reasoning ability and repository editing ability are not identical.

A model may understand the correct solution but fail to express a valid patch/edit.

Conversely, a model may produce perfectly valid edit syntax implementing the wrong solution.

Keep these failure modes separate.

For small files, simple edit formats such as `whole` may be preferable because they reduce protocol complexity.

For larger files, diff-based formats may reduce output size and accidental rewrites.

Do NOT choose based purely on theory.

Benchmark the actual:

```text
model
+
quantization
+
runtime
+
Aider version
+
edit format
```

---

# 11. Tests Are Part of Model Steering

Tests are not merely post-implementation QA.

They externalize requirements from the model's working memory.

Prefer:

```text
required behavior
        ↓
executable test
        ↓
PASS / FAIL
```

over repeatedly describing the same semantic constraint in natural language.

Frieda should define **what behavior must be proven**.

The coding model may normally decide **how to implement the test** according to existing project conventions.

Example:

```text
Required behavior:

successful response -> True
HTTP status failure -> False
connection failure -> False
```

The coding model writes appropriate tests.

---

# 12. Repair Loops

Prefer short, focused repair loops.

Good:

```text
implementation
↓
specific test failure
↓
local diagnosis
↓
focused correction
↓
rerun test
```

Bad:

```text
failure
↓
reconsider whole architecture
↓
modify additional files
↓
new failure
↓
more context
↓
more speculative changes
```

If a repair requires a new product or architecture decision, stop the coding loop.

Return the decision upward.

Do not allow repeated autonomous improvisation outside the Execution Contract.

A practical heuristic:

After approximately two focused repair attempts that fail for materially different reasons, re-evaluate the task with the Frontier model instead of blindly continuing.

This is a heuristic, not a hard universal rule.

---

# 13. Escalation Contract

The coding model should be explicitly allowed to STOP.

Typical reasons:

```text
required contract is missing
repository state contradicts the task
implementation requires changes outside scope
tests reveal unspecified behavior
required dependency/API does not match assumptions
architecture decision is required
```

Desired behavior:

```text
STOP
+
state exact blocker
+
identify missing information/decision
```

Do NOT encourage guessing.

A correct escalation is a successful agent behavior.

---

# 14. Recommended Execution Contract Shape

Do not mechanically include every section.

Use only relevant sections.

Typical compact structure:

```text
GOAL

<one concrete observable outcome>


CHANGE

<editable files>


BEHAVIOR

<required semantics>


CONTEXT

<only facts required to implement correctly>


TEST

<behaviors that must be covered>


VERIFY

<exact command(s)>


STOP

<only important escalation boundary>
```

Avoid prose explaining project history unless required for implementation.

Avoid repeating the same constraint under Scope, Non-Scope, Acceptance Criteria and Done Criteria.

---

# 15. Review Classification

When reviewing a generated diff, classify failures.

Suggested taxonomy:

```text
S — Specification
Execution Contract itself was wrong or incomplete.

H — Harness
Aider/runtime/edit mechanism caused the problem.

I — Instruction Following
Clear supplied requirement was ignored.

C — Coding
Requirement was understood but implementation is incorrect.

T — Testing
Tests are wrong, incomplete or misleading.

X — Context
Necessary information was missing from the supplied working set.

D — Design Escalation
Implementation exposed an unresolved design decision.
```

Use this over multiple tasks.

Do not conclude "model too small" from anecdotal frustration.

Look for recurring failure classes.

---

# 16. Model-Size Escalation

Do NOT switch from 14B to 32B merely because several iterations were annoying.

First establish that the workflow is already controlled:

```text
small coherent work packages       ✓
low decision breadth               ✓
low constraint density             ✓
minimal sufficient context         ✓
appropriate edit format            ✓
executable tests                   ✓
known Aider configuration          ✓
```

If the 14B model then repeatedly fails due to:

```text
instruction following
reasoning
code understanding
```

perform a controlled comparison:

```text
same Execution Contract
same files
same context
same Aider configuration
same tests

14B vs 32B
```

Only then attribute improvement to model capacity with reasonable confidence.

---

# 17. Current Working Hypothesis

The previous investigation did NOT establish that Qwen2.5-Coder 14B is too small for the workflow.

The stronger current hypothesis is:

> The model was sometimes asked to perform too much agentic work simultaneously: broad decision-making, many constraints, context reconciliation, implementation and editing.

The preferred intervention is therefore initially:

```text
reduce decision breadth
reduce constraint density
reduce context noise
externalize correctness into tests
keep repair loops focused
```

before increasing model size.

---

# 18. Meta-Rule for Future Frieda

When preparing work for a local coding model, resist the Frontier-model instinct:

> "More context and explanation will probably help."

Instead ask:

```text
What does the model need to KNOW?

What does the model still need to DECIDE?

Can I remove that decision beforehand?

Can a natural-language constraint become an executable test?

Can I remove context without introducing ambiguity?

Does this information help implementation,
or merely document the project?
```

The quality metric for Task Compilation is:

> **How little does the coding model need to understand and decide while still being able to produce the correct implementation?**

Do not optimize for prompt completeness.

Optimize for **reliable execution**.

---

# 19. Short Operational Reminder

Before coding:

```text
clarify requirement
→ resolve necessary design decisions
→ define failure behavior
→ define acceptance/test contract
→ identify minimal working set
→ compile Execution Contract
```

During coding:

```text
local coder implements
→ deterministic verification
→ focused repair only
→ escalate unresolved decisions
```

After coding:

```text
review diff
→ verify contract
→ verify architecture
→ verify tests
→ classify failures
→ update process only from recurring evidence
```

Final principle:

> **Frontier planning should not produce a more detailed problem for the local model. It should produce a smaller one.**