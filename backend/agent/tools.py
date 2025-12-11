# backend/agent/tools.py
from playwright.sync_api import sync_playwright
import base64
from datetime import datetime

class PlaywrightTools:
    """
    Classe che contiene i tool per interagire con il browser tramite Playwright
    """
    
    def __init__(self):
        """Inizializza Playwright"""
        self.playwright = None
        self.browser = None
        self.page = None
    
    def start_browser(self, headless=False):
        """
        Avvia il browser Chromium con impostazioni ottimizzate
        
        Args:
            headless: Se True, il browser è invisibile. Se False, vedi il browser aprirsi
        
        Returns:
            dict con status
        """
        try:
            self.playwright = sync_playwright().start()
            # Avvia browser con opzioni extra
            self.browser = self.playwright.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',  # Nasconde che è automation
                ]
            )

            # Crea context con impostazioni
            context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                locale='it-IT',  # Importante per i banner in italiano
                timezone_id='Europe/Rome'
            )

            self.page = context.new_page()
            
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
    
    def navigate_to_url(self, url):
        """
        Naviga a un URL specifico
        
        Args:
            url: L'URL completo (es. https://google.com)
        
        Returns:
            dict con status, url, title della pagina
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato. Chiama prima start_browser()"
                }
            
            # Naviga all'URL
            self.page.goto(url, wait_until="networkidle")
            
            # Prendi informazioni sulla pagina
            page_title = self.page.title()
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
    
    def capture_screenshot(self, filename=None):
        """
        Cattura uno screenshot della pagina corrente
        
        Args:
            filename: Nome del file (opzionale). Se None, usa timestamp
        
        Returns:
            dict con status, filename, screenshot in base64
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            # Se non è specificato un nome, usa timestamp
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            
            # Cattura screenshot
            screenshot_bytes = self.page.screenshot(full_page=True)
            
            # Converti in base64 per poterlo inviare via API
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
    
    def close_browser(self):
        """
        Chiude il browser e pulisce le risorse
        
        Returns:
            dict con status
        """
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            
            self.page = None
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
    
    def get_page_info(self):
        """
        Ottiene informazioni sulla pagina corrente
        
        Returns:
            dict con informazioni sulla pagina
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
                "title": self.page.title(),
                "viewport": self.page.viewport_size
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore: {str(e)}"
            }
        
    # ==================== TOOL AVANZATI ====================

    def click_element(self, selector, selector_type="css", timeout=30000):
        """
        Clicca su un elemento della pagina
        
        Args:
            selector: Il selettore dell'elemento (CSS, XPath, text)
            selector_type: Tipo di selettore ('css', 'xpath', 'text')
            timeout: Tempo massimo di attesa in millisecondi (default 30 secondi)
        
        Returns:
            dict con status dell'operazione
        
        Esempi:
            click_element("button#submit", "css")
            click_element("//button[@id='submit']", "xpath")
            click_element("Login", "text")
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            # Costruisci il locator in base al tipo
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
            
            # Aspetta che l'elemento sia visibile e cliccabile
            locator.wait_for(state="visible", timeout=timeout)
            locator.click()
            
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
    
    def fill_input(self, selector, value, selector_type="css", clear_first=True):
        """
        Compila un campo input con un valore
        
        Args:
            selector: Il selettore dell'input
            value: Il valore da inserire
            selector_type: Tipo di selettore ('css', 'xpath', 'placeholder')
            clear_first: Se True, pulisce il campo prima di scrivere
        
        Returns:
            dict con status
        
        Esempi:
            fill_input("#email", "test@test.com")
            fill_input("//input[@name='email']", "test@test.com", "xpath")
            fill_input("Enter your email", "test@test.com", "placeholder")
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            # Costruisci il locator
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
            
            # Pulisci il campo se richiesto
            if clear_first:
                locator.clear()
            
            # Inserisci il valore
            locator.fill(value)
            
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
    
    def wait_for_element(self, selector, selector_type="css", state="visible", timeout=30000):
        """
        Aspetta che un elemento appaia/scompaia dalla pagina
        
        Args:
            selector: Il selettore dell'elemento
            selector_type: Tipo di selettore ('css', 'xpath', 'text')
            state: Stato da aspettare ('visible', 'hidden', 'attached', 'detached')
            timeout: Tempo massimo in millisecondi
        
        Returns:
            dict con status
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            # Costruisci il locator
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
            
            # Aspetta lo stato richiesto
            locator.wait_for(state=state, timeout=timeout)
            
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
    
    def get_text(self, selector, selector_type="css"):
        """
        Estrae il testo da un elemento
        
        Args:
            selector: Il selettore dell'elemento
            selector_type: Tipo di selettore ('css', 'xpath')
        
        Returns:
            dict con status e testo estratto
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            # Costruisci il locator
            if selector_type == "css":
                locator = self.page.locator(selector)
            elif selector_type == "xpath":
                locator = self.page.locator(f"xpath={selector}")
            else:
                return {
                    "status": "error",
                    "message": f"Tipo selector non supportato: {selector_type}"
                }
            
            # Estrai il testo
            text = locator.inner_text()
            
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
    
    def check_element_exists(self, selector, selector_type="css"):
        """
        Verifica se un elemento esiste nella pagina
        
        Args:
            selector: Il selettore dell'elemento
            selector_type: Tipo di selettore ('css', 'xpath', 'text')
        
        Returns:
            dict con status e booleano exists
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            # Costruisci il locator
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
            
            # Verifica esistenza (con timeout breve per non aspettare troppo)
            exists = locator.count() > 0
            is_visible = False
            
            if exists:
                is_visible = locator.first.is_visible()
            
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
    
    def press_key(self, key):
        """
        Simula la pressione di un tasto
        
        Args:
            key: Il tasto da premere ('Enter', 'Escape', 'ArrowDown', etc)
        
        Returns:
            dict con status
        
        Esempi comuni:
            'Enter', 'Escape', 'Tab', 'Backspace', 'ArrowDown', 'ArrowUp'
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            self.page.keyboard.press(key)
            
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