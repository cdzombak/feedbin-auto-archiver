SHELL:=/usr/bin/env bash
VIRTUALENV_DIR=venv

.PHONY: all
all: help

.PHONY: help
help:  # via https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: virtualenv
virtualenv: clean ## Set up local virtualenv with requirements
	@virtualenv --python=python3 $(VIRTUALENV_DIR)
	@( \
		source ${VIRTUALENV_DIR}/bin/activate; \
		pip3 install -r "requirements.txt"; \
	)
	@echo ""
	@echo "Ready to rock 🤘"
	@echo "Please run:"
	@echo "  . $(VIRTUALENV_DIR)/bin/activate"

.PHONY: clean
clean: ## Cleanup local venv & any other temporary files
	@rm -rf $(VIRTUALENV_DIR)
	@echo ""
	@echo "Remember to run \`deactivate\` if you're working in your virtualenv right now."

.PHONY: lint
lint: ## Lint all source files in this repository (requires nektos/act: https://nektosact.com)
	act --artifact-server-path /tmp/artifacts -j lint

.PHONY: update-lint
update-lint: ## Pull updated images supporting the lint target (may fetch >10 GB!)
	docker pull catthehacker/ubuntu:full-latest
