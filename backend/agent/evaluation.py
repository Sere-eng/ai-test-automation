# backend/agent/evaluation.py
"""
Logica di valutazione run: parsing eventi stream, pass/fail da tool results.
Usa agent.utils per funzioni generiche (es. safe_json_loads); non sovrappone utils.
"""
import re
from typing import Any, Optional

from agent.utils import safe_json_loads


# Classificazione logica dei tool per la valutazione pass/fail.
#
# - INFRA_TOOLS: infrastruttura pura (screenshot, chiusura browser).
#   Gli errori vengono ignorati completamente — non sono asserzioni di test.
#
# - SOFT_TOOLS: azioni/interazioni dove errori intermedi fanno parte del fallback naturale.
#   Tolleranza: se l'ultimo uso del tool è success, gli errori precedenti vengono ignorati.
#
# - PROBING_TOOLS / VERIFICATION_TOOLS: tool di verifica usati spesso in coppia
#   (es. wait_for_text_content + get_text_by_visible_content).
#   Tolleranza a gruppo: se l'ultimo uso di QUALSIASI tool del gruppo è success,
#   gli errori di TUTTI i tool del gruppo vengono ignorati.
#
# - HARD_ASSERT_TOOLS: asserzioni vere e proprie; qualsiasi errore è bloccante.

INFRA_TOOLS: set[str] = {
    "capture_screenshot",
    "close_browser",
    "start_browser",
}

SOFT_TOOLS: set[str] = {
    "click_smart",
    "fill_smart",
    "scroll_to_bottom",
    "wait_for_clickable_by_name",
    "wait_for_field_by_name",
    "wait_for_control_by_name_and_type",
}

# Tool di verifica raggruppati: se uno del gruppo finisce in success,
# gli errori degli altri tool dello stesso gruppo vengono cancellati.
VERIFICATION_GROUPS: list[set[str]] = [
    {
        "wait_for_text_content",
        "get_text_by_visible_content",
    },
]

# Mantenuto per compatibilità — viene assorbito da VERIFICATION_GROUPS
PROBING_TOOLS: set[str] = {
    "wait_for_text_content",
}

HARD_ASSERT_TOOLS: set[str] = {
    "wait_for_element_state",
}


def normalize_tool_output_raw(output_raw: Any) -> Any:
    """
    Estrae la stringa content da oggetti message (es. ToolMessage LangChain).
    Così negli step si salva JSON parsato (dict) invece del repr con escape.
    """
    if output_raw is None or isinstance(output_raw, str):
        return output_raw
    if hasattr(output_raw, "content"):
        c = getattr(output_raw, "content", None)
        if isinstance(c, str):
            return c
        if c is not None:
            return str(c)
    return output_raw


def parse_tool_output(output_raw: Any) -> Any:
    """Normalizza output tool (stringa JSON -> dict se possibile). Evita di salvare oggetti non serializzabili."""
    raw = normalize_tool_output_raw(output_raw)
    if raw is None:
        return None
    if not isinstance(raw, str):
        return {
            "_raw_type": type(raw).__name__,
            "_note": "output was not string or message",
        }
    parsed = safe_json_loads(raw)
    return parsed if parsed is not None else raw


def step_from_tool_end(tool_name: str, output_obj: Any) -> dict:
    """Costruisce lo step da un evento on_tool_end."""
    return {
        "type": "tool_end",
        "tool": tool_name,
        "output": output_obj,
    }


def error_from_tool_output(tool_name: str, output_obj: dict) -> Optional[dict]:
    """Se output ha status=error, restituisce il dict errore.
    Gli errori di INFRA_TOOLS vengono ignorati a monte."""
    if tool_name in INFRA_TOOLS:
        return None

    # inspect_region: se il contenitore specifico non esiste perché il contenuto è reso
    # "inline" e non in dialog, la tool docstring suggerisce di NON considerarlo un blocco.
    # In quel caso ignoriamo quell'errore per non far fallire l'intero scenario.
    if tool_name == "inspect_region" and isinstance(output_obj, dict):
        msg = output_obj.get("message", "") or ""
        if output_obj.get("status") == "error" and "Contenitore non trovato per selector" in msg:
            return None

    # wait_for_dom_change: timeout senza mutazioni è frequente su SPA Angular (routing interno,
    # stesso body); non è un'asserzione affidabile — vedi LAB_SYSTEM_PROMPT (evitare questo tool).
    if tool_name == "wait_for_dom_change" and isinstance(output_obj, dict):
        msg = output_obj.get("message", "") or ""
        if output_obj.get("status") == "error" and "Nessun cambiamento DOM rilevato" in msg:
            return None

    if not isinstance(output_obj, dict) or output_obj.get("status") != "error":
        return None
    return {
        "tool": tool_name,
        "message": output_obj.get("message", "unknown error"),
    }


