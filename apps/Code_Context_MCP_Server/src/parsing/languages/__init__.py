"""One file per language. Importing this package registers every language in parsing.tables, in this order."""

# The languages register in this order, so the imports are not sorted.
# isort: off
from golestan_code_mcp.parsing.languages import python  # noqa: F401
from golestan_code_mcp.parsing.languages import go  # noqa: F401
from golestan_code_mcp.parsing.languages import javascript  # noqa: F401
from golestan_code_mcp.parsing.languages import csharp  # noqa: F401
from golestan_code_mcp.parsing.languages import typescript  # noqa: F401
from golestan_code_mcp.parsing.languages import c_family  # noqa: F401
from golestan_code_mcp.parsing.languages import java  # noqa: F401
from golestan_code_mcp.parsing.languages import kotlin  # noqa: F401
from golestan_code_mcp.parsing.languages import rust  # noqa: F401
from golestan_code_mcp.parsing.languages import php  # noqa: F401
from golestan_code_mcp.parsing.languages import ruby  # noqa: F401
from golestan_code_mcp.parsing.languages import swift  # noqa: F401
# isort: on
