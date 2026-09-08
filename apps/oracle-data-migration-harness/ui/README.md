# Oracle Data Migration Harness UI

React + TypeScript + Vite frontend for the Oracle Data Migration Harness demo.

The UI provides a split-screen workflow for comparing the RAG experience before and after migrating a MongoDB-backed corpus into Oracle AI Database 26ai. It expects the FastAPI backend to be running on `http://localhost:8000`.

## Run locally

From the app root:

```bash
make ui
```

Or directly from this folder:

```bash
npm install
npm run dev
```

Open <http://localhost:5173>.

## Build

```bash
npm run build
```
