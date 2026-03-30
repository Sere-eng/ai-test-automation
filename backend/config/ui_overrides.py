"""
Configurazione UI-specific (override) per tool Playwright.

Obiettivo: mantenere `backend/agent/tools.py` generico (standard web/WCAG) e spostare
ogni selettore o comportamento dipendente da una UI/app specifica in un modulo di config.

Queste impostazioni possono essere estese via variabili d'ambiente (comma-separated).
"""

from __future__ import annotations

import os
from typing import Tuple


class UIOverridesConfig:
    """
    Override UI/app-specific per:
    - inspect_interactive_elements: selettori extra cliccabili (oltre a HTML/WCAG standard)
    - scroll_to_bottom: gestione wrapper noti che richiedono scroll su lista interna + footer
    """

    # Registro incrementale per inspect_interactive_elements / inspect_region:
    # blocchi custom (spesso div / web component) che il nucleo in tools.py non include.
    # Estendere quando una run fallisce la discovery; evitare .pointer globale fuori da inspect_region.
    # Nota: righe tabella (mat-row, tr in tbody, …) sono già gestite a parte in tools.py (pass 2b).
    _INSPECT_EXTRA_CLICKABLE_DEFAULTS: Tuple[str, ...] = (
        # UNITY – KPI circolari dashboard (solo contatori cliccabili)
        "div.circle-card.pointer",
        # Griglia tile home (app-home-activity); copre anche tile senza role="button" nel markup
        "div.home-app[tabindex='0']",
        # Stessa tile se usano tabindex vuoto esplicito
        'div.home-app[tabindex=""]',
        # Card contenitore con classi Angular dinamiche ma token circle-card stabile
        "div[class*='circle-card'].pointer",
        # Pannello espandibile Material (header cliccabile, spesso non è <button>)
        "mat-expansion-panel-header",
        # Voci menu/lista come link (nav / impostazioni)
        "a.mat-mdc-list-item",
        # Chip / opzioni filtro selezionabili (MDC)
        "mat-chip-option",
        # UNITY – Tab / card / pulsanti custom aggiuntivi usati nella UI
        "div.ds-tab-navigation-link-container",
        "div.ds-tab-navigation-link-text",
        "div.ds-tool-card-wrapper",
        "div.filter-wrapper.pointer",
        "div.ds-add-button-container",
    )

    # scroll_to_bottom: il selettore `.sample-table-container` compare due volte nel DOM (wrapper vs
    # contenitore interno). Se l’agent passa uno di questi alias, il tool scrolla la lista reale e
    # porta in vista il riepilogo righe in fondo pagina.
    _SCROLL_SAMPLE_TABLE_WRAPPER_ALIASES: Tuple[str, ...] = (
        ".sample-table-container",
        ".table.sample-table-container",
        "div.sample-table-container",
        "div.table.sample-table-container",
    )
    _SCROLL_SAMPLE_TABLE_LIST_LOCATOR: str = "sample-table div.search-results"
    _SCROLL_SAMPLE_TABLE_FOOTER_TEXT: str = "Totale righe visualizzate"

    # Scope detection (fill_smart): selettori di container "padre" utili per disambiguare
    # locator ambigui e generare locator scoped nel codegen. UI/framework-specific.
    _SCOPE_DETECTION_DEFAULTS: Tuple[str, ...] = (
        # --- Generici (HTML / ARIA) ---
        "form",
        "fieldset",
        "section",
        "main",
        "article",
        '[role="region"]',
        '[role="form"]',
        '[role="dialog"]',
        "dialog",
        # --- Già trovati in UI (Material / layout app) ---
        "card-group",
        "mat-card",
        ".mat-mdc-card",
        ".filter-group",
        '[role="group"]',
        ".mat-expansion-panel",
        "mat-expansion-panel",
    )

    @classmethod
    def is_scroll_sample_table_wrapper(cls, selector: str) -> bool:
        return selector.strip() in cls._SCROLL_SAMPLE_TABLE_WRAPPER_ALIASES

    @classmethod
    def get_scroll_sample_table_list_locator(cls) -> str:
        return cls._SCROLL_SAMPLE_TABLE_LIST_LOCATOR

    @classmethod
    def get_scroll_sample_table_footer_text(cls) -> str:
        return cls._SCROLL_SAMPLE_TABLE_FOOTER_TEXT

    @classmethod
    def get_inspect_extra_clickable_selectors(cls) -> Tuple[str, ...]:
        """
        Default del registro + valori aggiuntivi da .env (comma-separated).
        Esempio: INSPECT_EXTRA_CLICKABLE_SELECTORS=div.my-tile.pointer,tr.clickable-row
        """
        raw = os.getenv("INSPECT_EXTRA_CLICKABLE_SELECTORS", "").strip()
        env_extras = [p.strip() for p in raw.split(",") if p.strip()]
        seen: set[str] = set()
        merged: list[str] = []
        for s in list(cls._INSPECT_EXTRA_CLICKABLE_DEFAULTS) + env_extras:
            if s not in seen:
                seen.add(s)
                merged.append(s)
        return tuple(merged)

    @classmethod
    def get_scope_detection_selectors(cls) -> Tuple[str, ...]:
        """
        Default + override da .env (comma-separated).
        Esempio: SCOPE_DETECTION_SELECTORS=form,fieldset,section,[role="region"]
        """
        raw = os.getenv("SCOPE_DETECTION_SELECTORS", "").strip()
        env_extras = [p.strip() for p in raw.split(",") if p.strip()]
        seen: set[str] = set()
        merged: list[str] = []
        for s in list(cls._SCOPE_DETECTION_DEFAULTS) + env_extras:
            if s not in seen:
                seen.add(s)
                merged.append(s)
        return tuple(merged)

