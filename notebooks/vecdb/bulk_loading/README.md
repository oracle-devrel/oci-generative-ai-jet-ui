[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)](#) [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](#) [![oracle-vecdb](https://img.shields.io/badge/oracle-vecdb-F80000?logo=oracle&logoColor=white)](#)

# Bulk Loading & Listings Notebook

These notebooks show end-to-end VecDB ingestion flows for metadata-only, BYO vectors with IDs, and BYO vectors with auto-generated IDs. Open the notebook that matches the scenario you need:

- `01_integrated_embedding.ipynb` – Bulk load metadata into a table with integrated embeddings.
- `02_byov_ids.ipynb` – Bulk load bring-your-own vectors with manual IDs.
- `03_byov_auto_ids.ipynb` – Bulk load bring-your-own vectors with database-generated IDs.

> **Embedding model prep:** Scenario A assumes an embedding model already exists in VecDB. Deploy it beforehand and set `EMBED_MODEL` in `.env` to that model’s name. This scenario does not upload or load ONNX artifacts on your behalf.

### Sample CSV fixtures

Fresh example datasets live under `bulk_loading/data/` so you can upload them to Object Storage and reuse the signed URL in `.env`:

| Scenario | Sample file | Columns | `.env` variable | Sample PAR |
| --- | --- | --- | --- | --- |
| Integrated embeddings | `bulktable_integrated_embedding.csv` | `METADATA, ID` | `INTEGRATED_CSV_URL` | `https://objectstorage.<region>.oraclecloud.com/p/<PAR_TOKEN>/n/<namespace>/b/<bucket>/o/sample_csv_data/bulktable_integrated_embedding.csv` |
| BYO vectors (manual IDs) | `bulktable_byov_ids.csv` | `ID, DENSE_VECTOR, METADATA` | `BYO_MANUAL_CSV_URL` | `https://objectstorage.<region>.oraclecloud.com/p/<PAR_TOKEN>/n/<namespace>/b/<bucket>/o/sample_csv_data/bulktable_byov_ids.csv` |
| BYO vectors (auto IDs) | `bulktable_byov_auto_ids.csv` | `DENSE_VECTOR, METADATA` | `BYO_AUTO_CSV_URL` | `https://objectstorage.<region>.oraclecloud.com/p/<PAR_TOKEN>/n/<namespace>/b/<bucket>/o/sample_csv_data/bulktable_byov_auto_ids.csv` |

#### How to publish the CSVs to Object Storage

1. **Pick a bucket/object path.** The repo already includes ready-to-upload files under `bulk_loading/data/`. Use predictable object names so you can rotate URLs without guessing.
2. **Upload each CSV via direct `curl -T`.** Example (repeat per file with the right filename):
   ```bash
   curl -T bulk_loading/data/bulktable_byov_auto_ids.csv \
     "https://objectstorage.<region>.oraclecloud.com/p/<PAR_TOKEN>/n/<namespace>/b/<bucket>/o/sample_csv_data/bulktable_byov_auto_ids.csv"
   ```
   Replace `<PAR_TOKEN>`, `<namespace>`, and `<bucket>` with your actual values (the sample URLs in the table show the expected shape).
3. **Update `.env`.** Paste the exact HTTPS URL you used for the upload into `INTEGRATED_CSV_URL`, `BYO_MANUAL_CSV_URL`, or `BYO_AUTO_CSV_URL` as needed. The notebooks download directly from these links.
4. **Quick validation.** Open the uploaded object in a browser to ensure the header row and quoting look identical to the local file. VecDB requires commas as separators, quoted vector/JSON fields, and escaped double quotes (`""`) inside the metadata JSON.

Each scenario walks through table provisioning, `load_vectors`, job inspection, pagination via `list_vectors`, catalog checks via `list_vector_tables`, and an automated cleanup at the end so the environment stays tidy.

## Prerequisites

- Python 3.10+ with `oracle-vecdb`, `python-dotenv`, and `pandas` (a `%pip install` helper cell is provided).
- A `.env` file that provides:
- `VECDB_REST_URL`, `VECDB_USERNAME`, `VECDB_PASSWORD`
  - `EMBED_MODEL` → name of an embedding model that already exists inside VecDB (deploy it using the model-management example before running Scenario A)
  - `EMBED_MODEL_URL` → (optional) retained for backward compatibility; Scenario A no longer auto-loads models from Object Storage
  - `INTEGRATED_CSV_URL` → signed Object Storage URL for `bulktable_integrated_embedding.csv`
  - `BYO_MANUAL_CSV_URL` → signed Object Storage URL for `bulktable_byov_ids.csv`
  - `BYO_AUTO_CSV_URL` → signed Object Storage URL for `bulktable_byov_auto_ids.csv`
- Object Storage access to host the CSVs (public PAR URLs or buckets readable by VecDB).

> **Auto-ID reminder:** Scenario C only produces database-generated IDs when the CSV omits the `ID` column (or leaves it empty). Create an ID-free dataset (see `bulktable_byov_auto_ids.csv`), upload it to Object Storage, and point `BYO_AUTO_CSV_URL` to that object before running the auto-ID cells.

## Running the Notebook

1. Open the scenario notebook you need (`01_...`, `02_...`, or `03_...`) and run the setup cells to install dependencies and authenticate.
2. Execute the scenario cells in order (table creation → load → job inspection → listings).
3. Finish with the cleanup cell so the demo tables do not linger in your VecDB environment.

> **Run checklist**
> 1. Upload/refresh the CSV in Object Storage.
> 2. Create or verify a PAR and update `.env`.
> 3. Drop/recreate the scenario table (integrated, BYO-ID, BYO-auto).
> 4. Execute the load job, inspect job logs/details, then move to listings and cleanup.
