help:
	@echo "Available commands:"
	@echo "  shell   	- Activate the virtual environment"
	@echo "            	This creates the virtual environment if it does not already exist"
	@echo "The following require you have run make shell first"
	@echo "  test    	- Run tests"
	@echo "  run 		- Run the application"
	@echo "  			  Set the ARGS env var or param to pass args eg make run ARGS=-vv"
	@echo "  			  make run ARGS=--help for more info"
	@echo "  format  	- Format the code"
	@echo "  lint    	- Lint the code"
	@echo "  type		- Type check the code"
	@echo "  preflight	- format, lint and type"
	@echo "  serve_docs	- Run the documentation server"

VENV_DIR := .venv
SCRIPTS_DIR := scripts

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
	@"$(SCRIPTS_DIR)/test.sh"

run: check-venv
	@echo "Running the application..."
	@python -m scadview $(ARGS)

format: check-venv
	@echo "Formatting the code..."
	@"$(SCRIPTS_DIR)/format.sh"

lint: check-venv
	@echo "Linting the code..."
	@"$(SCRIPTS_DIR)/lint.sh"

type: check-venv
	@echo "Type checking the code..."
	@"$(SCRIPTS_DIR)/type.sh"

preflight: format lint test type

serve_docs: check-venv
	@echo "Generating server documentation..."
	@"$(SCRIPTS_DIR)/serve_docs.sh"
