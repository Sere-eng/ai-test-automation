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
