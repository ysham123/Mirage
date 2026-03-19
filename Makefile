install:
	pip install -r requirements.txt

proxy:
	uvicorn src.proxy:app --reload

agent:
	python examples/rogue_agent.py

test:
	pytest tests/ -v -s