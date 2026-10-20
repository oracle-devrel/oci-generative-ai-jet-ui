"""Distillation: the model's text from exactly the documented inputs, its failures, and unknown names."""

import json

from golestan_code_mcp.memory import consolidate
from golestan_code_mcp.memory import distill

from memory.helpers import FakeLlm, ask, facts_of, make_repo, with_model


def test_model_writes_the_text_from_exactly_the_documented_inputs(ready, repo, monkeypatch):
    name, _ = repo
    llm = FakeLlm()
    with_model(monkeypatch, llm)
    ask("search_code", query="where is spin_widget defined", repo=name, limit=7)
    ask("find_callers", name="spin_widget", repo=name)
    consolidate.consolidate(ready, name)
    f = facts_of(ready, name)["spin_widget"]
    assert (f.text, f.distiller) == (llm.text, "llm:fake/model")
    assert len(llm.prompts) == 1  # one call per changed fact, none from the package (linking is off)
    prompt = llm.prompts[0]
    assert "def spin_widget(w):" in prompt and "where is spin_widget defined" in prompt and "use_widget" in prompt
    assert '"limit"' not in prompt and "client" not in prompt.lower()


def test_model_failure_falls_back_to_the_template(ready, repo, monkeypatch, caplog):
    import logging
    name, _ = repo
    with_model(monkeypatch, FakeLlm(fail=True))
    ask("get_symbol", name="spin_widget", repo=name)
    with caplog.at_level(logging.WARNING, logger="golestan_code_mcp.memory"):
        [c] = consolidate.consolidate(ready, name)
    f = facts_of(ready, name)["spin_widget"]
    assert f.distiller == distill.TEMPLATE and f.text.startswith("`spin_widget` is a function")
    assert c.distillers == {distill.TEMPLATE: 1}
    assert sum("memory_model_failed" in r.getMessage() for r in caplog.records) == 1


def test_model_text_naming_unknown_code_is_rejected(ready, repo, monkeypatch, caplog):
    import logging
    name, _ = repo
    with_model(monkeypatch, FakeLlm("`spin_widget` calls `launch_rockets` and `secret_module.boom`."))
    ask("get_symbol", name="spin_widget", repo=name)
    with caplog.at_level(logging.WARNING, logger="golestan_code_mcp.memory"):
        consolidate.consolidate(ready, name)
    assert facts_of(ready, name)["spin_widget"].distiller == distill.TEMPLATE
    [rec] = [json.loads(r.getMessage()) for r in caplog.records if "memory_model_rejected" in r.getMessage()]
    assert set(rec["names"]) == {"launch_rockets", "secret_module.boom"} and "calls" not in json.dumps(rec)


def test_the_model_never_decides_subject_runs_or_confidence(ready, tmp_path, monkeypatch):
    outcomes = []
    for i, llm in enumerate((None, FakeLlm())):
        name = make_repo(ready, tmp_path / f"r{i}")
        if llm:
            with_model(monkeypatch, llm)
        for q in ("where is spin_widget defined", "spin it"):
            ask("search_code", query=q, repo=name)
        consolidate.consolidate(ready, name)
        outcomes.append({s: (len(f.runs), f.confidence) for s, f in facts_of(ready, name).items()})
    assert outcomes[0] == outcomes[1]


def test_unknown_names():
    allowed = {"spin_widget", "Widget", "pkg/widgets.py", "turn_helper"}
    assert distill.unknown_names("`spin_widget` lives in `pkg/widgets.py` and wraps `turn_helper`.", allowed) == []
    assert distill.unknown_names("It calls `boom_now` via os.path.join and RocketLauncher.", allowed) == [
        "boom_now", "os.path.join", "RocketLauncher"]


def test_names_from_the_source_sent_are_allowed_and_prose_is_not_a_name():
    sent = "def get(self, name, default=None):\n    return self.__dict__.get(name, default)\nmarkupsafe.escape"
    assert distill.unknown_names("`get` wraps `self.__dict__.get` and markupsafe.escape.", {sent}) == []
    # unpaired backticks: the prose between them is not a name, the code-shaped words still are
    assert distill.unknown_names("`get` method is defined in `app.py` as noted by `boom_now", {sent}) == ["app.py", "boom_now"]
    assert distill.unknown_names("It returns view_args via `--debug`.", {sent}) == ["view_args"]
