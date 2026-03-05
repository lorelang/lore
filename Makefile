PYTHON ?= python3
PYTEST ?= $(PYTHON) -m pytest
PYTHONPATH ?= src

TARGETS := neo4j json jsonld agent embeddings mermaid palantir tools agents.md metrics

.PHONY: help install test test-fast test-stress conformance validate-examples curate-examples compile-matrix smoke launch-check build dist-check clean

help:
	@echo "Lorelang shortcuts:"
	@echo "  make install            # pip install -e ."
	@echo "  make test               # full test suite"
	@echo "  make test-fast          # fast local checks"
	@echo "  make test-stress        # stress/performance tests only"
	@echo "  make conformance        # language conformance checks"
	@echo "  make validate-examples  # validate every example ontology"
	@echo "  make curate-examples    # curation dry-run on all examples"
	@echo "  make compile-matrix     # compile all examples across built-in targets"
	@echo "  make smoke              # end-to-end launch smoke workflow"
	@echo "  make launch-check       # all launch readiness checks"
	@echo "  make build              # build package artifacts"
	@echo "  make dist-check         # verify package metadata"

install:
	$(PYTHON) -m pip install -e .

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTEST) -q

test-fast:
	PYTHONPATH=$(PYTHONPATH) $(PYTEST) -q tests/test_language_conformance.py tests/test_ingest_review.py

test-stress:
	PYTHONPATH=$(PYTHONPATH) $(PYTEST) -v tests/test_stress.py

conformance:
	PYTHONPATH=$(PYTHONPATH) $(PYTEST) -q tests/test_language_conformance.py

validate-examples:
	@set -e; \
	for d in examples/*; do \
		if [ -d "$$d" ]; then \
			echo "validate $$d"; \
			PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m lore.cli validate "$$d" >/dev/null; \
		fi; \
	done; \
	echo "all examples validated"

curate-examples:
	@set -e; \
	for d in examples/*; do \
		if [ -d "$$d" ]; then \
			echo "curate $$d"; \
			PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m lore.cli curate "$$d" --dry-run >/dev/null; \
		fi; \
	done; \
	echo "all example curations passed"

compile-matrix:
	@set -e; \
	for d in examples/*; do \
		if [ -d "$$d" ]; then \
			for t in $(TARGETS); do \
				echo "compile $$d -> $$t"; \
				PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m lore.cli compile "$$d" -t "$$t" >/dev/null; \
			done; \
		fi; \
	done; \
	echo "compile matrix passed"

smoke:
	./scripts/launch_smoke.sh

launch-check: test conformance validate-examples compile-matrix smoke
	@echo "launch check passed"

build:
	@$(PYTHON) -m build --version >/dev/null 2>&1 || \
		(echo "Missing/invalid packaging tool 'build'. Install with: pip install --upgrade build"; exit 1)
	$(PYTHON) -m build

dist-check: build
	@$(PYTHON) -m twine --version >/dev/null 2>&1 || \
		(echo "Missing packaging tool 'twine'. Install with: pip install --upgrade twine"; exit 1)
	$(PYTHON) -m twine check dist/*

clean:
	rm -rf dist build .pytest_cache .coverage htmlcov .tox
