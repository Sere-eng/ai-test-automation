# backend/mcp_servers/playwright_server_remote.py
"""
MCP Server per Playwright Tools - ASYNC Version
Comunicazione HTTP (remoto) compatibile con asyncio
"""

import sys
import os
from typing import Dict, List
from dotenv import load_dotenv

# Aggiungi la cartella backend al path PRIMA di importare i moduli
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Ora possiamo importare i moduli locali
from config.settings import AppConfig
from agent.tools import PlaywrightTools
import json
from mcp.server.fastmcp import FastMCP
from tool_names import TOOL_NAMES


def to_json(result: dict) -> str:
    """
    Converte il risultato di PlaywrightTools in JSON string.
    Garantisce output strutturato per MCP.
    """
    return json.dumps(result, indent=2, ensure_ascii=False)


# Crea il server MCP con porta HTTP
mcp = FastMCP(
    "PlaywrightTools",
    host=AppConfig.MCP.REMOTE_HOST,
    port=AppConfig.MCP.REMOTE_PORT
)

# Istanza globale dei tool Playwright
playwright = PlaywrightTools()


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
    result = await playwright.click_element(selector, selector_type, timeout)
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
async def inspect_interactive_elements() -> str:
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
    
    Example output:
        {
          "iframes": [{"src": "https://amc.eng.it/ui/registry/...", "selector": "iframe[src*='registry']"}],
          "clickable_elements": [
            {"role": "button", "accessible_name": "Causali", "text": "Causali",
             "playwright_suggestions": [{"strategy": "role", "click_smart": {"by": "role", "role": "button", "name": "Causali"}}]}
          ],
          "form_fields": [
            {"type": "password", "accessible_name": "Password", "placeholder": "Password",
             "playwright_suggestions": [{"strategy": "label", "fill_smart": {"by": "label", "label": "Password"}}]}
          ]
        }
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


@mcp.tool()
async def click_smart(targets: List[Dict[str, str]], timeout_per_try: int = 2000) -> str:
    """
    Click usando strategie multiple (fallback chain) - robusto per DOM complessi enterprise.

    Args:
        targets: Lista strategie da provare in ordine, es:
            [{"by": "role", "role": "button", "name": "Micrologistica"},
             {"by": "text", "text": "Micrologistica"},
             {"by": "tfa", "tfa": "radPageMenuItem:Micrologistica"}]
        timeout_per_try: Timeout per ogni tentativo in ms (default: 2000)

    Strategie disponibili (ordine consigliato):
        - role: getByRole (WCAG, più robusto)
        - label: getByLabel (form fields)
        - placeholder: getByPlaceholder
        - text: getByText
        - tfa: data-tfa attribute
        - css: CSS selector (fallback)
        - xpath: XPath (last resort)

    Returns: JSON con status, strategia usata, target

    Example (AMC Micrologistica):
        [{"by": "role", "role": "button", "name": "Micrologistica"},
         {"by": "text", "text": "Micrologistica"}]
    """
    result = await playwright.click_smart(targets=targets, timeout_per_try=timeout_per_try)
    return to_json(result)


@mcp.tool()
async def fill_smart(targets: list[dict], value: str, timeout_per_try: int = 2000) -> str:
    """
    Fill input usando strategie multiple (fallback chain) - robusto per DOM complessi.

    Args:
        targets: Lista strategie (stesso formato click_smart)
        value: Valore da inserire
        timeout_per_try: Timeout per tentativo in ms

    Returns: JSON con status, strategia usata

    Example (AMC Username):
        [{"by": "label", "label": "Username"},
         {"by": "placeholder", "placeholder": "Username"},
         {"by": "role", "role": "textbox", "name": "Username"}]
    """
    print(f"\n [MCP] fill_smart called:")
    print(f"   Targets: {targets}")
    print(f"   Value: {'*' * len(value) if value else 'empty'}")
    print(f"   Timeout: {timeout_per_try}ms")
    
    result = await playwright.fill_smart(targets=targets, value=value, timeout_per_try=timeout_per_try)
    
    print(f"   Result: {result.get('status')} - {result.get('message', 'N/A')}")
    if result.get('status') == 'success':
        print(f"   Used strategy: {result.get('strategy', 'N/A')}")
    
    return to_json(result)


@mcp.tool()
async def wait_for_text_content(text: str, timeout: int = 30000, case_sensitive: bool = False) -> str:
    """
    Aspetta che un testo specifico appaia OVUNQUE nella pagina.
    Utile per verificare caricamenti AJAX, messaggi success/error, titoli sezioni.
    
    Args:
        text: Testo da cercare nella pagina
        timeout: Timeout in ms (default: 30000)
        case_sensitive: Se True, match esatto case-sensitive (default: False)
    
    Returns:
        JSON con status e dettagli testo trovato
    
    Use case:
        - Verifica dopo login: aspetta "Welcome" o nome utente
        - Verifica dopo submit: aspetta messaggio "Saved successfully"
        - Verifica navigazione: aspetta titolo sezione "Micrologistica - Dashboard"
    
    Example workflow:
        click_smart([{"by": "role", "role": "button", "name": "Login"}])
        wait_for_text_content("Dashboard", timeout=10000)
        # Se passa -> login OK, se timeout -> login failed
    """
    result = await playwright.wait_for_text_content(text=text, timeout=timeout, case_sensitive=case_sensitive)
    return to_json(result)


