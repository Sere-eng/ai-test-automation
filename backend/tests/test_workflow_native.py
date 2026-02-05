"""
Test nativo del workflow AMC - chiamate dirette ai tool senza MCP/HTTP
Verifica che il discovery pattern funzioni end-to-end
"""
import asyncio
import sys
import os

# Aggiungi backend al path (parent directory di tests/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools import PlaywrightTools
from config.settings import AppConfig
import json


async def main():
    """Esegue il workflow completo con discovery pattern"""
    
    print("\n" + "="*80)
    print("TEST WORKFLOW AMC - NATIVE CALLS (NO MCP, NO LLM)")
    print("="*80)
    
    tools = PlaywrightTools()
    
    try:
        # STEP 1: Start browser
        print("\n🌐 STEP 1: Starting browser...")
        result = await tools.start_browser(headless=False)
        print(f"   {result['status']}: {result['message']}")
        
        # STEP 2: Navigate to login
        print("\n🌐 STEP 2: Navigating to AMC login...")
        result = await tools.navigate_to_url("https://amc.eng.it/multimodule/web/")
        print(f"   {result['status']}: {result['url']}")
        await tools.page.wait_for_timeout(2000)
        
        # STEP 3: Inspect login form (no need to wait for specific element)
        print("\n🔍 STEP 3: Inspecting login form...")
        result = await tools.inspect_interactive_elements()
        print(f"   {result['status']}: {result['message']}")
        
        # Parse risultati
        form_fields = result.get("form_fields", [])
        clickable = result.get("clickable_elements", [])
        
        print("\n📋 Discovered elements:")
        username_field = None
        password_field = None
        login_button = None
        
        for field in form_fields:
            name = field.get('accessible_name', '').lower()
            print(f"  Form field: {field.get('accessible_name')} ({field.get('type', 'text')})")
            if 'username' in name or 'user' in name:
                username_field = field
            elif 'password' in name or 'pass' in name:
                password_field = field
        
        for elem in clickable:
            name = elem.get('accessible_name', '').lower()
            print(f"  Clickable: {elem.get('accessible_name')} ({elem.get('role')})")
            if 'accedi' in name or 'login' in name:
                login_button = elem
        
        if not all([username_field, password_field, login_button]):
            raise Exception("Missing login elements")
        
        # Extract locators
        user_loc = username_field['playwright_suggestions'][0]['fill_smart']
        pass_loc = password_field['playwright_suggestions'][0]['fill_smart']
        login_loc = login_button['playwright_suggestions'][0]['click_smart']
        
        print(f"\n📝 Using discovered locators:")
        print(f"  Username: {user_loc}")
        print(f"  Password: {pass_loc}")
        print(f"  Login: {login_loc}")
        
        print(f"\n🔑 Credentials from .env:")
        print(f"  Username: {AppConfig.AMC.USERNAME}")
        print(f"  Password: {'*' * len(AppConfig.AMC.PASSWORD)}")
        
        # STEP 4-6: Fill login form
        print("\n✏️ STEP 4: Filling username...")
        result = await tools.fill_smart([user_loc], AppConfig.AMC.USERNAME)
        print(f"   {result['status']}: strategy={result.get('strategy', 'N/A')}")
        await tools.page.wait_for_timeout(500)
        
        print("\n✏️ STEP 5: Filling password...")
        result = await tools.fill_smart([pass_loc], AppConfig.AMC.PASSWORD)
        print(f"   {result['status']}: strategy={result.get('strategy', 'N/A')}")
        await tools.page.wait_for_timeout(500)
        
        # Screenshot prima del login
        print("\n📸 DEBUG: Screenshot prima del login...")
        await tools.capture_screenshot(filename="debug_before_login.png", return_base64=False)
        
        print("\n🖱️ STEP 6: Submitting login (pressing Enter)...")
        # Invece di cliccare il bottone, premi Enter sul campo password
        result = await tools.press_key("Enter")
        print(f"   {result['status']}: {result.get('message', 'N/A')}")
        
        print("\n⏳ STEP 7: Waiting for navigation (domcontentloaded)...")
        # Aspetta che la navigazione completi (usando Playwright direttamente)
        try:
            await tools.page.wait_for_load_state('domcontentloaded', timeout=15000)
            print(f"   ✓ Navigation completed")
        except Exception as e:
            print(f"   ⚠️ Navigation timeout: {str(e)}")
        
        # Verifica URL attuale
        page_info = await tools.get_page_info()
        print(f"\n🌐 Current URL: {page_info.get('url', 'N/A')}")
        
        # Screenshot dopo login
        print("\n📸 DEBUG: Screenshot dopo login...")
        await tools.capture_screenshot(filename="debug_after_login.png", return_base64=False)
        
        # Se siamo ancora su /sso/login, login fallito
        if "/sso/login" in page_info.get('url', ''):
            raise Exception(f"Login failed - still on SSO page: {page_info.get('url')}")
        
        # Aspetta che Angular sia montato (root component presente)
        print("\n⏳ Waiting for Angular root component...")
        result = await tools.wait_for_element("[ng-version]", state="attached", timeout=10000)
        if result['status'] == 'success':
            print(f"   ✓ Angular mounted")
        else:
            print(f"   ⚠️ Warning: {result.get('message', 'N/A')} - continuing anyway")
        
        # Aspetta che menu principale sia caricato (attende bottone Micrologistica)
        print("\n⏳ Waiting for main menu to load...")
        result = await tools.wait_for_element('[aria-label="Micrologistica"]', state="visible", timeout=10000)
        if result['status'] == 'success':
            print(f"   ✓ Main menu loaded")
        else:
            print(f"   ⚠️ Warning: {result.get('message', 'N/A')} - continuing anyway")
        
        await tools.page.wait_for_timeout(1000)  # Breve stabilizzazione
        print(f"   ✓ Page stabilized")
        
        # STEP 8: Find Micrologistica
        print("\n🔍 STEP 8: Inspecting home page...")
        result = await tools.inspect_interactive_elements()
        
        print(f"\n📋 Found {len(result.get('clickable_elements', []))} clickable elements:")
        for elem in result.get("clickable_elements", [])[:10]:  # Mostra primi 10
            print(f"  - {elem.get('accessible_name', 'N/A')} ({elem.get('role', 'N/A')})")
        
        micro_button = None
        for elem in result.get("clickable_elements", []):
            if "micrologistica" in elem.get("accessible_name", "").lower():
                micro_button = elem
                print(f"\n  ✓ Found Micrologistica - FULL DETAILS:")
                print(f"     {json.dumps(elem, indent=6)}")
                break
        
        if not micro_button:
            raise Exception("Micrologistica not found")
        
        micro_loc = micro_button['playwright_suggestions'][0]['click_smart']
        
        print("\n🖱️ STEP 9: Clicking Micrologistica...")
        # Prova TUTTE le strategie suggerite
        all_strategies = [s['click_smart'] for s in micro_button['playwright_suggestions']]
        print(f"   Available strategies: {len(all_strategies)}")
        
        result = await tools.click_smart(all_strategies, timeout_per_try=3000)
        print(f"   Result: {result['status']}")
        print(f"   Message: {result.get('message', 'N/A')}")
        print(f"   Used strategy: {result.get('strategy', 'N/A')}")  # Corretto: era 'strategies_tried'

        
        await tools.page.wait_for_timeout(3000)  # SPA - aspetta caricamento menu
        
        # Debug: mostra URL e screenshot
        page_info = await tools.get_page_info()
        print(f"   Current URL: {page_info.get('url', 'N/A')}")
        await tools.capture_screenshot(filename="debug_after_micro.png", return_base64=False)
        
        # STEP 10: Find Anagrafiche
        print("\n🔍 STEP 10: Inspecting menu...")
        result = await tools.inspect_interactive_elements()
        
        print(f"📋 Found {len(result.get('clickable_elements', []))} clickable elements:")
        for elem in result.get("clickable_elements", [])[:15]:  # Mostra primi 15
            print(f"  - {elem.get('accessible_name', 'N/A')} ({elem.get('role', 'N/A')})")
        
        anag_button = None
        for elem in result.get("clickable_elements", []):
            if "anagrafiche" in elem.get("accessible_name", "").lower():
                anag_button = elem
                print(f"\n  ✓ Found: {elem.get('accessible_name')}")
                break
        
        if not anag_button:
            print("\n  ❌ Anagrafiche NOT in list - menu probably not opened")
            await tools.capture_screenshot(filename="debug_no_anagrafiche.png", return_base64=False)
            raise Exception("Anagrafiche not found")
        
        anag_loc = anag_button['playwright_suggestions'][0]['click_smart']
        
        print("\n🖱️ STEP 11: Clicking Anagrafiche...")
        result = await tools.click_smart([anag_loc])
        print(f"   {result['status']}")
        await tools.page.wait_for_timeout(2000)  # SPA - aspetta rendering submenu
        
        # STEP 12: Find Causali
        print("\n🔍 STEP 12: Inspecting submenu...")
        result = await tools.inspect_interactive_elements()
        
        causali_button = None
        for elem in result.get("clickable_elements", []):
            if "causali" in elem.get("accessible_name", "").lower():
                causali_button = elem
                print(f"  ✓ Found: {elem.get('accessible_name')}")
                break
        
        if not causali_button:
            raise Exception("Causali not found")
        
        causali_loc = causali_button['playwright_suggestions'][0]['click_smart']
        
        print("\n🖱️ STEP 13: Clicking Causali...")
        result = await tools.click_smart([causali_loc])
        print(f"   {result['status']}")
        await tools.page.wait_for_timeout(3000)
        
        # STEP 14: Search in iframe
        print("\n🔍 STEP 14: Searching in Causali iframe...")
        result = await tools.fill_and_search(
            input_selector='input[type="text"]',
            search_value="carm",
            verify_result_text="CARMAG",
            in_iframe={"url_pattern": "movementreason"}
        )
        print(f"   {result['status']}: {result['message']}")
        
        # STEP 15: Screenshot
        print("\n📸 STEP 15: Taking screenshot...")
        result = await tools.capture_screenshot(filename="causali_results.png", return_base64=False)
        print(f"   {result['status']}: {result.get('filename', 'N/A')}")
        
        # STEP 16: Close
        print("\n🔒 STEP 16: Closing browser...")
        result = await tools.close_browser()
        print(f"   {result['status']}")
        
        print("\n" + "="*80)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("="*80)
        
    except Exception as e:
        print("\n" + "="*80)
        print(f"❌ TEST FAILED: {e}")
        print("="*80)
        import traceback
        traceback.print_exc()
        
        # Cleanup
        try:
            await tools.close_browser()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
