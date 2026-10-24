"""Shared file handling and presentation for the demo."""

import csv
from html import escape
import io
import json
import math
from pathlib import Path
import re
from typing import Literal

import pandas as pd
from IPython.display import Code, HTML, JSON, display
from matplotlib import pyplot as plt
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parent


class ModelOutputError(ValueError):
    """A generated request or report that the model can correct."""


class DemoAnalysisError(RuntimeError):
    """Stop a notebook step with a short, readable failure message."""

    def _render_traceback_(self):
        return [str(self)]


def read_json(path):
    """Read a UTF-8 JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def available_files(run):
    """Expose data and successful artifacts, never instructions or reference answers."""
    if "source_files" not in run:
        run["source_files"] = {
            path.name: path.read_bytes() for path in (ROOT / "assets").glob("*.csv")
        }
    return run["source_files"] | run["generated_files"]


def run_requested_code(*, conversation, sandboxes, response, validate_code):
    """Execute model tool requests and return results until the model answers."""
    corrections = 0
    executions = 0
    while conversation.requests_execution(response):
        try:
            tool_name, arguments = conversation.get_tool_call(response)
            if tool_name != "execute_python":
                raise ModelOutputError(f"Unknown tool: {tool_name}")
            payload = sandboxes.prepare_payload(arguments)
            validate_code(payload.code)
            if executions >= 5:
                raise DemoAnalysisError("The question reached the five-execution limit.")
            executions += 1
            try:
                sandbox = sandboxes.create_sandbox()
                result = sandbox.run_payload(payload)
            finally:
                sandboxes.shutdown()
            show_report(sandboxes.run, result)
        except ModelOutputError as error:
            if corrections >= 2:
                raise DemoAnalysisError(f"Analysis stopped after two corrections: {error}") from error
            corrections += 1
            result = error_result(error)
        response = conversation.send_result(response, result)
    conversation.show_answer(response)


class ChartSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["bar", "line", "scatter"]
    data_file: str
    x: str
    y: list[str] = Field(min_length=1)
    title: str = Field(min_length=1)
    x_label: str = Field(min_length=1)
    y_label: str = Field(min_length=1)


def chart_data(content, csv_files):
    """Resolve a chart against exact CSV bytes, never model-drawn coordinates."""
    spec = ChartSpec.model_validate_json(content)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\.csv", spec.data_file):
        raise ValueError("A chart must reference a simple CSV filename.")
    if spec.data_file not in csv_files:
        raise ValueError(f"Chart data file is unavailable: {spec.data_file}")
    data = pd.read_csv(io.BytesIO(csv_files[spec.data_file]))
    columns = [spec.x, *spec.y]
    if len(set(columns)) != len(columns) or not set(columns) <= set(data.columns):
        raise ValueError("Chart x and y must name distinct columns present in its CSV.")
    if data.empty or data[columns].isna().any().any():
        raise ValueError("Chart columns must have rows and no missing values.")
    numeric = spec.y if spec.kind == "bar" else columns
    for column in numeric:
        data[column] = pd.to_numeric(data[column], errors="raise")
        if not data[column].map(math.isfinite).all():
            raise ValueError(f"Chart column {column} contains non-finite values.")
    if spec.kind != "scatter" and data[spec.x].duplicated().any():
        raise ValueError("Bar and line charts need one row per x value; aggregate or pivot first.")
    return spec, data


def render_chart(spec, data):
    """Let Matplotlib compute marks and ticks from the same unmodified values."""
    fig, ax = plt.subplots(figsize=(9, 4.8), layout="constrained")
    if spec.kind == "bar":
        data.set_index(spec.x)[spec.y].plot.bar(ax=ax, rot=0)
    else:
        data = data.sort_values(spec.x)
        for column in spec.y:
            if spec.kind == "line":
                ax.plot(data[spec.x], data[column], marker="o", label=column)
            else:
                ax.scatter(data[spec.x], data[column], label=column)
    ax.set(title=spec.title, xlabel=spec.x_label, ylabel=spec.y_label)
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    ax.grid(axis="y", alpha=0.2)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", bbox_to_anchor=(1, 1))
    if spec.kind == "bar" and (len(data) > 6 or data[spec.x].astype(str).str.len().max() > 14):
        plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
    return fig


def reject_nonfinite(value):
    raise ValueError(f"JSON must contain finite numbers, not {value}")


def validate_artifact(name, content):
    """Check an output's format before storing it or returning it to the model."""
    if len(content) > 1_000_000:
        raise ValueError(f"{name}: output exceeds the one-megabyte limit")
    suffix = Path(name).suffix
    text = content.decode('utf-8')
    if suffix == '.json':
        value = json.loads(text, parse_constant=reject_nonfinite)
        if name.endswith(".chart.json") or (
            isinstance(value, dict) and {"kind", "data_file", "x", "y"} <= value.keys()
        ):
            suffix = ".chart"
    elif suffix == '.csv':
        try:
            rows = list(csv.reader(io.StringIO(text), strict=True))
        except csv.Error as error:
            raise ValueError(f'{name}: invalid CSV: {error}') from error
        if not rows or not rows[0] or any(not field for field in rows[0]):
            raise ValueError(f'{name}: CSV requires a header')
        if len(set(rows[0])) != len(rows[0]) or any(len(row) != len(rows[0]) for row in rows[1:]):
            raise ValueError(f'{name}: CSV columns must be unique and rows must match the header')
    elif suffix != '.txt':
        raise ValueError(f'Unsupported output format: {suffix}')
    return {'format': suffix[1:], 'content': text[:12000], 'truncated': len(text) > 12000}


