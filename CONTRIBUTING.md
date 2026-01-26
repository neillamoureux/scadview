# Contributing to SCADview

Thanks for your interest in contributing to **SCADview**!  
We welcome bug reports, feature ideas, documentation improvements, and code contributions.

---

## 🧩 How to Contribute

1. **Fork** the repository and create a branch, using [Conventional Branch](https://conventional-branch.github.io/) standards.  For example:

       git checkout -b feat/your-feature-name

1. **Read the README**: This explains some basics about developing in this repo.

1. **Follow coding standards**, as noted below.

1. **Make your changes** with clear commit messages, using [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) standards.

1. **Run tests** and verify your code passes linting, formating and type checks.  
There are `make` commands to help with this.  Also, run `make preflight` before creating a pull requests.

1. **Submit a pull request** describing your changes and how they improve SCADview.

---

## 📜 Contributor License Notice

By submitting a contribution (code, documentation, or other content) to this repository,
you agree that:

- Your contribution is provided under the **Apache License, Version 2.0**,  
  and may be distributed, modified, and sublicensed under those same terms.
- You have the right to submit the work (it is your original creation, or you have
  sufficient rights to include it).
- You grant Neil Lamoureux and all users of SCADview a **perpetual, worldwide,
  non-exclusive, royalty-free license** to use, modify, and distribute your contribution
  under the project’s license.

This ensures the project remains open and legally consistent for all contributors.

---

## 🧠 Code Style and Standards

- Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) except:
    - Use `ruff` instead of pylint for linting.
    - You may import classes, types, etc.
    - Line length limited per `ruff`
    - Sort imports per `ruff`
    - Formatting per `ruff`
    - License boilerplate is not required in every file.
- Follow existing code patterns and structure where possible.
- Prefer keeping functions and methods short.
- Comment where necessary, but keep to a minimum.  
Consider better naming, 
or extracting a method to make the intent of the code obvious.
- Use type hints for all methods / functions.
- Use docstrings for public methods / functions in [src/scadview/api/](src/scadview/api/).
    - Use the style from [Google Python Style Guide: Functions and Methods](https://google.github.io/styleguide/pyguide.html#383-functions-and-methods)
- Keep dependencies minimal and cross-platform.
- Write clear, descriptive commit messages.
- Where possible, add or update tests for new functionality.
- For scripts, write for `bash` where possible and follow the [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)

---

## 🗨️ Communication

If you’re planning a large feature or significant refactor, please open an issue first
to discuss your approach before investing time in a PR.

Thank you for helping improve SCADview!
