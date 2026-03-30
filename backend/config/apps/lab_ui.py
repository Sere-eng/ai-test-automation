"""
Configurazione UI LAB (frontend presets / labels).

Serve per evitare stringhe hardcoded in `static/index.html`.
"""

from __future__ import annotations

import json
import os
from typing import List, Dict


class LabUIConfig:
    """
    Configurazione UI specifica LAB usata dal frontend:
    - lista di tile/moduli disponibili sulla home dopo login ("Continua")

    Override tramite env:
      LAB_HOME_MODULE_PRESETS_JSON='[{"label":"Laboratorio Analisi","alt":"Clinical Laboratory"}, ...]'
    """

    _DEFAULT_HOME_MODULE_PRESETS: List[Dict[str, str]] = [
        {"label": "Laboratorio Analisi", "alt": "Clinical Laboratory"},
        {"label": "Tools", "alt": ""},
        {"label": "Sistema", "alt": ""},
        {"label": "Design System", "alt": ""},
        {"label": "Jobs Manager", "alt": ""},
        {"label": "Gestione report", "alt": ""},
        {"label": "Anagrafiche", "alt": ""},
        {"label": "UNITY - Clinical Data Manager", "alt": ""},
        {"label": "Decision Support System", "alt": ""},
        {"label": "Organigramma", "alt": ""},
        {"label": "RAD", "alt": ""},
        {"label": "Anagrafe Paziente", "alt": ""},
        {"label": "Configurazione Email", "alt": ""},
        {"label": "Gestione dei Parametri", "alt": ""},
        {"label": "BRIDGE", "alt": ""},
        {"label": "Audit", "alt": ""},
        {"label": "Gestione consensi", "alt": ""},
        {"label": "Configuratore per il Laboratorio Analisi", "alt": ""},
        {"label": "Gestore degli accessi", "alt": ""},
        {"label": "Dashboard PS", "alt": ""},
        {"label": "Telemedicina", "alt": ""},
    ]

    @classmethod
    def get_home_module_presets(cls) -> List[Dict[str, str]]:
        raw = os.getenv("LAB_HOME_MODULE_PRESETS_JSON", "").strip()
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    out: List[Dict[str, str]] = []
                    for item in parsed:
                        if not isinstance(item, dict):
                            continue
                        label = str(item.get("label", "")).strip()
                        alt = str(item.get("alt", "")).strip()
                        if label:
                            out.append({"label": label, "alt": alt})
                    if out:
                        return out
            except Exception:
                pass
        return list(cls._DEFAULT_HOME_MODULE_PRESETS)

