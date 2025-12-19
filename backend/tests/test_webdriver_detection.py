# test_webdriver_detection.py
import asyncio
from playwright.async_api import async_playwright

async def test_with_flag():
    """Test CON --disable-blink-features=AutomationControlled"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']  # Disabilita la proprietà navigator.webdriver
        )
        page = await browser.new_page()
        
        # Check navigator.webdriver
        webdriver = await page.evaluate("() => navigator.webdriver")
        print(f"CON flag: navigator.webdriver = {webdriver}")
        
        await browser.close()

async def test_without_flag():
    """Test SENZA flag (default Playwright)"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Check navigator.webdriver
        webdriver = await page.evaluate("() => navigator.webdriver")
        print(f"SENZA flag: navigator.webdriver = {webdriver}")
        
        await browser.close()

async def main():
    print("Test navigator.webdriver Detection\n")
    
    await test_without_flag()
    print()
    await test_with_flag()

asyncio.run(main())
