CONDA ?= conda
CONDA_ENV ?= zoro
PYTHON_VERSION ?= 3.11
PYTHON ?= python3
VENV ?= .venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/pip
PYTHON_VENV := $(VENV_BIN)/python
NPM ?= npm

.PHONY: setup setup-conda setup-venv install-python install-frontend dev backend test build-frontend clean check-conda ensure-conda-env

check-conda:
	@command -v $(CONDA) >/dev/null 2>&1 || { \
		echo "Error: '$(CONDA)' was not found in PATH."; \
		echo "Install Conda/Mamba first, then run 'make setup'."; \
		exit 1; \
	}

ensure-conda-env: check-conda
	@$(CONDA) env list | awk '{print $$1}' | grep -qx "$(CONDA_ENV)" || { \
		echo "Error: Conda env '$(CONDA_ENV)' was not found."; \
		echo "Run 'make setup' first to create and install Zoro."; \
		exit 1; \
	}

setup: setup-conda install-frontend

setup-conda: check-conda
	@if $(CONDA) env list | awk '{print $$1}' | grep -qx "$(CONDA_ENV)"; then \
		echo "Using existing conda env '$(CONDA_ENV)'"; \
	else \
		echo "Creating conda env '$(CONDA_ENV)' (python $(PYTHON_VERSION))"; \
		$(CONDA) create -y -n $(CONDA_ENV) python=$(PYTHON_VERSION) pip; \
	fi
	$(CONDA) run -n $(CONDA_ENV) python -m pip install --upgrade pip
	$(CONDA) run -n $(CONDA_ENV) python -m pip install -e . pytest

setup-venv: install-python install-frontend

install-python:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e .

install-frontend:
	$(NPM) --prefix frontend install

dev:
	@$(MAKE) ensure-conda-env
	$(CONDA) run -n $(CONDA_ENV) zoro-api

backend:
	@$(MAKE) ensure-conda-env
	$(CONDA) run -n $(CONDA_ENV) zoro-api --backend-only

test:
	@$(MAKE) ensure-conda-env
	$(CONDA) run -n $(CONDA_ENV) python -m pytest -q

build-frontend:
	$(NPM) --prefix frontend run build

clean:
	rm -rf .pytest_cache zoro.egg-info frontend/dist
	find backend tests -type d -name '__pycache__' -prune -exec rm -rf {} +
