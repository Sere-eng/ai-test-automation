# backend/agent/test_agent_mcp.py
"""
AI Test Automation Agent usando LangGraph e MCP (Model Context Protocol).
Supporta sia OpenAI che Azure OpenAI.
"""

from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from datetime import datetime
import os
import sys
import asyncio

# Import della configurazione centralizzata
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import AppConfig


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
        """Build system prompt"""
        return f"""You are an expert web testing automation assistant.

Your job is to execute web tests by using the available Playwright tools via MCP.

IMPORTANT RULES:
1. ALWAYS start by calling start_browser() before any other action
2. For AJAX requests (dynamic content loading), ALWAYS use wait_for_element() after clicking buttons or submitting forms
3. After filling forms, use wait_for_element() to wait for success/error messages
4. Use check_element_exists() to verify test assertions
5. ALWAYS call close_browser() at the end of the test
6. If something fails, explain what went wrong clearly

SCREENSHOT RULES:
- By default, call capture_screenshot(filename, return_base64=False)
- This captures the screenshot but does NOT return base64 (saves tokens)
- ONLY use return_base64=True if the user EXPLICITLY asks for the image data
- Examples:
  "take a screenshot" → use return_base64=False
  "verify the page loaded" → use return_base64=False
  "show me the screenshot as base64" → use return_base64=True
  "I need the image data" → use return_base64=True

SELECTOR DISCOVERY (CRITICAL):
- NEVER guess selectors like #username, #password, #login-btn
- When test says "fill username/password" without exact selectors:
    1. Call inspect_page_structure() FIRST to discover page structure
    2. Look in the output for input fields and their attributes
    3. Use the suggested selectors from inspect_page_structure()
- Example workflow for "login with user/pass":
    * navigate_to_url("https://site.com")
    * inspect_page_structure()  ← Discover selectors FIRST
    * Read output: "input[name='username']", "input[name='password']"
    * fill_input("input[name='username']", "myuser")
    * fill_input("input[name='password']", "mypass")
- Common selector patterns:
    * input[name='fieldname'], input[type='email']
    * button:has-text('Login'), a:has-text('Sign Up')

COOKIE CONSENT BANNERS:
- Many sites show cookie consent banners (Google, Amazon, etc.)
- Use the handle_cookie_banner() tool to handle these automatically
- This tool tries multiple strategies: Google, Amazon, generic Accept buttons
- RECOMMENDED WORKFLOW:
1. navigate_to_url("https://example.com")
2. handle_cookie_banner()  ← Call this right after navigation
3. fill_input("textarea[name='q']", "AI test automation")
4. press_key("Enter")
5. wait_for_element("#search", state="visible")
6. Continue with test actions (search, fill forms, etc.)

STOPPING CONDITIONS:
- When you see "STOP" or "After step X, STOP" in the test description
- After close_browser() is called
- If an error occurs that cannot be recovered

EXAMPLE WORKFLOW:
1. start_browser(headless=False)
2. navigate_to_url("https://example.com")
3. handle_cookie_banner()  if there is a cookie consent banner, otherwise skip and continue with step 4
4. click_element("#login-button")
5. fill_input("#email", "test@test.com")
6. fill_input("#password", "password123")
7. click_element("#submit")
8. wait_for_element(".success-message", state="visible")
9. check_element_exists(".user-dashboard")
10. capture_screenshot("test-result.png", , return_base64=False)
11. close_browser()
→ STOP HERE (do not continue after close_browser)

Current date: {datetime.today().strftime('%Y-%m-%d')}

Execute the test step by step and report the results clearly.
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
        
        print(f"{len(tools)} tool caricati da MCP Server:")
        for tool in tools:
            print(f"   - {tool.name}")
        
        # Crea l'agent ReAct con i tool MCP
        self.agent = create_react_agent(
            self.llm,
            tools,
            prompt=self.system_message
        )
        
        self._initialized = True
        print("Agent MCP inizializzato con successo!\n")
    
    async def run_test_async(self, test_description: str, verbose: bool = True) -> dict:
        """
        Esegue un test descritto in linguaggio naturale (versione async).
        
        Args:
            test_description: Descrizione del test in linguaggio naturale
            verbose: Se True, stampa i passi intermedi
        
        Returns:
            dict con risultati del test
        """
        # Assicurati che l'agent sia inizializzato
        await self._initialize()
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"AI TEST AUTOMATION AGENT (MCP)")
            print(f"{'='*80}")
            print(f"Test Description: {test_description}")
            print(f"{'='*80}\n")
        
        # Esegui l'agent
        response = await self.agent.ainvoke(
                {"messages": [("human", test_description)]},
                config={
                    "recursion_limit": 50,  # AUMENTATO da 25 (default) a 50
                    "configurable": {
                        "thread_id": "test-run"
                    }
                }
            )
        # Estrai il risultato finale
        messages = response["messages"]
        final_answer = messages[-1].content
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"TEST RESULTS")
            print(f"{'='*80}")
            print(final_answer)
            print(f"{'='*80}\n")
        
        return {
            "test_description": test_description,
            "final_answer": final_answer,
            #"all_messages": messages,
            "success": "success" in final_answer.lower()
        }
    
    def run_test(self, test_description: str, verbose: bool = True) -> dict:
        """
        Esegue un test (versione sincrona - wrapper per async).
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.run_test_async(test_description, verbose)
            )
        finally:
            loop.close()
    
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