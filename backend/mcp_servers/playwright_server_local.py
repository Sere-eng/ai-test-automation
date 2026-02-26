# backend/mcp_servers/playwright_server_local.py
"""
MCP Server per Playwright Tools - ASYNC Version (LOCAL)
Trasporto: stdio (subprocess)
Output: JSON string uniforme per tutti i tool
"""

import json
import sys
import os
from typing import Dict, List
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from tool_names import TOOL_NAMES

load_dotenv()

# Permette import da backend/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools import PlaywrightTools  # noqa: E402
from config.settings import AppConfig    # noqa: E402

# MCP server (stdio)
mcp = FastMCP("PlaywrightTools")

# Istanza globale tool Playwright (stato condiviso nella sessione MCP)
playwright = PlaywrightTools()


def to_json(result: dict) -> str:
    """Standard output: sempre JSON string."""
    return json.dumps(result, indent=2, ensure_ascii=False)


# =========================
# Tool base browser
# =========================

@mcp.tool()
async def start_browser(headless: bool = False) -> str:
    """Avvia browser Chromium."""
    result = await playwright.start_browser(headless=headless)
    return to_json(result)


@mcp.tool()
async def navigate_to_url(url: str) -> str:
    """Naviga verso un URL e aspetta il caricamento."""
    result = await playwright.navigate_to_url(url)
    return to_json(result)


@mcp.tool()
async def wait_for_load_state(state: str = "domcontentloaded", timeout: int = 30000) -> str:
    """Attende un load state Playwright (load/domcontentloaded/networkidle)."""
    result = await playwright.wait_for_load_state(state=state, timeout=timeout)
    return to_json(result)


@mcp.tool()
async def capture_screenshot(filename: str = None, return_base64: bool = False) -> str:
    """
    Cattura screenshot full-page.
    Se return_base64=True include base64 nel JSON (attenzione ai token).
    """
    result = await playwright.capture_screenshot(filename=filename, return_base64=return_base64)
    return to_json(result)


@mcp.tool()
async def close_browser() -> str:
    """Chiude il browser e libera risorse."""
    result = await playwright.close_browser()
    return to_json(result)


@mcp.tool()
async def get_page_info() -> str:
    """Ritorna info sulla pagina corrente (url, title, viewport)."""
    result = await playwright.get_page_info()
    return to_json(result)


# =========================
# Tool interazione pagina
# =========================

@mcp.tool()
async def wait_for_element_state(
    targets: List[Dict],
    state: str = "visible",
    timeout: int | None = None,
    in_iframe: dict | None = None,
) -> str:
    """
    Attende che un elemento individuato tramite SMART TARGETS raggiunga uno stato logico.

    - Usa la stessa semantica di targets di click_smart/fill_smart (role, label, placeholder, css, tfa, xpath).
    - Stati supportati:
        - Playwright nativi: "visible", "hidden", "attached", "detached"
        - Logici: "enabled", "disabled" (polling su is_enabled()).
    """
    result = await playwright.wait_for_element_state(
        targets=targets,
        state=state,
        timeout=timeout,
        in_iframe=in_iframe,
    )
    return to_json(result)


@mcp.tool()
async def get_text(selector: str, selector_type: str = "css") -> str:
    """Estrae testo da elemento."""
    result = await playwright.get_text(selector=selector, selector_type=selector_type)
    return to_json(result)


@mcp.tool()
async def press_key(key: str) -> str:
    """Premi un tasto (Enter/Escape/etc.)."""
    result = await playwright.press_key(key=key)
    return to_json(result)


@mcp.tool()
async def wait_for_clickable_by_name(name_substring: str, timeout: int = None, case_insensitive: bool = True) -> str:
    """Attende un elemento cliccabile il cui nome contiene name_substring (usa inspect)."""
    result = await playwright.wait_for_clickable_by_name(name_substring=name_substring, timeout=timeout, case_insensitive=case_insensitive)
    return to_json(result)


@mcp.tool()
async def wait_for_field_by_name(name_substring: str, timeout: int = None, case_insensitive: bool = True) -> str:
    """Attende un campo form il cui nome/placeholder contiene name_substring (usa inspect)."""
    result = await playwright.wait_for_field_by_name(name_substring=name_substring, timeout=timeout, case_insensitive=case_insensitive)
    return to_json(result)


@mcp.tool()
async def wait_for_control_by_name_and_type(name_substring: str, control_type: str, timeout: int = None, case_insensitive: bool = True) -> str:
    """Attende un controllo (es. combobox) con nome e tipo (usa inspect)."""
    result = await playwright.wait_for_control_by_name_and_type(name_substring=name_substring, control_type=control_type, timeout=timeout, case_insensitive=case_insensitive)
    return to_json(result)


