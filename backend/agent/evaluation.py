# backend/agent/evaluation.py
"""
Logica di valutazione run: parsing eventi stream, pass/fail da tool results.
Usa agent.utils per funzioni generiche (es. safe_json_loads); non sovrappone utils.
"""
from typing import Any, Optional

from agent.utils import safe_json_loads


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
        # oggetto non message: non salvare il repr, solo un placeholder
        return {"_raw_type": type(raw).__name__, "_note": "output was not string or message"}
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
    """Se output ha status=error, restituisce il dict errore."""
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
    """
    errors_out = list(errors)

    # TOLLERANZA: se l'ULTIMO uso di alcuni action tool (es. click_smart/fill_smart)
    # è andato in success, ignoriamo gli errori precedenti di quel tool.
    # Esempio tipico: primo click_smart fallisce, il secondo sullo stesso bottone va in success.
    last_status_by_tool: dict[str, str] = {}
    for s in steps:
        tool = s.get("tool")
        out = s.get("output")
        if not isinstance(out, dict):
            continue
        status = out.get("status")
        if status in ("success", "error") and tool:
            last_status_by_tool[tool] = status

    tolerant_tools = {"click_smart", "fill_smart"}
    for t in tolerant_tools:
        if last_status_by_tool.get(t) == "success":
            errors_out = [e for e in errors_out if e.get("tool") != t]

    passed = len(errors_out) == 0

    return passed, errors_out

