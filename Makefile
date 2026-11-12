.DEFAULT_GOAL := help
V1_PYTHON ?= python
ifneq (,$(wildcard backendV1/.venv/Scripts/python.exe))
V1_PYTHON := backendV1/.venv/Scripts/python.exe
else ifneq (,$(wildcard backendV1/.venv/bin/python))
V1_PYTHON := backendV1/.venv/bin/python
endif
V1_ARGS ?=
ARGS ?= $(V1_ARGS)
TASKS := help dev dev1 dev2 be worker fe fe2 check db-ready migrate db-check install-be install-fe infra-up infra-down infra-status infra-logs test test-be test-fe test-e2e e2e lint lint-fix typecheck build seed reset-db reseed reconcile reindex
V1_TASKS := $(addprefix v1-,help dev be worker fe check migrate db-check install-be install-fe infra-up infra-down infra-status infra-logs test test-be test-fe test-e2e e2e lint lint-fix typecheck build)
V2_TASKS := v2-dev v2-fe v2-check
.PHONY: $(TASKS) $(V1_TASKS) $(V2_TASKS)
TASKS += clear seed-modelops
V1_TASKS += v1-clear v1-seed-modelops
.PHONY: clear v1-clear seed-modelops v1-seed-modelops
$(TASKS) $(V1_TASKS) $(V2_TASKS):
	"$(V1_PYTHON)" scripts/run_v1.py $@ $(ARGS)
