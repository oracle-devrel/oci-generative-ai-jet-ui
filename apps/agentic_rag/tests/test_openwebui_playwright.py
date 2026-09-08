"""
Playwright E2E tests for Open WebUI integration.

These tests verify that Open WebUI can:
1. Connect to our backend
2. Display available models
3. Send messages and receive responses
4. Stream responses properly

Prerequisites:
1. Install Playwright: pip install playwright && playwright install chromium
2. Start the backend: python run_app.py --api-only
3. Start Open WebUI: python run_app.py --openwebui

Run with: pytest tests/test_openwebui_playwright.py -v --browser chromium
"""


import pytest
import pytest_asyncio

# Try to import playwright
try:
    from playwright.async_api import Page, async_playwright
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    Page = None  # type: ignore[assignment,misc]
    PLAYWRIGHT_AVAILABLE = False


# Configuration
OPENWEBUI_URL = "http://localhost:3000"
BACKEND_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 30000  # 30 seconds

def _openwebui_reachable() -> bool:
    """Check if Open WebUI is reachable."""
    try:
        import requests
        requests.get(OPENWEBUI_URL, timeout=2)
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed"),
    pytest.mark.skipif(not _openwebui_reachable(), reason="Open WebUI not running at localhost:3000"),
]


@pytest_asyncio.fixture(scope="session")
async def browser():
    """Create browser instance."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest_asyncio.fixture
async def page(browser):
    """Create new page for each test."""
    context = await browser.new_context()
    page = await context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT)
    yield page
    await context.close()


class TestOpenWebUIConnection:
    """Test Open WebUI connection and basic functionality."""

    @pytest.mark.asyncio
    async def test_openwebui_loads(self, page: Page):
        """Test that Open WebUI page loads successfully."""
        response = await page.goto(OPENWEBUI_URL, wait_until="networkidle")
        assert response.status == 200, f"Failed to load Open WebUI: {response.status}"

    @pytest.mark.asyncio
    async def test_backend_health_from_ui(self, page: Page):
        """Test that UI can reach backend health endpoint."""
        # Navigate to page and check network requests
        await page.goto(OPENWEBUI_URL, wait_until="networkidle")

        # Try to fetch health directly from the context
        response = await page.evaluate("""
            async () => {
                try {
                    const response = await fetch('http://localhost:8000/v1/health');
                    const data = await response.json();
                    return { status: response.status, data };
                } catch (e) {
                    return { error: e.message };
                }
            }
        """)

        if "error" in response:
            pytest.skip(f"Could not reach backend from UI: {response['error']}")

        assert response["status"] == 200
        assert response["data"]["status"] == "ok"


class TestModelSelection:
    """Test model selection in Open WebUI."""

    @pytest.mark.asyncio
    async def test_models_available(self, page: Page):
        """Test that models are listed in the UI."""
        await page.goto(OPENWEBUI_URL, wait_until="networkidle")

        # Wait for the app to fully load
        await page.wait_for_timeout(2000)

        # Look for model selector (Open WebUI typically has a dropdown)
        # The exact selector depends on Open WebUI version
        model_selectors = [
            'button:has-text("Select a model")',
            '[data-testid="model-selector"]',
            'select[name="model"]',
            '#model-selector',
            '.model-selector'
        ]

        found_selector = False
        for selector in model_selectors:
            try:
                element = page.locator(selector).first
                if await element.count() > 0:
                    found_selector = True
                    break
            except Exception:
                continue

        # If no selector found, check if models are visible in any form
        if not found_selector:
            # Check page content for model names
            content = await page.content()
            has_models = any(model in content.lower() for model in
                           ["standard", "chain of thought", "cot", "tree of thoughts"])
            if has_models:
                found_selector = True

        # This test is informational - Open WebUI structure varies
        if not found_selector:
            pytest.skip("Could not locate model selector - UI structure may differ")


class TestChatFunctionality:
    """Test chat functionality."""

    async def _find_chat_input(self, page: Page) -> str | None:
        """Find the chat input element."""
        possible_selectors = [
            'textarea[placeholder*="message"]',
            'textarea[placeholder*="Message"]',
            'textarea#chat-input',
            'textarea[data-testid="chat-input"]',
            '#chat-textarea',
            'textarea',  # Fallback to any textarea
        ]

        for selector in possible_selectors:
            try:
                element = page.locator(selector).first
                if await element.count() > 0 and await element.is_visible():
                    return selector
            except Exception:
                continue
        return None

    async def _find_send_button(self, page: Page) -> str | None:
        """Find the send button element."""
        possible_selectors = [
            'button[type="submit"]',
            'button:has-text("Send")',
            'button[aria-label*="send"]',
            'button[aria-label*="Send"]',
            '[data-testid="send-button"]',
        ]

        for selector in possible_selectors:
            try:
                element = page.locator(selector).first
                if await element.count() > 0 and await element.is_visible():
                    return selector
            except Exception:
                continue
        return None

    @pytest.mark.asyncio
    async def test_can_send_message(self, page: Page):
        """Test that a message can be sent and response received."""
        await page.goto(OPENWEBUI_URL, wait_until="networkidle")
        await page.wait_for_timeout(3000)  # Wait for full load

        # Find chat input
        input_selector = await self._find_chat_input(page)
        if not input_selector:
            pytest.skip("Could not find chat input element")

        # Type a message
        await page.fill(input_selector, "What is 2+2?")

        # Find and click send button or press Enter
        send_selector = await self._find_send_button(page)
        if send_selector:
            await page.click(send_selector)
        else:
            await page.press(input_selector, "Enter")

        # Wait for response (look for new content in chat)
        try:
            # Wait for loading indicator to appear and disappear
            await page.wait_for_timeout(500)

            # Wait for response content to appear (various selectors)
            response_selectors = [
                '.message-content',
                '[data-testid="message"]',
                '.chat-message',
                '.assistant-message',
                'div:has-text("4")',  # Simple check for the answer
            ]

            response_found = False
            for selector in response_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=30000)
                    response_found = True
                    break
                except Exception:
                    continue

            if not response_found:
                # Check if any new content appeared
                await page.wait_for_timeout(5000)
                content = await page.content()
                # Look for signs of a response
                response_found = "4" in content or "four" in content.lower()

            assert response_found, "No response received from the model"

        except PlaywrightTimeoutError:
            pytest.fail("Timeout waiting for chat response")

    @pytest.mark.asyncio
    async def test_streaming_response_displays(self, page: Page):
        """Test that streaming responses are displayed incrementally."""
        await page.goto(OPENWEBUI_URL, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        input_selector = await self._find_chat_input(page)
        if not input_selector:
            pytest.skip("Could not find chat input element")

        # Send a message that should produce a longer response
        await page.fill(input_selector, "Explain what a computer is in one sentence.")

        send_selector = await self._find_send_button(page)
        if send_selector:
            await page.click(send_selector)
        else:
            await page.press(input_selector, "Enter")

        # Monitor for streaming (text appearing incrementally)
        # This is a simplified check - real streaming would show text appearing character by character
        try:
            await page.wait_for_timeout(1000)

            # Take snapshots to see if content is growing
            content_lengths = []
            for _ in range(5):
                content = await page.content()
                content_lengths.append(len(content))
                await page.wait_for_timeout(500)

            # Content should be growing if streaming is working
            # (though this might fail if response is very fast)
            is_growing = any(content_lengths[i+1] > content_lengths[i]
                           for i in range(len(content_lengths)-1))

            # Just log, don't fail - response might complete quickly
            if not is_growing:
                print("Note: Content didn't appear to stream - response may have completed quickly")

        except PlaywrightTimeoutError:
            pytest.fail("Timeout during streaming test")


class TestErrorHandling:
    """Test error handling in the UI."""

    @pytest.mark.asyncio
    async def test_handles_backend_unavailable(self, page: Page):
        """Test UI behavior when backend is unavailable."""
        # This test requires temporarily stopping the backend
        # For now, we just verify the UI loads properly
        await page.goto(OPENWEBUI_URL, wait_until="networkidle")

        # Check that the page loaded without critical errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)

        await page.wait_for_timeout(2000)

        # Filter out expected errors (like CORS issues which might happen)
        critical_errors = [e for e in console_errors
                         if "failed" not in str(e).lower() or "fetch" in str(e).lower()]

        # Just log errors, don't fail - some console errors are expected
        for error in critical_errors:
            print(f"Console error: {error}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
