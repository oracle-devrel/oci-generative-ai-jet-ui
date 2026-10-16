"""Oracle MLE wrapper: runs JavaScript inside the database via DBMS_MLE.
Mirrors §9 of the notebook.

exec_js is advertised as "no filesystem, no network" scratch computation, but a
bare MLE context also hands the script `session` / `oracledb` /
`require("mle-js-oracledb")`: a live connection as AGENT that can run any SQL
(reproduced: it read AGENT.AGENT_CLEARANCES, a table `run_sql` refuses). The
wrapper therefore removes those before the model's code runs and leaves
`require` only the bindings module the wrapper itself needs.
"""


def exec_js(agent_conn, code: str) -> dict:
    wrapper = (
        '(function() {\n'
        '  let _stdout = "";\n'
        '  let _stderr = "";\n'
        '  let _ok = true;\n'
        '  const _origLog = console.log;\n'
        '  const _bindings = require("mle-js-bindings");\n'
        '  (function() {\n'
        '    globalThis.require = function(name) {\n'
        '      throw new Error("module " + name + " is not available in exec_js");\n'
        '    };\n'
        '    for (const k of ["session", "oracledb"]) {\n'
        '      try { delete globalThis[k]; } catch (e) {}\n'
        '      if (globalThis[k] !== undefined) { globalThis[k] = undefined; }\n'
        '    }\n'
        '  })();\n'
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
        '  _bindings.exportValue("result", JSON.stringify({stdout: _stdout, stderr: _stderr, ok: _ok}));\n'
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
