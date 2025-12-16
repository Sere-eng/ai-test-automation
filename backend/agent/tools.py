# backend/agent/tools.py
"""
Playwright Tools - ASYNC Version (compatibile con MCP asyncio)
"""
from playwright.async_api import async_playwright
import base64
from datetime import datetime


class PlaywrightTools:
    """
    Classe che contiene i tool per interagire con il browser tramite Playwright (ASYNC)
    """
    
    def __init__(self):
        """Inizializza Playwright"""
        self.playwright = None
        self.browser = None
        self.page = None
        self.context = None
    
    async def start_browser(self, headless=False):
        """
        Avvia il browser Chromium con impostazioni ottimizzate (ASYNC)
        
        Args:
            headless: Se True, il browser è invisibile. Se False, vedi il browser aprirsi
        
        Returns:
            dict con status
        """
        try:
            self.playwright = await async_playwright().start()
            # Avvia browser con opzioni extra
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                ]
            )

            # Crea context con impostazioni
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                locale='it-IT',
                timezone_id='Europe/Rome'
            )

            self.page = await self.context.new_page()
            
            return {
                "status": "success",
                "message": "Browser avviato con successo",
                "headless": headless
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore nell'avviare il browser: {str(e)}"
            }
    
    async def navigate_to_url(self, url):
        """
        Naviga a un URL specifico (ASYNC)
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato. Chiama prima start_browser()"
                }
            
            await self.page.goto(url, wait_until="networkidle")
            
            page_title = await self.page.title()
            current_url = self.page.url
            
            return {
                "status": "success",
                "message": f"Navigato a {url}",
                "url": current_url,
                "page_title": page_title
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore nella navigazione: {str(e)}"
            }
    
    async def capture_screenshot(self, filename=None):
        """
        Cattura uno screenshot della pagina corrente (ASYNC)
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            
            screenshot_bytes = await self.page.screenshot(full_page=True)
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            return {
                "status": "success",
                "message": "Screenshot catturato",
                "filename": filename,
                "screenshot": screenshot_base64,
                "size_bytes": len(screenshot_bytes)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore nel catturare screenshot: {str(e)}"
            }
    
    async def close_browser(self):
        """
        Chiude il browser e pulisce le risorse (ASYNC)
        """
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
            
            return {
                "status": "success",
                "message": "Browser chiuso correttamente"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore nella chiusura: {str(e)}"
            }
    
    async def get_page_info(self):
        """
        Ottiene informazioni sulla pagina corrente (ASYNC)
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            return {
                "status": "success",
                "url": self.page.url,
                "title": await self.page.title(),
                "viewport": self.page.viewport_size
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore: {str(e)}"
            }
    
    # ==================== TOOL AVANZATI ASYNC ====================

    async def click_element(self, selector, selector_type="css", timeout=30000):
        """
        Clicca su un elemento della pagina (ASYNC)
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            if selector_type == "css":
                locator = self.page.locator(selector)
            elif selector_type == "xpath":
                locator = self.page.locator(f"xpath={selector}")
            elif selector_type == "text":
                locator = self.page.get_by_text(selector)
            else:
                return {
                    "status": "error",
                    "message": f"Tipo selector non supportato: {selector_type}"
                }
            
            await locator.wait_for(state="visible", timeout=timeout)
            await locator.click()
            
            return {
                "status": "success",
                "message": f"Cliccato su elemento: {selector}",
                "selector": selector,
                "selector_type": selector_type
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore nel click: {str(e)}",
                "selector": selector
            }
    
    async def fill_input(self, selector, value, selector_type="css", clear_first=True):
        """
        Compila un campo input con un valore (ASYNC)
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            if selector_type == "css":
                locator = self.page.locator(selector)
            elif selector_type == "xpath":
                locator = self.page.locator(f"xpath={selector}")
            elif selector_type == "placeholder":
                locator = self.page.get_by_placeholder(selector)
            else:
                return {
                    "status": "error",
                    "message": f"Tipo selector non supportato: {selector_type}"
                }
            
            if clear_first:
                await locator.clear()
            
            await locator.fill(value)
            
            return {
                "status": "success",
                "message": f"Campo compilato: {selector} = {value}",
                "selector": selector,
                "value": value
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore nella compilazione: {str(e)}",
                "selector": selector
            }
    
    async def wait_for_element(self, selector, selector_type="css", state="visible", timeout=30000):
        """
        Aspetta che un elemento appaia/scompaia dalla pagina (ASYNC)
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            if selector_type == "css":
                locator = self.page.locator(selector)
            elif selector_type == "xpath":
                locator = self.page.locator(f"xpath={selector}")
            elif selector_type == "text":
                locator = self.page.get_by_text(selector)
            else:
                return {
                    "status": "error",
                    "message": f"Tipo selector non supportato: {selector_type}"
                }
            
            await locator.wait_for(state=state, timeout=timeout)
            
            return {
                "status": "success",
                "message": f"Elemento {selector} è ora {state}",
                "selector": selector,
                "state": state
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Timeout o errore: {str(e)}",
                "selector": selector
            }
    
    async def get_text(self, selector, selector_type="css"):
        """
        Estrae il testo da un elemento (ASYNC)
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            if selector_type == "css":
                locator = self.page.locator(selector)
            elif selector_type == "xpath":
                locator = self.page.locator(f"xpath={selector}")
            else:
                return {
                    "status": "error",
                    "message": f"Tipo selector non supportato: {selector_type}"
                }
            
            text = await locator.inner_text()
            
            return {
                "status": "success",
                "message": "Testo estratto con successo",
                "selector": selector,
                "text": text
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore nell'estrazione: {str(e)}",
                "selector": selector
            }
    
    async def check_element_exists(self, selector, selector_type="css"):
        """
        Verifica se un elemento esiste nella pagina (ASYNC)
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            if selector_type == "css":
                locator = self.page.locator(selector)
            elif selector_type == "xpath":
                locator = self.page.locator(f"xpath={selector}")
            elif selector_type == "text":
                locator = self.page.get_by_text(selector)
            else:
                return {
                    "status": "error",
                    "message": f"Tipo selector non supportato: {selector_type}"
                }
            
            count = await locator.count()
            exists = count > 0
            is_visible = False
            
            if exists:
                is_visible = await locator.first.is_visible()
            
            return {
                "status": "success",
                "message": f"Elemento {'trovato' if exists else 'non trovato'}",
                "selector": selector,
                "exists": exists,
                "is_visible": is_visible
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore nella verifica: {str(e)}",
                "selector": selector
            }
    
    async def press_key(self, key):
        """
        Simula la pressione di un tasto (ASYNC)
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            await self.page.keyboard.press(key)
            
            return {
                "status": "success",
                "message": f"Tasto premuto: {key}",
                "key": key
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore: {str(e)}",
                "key": key
            }