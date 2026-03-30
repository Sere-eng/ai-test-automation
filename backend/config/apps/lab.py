"""
Configurazione LAB (app-specific).

Separata da `config/settings.py` per mantenere i moduli per dominio/app isolati.
"""

from __future__ import annotations

import os


class LABConfig:
    """Configurazione per test Laboratory / Clinical Laboratory"""

    URL = os.getenv(
        "LAB_URL",
        "https://mdrsanitalab2.eng.it/multimodule/ELLIPSE_LAB/?ENGAPPCONFIGS=%7B%22ENG_APP_DISABLE_DATA_PROFILER%22%3Atrue%2C%22ENG_APP_DISABLE_ACTIVITY_PROFILER%22%3Atrue%2C%22ENG_APP_DISABLE_MENU_PROFILER%22%3Atrue%7D",
    )
    USERNAME = os.getenv("LAB_USERNAME", "")
    PASSWORD = os.getenv("LAB_PASSWORD", "")

    @classmethod
    def validate(cls) -> bool:
        # Facoltativo: le credenziali LAB potrebbero non essere sempre configurate
        return bool(cls.USERNAME and cls.PASSWORD)

