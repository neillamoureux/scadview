# Contributing to SCADview

Thanks for your interest in contributing to **SCADview**!  
All contributions are made via pull requests (PRs) from a fork to ensure a clean, reviewable history.

---

## Requirements:
- mise


## TL;DR (Quick Start)

```
issue → fork → branch (conventional) → change → preflight → commit (conventional) → push → PR
```

- Every PR must resolve an issue.
- Branch names must be conventional with issue number after \<type\>/.
- Follow code style and standards.
- PRs will be squash merged by a maintainer.
- Clear commit messages matter.  Use conventional commits.
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

### 4. Set Up the Development Environment

This project uses `mise` tasks for cross-platform development (macOS/Linux/Windows).
Install mise using these [instructions](https://mise.jdx.dev/installing-mise.html) to get started.

#### Activate mise in your shell (recommended)

To make `mise` manage tools automatically in your current shell, run

You can [integrate mise with your shell](https://mise.jdx.dev/dev-tools/#environment-integration) using `mise activate`,
which writes a script you can use in your particular shell.

```bash
mise activate <your shell type>
```

Common examples:

- zsh: `eval "$(mise activate zsh)"`
- bash: `eval "$(mise activate bash)"`
- fish:,`mise activate fish | source`
- PowerShell: `mise activate pwsh | Out-String | Invoke-Expression`

If you don’t want persistent activation, you can still run commands directly with:

```
mise exec -- command -with=parameters
```

To prepare your enviroment, run:

```bash
mise install
mise run bootstrap
```

This is optional if you first run a task, which will run these automatically if needed.

CI-only environments that cannot install GUI deps should use:

```bash
mise run bootstrap_ci
```

List available tasks with:

```bash
mise tasks
```

To run a task:

```bash
mise run <task_name>
```

Common tasks:

```bash
mise run scadview
mise run format
mise run lint
mise run type
mise run test
mise run preflight
mise run actionlint
mise run reset
```


### 5. Make Your Changes

- Keep changes focused and scoped to the issue
- **Follow coding standards**, as documented `STYLE.md`
- Add or update tests where appropriate
- Update documentation if public behavior or APIs change

#### Documentation Workflow (Versioned Docs)

Use two commands depending on what you need:

1. Live edit loop (recommended while writing docs):
```
mise run docs_live_serve
```
This uses `mkdocs serve` and hot-reloads on file changes.

2. Sync versioned docs state (mike):
```
mise run docs_sync_serve
```
This updates local branch `gh-pages` docs versions and `latest` alias, 
and serves the docs.

Version selection behavior for `mise run docs_sync` and `mise run docs_sync_serve`:

- If `--docs-version` is provided, that value is used.
- Else if `DOCS_VERSION` is set, that value is used.
- Else if `HEAD` has a release tag like `v0.2.5`, it uses `0.2.5`.
- Else it uses `dev`.

Examples:
```
mise run docs_live_serve
mise run docs_sync
mise run docs_sync_serve -- --docs-version 0.3.1
```

After a release, the common local refresh flow is:

```
git checkout main
git pull
mise run docs_sync_serve -- --docs-version 0.3.1
```

`mise run docs_sync` and `mise run docs_sync_serve` only updates local docs state by default.
CI handles published docs on release.

---

### 6. Commit Your Changes

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

### 7. Run Preflight Checks

Before submitting your PR, ensure your changes pass all local checks:

- Formatting
- Linting
- Type checks (if applicable)
- Tests

If a `mise preflight`, script, or equivalent workflow exists, it must pass before opening a PR.
CI failures will block merging.

Recommended local gate:

```bash
mise run preflight
```

---

### 8. Push to Your Fork

```bash
git push origin <your-branch-name>
```

---

### 9. Open a Pull Request

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

## Communication

If you’re planning a large feature or significant refactor, please open an issue first
to discuss your approach before investing time in a PR.

Thank you for helping improve SCADview!
