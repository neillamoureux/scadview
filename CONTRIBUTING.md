# Contributing to SCADview

Thanks for your interest in contributing to **SCADview**!  
All contributions are made via pull requests (PRs) from a fork to ensure a clean, reviewable history.

---

## TL;DR (Quick Start)

```
issue → fork → branch (conventional) → change → preflight → commit (conventional) → push → PR
```

- Every PR must resolve an issue.
- Branch names must be conventional with issue number after type/.
- Follow code style and standards.
- PRs will be squash merged by a maintainer.
- Clear commit messages matter.
- You contribute to conform with the [Apache License, Version 2.0](http://www.apache.org/licenses/LICENSE-2.0).

---

## Contribution Workflow

### 0. Start With an Issue (Required)

Every pull request must resolve an issue.

- If an issue already exists, reference it in your PR
- If no issue exists, create one first with:
  - A clear problem statement.
  - Expected behavior or outcome.
  - Relevant context or constraints.

Small fixes and refactors still require an issue (they may be brief).

---

### 1. Fork the Repository

Fork the scadview repository to your own GitHub account using the **Fork** button.

---

### 2. Clone Your Fork

```bash
git clone https://github.com/<your-username>/scadview.git
cd scadview
```

Optional but recommended:

```bash
git remote add upstream https://github.com/<original-org-or-user>/scadview.git
```

This allows you to keep your fork in sync with the main project.

---

### 3. Create a Conventional Branch

Do not work directly on `main`.

Branch names must follow the [Conventional Branch specification](https://conventional-branch.github.io/).

Format:

```
<type>/<issue-no>-<short-description>
```

#### Branch Name Cheat Sheet (short forms)

| Type     | Purpose                                |
| -------- | -------------------------------------- |
| feat/    | New features                           |
| fix/     | Bug fixes                              |
| hotfix/  | Urgent fixes                           |
| chore/   | Maintenance or non-feature work        |
| release/ | Release preparation (maintainers only) |

Examples:

- feat/123-linear-extrude
- fix/124-mesh-bounds
- hotfix/125-crash-on-empty-mesh
- chore/126-update-deps

---

### 4. Make Your Changes

- Keep changes focused and scoped to the issue
- **Follow coding standards**, as noted below.
- Follow existing code style and patterns
- Add or update tests where appropriate
- Update documentation if public behavior or APIs change

---

### 5. Commit Your Changes

This project uses **[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)**.

Although PRs are squash merged, commit messages still matter:

- Maintainers curate the final squash commit message
- Clear, well-structured commit messages make this easier
- Well-formed Conventional Commits improve changelogs and release notes

Preferred format:

```
feat: add linear extrude support
fix: handle empty mesh input
```

Breaking changes must follow Conventional Commit rules.



The commit types supported in this repo are: 

Commit type | Example | Version impact
-- | -- | --
build: | Build changes | Patch
fix: | Bug fixes | Patch
feat: | New user-visible functionality | Minor
feat!: or BREAKING CHANGE: | Breaking API changes | Major
docs: | Documentation only | Patch
chore: | Tooling, CI, maintenance | Patch
perf: | Performance optimization | Patch
refactor: | Internal changes | Patch
revert: | Revert a change | Patch?
test: | Tests only | Patch
ci: | GitHub Actions / CI | Patch

---

### 6. Run Preflight Checks

Before submitting your PR, ensure your changes pass all local checks:

- Formatting
- Linting
- Type checks (if applicable)
- Tests

If a `make preflight`, script, or equivalent workflow exists, it must pass before opening a PR.
CI failures will block merging.

---

### 7. Push to Your Fork

```bash
git push origin <your-branch-name>
```

---

### 8. Open a Pull Request

Open a PR from your fork to the `main` branch of the upstream repository.

- Fill out the PR template completely
- Reference the issue the PR resolves:

```
Resolves: #123
```

- Clearly explain:
  - What the change does
  - How it resolves the issue
  - Any trade-offs or follow-up work

---

## Contributor License Notice

By submitting a contribution (code, documentation, or other content) to this repository,
you agree that:

- Your contribution is provided under the **[Apache License, Version 2.0](http://www.apache.org/licenses/LICENSE-2.0)**,
  and may be distributed, modified, and sublicensed under those same terms.
- You have the right to submit the work (it is your original creation, or you have
  sufficient rights to include it).
- You grant Neil Lamoureux and all users of SCADview a **perpetual, worldwide,
  non-exclusive, royalty-free license** to use, modify, and distribute your contribution
  under the project’s license.

This ensures the project remains open and legally consistent for all contributors.

---

## Code Style and Standards

- Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) except:
    - Use `ruff` instead of pylint for linting.
    - You may import classes, types, etc.
    - Line length limited per `ruff`
    - Sort imports per `ruff`
    - Formatting per `ruff`
    - License boilerplate is not required in every file.
    - Files should end with an empty blank line.
- Follow existing code patterns and structure where possible.
- Prefer keeping functions and methods short.
- Comment where necessary, but keep to a minimum.  
Consider better naming, 
or extracting a method to make the intent of the code obvious.
- Use type hints for all methods / functions (code in tests and examples are exceptions)
- Use docstrings for public methods / functions in [src/scadview/api/](src/scadview/api/).
    - Use the style from [Google Python Style Guide: Functions and Methods](https://google.github.io/styleguide/pyguide.html#383-functions-and-methods)
- Keep dependencies minimal and cross-platform.
- Write clear, descriptive commit messages.
- Where possible, add or update tests for new functionality.
- For scripts, write for `bash` where possible and follow the [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)


---

## Communication

If you’re planning a large feature or significant refactor, please open an issue first
to discuss your approach before investing time in a PR.

Thank you for helping improve SCADview!
