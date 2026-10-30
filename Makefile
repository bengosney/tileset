.PHONY: help clean install init
.DEFAULT_GOAL := install
.PRECIOUS: requirements.%.txt

REQS=$(shell python -c "import tomllib; print(' '.join(f'requirements.{k}.txt' for k in tomllib.load(open('pyproject.toml', 'rb')).get('project', {}).get('optional-dependencies', {}).keys()))")

SYSTEM_PYTHON_VERSION:=$(shell ls /usr/bin/python* | grep -Eo '[0-9]+\.[0-9]+' | sort -V | tail -n 1)
UV_PATH:=~/.cargo/bin/uv
VENV_PATH:=.venv
VENV_LOCK:=$(VENV_PATH)/.install_lock
PIP_PATH:=$(VENV_PATH)/bin/pip
WHEEL_PATH:=$(VENV_PATH)/bin/wheel
PRE_COMMIT_PATH:=$(VENV_PATH)/bin/pre-commit

help: ## Display this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.gitignore:
	curl -sS "https://www.toptal.com/developers/gitignore/api/visualstudiocode,python,direnv" > $@

.git: .gitignore
	git init

.pre-commit-config.yaml: | $(PRE_COMMIT_PATH) .git
	curl -sS https://gist.githubusercontent.com/bengosney/4b1f1ab7012380f7e9b9d1d668626143/raw/.pre-commit-config.yaml > $@
	$(PRE_COMMIT_PATH) autoupdate
	@touch $@

pyproject.toml: | $(UV_PATH)
	curl -sS https://gist.githubusercontent.com/bengosney/f703f25921628136f78449c32d37fcb5/raw/pyproject.toml > $@
	@touch $@

requirements.%.txt: $(UV_PATH) pyproject.toml
	@echo "Building $@"
	$(UV_PATH) pip compile --generate-hashes -q --extra $* -o $@ $(filter-out $<,$^)

requirements.txt: $(UV_PATH) pyproject.toml
	@echo "Building $@"
	$(UV_PATH) pip compile --generate-hashes -q -o $@ $(filter-out $<,$^)

$(VENV_PATH): | $(UV_PATH) .envrc
	$(UV_PATH) venv --managed-python --python $(SYSTEM_PYTHON_VERSION)
	@touch $@

.git/hooks/pre-commit: .git $(PRE_COMMIT_PATH) .pre-commit-config.yaml
	$(PRE_COMMIT_PATH) install

.envrc:
	@echo "Setting up .envrc then stopping"
	@echo 'if [ ! -d .venv ]; then' > $@
	@echo '    make .venv' >> $@
	@echo 'fi' >> $@
	@echo '' >> $@
	@echo 'PATH_add ".venv/bin"' >> $@
	@echo 'export VIRTUAL_ENV="$$PWD/.venv"' >> $@
	@echo 'export VIRTUAL_ENV_PROMPT="$$(basename $$PWD)"' >> $@
	@echo 'watch_file .venv' >> $@
	@touch -d '+1 minute' $@
	@false

$(UV_PATH):
	@echo "Error: uv is not installed. Install it from https://github.com/astral-sh/uv" && false

$(PRE_COMMIT_PATH): $(UV_PATH) $(VENV_PATH)
	$(UV_PATH) pip install pre-commit

init: .envrc $(UV_PATH) requirements.txt requirements.dev.txt .git/hooks/pre-commit ## Initalise a enviroment

clean: ## Remove all build files
	find . -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	rm -rf .pytest_cache
	rm -f .testmondata

$(VENV_LOCK): requirements.txt $(REQS)
	@echo "Installing $(filter-out $<,$^)"
	$(UV_PATH) pip sync $(filter-out $<,$^)
	$(UV_PATH) pip install --no-deps -e .
	@touch $@

install: $(VENV_LOCK) ## Install development requirements (default)
