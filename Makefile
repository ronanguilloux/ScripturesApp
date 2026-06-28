.PHONY: setup install test clean macos rebuild ngrok run build-index

# Default shell
SHELL := /bin/bash

# Venv config
VENV_DIR = .venv
UV = uv

# grc_odycy_joint_sm wheel — upstream filename uses 'any' as version (invalid
# PEP 427). Download once to /tmp under the real version name so uv accepts it.
GRC_WHL_URL   = https://huggingface.co/chcaa/grc_odycy_joint_sm/resolve/main/grc_odycy_joint_sm-any-py3-none-any.whl
GRC_WHL_FIXED = /tmp/grc_odycy_joint_sm-0.7.0-py3-none-any.whl

# Targets
setup: clean
	$(UV) venv $(VENV_DIR)

install: setup
	$(UV) pip install -r requirements.txt
	@if [ ! -f "$(GRC_WHL_FIXED)" ]; then \
		echo "Downloading grc_odycy_joint_sm wheel..."; \
		curl -fsSL -o $(GRC_WHL_FIXED) "$(GRC_WHL_URL)"; \
	fi
	$(UV) pip install --no-deps $(GRC_WHL_FIXED)
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
	@$(MAKE) macos	

clean:
	rm -rf $(VENV_DIR)

build-index:
	PYTHONPATH=. $(VENV_DIR)/bin/python scripts/build/build_greek_index.py

ngrok:
	@echo "Starting ngrok tunnel..."
	ngrok http http://localhost:8000
	@echo "webservice running."

run:
	$(MAKE) -j 2 macos ngrok
