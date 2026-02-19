# backend/agent/test_agent_mcp.py
"""
AI Test Automation Agent usando LangGraph e MCP (Model Context Protocol).
Supporta OpenRouter, Azure OpenAI, OpenAI.
"""

import asyncio
import os
import sys
import time
import uuid

from agent.setup import create_llm, create_mcp_config
from agent.system_prompt import get_lab_optimized_prompt
from agent.utils import export_agent_graph, format_tool_io
from agent.evaluation import (
    parse_tool_output,
    step_from_tool_end,
    error_from_tool_output,
    artifact_from_screenshot,
    extract_final_answer_from_event,
    evaluate_passed,
)
from config.settings import AppConfig
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAgentMCP:
    """
    Agent AI per automazione test web usando MCP.
    Configurazione centralizzata tramite AppConfig:
        temperature: Creatività del modello (0 = deterministico)
        use_remote: Se True, usa MCP server remoto. Se False, usa locale (stdio)
    """

    def __init__(self, custom_prompt=None):
        """
        Inizializza l'agent MCP con configurazione da AppConfig.
        custom_prompt: system prompt (opzionale); se None usa get_lab_optimized_prompt().
        """
        self.llm = create_llm()
        self.use_remote = AppConfig.MCP.use_remote()
        self.mcp_config = create_mcp_config(self.use_remote)
        self.custom_prompt = custom_prompt
        self.system_message = self._build_system_message()

        self.client = None
        self.agent = None
        self._initialized = False
        self.tools = []
        self.tools_count = 0
        self.tool_names = []

    def _build_system_message(self):
        """Build system prompt: custom se fornito, altrimenti get_lab_optimized_prompt()."""
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

        print("Esportazione LangGraph visualization...")
        export_agent_graph(self.agent)

        self._initialized = True
        print("Agent MCP inizializzato con successo!\n")

    async def run_test_async(self, test_description: str, verbose: bool = True) -> dict:
        """
        Esegue un test descritto in linguaggio naturale (async).
        Pass/fail deciso dal codice (tool results), non dal modello.
        """
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
            tool_name = ev.get("name") or ev.get("metadata", {}).get("tool_name")

            # Log minimale + input/output tool (per analisi stabilità catena)
            if verbose and event_type == "on_tool_start":
                print(f"[on_tool_start] {tool_name}")
                inp = ev.get("data", {}).get("input")
                if inp is not None:
                    inp_str = format_tool_io(inp)
                    print(f"  input:  {inp_str}")
            if verbose and event_type == "on_tool_end":
                print(f"[on_tool_end] {tool_name}")
                out_raw = ev.get("data", {}).get("output")
                if out_raw is not None:
                    out_clean = parse_tool_output(out_raw)  # stesso output degli step: niente repr/escape
                    print(f"  output: {format_tool_io(out_clean)}")
            if verbose and event_type == "on_tool_error":
                print(f"[on_tool_error] {tool_name}")
                err = ev.get("data", {}).get("error")
                if err is not None:
                    print(f"  error:  {err}")

            if event_type == "on_tool_end":
                tool_name = ev.get("name") or ev.get("metadata", {}).get("tool_name")
                output_obj = parse_tool_output(ev.get("data", {}).get("output"))
                steps.append(step_from_tool_end(tool_name, output_obj))
                err = error_from_tool_output(tool_name, output_obj)
                if err:
                    errors.append(err)
                if tool_name == "capture_screenshot":
                    art = artifact_from_screenshot(output_obj)
                    if art:
                        artifacts.append(art)

            elif event_type == "on_tool_error":
                tool_name = ev.get("name") or ev.get("metadata", {}).get("tool_name")
                err = ev.get("data", {}).get("error")
                errors.append({
                    "tool": tool_name,
                    "message": str(err) if err is not None else "tool error",
                })

            else:
                candidate = extract_final_answer_from_event(ev)
                if candidate:
                    final_answer = candidate

        duration_ms = int((time.monotonic() - start_ts) * 1000)
        passed, errors_final = evaluate_passed(steps, errors)

        if verbose:
            print(f"\n{'='*80}")
            print("TEST RESULTS (LEVEL 4)")
            print(f"{'='*80}")
            print(f"PASSED: {passed}")
            if errors_final:
                print("ERRORS:")
                for e in errors_final:
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
            "errors": errors_final,
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
