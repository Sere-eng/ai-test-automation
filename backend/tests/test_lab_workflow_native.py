"""
Test nativo del workflow LAB - chiamate dirette ai tool senza MCP/HTTP
Verifica che i PlaywrightTools funzionino sul flusso Laboratory / dashboard.
"""
import asyncio
import sys
import os

# Aggiungi backend al path (parent directory di tests/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools import PlaywrightTools
from config.settings import AppConfig


async def main():
    """Esegue il workflow LAB descritto nel test in linguaggio naturale."""

    print("\n" + "=" * 80)
    print("TEST WORKFLOW LAB - NATIVE CALLS (NO MCP, NO LLM)")
    print("=" * 80)

    tools = PlaywrightTools()

    try:
        # STEP 1: Start browser
        print("\n🌐 STEP 1: Starting browser...")
        result = await tools.start_browser(headless=AppConfig.PLAYWRIGHT.HEADLESS)
        print(f"   {result['status']}: {result['message']}")

        # STEP 2: Navigate to LAB URL
        print("\n🌐 STEP 2: Navigating to LAB login...")
        result = await tools.navigate_to_url(AppConfig.LAB.URL)
        print(f"   {result['status']}: {result.get('url', 'N/A')}")

        # Attendi che il DOM sia pronto (senza usare selettori hard-coded)
        try:
            await tools.page.wait_for_load_state("domcontentloaded", timeout=30000)
            print("   ✓ load_state=domcontentloaded reached")
        except Exception as e:
            print(f"   ⚠️ wait_for_load_state(domcontentloaded) timeout/non-fatal: {e}")
        await tools.page.wait_for_timeout(1000)  # piccola stabilizzazione

        # STEP 3: Wait for login fields/buttons using semantic wait_for_* tools
        print("\n🔍 STEP 3: Waiting for login form elements...")
        user_wait = await tools.wait_for_field_by_name("Username", timeout=15000)
        pass_wait = await tools.wait_for_field_by_name("Password", timeout=15000)
        button_wait = await tools.wait_for_clickable_by_name("Login", timeout=15000)

        if not (
            user_wait.get("status") == "success"
            and pass_wait.get("status") == "success"
            and button_wait.get("status") == "success"
        ):
            raise Exception(
                f"Missing login elements on LAB login page: "
                f"user={user_wait.get('status')}, pass={pass_wait.get('status')}, button={button_wait.get('status')}"
            )

        username_field = user_wait.get("element")
        password_field = pass_wait.get("element")
        login_button = button_wait.get("element")

        user_locators = user_wait.get("targets") or [
            s["fill_smart"] for s in (username_field.get("playwright_suggestions") or [])
            if "fill_smart" in s
        ]
        pass_locators = pass_wait.get("targets") or [
            s["fill_smart"] for s in (password_field.get("playwright_suggestions") or [])
            if "fill_smart" in s
        ]
        login_locators = button_wait.get("targets") or [
            s["click_smart"] for s in (login_button.get("playwright_suggestions") or [])
            if "click_smart" in s
        ]

        print("\n🔑 Credentials from .env (LAB):")
        print(f"  Username: {AppConfig.LAB.USERNAME}")
        print(f"  Password: {'*' * len(AppConfig.LAB.PASSWORD)}")

        # STEP 4: Fill username
        print("\n✏️ STEP 4: Filling LAB username...")
        result = await tools.fill_smart(user_locators, AppConfig.LAB.USERNAME)
        print(f"   {result['status']}: strategy={result.get('strategy', 'N/A')}")
        await tools.page.wait_for_timeout(500)

        # STEP 5: Fill password
        print("\n✏️ STEP 5: Filling LAB password...")
        result = await tools.fill_smart(pass_locators, AppConfig.LAB.PASSWORD)
        print(f"   {result['status']}: strategy={result.get('strategy', 'N/A')}")
        await tools.page.wait_for_timeout(500)

        # STEP 6: Click login button
        print("\n🖱️ STEP 6: Submitting LAB login (click button)...")
        result = await tools.click_smart(login_locators)
        print(f"   {result['status']}: {result.get('message', 'N/A')}")

        # STEP 7: Wait for navigation to organization selection
        print("\n⏳ STEP 7: Waiting for post-login navigation...")
        try:
            await tools.page.wait_for_load_state("domcontentloaded", timeout=15000)
            print("   ✓ Navigation completed")
        except Exception as e:
            print(f"   ⚠️ Navigation timeout: {e}")

        # STEP 8: Handle 'Seleziona Organizzazione' page con i nuovi wait_for_* tools
        print("\n🔍 STEP 8: Waiting for 'Seleziona Organizzazione' combobox...")
        org_wait = await tools.wait_for_control_by_name_and_type(
            "Seleziona Organizzazione",
            control_type="combobox",
            timeout=20000,
        )

        if org_wait.get("status") != "success":
            raise Exception(f"Organization combobox not found: {org_wait.get('message')}")

        org_control = org_wait.get("element") or {}
        org_targets = org_wait.get("targets") or []

        print(
            "   ✓ Found organization combobox: "
            f"name='{org_control.get('accessible_name')}', type='{org_control.get('type')}'"
        )

        # 8.b Apri il dropdown usando solo strategie derivate dall'ispezione
        if org_targets:
            print("\n🖱️ STEP 9: Opening 'Seleziona Organizzazione' dropdown...")
            result = await tools.click_smart(org_targets, timeout_per_try=3000)
            print(f"   {result['status']}: {result.get('strategy', 'N/A')}")
            await tools.page.wait_for_timeout(1000)
        else:
            print("   ⚠️ No click strategies found for organization combobox (from wait_for_control_by_name_and_type).")

        # 8.c Re‑inspect per trovare le opzioni del dropdown e selezionare l'organizzazione
        print("\n🔍 STEP 10: Inspecting dropdown options for organization...")
        result = await tools.inspect_interactive_elements()
        clickable = result.get("clickable_elements", []) or []

        # Prendi tutte le opzioni del menu (role=option o elementi della tendina)
        option_elements = [
            e
            for e in clickable
            if (e.get("role") in ("option", "menuitem", "listitem"))
        ]
        print(f"   Found {len(option_elements)} option-like clickable elements")
        for idx, e in enumerate(option_elements):
            print(f"      option[{idx}]: name='{e.get('accessible_name')}', tag={e.get('tag')}, data_tfa={e.get('data_tfa')}")

        org_option = None

        # Preferisci l'opzione che contiene "organizzazione di sistema" nel nome accessibile
        for e in option_elements:
            name = (e.get("accessible_name") or "").lower()
            if "organizzazione" in name and "sistema" in name:
                org_option = e
                print(f"   ✓ Choosing organization by name: {e.get('accessible_name')}")
                break

        # Fallback: se non troviamo la label attesa, usa comunque la prima opzione
        if not org_option and option_elements:
            org_option = option_elements[0]
            print(f"   ✓ Choosing first option as organization (fallback): {org_option.get('accessible_name')}")

        if org_option:
            opt_targets = []
            suggestions = org_option.get("playwright_suggestions") or []
            for s in suggestions:
                if "click_smart" in s:
                    opt_targets.append(s["click_smart"])
            # Fallback semantico se non abbiamo suggerimenti dal tool
            opt_name = org_option.get("accessible_name") or ""
            if opt_name:
                opt_targets.insert(0, {"by": "role", "role": "option", "name": opt_name})
                opt_targets.append({"by": "text", "text": opt_name})

            print("\n🖱️ STEP 11: Selecting organization option...")
            result = await tools.click_smart(opt_targets, timeout_per_try=3000)
            print(f"   {result['status']}: {result.get('strategy', 'N/A')}")
            await tools.page.wait_for_timeout(1000)
        else:
            print("   ⚠️ 'organizzazione di sistema' option not found - leaving default selection.")

        # 8.d Re‑inspect e clicca 'Continua' SOLO dopo aver selezionato l'organizzazione
        print("\n🔍 STEP 12: Looking for enabled 'Continua' button...")
        result = await tools.inspect_interactive_elements()
        clickable = result.get("clickable_elements", []) or []

        continua_button = None
        for elem in clickable:
            name = (elem.get("accessible_name") or "").lower()
            if "continua" in name:
                continua_button = elem
                print(f"   ✓ Found 'Continua' button: {elem.get('accessible_name')}")
                break

        if continua_button:
            continua_locators = [
                s["click_smart"] for s in (continua_button.get("playwright_suggestions") or [])
                if "click_smart" in s
            ]
            if not continua_locators:
                continua_locators = [
                    {"by": "role", "role": "button", "name": continua_button.get("accessible_name", "Continua")}
                ]
            print("\n🖱️ STEP 13: Clicking 'Continua'...")
            result = await tools.click_smart(continua_locators, timeout_per_try=5000)
            print(f"   {result['status']}: {result.get('strategy', 'N/A')}")
        else:
            print("   ⚠️ 'Continua' button not found or still disabled - cannot proceed.")

        # STEP 10 (logico): Wait for main shell after 'Continua' (home con tile Clinical Laboratory)
        print("\n⏳ STEP 14: Waiting for home shell after 'Continua' (domcontentloaded)...")
        try:
            await tools.page.wait_for_load_state("domcontentloaded", timeout=20000)
            print("   ✓ load_state=domcontentloaded reached after 'Continua'")
        except Exception as e:
            print(f"   ⚠️ wait_for_load_state(domcontentloaded) after 'Continua' timeout/non-fatal: {e}")
        await tools.page.wait_for_timeout(1000)
        page_info = await tools.get_page_info()
        print(f"   Current URL: {page_info.get('url', 'N/A')}")

        # STEP 15: Clicca la card "Clinical Laboratory" / "Laboratorio Analisi" sulla home
        print("\n🔍 STEP 15: Waiting for 'Clinical Laboratory' / 'Laboratorio Analisi' tile on home page...")
        # Prova prima in inglese, poi in italiano
        clinical_tile_wait = await tools.wait_for_clickable_by_name("Clinical Laboratory", timeout=12000)
        if clinical_tile_wait.get("status") != "success":
            print("   ⚠️ English label not found, trying 'Laboratorio Analisi'...")
            clinical_tile_wait = await tools.wait_for_clickable_by_name("Laboratorio Analisi", timeout=8000)

        if clinical_tile_wait.get("status") != "success":
            # Fallback di debug: ispeziona manualmente i clickables per capire cosa vede davvero la pagina
            print("   ⚠️ Semantic wait failed, running inspect_interactive_elements() fallback for 'Clinical Laboratory'...")
            insp = await tools.inspect_interactive_elements()
            if insp.get("status") == "success":
                clickables = insp.get("clickable_elements") or []
                candidates = []
                for e in clickables:
                    raw_name = (e.get("accessible_name") or e.get("text") or "").strip()
                    if not raw_name:
                        continue
                    lower = raw_name.lower()
                    if "clinical laboratory" in lower or "laboratorio analisi" in lower:
                        candidates.append(e)

                print(
                    "   → inspect_interactive_elements found "
                    f"{len(candidates)} clickable(s) containing 'Clinical Laboratory' or 'Laboratorio Analisi'"
                )
                if candidates:
                    # scegli il candidato col nome più corto (più probabile sia la tile)
                    clinical_elem = min(
                        candidates,
                        key=lambda el: len((el.get('accessible_name') or el.get('text') or ""))
                    )
                    print(
                        "   ✓ Fallback chose 'Clinical Laboratory' element: "
                        f"name='{clinical_elem.get('accessible_name')}', text='{clinical_elem.get('text')}'"
                    )
                    suggestions = clinical_elem.get("playwright_suggestions") or []
                    clinical_targets = [
                        s["click_smart"]
                        for s in suggestions
                        if isinstance(s, dict) and "click_smart" in s
                    ]
                    # Fallback ulteriore: role+name
                    if not clinical_targets and clinical_elem.get("role") and clinical_elem.get("accessible_name"):
                        clinical_targets = [{
                            "by": "role",
                            "role": clinical_elem["role"],
                            "name": clinical_elem["accessible_name"],
                        }]

                    if clinical_targets:
                        print("\n🖱️ STEP 16: Clicking 'Clinical Laboratory' (fallback path)...")
                        result = await tools.click_smart(clinical_targets, timeout_per_try=5000)
                        print(f"   {result['status']}: {result.get('strategy', 'N/A')}")
                        await tools.page.wait_for_timeout(2000)
                    else:
                        print("   ⚠️ Fallback: no click_smart targets built for 'Clinical Laboratory'.")
                else:
                    print("   ⚠️ Fallback: no clickable elements containing 'Clinical Laboratory' were found.")
            else:
                print(f"   ⚠️ inspect_interactive_elements() failed in fallback: {insp.get('message')}")
        else:
            clinical_elem = clinical_tile_wait.get("element") or {}
            clinical_targets = clinical_tile_wait.get("targets") or []

            print(
                "   ✓ Found 'Clinical Laboratory' tile/menu: "
                f"name='{clinical_elem.get('accessible_name')}', text='{clinical_elem.get('text')}'"
            )

            if clinical_targets:
                print("\n🖱️ STEP 16: Clicking 'Clinical Laboratory'...")
                result = await tools.click_smart(clinical_targets, timeout_per_try=5000)
                print(f"   {result['status']}: {result.get('strategy', 'N/A')}")
                await tools.page.wait_for_timeout(2000)
            else:
                print("   ⚠️ No click_smart targets returned for 'Clinical Laboratory' - cannot click.")

        # STEP 17: Dopo il click su Clinical Laboratory, attendi la shell dell'Analytic Manager
        print("\n⏳ STEP 17: Waiting for Analytic Manager shell after 'Clinical Laboratory' (domcontentloaded)...")
        try:
            await tools.page.wait_for_load_state("domcontentloaded", timeout=20000)
            print("   ✓ load_state=domcontentloaded reached after 'Clinical Laboratory'")
        except Exception as e:
            print(f"   ⚠️ wait_for_load_state(domcontentloaded) after 'Clinical Laboratory' timeout/non-fatal: {e}")
        await tools.page.wait_for_timeout(1000)
        page_info = await tools.get_page_info()
        print(f"   Current URL after Clinical Laboratory: {page_info.get('url', 'N/A')}")

        # STEP 18: Dal menu laterale, apri il modulo 'Laboratory' / 'Laboratorio'
        # Nota: per essere LLM-friendly ci sincronizziamo SEMPRE sull'elemento
        # che ci serve (voce di menu), non solo sullo stato di load.
        print("\n🔍 STEP 18: Waiting for side-menu 'Laboratory' / 'Laboratorio' entry...")
        lab_menu_wait = await tools.wait_for_clickable_by_name("Laboratory", timeout=20000)
        if lab_menu_wait.get("status") != "success":
            print("   ⚠️ English label not found, trying 'Laboratorio'...")
            lab_menu_wait = await tools.wait_for_clickable_by_name("Laboratorio", timeout=15000)

        if lab_menu_wait.get("status") != "success":
            # Fallback: stessa logica usata per la tile "Clinical Laboratory"
            print("   ⚠️ Semantic wait failed, running inspect_interactive_elements() fallback for side-menu 'Laboratory'...")
            insp = await tools.inspect_interactive_elements()
            if insp.get("status") == "success":
                clickables = insp.get("clickable_elements") or []
                candidates = []
                for e in clickables:
                    raw_name = (e.get("accessible_name") or e.get("text") or "").strip()
                    if not raw_name:
                        continue
                    lower = raw_name.lower()
                    if "laboratory" in lower or "laboratorio" in lower:
                        candidates.append(e)

                print(
                    "   → inspect_interactive_elements found "
                    f"{len(candidates)} clickable(s) containing 'Laboratory' or 'Laboratorio'"
                )
                if candidates:
                    lab_menu_elem = min(
                        candidates,
                        key=lambda el: len((el.get('accessible_name') or el.get('text') or ""))
                    )
                    print(
                        "   ✓ Fallback chose side-menu 'Laboratory' element: "
                        f"name='{lab_menu_elem.get('accessible_name')}', text='{lab_menu_elem.get('text')}'"
                    )
                    suggestions = lab_menu_elem.get("playwright_suggestions") or []
                    lab_menu_targets = [
                        s["click_smart"]
                        for s in suggestions
                        if isinstance(s, dict) and "click_smart" in s
                    ]
                    if not lab_menu_targets and lab_menu_elem.get("role") and lab_menu_elem.get("accessible_name"):
                        lab_menu_targets = [{
                            "by": "role",
                            "role": lab_menu_elem["role"],
                            "name": lab_menu_elem["accessible_name"],
                        }]
                else:
                    lab_menu_elem = {}
                    lab_menu_targets = []
            else:
                print(f"   ⚠️ inspect_interactive_elements() failed in fallback: {insp.get('message')}")
                lab_menu_elem = {}
                lab_menu_targets = []
        else:
            lab_menu_elem = lab_menu_wait.get("element") or {}
            lab_menu_targets = lab_menu_wait.get("targets") or []

        if lab_menu_elem:
            print(
                "   ✓ Found side-menu 'Laboratory': "
                f"name='{lab_menu_elem.get('accessible_name')}', text='{lab_menu_elem.get('text')}'"
            )

            if lab_menu_targets:
                print("\n🖱️ STEP 19: Clicking side-menu 'Laboratory'...")
                result = await tools.click_smart(lab_menu_targets, timeout_per_try=5000)
                print(f"   {result['status']}: {result.get('strategy', 'N/A')}")
                await tools.page.wait_for_timeout(1500)
            else:
                print("   ⚠️ No click_smart targets returned for side-menu 'Laboratory' - cannot click.")
        else:
            print("   ⚠️ Side-menu 'Laboratory' / 'Laboratorio' not found; cannot proceed to Laboratory dashboard.")

        # STEP 20: Assicurati che la tab 'Filters' / 'Filtri' sia attiva (dashboard Laboratory)
        print("\n🔍 STEP 20: Waiting for 'Filters' / 'Filtri' tab on Laboratory dashboard...")
        filters_wait = await tools.wait_for_clickable_by_name("Filters", timeout=10000)
        if filters_wait.get("status") != "success":
            print("   ⚠️ English tab label not found, trying 'Filtri'...")
            filters_wait = await tools.wait_for_clickable_by_name("Filtri", timeout=8000)

        if filters_wait.get("status") == "success":
            filters_elem = filters_wait.get("element") or {}
            filters_targets = filters_wait.get("targets") or []

            print(
                "   ✓ Found 'Filters' tab: "
                f"name='{filters_elem.get('accessible_name')}', text='{filters_elem.get('text')}'"
            )

            if filters_targets:
                print("\n🖱️ STEP 21: Clicking 'Filters' tab (if needed)...")
                result = await tools.click_smart(filters_targets, timeout_per_try=5000)
                print(f"   {result['status']}: {result.get('strategy', 'N/A')}")
                await tools.page.wait_for_timeout(1000)
            else:
                print("   ⚠️ No click_smart targets returned for 'Filters' tab - cannot click.")
        else:
            print(f"   ⚠️ {filters_wait.get('message')}")

        # STEP 22: Click 'Edit' / 'Modifica' per entrare in modalità modifica dei filtri
        print("\n🔍 STEP 22: Waiting for 'Edit' / 'Modifica' button on Filters tab...")
        edit_wait = await tools.wait_for_clickable_by_name("Edit", timeout=10000)
        if edit_wait.get("status") != "success":
            print("   ⚠️ English label not found, trying 'Modifica'...")
            edit_wait = await tools.wait_for_clickable_by_name("Modifica", timeout=8000)

        if edit_wait.get("status") == "success":
            edit_elem = edit_wait.get("element") or {}
            edit_targets = edit_wait.get("targets") or []

            print(
                "   ✓ Found edit button: "
                f"name='{edit_elem.get('accessible_name')}', text='{edit_elem.get('text')}'"
            )

            if edit_targets:
                print("\n🖱️ STEP 23: Clicking 'Edit'...")
                result = await tools.click_smart(edit_targets, timeout_per_try=5000)
                print(f"   {result['status']}: {result.get('strategy', 'N/A')}")
                await tools.page.wait_for_timeout(1500)
            else:
                print("   ⚠️ No click_smart targets returned for 'Edit' - cannot click.")
        else:
            print(f"   ⚠️ {edit_wait.get('message')}")

        # =====================================================================
        # STEP 24-28: Crea un nuovo gruppo e un nuovo filtro (best-effort)
        # =====================================================================
        # Nota: questi passi usano solo gli stessi tool semantici:
        #  - wait_for_clickable_by_name
        #  - wait_for_field_by_name
        #  - click_smart / fill_smart
        # in modo da restare allineati con ciò che potrà fare l'LLM.

        GROUP_TITLE = "AI_TEST_GROUP_001"
        FILTER_TITLE = "AI_TEST_FILTER_001"

        # STEP 24: Prova ad aprire la creazione di un nuovo gruppo (card "+ AGGIUNGI GRUPPO")
        print("\n🔍 STEP 24: Looking for group creation (New group / Aggiungi gruppo / AGGIUNGI GRUPPO)...")
        group_button_wait = None
        # Prova prima label italiana come in UI, poi inglese
        for label in ["AGGIUNGI GRUPPO", "Aggiungi gruppo", "New group", "New object", "Nuovo gruppo", "Nuovo oggetto"]:
            group_button_wait = await tools.wait_for_clickable_by_name(label, timeout=8000)
            if group_button_wait.get("status") == "success":
                print(f"   ✓ Found group creation with label containing '{label}'")
                break

        if group_button_wait and group_button_wait.get("status") == "success":
            group_elem = group_button_wait.get("element") or {}
            group_targets = group_button_wait.get("targets") or []

            print(
                "   → Group creation element: "
                f"name='{group_elem.get('accessible_name')}', text='{group_elem.get('text')}'"
            )

            # Card "Aggiungi Gruppo" è un div.ds-add-button-container: i locator da testo
            # spesso falliscono (testo "add\nAGGIUNGI GRUPPO"). Usiamo prima il CSS così
            # il click è rapido e non resta appeso su più strategie.
            raw_name = (group_elem.get("accessible_name") or "").lower()
            raw_text = (group_elem.get("text") or "").lower()
            if "aggiungi gruppo" in raw_name or "aggiungi gruppo" in raw_text:
                custom_targets = [
                    {"by": "css", "selector": "div.ds-add-button-container"},
                    {"by": "text", "text": "AGGIUNGI GRUPPO"},
                    {"by": "text", "text": "Aggiungi Gruppo"},
                ]
                group_targets = custom_targets + group_targets

            if group_targets:
                print("\n🖱️ STEP 25: Clicking group creation (AGGIUNGI GRUPPO)...")
                result = await tools.click_smart(group_targets, timeout_per_try=3000)
                print(f"   {result['status']}: {result.get('strategy', 'N/A')}")
                await tools.page.wait_for_timeout(1000)
            else:
                print("   ⚠️ No click_smart targets for group creation - cannot click.")
        else:
            # Fallback: ispeziona i clickable e cerca elemento che contenga "gruppo"/"group"
            print("   ⚠️ Semantic wait failed, trying inspect fallback for group creation...")
            insp = await tools.inspect_interactive_elements()
            if insp.get("status") == "success":
                clickables = insp.get("clickable_elements") or []
                candidates = []
                for e in clickables:
                    raw = (e.get("accessible_name") or e.get("text") or "").strip()
                    lower = raw.lower()
                    if ("gruppo" in lower or "group" in lower) and ("aggiungi" in lower or "new" in lower or "nuovo" in lower or "add" in lower):
                        candidates.append(e)
                if candidates:
                    group_elem = min(candidates, key=lambda el: len((el.get("accessible_name") or el.get("text") or "")))
                    print(f"   ✓ Fallback found group creation: name='{group_elem.get('accessible_name')}', text='{group_elem.get('text')}'")
                    suggestions = group_elem.get("playwright_suggestions") or []
                    group_targets = [s["click_smart"] for s in suggestions if isinstance(s, dict) and "click_smart" in s]
                    if not group_targets and group_elem.get("role") and group_elem.get("accessible_name"):
                        group_targets = [{"by": "role", "role": group_elem["role"], "name": group_elem["accessible_name"]}]
                    if group_targets:
                        print("\n🖱️ STEP 25: Clicking group creation (fallback)...")
                        result = await tools.click_smart(group_targets, timeout_per_try=5000)
                        print(f"   {result['status']}: {result.get('strategy', 'N/A')}")
                        await tools.page.wait_for_timeout(1000)
                    else:
                        print("   ⚠️ Fallback: no click_smart targets for group creation.")
                else:
                    print("   ⚠️ No clickable with 'gruppo'/'group' + 'aggiungi'/'new' found; skipping group creation.")
            else:
                print("   ⚠️ No 'AGGIUNGI GRUPPO' / 'New group' / 'Aggiungi gruppo' found; skipping group creation.")

        # STEP 26: Compila il titolo del gruppo (se esiste un campo coerente)
        print("\n🔍 STEP 26: Looking for group title field...")
        group_title_wait = None
        for label in ["Group title", "Titolo gruppo", "Title", "Nome gruppo"]:
            group_title_wait = await tools.wait_for_field_by_name(label, timeout=8000)
            if group_title_wait.get("status") == "success":
                print(f"   ✓ Found group title field with label containing '{label}'")
                break

        if group_title_wait and group_title_wait.get("status") == "success":
            group_title_targets = group_title_wait.get("targets") or []
            if group_title_targets:
                print(f"\n✏️ STEP 27: Filling group title with '{GROUP_TITLE}'...")
                result = await tools.fill_smart(group_title_targets, GROUP_TITLE)
                print(f"   {result['status']}: strategy={result.get('strategy', 'N/A')}")
                await tools.page.wait_for_timeout(500)
            else:
                print("   ⚠️ Group title field found but no fill_smart targets available.")
        else:
            # Fallback: il campo titolo gruppo è un input di testo senza label esplicita
            # dentro l'ultimo card-group. Proviamo a riempirlo via CSS.
            print("   ⚠️ No explicit group title field found; trying CSS fallback on last group card...")
            try:
                title_input = tools.page.locator("card-group ds-text-field input[type='text']").last
                await title_input.fill(GROUP_TITLE)
                print("   ✓ Filled group title via CSS fallback on last group card.")
                await tools.page.wait_for_timeout(500)
            except Exception as e:
                print(f"   ⚠️ CSS fallback for group title failed: {e}")

        # STEP 27: Crea un nuovo filtro (se presente un bottone dedicato)
        print("\n🔍 STEP 27: Looking for 'New filter' / 'Aggiungi filtro' button...")
        filter_button_wait = None
        for label in ["New filter", "Nuovo filtro", "Add filter", "Aggiungi filtro", "AGGIUNGI FILTRO"]:
            filter_button_wait = await tools.wait_for_clickable_by_name(label, timeout=8000)
            if filter_button_wait.get("status") == "success":
                print(f"   ✓ Found filter creation button with label containing '{label}'")
                break

        if filter_button_wait and filter_button_wait.get("status") == "success":
            filter_elem = filter_button_wait.get("element") or {}
            filter_targets = filter_button_wait.get("targets") or []

            print(
                "   → Filter button details: "
                f"name='{filter_elem.get('accessible_name')}', text='{filter_elem.get('text')}'"
            )

            # Il bottone "Aggiungi filtro" è reso come ds-button/add-option-column con testo
            # "add\nAGGIUNGI FILTRO". Miglioriamo i target mettendo prima:
            #  - un CSS specifico per i bottoni add-option-column
            #  - locator testuali puliti su "AGGIUNGI FILTRO"/"Aggiungi filtro"
            raw_name = (filter_elem.get("accessible_name") or "").lower()
            raw_text = (filter_elem.get("text") or "").lower()
            if "aggiungi filtro" in raw_name or "aggiungi filtro" in raw_text:
                custom_targets = [
                    {"by": "css", "selector": "card-group ds-button.add-option-column button"},
                    {"by": "text", "text": "AGGIUNGI FILTRO"},
                    {"by": "text", "text": "Aggiungi filtro"},
                ]
                filter_targets = custom_targets + filter_targets

            if filter_targets:
                print("\n🖱️ STEP 28: Clicking filter creation button...")
                result = await tools.click_smart(filter_targets, timeout_per_try=3000)
                print(f"   {result['status']}: {result.get('strategy', 'N/A')}")
                await tools.page.wait_for_timeout(1000)
            else:
                print("   ⚠️ No click_smart targets returned for filter creation button - cannot click.")
        else:
            print("   ⚠️ No 'New filter' button found; skipping explicit filter creation button step.")

        # STEP 28: Compila il titolo del filtro (obbligatorio)
        print("\n🔍 STEP 28: Looking for filter title field...")
        filter_title_wait = None
        for label in ["Filter title", "Titolo filtro", "Nome filtro", "Filter name"]:
            filter_title_wait = await tools.wait_for_field_by_name(label, timeout=8000)
            if filter_title_wait.get("status") == "success":
                print(f"   ✓ Found filter title field with label containing '{label}'")
                break

        if filter_title_wait and filter_title_wait.get("status") == "success":
            filter_title_targets = filter_title_wait.get("targets") or []
            if filter_title_targets:
                print(f"\n✏️ STEP 29: Filling filter title with '{FILTER_TITLE}'...")
                result = await tools.fill_smart(filter_title_targets, FILTER_TITLE)
                print(f"   {result['status']}: strategy={result.get('strategy', 'N/A')}")
                await tools.page.wait_for_timeout(500)
            else:
                print("   ⚠️ Filter title field found but no fill_smart targets available.")
        else:
            print("   ⚠️ No explicit filter title field found; continuing to save step.")

        # STEP 29: Prova a salvare il filtro/gruppo (SAVE / SAVE SEARCH FILTER / Salva / Conferma)
        print("\n🔍 STEP 29: Looking for save button for filter/group...")
        save_button_wait = None
        for label in ["SAVE SEARCH FILTER", "Save", "Salva", "Conferma", "Confirm"]:
            save_button_wait = await tools.wait_for_clickable_by_name(label, timeout=8000)
            if save_button_wait.get("status") == "success":
                print(f"   ✓ Found save button with label containing '{label}'")
                break

        if save_button_wait and save_button_wait.get("status") == "success":
            save_elem = save_button_wait.get("element") or {}
            save_targets = save_button_wait.get("targets") or []

            print(
                "   → Save button details: "
                f"name='{save_elem.get('accessible_name')}', text='{save_elem.get('text')}'"
            )

            if save_targets:
                print("\n🖱️ STEP 30: Clicking save button for filter/group...")
                result = await tools.click_smart(save_targets, timeout_per_try=5000)
                print(f"   {result['status']}: {result.get('strategy', 'N/A')}")
                await tools.page.wait_for_timeout(1500)
            else:
                print("   ⚠️ No click_smart targets returned for save button - cannot click.")
        else:
            print("   ⚠️ No save button found for filter/group; ending after edit-only path.")

        # STEP 31: Screenshot finale
        print("\n📸 STEP 31: Taking final screenshot (LAB Laboratory dashboard after group/filter flow)...")
        result = await tools.capture_screenshot(filename="lab_laboratory_dashboard.png", return_base64=False)
        print(f"   {result['status']}: {result.get('filename', 'N/A')}")

        # STEP 32: Close browser
        print("\n🔒 STEP 32: Closing browser...")
        result = await tools.close_browser()
        print(f"   {result['status']}")

        print("\n" + "=" * 80)
        print("✅ LAB TEST COMPLETED (up to Edit action)!")
        print("=" * 80)

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ LAB TEST FAILED: {e}")
        print("=" * 80)
        import traceback

        traceback.print_exc()

        # Cleanup
        try:
            await tools.close_browser()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())

