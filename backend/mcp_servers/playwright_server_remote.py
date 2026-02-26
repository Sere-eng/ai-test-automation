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
    """Attende che compaia un elemento cliccabile il cui nome contiene name_substring (usa inspect)."""
    result = await playwright.wait_for_clickable_by_name(name_substring=name_substring, timeout=timeout, case_insensitive=case_insensitive)
    return to_json(result)


@mcp.tool()
async def wait_for_field_by_name(name_substring: str, timeout: int = None, case_insensitive: bool = True) -> str:
    """Attende che compaia un campo form il cui nome/placeholder contiene name_substring (usa inspect)."""
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

    Strategie disponibili (ordine consigliato per AMC/Angular Material):
        - role: {"by": "role", "role": "button", "name": "Login"} ← WCAG (most robust, disambiguates duplicates)
        - css_aria: {"by": "css", "selector": "[aria-label='Submit']"} ← Fallback for Angular icons
        - text: {"by": "text", "text": "Click me"}
        - tfa: {"by": "tfa", "tfa": "submit_btn"} ← Test IDs (possono cambiare)
        - label: {"by": "label", "label": "Username"} (solo form fields)
        - placeholder: {"by": "placeholder", "placeholder": "Enter email"}
        - xpath: {"by": "xpath", "xpath": "//button"} ← Last resort

    Returns: JSON con status, strategia usata, strategie provate, se fallback usato

    Example (pagina principale):
        [{"by": "role", "role": "button", "name": "Micrologistica"},
         {"by": "css", "selector": "[aria-label='Micrologistica']"},
         {"by": "text", "text": "Micrologistica"}]
        # Tool tries role → if fails tries css_aria → if fails tries text
    
    Example (dentro iframe singolo AMC Causali):
        click_smart(
            targets=[{"by": "role", "role": "button", "name": "Save"}],
            in_iframe={"url_pattern": "movementreason"}
        )
    
    Example (iframe annidati - dashboard → widget → form):
        click_smart(
            targets=[{"by": "role", "role": "button", "name": "Submit"}],
            in_iframe={"iframe_path": [
                {"url_pattern": "dashboard"},
                {"selector": "iframe#payment-widget"}
            ]}
        )
    
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

    Strategie disponibili (ordine consigliato per form fields):
        - label: {"by": "label", "label": "Username"} ← Più affidabile
        - placeholder: {"by": "placeholder", "placeholder": "Enter email"}
        - role: {"by": "role", "role": "textbox", "name": "Search"}
        - css_name: {"by": "css", "selector": "[name='email']"}
        - css_id: {"by": "css", "selector": "#username"}
        - css_aria: {"by": "css", "selector": "[aria-label='Email']"}
        - tfa: {"by": "tfa", "tfa": "login_email"} ← Test IDs (possono cambiare)

    Returns: JSON con status, strategia usata, strategie provate, se fallback usato

    Example (pagina principale):
        [{"by": "label", "label": "Username"},
         {"by": "placeholder", "placeholder": "Enter username"}]
        # Tool tries label → if fails tries placeholder
    
    Example (dentro iframe singolo AMC Causali):
        fill_smart(
            targets=[{"by": "label", "label": "Codice"}],
            value="CARM",
            in_iframe={"url_pattern": "movementreason"}
        )
    
    Example (iframe annidati - portal → dashboard → search):
        fill_smart(
            targets=[{"by": "label", "label": "Search"}],
            value="Product",
            in_iframe={"iframe_path": [
                {"url_pattern": "portal"},
                {"selector": "iframe.dashboard"}
            ]}
        )
    
    Best practice: Usa inspect_interactive_elements() e copia TUTTE le strategie da playwright_suggestions.
    """
    print(f"\n [MCP] fill_smart called:")
    print(f"   Targets: {targets}")
    print(f"   Value: {'*' * len(value) if value else 'empty'}")
    print(f"   Timeout: {timeout_per_try}ms")
    print(f"   In iframe: {in_iframe}")
    
    result = await playwright.fill_smart(targets=targets, value=value, timeout_per_try=timeout_per_try, in_iframe=in_iframe)
    
    print(f"   Result: {result.get('status')} - {result.get('message', 'N/A')}")
    if result.get('status') == 'success':
        print(f"   Used strategy: {result.get('strategy', 'N/A')}")
    
    return to_json(result)


@mcp.tool()
async def wait_for_text_content(text: str, timeout: int = 30000, case_sensitive: bool = False, in_iframe: dict = None) -> str:
    """
    Aspetta che un testo specifico appaia OVUNQUE nella pagina o dentro un iframe.
    Utile per verificare caricamenti AJAX, messaggi success/error, risultati search in iframe.
    
    Args:
        text: Testo da cercare nella pagina
        timeout: Timeout in ms (default: 30000)
        case_sensitive: Se True, match esatto case-sensitive (default: False)
        in_iframe: Dict per cercare dentro iframe (opzionale)
            {"url_pattern": "movementreason"} - iframe singolo
            {"iframe_path": [{...}, {...}]} - iframe annidati
    
    Returns:
        JSON con status e dettagli testo trovato
    
    Use case:
        - Verifica dopo login: aspetta "Welcome" (pagina principale)
        - Verifica dopo search in iframe Causali: aspetta "CARMAG" DENTRO iframe
        - Verifica navigazione: aspetta titolo sezione
    
    Example (main page):
        click_smart([{"by": "role", "role": "button", "name": "Login"}])
        wait_for_text_content("Dashboard", timeout=10000)
    
    Example (iframe - Causali search):
        fill_smart(
            targets=[{"by": "placeholder", "placeholder": "Cerca"}],
            value="carm",
            in_iframe={"url_pattern": "movementreason"}
        )
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
    """
    Combina click_smart + wait_for_text_content. Per step critici (login, Continua, moduli).
    Se targets è vuoto, esegue solo wait_for_text_content(text).
    """
    if not targets:
        result = await playwright.wait_for_text_content(text=text, timeout=text_timeout, case_sensitive=False, in_iframe=in_iframe)
        return to_json({"status": result.get("status"), "message": result.get("message"), "click": None, "text_check": result, "fallback_mode": "wait_for_text_content_only"})
    result = await playwright.click_and_wait_for_text(targets=targets, text=text, timeout_per_try=timeout_per_try, text_timeout=text_timeout, in_iframe=in_iframe)
    return to_json(result)


