.PHONY: install seed embed app ui notebook test cache fallback reset

PYTHON ?= python3

install:
	$(PYTHON) -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
	cd ui && npm install

seed:
	$(PYTHON) scripts/seed_mongo.py

embed:
	$(PYTHON) scripts/embed_mongo.py

app:
	uvicorn data_migration_harness.app:app --reload --port 8000

ui:
	cd ui && npm run dev

notebook:
	jupyter lab ../../notebooks/oracle_data_migration_harness_walkthrough.ipynb

cache:
	$(PYTHON) scripts/cache_demo_responses.py

test:
	pytest -v

fallback:
	@echo "Record desktop video manually; save to assets/migration-fallback.mp4"

reset:
	curl -s -X POST http://localhost:8000/reset && echo
