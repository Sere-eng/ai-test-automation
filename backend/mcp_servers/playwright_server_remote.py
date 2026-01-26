# backend/mcp_servers/playwright_server_remote.py
"""
MCP Server per Playwright Tools - ASYNC Version
Comunicazione HTTP (remoto) compatibile con asyncio
"""

import json
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import sys
import os
import asyncio

load_dotenv()

# Aggiungi la cartella parent al path per importare tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.tools import PlaywrightTools
from config.settings import AppConfig

# Crea il server MCP con porta HTTP
mcp = FastMCP(
    "PlaywrightTools",
    host=AppConfig.MCP.REMOTE_HOST,
    port=AppConfig.MCP.REMOTE_PORT
)

# Istanza globale dei tool Playwright
playwright = PlaywrightTools()


@mcp.tool()
async def start_browser(headless: bool = False) -> str:
    """Avvia il browser Chromium per i test."""
    result = await playwright.start_browser(headless)
    
    if result["status"] == "success":
        return f"Browser avviato con successo (headless={headless})"
    else:
        return f"Errore nell'avviare il browser: {result['message']}"


@mcp.tool()
async def navigate_to_url(url: str) -> str:
    """Naviga a un URL specifico e aspetta il caricamento della pagina."""
    result = await playwright.navigate_to_url(url)
    
    if result["status"] == "success":
        return f"Navigato a {result['url']}\nTitolo pagina: {result['page_title']}"
    else:
        return f"Errore nella navigazione: {result['message']}"


@mcp.tool()
async def click_element(selector: str, selector_type: str = "css", timeout: int = 30000) -> str:
    """Clicca su un elemento della pagina web."""
    result = await playwright.click_element(selector, selector_type, timeout)
    
    if result["status"] == "success":
        return f"Click eseguito su elemento: {selector} ({selector_type})"
    else:
        return f"Errore nel click: {result['message']}\nSelector: {selector}"


@mcp.tool()
async def fill_input(selector: str, value: str, selector_type: str = "css", clear_first: bool = True) -> str:
    """Compila un campo input con del testo."""
    result = await playwright.fill_input(selector, value, selector_type, clear_first)
    
    if result["status"] == "success":
        display_value = "***" if "password" in selector.lower() else value
        return f"Campo compilato: {selector} = {display_value}"
    else:
        return f"Errore nella compilazione: {result['message']}\nSelector: {selector}"


@mcp.tool()
async def wait_for_element(selector: str, state: str = "visible", selector_type: str = "css", timeout: int = 30000) -> str:
    """Aspetta che un elemento appaia o scompaia dalla pagina. FONDAMENTALE per caricamenti AJAX!"""
    result = await playwright.wait_for_element(selector, selector_type, state, timeout)
    
    if result["status"] == "success":
        return f"Elemento {selector} è ora {state}"
    else:
        return f"Timeout: elemento {selector} non è diventato {state}\n{result['message']}"


@mcp.tool()
async def get_text(selector: str, selector_type: str = "css") -> str:
    """Estrae il testo visibile da un elemento della pagina."""
    result = await playwright.get_text(selector, selector_type)
    
    if result["status"] == "success":
        return f"Testo estratto da {selector}:\n{result['text']}"
    else:
        return f"Errore nell'estrazione del testo: {result['message']}"


@mcp.tool()
async def check_element_exists(selector: str, selector_type: str = "css") -> str:
    """Verifica se un elemento esiste ed è visibile nella pagina."""
    result = await playwright.check_element_exists(selector, selector_type)
    
    if result["status"] == "success":
        exists = result["exists"]
        visible = result["is_visible"]
        
        if exists and visible:
            return f"Elemento {selector} esiste ed è visibile"
        elif exists and not visible:
            return f"Elemento {selector} esiste ma NON è visibile"
        else:
            return f"Elemento {selector} NON esiste nella pagina"
    else:
        return f"Errore nella verifica: {result['message']}"


@mcp.tool()
async def press_key(key: str) -> str:
    """Simula la pressione di un tasto speciale."""
    result = await playwright.press_key(key)
    
    if result["status"] == "success":
        return f"Tasto premuto: {key}"
    else:
        return f"Errore: {result['message']}"


mcp.tool()
async def capture_screenshot(filename: str = None, return_base64: bool = False) -> str:
    """
    Cattura uno screenshot full-page della pagina corrente.
    
    Args:
        filename: Nome file per reference (opzionale)
        return_base64: Se True, include il base64 nella risposta. 
                       ATTENZIONE: aumenta i token! Usa solo se necessario.
    
    Returns:
        Conferma con metadata. Se return_base64=True, include anche il base64.
    """
    result = await playwright.capture_screenshot(filename, return_base64)
    
    if result["status"] == "success":
        response = f"Screenshot catturato: {result['filename']} ({result['size_bytes']} bytes)"
        
        # Include base64 SOLO se richiesto
        if return_base64 and "base64" in result:
            response += f"\n\n SCREENSHOT_BASE64:\n{result['base64']}"
        
        return response
    else:
        return f"Errore nello screenshot: {result['message']}"


