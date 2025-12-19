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
        Avvia il browser Chromium con cookie consent pre-impostato per Google
        """
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=headless, # headless=True → Browser INVISIBILE (no interfaccia grafica)
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ] # Disabilita la proprietà navigator.webdriver -> Nasconde al sito web che il browser è controllato da automazione (Bypassa alcuni controlli anti-bot)
            )

            # SOLUZIONE COOKIE GOOGLE: Pre-imposta cookie di consenso
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
                locale='it-IT',
                timezone_id='Europe/Rome',
                viewport={'width': 1664, 'height': 1110}
            )

            self.page = await self.context.new_page()
            
            return {
                "status": "success",
                "message": "Browser avviato con successo (stealth mode)",
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
    
    async def capture_screenshot(self, filename=None, return_base64=False):
            """
            Cattura uno screenshot della pagina corrente (ASYNC)
            
            Args:
                filename: Nome file per reference (non viene salvato)
                return_base64: Se True, include base64 nella risposta. Default False.
            
            Returns:
                dict con status e opzionalmente base64
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
                
                # Cattura screenshot come bytes
                screenshot_bytes = await self.page.screenshot(full_page=True)
                
                result = {
                    "status": "success",
                    "message": f"Screenshot catturato: {filename}",
                    "filename": filename,
                    "size_bytes": len(screenshot_bytes)
                }
                
                # Include base64 SOLO se richiesto
                if return_base64:
                    screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    result["base64"] = screenshot_base64
                
                return result
                
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

    async def inspect_page_structure(self):
        """
        Ispeziona la struttura della pagina corrente per trovare selettori.
        Utile per debugging form di login.
        
        Returns:
            dict con informazioni su input fields, buttons, forms
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }
            
            # Trova tutti gli input
            inputs = await self.page.locator("input").all()
            input_info = []
            
            for idx, inp in enumerate(inputs):
                try:
                    input_type = await inp.get_attribute("type") or "text"
                    input_name = await inp.get_attribute("name") or ""
                    input_id = await inp.get_attribute("id") or ""
                    input_placeholder = await inp.get_attribute("placeholder") or ""
                    input_class = await inp.get_attribute("class") or ""
                    
                    input_info.append({
                        "index": idx,
                        "type": input_type,
                        "name": input_name,
                        "id": input_id,
                        "placeholder": input_placeholder,
                        "class": input_class,
                        "selector_suggestions": [
                            f"input[name='{input_name}']" if input_name else None,
                            f"#{input_id}" if input_id else None,
                            f"input[type='{input_type}']",
                            f"input[placeholder='{input_placeholder}']" if input_placeholder else None
                        ]
                    })
                except Exception as e:
                    print(f"Error inspecting input {idx}: {e}")
                    continue
            
            # Trova tutti i button
            buttons = await self.page.locator("button").all()
            button_info = []
            
            for idx, btn in enumerate(buttons):
                try:
                    button_text = await btn.inner_text()
                    button_type = await btn.get_attribute("type") or ""
                    button_class = await btn.get_attribute("class") or ""
                    button_id = await btn.get_attribute("id") or ""
                    
                    button_info.append({
                        "index": idx,
                        "text": button_text.strip(),
                        "type": button_type,
                        "id": button_id,
                        "class": button_class,
                        "selector_suggestions": [
                            f"button:has-text('{button_text.strip()}')" if button_text.strip() else None,
                            f"#{button_id}" if button_id else None,
                            f"button[type='{button_type}']" if button_type else None
                        ]
                    })
                except Exception as e:
                    print(f"Error inspecting button {idx}: {e}")
                    continue
            
            # Trova form
            forms = await self.page.locator("form").all()
            form_info = []
            
            for idx, form in enumerate(forms):
                try:
                    form_action = await form.get_attribute("action") or ""
                    form_method = await form.get_attribute("method") or ""
                    form_id = await form.get_attribute("id") or ""
                    
                    form_info.append({
                        "index": idx,
                        "action": form_action,
                        "method": form_method,
                        "id": form_id
                    })
                except Exception as e:
                    print(f"Error inspecting form {idx}: {e}")
                    continue
            
            return {
                "status": "success",
                "message": f"Page structure analyzed: {len(input_info)} inputs, {len(button_info)} buttons, {len(form_info)} forms",
                "page_info": {
                    "url": self.page.url,
                    "title": await self.page.title()
                },
                "inputs": input_info,
                "buttons": button_info,
                "forms": form_info
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore nell'ispezione: {str(e)}"
            } 

    async def handle_cookie_banner(self, strategies: list = None, timeout: int = 5000):
        """
        Gestisce automaticamente i banner dei cookie con strategie multiple
        
        Args:
            strategies: Lista di strategie da provare (default: tutte)
            timeout: Timeout per ogni tentativo in ms (default: 5000)
        
        Returns:
            dict con status e strategia usata
        
        Strategies disponibili:
            - "generic_accept": Bottoni generici "Accept"/"Accetta"
            - "generic_agree": Bottoni generici "Agree"/"Acconsento"
            - "reject_all": Bottoni "Reject all"/"Rifiuta tutto"
        """
        if not self.page:
            return {
                "status": "error",
                "message": "Browser non avviato. Chiama start_browser() prima."
            }
        
        # Default: prova tutte le strategie comuni
        if strategies is None:
            strategies = ["generic_accept", "generic_agree"]
        
        # Definizione selettori per ogni strategia
        selectors_map = {
            "generic_accept": [
                "button:has-text('Accept')",
                "button:has-text('Accetta')",
                "button:has-text('Accepter')",
                "button:has-text('Aceptar')",
                "button:has-text('Akzeptieren')",
                "a:has-text('Accept')",
                "a:has-text('Accetta')"
            ],
            "generic_agree": [
                "button:has-text('Agree')",
                "button:has-text('Acconsento')",
                "button:has-text('I agree')",
                "button:has-text('Sono d\\'accordo')"
            ],
            "reject_all": [
                "button:has-text('Reject all')",
                "button:has-text('Rifiuta tutto')",
                "button:has-text('Refuse')"
            ]
        }
        
        try:
            # Aspetta la pagina carichi
            await self.page.wait_for_timeout(1000)
            
            # Prova ogni strategia
            for strategy in strategies:
                if strategy not in selectors_map:
                    continue
                
                selectors = selectors_map[strategy]
                
                for selector in selectors:
                    try:
                        # Controlla se elemento esiste ed è visibile
                        element = self.page.locator(selector).first
                        
                        # Aspetta che sia visibile (con timeout breve)
                        await element.wait_for(state="visible", timeout=timeout)
                        
                        # Clicca
                        await element.click(timeout=timeout)
                        
                        # Aspetta che il banner sparisca
                        await self.page.wait_for_timeout(1000)
                        
                        return {
                            "status": "success",
                            "message": f"Cookie banner gestito con strategia '{strategy}'",
                            "strategy": strategy,
                            "selector": selector,
                            "clicked": True
                        }
                        
                    except Exception:
                        # Questo selettore non ha funzionato, prova il prossimo
                        continue
            
            # Nessuna strategia ha funzionato
            return {
                "status": "success",
                "message": "Nessun cookie banner trovato (o già accettato)",
                "strategy": None,
                "selector": None,
                "clicked": False
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore durante gestione cookie banner: {str(e)}",
                "strategy": None,
                "clicked": False
            }      

