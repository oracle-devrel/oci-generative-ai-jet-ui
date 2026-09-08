# Makefile for the RAG on Oracle 26ai demo
# Usage:  make <target>
# Run `make help` to see all targets.

.PHONY: help setup db-up db-down db-init db-status seed run clean reset

# Default target
help:
	@echo "RAG on Oracle AI Database 26ai - available targets:"
	@echo ""
	@echo "  make setup       Create venv, install deps, copy .env"
	@echo "  make db-up       Start the Oracle Database container"
	@echo "  make db-down     Stop the database (keeps data)"
	@echo "  make db-init     Configure VECTOR_MEMORY_SIZE for HNSW (one-time)"
	@echo "  make db-status   Show database container status"
	@echo "  make seed        Load the embedding model and source PDFs"
	@echo "  make run         Launch the Streamlit chat UI"
	@echo "  make clean       Remove downloaded data files (keeps DB and venv)"
	@echo "  make reset       Wipe everything and start over"
	@echo ""
	@echo "Typical first-time setup:"
	@echo "  make setup && make db-up && make db-init && make seed && make run"

setup:
	@if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
	@. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
	@if [ ! -f ".env" ]; then cp .env.example .env; echo "Created .env from .env.example"; fi
	@echo "Setup complete. Run: make db-up"

db-up:
	docker compose up -d
	@echo "Database starting. Check status with: make db-status"

db-down:
	docker compose down

db-status:
	@docker compose ps

db-init:
	@echo "Configuring VECTOR_MEMORY_SIZE for HNSW indexing (requires DB restart)..."
	@docker exec -i oracle-26ai-rag sqlplus -s / as sysdba < scripts/init_db.sql
	@echo "Database restart in progress. Wait until 'make db-status' shows (healthy)."

seed:
	@. .venv/bin/activate && python3 seed.py

run:
	@. .venv/bin/activate && streamlit run app.py

clean:
	rm -f data/*.onnx data/*.pdf

reset:
	docker compose down -v
	rm -rf .venv data/*.onnx data/*.pdf
	@echo "Reset complete. Start over with: make setup"