def show_heading(title):
    """Space output headings, except above the first output in a JupyterLab cell."""
    display(HTML(
        "<style>.jp-OutputArea-child .sandboxes-demo-heading {margin: 0; padding: 18px 0 8px;}"
        ".jp-OutputArea-child:first-child .sandboxes-demo-heading {padding-top: 0;}"
        "</style>"
        f'<h3 class="sandboxes-demo-heading">{escape(title)}</h3>'
    ))


def show_message(title, message):
    """Show a JSON tree with shortened prompts and decoded tool JSON in a copy."""
    def format_preview_fields(fields):
        for key in ("arguments", "output"):
            if isinstance(fields.get(key), str):
                try:
                    fields[key] = json.loads(fields[key])
                except json.JSONDecodeError:
                    pass
        for key in ("instructions", "input", "prompt"):
            text = fields.get(key)
            if isinstance(text, str) and len(text) > 200:
                fields[key] = f"{text[:200]}… [{len(text) - 200:,} more characters]"
        return fields

    preview = json.loads(json.dumps(message), object_hook=format_preview_fields)
    show_heading(title)
    display(JSON(preview, expanded=False, root=title))
    for item in preview.get("output", []):
        if item.get("type") == "function_call":
            arguments = item.get("arguments")
            if isinstance(arguments, dict) and isinstance(arguments.get("code"), str):
                instructions = [
                    content["text"]
                    for entry in preview["output"] if entry.get("type") == "message"
                    for content in entry.get("content", [])
                    if content.get("type") == "output_text" and content.get("text")
                ]
                purpose = arguments.get("purpose")
                if isinstance(purpose, str) and purpose.strip():
                    instructions.append(purpose)
                if instructions:
                    show_heading("Model Instructions")
                    print("\n\n".join(instructions))
                input_files = arguments.get("input_files")
                if isinstance(input_files, list):
                    show_heading("Input Files")
                    print("\n".join(map(str, input_files)) or "No input files")
                show_heading("Generated Code")
                display(Code(arguments["code"], language="python"))


def error_result(error):
    return {
        "status": "error", "error": str(error)[-4000:],
        "instruction": "The requested tool action failed. Use the error details to correct "
                       "your request if you retry. Do not claim the failed action succeeded.",
    }


def show_report(run, result):
    """Display whichever supported artifacts the model chose to produce."""
    show_heading("Sandbox Execution Result")
    if result["stdout"].strip():
        print(result["stdout"])
    for name, report in result["files"].items():
        content = run["generated_files"][name]
        if report["format"] == "csv":
            display(pd.read_csv(io.BytesIO(content)))
        elif report["format"] == "chart":
            spec, data = chart_data(content, available_files(run))
            figure = render_chart(spec, data)
            try:
                display(figure)
            finally:
                plt.close(figure)
        elif report["format"] == "txt":
            print(content.decode("utf-8"))


def store_outputs(run, artifacts, stdout):
    """Validate all reports before making them available to follow-up requests."""
    try:
        files = {name: validate_artifact(name, content) for name, content in artifacts.items()}
        csv_files = available_files(run)
        csv_files.update({name: content for name, content in artifacts.items() if name.endswith(".csv")})
        for name, content in artifacts.items():
            if files[name]["format"] == "chart":
                chart_data(content, csv_files)
        if not files and not stdout.strip():
            raise ValueError("The program produced neither text nor declared output files.")
    except ValueError as error:
        raise ModelOutputError(f"Report validation failed: {error}") from error
    run["generated_files"].update(artifacts)
    return {"status": "success", "stdout": stdout[:12000],
            "stdout_truncated": len(stdout) > 12000, "files": files}
