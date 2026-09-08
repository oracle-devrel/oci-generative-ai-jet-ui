"""Oracle MLE wrapper: runs JavaScript inside the database via DBMS_MLE.
Mirrors §9 of the notebook."""


def exec_js(agent_conn, code: str) -> dict:
    wrapper = (
        '(function() {\n'
        '  let _stdout = "";\n'
        '  let _stderr = "";\n'
        '  let _ok = true;\n'
        '  const _origLog = console.log;\n'
        '  console.log = function() {\n'
        '    _stdout += Array.from(arguments).map(String).join(" ") + "\\n";\n'
        '  };\n'
        '  try {\n'
        + code + '\n'
        '  } catch (e) {\n'
        '    _stderr = String(e && e.message ? e.message : e) + "\\n" + (e && e.stack ? e.stack : "");\n'
        '    _ok = false;\n'
        '  } finally {\n'
        '    console.log = _origLog;\n'
        '  }\n'
        '  const bindings = require("mle-js-bindings");\n'
        '  bindings.exportValue("result", JSON.stringify({stdout: _stdout, stderr: _stderr, ok: _ok}));\n'
        '})();'
    )
    plsql = """
DECLARE
  ctx DBMS_MLE.context_handle_t;
  buf CLOB;
BEGIN
  ctx := DBMS_MLE.create_context();
  DBMS_MLE.eval(ctx, 'JAVASCRIPT', :code);
  DBMS_MLE.import_from_mle(ctx, 'result', buf);
  DBMS_MLE.drop_context(ctx);
  :out := buf;
END;
"""
    with agent_conn.cursor() as cur:
        out_var = cur.var(str)
        cur.execute(plsql, code=wrapper, out=out_var)
        result_str = out_var.getvalue()
    import json as _json
    return _json.loads(result_str) if result_str else {"stdout": "", "stderr": "no result", "ok": False}
