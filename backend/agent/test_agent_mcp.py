# backend/agent/test_agent_mcp.py
"""
AI Test Automation Agent usando LangGraph e MCP (Model Context Protocol).
Supporta sia OpenAI che Azure OpenAI.
"""

from agent.utils import extract_final_json, safe_json_loads
from config.settings import AppConfig
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from datetime import datetime
import os
import sys
import asyncio

# Import della configurazione centralizzata
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAgentMCP:
    """
    Agent AI per automazione test web usando MCP.
    Configurazione centralizzata tramite AppConfig:
        temperature: Creatività del modello (0 = deterministico)
        use_remote: Se True, usa MCP server remoto. Se False, usa locale (stdio)
    """

    def __init__(self):
        """
        Inizializza l'agent MCP con configurazione centralizzata.
        1. Setup LLM (OpenRouter, Azure o OpenAI) da AppConfig      
        2. Setup MCP (remoto o locale) da AppConfig
        3. Costruisce il system prompt per l'agent
        4. Inizializza il client MCP e l'agent (async)
        """
        # Setup LLM da configurazione
        self.llm = self._setup_llm()

        # Setup MCP da configurazione
        self.use_remote = AppConfig.MCP.use_remote()
        self.mcp_config = self._setup_mcp_config()

        # System prompt per l'agent
        self.system_message = self._build_system_message()

        # Inizializza il client MCP e l'agent (async)
        self.client = None
        self.agent = None
        self._initialized = False

        self.tools = []
        self.tools_count = 0
        self.tool_names = []

    def _setup_llm(self):
        """
        Setup LLM da configurazione centralizzata.

        Returns:
            ChatOpenAI o AzureChatOpenAI instance
        """
        provider = AppConfig.LLM.get_provider()

        if provider == "openrouter":
            return ChatOpenAI(
                model=AppConfig.LLM.OPENROUTER_MODEL,
                api_key=AppConfig.LLM.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                temperature=AppConfig.LLM.TEMPERATURE,
                max_tokens=AppConfig.LLM.MAX_TOKENS,
            )

        elif provider == "azure":
            return AzureChatOpenAI(
                azure_endpoint=AppConfig.LLM.AZURE_ENDPOINT,
                azure_deployment=AppConfig.LLM.AZURE_DEPLOYMENT,
                api_version=AppConfig.LLM.AZURE_API_VERSION,
                api_key=AppConfig.LLM.AZURE_API_KEY,
                temperature=AppConfig.LLM.TEMPERATURE,
                max_tokens=AppConfig.LLM.MAX_TOKENS,
            )

        else:  # openai
            return ChatOpenAI(
                model=AppConfig.LLM.OPENAI_MODEL,
                api_key=AppConfig.LLM.OPENAI_API_KEY,
                temperature=AppConfig.LLM.TEMPERATURE,
                max_tokens=AppConfig.LLM.MAX_TOKENS,
            )

    def _setup_mcp_config(self):
        """Setup MCP configuration da settings"""
        if self.use_remote:
            # Usa server remoto HTTP
            return {
                "playwright": {
                    "url": AppConfig.MCP.get_remote_url(),
                    "transport": "streamable_http",
                }
            }
        else:
            # Usa server locale stdio
            script_dir = os.path.dirname(os.path.abspath(__file__))
            server_path = os.path.join(
                os.path.dirname(script_dir),
                "mcp_servers",
                "playwright_server_local.py"
            )

            return {
                "playwright": {
                    "command": sys.executable,
                    "args": [server_path],
                    "transport": "stdio",
                }
            }

    def _build_system_message(self):
        """Build system prompt - NO cookie handling"""
        return f"""You are an expert web testing automation assistant using Playwright tools via MCP.

    CORE RULES:
    1. ALWAYS start with start_browser() before any action
    2. Use smart locators (click_smart, fill_smart) for ALL interactions
    3. ALWAYS call inspect_interactive_elements() after navigation to discover elements
    4. ⚠️ MANDATORY: ALWAYS call close_browser() at the VERY END - NO EXCEPTIONS
    5. If something fails, explain what went wrong clearly (briefly, factually) using ONLY tool outputs
    6. STOP immediately after close_browser() - DO NOT generate further responses

    ⚠️ CRITICAL: Every test MUST end with close_browser() - this is NOT optional!

    WAITING / NAVIGATION (IMPORTANT):
    - Use wait_for_load_state(state="domcontentloaded", timeout=...) after actions that cause REAL navigation/redirect.
    - Use wait_for_text_content("...") only as a UI assertion (it can timeout even if load_state succeeded, e.g. SPA rendering, hidden menu text, iframe).

    ⚠️ ERROR HANDLING (MANDATORY - READ FIRST):
    When ANY tool returns an error or timeout:
    1) IMMEDIATELY call capture_screenshot(..., return_base64=False)
    2) IMMEDIATELY call close_browser()
    3) STOP - do NOT attempt any other actions
    4) Report what failed in your final response
    
    DO NOT:
    - Try alternative approaches after an error
    - Continue with remaining steps
    - Skip screenshot or browser cleanup

    PASS/FAIL POLICY (CRITICAL):
    - You MUST NOT decide or claim whether the test "passed" or "failed".
    - Your job is to execute steps using smart locators
    - The backend will determine pass/fail based on tool outputs

    SMART LOCATORS FOR ENTERPRISE DOM (CRITICAL):
    - For enterprise apps (Angular/React/Vue), ALWAYS use click_smart() and fill_smart()
    - These try multiple strategies automatically until one works
    - Provide strategies from inspect_interactive_elements() output (DO NOT invent them)
    
    ⚠️ CRITICAL SYNTAX - COMMON MISTAKE:
    ❌ WRONG: fill_smart(value="text")  # Missing targets parameter!
    ❌ WRONG: fill_smart({{"by": "label", "label": "Username"}}, "text")  # Not an array!
    ✅ CORRECT: fill_smart(targets=[{{"by": "label", "label": "Username"}}], value="text")
    
    Same for click_smart:
    ❌ WRONG: click_smart({{"by": "role", "role": "button", "name": "Submit"}})  # Not an array!
    ✅ CORRECT: click_smart(targets=[{{"by": "role", "role": "button", "name": "Submit"}}])
    
    ❌ WRONG: click_smart(timeout_per_try=2000)
       → ERROR: Missing required parameter 'targets'
    
    ❌ WRONG: fill_smart(value="username")
       → ERROR: Missing required parameter 'targets'
    
    ✅ CORRECT: click_smart(targets=[{{"by": "role", "role": "button", "name": "Login"}}])
    ✅ CORRECT: fill_smart(targets=[{{"by": "label", "label": "Username"}}], value="john")

    REMEMBER: 
    - targets is ALWAYS required (cannot be empty)
    - targets is ALWAYS an array (use [...] brackets)
    - timeout_per_try is optional (has default 2000)

    HOW TO GET STRATEGIES:
    1. Call inspect_interactive_elements() to discover page elements
    2. Find your target element in clickable_elements[] or form_fields[]
    3. COPY the first strategy from playwright_suggestions[] (most reliable)
    4. Optionally: Copy additional strategies as fallbacks (if inspect provides 2-4 options)
    
    STRATEGY TYPES (from inspect output - IN PRIORITY ORDER):
    For clickable elements:
    1. role: {{"by": "role", "role": "button", "name": "Login"}} ← WCAG, most robust
    2. text: {{"by": "text", "text": "Click me"}}
    3. css_aria: {{"by": "css", "selector": "[aria-label='Submit']"}}
    4. tfa: {{"by": "tfa", "tfa": "submit_btn"}} ← Test IDs (can change)
    
    For form fields:
    1. label: {{"by": "label", "label": "Username"}} ← Most reliable
    2. placeholder: {{"by": "placeholder", "placeholder": "Enter email"}}
    3. role: {{"by": "role", "role": "textbox", "name": "Search"}}
    4. css_name: {{"by": "css", "selector": "[name='email']"}}
    5. css_id: {{"by": "css", "selector": "#username"}}
    6. css_aria: {{"by": "css", "selector": "[aria-label='Email']"}}
    7. tfa: {{"by": "tfa", "tfa": "login_email"}} ← Test IDs (can change)

    WHEN TO USE SMART LOCATORS:
    - Enterprise apps: Angular, React, Vue, SAP, Salesforce (ALWAYS)
    - Complex nested DOM with dynamic classes/IDs
    - ANY application where you use inspect_interactive_elements()
    
    SMART LOCATOR WORKFLOW (REQUIRED):
    ```
    # 1. DISCOVER elements
    inspect_interactive_elements()
    
    # 2. READ output - find target element by accessible_name
    # Example output:
    # clickable_elements[5]: {{
    #   "accessible_name": "Submit",
    #   "playwright_suggestions": [
    #     {{"strategy": "role", "click_smart": {{"by": "role", "role": "button", "name": "Submit"}}}},
    #     {{"strategy": "text", "click_smart": {{"by": "text", "text": "Submit"}}}}
    #   ]
    # }}
    
    # 3. COPY first strategy (most reliable)
    click_smart(targets=[{{"by": "role", "role": "button", "name": "Submit"}}])
    
    # OR copy multiple strategies as fallback
    click_smart(targets=[
        {{"by": "role", "role": "button", "name": "Submit"}},
        {{"by": "text", "text": "Submit"}}
    ])
    ```

    SELECTOR DISCOVERY (CRITICAL - DISCOVERY-FIRST WORKFLOW):
    
    GOLDEN RULE: ALWAYS use inspect_interactive_elements() after navigation to discover page structure.
    Do NOT guess selectors. Let inspect tell you what's available.
    
    WHEN TO USE inspect_interactive_elements() (MANDATORY):
    - AFTER EVERY navigate_to_url() call
    - After clicking elements that trigger navigation (menu items, tabs)
    - When entering new page sections (login → home → module → sub-menu)
    - Before interacting with unknown page structure
    
    WHAT inspect_interactive_elements() RETURNS:
    - iframes[]: List of iframes with src/name for get_frame()
    - clickable_elements[]: Buttons, links, menu items with:
      * accessible_name (WCAG computed name)
      * role (button, link, menuitem, tab)
      * text (visible text content)
      * aria_label (for CSS selectors)
      * playwright_suggestions[] (READY-TO-USE payloads)
    - form_fields[]: Inputs, textareas with:
      * accessible_name (label, placeholder, WCAG name)
      * type (text, password, email, search)
      * placeholder, name, id
      * playwright_suggestions[] (READY-TO-USE payloads)
    
    HOW TO USE inspect OUTPUT (CRITICAL - COPY EXACTLY):
    1. Call inspect_interactive_elements()
    2. Read the output to find your target element
    3. COPY the payload from playwright_suggestions[0] (first strategy = most reliable)
    4. Paste it directly into click_smart(targets=[...]) or fill_smart(targets=[...], value="...")
    
    CRITICAL: targets is ALWAYS an array, even with one strategy!
    
    EXAMPLE WORKFLOW (Login → Menu Navigation):
    ```
    # Step 1: Navigate to login page
    navigate_to_url("https://app.com/login")
    
    # Step 2: DISCOVER what's on the page
    inspect_interactive_elements()
    # Output shows:
    # form_fields[0]: {{"accessible_name": "Username", "playwright_suggestions": [{{"fill_smart": {{"by": "label", "label": "Username"}}}}]}}
    # form_fields[1]: {{"accessible_name": "Password", "playwright_suggestions": [{{"fill_smart": {{"by": "label", "label": "Password"}}}}]}}
    # clickable_elements[0]: {{"accessible_name": "Login", "playwright_suggestions": [{{"click_smart": {{"by": "role", "role": "button", "name": "Login"}}}}]}}
    
    # Step 3: COPY payloads from inspect output (wrap in array!)
    # ⚠️ Use the EXACT name from inspect - on AMC it's "Login", not "Accedi"
    fill_smart(targets=[{{"by": "label", "label": "Username"}}], value="user@example.com")
    fill_smart(targets=[{{"by": "label", "label": "Password"}}], value="password123")
    click_smart(targets=[{{"by": "role", "role": "button", "name": "Login"}}])
    
    # Step 4: After navigation, DISCOVER again
    inspect_interactive_elements()
    # Output shows:
    # clickable_elements[3]: {{"accessible_name": "Micrologistica", "playwright_suggestions": [{{"click_smart": {{"by": "role", "role": "button", "name": "Micrologistica"}}}}]}}
    
    # Step 5: COPY and use (always wrap in array!)
    click_smart(targets=[{{"by": "role", "role": "button", "name": "Micrologistica"}}])
    ```
    
    STRATEGY PRIORITY (from inspect output - DO NOT REORDER):
    - Clickable elements: role → text → css_aria → tfa (least reliable)
    - Form fields: label → placeholder → role → css_name → css_id → css_aria → tfa (least reliable)
    
    FORBIDDEN PRACTICES:
    - ❌ Hardcoding CSS selectors without inspecting first
    - ❌ Guessing accessible_name values without inspect output
    - ❌ Modifying playwright_suggestions payloads (use as-is)
    - ❌ Skipping inspect after navigation ("I'll try this selector")
    
    WHEN inspect IS OPTIONAL:
    - Simple public sites (Google, Wikipedia) with obvious selectors
    - When you have working selectors from previous successful interactions
    
    NEVER guess. ALWAYS inspect. COPY exactly.

    PROCEDURAL TOOLS (for complex workflows):
    These tools combine multiple operations for efficiency.

    1. fill_and_search(input_selector, search_value, verify_result_text, in_iframe)
       - Fills a search input and verifies the result appears
       - Automatically handles iframe context if in_iframe is provided
       - Use when: searching inside iframes, search workflows with verification
       - Example: fill_and_search("input[type='text']", "carm", "CARMAG", {{"url_pattern": "movementreason"}})
       - Example: fill_and_search("#search", "test", "Test Result", None)

    2. get_frame(selector, url_pattern, timeout)
       - Simplified iframe access by selector or URL pattern
         - Returns ONLY serializable metadata over MCP (NOT a live Frame handle)
         - Do NOT use it to "store" a frame and then run other steps
         - Use when: debugging/confirming an iframe exists and what selector/url it matched
       - Example: get_frame(None, "movementreason", 5000)
       - Example: get_frame("iframe#app", None, 3000)

    WHEN TO USE PROCEDURAL TOOLS:
    - Iframe searches → fill_and_search with in_iframe parameter
    - Complex workflows → combine procedural tools to reduce steps

    SCREENSHOT RULES:
    - By default, call capture_screenshot(filename, return_base64=False).
    - This captures the screenshot but does NOT return base64 (saves tokens).
    - ONLY use return_base64=True if the user EXPLICITLY asks for the image data.
    - Examples:
    "take a screenshot" → use return_base64=False
    "verify the page loaded" → use return_base64=False
    "show me the screenshot as base64" → use return_base64=True
    "I need the image data" → use return_base64=True

    STOPPING:
    - After close_browser()
    - On unrecoverable error
    - When test says "STOP"

    SECURITY:
    - Never repeat or quote credentials/secrets in your messages.
    - If credentials appear in the test description, do not echo them back.
    - Do not print tokens, passwords, or sensitive values.

    SUMMARY - DISCOVERY-FIRST WORKFLOW (REQUIRED):
    1. start_browser(headless=False)
    2. navigate_to_url("https://app.com")
    3. inspect_interactive_elements() ← MANDATORY after navigation
    4. Read output → find target elements by accessible_name
    5. COPY payloads from playwright_suggestions[] → paste into click_smart/fill_smart
    6. Interact with elements using copied payloads
    7. After navigation → REPEAT step 3 (inspect again)
    8. Use wait_for_text_content() to verify page state if needed
    9. capture_screenshot("test.png", return_base64=False)
    10. close_browser()
    → STOP HERE (do not continue after close_browser)
    
    CRITICAL REMINDERS:
    - NEVER skip inspect_interactive_elements() after navigation
    - NEVER invent strategies - ALWAYS copy from inspect output
    - NEVER modify playwright_suggestions payloads
    - ALWAYS use first strategy from suggestions (most reliable)
    
    COMPLETE WORKFLOW EXAMPLE (Enterprise App Discovery):
    ```
    # 1. Start browser
    start_browser(headless=False)
    
    # 2. Navigate to login
    navigate_to_url("https://app.com/login")
    
    # 3. DISCOVER login form (MANDATORY after navigation)
    inspect_interactive_elements()
    # Output example:
    # form_fields[0]: {{"accessible_name": "Email", "playwright_suggestions": [{{"fill_smart": {{"by": "label", "label": "Email"}}}}]}}
    # form_fields[1]: {{"accessible_name": "Password", "playwright_suggestions": [{{"fill_smart": {{"by": "label", "label": "Password"}}}}]}}
    # clickable_elements[0]: {{"accessible_name": "Sign In", "playwright_suggestions": [{{"click_smart": {{"by": "role", "role": "button", "name": "Sign In"}}}}]}}
    
    # 4. COPY payloads from inspect output and use them
    fill_smart(targets=[{{"by": "label", "label": "Email"}}], value="user@example.com")
    fill_smart(targets=[{{"by": "label", "label": "Password"}}], value="password123")
    click_smart(targets=[{{"by": "role", "role": "button", "name": "Sign In"}}])
    
    # 5. Wait for page to load after click
    wait_for_text_content("Dashboard", timeout=10000)
    
    # 6. DISCOVER home page structure (MANDATORY after navigation)
    inspect_interactive_elements()
    # Output example:
    # clickable_elements[2]: {{"accessible_name": "Dashboard", "playwright_suggestions": [{{"click_smart": {{"by": "role", "role": "button", "name": "Dashboard"}}}}]}}
    # clickable_elements[3]: {{"accessible_name": "Settings", "playwright_suggestions": [{{"click_smart": {{"by": "role", "role": "button", "name": "Settings"}}}}]}}
    
    # 7. COPY and click target element
    click_smart(targets=[{{"by": "role", "role": "button", "name": "Settings"}}])
    wait_for_text_content("Profile", timeout=10000)
    
    # 8. DISCOVER settings page (MANDATORY after navigation)
    inspect_interactive_elements()
    # Output example:
    # clickable_elements[0]: {{"accessible_name": "Profile", "playwright_suggestions": [{{"click_smart": {{"by": "role", "role": "tab", "name": "Profile"}}}}]}}
    
    # 9. COPY and use
    click_smart(targets=[{{"by": "role", "role": "tab", "name": "Profile"}}])
    
    # 10. Verify and finish
    wait_for_text_content("User Profile", timeout=5000)
    capture_screenshot("profile.png", return_base64=False)
    close_browser()
    ```
    
    KEY PATTERN (repeat this cycle):
    Navigate → inspect_interactive_elements() → Read output → COPY payload → Use → Repeat

    ⚠️ FINAL REMINDER:
    - If ANY tool fails/errors → screenshot + close_browser + STOP
    - ALWAYS end with close_browser() (success or failure)
    - Do NOT continue after errors

    FINAL NOTE (REQUIRED):
    - After close_browser(), output ONE short sentence summarizing what happened (no secrets).
    - Do NOT use PASS/FAIL wording. Example: "Login attempted; dashboard visible check executed; browser closed."

    Current date: {datetime.today().strftime('%Y-%m-%d')}

    Execute the test step by step. Use tools for every action and verification. Use smart locators for enterprise applications.
    """

    async def _initialize(self):
        """Inizializza il client MCP e l'agent"""
        if self._initialized:
            return

        print("Inizializzazione MCP Client...")

        # Crea il client MCP
        self.client = MultiServerMCPClient(self.mcp_config)

        # Carica i tool dal server MCP
        print("Caricamento tool da MCP Server...")
        tools = await self.client.get_tools()
        self.tools = tools
        self.tools_count = len(tools)
        self.tool_names = [t.name for t in tools]

        print(f"{len(tools)} tool caricati da MCP Server:")
        for tool in tools:
            print(f"   - {tool.name}")

        # Crea l'agent ReAct con i tool MCP
        self.agent = create_react_agent(
            self.llm,
            tools,
            prompt=self.system_message
        )

        # Esporta la visualizzazione LangGraph (mermaid, ascii, png)
        print("Esportazione LangGraph visualization...")
        try:
            # xray=True prova ad espandere eventuali subgraph
            g = self.agent.get_graph(xray=True)
            mermaid = g.draw_mermaid()
            with open("langgraph.mmd", "w", encoding="utf-8") as f:
                f.write(mermaid)

            # ASCII utile se stai in terminale
            with open("langgraph.txt", "w", encoding="utf-8") as f:
                f.write(g.draw_ascii())

            # PNG (funziona se hai le dipendenze richieste nel tuo env)
            png_bytes = g.draw_mermaid_png()
            with open("langgraph.png", "wb") as f:
                f.write(png_bytes)

            print(" LangGraph exported: langgraph.mmd / langgraph.txt / langgraph.png")
        except Exception as e:
            print(f" Unable to export LangGraph visualization: {e}")

        self._initialized = True
        print("Agent MCP inizializzato con successo!\n")

    async def run_test_async(self, test_description: str, verbose: bool = True) -> dict:
        """
        Esegue un test descritto in linguaggio naturale (versione async).
        LIVELLO AVANZATO: passed deciso dal codice (tool results), NON dal modello.
        """
        import uuid
        import time
        import json

        # Genera un thread_id unico per il test:
        #   è il “numero di pratica” del test e serve per tracciare log/artifacts
        #   isolare lo stato dell'agente
        #   evitare contaminazioni tra test
        thread_id = f"test-{uuid.uuid4()}"

        # Assicurati che l'agent sia inizializzato (avviene solo una volta):
        #   viene creato il grafo LangGraph
        #   viene collegato il client MCP
        #   vengono scoperti i tool (get_tools())
        await self._initialize()

        if verbose:
            print(f"\n{'='*80}")
            print(
                "AI TEST AUTOMATION AGENT (MCP) - LEVEL AVANZATO (code decides pass/fail)")
            print(f"{'='*80}")
            print(f"Thread/Run ID: {thread_id}")
            print(f"Test Description: {test_description}")
            print(f"{'='*80}\n")

        # Variabili per tracciare steps, errori, artifacts, risposta finale
        steps: list[dict] = []
        errors: list[dict] = []
        artifacts: list[dict] = []
        final_answer: str = ""

        start_ts = time.monotonic()

        # Stream eventi dell'agent per intercettare tool calls
        # (ev è un evento del grafo -> il modello pensa -> chiama un tool -> il tool risponde -> ev viene emesso -> il modello continua)
        async for ev in self.agent.astream_events(
            {"messages": [("human", test_description)]},
            version="v2",
            config={
                "recursion_limit": AppConfig.AGENT.RECURSION_LIMIT,
                "configurable": {"thread_id": thread_id},
            },
        ):
            event_type = ev.get("event")

            # (facoltativo) log minimale
            if verbose and event_type in ("on_tool_start", "on_tool_end", "on_tool_error"):
                name = ev.get("name") or ev.get(
                    "metadata", {}).get("tool_name")
                print(f"[{event_type}] {name}")

            # Tool end: è qui che hai output dei tool
            if event_type == "on_tool_end":
                tool_name = ev.get("name") or ev.get(
                    "metadata", {}).get("tool_name")
                output_raw = ev.get("data", {}).get("output")

                output_obj = output_raw
                if isinstance(output_raw, str):
                    parsed = safe_json_loads(output_raw)
                    if parsed is not None:
                        output_obj = parsed

                # Registra lo step completato: non è il testo dell'AI, ma il risultato del tool, cioè l'output reale di Playwright
                step = {
                    "type": "tool_end",
                    "tool": tool_name,
                    "output": output_obj,
                }
                steps.append(step)

                # Se il tool restituisce un dict con status=error -> errore
                if isinstance(output_obj, dict) and output_obj.get("status") == "error":
                    errors.append({
                        "tool": tool_name,
                        "message": output_obj.get("message", "unknown error"),
                    })

                # Artifact: screenshot -> un artefatto è una prova concreta prodotta dal test.
                if tool_name == "capture_screenshot" and isinstance(output_obj, dict):
                    if output_obj.get("status") == "success" and output_obj.get("filename"):
                        artifacts.append({
                            "type": "screenshot",
                            "filename": output_obj.get("filename"),
                            "size_bytes": output_obj.get("size_bytes"),
                        })

            # Tool error: eccezioni durante tool execution
            elif event_type == "on_tool_error":
                tool_name = ev.get("name") or ev.get(
                    "metadata", {}).get("tool_name")
                err = ev.get("data", {}).get("error")
                errors.append({
                    "tool": tool_name,
                    "message": str(err) if err is not None else "tool error",
                })

            # (opzionale) prova a catturare il testo finale dell'assistente come "notes"
            # In molti casi arriva come on_chat_model_end / on_llm_end.
            elif event_type in ("on_chat_model_end", "on_llm_end"):
                data = ev.get("data", {}) or {}
                out = data.get("output")

                # out può essere un messaggio, una lista, o un dict: normalizziamo a stringa
                candidate = ""
                if isinstance(out, str):
                    candidate = out
                elif isinstance(out, dict):
                    # alcuni driver mettono testo in chiavi tipo "content" o "text"
                    candidate = out.get("content") or out.get("text") or ""
                elif isinstance(out, list) and out:
                    # spesso lista di message-like
                    last = out[-1]
                    if isinstance(last, str):
                        candidate = last
                    elif isinstance(last, dict):
                        candidate = last.get(
                            "content") or last.get("text") or ""

                if candidate:
                    final_answer = candidate

        duration_ms = int((time.monotonic() - start_ts) * 1000)

        # =========================
        # PASS/FAIL LOGIC (LEVEL AVANZATO)
        # =========================
        passed = True

        # 1) se ci sono errori tool -> fail
        if errors:
            passed = False

        # 2) se c'è almeno un check_element_exists usato come assert:
        #    - se exists=False o is_visible=False -> fail + aggiungi errore
        for s in steps:
            if s.get("tool") == "check_element_exists":
                out = s.get("output")
                if isinstance(out, dict) and out.get("status") == "success":
                    exists = bool(out.get("exists", False))
                    visible = bool(out.get("is_visible", False))
                    if not exists or not visible:
                        passed = False
                        errors.append({
                            "tool": "check_element_exists",
                            "message": f"Assertion failed: exists={exists}, is_visible={visible}",
                        })

        if verbose:
            print(f"\n{'='*80}")
            print("TEST RESULTS (LEVEL 4)")
            print(f"{'='*80}")
            print(f"PASSED: {passed}")
            if errors:
                print("ERRORS:")
                for e in errors:
                    print(f" - [{e.get('tool')}] {e.get('message')}")
            print(f"Artifacts: {artifacts}")
            if final_answer:
                print("\nNOTES (model text, not used for pass/fail):")
                print(final_answer)
            print(f"{'='*80}\n")

        return {
            "run_id": thread_id,
            "thread_id": thread_id,
            "test_description": test_description,
            "passed": passed,
            "errors": errors,
            "artifacts": artifacts,
            "steps": steps,
            "notes": final_answer,
            "duration_ms": duration_ms,
            "mcp_mode": AppConfig.MCP.MODE,
        }

    def run_test(self, test_description: str, verbose: bool = True) -> dict:
        """
        Esegue un test (versione sincrona - wrapper per async).
        Robusto: se esiste già un event loop attivo, ne crea uno dedicato in modo sicuro.
        """
        try:
            # Se siamo già dentro un loop (es. Jupyter), questo solleverà RuntimeError
            asyncio.get_running_loop()
            has_running_loop = True
        except RuntimeError:
            has_running_loop = False

        if not has_running_loop:
            # Caso normale (CLI/Flask thread): possiamo usare un loop dedicato qui
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(self.run_test_async(test_description, verbose))
            finally:
                loop.close()
        else:
            # Siamo già dentro un loop: creiamo un nuovo loop in un thread separato
            import threading

            result_container = {"result": None, "error": None}

            def _runner():
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    result_container["result"] = loop.run_until_complete(
                        self.run_test_async(test_description, verbose)
                    )
                except Exception as e:
                    result_container["error"] = e
                finally:
                    loop.close()

            t = threading.Thread(target=_runner, daemon=True)
            t.start()
            t.join()

            if result_container["error"]:
                raise result_container["error"]
            return result_container["result"]

    async def run_test_stream(self, test_description: str):
        """
        Esegue un test e streama i risultati in tempo reale.
        """
        await self._initialize()

        print(f"\n{'='*80}")
        print(f"AI TEST AUTOMATION AGENT (MCP STREAMING)")
        print(f"{'='*80}")
        print(f"Test: {test_description}")
        print(f"{'='*80}\n")

        async for event in self.agent.astream({
            "messages": [("human", test_description)]
        }):
            if "agent" in event:
                message = event["agent"]["messages"][-1]
                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tool_call in message.tool_calls:
                        print(f"Calling tool: {tool_call['name']}")
                        print(f"   Args: {tool_call['args']}")
                elif hasattr(message, "content"):
                    print(f"Agent: {message.content[:200]}...")

            elif "tools" in event:
                tool_message = event["tools"]["messages"][-1]
                print(f"Tool response: {tool_message.content[:200]}...")

            yield event


# ==================== ESEMPI DI UTILIZZO ====================

async def example_simple_navigation():
    """Esempio: Navigazione semplice con MCP"""
    agent = TestAgentMCP()

    await agent.run_test_async("""
    Go to google.com and verify the page loads correctly.
    Take a screenshot.
    """)


if __name__ == "__main__":
    print("AI Test Automation Agent con MCP")
    print("=" * 80)
    print("\nConfigurazione centralizzata in config/settings.py")
    print(f"   MCP Mode: {AppConfig.MCP.MODE}")
    print(f"   LLM Provider: {AppConfig.LLM.get_provider()}")
    print("\nRun: asyncio.run(example_simple_navigation())\n")
