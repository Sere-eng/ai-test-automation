# backend/mcp_servers/playwright_server_local.py
"""
MCP Server per Playwright Tools - ASYNC Version (LOCAL)
Trasporto: stdio (subprocess)
Output: JSON string uniforme per tutti i tool
"""

import json
import sys
import os
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
async def click_element(selector: str, selector_type: str = "css", timeout: int = 30000) -> str:
    """Click su elemento."""
    result = await playwright.click_element(selector=selector, selector_type=selector_type, timeout=timeout)
    return to_json(result)


@mcp.tool()
async def fill_input(
    selector: str,
    value: str,
    selector_type: str = "css",
    clear_first: bool = True
) -> str:
    """Compila un input."""
    result = await playwright.fill_input(
        selector=selector,
        value=value,
        selector_type=selector_type,
        clear_first=clear_first
    )
    return to_json(result)


@mcp.tool()
async def wait_for_element(
    selector: str,
    state: str = "visible",
    selector_type: str = "css",
    timeout: int = 30000
) -> str:
    """Attende che un elemento diventi visible/hidden/attached/detached."""
    result = await playwright.wait_for_element(
        selector=selector,
        selector_type=selector_type,
        state=state,
        timeout=timeout
    )
    return to_json(result)


@mcp.tool()
async def get_text(selector: str, selector_type: str = "css") -> str:
    """Estrae testo da elemento."""
    result = await playwright.get_text(selector=selector, selector_type=selector_type)
    return to_json(result)


@mcp.tool()
async def check_element_exists(selector: str, selector_type: str = "css") -> str:
    """Verifica esistenza/visibilità di un elemento."""
    result = await playwright.check_element_exists(selector=selector, selector_type=selector_type)
    return to_json(result)


@mcp.tool()
async def press_key(key: str) -> str:
    """Premi un tasto (Enter/Escape/etc.)."""
    result = await playwright.press_key(key=key)
    return to_json(result)


# =========================
# Tool avanzati
# =========================

@mcp.tool()
async def inspect_interactive_elements(in_iframe: dict | None = None) -> str:
    """
    Ispeziona elementi interattivi (clickable, form fields, iframes).
    Genera strategie pronte per click_smart e fill_smart.
    """
    result = await playwright.inspect_interactive_elements(in_iframe=in_iframe)
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
async def click_smart(targets: list[dict], timeout_per_try: int = 2000) -> str:
    """
    Click enterprise con strategie multiple.
    Prova role → text → css_aria → tfa finché uno funziona.
    targets: [{"by": "role", "role": "button", "name": "Login"}, ...]
    """
    result = await playwright.click_smart(targets=targets, timeout_per_try=timeout_per_try)
    return to_json(result)


@mcp.tool()
async def fill_smart(targets: list[dict], value: str, timeout_per_try: int = 2000) -> str:
    """
    Fill enterprise con strategie multiple.
    Prova label → placeholder → role → css → tfa finché uno funziona.
    targets: [{"by": "label", "label": "Username"}, ...]
    """
    result = await playwright.fill_smart(targets=targets, value=value, timeout_per_try=timeout_per_try)
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


# @mcp.tool()  # DEBUG ONLY - disabilitato per evitare confusione AI
async def inspect_dom_changes(click_target: dict, wait_after_click: int = 2000) -> str:
    """
    Click su elemento e ispeziona cambiamenti DOM (elementi aggiunti/rimossi).
    Utile per debug di menu dinamici/modali.
    click_target: {"by": "role", "role": "button", "name": "Menu"}
    """
    result = await playwright.inspect_dom_changes(click_target=click_target, wait_after_click=wait_after_click)
    return to_json(result)


# =========================
# Tool procedurali (workflow complessi)
# =========================

@mcp.tool()
async def get_frame(selector: str = None, url_pattern: str = None, timeout: int = 10000) -> str:
    """
    Accesso semplificato a iframe.
    Usa selector CSS oppure url_pattern.
    Ritorna SOLO metadata serializzabile (non l'oggetto Frame).
    Per interagire dentro iframe, usa click_smart/fill_smart con in_iframe parameter.
    
    Example:
        frame = get_frame(url_pattern="movementreason")
        fill_smart(
            targets=[
                {"by": "placeholder", "placeholder": "Search"},
                {"by": "label", "label": "Search"}
            ],
            value="carm",
            in_iframe={"url_pattern": "movementreason"}
        )
    """
    result = await playwright.get_frame(selector=selector, url_pattern=url_pattern, timeout=timeout)
    return to_json(result)


# @mcp.tool()  # DEPRECATED - Use fill_smart + wait_for_text_content instead
async def fill_and_search(
    input_selector: str,
    search_value: str,
    verify_result_text: str = None,
    in_iframe: dict = None,
    timeout: int = 10000
) -> str:
    """
    ⚠️ DEPRECATED: Use fill_smart + wait_for_text_content instead.
    
    NEW RECOMMENDED WORKFLOW:
        fill_smart(targets=[...], value="carm", in_iframe={...})
        wait_for_text_content("CARMAG", timeout=5000)
    
    Kept for backward compatibility only.
    """
    result = await playwright.fill_and_search(
        input_selector=input_selector,
        search_value=search_value,
        verify_result_text=verify_result_text,
        in_iframe=in_iframe,
        timeout=timeout
    )
    return to_json(result)


@mcp.tool()
async def inspect_page_structure() -> str:
    """
    DEPRECATED: Usa inspect_interactive_elements() invece.
    Mantenu per compatibilità con codice legacy.
    """
    result = await playwright.inspect_interactive_elements()
    return to_json(result)


@mcp.tool()
async def handle_cookie_banner(strategies: list[str] | None = None, timeout: int = 5000) -> str:
    """
    Gestisce cookie banner con strategie multiple.
    Output: JSON con strategia usata e selector cliccato (se trovato).
    """
    result = await playwright.handle_cookie_banner(strategies=strategies, timeout=timeout)
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

    # Per stdio basta run() senza specificare transport (default stdio in FastMCP),
    # ma lo esplicitiamo per chiarezza.
    mcp.run(transport="stdio")
