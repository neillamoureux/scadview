help: ## Display this help message.
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

VENV_DIR := .venv
SCRIPTS_DIR := scripts

venv: # Create the virtual environment if it does not already exist.
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

test: check-venv ## Run tests.
	@echo "Running tests..."
	@"$(SCRIPTS_DIR)/test.sh"

run: check-venv ## Run the application. Set the ARGS env var or param to pass args eg make run ARGS=-vv
	@echo "Running the application..."
	@python -m scadview $(ARGS)

format: check-venv ## Format the code.
	@echo "Formatting the code..."
	@"$(SCRIPTS_DIR)/format.sh"

lint: check-venv ## Lint the code.
	@echo "Linting the code..."
	@"$(SCRIPTS_DIR)/lint.sh"

type: check-venv ## Type check the code.
	@echo "Type checking the code..."
	@"$(SCRIPTS_DIR)/type.sh"

preflight: format lint test type ## Format, lint, test, and type check the code.
	@echo "Preflight checks complete."

serve_docs: check-venv ## Serve docs with live reload (mkdocs).
	@echo "Serving docs with live reload..."
	@"$(SCRIPTS_DIR)/serve_docs.sh"

serve_docs_sync: check-venv ## Sync versioned docs state locally (mike). Optional: SERVE=1 (to start the server after syncing).
	@echo "Syncing local versioned docs state..."
	@if [ "$(SERVE)" = "1" ]; then \
		"$(SCRIPTS_DIR)/sync_docs_versions.sh" --serve; \
	else \
		"$(SCRIPTS_DIR)/sync_docs_versions.sh"; \
	fi

docs_release_preview: check-venv ## Preview a release docs version locally. Requires DOCS_VERSION (e.g. 0.2.6)
	@if [ -z "$(DOCS_VERSION)" ]; then \
		echo "DOCS_VERSION is required. Example: make docs_release_preview DOCS_VERSION=0.2.6"; \
		exit 1; \
	fi
	@echo "Previewing release docs version $(DOCS_VERSION)..."
	@DOCS_VERSION="$(DOCS_VERSION)" "$(SCRIPTS_DIR)/sync_docs_versions.sh" --serve