@mcp.tool()
async def get_frame(selector: str = None, url_pattern: str = None, iframe_path: list = None, timeout: int = 10000) -> str:
    """
    Accede al contenuto di un iframe (singolo o annidati) per interagire con elementi al suo interno.
    Risolve il problema delle pagine dentro iframe (es: Gestione Causali in AMC).
    
    Args:
        selector: CSS selector dell'iframe (es: 'iframe[src*="movementreason"]')
        url_pattern: Pattern URL dell'iframe (alternativa, es: "registry/movementreason")
        iframe_path: Lista di dict per iframe annidati (es: [{"url_pattern": "dashboard"}, {"selector": "iframe#widget"}])
        timeout: Timeout in ms per ogni livello (default: 10000)
    
    Returns:
        JSON con metadata del frame (serializzabile). Per interagire dentro iframe, usa 
        click_smart/fill_smart con in_iframe parameter.
    
    Example (iframe singolo):
        frame = get_frame(url_pattern="movementreason")
        fill_smart(
            targets=[
                {"by": "placeholder", "placeholder": "Search"},
                {"by": "label", "label": "Search"},
                {"by": "role", "role": "searchbox", "name": "Search"}
            ],
            value="carm",
            in_iframe={"url_pattern": "movementreason"}
        )
    
    Example (iframe annidati):
        frame = get_frame(iframe_path=[
            {"url_pattern": "dashboard"},
            {"selector": "iframe#payment-widget"}
        ])
        click_smart(
            targets=[{"by": "role", "role": "button", "name": "Pay"}],
            in_iframe={"iframe_path": [
                {"url_pattern": "dashboard"},
                {"selector": "iframe#payment-widget"}
            ]}
        )
    """
    result = await playwright.get_frame(selector=selector, url_pattern=url_pattern, iframe_path=iframe_path, timeout=timeout)
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
