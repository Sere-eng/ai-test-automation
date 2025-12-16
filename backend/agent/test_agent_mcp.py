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
from dotenv import load_dotenv
import asyncio

# Carica variabili d'ambiente
load_dotenv()


class TestAgentMCP:
    """
    Agent AI per automazione test web usando MCP.
    Supporta OpenAI e Azure OpenAI.
    """
    
    def __init__(self, temperature=0, use_remote=False):
        """
        Inizializza l'agent con MCP.
        
        Args:
            temperature: Creatività del modello (0 = deterministico)
            use_remote: Se True, usa MCP server remoto. Se False, usa locale (stdio)
        """
        # Determina quale LLM usare (OpenAI o Azure)
        self.llm = self._setup_llm(temperature)
        
        self.use_remote = use_remote
        
        # Configurazione MCP Client
        if use_remote:
            # Usa server remoto HTTP
            self.mcp_config = {
                "playwright": {
                    "url": "http://localhost:8001/mcp/",
                    "transport": "streamable_http",
                }
            }
            print("🌐 Usando MCP Server REMOTO (HTTP) su porta 8001")
        else:
            # Usa server locale stdio
            import sys
            script_dir = os.path.dirname(os.path.abspath(__file__))
            server_path = os.path.join(
                os.path.dirname(script_dir),
                "mcp_servers",
                "playwright_server_local.py"
            )
            
            self.mcp_config = {
                "playwright": {
                    "command": sys.executable,  # Python interpreter
                    "args": [server_path],
                    "transport": "stdio",
                }
            }
            print(f"💻 Usando MCP Server LOCALE (stdio)")
        
        # System prompt per l'agent
        self.system_message = f"""You are an expert web testing automation assistant.

Your job is to execute web tests by using the available Playwright tools via MCP.

IMPORTANT RULES:
1. ALWAYS start by calling start_browser() before any other action
2. For AJAX requests (dynamic content loading), ALWAYS use wait_for_element() after clicking buttons or submitting forms
3. After filling forms, use wait_for_element() to wait for success/error messages
4. Use check_element_exists() to verify test assertions
5. ALWAYS call close_browser() at the end of the test
6. If something fails, explain what went wrong clearly

EXAMPLE WORKFLOW:
1. start_browser(headless=False)
2. navigate_to_url("https://example.com")
3. click_element("#login-button")
4. fill_input("#email", "test@test.com")
5. fill_input("#password", "password123")
6. click_element("#submit")
7. wait_for_element(".success-message", state="visible")
8. check_element_exists(".user-dashboard")
9. capture_screenshot("test-result.png")
10. close_browser()

Current date: {datetime.today().strftime('%Y-%m-%d')}

Execute the test step by step and report the results clearly.
"""
        
        # Inizializza il client MCP e l'agent (async)
        self.client = None
        self.agent = None
        self._initialized = False
    
    def _setup_llm(self, temperature):
        """
        Setup LLM - supporta OpenAI, Azure OpenAI, e OpenRouter.
        
        Returns:
            ChatOpenAI o AzureChatOpenAI instance
        """
        # Check se OpenRouter è configurato (priorità alta)
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        openrouter_model = os.getenv("OPENROUTER_MODEL")
        
        if openrouter_key and openrouter_model:
            # Usa OpenRouter
            print(f"🟣 Usando OpenRouter")
            print(f"   Model: {openrouter_model}")
            
            return ChatOpenAI(
                model=openrouter_model,
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=temperature,
                max_tokens=4000,
            )
        
        # Check se Azure OpenAI è configurato
        azure_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        
        if azure_key and azure_endpoint and azure_deployment:
            # Usa Azure OpenAI
            print(f"🔵 Usando AZURE OpenAI")
            print(f"   Endpoint: {azure_endpoint}")
            print(f"   Deployment: {azure_deployment}")
            
            return AzureChatOpenAI(
                azure_endpoint=azure_endpoint,
                azure_deployment=azure_deployment,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
                api_key=azure_key,
                temperature=temperature,
                max_tokens=4000,
            )
        else:
            # Usa OpenAI standard
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                raise ValueError(
                    "Nessuna API key configurata!\n"
                    "Configura .env con una di queste:\n"
                    "  - OPENROUTER_API_KEY + OPENROUTER_MODEL\n"
                    "  - OPENAI_API_KEY\n"
                    "  - AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_DEPLOYMENT_NAME"
                )
            
            print(f"🟢 Usando OpenAI Standard")
            print(f"   Model: gpt-4o-mini")
            
            return ChatOpenAI(
                model="gpt-4o-mini",
                temperature=temperature,
                max_tokens=4000,
            )
    
    async def _initialize(self):
        """Inizializza il client MCP e l'agent (deve essere chiamato una volta)"""
        if self._initialized:
            return
        
        print("🔧 Inizializzazione MCP Client...")
        
        # Crea il client MCP
        self.client = MultiServerMCPClient(self.mcp_config)
        
        # Carica i tool dal server MCP
        print("📥 Caricamento tool da MCP Server...")
        tools = await self.client.get_tools()
        
        print(f"✅ {len(tools)} tool caricati da MCP Server:")
        for tool in tools:
            print(f"   - {tool.name}")
        
        # Crea l'agent ReAct con i tool MCP
        self.agent = create_react_agent(
            self.llm,
            tools,
            prompt=self.system_message
        )
        
        self._initialized = True
        print("✅ Agent MCP inizializzato con successo!\n")
    
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
            print(f"🤖 AI TEST AUTOMATION AGENT (MCP)")
            print(f"{'='*80}")
            print(f"📝 Test Description: {test_description}")
            print(f"{'='*80}\n")
        
        # Esegui l'agent
        response = await self.agent.ainvoke({
            "messages": [("human", test_description)]
        })
        
        # Estrai il risultato finale
        messages = response["messages"]
        final_answer = messages[-1].content
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"📊 TEST RESULTS")
            print(f"{'='*80}")
            print(final_answer)
            print(f"{'='*80}\n")
        
        return {
            "test_description": test_description,
            "final_answer": final_answer,
            "all_messages": messages,
            "success": "✅" in final_answer or "success" in final_answer.lower()
        }
    
    def run_test(self, test_description: str, verbose: bool = True) -> dict:
        """
        Esegue un test (versione sincrona - wrapper per async).
        
        Args:
            test_description: Descrizione del test
            verbose: Se True, stampa output
        
        Returns:
            dict con risultati
        """
        # Crea un nuovo event loop per eseguire la versione async
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
        Utile per mostrare progresso nell'UI.
        
        Args:
            test_description: Descrizione del test
        
        Yields:
            Eventi dell'agent step by step
        """
        # Assicurati che l'agent sia inizializzato
        await self._initialize()
        
        print(f"\n{'='*80}")
        print(f"🤖 AI TEST AUTOMATION AGENT (MCP STREAMING)")
        print(f"{'='*80}")
        print(f"📝 Test: {test_description}")
        print(f"{'='*80}\n")
        
        async for event in self.agent.astream({
            "messages": [("human", test_description)]
        }):
            # Stampa eventi intermedi
            if "agent" in event:
                message = event["agent"]["messages"][-1]
                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tool_call in message.tool_calls:
                        print(f"🔧 Calling tool: {tool_call['name']}")
                        print(f"   Args: {tool_call['args']}")
                elif hasattr(message, "content"):
                    print(f"💭 Agent: {message.content[:200]}...")
            
            elif "tools" in event:
                tool_message = event["tools"]["messages"][-1]
                print(f"📤 Tool response: {tool_message.content[:200]}...")
            
            yield event


# ==================== ESEMPI DI UTILIZZO ====================

async def example_simple_navigation():
    """Esempio: Navigazione semplice con MCP"""
    agent = TestAgentMCP(use_remote=False)
    
    await agent.run_test_async("""
    Go to google.com and verify the page loads correctly.
    Take a screenshot.
    """)


async def example_form_filling():
    """Esempio: Compilazione form con AJAX"""
    agent = TestAgentMCP(use_remote=False)
    
    await agent.run_test_async("""
    Go to https://example.com/login
    Fill the email field with test@test.com
    Fill the password field with password123
    Click the login button
    Wait for the page to load (AJAX)
    Verify that a success message appears
    Take a screenshot
    """)


async def example_remote_server():
    """Esempio: Usa MCP server remoto"""
    print("📝 NOTA: Assicurati che il server remoto sia avviato:")
    print("   python backend/mcp_servers/playwright_server_remote.py\n")
    
    agent = TestAgentMCP(use_remote=True)
    
    await agent.run_test_async("""
    Test navigation to google.com and take a screenshot.
    """)


if __name__ == "__main__":
    print("🚀 AI Test Automation Agent con MCP")
    print("=" * 80)
    print("\n✅ Supporta OpenAI e Azure OpenAI")
    print("   Configura .env con le credenziali appropriate\n")
    print("\nEsempi disponibili:")
    print("1. asyncio.run(example_simple_navigation())")
    print("2. asyncio.run(example_form_filling())")
    print("3. asyncio.run(example_remote_server())  # Richiede server remoto attivo")
    print("\nRun any example to test the agent!\n")
    
    # Uncomment to run example:
    # asyncio.run(example_simple_navigation())