@mcp.tool()
async def close_browser() -> str:
    """Chiude il browser e libera tutte le risorse."""
    result = await playwright.close_browser()
    
    if result["status"] == "success":
        return "Browser chiuso correttamente"
    else:
        return f"Errore nella chiusura: {result['message']}"


@mcp.tool()
async def get_page_info() -> str:
    """Ottiene informazioni sulla pagina corrente (URL, titolo, viewport)."""
    result = await playwright.get_page_info()
    
    if result["status"] == "success":
        return f"""Informazioni pagina corrente:
- URL: {result['url']}
- Titolo: {result['title']}
- Viewport: {result['viewport']}"""
    else:
        return f"Errore: {result['message']}"


@mcp.tool() 
async def inspect_page_structure() -> str:
    """
    Inspects the current page structure to find selectors for forms, inputs, and buttons.
    
    This is extremely useful for debugging login forms or any interactive elements.
    Returns detailed information about:
    - All input fields (type, name, id, placeholder, suggested selectors)
    - All buttons (text, type, id, suggested selectors)
    - All forms (action, method, id)
    
    Use this when you need to figure out the correct selectors for a page you haven't seen before.
    
    Returns:
        Detailed JSON structure with all page elements and suggested selectors
    """
    result = await playwright.inspect_page_structure()
    
    if result["status"] == "success":
        # Formatta output in modo leggibile
        output = f""" Page Structure Analysis Complete

Page Info:
   URL: {result['page_info']['url']}
   Title: {result['page_info']['title']}

INPUT FIELDS ({len(result['inputs'])}):
"""
        
        for inp in result['inputs']:
            output += f"\n   Input #{inp['index']}:"
            output += f"\n      Type: {inp['type']}"
            if inp['name']:
                output += f"\n      Name: {inp['name']}"
            if inp['id']:
                output += f"\n      ID: {inp['id']}"
            if inp['placeholder']:
                output += f"\n      Placeholder: {inp['placeholder']}"
            output += f"\n      Suggested selectors:"
            for selector in inp['selector_suggestions']:
                if selector:
                    output += f"\n         - {selector}"
            output += "\n"
        
        output += f"\n BUTTONS ({len(result['buttons'])}):\n"
        
        for btn in result['buttons']:
            output += f"\n   Button #{btn['index']}:"
            output += f"\n      Text: '{btn['text']}'"
            if btn['type']:
                output += f"\n      Type: {btn['type']}"
            if btn['id']:
                output += f"\n      ID: {btn['id']}"
            output += f"\n      Suggested selectors:"
            for selector in btn['selector_suggestions']:
                if selector:
                    output += f"\n         - {selector}"
            output += "\n"
        
        if result['forms']:
            output += f"\n FORMS ({len(result['forms'])}):\n"
            for form in result['forms']:
                output += f"\n   Form #{form['index']}:"
                if form['action']:
                    output += f"\n      Action: {form['action']}"
                if form['method']:
                    output += f"\n      Method: {form['method']}"
                if form['id']:
                    output += f"\n      ID: {form['id']}"
                output += "\n"
        
        return output
    else:
        return f"Error: {result['message']}"


@mcp.tool()
async def handle_cookie_banner(
    strategies: list[str] | None = None,
    timeout: int = 5000
) -> str:
    """
    Handles cookie consent banners automatically with multiple strategies.
    
    Args:
        strategies: List of strategies to try (default: all common ones)
                   Options: "google", "amazon", "generic_accept", "generic_agree", "reject_all"
        timeout: Timeout per attempt in milliseconds (default: 5000)
    
    Returns:
        JSON result with status and strategy used
    
    Example:
        # Try all default strategies
        handle_cookie_banner()
        
        # Try specific strategies only
        handle_cookie_banner(strategies=["google", "amazon"])
    """
    result = await playwright.handle_cookie_banner(
        strategies=strategies,
        timeout=timeout
    )
    return json.dumps(result, indent=2)


# Avvia il server MCP su HTTP
if __name__ == "__main__":
    port = AppConfig.MCP.REMOTE_PORT
    host = AppConfig.MCP.REMOTE_HOST
    
    print("=" * 80)
    print("  MCP Playwright Server (HTTP transport) - ASYNC Version")
    print("=" * 80)
    print(f"  Server URL: http://{host}:{port}/mcp/")
    print(f"  Tool disponibili: 13")
    print(f"  Per usarlo dall'agent, configura in config/settings.py:")
    print(f'  MCPConfig.MODE = "remote"')
    print(f'  MCPConfig.REMOTE_PORT = {port}')
    print("=" * 80)
    print("Premi CTRL+C per fermare il server")
    print("=" * 80)
    
    # run() senza parametri - tutto è già in __init__
    mcp.run(transport="streamable-http")