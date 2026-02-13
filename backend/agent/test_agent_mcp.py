# backend/agent/test_agent_mcp.py
"""
AI Test Automation Agent usando LangGraph e MCP (Model Context Protocol).
Supporta sia OpenAI che Azure OpenAI.
"""

from agent.utils import extract_final_json, safe_json_loads
from agent.system_prompt import get_amc_optimized_prompt, get_lab_optimized_prompt
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

    def __init__(self, custom_prompt=get_lab_optimized_prompt()):
        """
        Inizializza l'agent MCP con configurazione centralizzata.
        
        Args:
            custom_prompt: System prompt personalizzato (opzionale).
                          Se None, usa AMC_SYSTEM_PROMPT di default.
        
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

        # System prompt per l'agent (custom o default)
        self.custom_prompt = custom_prompt
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
        """Build system prompt - usa custom se fornito, altrimenti default AMC"""
        prompt_template = self.custom_prompt if self.custom_prompt else get_lab_optimized_prompt()
        return prompt_template

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
                        artifact = {
                            "type": "screenshot",
                            "filename": output_obj.get("filename"),
                            "size_bytes": output_obj.get("size_bytes"),
                        }
                        # Include base64 if present (when return_base64=True)
                        if output_obj.get("base64"):
                            artifact["base64"] = output_obj.get("base64")
                        artifacts.append(artifact)

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
            
            # Cattura anche l'ultimo messaggio AI dallo stato finale del grafo
            elif event_type == "on_chain_end":
                data = ev.get("data", {}) or {}
                output = data.get("output")
                if isinstance(output, dict) and "messages" in output:
                    messages = output["messages"]
                    if messages:
                        # Cerca l'ultimo messaggio AI
                        for msg in reversed(messages):
                            if hasattr(msg, "content") and hasattr(msg, "type"):
                                if msg.type == "ai" and msg.content:
                                    final_answer = msg.content
                                    break

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
