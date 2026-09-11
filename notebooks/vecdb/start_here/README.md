[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)](#)
[![Python](https://img.shields.io/pypi/pyversions/oracle-vecdb)](https://pypi.org/project/oracle-vecdb/)
[![oracle-vecdb](https://img.shields.io/badge/oracle-vecdb-2EA44F?logo=oracle&logoColor=white)](#)

# Start here

Use these notebooks to configure access to Oracle AI Database and run your first Oracle VecDB Python SDK workflow.

| Notebook | Use it when | Prerequisites |
| --- | --- | --- |
| [`quickstart.ipynb`](./quickstart.ipynb) | You want to create a vector table, load records, and run your first semantic search. | Oracle AI Database with the `all_MiniLM_L12_v2` embedding model loaded, a vector user, and the SDK REST endpoint. |
| [`connect.ipynb`](./connect.ipynb) | You want to configure username and password or OAuth 2.0 authentication, verify the connection, or review TLS, proxy, and retry options. | Oracle AI Database with the VecDB REST endpoint and either vector-user credentials or an OAuth 2.0 bearer token. |

## Run the notebooks

1. Run [`quickstart.ipynb`](./quickstart.ipynb) for the shortest path to a working semantic search.
2. Run [`connect.ipynb`](./connect.ipynb) when you need the full authentication and connection-configuration guide.

Open the [Quickstart notebook in Google Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/vecdb/start_here/quickstart.ipynb) or the [connection notebook in Google Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/vecdb/start_here/connect.ipynb).

When you are ready for a task-specific workflow, return to the [VecDB sample notebook catalog](../README.md).
