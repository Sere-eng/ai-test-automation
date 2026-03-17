# backend/codegen/script_generator.py
"""
Genera uno script Playwright Python da una trace normalizzata.

Versione attuale: compilazione DETERMINISTICA senza LLM.
Le regole di traduzione MCP → Playwright sono implementate in trace_to_playwright.py.

Gli script generati vengono salvati in backend/generated/ (creata automaticamente).
"""
import logging
from pathlib import Path
from typing import Optional

from codegen.trace_extractor import extract_trace
from codegen.trace_to_playwright import generate_script_from_trace

logger = logging.getLogger(__name__)

# Cartella dove vengono salvati gli script generati.
# Relativa alla directory di questo file: backend/codegen/../generated → backend/generated/
_GENERATED_DIR = Path(__file__).parent.parent / "generated"


def generate_playwright_script(
    scenario_result: dict,
    scenario_id: str,
    scenario_name: str,
    save_to_disk: bool = True,
    prefix_result: Optional[dict] = None,
) -> Optional[str]:
    """
    Genera uno script Playwright Python sincrono da scenario_result (e opzionalmente prefix).

    Args:
        scenario_result: dict restituito da run_lab_scenario (contiene "steps").
        scenario_id:     es. "scenario_1"
        scenario_name:   es. "Creazione filtro e visualizzazione in dashboard"
        save_to_disk:    se True (default), salva lo script in backend/generated/
        prefix_result:   opzionale, dict restituito da run_prefix_to_home (contiene "steps").
                        Se fornito, l'helper di login viene generato dalla trace del prefix
                        (stesse strategie/target della run MCP) invece che dal template fisso.

    Returns:
        Stringa con il codice Python, oppure None se la generazione fallisce.
    """

    steps = scenario_result.get("steps", [])
    if not steps:
        logger.warning(
            "generate_playwright_script: nessuno step trovato in scenario_result"
        )
        return None

    trace = extract_trace(steps)
    if not trace:
        logger.warning("generate_playwright_script: trace vuota dopo estrazione")
        return None

    prefix_trace: Optional[list] = None
    if prefix_result and prefix_result.get("steps"):
        prefix_trace = extract_trace(prefix_result["steps"])
        if not prefix_trace:
            logger.info(
                "generate_playwright_script: prefix_result fornito ma trace prefix vuota, uso template login"
            )
            prefix_trace = None

    try:
        script = generate_script_from_trace(
            trace=trace,
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            prefix_trace=prefix_trace,
        )
    except Exception as e:
        logger.error(
            f"generate_playwright_script: errore compilazione trace → script: {e}"
        )
        return None

    if save_to_disk and script:
        _save_script(script, scenario_id)

    return script


def _save_script(script: str, scenario_id: str) -> Optional[Path]:
    """
    Salva lo script in backend/generated/test_<scenario_id>.py.
    Crea la cartella se non esiste.

    Returns:
        Path del file salvato, oppure None in caso di errore.
    """
    try:
        _GENERATED_DIR.mkdir(parents=True, exist_ok=True)

        # Aggiungi __init__.py vuoto per rendere la cartella un package Python
        init_file = _GENERATED_DIR / "__init__.py"
        if not init_file.exists():
            init_file.write_text("", encoding="utf-8")

        output_path = _GENERATED_DIR / f"test_{scenario_id}.py"
        output_path.write_text(script, encoding="utf-8")
        logger.info(f"Script salvato in: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"_save_script: impossibile salvare su disco: {e}")
        return None
