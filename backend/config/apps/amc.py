"""
Configurazione AMC (app-specific).

Separata da `config/settings.py` per evitare mixing tra config generiche e per-app.
"""

from __future__ import annotations

import os


class AMCConfig:
    """Configurazione per test login AMC"""

    URL = os.getenv("AMC_URL", "https://amc.eng.it/multimodule/web/")
    USERNAME = os.getenv("AMC_USERNAME", "")
    PASSWORD = os.getenv("AMC_PASSWORD", "")

    @classmethod
    def validate(cls) -> bool:
        return bool(cls.USERNAME and cls.PASSWORD)

