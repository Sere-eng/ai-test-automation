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
from typing import Optional, Tuple

from config.settings import AppConfig
from agent.system_prompt import build_lab_prefix_prompt, get_lab_optimized_prompt
from agent.test_agent_mcp import TestAgentMCP
from agent.lab_scenarios import get_scenario_by_id, LabScenario
from codegen.trace_extractor import extract_trace
from codegen.trace_to_playwright import summarize_trace


def _resolve_home_tile(
    module_label: Optional[str] = None,
    module_label_alt: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """
    Tile da aprire sulla home dopo il Continua (solo titoli visibili).
    Se module_label è assente, default storico: Laboratorio Analisi + Clinical Laboratory.
    """
    label = (module_label or "").strip()
    if not label:
        return "Laboratorio Analisi", "Clinical Laboratory"
    alt = (module_label_alt or "").strip() or None
    return label, alt


# Istruzione per il Prefix Agent (URL, credenziali, modulo home)
def _prefix_instruction(
    url: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    module_label: Optional[str] = None,
    module_label_alt: Optional[str] = None,
) -> str:
    """
    - Se url/user/password sono forniti esplicitamente, usa quelli; altrimenti AppConfig.LAB.
    - module_* definisce la tile sulla griglia home (solo titolo visibile in UI).
    """
    resolved_url = url or AppConfig.LAB.URL
    resolved_user = user or AppConfig.LAB.USERNAME or "<username from env>"
    resolved_password = password or AppConfig.LAB.PASSWORD or "<password from env>"
    primary, alt = _resolve_home_tile(module_label, module_label_alt)
    alt_note = (
        f" Se non trovi la tile '{primary}', usa il titolo alternativo '{alt}'."
        if alt
        else ""
    )
    return (
        f"Navigate to {resolved_url}. "
        f"Log in with username '{resolved_user}' and password '{resolved_password}'. "
        "In 'Seleziona Organizzazione' dropdown: open it and select the SECOND option, i.e. 'ORGANIZZAZIONE DI SISTEMA' (not the first 'Dipartimento Interaziendale...'). "
        "Click the 'Continua' button. "
        f"Verify the home page with tiles is visible. Apri il modulo cliccando la tile dal titolo '{primary}' (come in pagina).{alt_note} "
        f"When you are inside that module (its dashboard or menu visible), output one short sentence and STOP. Do NOT call close_browser()."
    )


def _scenario_instruction(scenario: LabScenario) -> str:
    steps = "\n".join(f"- {s}" for s in scenario.execution_steps)
    results = "\n".join(f"- {r}" for r in scenario.expected_results)
    hints_section = (
        f"\nOPERATIVE HINTS (scenario-specific):\n{scenario.prompt_hints.strip()}\n"
        if scenario.prompt_hints
        else ""
    )
    return (
        "The browser is already open and you are inside the Laboratory module "
        "(you may see Preanalitica or Laboratorio or Preanalytic or Laboratory). "
        "Do NOT call start_browser() or navigate_to_url().\n\n"
        "Esegui nel modo dei passi sotto: una sola azione tool per messaggio; attendi l'esito prima "
        "del passo successivo. Aspetta che il contenuto principale della dashboard sia visibile prima "
        "di interagire se la vista è ancora vuota.\n\n"
        f"Scenario: {scenario.name} (id: {scenario.id})\n\n"
        f"Steps:\n{steps}\n\n"
        f"Expected results (for verification):\n{results}\n"
        f"{hints_section}\n"
        "After completing all steps: call close_browser(), then output ONE short neutral sentence. "
        "Do NOT say 'need more steps' or 'sorry' when you have finished the steps."
    )


async def run_prefix_to_home(
    verbose: bool = True,
    url: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    module_label: Optional[str] = None,
    module_label_alt: Optional[str] = None,
) -> dict:
    """
    Esegue il Prefix Agent: login → selezione organizzazione → Continua → apertura tile modulo su home.
    Non chiude il browser; il server MCP (remoto o locale) mantiene la sessione.
    """
    primary, alt = _resolve_home_tile(module_label, module_label_alt)
    prefix_prompt = build_lab_prefix_prompt(
        tile_primary=primary,
        tile_alternate=alt,
    )
    agent = TestAgentMCP(custom_prompt=prefix_prompt)
    instruction = _prefix_instruction(
        url=url,
        user=user,
        password=password,
        module_label=module_label,
        module_label_alt=module_label_alt,
    )
    result = await agent.run_test_async(instruction, verbose=verbose)
    result["phase"] = "prefix"
    return result


async def run_lab_scenario(
    scenario_id: Optional[str] = None,
    scenario: Optional[LabScenario] = None,
    verbose: bool = True,
) -> dict:
    """
    Esegue lo scenario LAB dalla home. Presuppone che il browser sia già sulla home
    (dopo run_prefix_to_home sullo stesso server MCP).

    Args:
        scenario_id: ID dello scenario da cercare in LAB_SCENARIOS (opzionale se scenario è fornito)
        scenario: Oggetto LabScenario diretto (per scenari dinamici estratti da documenti)
        verbose: Se True stampa log dettagliati

    Returns:
        Dict con risultato dell'esecuzione
    """
    # Se scenario non è fornito, cerca per ID
    if scenario is None:
        if scenario_id is None:
            return {
                "phase": "scenario",
                "passed": False,
                "errors": [
                    {
                        "tool": "orchestrator",
                        "message": "Either scenario_id or scenario must be provided",
                    }
                ],
                "artifacts": [],
                "steps": [],
                "notes": "",
                "duration_ms": 0,
            }
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            return {
                "phase": "scenario",
                "passed": False,
                "errors": [
                    {
                        "tool": "orchestrator",
                        "message": f"Scenario '{scenario_id}' not found",
                    }
                ],
                "artifacts": [],
                "steps": [],
                "notes": "",
                "duration_ms": 0,
                "scenario_id": scenario_id,
            }

    # Esegui lo scenario
    agent = TestAgentMCP(custom_prompt=get_lab_optimized_prompt())
    instruction = _scenario_instruction(scenario)
    result = await agent.run_test_async(instruction, verbose=verbose)
    result["phase"] = "scenario"
    result["scenario_id"] = scenario.id
    result["scenario_name"] = scenario.name

    # Testo naturale prodotto dal modello (per uso "umano")
    model_notes = result.get("notes")

    # Summary deterministica derivata direttamente dalla trace MCP (steps)
    steps = result.get("steps") or []
    trace = extract_trace(steps)
    if trace:
        result["trace_summary"] = summarize_trace(
            trace, scenario_id=scenario_id, scenario_name=scenario.name
        )

    # Esponi entrambi:
    # - notes: frase naturale del modello (per compatibilità/UI)
    # - trace_summary: riepilogo tecnico dalla trace
    if model_notes:
        result["notes"] = model_notes

    return result


async def run_full(
    scenario_id: str,
    verbose: bool = True,
    skip_prefix_if_already_home: bool = False,
    url: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    module_label: Optional[str] = None,
    module_label_alt: Optional[str] = None,
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
        module_label=module_label,
        module_label_alt=module_label_alt,
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
    artifacts = prefix_result.get("artifacts", []) + scenario_result.get(
        "artifacts", []
    )

    return {
        "passed": passed,
        "phase": "full",
        "prefix": prefix_result,
        "scenario": scenario_result,
        "errors": errors,
        "artifacts": artifacts,
        "duration_ms": prefix_result.get("duration_ms", 0)
        + scenario_result.get("duration_ms", 0),
    }


def run_full_sync(
    scenario_id: str,
    verbose: bool = True,
    url: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    module_label: Optional[str] = None,
    module_label_alt: Optional[str] = None,
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
                module_label=module_label,
                module_label_alt=module_label_alt,
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
                module_label=module_label,
                module_label_alt=module_label_alt,
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