# @mcp.tool()  # DEBUG ONLY - disabilitato per evitare confusione AI
async def inspect_dom_changes(click_target: dict, wait_after_click: int = 2000) -> str:
    """
    Ispeziona cosa cambia nel DOM dopo un click (diagnostico).
    Mostra nuovi elementi, elementi rimossi, menu/popup aperti.
    
    Args:
        click_target: Target da cliccare (formato click_smart), es: {"by": "text", "text": "Micrologistica"}
        wait_after_click: Millisecondi da aspettare dopo click (default: 2000)
    
    Returns:
        JSON con:
        - elements_added: nuovi elementi interattivi apparsi (button, link, menu)
        - elements_removed: elementi scomparsi
        - recommendations: suggerimenti su cosa fare dopo (es: "clicca su submenu item X")
    
    Use case:
        - Debug: scoprire perché un click non fa quello che ti aspetti
        - Capire se si apre un menu/submenu/popup
        - Trovare il prossimo elemento da cliccare
    
    Example workflow:
        # Invece di:
        click_smart([{"by": "text", "text": "Micrologistica"}])
        # Non so cosa succede...
        
        # Usa:
        result = inspect_dom_changes(
            click_target={"by": "text", "text": "Micrologistica"},
            wait_after_click=3000
        )
        # Output: "Rilevato submenu con 3 item: ['Dashboard', 'Richieste', 'Movimenti']"
        # -> Ora sai che devi cliccare su "Dashboard"!
    """
    result = await playwright.inspect_dom_changes(click_target=click_target, wait_after_click=wait_after_click)
    return to_json(result)


@mcp.tool()
async def get_frame(selector: str = None, url_pattern: str = None, timeout: int = 10000) -> str:
    """
    Accede al contenuto di un iframe per interagire con elementi al suo interno.
    Risolve il problema delle pagine dentro iframe (es: Gestione Causali in AMC).
    
    Args:
        selector: CSS selector dell'iframe (es: 'iframe[src*="movementreason"]')
        url_pattern: Pattern URL dell'iframe (alternativa, es: "registry/movementreason")
        timeout: Timeout in ms (default: 10000)
    
    Returns:
        JSON con metadata del frame (serializzabile). Per interagire dentro iframe, usa fill_and_search(in_iframe=...).
    
    Example:
        # Problema: campo input non trovato perché è dentro iframe
        # Soluzione:
        frame = get_frame(url_pattern="movementreason")
        fill_and_search(
            input_selector="input[type='text']",
            search_value="carm",
            in_iframe={"url_pattern": "movementreason"}
        )
    """
    result = await playwright.get_frame(selector=selector, url_pattern=url_pattern, timeout=timeout)
    return to_json(result)


@mcp.tool()
async def fill_and_search(
    input_selector: str,
    search_value: str,
    verify_result_text: str = None,
    in_iframe: dict = None
) -> str:
    """
    Riempie campo input e verifica risultati (approccio procedurale).
    Supporta iframe automaticamente - ideale per ricerche in griglie.
    
    Args:
        input_selector: Selettore del campo input (es: "input[type='text']")
        search_value: Valore da cercare (es: "carm")
        verify_result_text: Testo atteso nei risultati (es: "CARMAG")
        in_iframe: {"selector": "..."} o {"url_pattern": "..."} se in iframe
    
    Returns:
        JSON con status e count risultati
    
    Example:
        # Ricerca in pagina normale:
        fill_and_search(
            input_selector="input[name='search']",
            search_value="test",
            verify_result_text="TEST-001"
        )
        
        # Ricerca in iframe:
        fill_and_search(
            input_selector="input[type='text']",
            search_value="carm",
            verify_result_text="CARMAG",
            in_iframe={"url_pattern": "movementreason"}
        )
    """
    result = await playwright.fill_and_search(
        input_selector=input_selector,
        search_value=search_value,
        verify_result_text=verify_result_text,
        in_iframe=in_iframe
    )
    return to_json(result)


# =========================
# Avvia il server MCP su HTTP
# =========================

if __name__ == "__main__":
    port = AppConfig.MCP.REMOTE_PORT
    host = AppConfig.MCP.REMOTE_HOST

    print("=" * 80)
    print("  MCP Playwright Server (HTTP transport) - ASYNC Version")
    print("=" * 80)
    print(f"  Server URL: http://{host}:{port}/mcp/")
    print(f"  Tool disponibili: {len(TOOL_NAMES)}")
    print("  Tool list:")
    for name in TOOL_NAMES:
        print(f"   - {name}")
    print(f"  Per usarlo dall'agent, configura in config/settings.py:")
    print(f'  MCPConfig.MODE = "remote"')
    print(f'  MCPConfig.REMOTE_PORT = {port}')
    print("=" * 80)
    print("Premi CTRL+C per fermare il server")
    print("=" * 80)

    # run() senza parametri - tutto è già in __init__
    mcp.run(transport="streamable-http")
