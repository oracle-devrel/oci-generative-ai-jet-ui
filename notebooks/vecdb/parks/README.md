[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)](#) [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](#) [![oracle-vecdb](https://img.shields.io/badge/oracle-vecdb-F80000?logo=oracle&logoColor=white)](#)

# Parks Notebook Quickstart

`parks-demo.ipynb` demonstrates end-to-end interaction with the sample National Parks dataset using the oracle-vecdb Python SDK:

- Connects to Oracle Autonomous AI Vector Database and inspects vector database statistics.
- Describes the parks vector table and previews metadata.
- Executes vector searches blended with metadata filters.
- Generates and upserts a temporary embedding for walkthrough purposes, then cleans up.

### Prerequisites
- `.env` file with `VECDB_REST_URL`, username/password or token credentials.
- Python 3.10+ environment with `oracle-vecdb`, `python-dotenv`, and `pandas` installed.
- Register the notebook kernel against your project virtual environment before running cells.

The notebook includes a cleanup cell to remove any temporary demo vectors you create while exploring the workflow.