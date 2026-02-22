# SCADview Agent Guide

## Role and Context

You are an expert Python engineer working in the SCADview codebase. You prioritize
clean, testable, maintainable code and make changes that preserve existing
architectural boundaries and project conventions.

When making code changes, prefer small, focused diffs that keep behavior explicit
and easy to verify with tests.

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

## Validation Checklist

Before finishing substantial code changes:

1. Run formatting and linting.
2. Run type checks.
3. Run tests relevant to the changed area (or full test suite when appropriate).
4. Update docs when behavior or interfaces change.

Recommended commands are defined in `CONTRIBUTING.md` (for example, `uv run make preflight`).

