PROCUREMENT_MOCKS=examples/procurement_harness/mocks.yaml
PROCUREMENT_POLICIES=examples/procurement_harness/policies.yaml
HOST ?= 127.0.0.1
PORT ?= 5100

install:
	python -m pip install --no-build-isolation -e '.[dev]'

proxy:
	python -m uvicorn mirage.proxy:app --reload

proxy-procurement:
	MIRAGE_MOCKS_PATH=$(PROCUREMENT_MOCKS) MIRAGE_POLICIES_PATH=$(PROCUREMENT_POLICIES) python -m uvicorn mirage.proxy:app --reload

agent:
	python examples/rogue_agent.py

agent-safe:
	python examples/safe_agent.py

agent-unmatched:
	python examples/unmatched_route.py

procurement-demo-safe:
	MIRAGE_RUN_ID=procurement-safe-demo python -m examples.procurement_harness.demo safe

procurement-demo-risky:
	MIRAGE_RUN_ID=procurement-risky-demo python -m examples.procurement_harness.demo risky

procurement-demo-unmatched:
	MIRAGE_RUN_ID=procurement-unmatched-demo python -m examples.procurement_harness.demo unmatched

demo-ui:
	HOST=$(HOST) PORT=$(PORT) python -m demo_ui.server

console-api:
	HOST=$(HOST) PORT=$(PORT) python -m demo_ui.server

ui-install:
	cd ui && pnpm install

ui-dev:
	cd ui && pnpm dev

ui-dev-local:
	cd ui && NEXT_PUBLIC_MIRAGE_API_BASE_URL=http://127.0.0.1:5100 pnpm dev

ui-build:
	cd ui && pnpm build

ui-test:
	cd ui && pnpm test

mirage-summary:
	python -m mirage.cli summarize-run --run-id $(RUN_ID)

mirage-gate:
	python -m mirage.cli gate-run --run-id $(RUN_ID)

mirage-validate-config:
	python -m mirage.cli validate-config

test:
	pytest tests/ -v -s

test-procurement:
	pytest tests/test_procurement_harness.py -v -s

worklog:
	python scripts/new_worklog.py "$(TITLE)"
