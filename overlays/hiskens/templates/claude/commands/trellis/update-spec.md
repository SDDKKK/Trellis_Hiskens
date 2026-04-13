# Update Spec - Capture Executable Contracts

When you learn something valuable (from debugging, implementing, or discussion), use this command to update the relevant spec documents.

**Timing**: After completing a task, fixing a bug, or discovering a new pattern

---

## Code-Spec First Rule (CRITICAL)

In this project, "spec" for implementation work means **code-spec**:
- Executable contracts (not principle-only text)
- Concrete signatures, payload fields, env keys, and boundary behavior
- Testable validation/error behavior

If the change touches infra or cross-layer contracts, code-spec depth is mandatory.

### Mandatory Triggers

Apply code-spec depth when the change includes any of:
- New/changed command or API signature
- Cross-layer request/response contract change (Python↔MATLAB)
- Data format/schema change (CSV, Excel, MAT files)
- Infra integration (storage, data pipeline, env wiring)

### Mandatory Output (7 Sections)

For triggered tasks, include all sections below:

1. Scope / Trigger
2. Signatures (command/API/DB)
3. Contracts (request/response/env)
4. Validation & Error Matrix
5. Good/Base/Bad Cases
6. Tests Required (with assertion points)
7. Wrong vs Correct (at least one pair)

---

## When to Update Specs

| Trigger | Example | Target Spec |
|---------|---------|-------------|
| **Implemented a feature** | Added new data processing pipeline | Relevant `python/` or `matlab/` file |
| **Made a design decision** | Chose approach X over Y for reliability calc | Relevant spec + "Design Decisions" section |
| **Fixed a bug** | Found a subtle issue with error handling | `python/quality-guidelines.md` |
| **Discovered a pattern** | Found a better way to structure code | Relevant guidelines file |
| **Hit a gotcha** | Learned that X must be done before Y | Relevant spec + "Common Mistakes" section |
| **Established a convention** | Team agreed on naming pattern | `quality-guidelines.md` |
| **Cross-layer insight** | Understood how data flows between layers | `guides/cross-layer-thinking-guide.md` |
| **Accumulated learnings** | Multiple learnings in same area | Review `.trellis/memory/learnings.md` |

**Key Insight**: Code-spec updates are NOT just for problems. Every feature implementation contains design decisions and contracts that future AI/developers need to execute safely.

---

## Spec Structure Overview

```
.trellis/spec/
├── python/            # Python development standards
│   ├── index.md       # Overview and links
│   └── *.md           # Topic-specific guidelines
├── matlab/            # MATLAB development standards
│   ├── index.md       # Overview and links
│   └── *.md           # Topic-specific guidelines
└── guides/            # Thinking guides
    ├── index.md       # Guide index
    └── *.md           # Topic-specific guides
```

### CRITICAL: Code-Spec vs Guide - Know the Difference

| Type | Location | Purpose | Content Style |
|------|----------|---------|---------------|
| **Code-Spec** | `python/*.md`, `matlab/*.md` | Tell AI "how to implement safely" | Signatures, contracts, matrices, cases, test points |
| **Guide** | `guides/*.md` | Help AI "what to think about" | Checklists, questions, pointers to specs |

**Decision Rule**: Ask yourself:
- "This is **how to write** the code" → Put in `python/` or `matlab/`
- "This is **what to consider** before writing" → Put in `guides/`

**Guides should be short checklists that point to specs**, not duplicate the detailed rules.

---

## Update Process

### Step 1: Identify What You Learned

Answer these questions:

1. **What did you learn?** (Be specific)
2. **Why is it important?** (What problem does it prevent?)
3. **Where does it belong?** (Which spec file?)
4. **Check learnings.md** — Recent learnings in `.trellis/memory/learnings.md` that should become spec entries?

### Step 2: Classify the Update Type

| Type | Description | Action |
|------|-------------|--------|
| **Design Decision** | Why we chose approach X over Y | Add to "Design Decisions" section |
| **Project Convention** | How we do X in this project | Add to relevant section with examples |
| **New Pattern** | A reusable approach discovered | Add to "Patterns" section |
| **Forbidden Pattern** | Something that causes problems | Add to "Anti-patterns" or "Don't" section |
| **Common Mistake** | Easy-to-make error | Add to "Common Mistakes" section |
| **Convention** | Agreed-upon standard | Add to relevant section |
| **Gotcha** | Non-obvious behavior | Add warning callout |

