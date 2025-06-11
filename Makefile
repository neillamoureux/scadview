help:
	@echo "Available commands:"
	@echo "  shell   - Activate the virtual environment"
	@echo "            This creates the virtual environment if it does not already exist"
	@echo "The following require you have run make shell first"
	@echo "  test    - Run tests"
	@echo "  run     - Run the application"
	@echo "  format  - Format the code"
	@echo "  lint    - Lint the code"
	@echo "  type	 - Type check the code"

VENV_DIR := .venv

venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		python3 -m venv $(VENV_DIR); \
		echo "Virtual environment created."; \
	else \
		echo "Virtual environment already exists."; \
	fi

shell: venv
	@echo "Activating virtual environment..."
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		. $(VENV_DIR)/bin/activate; \
		PS1="\[\e[0;32m\]\w> $ \[\e[m\]" $(SHELL); \
	else \
		echo "Virtual environment already activated."; \
	fi

check-venv:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "Run make shell first."; \
		exit 1; \
	fi

test: check-venv
	@echo "Running tests..."
	@pytest

run: check-venv
	@echo "Running the application..."
	@python -m meshsee

format: check-venv
	@echo "Formatting the code..."
	@ruff format

lint: check-venv
	@echo "Linting the code..."
	@ruff check

type: check-venv
	@echo "Type checking the code..."
	@pyright src/meshsee
