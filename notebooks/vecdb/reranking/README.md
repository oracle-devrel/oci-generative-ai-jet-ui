[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)](#)
[![Python](https://img.shields.io/pypi/pyversions/oracle-vecdb)](https://pypi.org/project/oracle-vecdb/)
[![oracle-vecdb](https://img.shields.io/badge/oracle-vecdb-2EA44F?logo=oracle&logoColor=white)](#)
[![OCI](https://img.shields.io/badge/OCI-Generative%20AI-0072CE?logo=oracle&logoColor=white)](#)

# VecDB Reranking Notebooks

Reranking is a second-stage operation: first retrieve candidates with a VecDB semantic search, then score and reorder those candidates with a reranking model. These notebooks demonstrate two alternative ways to use reranking models.

## Choose a reranking path

| Path                                     | Notebook                                                                                     | Use this when                                                                                                                                                                                | Main prerequisites                                                                                                              |
| ---------------------------------------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| In-database model pipeline and reranking | [`load-model-for-in-database-reranking.ipynb`](./load-model-for-in-database-reranking.ipynb) | You want to download a Hugging Face model, convert and validate ONNX, upload it to OCI Object Storage, load it into Oracle AI Database, and run in-database reranking through the VecDB SDK. | Docker or Podman, the Oracle OML4Py 2.1.1 client archive, OCI CLI configured for Object Storage, and permission to load models. |
| OCI-hosted reranking                     | [`oci-reranking.ipynb`](./oci-reranking.ipynb)                                               | You want VecDB retrieval followed by OCI Generative AI `RerankText`.                                                                                                                         | OCI Generative AI access, an on-demand reranking model in a supported region, and an embedding model available in VecDB.        |

The notebooks are alternatives, not sequential steps. Use the first notebook only when you need to convert and load your own in-database reranking model. The second notebook does not load a model into VecDB.

## Before you run

### Both paths

- A working VecDB REST endpoint and credentials.
- Python 3.10 or later with the packages listed in the selected notebook.
- A `.env` file based on [`.env.example`](./.env.example).
- Jupyter with a working directory inside the repository; the notebook finds `.env` from the repository root or the notebook directory.

### In-database model pipeline and reranking

- Run the notebook's installation cell to install the host-side Python packages.
- Install [Docker Desktop](https://docs.docker.com/desktop/) or [Podman](https://podman.io/docs/installation), and allocate at least 12 GB to the container virtual machine.
- Download Oracle's [OML4Py 2.1.1 client archive](https://www.oracle.com/database/technologies/oml4py-downloads.html).
- Install the [OCI CLI](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm) and configure a profile that can upload to Object Storage and manage PARs.
- Use Oracle AI Database 26ai or later with permission to load and rerank models.

The notebook uses a public Python container for conversion; it does not require the licensed OML4Py container or an Oracle Container Registry login.

### OCI-hosted reranking

- Have OCI Generative AI access and use a region where the selected reranking model is available on-demand.
- Have an embedding model available in VecDB for the first-stage semantic search.

## Open in Google Colab

- [In-database reranking](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/vecdb/reranking/load-model-for-in-database-reranking.ipynb)
- [OCI-hosted reranking](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/vecdb/reranking/oci-reranking.ipynb)

For the complete Python SDK procedures, use the companion VecDB documentation.
