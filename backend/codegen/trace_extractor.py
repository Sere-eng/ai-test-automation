# backend/codegen/trace_extractor.py
"""
Normalizza la lista steps prodotta da evaluation.py in una trace pulita
adatta al codegen (solo tool call andati a buon fine, campi essenziali).
"""
from agent.utils import make_json_serializable


# Tool che non producono interazioni Playwright utili nello script finale.
# - infrastruttura browser: start/close/screenshot/waits generici
# - discovery: inspect_* (navigazione interna, non interazione utente)
# - navigazione: navigate_to_url (gestita dal login helper)
# - attesa nominale: wait_for_* per element/field/control (ridondanti nello script diretto)
_SKIP_TOOLS = {
    # Browser lifecycle
    "start_browser",
    "close_browser",
    "capture_screenshot",
    # Waits generici
    "wait_for_dom_change",
    "wait_for_timeout",
    # Discovery (solo input per l'agente, non azioni Playwright)
    "inspect_interactive_elements",
    "inspect_region",
    "get_page_info",
    # Navigazione (gestita da do_login_and_go_to_laboratory nel helper)
    "navigate_to_url",
    # Attesa nominale — nel test diretto si aspetta tramite locator.wait_for()
    "wait_for_clickable_by_name",
    "wait_for_field_by_name",
    "wait_for_control_by_name_and_type",
}


# Chiavi interne di LangChain/LangGraph che si infiltrano negli args del tool
# e non devono finire nel codice generato.
_LANGCHAIN_INTERNAL_KEYS = {"run_manager", "config", "callbacks", "tags", "metadata"}


def _strip_internal_args(args: dict) -> dict:
    """Rimuove chiavi interne LangChain dagli args del tool."""
    return {k: v for k, v in args.items() if k not in _LANGCHAIN_INTERNAL_KEYS}


def extract_trace(steps: list[dict]) -> list[dict]:
    """
    Filtra e normalizza gli step della run in una trace adatta al codegen.

    Regole:
    - Include solo step con type="tool_end" e output.status="success".
    - Esclude i tool di infrastruttura/discovery (vedi _SKIP_TOOLS).
    - Per ogni step estrae: tool, args (dalla chiave "input" se presente), result (campi utili).

    Conseguenza: se uno step è fallito (es. click_smart su un contatore), non
    entra in trace. La run può comunque passare (e.g. SOFT_TOOLS in evaluation),
    ma lo script generato dalla trace risulterà incompleto. Per generare script
    completi, la run deve aver completato con successo tutti gli step dello scenario.

    Returns:
        Lista di dict: [{"tool": str, "args": dict, "result": dict}, ...]
    """
    trace = []
    for step in steps:
        if step.get("type") != "tool_end":
            continue
        tool = step.get("tool", "")
        if tool in _SKIP_TOOLS:
            continue
        output = step.get("output")
        if not isinstance(output, dict):
            continue
        if output.get("status") != "success":
            continue

        # "input" viene popolato dal pending_inputs patch in test_agent_mcp.py.
        # Fallback su "args" per compatibilità con run pre-patch.
        raw_args = step.get("input") or step.get("args") or {}
        args = _strip_internal_args(make_json_serializable(raw_args))
        result = _clean_result(tool, output)

        trace.append(
            {
                "tool": tool,
                "args": args,
                "result": result,
            }
        )

    return trace


# Campi da preservare per codegen: strategia usata, target che ha funzionato, fallback.
_RESULT_KEEP_BASE = {"status", "message", "strategy", "text", "filename"}
_RESULT_KEEP_RICH = {
    "target",  # target effettivo che ha funzionato (click_smart, fill_smart, ecc.)
    "strategies_tried",  # lista strategie tentate
    "fallback_used",  # True se usata una strategia non prima
    "click_type",  # "normal" | "js" (click_smart)
    "scope",  # container padre disambiguante (aggiunto da click_smart/fill_smart)
}


def _clean_result(tool: str, output: dict) -> dict:
    """Preserva status, strategy e info ricche (target, fallback_used, click_type) per codegen."""
    keep = _RESULT_KEEP_BASE | _RESULT_KEEP_RICH
    result = {k: v for k, v in output.items() if k in keep}
    # target e scope possono essere dict: assicuriamoci che siano serializzabili (no oggetti)
    if "target" in result and isinstance(result["target"], dict):
        result["target"] = make_json_serializable(result["target"])
    if "scope" in result and isinstance(result["scope"], dict):
        result["scope"] = make_json_serializable(result["scope"])
    return result
