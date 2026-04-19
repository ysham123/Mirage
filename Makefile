PROCUREMENT_MOCKS=examples/procurement_harness/mocks.yaml
PROCUREMENT_POLICIES=examples/procurement_harness/policies.yaml

install:
	pip install -r requirements.txt

proxy:
	uvicorn src.proxy:app --reload

proxy-procurement:
	MIRAGE_MOCKS_PATH=$(PROCUREMENT_MOCKS) MIRAGE_POLICIES_PATH=$(PROCUREMENT_POLICIES) uvicorn src.proxy:app --reload

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
	python -m demo_ui.server

ui-install:
	cd ui && pnpm install

ui-dev:
	cd ui && pnpm dev

ui-build:
	cd ui && pnpm build

ui-test:
	cd ui && pnpm test

mirage-summary:
	python -m src.cli summarize-run --run-id $(RUN_ID)

mirage-gate:
	python -m src.cli gate-run --run-id $(RUN_ID)

mirage-validate-config:
	python -m src.cli validate-config

test:
	pytest tests/ -v -s

test-procurement:
	pytest tests/test_procurement_harness.py -v -s

worklog:
	python scripts/new_worklog.py "$(TITLE)"