# =========================
# Tool avanzati
# =========================

@mcp.tool()
async def inspect_interactive_elements(in_iframe: dict | None = None) -> str:
    """
    Scansiona TUTTI gli elementi interattivi usando solo standard web (NO attributi custom).
    Trova: iframe, button, link, input, select, textarea + ARIA roles.
    Output: JSON con iframes, clickable_elements, form_fields + accessibility info inline.

    Use case principale:
        - Scoprire struttura pagina sconosciuta
        - Trovare selettori robusti per login/navigation
        - Identificare iframe (per get_frame)

    Cosa cerca (SOLO STANDARD):
        1. Iframe: src, title, name
        2. Clickable: button, a, [role=button/link/menuitem]
        3. Form fields: input, select, textarea

    Per ogni elemento estrae:
        - accessible_name (WCAG)
        - role (ARIA/semantic)
        - aria-label
        - testo visibile
        - playwright_suggestions: locator pronti per click_smart/fill_smart

    IGNORA: data-*, ng-*, class names (instabili)

    Returns:
        JSON con:
        - iframes: [{src, title, selector}]
        - clickable_elements: [{role, accessible_name, text, playwright_suggestions}]
        - form_fields: [{type, accessible_name, placeholder, playwright_suggestions}]
    """
    result = await playwright.inspect_interactive_elements(in_iframe=in_iframe)
    return to_json(result)


@mcp.tool()
async def inspect_region(root_selector: str, in_iframe: dict | None = None) -> str:
    """
    Ispeziona SOLO una regione della pagina, identificata da root_selector (CSS).

    Restituisce clickable_elements, interactive_controls e form_fields limitati all'interno
    del contenitore, con la stessa struttura di inspect_interactive_elements.
    """
    result = await playwright.inspect_region(root_selector=root_selector, in_iframe=in_iframe)
    return to_json(result)


@mcp.tool()
async def handle_cookie_banner(strategies: list[str] | None = None, timeout: int = 5000) -> str:
    """
    Gestisce cookie banner con strategie multiple.
    Output: JSON con strategia usata e selector cliccato (se trovato).
    """
    result = await playwright.handle_cookie_banner(strategies=strategies, timeout=timeout)
    return to_json(result)


@mcp.tool()
async def wait_for_dom_change(
    root_selector: str = "body",
    timeout: int | None = None,
    attributes: bool = True,
    child_list: bool = True,
    subtree: bool = True,
    attribute_filter: list[str] | None = None,
    in_iframe: dict | None = None,
) -> str:
    """
    Attende il primo cambiamento DOM (MutationObserver) sotto un contenitore.

    Use-case tipico:
    - dopo un click critico (es. "Aggiungi filtro"), usa wait_for_dom_change(root_selector="<card selector>")
      per sapere quando la card/modal ha cambiato struttura, poi chiama inspect_region(root_selector)
      per scoprire i nuovi controlli senza re-ispezionare l'intera pagina.
    """
    result = await playwright.wait_for_dom_change(
        root_selector=root_selector,
        timeout=timeout,
        attributes=attributes,
        child_list=child_list,
        subtree=subtree,
        attribute_filter=attribute_filter,
        in_iframe=in_iframe,
    )
    return to_json(result)


@mcp.tool()
async def click_smart(targets: List[Dict[str, str]], timeout_per_try: int = 8000, in_iframe: dict = None) -> str:
    """
    Click elemento con FALLBACK CHAIN automatico - prova tutte le strategie fino al successo.
    Resilienza massima: role fallisce su duplicato? Prova css_aria. css_aria manca? Prova text.
    Supporta interazioni dentro iframe (app Angular embedded).

    Args:
        targets: Lista strategie ordinate per robustezza (da inspect_interactive_elements), es:
            [{"by": "role", "role": "button", "name": "Login"},
             {"by": "css", "selector": "[aria-label='Login']"},
             {"by": "text", "text": "Login"}]
        timeout_per_try: Timeout per ogni tentativo in ms (default: 8000)
        in_iframe: dict per iframe (singolo o annidati)
            - Singolo: {"selector": "..."} o {"url_pattern": "..."}
            - Annidati: {"iframe_path": [{"url_pattern": "..."}, {"selector": "..."}]}

    Best practice: Usa inspect_interactive_elements() e copia TUTTE le strategie da playwright_suggestions.
    """
    result = await playwright.click_smart(targets=targets, timeout_per_try=timeout_per_try, in_iframe=in_iframe)
    return to_json(result)


