.PHONY: setup install test clean run_macos ngrok

# Default shell
SHELL := /bin/bash

# Venv config
VENV_DIR = .venv
PYTHON = $(VENV_DIR)/bin/python3.12
PIP = $(VENV_DIR)/bin/pip

# Targets
setup: clean
	python3.12 -m venv $(VENV_DIR)

install: setup
	$(PYTHON) -m pip install "pip<25.0"
	$(PIP) install -r requirements.txt
	$(PIP) install --no-deps "grc_odycy_joint_sm @ https://huggingface.co/chcaa/grc_odycy_joint_sm/resolve/main/grc_odycy_joint_sm-any-py3-none-any.whl"
	@echo "Running tests..."
	@$(MAKE) test

test:
	PYTHONPATH=. $(VENV_DIR)/bin/pytest

macos:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Virtual environment not found. Installing dependencies..."; \
		$(MAKE) install; \
	fi
	@echo "Running macOS application..." 
	cd macos && swift build && swift run
	@echo "macos app running."

rebuild:
	rm -rf macos/.build
	@$(MAKE) run_macos	

clean:
	rm -rf $(VENV_DIR)

ngrok:
	@echo "Starting ngrok tunnel..."
	ngrok http http://localhost:8000
	@echo "webservice running."

run:
	$(MAKE) macos
	$(MAKE) ngrok
