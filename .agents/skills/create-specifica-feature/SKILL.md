---
name: create-specifica-feature
description: >
  Step-by-step guide for creating a new Specifica feature folder with
  spec.md and design.md. Use when adding a new feature, workflow, or
  cross-cutting concern to spec/ or middleware/{component}/spec/.
  Also covers where to place the folder (project-level vs component-level)
  and how to register a link in AGENTS.md.
---

# Creating a Specifica Feature

[Specifica](https://specifica.org) organises software specs as plain Markdown
files in a directory: one folder per feature, three optional files
(`spec.md`, `design.md`, `tasks.md`).

---

## 1. Choose the Right Location

| Concern | Location |
| ------- | -------- |
| Affects multiple components, or belongs to no single component | `spec/<feature>/` (project-level) |
| Internal to one component | `middleware/<component>/spec/<feature>/` (component-level) |

**Rule of thumb:** if the spec would need to be copied if a second component
appeared, it is project-level.

---

## 2. Create the Folder

Use kebab-case names that describe the feature.

```bash
# component-level example
mkdir -p middleware/sql_to_arc/spec/<feature>

# project-level example
mkdir -p spec/<feature>
```

---

## 3. Write `spec.md` — The *What*

`spec.md` captures **requirements**: what the feature must do, in testable,
checkbox form. Keep implementation details out.

```markdown
# <Feature Title>

One-sentence description of purpose and context. Include the trigger
condition and the expected output or side-effect.

## Requirements

- [ ] <Single, testable behaviour — one sentence>
- [ ] <Another behaviour>
- [ ] ...

## Edge Cases

<Scenario> → <Expected outcome>.

<Another scenario> → <Expected outcome>.
```

**Rules for requirements:**

- One behaviour per checkbox — if you need "and" it is two requirements.
- State the outcome, not the implementation (`→ return 404` not `→ use Flask abort()`).
- Every edge case ends with a concrete outcome — no open-ended statements.

---

## 4. Write `design.md` — The *How*

`design.md` captures **decisions**: how it works and why. Skip obvious
implementation details; focus on non-obvious choices and trade-offs.

```markdown
# <Feature Title> — Design

## <Architecture / Module Overview>

Brief description or diagram of the main components and their
responsibilities.

## Key Decisions

1. **<Decision title>**
   — <Reasoning. What alternatives were considered and why they were
   rejected.>

2. **<Decision title>**
   — <Reasoning.>
```

**Rules for Key Decisions:**

- Every decision has a stated reason (the `—` clause is mandatory).
- "We chose X because Z" is the target sentence structure. Mentioning a
  rejected alternative is allowed when the contrast clarifies the reasoning,
  but it must appear in the `—` body, never in the title.
- Decisions are numbered so they can be referenced from code comments
  or other specs.
- **Decisions describe the current state of the system, not a history of
  changes.** Do not write "we changed from X to Y" or "previously we used X".
  A reader arriving for the first time must be able to understand the decision
  without knowing what came before. When a decision changes, rewrite it in
  place; the old reasoning has no value once it is superseded.

---

## 5. Write `tasks.md` — The *Work* (optional)

`tasks.md` is an ordered checklist. Use it for multi-step implementation
work or migrations. Omit it for completed or stable features.

```markdown
# <Feature Title> — Tasks

- [ ] <First step (no dependencies)>
- [ ] <Second step>
- [x] <Already done>
```

Tasks are ordered by dependency. Checked boxes = done. Tools can parse
and update `tasks.md` programmatically — keep entries flat and unambiguous.

---

## 6. Register in `AGENTS.md`

Add a link under the **Architecture & Design** section so every agent can
discover the new spec.

```markdown
- **[`middleware/sql_to_arc/spec/<feature>/`](...)**  — Short description.
```

Use a relative path from the repository root.

---

## 7. Project Conventions

These rules apply specifically to this project (see also
[`spec/principles.md`](../../../spec/principles.md)):

- `spec.md` never restates database view definitions — reference
  `docs/sql_to_arc_database_views.md` instead.
- Requirements that are already captured in `spec/principles.md`
  (typing, `uv`, `os.environ`) are **not** repeated in feature specs.
- Design decisions that affect public API types go in the component-level
  spec, not the project-level spec.
- `tasks.md` is optional and should be removed once the feature is fully
  implemented to avoid stale checklists.
