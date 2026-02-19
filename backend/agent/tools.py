# backend/agent/tools.py
"""
Playwright Tools - ASYNC Version (compatibile con MCP asyncio)
"""
import asyncio
import base64
import datetime
from playwright.async_api import async_playwright, Page
from typing import Literal, Optional, List, Dict

from config.settings import AppConfig


def _normalize_css_selector(by: str, target: dict) -> Optional[str]:
    """Normalize CSS selector: for css_id or id-like selector (e.g. mat-input-17), prefix with #."""
    selector = target.get("selector") or (f"#{target['id']}" if by == "css_id" and target.get("id") else None)
    if not selector:
        return None
    # If it looks like an id (starts with letter/underscore, only alphanumeric/hyphen), ensure # prefix
    s = selector.strip()
    if s and not s.startswith("#") and not s.startswith("[") and not s.startswith(".") and "/" not in s:
        if (s[0].isalpha() or s[0] == "_") and all(c.isalnum() or c in "-_" for c in s):
            return "#" + s
    return selector


class PlaywrightTools:
    """
    Classe che contiene i tool per interagire con il browser tramite Playwright (ASYNC).

    Ordine dei tool (raw → advanced):
    - RAW: lifecycle (start/close/navigate), pagina (info, screenshot), elementi (press_key, get_text, wait_for_element), load_state, get_frame
    - MEDIUM: wait_for_text_content
    - SMART LOCATORS: click_smart, fill_smart (fallback chain)
    - INSPECTION: inspect_interactive_elements (scansione per smart/advanced)
    - ADVANCED: wait_for_clickable_by_name, wait_for_control_by_name_and_type, wait_for_field_by_name, handle_cookie_banner, click_and_wait_for_text
    """

    def __init__(self):
        """Inizializza Playwright"""
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    # =====================================================================
    # RAW - Lifecycle & pagina
    # =====================================================================

    async def start_browser(self, headless=False):
        """
        Avvia il browser Chromium con cookie consent pre-impostato per Google
        """
        try:
            self.playwright = await async_playwright().start()
            
            # Args: disabilitano rilevamento automazione (navigator.webdriver, feature detection)
            browser_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
            
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=browser_args
            )

            # SOLUZIONE COOKIE GOOGLE: Pre-imposta cookie di consenso
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
                locale=AppConfig.PLAYWRIGHT.LOCALE,
                timezone_id=AppConfig.PLAYWRIGHT.TIMEZONE,
                viewport={'width': AppConfig.PLAYWRIGHT.VIEWPORT_WIDTH,
                          'height': AppConfig.PLAYWRIGHT.VIEWPORT_HEIGHT}
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

            # Importante: NON usare più "networkidle" come default.
            # Molte app moderne (SPA, polling, WebSocket) non raggiungono mai
            # uno stato di rete completamente idle e causano timeout inutili.
            # Per la LAB URL e in generale per questi workflow usiamo
            # "domcontentloaded", che è sufficiente per iniziare ad
            # interagire con la pagina.
            await self.page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=AppConfig.PLAYWRIGHT.TIMEOUT,
            )

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
                screenshot_base64 = base64.b64encode(
                    screenshot_bytes).decode('utf-8')
                result["base64"] = screenshot_base64

            return result

        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore nel catturare screenshot: {str(e)}"
            }

    # =====================================================================
    # RAW - Elementi, tastiera, load state, iframe
    # =====================================================================

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

    async def wait_for_load_state(
        self,
        state: Literal["load", "domcontentloaded", "networkidle"] = "domcontentloaded",
        timeout: int = 30000,
    ) -> dict:
        """Attende uno specifico load state di Playwright.
        Nota: su SPA spesso il load event è già avvenuto; questo tool è utile
        soprattutto dopo navigazioni vere (login redirect, cambio pagina, refresh).
        """
        if not self.page:
            return {
                "status": "error",
                "message": "Browser non avviato",
            }

        try:
            await self.page.wait_for_load_state(state=state, timeout=timeout)
            return {
                "status": "success",
                "message": f"Load state '{state}' raggiunto",
                "state": state,
                "timeout_ms": timeout,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Timeout waiting for load state '{state}'",
                "state": state,
                "timeout_ms": timeout,
                "error": str(e),
            }

    async def get_frame(
        self,
        selector: str = None,
        url_pattern: str = None,
        iframe_path: list = None,
        timeout: int = 10000,
        return_frame: bool = False,
    ):
        """
        Accede al contenuto di un iframe (anche annidati).

        Args:
            selector: CSS selector dell'iframe (es: 'iframe[src*="movementreason"]')
            url_pattern: Pattern dell'URL dell'iframe (alternativa a selector)
            iframe_path: Lista di dict per iframe annidati (es: [{"url_pattern": "dashboard"}, {"selector": "iframe#widget"}])
            timeout: Timeout in ms per ogni livello
            return_frame: Se True, include oggetto Frame per uso interno

        Returns:
            dict JSON-serializzabile con metadata iframe/frame.
            Se return_frame=True include anche l'oggetto Frame (NON serializzabile) per uso interno.

        Examples:
            # Iframe singolo
            frame = await get_frame(url_pattern="registry/movementreason")
            
            # Iframe annidati (dashboard → payment widget → form)
            frame = await get_frame(iframe_path=[
                {"url_pattern": "dashboard"},
                {"selector": "iframe#payment-widget"},
                {"url_pattern": "checkout-form"}
            ])
        """
        if not self.page:
            return {"status": "error", "message": "Browser non avviato"}

        try:
            # Determina strategia: iframe_path (annidati) o selector singolo
            if iframe_path:
                # Navigazione multi-livello per iframe annidati
                context = self.page
                selectors_used = []
                frame_urls = []
                
                for level_idx, level_spec in enumerate(iframe_path):
                    level_selector = None
                    if "selector" in level_spec:
                        level_selector = level_spec["selector"]
                    elif "url_pattern" in level_spec:
                        level_selector = f'iframe[src*="{level_spec["url_pattern"]}"]'
                    else:
                        level_selector = 'iframe'
                    
                    selectors_used.append(level_selector)
                    
                    # Trova iframe nel context corrente (page o frame parent)
                    iframe_element = await context.wait_for_selector(level_selector, timeout=timeout)
                    
                    # Accedi al content_frame
                    frame = await iframe_element.content_frame()
                    if frame is None:
                        return {
                            "status": "error",
                            "message": f"Iframe livello {level_idx + 1} trovato ma content_frame() è None",
                            "iframe_path": iframe_path,
                            "selectors_used": selectors_used,
                            "failed_at_level": level_idx + 1,
                        }
                    
                    await frame.wait_for_load_state('load', timeout=timeout)
                    frame_urls.append(getattr(frame, "url", None))
                    
                    # Il frame diventa il nuovo context per il prossimo livello
                    context = frame
                
                # context ora è il frame più profondo
                result = {
                    "status": "success",
                    "message": f"Frame annidato trovato ({len(iframe_path)} livelli)",
                    "iframe_path": iframe_path,
                    "selectors_used": selectors_used,
                    "frame_urls": frame_urls,
                    "final_frame_url": frame_urls[-1] if frame_urls else None,
                    "levels": len(iframe_path),
                    "timeout_ms": timeout,
                }
                if return_frame:
                    result["frame"] = context  # frame più profondo
                return result
                
            else:
                # Singolo iframe (backward compatibility)
                iframe_selector_used = None
                if selector:
                    iframe_selector_used = selector
                elif url_pattern:
                    iframe_selector_used = f'iframe[src*="{url_pattern}"]'
                else:
                    iframe_selector_used = 'iframe'

                # Prova prima con il selector specifico; se non trova nulla e avevamo
                # un url_pattern, fai fallback al primo iframe generico invece di
                # andare in timeout per 60s.
                try:
                    iframe_element = await self.page.wait_for_selector(iframe_selector_used, timeout=timeout)
                except Exception as e:
                    if url_pattern:
                        # Fallback: primo iframe disponibile
                        iframe_selector_used = 'iframe'
                        iframe_element = await self.page.wait_for_selector(iframe_selector_used, timeout=timeout)
                    else:
                        raise

                # Accedi al frame content
                frame = await iframe_element.content_frame()
                if frame is None:
                    return {
                        "status": "error",
                        "message": "Iframe trovato ma content_frame() è None",
                        "iframe_selector": iframe_selector_used,
                        "timeout_ms": timeout,
                    }

                await frame.wait_for_load_state('load', timeout=timeout)

                result = {
                    "status": "success",
                    "message": "Frame trovato e caricato",
                    "iframe_selector": iframe_selector_used,
                    "url_pattern": url_pattern,
                    "frame_url": getattr(frame, "url", None),
                    "timeout_ms": timeout,
                }
                if return_frame:
                    result["frame"] = frame
                return result

        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore accesso iframe: {str(e)}"
            }

    # =====================================================================
    # MEDIUM - Wait per testo
    # =====================================================================

    async def wait_for_text_content(
        self,
        text: str,
        timeout: int = 30000,
        case_sensitive: bool = False,
        in_iframe: dict = None
    ):
        """
        Aspetta che un testo specifico appaia OVUNQUE nella pagina o dentro un iframe.
        Utile per verificare messaggi di successo, titoli, nomi elementi dopo azioni AJAX.

        Args:
            text: Testo da cercare
            timeout: Timeout in ms (default: 30000)
            case_sensitive: Se True, match esatto (default: False)
            in_iframe: Dict per cercare dentro iframe (opzionale)
                {"url_pattern": "movementreason"} - iframe singolo
                {"iframe_path": [{...}, {...}]} - iframe annidati

        Returns:
            dict con status e informazioni sul testo trovato

        Example:
            # Dopo login, aspetta che appaia "Dashboard" (pagina principale)
            await wait_for_text_content("Dashboard", timeout=10000)

            # Dopo search in iframe Causali, aspetta risultato dentro iframe
            await wait_for_text_content(
                "CARMAG", 
                timeout=5000,
                in_iframe={"url_pattern": "movementreason"}
            )
        """
        if not self.page:
            return {
                "status": "error",
                "message": "Browser non avviato"
            }
        try:
            # Determina il contesto (page o frame)
            context = self.page
            if in_iframe:
                # Naviga al frame target (stessa semantica di inspect_interactive_elements)
                frame_result = await self.get_frame(
                    selector=in_iframe.get("selector"),
                    url_pattern=in_iframe.get("url_pattern"),
                    iframe_path=in_iframe.get("iframe_path"),
                    timeout=timeout,
                    return_frame=True,
                )
                if frame_result.get("status") == "error":
                    return frame_result
                # Usa direttamente l'oggetto frame restituito
                context = frame_result.get("frame", self.page)
            
            # Costruisci selector Playwright per text
            if case_sensitive:
                selector = f"text={text}"
            else:
                # Case-insensitive con regex
                selector = f"text=/{text}/i"

            # Aspetta che l'elemento con quel testo sia visibile
            await context.wait_for_selector(
                selector,
                timeout=timeout,
                state="visible",
            )

            return {
                "status": "success",
                "message": f"Testo '{text}' trovato e visibile",
                "text": text,
                "case_sensitive": case_sensitive
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Testo '{text}' non trovato dopo {timeout}ms",
                "text": text,
                "timeout_ms": timeout
            }

    # =====================================================================
    # SMART LOCATORS - Click/Fill con fallback chain
    # =====================================================================
    async def click_smart(
        self,
        targets: List[Dict],
        timeout_per_try: int = AppConfig.AGENT.DEFAULT_TIMEOUT_PER_TRY,
        in_iframe: dict = None
    ) -> dict:
        """
        Click elemento con fallback chain automatico - prova tutte le strategie fino al successo.
        Resilienza massima: role fallisce su duplicato? Prova css_aria. css_aria manca? Prova text.
        Supporta interazioni dentro iframe (per app Angular embedded).

        Args:
            targets: Lista strategie ordinate per robustezza (da inspect_interactive_elements)
                Es: [
                    {"by": "role", "role": "button", "name": "Login"},
                    {"by": "css", "selector": "[aria-label='Login']"},
                    {"by": "text", "text": "Login"}
                ]
            timeout_per_try: Timeout per ogni tentativo in ms
                            (default configurato in AppConfig.AGENT.DEFAULT_TIMEOUT_PER_TRY)
            in_iframe: dict per iframe (singolo o annidati)
                - Singolo: {"selector": "..."} o {"url_pattern": "..."}
                - Annidati: {"iframe_path": [{"url_pattern": "..."}, {"selector": "..."}]}

        Returns:
            dict con status, strategia usata, strategie provate

        Example:
            # Click nella pagina principale
            result = await click_smart([
                {"by": "role", "role": "button", "name": "Login"},
                {"by": "text", "text": "Login"}
            ])
            
            # Click dentro iframe singolo
            result = await click_smart(
                targets=[{"by": "role", "role": "button", "name": "Save"}],
                in_iframe={"url_pattern": "movementreason"}
            )
            
            # Click dentro iframe annidati (dashboard → widget → form)
            result = await click_smart(
                targets=[{"by": "role", "role": "button", "name": "Submit"}],
                in_iframe={"iframe_path": [
                    {"url_pattern": "dashboard"},
                    {"selector": "iframe#payment-widget"}
                ]}
            )
        """
        if not self.page:
            return {
                "status": "error",
                "message": "Browser non avviato. Chiama start_browser() prima."
            }
        
        if not targets or len(targets) == 0:
            return {
                "status": "error",
                "message": "Nessuna strategia fornita (targets vuoto)"
            }

        # Determina context (page o iframe)
        context = self.page
        if in_iframe:
            frame_result = await self.get_frame(**in_iframe, timeout=timeout_per_try, return_frame=True)
            if frame_result["status"] == "error":
                return frame_result
            context = frame_result["frame"]

        # FALLBACK CHAIN: prova tutte le strategie fino al successo
        strategies_tried = []
        last_error_msg = ""
        
        for idx, target in enumerate(targets):
            by = target.get("by")
            strategies_tried.append(by)
            
            try:
                locator = None

                # Strategy 1: Role-based (WCAG accessible)
                if by == "role":
                    role = target.get("role")
                    name = target.get("name")
                    locator = context.get_by_role(role, name=name)

                # Strategy 2: Label (form fields)
                elif by == "label":
                    label = target.get("label")
                    locator = context.get_by_label(label)

                # Strategy 3: Placeholder
                elif by == "placeholder":
                    placeholder = target.get("placeholder")
                    locator = context.get_by_placeholder(placeholder)

                # Strategy 4: Text content
                elif by == "text":
                    text = target.get("text")
                    locator = context.get_by_text(text)

                # Strategy 5: Test automation ID (data-tfa)
                elif by == "tfa":
                    tfa = target.get("tfa")
                    locator = context.locator(f'[data-tfa="{tfa}"]')

                # Strategy 6: CSS selector (fallback; accept css_name/css_id from model)
                elif by in ("css", "css_name", "css_id"):
                    selector = _normalize_css_selector(by, target)
                    locator = context.locator(selector) if selector else None

                # Strategy 7: XPath (last resort)
                elif by == "xpath":
                    xpath = target.get("xpath")
                    locator = context.locator(f"xpath={xpath}")
                
                if not locator:
                    last_error_msg = f"Impossibile creare locator per strategia '{by}'"
                    if idx < len(targets) - 1:
                        continue  # Prova prossima strategia
                    else:
                        break  # Ultima strategia - esci

                # CLICK VELOCE - 2 tentativi (scroll+normale → JS)
                # Try 1: SCROLL + CLICK NORMALE (preferito)
                try:
                    first = locator.first
                    # Scroll nel viewport se necessario (menu lunghi, side nav, toolbar compressa)
                    try:
                        await first.scroll_into_view_if_needed()
                    except Exception:
                        # Se lo scroll fallisce non bloccare il test: prova comunque a cliccare
                        pass

                    await first.click(timeout=timeout_per_try)
                    return {
                        "status": "success",
                        "message": f"Clicked using {by}",
                        "strategy": by,
                        "target": target,
                        "click_type": "normal",
                        "strategies_tried": strategies_tried,
                        "fallback_used": idx > 0
                    }
                except Exception as click_error:
                    # Click normale fallito - prova JS
                    error_msg = str(click_error)[:100]
                    if idx == 0:  # Log solo per prima strategia
                        print(f"   Strategy {idx+1}/{len(targets)} ({by}): normal click failed")
                
                # Try 2: JAVASCRIPT CLICK (fallback per strategia corrente)
                try:
                    element = await locator.first.element_handle(timeout=timeout_per_try)
                    if element:
                        await element.evaluate("el => el.click()")
                        return {
                            "status": "success",
                            "message": f"Clicked (JS) using {by}",
                            "strategy": by,
                            "target": target,
                            "click_type": "js",
                            "strategies_tried": strategies_tried,
                            "fallback_used": idx > 0
                        }
                except Exception as js_error:
                    last_error_msg = str(js_error)[:100]
                    # Se non è l'ultima strategia, continua con la prossima
                    if idx < len(targets) - 1:
                        print(f"   Strategy {idx+1}/{len(targets)} ({by}): failed, trying next...")
                        continue
            
            except Exception as e:
                last_error_msg = str(e)[:150]
                if idx < len(targets) - 1:
                    continue  # Prova prossima strategia

        # Tutte le strategie fallite
        return {
            "status": "error",
            "message": f"All {len(strategies_tried)} strategies failed. Last error: {last_error_msg}",
            "strategies_tried": strategies_tried,
            "last_error": last_error_msg
        }

    async def fill_smart(
        self,
        targets: List[Dict],
        value: str,
        timeout_per_try: int = AppConfig.AGENT.DEFAULT_TIMEOUT_PER_TRY,
        clear_first=True,
        in_iframe: dict = None
    ) -> dict:
        """
        Compila input con fallback chain automatico - prova tutte le strategie fino al successo.
        Resilienza massima: label manca? Prova placeholder. Placeholder vuoto? Prova role.
        Supporta interazioni dentro iframe (per app Angular embedded).

        Args:
            targets: Lista strategie ordinate per robustezza (da inspect_interactive_elements)
                Es: [
                    {"by": "label", "label": "Username"},
                    {"by": "placeholder", "placeholder": "Enter username"},
                    {"by": "role", "role": "textbox", "name": "Username"}
                ]
            value: Valore da inserire
            timeout_per_try: Timeout per ogni tentativo in ms (default: 2000ms)
            clear_first: Se True, pulisce campo prima di riempire
            in_iframe: dict per iframe (singolo o annidati)
                - Singolo: {"selector": "..."} o {"url_pattern": "..."}
                - Annidati: {"iframe_path": [{"url_pattern": "..."}, {"selector": "..."}]}

        Returns:
            dict con status, strategia usata, strategie provate

        Example:
            # Fill nella pagina principale
            result = await fill_smart([
                {"by": "label", "label": "Username"},
                {"by": "placeholder", "placeholder": "Enter username"}
            ], "test@example.com")
            
            # Fill dentro iframe singolo
            result = await fill_smart(
                targets=[{"by": "label", "label": "Codice"}],
                value="CARM",
                in_iframe={"url_pattern": "movementreason"}
            )
            
            # Fill dentro iframe annidati (portal → dashboard → input)
            result = await fill_smart(
                targets=[{"by": "label", "label": "Search"}],
                value="Product",
                in_iframe={"iframe_path": [
                    {"url_pattern": "portal"},
                    {"selector": "iframe.dashboard"}
                ]}
            )
        """
        if not self.page:
            return {
                "status": "error",
                "message": "Browser non avviato"
            }
        
        if not targets or len(targets) == 0:
            return {
                "status": "error",
                "message": "Nessuna strategia fornita (targets vuoto)"
            }

        # Determina context (page o iframe)
        context = self.page
        if in_iframe:
            frame_result = await self.get_frame(**in_iframe, timeout=timeout_per_try, return_frame=True)
            if frame_result["status"] == "error":
                return frame_result
            context = frame_result["frame"]

        # FALLBACK CHAIN: prova tutte le strategie fino al successo
        strategies_tried = []
        last_error_msg = ""
        
        for idx, target in enumerate(targets):
            by = target.get("by")
            strategies_tried.append(by)
            
            try:
                locator = None

                # Stesse strategie di click_smart
                if by == "role":
                    locator = context.get_by_role(
                        target.get("role"),
                        name=target.get("name")
                    )
                elif by == "label":
                    locator = context.get_by_label(target.get("label"))
                elif by == "placeholder":
                    locator = context.get_by_placeholder(
                        target.get("placeholder"))
                elif by == "tfa":
                    locator = context.locator(
                        f'[data-tfa="{target.get("tfa")}"]')
                elif by in ("css", "css_name", "css_id"):
                    selector = _normalize_css_selector(by, target)
                    locator = context.locator(selector) if selector else None
                elif by == "xpath":
                    locator = context.locator(f"xpath={target.get('xpath')}")
                
                if not locator:
                    last_error_msg = f"Impossibile creare locator per strategia '{by}'"
                    if idx < len(targets) - 1:
                        continue  # Prova prossima strategia
                    else:
                        break  # Ultima strategia - esci

                # FILL
                try:
                    # Clear first (se possibile)
                    if clear_first:
                        try:
                            await locator.first.clear(timeout=timeout_per_try)
                        except:
                            # Se clear fallisce (input readonly), continua
                            pass

                    # Fill
                    await locator.first.fill(value, timeout=timeout_per_try)

                    return {
                        "status": "success",
                        "message": f"Filled using {by}",
                        "strategy": by,
                        "target": target,
                        "value_length": len(value),
                        "strategies_tried": strategies_tried,
                        "fallback_used": idx > 0
                    }
                
                except Exception as fill_error:
                    last_error_msg = str(fill_error)[:150]
                    # Se non è l'ultima strategia, continua con la prossima
                    if idx < len(targets) - 1:
                        print(f"   Strategy {idx+1}/{len(targets)} ({by}): failed, trying next...")
                        continue

            except Exception as e:
                last_error_msg = str(e)[:150]
                if idx < len(targets) - 1:
                    continue  # Prova prossima strategia

        # Tutte le strategie fallite
        return {
            "status": "error",
            "message": f"All {len(strategies_tried)} strategies failed. Last error: {last_error_msg}",
            "strategies_tried": strategies_tried,
            "last_error": last_error_msg
        }

    # =====================================================================
    # INSPECTION - Scansione elementi interattivi (per smart/advanced)
    # =====================================================================

    async def inspect_interactive_elements(self, in_iframe: dict = None):
        """
        Scansiona TUTTI gli elementi interattivi della pagina usando solo standard web.
        Trova: iframe, button, link, input, select, textarea, checkbox, radio, switch, tabs + ARIA roles.
        Estrae: accessible_name, aria-label, role, testo visibile, checked state, options.

        Preferisce standard WCAG (role/label/text). Se presente, include anche `data-tfa`
        come fallback "test id" (utile in app corporate) ma con priorità più bassa.

        Args:
            in_iframe: opzionale dict per ispezionare l'interno di un iframe invece
                       della pagina principale. Stessa semantica usata da altri tool:
                       {"url_pattern": "..."} oppure {"selector": "..."} oppure
                       {"iframe_path": [{...}, {...}]} per iframe annidati.

        Returns:
            dict con:
            - iframes: Liste iframe con src/name
            - clickable_elements: Button, link, menu items → click_smart strategies
            - interactive_controls: Checkbox, radio, switch, tabs, select → click_smart strategies
            - form_fields: Text input, password, email, textarea → fill_smart strategies
            - page_info: URL, title

        Example:
            result = await inspect_interactive_elements()
            # Returns: {"iframes": [...], "clickable_elements": [...],
            #           "interactive_controls": [...], "form_fields": [...]}
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }

            # Determina il contesto: pagina principale o iframe selezionato
            context = self.page
            page_url = self.page.url
            page_title = await self.page.title()

            if in_iframe:
                # Usa get_frame per individuare il frame corretto (singolo o annidato)
                frame_result = await self.get_frame(
                    selector=in_iframe.get("selector"),
                    url_pattern=in_iframe.get("url_pattern"),
                    iframe_path=in_iframe.get("iframe_path"),
                    timeout=AppConfig.PLAYWRIGHT.TIMEOUT,
                    return_frame=True,
                )
                if frame_result.get("status") == "error":
                    return frame_result

                context = frame_result.get("frame")
                # Aggiorna info pagina con URL del frame, se disponibile
                page_url = frame_result.get("frame_url") or getattr(context, "url", page_url)
                try:
                    page_title = await context.title()
                except Exception:
                    # Alcuni frame potrebbero non avere titolo accessibile
                    pass

            # === 1. IFRAME (nel contesto corrente) ===
            iframes = await context.locator("iframe").all()
            iframe_info = []

            for idx, iframe in enumerate(iframes):
                try:
                    src = await iframe.get_attribute("src") or ""
                    title = await iframe.get_attribute("title") or ""
                    name = await iframe.get_attribute("name") or ""

                    iframe_info.append({
                        "index": idx,
                        "src": src,
                        "title": title,
                        "name": name,
                        "selector": f"iframe[src*='{src.split('/')[-1][:30]}']" if src else f"iframe >> nth={idx}"
                    })
                except Exception as e:
                    print(f"Error inspecting iframe {idx}: {e}")
                    continue

            # === 2. ELEMENTI CLICCABILI ===
            clickable_selector = (
                "button, a, input[type='submit'], input[type='button'], "
                "[role='button'], [role='link'], [role='menuitem'], [role='option'], "
                "div.ds-tab-navigation-link-container, div.ds-tab-navigation-link-text, "
                "div.ds-tool-card-wrapper, div.filter-wrapper.pointer, div.ds-add-button-container"
            )
            clickables = await context.locator(clickable_selector).all()
            clickable_info = []

            for idx, elem in enumerate(clickables):
                try:
                    tag = await elem.evaluate("el => el.tagName.toLowerCase()")
                    accessible_name = await elem.evaluate("""
                        el => {
                            if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
                            if (el.getAttribute('aria-labelledby')) {
                                const labelId = el.getAttribute('aria-labelledby');
                                const labelEl = document.getElementById(labelId);
                                if (labelEl) return labelEl.textContent.trim();
                            }
                            if (el.textContent && el.textContent.trim()) return el.textContent.trim();
                            if (el.title) return el.title;
                            if (el.value) return el.value;
                            return null;
                        }
                    """)
                    role = await elem.get_attribute("role")
                    aria_label = await elem.get_attribute("aria-label")
                    data_tfa = await elem.get_attribute("data-tfa")
                    effective_role = role if role else {
                        'button': 'button', 'a': 'link', 'input': 'button'
                    }.get(tag, None)
                    visible_text = ""
                    try:
                        visible_text = await elem.inner_text()
                        visible_text = visible_text.strip()[:100]
                    except Exception:
                        pass
                    suggestions = []
                    if effective_role and accessible_name:
                        suggestions.append({
                            "strategy": "role",
                            "click_smart": {"by": "role", "role": effective_role, "name": accessible_name}
                        })
                    if aria_label:
                        suggestions.append({
                            "strategy": "css_aria",
                            "click_smart": {"by": "css", "selector": f'[aria-label="{aria_label}"]'}
                        })
                    # Icon+label buttons (e.g. "add\n\nAGGIUNGI FILTRO"): add text with label only first,
                    # so get_by_text("AGGIUNGI FILTRO") is tried before the full string (which often times out).
                    if visible_text and "\n" in visible_text:
                        parts = [p.strip() for p in visible_text.split("\n") if p.strip()]
                        if parts:
                            label_only = parts[-1]
                            if len(label_only) >= 2 and label_only != visible_text.strip():
                                suggestions.append({
                                    "strategy": "text_label",
                                    "click_smart": {"by": "text", "text": label_only}
                                })
                    if visible_text:
                        suggestions.append({
                            "strategy": "text",
                            "click_smart": {"by": "text", "text": visible_text}
                        })
                    if data_tfa:
                        suggestions.append({
                            "strategy": "tfa",
                            "click_smart": {"by": "tfa", "tfa": data_tfa}
                        })
                    clickable_info.append({
                        "index": idx, "tag": tag, "role": effective_role,
                        "accessible_name": accessible_name, "text": visible_text,
                        "aria_label": aria_label, "data_tfa": data_tfa,
                        "playwright_suggestions": suggestions
                    })
                except Exception as e:
                    print(f"Error inspecting clickable {idx}: {e}")
                    continue

            # === 3. FORM FIELDS ===
            form_fields = await context.locator("input, select, textarea").all()
            field_info = []
            for idx, field in enumerate(form_fields):
                try:
                    tag = await field.evaluate("el => el.tagName.toLowerCase()")
                    field_type = await field.get_attribute("type") if tag == "input" else tag
                    accessible_name = await field.evaluate("""
                        el => {
                            if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
                            if (el.id) {
                                const label = document.querySelector(`label[for="${el.id}"]`);
                                if (label) return label.textContent.trim();
                            }
                            if (el.placeholder) return el.placeholder;
                            if (el.name) return el.name;
                            return null;
                        }
                    """)
                    aria_label = await field.get_attribute("aria-label")
                    placeholder = await field.get_attribute("placeholder") or ""
                    name = await field.get_attribute("name") or ""
                    input_id = await field.get_attribute("id") or ""
                    suggestions = []
                    if accessible_name:
                        suggestions.append({
                            "strategy": "label",
                            "fill_smart": {"by": "label", "label": accessible_name}
                        })
                    if placeholder:
                        suggestions.append({
                            "strategy": "placeholder",
                            "fill_smart": {"by": "placeholder", "placeholder": placeholder}
                        })
                    if field_type:
                        role_map = {
                            "text": "textbox", "email": "textbox", "password": "textbox",
                            "search": "searchbox", "tel": "textbox", "url": "textbox",
                            "select": "combobox", "textarea": "textbox"
                        }
                        role_name = role_map.get(field_type)
                        if role_name and accessible_name:
                            suggestions.append({
                                "strategy": "role",
                                "fill_smart": {"by": "role", "role": role_name, "name": accessible_name}
                            })
                    if name:
                        suggestions.append({
                            "strategy": "css_name",
                            "fill_smart": {"by": "css", "selector": f'[name="{name}"]'}
                        })
                    if input_id:
                        suggestions.append({
                            "strategy": "css_id",
                            "fill_smart": {"by": "css", "selector": f'#{input_id}'}
                        })
                    if aria_label:
                        suggestions.append({
                            "strategy": "css_aria",
                            "fill_smart": {"by": "css", "selector": f'[aria-label="{aria_label}"]'}
                        })
                    data_tfa = await field.get_attribute("data-tfa")
                    if data_tfa:
                        suggestions.append({
                            "strategy": "tfa",
                            "fill_smart": {"by": "tfa", "tfa": data_tfa}
                        })
                    field_info.append({
                        "index": idx, "tag": tag, "type": field_type,
                        "accessible_name": accessible_name, "aria_label": aria_label,
                        "placeholder": placeholder, "name": name, "id": input_id,
                        "playwright_suggestions": suggestions
                    })
                except Exception as e:
                    print(f"Error inspecting field {idx}: {e}")
                    continue

            # === 4. INTERACTIVE CONTROLS ===
            interactive_selector = """
                input[type='checkbox'], input[type='radio'], select, input[type='file'],
                input[type='range'], input[type='color'],
                [role='checkbox'], [role='radio'], [role='switch'], [role='tab'], [role='combobox']
            """
            interactives = await context.locator(interactive_selector).all()
            interactive_info = []
            for idx, elem in enumerate(interactives):
                try:
                    tag = await elem.evaluate("el => el.tagName.toLowerCase()")
                    elem_type = await elem.get_attribute("type") if tag == "input" else tag
                    role = await elem.get_attribute("role")
                    effective_type = role if role else elem_type
                    accessible_name = await elem.evaluate("""
                        el => {
                            if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
                            if (el.id) {
                                const label = document.querySelector(`label[for="${el.id}"]`);
                                if (label) return label.textContent.trim();
                            }
                            if (el.getAttribute('aria-labelledby')) {
                                const labelId = el.getAttribute('aria-labelledby');
                                const labelEl = document.getElementById(labelId);
                                if (labelEl) return labelEl.textContent.trim();
                            }
                            if (el.title) return el.title;
                            if (el.name) return el.name;
                            return null;
                        }
                    """)
                    aria_label = await elem.get_attribute("aria-label")
                    name = await elem.get_attribute("name") or ""
                    elem_id = await elem.get_attribute("id") or ""
                    data_tfa = await elem.get_attribute("data-tfa")
                    checked = None
                    if effective_type in ["checkbox", "radio", "switch"]:
                        checked = await elem.is_checked()
                    selected = None
                    if effective_type == "tab":
                        selected = await elem.get_attribute("aria-selected") == "true"
                    options = []
                    if tag == "select":
                        option_elements = await elem.locator("option").all()
                        for opt in option_elements:
                            opt_text = await opt.inner_text()
                            opt_value = await opt.get_attribute("value")
                            options.append({"text": opt_text.strip(), "value": opt_value})
                    suggestions = []
                    if effective_type in ["checkbox", "radio", "switch", "tab"]:
                        if accessible_name:
                            suggestions.append({
                                "strategy": "role",
                                "click_smart": {"by": "role", "role": effective_type, "name": accessible_name}
                            })
                        if accessible_name and tag == "input":
                            suggestions.append({
                                "strategy": "label",
                                "click_smart": {"by": "label", "label": accessible_name}
                            })
                        if accessible_name:
                            suggestions.append({
                                "strategy": "text",
                                "click_smart": {"by": "text", "text": accessible_name}
                            })
                        if aria_label:
                            suggestions.append({
                                "strategy": "css_aria",
                                "click_smart": {"by": "css", "selector": f'[aria-label="{aria_label}"]'}
                            })
                        if name:
                            suggestions.append({
                                "strategy": "css_name",
                                "click_smart": {"by": "css", "selector": f'[name="{name}"]'}
                            })
                        if data_tfa:
                            suggestions.append({
                                "strategy": "tfa",
                                "click_smart": {"by": "tfa", "tfa": data_tfa}
                            })
                    elif tag == "select":
                        suggestions.append({
                            "strategy": "note", "action": "select_option",
                            "message": "Use fill_smart with value, or click_smart to open dropdown then click option"
                        })
                    elif elem_type == "file":
                        suggestions.append({
                            "strategy": "note", "action": "set_input_files",
                            "message": "File upload requires dedicated tool (not yet implemented)"
                        })
                    elif elem_type in ["range", "color"] and accessible_name:
                        suggestions.append({
                            "strategy": "fill",
                            "fill_smart": {"by": "label", "label": accessible_name}
                        })
                    interactive_info.append({
                        "index": idx, "tag": tag, "type": effective_type,
                        "accessible_name": accessible_name, "aria_label": aria_label,
                        "name": name, "id": elem_id, "data_tfa": data_tfa,
                        "checked": checked, "selected": selected,
                        "options": options if options else None,
                        "playwright_suggestions": suggestions
                    })
                except Exception as e:
                    print(f"Error inspecting interactive {idx}: {e}")
                    continue

            return {
                "status": "success",
                "message": f"Found: {len(iframe_info)} iframes, {len(clickable_info)} clickable, {len(interactive_info)} interactive controls, {len(field_info)} form fields",
                "page_info": {"url": page_url, "title": page_title},
                "iframes": iframe_info,
                "clickable_elements": clickable_info,
                "interactive_controls": interactive_info,
                "form_fields": field_info
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error inspecting page: {str(e)}"
            }

    # =====================================================================
    # ADVANCED - Wait by name, cookie banner, composed
    # =====================================================================

    async def wait_for_clickable_by_name(
        self,
        name_substring: str,
        timeout: int = None,
        case_insensitive: bool = True,
    ):
        """
        Aspetta in modo POLLING che compaia un elemento CLICCABILE, usando solo
        i dati di `inspect_interactive_elements`.

        Logica:
        - chiama ripetutamente `inspect_interactive_elements()` entro `timeout`
        - guarda tutti i `clickable_elements`
        - se trova un elemento il cui `accessible_name` o testo visibile contiene
          `name_substring` (case-insensitive di default), lo restituisce subito,
          insieme a tutti i `click_smart` suggeriti.

        Args:
            name_substring: porzione di testo da cercare in accessible_name / text
                           (es. "Clinical Laboratory", "Filters", "Edit", "Causali").
            timeout: timeout massimo in millisecondi. Se None, usa AppConfig.PLAYWRIGHT.TIMEOUT.
            case_insensitive: se True (default), il match viene fatto in minuscolo.

        Returns:
            dict con:
              - status: "success" | "error"
              - message: descrizione umana del risultato
              - element: (solo in caso di success) il clickable come restituito da
                         `inspect_interactive_elements()["clickable_elements"][i]`
              - targets: (solo in caso di success) lista di oggetti `click_smart`
                         già pronta da passare a `click_smart(targets, ...)`.

        Uso tipico:
            res = await tools.wait_for_clickable_by_name("Clinical Laboratory", timeout=20000)
            if res["status"] == "success":
                await tools.click_smart(res["targets"])
        """
        import time

        if not self.page:
            return {
                "status": "error",
                "message": "Browser non avviato",
            }

        if timeout is None:
            timeout = AppConfig.PLAYWRIGHT.TIMEOUT

        start = time.time()
        needle = name_substring.lower() if case_insensitive else name_substring

        last_error = None

        while (time.time() - start) * 1000 < timeout:
            try:
                result = await self.inspect_interactive_elements()
                if result.get("status") != "success":
                    last_error = result.get("message")
                    await self.page.wait_for_timeout(500)
                    continue

                clickables = result.get("clickable_elements") or []

                # Prima raccogli tutti i candidati che contengono il testo,
                # poi scegli il migliore:
                #   1) match esatto (case-insensitive) se presente
                #   2) altrimenti il più "vicino" → stringa più corta
                candidates = []

                for elem in clickables:
                    raw_name = elem.get("accessible_name") or elem.get("text") or ""
                    haystack = raw_name.lower() if case_insensitive else raw_name

                    if needle in haystack:
                        candidates.append(
                            {
                                "elem": elem,
                                "raw_name": raw_name,
                                "haystack": haystack,
                                "exact": haystack == needle,
                            }
                        )

                if candidates:
                    # 1) Preferisci match esatto
                    exact_candidates = [c for c in candidates if c["exact"]]
                    if exact_candidates:
                        # se ce ne sono più di uno, prendi il più corto
                        best = min(exact_candidates, key=lambda c: len(c["haystack"]))
                    else:
                        # 2) Nessun match esatto → prendi comunque il più corto
                        best = min(candidates, key=lambda c: len(c["haystack"]))

                    elem = best["elem"]

                    suggestions = elem.get("playwright_suggestions") or []
                    targets = [
                        s["click_smart"]
                        for s in suggestions
                        if isinstance(s, dict) and "click_smart" in s
                    ]

                    # Fallback: usa role+name se non ci sono suggerimenti espliciti
                    if not targets and elem.get("role") and elem.get("accessible_name"):
                        targets = [
                            {
                                "by": "role",
                                "role": elem["role"],
                                "name": elem["accessible_name"],
                            }
                        ]

                    return {
                        "status": "success",
                        "message": f"Trovato clickable contenente '{name_substring}'",
                        "element": elem,
                        "targets": targets,
                    }

                await self.page.wait_for_timeout(500)
            except Exception as e:
                last_error = str(e)
                await self.page.wait_for_timeout(500)

        return {
            "status": "error",
            "message": (
                f"Clickable contenente '{name_substring}' non trovato entro {timeout} ms"
                + (f" (ultimo errore: {last_error})" if last_error else "")
            ),
        }

    async def wait_for_control_by_name_and_type(
        self,
        name_substring: str,
        control_type: str,
        timeout: int = None,
        case_insensitive: bool = True,
    ):
        """
        Aspetta in modo POLLING che compaia un CONTROLLO interattivo specifico,
        usando i dati di `inspect_interactive_elements()["interactive_controls"]`.

        È pensato per elementi come:
        - combobox (Angular Material `mat-select`, select HTML, ecc.)
        - checkbox / radio / switch
        - tab (role="tab")

        Args:
            name_substring: porzione di testo da cercare nell'`accessible_name`
                            del controllo (es. "Seleziona Organizzazione").
            control_type: tipo logico del controllo, come esposto in `type` dentro
                          `interactive_controls` (es. "combobox", "checkbox", "tab").
            timeout: timeout massimo in millisecondi. Se None, usa AppConfig.PLAYWRIGHT.TIMEOUT.
            case_insensitive: se True (default), match del nome in minuscolo.

        Returns:
            dict con:
              - status: "success" | "error"
              - message: descrizione
              - element: (success) l'interactive_control trovato
              - targets: (success) lista di `click_smart` già pronta per `click_smart`.

        Uso tipico:
            res = await tools.wait_for_control_by_name_and_type(
                "Seleziona Organizzazione",
                control_type="combobox",
                timeout=15000,
            )
            if res["status"] == "success":
                await tools.click_smart(res["targets"])
        """
        import time

        if not self.page:
            return {
                "status": "error",
                "message": "Browser non avviato",
            }

        if timeout is None:
            timeout = AppConfig.PLAYWRIGHT.TIMEOUT

        start = time.time()
        needle = name_substring.lower() if case_insensitive else name_substring
        desired_type = control_type.lower() if case_insensitive else control_type

        last_error = None

        while (time.time() - start) * 1000 < timeout:
            try:
                result = await self.inspect_interactive_elements()
                if result.get("status") != "success":
                    last_error = result.get("message")
                    await self.page.wait_for_timeout(500)
                    continue

                controls = result.get("interactive_controls") or []

                for ctrl in controls:
                    ctrl_type = (ctrl.get("type") or "").lower() if case_insensitive else (ctrl.get("type") or "")
                    raw_name = ctrl.get("accessible_name") or ""
                    haystack = raw_name.lower() if case_insensitive else raw_name

                    if desired_type == ctrl_type and needle in haystack:
                        suggestions = ctrl.get("playwright_suggestions") or []
                        targets = [
                            s["click_smart"]
                            for s in suggestions
                            if isinstance(s, dict) and "click_smart" in s
                        ]

                        # Fallback: prova role+name se non ci sono suggerimenti
                        if not targets and ctrl.get("type") and ctrl.get("accessible_name"):
                            targets = [
                                {
                                    "by": "role",
                                    "role": ctrl["type"],
                                    "name": ctrl["accessible_name"],
                                }
                            ]

                        return {
                            "status": "success",
                            "message": (
                                f"Controllo '{control_type}' contenente '{name_substring}' trovato"
                            ),
                            "element": ctrl,
                            "targets": targets,
                        }

                await self.page.wait_for_timeout(500)
            except Exception as e:
                last_error = str(e)
                await self.page.wait_for_timeout(500)

        return {
            "status": "error",
            "message": (
                f"Control type='{control_type}' contenente '{name_substring}' non trovato entro {timeout} ms"
                + (f" (ultimo errore: {last_error})" if last_error else "")
            ),
        }

    async def wait_for_field_by_name(
        self,
        name_substring: str,
        timeout: int = None,
        case_insensitive: bool = True,
    ):
        """
        Aspetta in modo POLLING che compaia un CAMPO FORM (input/textarea/select),
        utilizzando `inspect_interactive_elements()["form_fields"]`.

        Matcha se il campo ha:
        - `accessible_name` che contiene `name_substring`, oppure
        - `placeholder` che contiene `name_substring`, oppure
        - `name` che contiene `name_substring`.

        Args:
            name_substring: porzione di testo da cercare (es. "Username", "Password", "Cerca").
            timeout: timeout massimo in millisecondi. Se None, usa AppConfig.PLAYWRIGHT.TIMEOUT.
            case_insensitive: se True (default), match in minuscolo.

        Returns:
            dict con:
              - status: "success" | "error"
              - message: descrizione
              - element: (success) il form_field trovato
              - targets: (success) lista di oggetti `fill_smart` già pronta per `fill_smart`.
                         Se il tool non trova suggerimenti, prova un fallback CSS su id/name.

        Uso tipico:
            res = await tools.wait_for_field_by_name("Username", timeout=10000)
            if res["status"] == "success":
                await tools.fill_smart(res["targets"], "vdentato")
        """
        import time

        if not self.page:
            return {
                "status": "error",
                "message": "Browser non avviato",
            }

        if timeout is None:
            timeout = AppConfig.PLAYWRIGHT.TIMEOUT

        start = time.time()
        needle = name_substring.lower() if case_insensitive else name_substring

        last_error = None

        while (time.time() - start) * 1000 < timeout:
            try:
                result = await self.inspect_interactive_elements()
                if result.get("status") != "success":
                    last_error = result.get("message")
                    await self.page.wait_for_timeout(500)
                    continue

                fields = result.get("form_fields") or []

                for field in fields:
                    candidates = [
                        field.get("accessible_name") or "",
                        field.get("placeholder") or "",
                        field.get("name") or "",
                    ]
                    haystacks = [
                        c.lower() if case_insensitive else c
                        for c in candidates
                    ]

                    if any(needle in h for h in haystacks if h):
                        suggestions = field.get("playwright_suggestions") or []
                        targets = [
                            s["fill_smart"]
                            for s in suggestions
                            if isinstance(s, dict) and "fill_smart" in s
                        ]

                        # Fallback: se non ci sono suggerimenti, prova con css id/name generico
                        if not targets:
                            selector = None
                            if field.get("id"):
                                selector = f"#{field['id']}"
                            elif field.get("name"):
                                selector = f'[name="{field["name"]}"]'

                            if selector:
                                targets = [
                                    {"by": "css", "selector": selector},
                                ]

                        return {
                            "status": "success",
                            "message": f"Campo form contenente '{name_substring}' trovato",
                            "element": field,
                            "targets": targets,
                        }

                await self.page.wait_for_timeout(500)
            except Exception as e:
                last_error = str(e)
                await self.page.wait_for_timeout(500)

        return {
            "status": "error",
            "message": (
                f"Campo form contenente '{name_substring}' non trovato entro {timeout} ms"
                + (f" (ultimo errore: {last_error})" if last_error else "")
            ),
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

    async def click_and_wait_for_text(
        self,
        targets: List[Dict],
        text: str,
        timeout_per_try: int = AppConfig.AGENT.DEFAULT_TIMEOUT_PER_TRY,
        text_timeout: int = 30000,
        in_iframe: dict = None,
    ) -> dict:
        """
        Esegue click_smart con targets e poi wait_for_text_content per text.
        Utile per step critici (login, Continua, apertura moduli).
        """
        click_result = await self.click_smart(
            targets=targets,
            timeout_per_try=timeout_per_try,
            in_iframe=in_iframe,
        )
        if click_result.get("status") != "success":
            return {
                "status": "error",
                "message": f"click_smart failed: {click_result.get('message')}",
                "click": click_result,
                "text_check": None,
            }
        text_result = await self.wait_for_text_content(
            text=text,
            timeout=text_timeout,
            case_sensitive=False,
            in_iframe=in_iframe,
        )
        overall_status = "success" if text_result.get("status") == "success" else "error"
        return {
            "status": overall_status,
            "message": text_result.get("message"),
            "click": click_result,
            "text_check": text_result,
        }

