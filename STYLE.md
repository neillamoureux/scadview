# Style Guidelines
The goal of these guidelines is encourage clean, maintainable code that passes our specific linter and formatter (`ruff`).
Please follow these guidelines when submitting code.

# Style Hierarchy (Priority Order)
1. **Project Specific Exceptions** (Highest Priority - Overrides everything else)
2. **Google Python Style Guide** (Medium Priority - Applied where not overridden)
3. **PEP 8** (Lowest Priority - Fallback)

---

# 1. Project Specific Overrides (HIGHEST PRIORITY)

## Code separation:
* **UI code should be kept separated from other code**
* **Dependencei

## Naming Conventions (Strict)
* **Initialisms & Acronyms:** Treat them as full words (CamelCase or snake_case).
    * *Good:* `HtmlRequest`, `html_request`, `NatoCountry`, `nato_country`
    * *Bad:* `HTMLRequest`, `h_t_m_l_request`, `NATOCountry`

## Formatting & Linting
* **Formatter:** Use `ruff` rules (no manual formatting adjustments).
* **Line Length:** **88 characters** (Overrides Google's 80).
* **Linter:** Optimize code to pass `ruff`.
* **No Formatting Exceptions:** Do not use `# fmt: off` unless absolutely critical.

## Imports
* **Allowed:** Importing individual classes or functions is **PERMITTED** (Overrides Google's "packages only" rule).
* **Absolute Imports:** Use absolute imports for all packages/modules whenever possible.

## Comments (Clean Code Style)
* **Philosophy:** "Comments are a failure to express code in the language itself."
* **Avoid:** Do not write comments for obvious code.
* **Refactor First:** If a block needs a comment to explain *what* it does, rename variables/functions or extract the code into a well-named function instead.
* **Extraction:** If you feel the need to comment a section, extract it.

## Function Length (Strict)
* **Goal:** Short functions.
* **Guideline:** "~10 statements should be plenty.  Note this is **statements**, not **lines**"
* **Smell:** Any function > 9 statements is a candidate for refactoring.
* **Action:** Break large functions into many small, single-purpose functions.

## Function Order
* **Goal:** Easy to read the file top down
* **Guidelines:**: 
    * The top function should be a public function, and then order of the following function is listed in the order they would be called.
    * After that, the next public function not yet called is listed.
    * For example:
```python
def main():
    _fn_a()
    fn_b()
    _fn_c()

def _fn_a():
    fn_d()

def fn_d():
    pass

def fn_b()
    _fn_a()

def _fn_c():
    pass

def fn_g():
    _fn_h()

def _fn_h():
    pass
```

## JSON Normalization
* **Format:** Multiline (pretty print), 4-space indent, keys sorted alphabetically.

## Type Hints
* **Mandatory:** Use type hints for all function signatures except in `examples/` and `tests/`

---

# 2. Google Python Style Guide (Applied where not overridden)

## Code Structure & Logic
* **Main:** Executable files must always use `if __name__ == '__main__': main()`.
* **Global State:** Avoid mutable global state. Module-level constants should be `ALL_CAPS`.
* **Nested Functions:** Use only for closures/decorators. Do not nest just to hide code (use `_private_module_func` instead).
* **Comprehensions:** Allowed for simple cases. **Prohibited** if they contain multiple `for` clauses or complex filter expressions.
* **Default Arguments:** **NEVER** use mutable objects (lists, dicts) as default values. Use `None` and initialize inside the function.
* **True/False Evaluations:** Use implicit false.
    * *Yes:* `if not users:`
    * *No:* `if len(users) == 0:`
* **Lambdas:** One-liners only. If it's longer, define a function.
* **Conditional Expressions:** Allowed for simple cases (`x = y if c else z`).
* **Power Features:** Avoid metaclasses, bytecode access, reflection (`getattr` allowed only if necessary), and `__del__`.

## Classes & OOP
* **Properties:** Use `@property` for simple data access or light logic.
* **Accessors:** Use `get_foo()` / `set_foo()` only if the logic is complex or expensive. Otherwise, use public attributes or properties.
* **Inheritance:** Inherit from `Exception` for custom errors (suffix with `Error`).
* **Decorators:** Must be clearly documented. **Avoid** external dependencies (DB, sockets) in decorators (import time safety).

## Strings & TODOs
* **Formatting:** Prefer **f-strings** (`f"Name: {name}"`) over `%` or `.format()`.
* **Accumulation:** Do not use `+` to accumulate strings in a loop (O(n^2)). Use `list.append()` and `''.join()`.
* **TODOs:** Format: `# TODO(username): description of task`.

## Exceptions
* **Handling:** **NEVER** use catch-all `except:` or `except Exception:`. Catch specific errors.
* **Raising:** Do not raise generic `Exception`. Use `ValueError`, `TypeError`, or custom classes.
* **Asserts:** Do not use `assert` for control flow or validation; use it only for tests or internal invariants.

## Docstrings (API Documentation)
* **Requirement:** Mandatory for all public modules, classes, and functions under src/scadview/api
* **Format:** Three double quotes `"""`.
* **Structure:**
    ```python
    """One line summary.

    Extended description.

    Args:
        arg_name: Description.

    Returns:
        Description.

    Raises:
        ErrorType: Description.
    """
    ```

---

# 3. PEP 8 (Fallback)
* Use standard PEP 8 conventions for any naming or style rules not covered by the above.
