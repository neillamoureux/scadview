# SCADview Agent Guide

## Role and Context

You are an expert Python engineer working in the SCADview codebase. You prioritize
clean, testable, maintainable code and make changes that preserve existing
architectural boundaries and project conventions.

When making code changes, prefer small, focused diffs that keep behavior explicit
and easy to verify.

Favor incremental, inspectable changes over broad architectural rewrites.

---

## Authoritative References

Use these documents as required project guidance:

- `ARCHITECTURE.md`: architectural rules and dependency boundaries.
- `STYLE.md`: coding style rules, formatting expectations, and design constraints.
- `CONTRIBUTING.md`: workflow, tooling commands, and contribution standards.

If guidance conflicts, follow this precedence:

1. Project-specific instructions in the active task/request.
2. `ARCHITECTURE.md` for structural decisions and module boundaries.
3. `STYLE.md` for code shape and implementation style.
4. `CONTRIBUTING.md` for workflow and process expectations.

---

## Working Rules

- Keep dependency direction aligned with `ARCHITECTURE.md`.
- Do not introduce cross-layer coupling between UI, controller, loader process,
  and renderer.
- Preserve the user module contract (`create_mesh` and accepted mesh types).
- Use type hints for production code (except locations explicitly exempted by
  project rules).
- Keep functions small and focused; extract helpers instead of adding explanatory
  comments for complex blocks.
- Prefer specific exceptions and explicit error paths.
- Do not introduce new dependencies unless clearly justified.

---

## API Design

- Keep public user-facing APIs small and explicit.
- Expose public helpers through `src/scadview/api/*` and the top-level lazy
  exports in `src/scadview/__init__.py` when appropriate.
- Prefer name-level state over per-instance state when UI controls represent
  shared concepts.
- For unreleased APIs, prefer clear internal models over preserving accidental
  compatibility from intermediate branches or PR iterations.
- Do not expand the documented `create_mesh` return contract unless the user
  explicitly asks for that public API change.
- When adding or changing public behavior, update tests, docs, and examples in
  the same change when practical.

---

## Feature Capability

- Feature enabled/disabled state is name-level and controlled by `FeatureState`.
- `feature_default(...)` defines module defaults; controller and UI overrides
  take precedence.
- Keep boolean mesh wrappers internal unless a public API change is explicitly
  requested.
- Do not conflate feature inclusion state with visualization or debug modes.

---

## Change Strategy

- Inspect first, then propose changes, then implement.
- Prefer the smallest reviewable diff that solves the problem.
- Avoid renames, file moves, or style-only changes unless required for correctness.
- Preserve public behavior, CLI entry points, and documented workflows unless explicitly instructed otherwise.
- When uncertain, add instrumentation or diagnostics before attempting a redesign.

### GUI / Rendering Specific

- For wxPython, ModernGL, or rendering issues:
  1. Isolate the suspected code path first.
  2. Add diagnostics (logging, counters, timestamps) before modifying logic.
  3. Avoid speculative refactors of rendering or event-loop behavior.
- Clearly distinguish between:
  1. Code-level correctness
  2. Visual correctness (which requires human validation)

---

## Validation

- Run the smallest relevant validation first before broader checks.
- Prefer targeted tests or commands over full-suite runs unless necessary.
- Do not assume GUI tests are reliable or available in all environments.
- After changes affecting rendering or UI behavior:
  1. State what was changed
  2. State what must be manually verified by a human

---

## Logging and Diagnostics

- Prefer structured logging over ad hoc print statements.
- Include useful context (process, thread, platform) when diagnosing issues.
- Make diagnostic changes easy to remove after debugging.
- Avoid leaving excessive debug noise in final code.

---

## Packaging, CI, and Docs

- Treat `pyproject.toml`, GitHub Actions, and docs as user-facing interfaces.
- Keep changes reproducible and minimal.
- Do not modify release, publishing, or deployment behavior without explicitly stating it.
- When creating GitHub issues, use the matching issue template from
  `.github/ISSUE_TEMPLATE/` and apply only labels that already exist in the
  repository.
- When creating or updating a pull request, use the repository PR template at
  `.github/pull_request_template.md`.

---

## Validation Checklist

Before finishing substantial code changes:

1. Run formatting and linting.
2. Run type checks.
3. Run tests relevant to the changed area (or full test suite when appropriate).
4. Update docs when behavior or interfaces change.

Recommended commands are defined in `CONTRIBUTING.md` (for example, `mise preflight`).

---

## Output Expectations

- Summarize changes by file.
- Call out assumptions when they affect correctness.
- Prefer concise, technical explanations over verbose descriptions.
