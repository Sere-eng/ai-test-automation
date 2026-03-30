"""
Pipeline LAB: prefix (login → home → tile) + scenario.

Questo modulo contiene la logica "di orchestrazione" (composizione di agenti/prompt),
separata dall'infrastruttura runtime e dai prompt stessi.
"""

from __future__ import annotations

import asyncio
from typing import Optional, Tuple

from agent.prompts.lab import get_lab_optimized_prompt
from agent.prompts.lab_prefix import build_lab_prefix_prompt
from agent.runtime import MCPAgentRuntime
from agent.test_agent_mcp import TestAgentMCP
from agent.lab_scenarios import get_scenario_by_id, LabScenario
from codegen.trace_extractor import extract_trace
from codegen.trace_to_playwright import summarize_trace
from config.settings import AppConfig


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
        "When you are inside that module (its dashboard or menu visible), output one short sentence and STOP. Do NOT call close_browser()."
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
    prefix_prompt = build_lab_prefix_prompt(tile_primary=primary, tile_alternate=alt)
    runtime = MCPAgentRuntime()
    agent = TestAgentMCP(custom_prompt=prefix_prompt, runtime=runtime)
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
    """
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

    runtime = MCPAgentRuntime()
    agent = TestAgentMCP(custom_prompt=get_lab_optimized_prompt(), runtime=runtime)
    instruction = _scenario_instruction(scenario)
    result = await agent.run_test_async(instruction, verbose=verbose)
    result["phase"] = "scenario"
    result["scenario_id"] = scenario.id
    result["scenario_name"] = scenario.name

    model_notes = result.get("notes")
    steps = result.get("steps") or []
    trace = extract_trace(steps)
    if trace:
        result["trace_summary"] = summarize_trace(
            trace, scenario_id=scenario_id, scenario_name=scenario.name
        )
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
    Esegue prefix + scenario LAB usando un runtime condiviso (stessa sessione MCP/browser).
    """
    runtime = MCPAgentRuntime()

    primary, alt = _resolve_home_tile(module_label, module_label_alt)
    prefix_prompt = build_lab_prefix_prompt(tile_primary=primary, tile_alternate=alt)
    prefix_agent = TestAgentMCP(custom_prompt=prefix_prompt, runtime=runtime)
    prefix_instruction = _prefix_instruction(
        url=url,
        user=user,
        password=password,
        module_label=module_label,
        module_label_alt=module_label_alt,
    )
    prefix_result = await prefix_agent.run_test_async(prefix_instruction, verbose=verbose)
    prefix_result["phase"] = "prefix"
    if not prefix_result.get("passed", False):
        return {
            "passed": False,
            "phase": "full",
            "prefix": prefix_result,
            "scenario": None,
            "errors": prefix_result.get("errors", []),
            "artifacts": prefix_result.get("artifacts", []),
        }

    scenario_agent = TestAgentMCP(custom_prompt=get_lab_optimized_prompt(), runtime=runtime)
    scenario_obj = get_scenario_by_id(scenario_id)
    if not scenario_obj:
        return {
            "passed": False,
            "phase": "full",
            "prefix": prefix_result,
            "scenario": None,
            "errors": [
                {
                    "tool": "orchestrator",
                    "message": f"Scenario '{scenario_id}' not found",
                }
            ],
            "artifacts": prefix_result.get("artifacts", []),
        }

    scenario_instruction = _scenario_instruction(scenario_obj)
    scenario_result = await scenario_agent.run_test_async(
        scenario_instruction, verbose=verbose
    )
    scenario_result["phase"] = "scenario"
    scenario_result["scenario_id"] = scenario_obj.id
    scenario_result["scenario_name"] = scenario_obj.name

    steps = scenario_result.get("steps") or []
    trace = extract_trace(steps)
    if trace:
        scenario_result["trace_summary"] = summarize_trace(
            trace, scenario_id=scenario_id, scenario_name=scenario_obj.name
        )

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