### Step 3: Read the Target Spec

Before editing, read the current spec to:
- Understand existing structure
- Avoid duplicating content
- Find the right section for your update

```bash
cat .trellis/spec/<category>/<file>.md
```

### Step 4: Make the Update

Follow these principles:

1. **Be Specific**: Include concrete examples, not just abstract rules
2. **Explain Why**: State the problem this prevents
3. **Show Code**: Add code snippets for patterns
4. **Keep it Short**: One concept per section

### Step 5: Update the Index (if needed)

If you added a new section or the spec status changed, update the category's `index.md`.

---

## Update Templates

### Mandatory Template for Infra/Cross-Layer Work

```markdown
## Scenario: <title>

### 1. Scope / Trigger
- Trigger: <what triggered this>

### 2. Signatures
- Command/API/DB signature(s)

### 3. Contracts
- Request fields (name, type, constraints)
- Response fields (name, type, constraints)
- Environment keys (required/optional)

### 4. Validation & Error Matrix
- <input> -> <error>

### 5. Good/Base/Bad Cases
- Good: ...
- Base: ...
- Bad: ...

### 6. Tests Required
- Unit/Integration with assertion points

### 7. Wrong vs Correct
#### Wrong
...
#### Correct
...
```

### Adding a Design Decision

```markdown
### Design Decision: [Decision Name]

**Context**: What problem were we solving?

**Options Considered**:
1. Option A - brief description
2. Option B - brief description

**Decision**: We chose Option X because...

**Extensibility**: How to extend this in the future...
```

### Adding a New Pattern

```markdown
### Pattern Name

**Problem**: What problem does this solve?

**Solution**: Brief description of the approach.

**Example**:
\`\`\`
// Good
code example

// Bad
code example
\`\`\`

**Why**: Explanation of why this works better.
```

### Adding a Forbidden Pattern

```markdown
### Don't: Pattern Name

**Problem**:
\`\`\`
// Don't do this
bad code example
\`\`\`

**Why it's bad**: Explanation of the issue.

**Instead**:
\`\`\`
// Do this instead
good code example
\`\`\`
```

### Adding a Common Mistake

```markdown
### Common Mistake: Description

**Symptom**: What goes wrong

**Cause**: Why this happens

**Fix**: How to correct it

**Prevention**: How to avoid it in the future
```

### Adding a Gotcha

```markdown
> **Warning**: Brief description of the non-obvious behavior.
>
> Details about when this happens and how to handle it.
```

---

## Interactive Mode

If you're unsure what to update, answer these prompts:

1. **What did you just finish?**
   - [ ] Fixed a bug
   - [ ] Implemented a feature
   - [ ] Refactored code
   - [ ] Had a discussion about approach

2. **What surprised you or was non-obvious?**
   - (Describe the insight)

3. **Would this help someone else avoid the same problem?**
   - Yes → Proceed to update spec
   - No → Maybe not worth documenting

4. **Which area does it relate to?**
   - [ ] Python code
   - [ ] MATLAB code
   - [ ] Cross-layer data flow
   - [ ] Code organization/reuse
   - [ ] Quality/testing

---

## Quality Checklist

Before finishing your spec update:

- [ ] Is the content specific and actionable?
- [ ] Did you include a code example?
- [ ] Did you explain WHY, not just WHAT?
- [ ] Did you include executable signatures/contracts (if infra/cross-layer)?
- [ ] Did you include validation and error matrix (if infra/cross-layer)?
- [ ] Did you include Good/Base/Bad cases (if infra/cross-layer)?
- [ ] Is it in the right spec file?
- [ ] Does it duplicate existing content?
- [ ] Would a new team member understand it?

---

## Relationship to Other Commands

```
Development Flow:
  Learn something → /trellis:update-spec → Knowledge captured
       ↑                                  ↓
  /trellis:break-loop ←──────────────────── Future sessions benefit
  (deep bug analysis)
```

- `/trellis:break-loop` - Analyzes bugs deeply, often reveals spec updates needed
- `/trellis:update-spec` - Actually makes the updates (this command)
- `/trellis:finish-work` - Reminds you to check if specs need updates

---

## Core Philosophy

> **Specs are living documents. Every debugging session, every "aha moment" is an opportunity to make the spec better.**

The goal is **institutional memory**:
- What one person learns, everyone benefits from
- What AI learns in one session, persists to future sessions
- Mistakes become documented guardrails
