"""Execute in this directory using the current Python interpreter."""

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

root = Path(__file__).resolve().parent
notebook = root / "context_assembly_walkthrough.ipynb"
nb = nbformat.read(notebook, as_version=4)
client = NotebookClient(nb, timeout=180, resources={"metadata": {"path": str(root)}})
client.create_kernel_manager()
# Avoid installing a persistent kernelspec for this execution.
spec = client.km.kernel_spec
spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
client.execute()
nbformat.write(nb, notebook)
print(f"Executed {sum(c.cell_type == 'code' for c in nb.cells)} code cells successfully.")
