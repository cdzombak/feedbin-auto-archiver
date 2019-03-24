SHELL:=/usr/bin/env bash
VIRTUALENV_DIR=venv

.PHONY: all
all: help

.PHONY: bootstrap
bootstrap: ## Set up local virtualenv
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
	@rm -rf venv
	@echo ""
	@echo "Remember to run \`deactivate\` if you're working in your virtualenv right now."

# via https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
