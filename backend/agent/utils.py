import json
import re
from typing import Optional

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
