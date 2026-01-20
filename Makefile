.PHONY: setup install test clean

# Default shell
SHELL := /bin/bash

# Venv config
VENV_DIR = .venv
PYTHON = $(VENV_DIR)/bin/python3
PIP = $(VENV_DIR)/bin/pip

# Targets
setup: clean
	python3 -m venv $(VENV_DIR)

install: setup
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -r requirements.txt
	@$(MAKE) test

test:
	pytest

clean:
	rm -rf $(VENV_DIR)