def artifact_from_screenshot(output_obj: dict) -> Optional[dict]:
    """Se output è screenshot di successo, restituisce artifact."""
    if not isinstance(output_obj, dict) or output_obj.get("status") != "success":
        return None
    if not output_obj.get("filename"):
        return None
    art = {
        "type": "screenshot",
        "filename": output_obj.get("filename"),
        "size_bytes": output_obj.get("size_bytes"),
    }
    if output_obj.get("base64"):
        art["base64"] = output_obj["base64"]
    return art


def extract_final_answer_from_event(ev: dict) -> Optional[str]:
    """Estrae testo finale da eventi on_chat_model_end / on_llm_end / on_chain_end."""
    event_type = ev.get("event")
    data = ev.get("data") or {}

    if event_type in ("on_chat_model_end", "on_llm_end"):
        out = data.get("output")
        if isinstance(out, str):
            return out
        if isinstance(out, dict):
            return out.get("content") or out.get("text") or ""
        if isinstance(out, list) and out:
            last = out[-1]
            if isinstance(last, str):
                return last
            if isinstance(last, dict):
                return last.get("content") or last.get("text") or ""
        return None

    if event_type == "on_chain_end":
        output = data.get("output")
        if not isinstance(output, dict) or "messages" not in output:
            return None
        for msg in reversed(output["messages"]):
            if getattr(msg, "type", None) == "ai" and getattr(msg, "content", None):
                return msg.content
    return None


def evaluate_passed(steps: list[dict], errors: list[dict]) -> tuple[bool, list[dict]]:
    """
    Pass/fail da steps e errori (livello avanzato: codice decide, non il modello).

    Logica di tolleranza (in ordine):
    1. INFRA_TOOLS: errori ignorati completamente (già filtrati da error_from_tool_output).
    2. SOFT_TOOLS: se l'ultimo uso del tool è success, errori precedenti ignorati.
    3. VERIFICATION_GROUPS: se almeno una invocazione (nel trace) di un tool del gruppo è success,
       errori di tutte le invocazioni di quel gruppo vengono ignorati.
    """
    errors_out = list(errors)

    # Calcola l'ultimo status per ogni tool (per SOFT_TOOLS: retry / ultimo risultato)
    last_status_by_tool: dict[str, str] = {}
    for s in steps:
        tool = s.get("tool")
        out = s.get("output")
        if not isinstance(out, dict):
            continue
        status = out.get("status")
        if status in ("success", "error") and tool:
            last_status_by_tool[tool] = status

    def _any_step_success_in_group(group: set[str]) -> bool:
        """Almeno una invocazione nel trace con status success (non solo l'ultima per nome tool)."""
        for s in steps:
            if s.get("tool") not in group:
                continue
            out = s.get("output")
            if isinstance(out, dict) and out.get("status") == "success":
                return True
        return False

    # Tolleranza SOFT_TOOLS: ultimo uso success → cancella errori precedenti
    for t in SOFT_TOOLS:
        if last_status_by_tool.get(t) == "success":
            errors_out = [e for e in errors_out if e.get("tool") != t]

    # Tolleranza VERIFICATION_GROUPS: se QUALSIASI invocazione di un tool del gruppo è success,
    # cancella tutti gli errori del gruppo (probe multipli: es. wait su testo A ok, wait su testo B fallito).
    for group in VERIFICATION_GROUPS:
        if _any_step_success_in_group(group):
            errors_out = [e for e in errors_out if e.get("tool") not in group]

    errors_out = _strip_redundant_wait_for_tile_title_after_click(steps, errors_out)

    passed = len(errors_out) == 0

    return passed, errors_out


_WAIT_TEXT_NOT_FOUND_IT = re.compile(
    r"Testo\s+'([^']+)'\s+non\s+trovato",
    re.IGNORECASE,
)


def _strip_redundant_wait_for_tile_title_after_click(
    steps: list[dict], errors_out: list[dict]
) -> list[dict]:
    """
    Dopo un click_smart riuscito su role=button con name=X, spesso il modello chiama ancora
    wait_for_text_content(X): sulla nuova vista quel testo (titolo tile) non c'è più → errore fittizio.
    In quel caso non consideriamo l'errore bloccante.
    """
    clicked_button_names: set[str] = set()
    for s in steps:
        if s.get("tool") != "click_smart":
            continue
        out = s.get("output")
        if not isinstance(out, dict) or out.get("status") != "success":
            continue
        tgt = out.get("target") or {}
        if tgt.get("by") == "role" and tgt.get("role") == "button":
            n = (tgt.get("name") or "").strip()
            if n:
                clicked_button_names.add(n)
    if not clicked_button_names:
        return errors_out

    kept: list[dict] = []
    for e in errors_out:
        if e.get("tool") != "wait_for_text_content":
            kept.append(e)
            continue
        msg = e.get("message", "") or ""
        m = _WAIT_TEXT_NOT_FOUND_IT.search(msg)
        if not m:
            kept.append(e)
            continue
        waited = m.group(1).strip()
        if waited in clicked_button_names:
            continue
        kept.append(e)
    return kept
