# backend/mcp_servers/playwright_server_remote.py
"""
MCP Server per Playwright Tools - ASYNC Version
Comunicazione HTTP (remoto) compatibile con asyncio
"""

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import sys
import os
import asyncio

load_dotenv()

# Aggiungi la cartella parent al path per importare tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.tools import PlaywrightTools

# Crea il server MCP con porta HTTP
mcp = FastMCP("PlaywrightTools", port=8001)

# Istanza globale dei tool Playwright
playwright = PlaywrightTools()


@mcp.tool()
async def start_browser(headless: bool = False) -> str:
    """Avvia il browser Chromium per i test."""
    result = await playwright.start_browser(headless)
    
    if result["status"] == "success":
        return f"✅ Browser avviato con successo (headless={headless})"
    else:
        return f"❌ Errore nell'avviare il browser: {result['message']}"


@mcp.tool()
async def navigate_to_url(url: str) -> str:
    """Naviga a un URL specifico e aspetta il caricamento della pagina."""
    result = await playwright.navigate_to_url(url)
    
    if result["status"] == "success":
        return f"✅ Navigato a {result['url']}\nTitolo pagina: {result['page_title']}"
    else:
        return f"❌ Errore nella navigazione: {result['message']}"


@mcp.tool()
async def click_element(selector: str, selector_type: str = "css", timeout: int = 30000) -> str:
    """Clicca su un elemento della pagina web."""
    result = await playwright.click_element(selector, selector_type, timeout)
    
    if result["status"] == "success":
        return f"✅ Click eseguito su elemento: {selector} ({selector_type})"
    else:
        return f"❌ Errore nel click: {result['message']}\nSelector: {selector}"


@mcp.tool()
async def fill_input(selector: str, value: str, selector_type: str = "css", clear_first: bool = True) -> str:
    """Compila un campo input con del testo."""
    result = await playwright.fill_input(selector, value, selector_type, clear_first)
    
    if result["status"] == "success":
        display_value = "***" if "password" in selector.lower() else value
        return f"✅ Campo compilato: {selector} = {display_value}"
    else:
        return f"❌ Errore nella compilazione: {result['message']}\nSelector: {selector}"


@mcp.tool()
async def wait_for_element(selector: str, state: str = "visible", selector_type: str = "css", timeout: int = 30000) -> str:
    """Aspetta che un elemento appaia o scompaia dalla pagina. FONDAMENTALE per caricamenti AJAX!"""
    result = await playwright.wait_for_element(selector, selector_type, state, timeout)
    
    if result["status"] == "success":
        return f"✅ Elemento {selector} è ora {state}"
    else:
        return f"❌ Timeout: elemento {selector} non è diventato {state}\n{result['message']}"


@mcp.tool()
async def get_text(selector: str, selector_type: str = "css") -> str:
    """Estrae il testo visibile da un elemento della pagina."""
    result = await playwright.get_text(selector, selector_type)
    
    if result["status"] == "success":
        return f"Testo estratto da {selector}:\n{result['text']}"
    else:
        return f"❌ Errore nell'estrazione del testo: {result['message']}"


@mcp.tool()
async def check_element_exists(selector: str, selector_type: str = "css") -> str:
    """Verifica se un elemento esiste ed è visibile nella pagina."""
    result = await playwright.check_element_exists(selector, selector_type)
    
    if result["status"] == "success":
        exists = result["exists"]
        visible = result["is_visible"]
        
        if exists and visible:
            return f"✅ Elemento {selector} esiste ed è visibile"
        elif exists and not visible:
            return f"⚠️ Elemento {selector} esiste ma NON è visibile"
        else:
            return f"❌ Elemento {selector} NON esiste nella pagina"
    else:
        return f"❌ Errore nella verifica: {result['message']}"


@mcp.tool()
async def press_key(key: str) -> str:
    """Simula la pressione di un tasto speciale."""
    result = await playwright.press_key(key)
    
    if result["status"] == "success":
        return f"✅ Tasto premuto: {key}"
    else:
        return f"❌ Errore: {result['message']}"


@mcp.tool()
async def capture_screenshot(filename: str = None) -> str:
    """Cattura uno screenshot full-page della pagina corrente e ritorna base64."""
    result = await playwright.capture_screenshot(filename)
    
    if result["status"] == "success":
        # ⭐ Ritorna base64 nel messaggio così l'AI può usarlo
        return f"""✅ Screenshot catturato: {result['filename']} ({result['size_bytes']} bytes)
📸 Base64: {result['screenshot'][:100]}... (truncated)

🔑 SCREENSHOT_BASE64_START
{result['screenshot']}
🔑 SCREENSHOT_BASE64_END"""
    else:
        return f"❌ Errore nello screenshot: {result['message']}"


@mcp.tool()
async def close_browser() -> str:
    """Chiude il browser e libera tutte le risorse."""
    result = await playwright.close_browser()
    
    if result["status"] == "success":
        return "✅ Browser chiuso correttamente"
    else:
        return f"❌ Errore nella chiusura: {result['message']}"


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
        return f"❌ Errore: {result['message']}"


# Avvia il server MCP su HTTP
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 MCP Playwright Server (HTTP transport) - ASYNC Version")
    print("=" * 80)
    print(f"📡 Server URL: http://localhost:8001/mcp/")
    print(f"🔧 Tool disponibili: 11")
    print(f"📝 Per usarlo dall'agent, configura:")
    print(f'   "url": "http://localhost:8001/mcp/"')
    print(f'   "transport": "streamable_http"')
    print("=" * 80)
    print("Premi CTRL+C per fermare il server")
    print("=" * 80)
    
    mcp.run(transport="streamable-http")