import pytest
from playwright.async_api import async_playwright

@pytest.mark.asyncio
async def test_onboarding_flow():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("http://localhost:3000/onboarding")
        # Simulate user actions (adjust selectors based on your frontend)
        await page.fill("#email", "test@example.com")
        await page.click("#submit")
        # Check if progress is saved (adjust based on your UI)
        await page.wait_for_selector("#progress-saved")
        assert await page.is_visible("#progress-saved")
        await browser.close()