@mcp.tool()
async def fill_smart(targets: list[dict], value: str, timeout_per_try: int = 8000, in_iframe: dict = None) -> str:
    """
    Fill input con FALLBACK CHAIN automatico - prova tutte le strategie fino al successo.
    Resilienza massima: label manca? Prova placeholder. Placeholder vuoto? Prova role.
    Supporta interazioni dentro iframe (app Angular embedded).

    Args:
        targets: Lista strategie ordinate per robustezza (da inspect_interactive_elements), es:
            [{"by": "label", "label": "Username"},
             {"by": "placeholder", "placeholder": "Enter username"},
             {"by": "role", "role": "textbox", "name": "Username"}]
        value: Valore da inserire
        timeout_per_try: Timeout per ogni tentativo in ms (default: 8000)
        in_iframe: dict per iframe (singolo o annidati)
            - Singolo: {"selector": "..."} o {"url_pattern": "..."}
            - Annidati: {"iframe_path": [{"url_pattern": "..."}, {"selector": "..."}]}

    Best practice: Usa inspect_interactive_elements() e copia TUTTE le strategie da playwright_suggestions.
    """
    result = await playwright.fill_smart(targets=targets, value=value, timeout_per_try=timeout_per_try, in_iframe=in_iframe)
    return to_json(result)


@mcp.tool()
async def wait_for_text_content(text: str, timeout: int = 30000, case_sensitive: bool = False, in_iframe: dict = None) -> str:
    """
    Attende che un testo appaia nel DOM (pagina principale o iframe).
    Utile per verificare stato della pagina dopo azioni o risultati search in iframe.

    Args:
        in_iframe: {"url_pattern": "..."} per cercare dentro iframe

    Example (iframe):
        wait_for_text_content(
            "CARMAG",
            timeout=5000,
            in_iframe={"url_pattern": "movementreason"}
        )
    """
    result = await playwright.wait_for_text_content(text=text, timeout=timeout, case_sensitive=case_sensitive, in_iframe=in_iframe)
    return to_json(result)


@mcp.tool()
async def click_and_wait_for_text(
    targets: list[dict] | None = None,
    text: str = "",
    timeout_per_try: int = 8000,
    text_timeout: int = 30000,
    in_iframe: dict = None,
) -> str:
    """Combina click_smart + wait_for_text_content. Se targets vuoto, solo wait_for_text_content."""
    if not targets:
        result = await playwright.wait_for_text_content(text=text, timeout=text_timeout, case_sensitive=False, in_iframe=in_iframe)
        return to_json({"status": result.get("status"), "message": result.get("message"), "click": None, "text_check": result, "fallback_mode": "wait_for_text_content_only"})
    result = await playwright.click_and_wait_for_text(targets=targets, text=text, timeout_per_try=timeout_per_try, text_timeout=text_timeout, in_iframe=in_iframe)
    return to_json(result)


@mcp.tool()
async def get_frame(selector: str = None, url_pattern: str = None, iframe_path: list = None, timeout: int = 10000) -> str:
    """
    Accesso semplificato a iframe (singolo o annidati).
    Per interagire dentro iframe, usa click_smart/fill_smart con in_iframe parameter.

    Args:
        selector: CSS selector dell'iframe
        url_pattern: Pattern URL dell'iframe (alternativa a selector)
        iframe_path: Lista di dict per iframe annidati
        timeout: Timeout in ms per ogni livello (default: 10000)

    Example (iframe singolo):
        get_frame(url_pattern="movementreason")
        fill_smart(targets=[...], value="carm", in_iframe={"url_pattern": "movementreason"})

    Example (iframe annidati):
        get_frame(iframe_path=[{"url_pattern": "dashboard"}, {"selector": "iframe#widget"}])
    """
    result = await playwright.get_frame(selector=selector, url_pattern=url_pattern, iframe_path=iframe_path, timeout=timeout)
    return to_json(result)


# =========================
# Avvio (stdio)
# =========================

if __name__ == "__main__":
    print("=" * 80)
    print("  MCP Playwright Server (STDIO) - ASYNC Version")
    print("=" * 80)
    print("  Transport: stdio")
    print(f"  MCP Mode (config): {AppConfig.MCP.MODE}")
    print(f"  Tool disponibili: {len(TOOL_NAMES)}")
    print("  Tool list:")
    for name in TOOL_NAMES:
        print(f"   - {name}")
    print("=" * 80)

    mcp.run(transport="stdio")