# backend/agent/orchestrator.py
"""
Orchestrator per l'approccio agentico LAB: Prefix Agent (login → home) + Dashboard Agent (scenari).

Flusso:
  1. run_prefix_to_home() → un agente con prompt "prefix" esegue login, org, Continua, verifica home.
     Non chiude il browser (stesso server MCP = stesso browser).
  2. run_lab_scenario(scenario_id) → un agente con prompt LAB esegue lo scenario dalla home.
     Chiude il browser alla fine.
  3. run_full(scenario_id) → esegue 1 poi 2 e restituisce risultato combinato.
"""

import asyncio
from typing import Optional

from config.settings import AppConfig
from agent.system_prompt import get_prefix_prompt, get_lab_optimized_prompt
from agent.test_agent_mcp import TestAgentMCP
from agent.lab_scenarios import get_scenario_by_id, LabScenario


# Istruzione per il Prefix Agent (URL e credenziali parametrizzabili, con fallback da config)
def _prefix_instruction(
    url: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> str:
    """
    Costruisce l'istruzione naturale per il Prefix Agent (login → organizzazione → Continua → tile LAB).

    - Se url/user/password sono forniti esplicitamente, usa quelli.
    - Altrimenti fa fallback su AppConfig.LAB (e infine sui placeholder "<... from env>").
    """
    resolved_url = url or AppConfig.LAB.URL
    resolved_user = user or AppConfig.LAB.USERNAME or "<username from env>"
    resolved_password = password or AppConfig.LAB.PASSWORD or "<password from env>"
    return (
        f"Navigate to {resolved_url}. "
        f"Log in with username '{resolved_user}' and password '{resolved_password}'. "
        "In 'Seleziona Organizzazione' dropdown: open it and select the SECOND option, i.e. 'ORGANIZZAZIONE DI SISTEMA' (not the first 'Dipartimento Interaziendale...'). "
        "Click the 'Continua' button. "
        "Verify the home page with tiles is visible. Then CLICK the tile 'Laboratorio Analisi' (use this exact label first; if the UI is in English, use 'Clinical Laboratory') to enter the Laboratory module. "
        "When you are inside the Laboratory module (Laboratory dashboard or menu visible), output one short sentence and STOP. Do NOT call close_browser()."
    )


def _scenario_instruction(scenario: LabScenario) -> str:
    steps = "\n".join(f"- {s}" for s in scenario.execution_steps)
    results = "\n".join(f"- {r}" for r in scenario.expected_results)
    hints_section = (
        f"\nOPERATIVE HINTS (scenario-specific):\n{scenario.prompt_hints.strip()}\n"
        if scenario.prompt_hints else ""
    )
    return (
        "The browser is already open and you are inside the Laboratory module "
        "(you may see Preanalitica or Laboratorio). "
        "Do NOT call start_browser() or navigate_to_url().\n\n"
        "SEQUENTIAL TOOLS: Issue only ONE tool call per message. "
        "Wait for the result, then in the next message call the next tool. "
        "Do NOT send multiple tool calls in the same response "
        "(they would run in parallel and break the step order).\n\n"
        "INITIAL WAIT: call wait_for_load_state(\"domcontentloaded\"), then "
        "wait_for_text_content(\"Preanalitica\") — if it times out try "
        "wait_for_text_content(\"Laboratorio\"). "
        "Do NOT inspect or interact while the main content area is still blank.\n\n"
        f"Scenario: {scenario.name} (id: {scenario.id})\n\n"
        f"Steps:\n{steps}\n\n"
        f"Expected results (for verification):\n{results}\n"
        f"{hints_section}\n"
        "After completing all steps: capture_screenshot(\"test_success.png\", return_base64=False), "
        "then close_browser(), then ONE short sentence. "
        "Do NOT say 'need more steps' or 'sorry' when you have finished the steps."
    )


async def run_prefix_to_home(
    verbose: bool = True,
    url: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> dict:
    """
    Esegue il Prefix Agent: login → selezione organizzazione → Continua → verifica home.
    Non chiude il browser; il server MCP (remoto o locale) mantiene la sessione.
    """
    agent = TestAgentMCP(custom_prompt=get_prefix_prompt())
    instruction = _prefix_instruction(url=url, user=user, password=password)
    result = await agent.run_test_async(instruction, verbose=verbose)
    result["phase"] = "prefix"
    return result


async def run_lab_scenario(scenario_id: str, verbose: bool = True) -> dict:
    """
    Esegue lo scenario LAB dalla home. Presuppone che il browser sia già sulla home
    (dopo run_prefix_to_home sullo stesso server MCP).
    """
    scenario = get_scenario_by_id(scenario_id)
    if not scenario:
        return {
            "phase": "scenario",
            "passed": False,
            "errors": [{"tool": "orchestrator", "message": f"Scenario '{scenario_id}' not found"}],
            "artifacts": [],
            "steps": [],
            "notes": "",
            "duration_ms": 0,
            "scenario_id": scenario_id,
        }
    agent = TestAgentMCP(custom_prompt=get_lab_optimized_prompt())
    instruction = _scenario_instruction(scenario)
    result = await agent.run_test_async(instruction, verbose=verbose)
    result["phase"] = "scenario"
    result["scenario_id"] = scenario_id
    result["scenario_name"] = scenario.name
    return result


async def run_full(
    scenario_id: str,
    verbose: bool = True,
    skip_prefix_if_already_home: bool = False,
    url: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> dict:
    """
    Esegue prima il prefix (login → home), poi lo scenario LAB.
    Restituisce un risultato combinato; passed = True solo se entrambe le fasi passano.

    - url/user/password possono essere passati esplicitamente (es. da frontend);
      se None, viene usata la configurazione da AppConfig.LAB.
    """
    prefix_result = await run_prefix_to_home(
        verbose=verbose,
        url=url,
        user=user,
        password=password,
    )
    if not prefix_result.get("passed", False):
        return {
            "passed": False,
            "phase": "full",
            "prefix": prefix_result,
            "scenario": None,
            "errors": prefix_result.get("errors", []),
            "artifacts": prefix_result.get("artifacts", []),
        }

    scenario_result = await run_lab_scenario(scenario_id, verbose=verbose)
    passed = scenario_result.get("passed", False)
    errors = prefix_result.get("errors", []) + scenario_result.get("errors", [])
    artifacts = prefix_result.get("artifacts", []) + scenario_result.get("artifacts", [])

    return {
        "passed": passed,
        "phase": "full",
        "prefix": prefix_result,
        "scenario": scenario_result,
        "errors": errors,
        "artifacts": artifacts,
        "duration_ms": prefix_result.get("duration_ms", 0) + scenario_result.get("duration_ms", 0),
    }


def run_full_sync(
    scenario_id: str,
    verbose: bool = True,
    url: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> dict:
    """Versione sincrona di run_full (per Flask o script non-async)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(
            run_full(
                scenario_id,
                verbose=verbose,
                url=url,
                user=user,
                password=password,
            )
        )
    # Già in un loop (es. Jupyter): esegui in un thread
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(
            asyncio.run,
            run_full(
                scenario_id,
                verbose=verbose,
                url=url,
                user=user,
                password=password,
            ),
        )
        return future.result()


if __name__ == "__main__":
    import sys
    scenario_id = sys.argv[1] if len(sys.argv) > 1 else "scenario_1"
    print(f"Orchestrator: prefix → scenario {scenario_id}")
    result = run_full_sync(scenario_id, verbose=True)
    print(f"Passed: {result.get('passed')}")
    if result.get("errors"):
        for e in result["errors"]:
            print(f"  Error: [{e.get('tool')}] {e.get('message')}")
    sys.exit(0 if result.get("passed") else 1)