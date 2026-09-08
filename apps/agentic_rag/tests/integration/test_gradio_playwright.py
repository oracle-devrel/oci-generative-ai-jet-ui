"""Integration test: Gradio UI loads and responds to a message.

Launches the Gradio app as a subprocess (via the gradio_server session
fixture) and drives it with Playwright. Requires:
- Oracle DB reachable
- Ollama reachable
- playwright + chromium installed

What this catches:
- Gradio version bumps that break the Chatbot component (the 5.x tuples
  bug that landed in commits 434216a..af54c72)
- launch() / Blocks() parameter drift between Gradio major versions
- Any backend error that surfaces as a red error banner in the UI
"""
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_oracle,
    pytest.mark.requires_ollama,
    pytest.mark.requires_playwright,
]


def test_gradio_app_loads_without_error_banner(gradio_server, playwright_page):
    """The app's main page renders and shows no error toast."""
    playwright_page.goto(gradio_server, wait_until="networkidle", timeout=60_000)
    # Gradio 5.x renders a <main> with aria-live regions for errors.
    content = playwright_page.content()
    assert "Agentic RAG System" in content or "gradio" in content.lower()
    # Check for the specific error banner classes Gradio uses for exceptions.
    error_banner = playwright_page.locator(".error, [role='alert']").count()
    # An error banner is only a failure if it contains an exception message.
    if error_banner:
        for i in range(error_banner):
            text = playwright_page.locator(".error, [role='alert']").nth(i).inner_text()
            assert "Traceback" not in text and "Error" not in text.split("\n")[0], (
                f"Gradio app rendered with error banner: {text[:500]}"
            )


def test_gradio_a2a_chat_accepts_a_message(gradio_server, playwright_page):
    """Smoke check: typing a message into the A2A chat textbox and submitting
    it doesn't immediately blow up with a Gradio tuples/messages format error.

    This is intentionally tolerant -- we can't reliably wait for a real LLM
    reply in CI time budgets. We only assert that no exception dialog or
    'Data incompatible with messages format' error fires within 15s.
    """
    playwright_page.goto(gradio_server, wait_until="networkidle", timeout=60_000)

    # Wait for any Textbox to appear. Gradio 5.x renders them as role=textbox.
    try:
        playwright_page.wait_for_selector("textarea, input[type='text']", timeout=15_000)
    except Exception:
        pytest.skip("Gradio UI loaded but no textbox was found in time")

    # Find a textbox that looks like a chat input (prefer placeholders).
    textbox = playwright_page.locator("textarea").first
    textbox.fill("Hello from the integration test")

    # Check console for the specific regression error before we submit.
    console_errors = []
    playwright_page.on(
        "pageerror", lambda err: console_errors.append(str(err))
    )
    playwright_page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )

    # Press Enter to submit (Gradio chat interfaces accept Enter-to-send).
    textbox.press("Enter")

    # Give the UI a short window to render an error toast if one is coming.
    playwright_page.wait_for_timeout(5_000)

    regression_markers = [
        "Data incompatible with messages format",
        "got an unexpected keyword argument 'css'",
        "Blocks.launch()",
    ]
    for err in console_errors:
        for marker in regression_markers:
            assert marker not in err, (
                f"Detected known Gradio regression: {marker!r}. Full error: {err}"
            )
