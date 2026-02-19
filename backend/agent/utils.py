"""
Utility generiche (serializzazione, formattazione, parsing, export grafo).
Nessuna logica di valutazione run: per pass/fail e interpretazione eventi → evaluation.py.
"""
import json
import re
from typing import Any, Optional


# ---------- Serializzazione JSON (response API) ----------

def make_json_serializable(obj: Any) -> Any:
    """Converte un oggetto in forma JSON-serializable (evita 500 su response)."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [make_json_serializable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): make_json_serializable(v) for k, v in obj.items()}
    return str(obj)


# ---------- Formattazione log tool (input/output) ----------

TOOL_IO_MAX_LEN = 800


def format_tool_io(value: Any, max_len: int = TOOL_IO_MAX_LEN) -> str:
    """Formatta input o output di un tool per log (troncato se troppo lungo)."""
    if value is None:
        return ""
    if isinstance(value, str):
        s = value
    elif isinstance(value, (dict, list)):
        try:
            s = json.dumps(value, ensure_ascii=False)
        except Exception:
            s = repr(value)
    else:
        s = repr(value)
    if len(s) > max_len:
        return s[:max_len] + f" ... ({len(s)} chars)"
    return s


# ---------- Estrazione / parsing ----------

def extract_final_json(text: str) -> Optional[dict]:
    """
    Estrae l'ultimo JSON valido presente in un testo.
    Usato per leggere il report finale dell'agent.
    """
    if not text:
        return None

    # prende l'ultimo blocco {...} nel testo
    matches = re.findall(r"\{.*\}", text, flags=re.DOTALL)
    if not matches:
        return None

    candidate = matches[-1].strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None
    
def safe_json_loads(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None


def export_agent_graph(agent, base_path: str = ".") -> None:
    """Esporta visualizzazione LangGraph (mermaid, ascii, png). Fallisce in silenzio."""
    try:
        g = agent.get_graph(xray=True)
        mermaid = g.draw_mermaid()
        with open(f"{base_path}/langgraph.mmd", "w", encoding="utf-8") as f:
            f.write(mermaid)
        with open(f"{base_path}/langgraph.txt", "w", encoding="utf-8") as f:
            f.write(g.draw_ascii())
        png_bytes = g.draw_mermaid_png()
        with open(f"{base_path}/langgraph.png", "wb") as f:
            f.write(png_bytes)
        print(" LangGraph exported: langgraph.mmd / langgraph.txt / langgraph.png")
    except Exception as e:
        print(f" Unable to export LangGraph visualization: {e}")
