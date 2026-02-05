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


class PlaywrightTools:
    """
    Classe che contiene i tool per interagire con il browser tramite Playwright (ASYNC)
    """

    def __init__(self):
        """Inizializza Playwright"""
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    # =====================================================================
    # SMART LOCATORS - Nuovi Tool Robusti
    # =====================================================================
    async def click_smart(
        self,
        targets: List[Dict],
        timeout_per_try: int = 2000
    ) -> dict:
        """
        Click su elemento usando strategie multiple (fallback chain).
        Prova ogni strategia finché una funziona.

        Args:
            targets: Lista di strategie, es:
                [
                    {"by": "role", "role": "button", "name": "Micrologistica"},
                    {"by": "text", "text": "Micrologistica"},
                    {"by": "tfa", "tfa": "radPageMenuItem:Micrologistica"}
                ]
            timeout_per_try: Timeout per ogni tentativo (ms)

        Returns:
            dict con status e strategia usata

        Example:
            await click_smart([
                {"by": "role", "role": "button", "name": "Login"},
                {"by": "text", "text": "Login"}
            ])
        """
        if not self.page:
            return {
                "status": "error",
                "message": "Browser non avviato. Chiama start_browser() prima."
            }

        for idx, target in enumerate(targets):
            try:
                locator = None
                by = target.get("by")

                # Strategy 1: Role-based (WCAG accessible)
                if by == "role":
                    role = target.get("role")
                    name = target.get("name")
                    locator = self.page.get_by_role(role, name=name)

                # Strategy 2: Label (form fields)
                elif by == "label":
                    label = target.get("label")
                    locator = self.page.get_by_label(label)

                # Strategy 3: Placeholder
                elif by == "placeholder":
                    placeholder = target.get("placeholder")
                    locator = self.page.get_by_placeholder(placeholder)

                # Strategy 4: Text content
                elif by == "text":
                    text = target.get("text")
                    locator = self.page.get_by_text(text)

                # Strategy 5: Test automation ID (data-tfa)
                elif by == "tfa":
                    tfa = target.get("tfa")
                    locator = self.page.locator(f'[data-tfa="{tfa}"]')

                # Strategy 6: CSS selector (fallback)
                elif by == "css":
                    selector = target.get("selector")
                    locator = self.page.locator(selector)

                # Strategy 7: XPath (last resort)
                elif by == "xpath":
                    xpath = target.get("xpath")
                    locator = self.page.locator(f"xpath={xpath}")

                if locator:
                    # ========================================================
                    # FALLBACK CHAIN - 3 LIVELLI DI CLICK (dal più sicuro al meno)
                    # ========================================================

                    # Try 1: CLICK NORMALE con RETRY (preferito - più sicuro)
                    # - Aspetta che elemento sia visibile
                    # - RETRY automatico per gestire animazioni Angular (visibility:hidden → visible)
                    # - Backoff progressivo: 0.5s → 1.5s → 3s (totale max ~5s)
                    # - Verifica che sia actionable (non coperto, non disabilitato)
                    # - Verifica che sia stabile (non si muove durante animazioni)
                    # - Funziona per: <button>, <a>, <input type="button/submit">
                    # - FALLISCE per: DIV con role="button", elementi con visibility:hidden permanente
                    max_retries = 1  # Ridotto da 3 per velocità (fallback comunque presente)
                    # ms - backoff progressivo
                    retry_delays = [500, 1500, 3000]

                    for retry in range(max_retries):
                        try:
                            await locator.first.wait_for(
                                state="visible",
                                timeout=timeout_per_try
                            )
                            await locator.first.click()

                            retry_info = f" (retry {retry+1})" if retry > 0 else ""
                            return {
                                "status": "success",
                                "message": f"Clicked using strategy #{idx+1}: {by}{retry_info}",
                                "strategy": by,
                                "target": target,
                                "retries": retry
                            }

                        except Exception as click_error:
                            # DEBUG: mostra motivo fallimento
                            error_type = type(click_error).__name__
                            error_msg = str(click_error)[:100]
                            print(f"   🐛 DEBUG: Strategy #{idx+1} ({by}) retry {retry+1} failed - {error_type}: {error_msg}")
                            
                            # Se non è l'ultimo retry, aspetta e riprova
                            if retry < max_retries - 1:
                                await self.page.wait_for_timeout(retry_delays[retry])
                                continue
                            # Ultimo retry fallito, passa a Try 2 (force click)
                            print(f"   🐛 DEBUG: All retries exhausted for strategy #{idx+1} ({by}), trying force click...")
                            pass
                    
                    # Try 2: FORCE CLICK (intermedio - bypassa actionability)
                    # - Salta verifica "è semanticamente clickable?"
                    # - NON bypassa visibilità (elemento deve essere visibile)
                    # - Funziona per: DIV/SPAN con CSS pointer-events:auto (Angular Material)
                    # - FALLISCE per: elementi completamente nascosti (visible:False)
                    # - Usa questo per framework UI moderni che abusano di DIV
                    # - SKIP: se elemento non è visibile (evita false positive - force click non attiva JS)
                    try:
                        # Verifica che elemento sia visibile prima di force click
                        is_visible = await locator.first.is_visible()
                        if not is_visible:
                            # Elemento non visibile - skip force, vai diretto a JS click
                            print(f"   🐛 DEBUG: Element not visible for force click, skipping to JS click")
                            raise Exception("Element not visible - skip force click")
                        
                        await locator.first.click(force=True)
                        
                        return {
                            "status": "success",
                            "message": f"Clicked (force) using strategy #{idx+1}: {by}",
                            "strategy": by,
                            "force_click": True,
                            "target": target
                        }
                    except Exception as force_error:
                        # DEBUG: mostra motivo fallimento force click
                        error_type = type(force_error).__name__
                        error_msg = str(force_error)[:100]
                        print(f"   🐛 DEBUG: Force click failed - {error_type}: {error_msg}")
                        print(f"   🐛 DEBUG: Trying JS click as last resort...")
                        
                        # Try 3: JAVASCRIPT CLICK (ultima risorsa - bypassa TUTTO)
                        # - Bypassa TUTTI i controlli Playwright (visibilità, actionability, stabilità)
                        # - Esegue click diretto sul DOM via JavaScript
                        # - Funziona per: elementi off-viewport, opacity:0, visibility:hidden permanente
                        # - RISCHIO: può cliccare elementi che l'utente reale non vedrebbe
                        # - Usa questo SOLO quando hai verificato che l'elemento esiste ma Playwright non lo vede
                        try:
                            element = await locator.first.element_handle()
                            if element:
                                await element.evaluate("el => el.click()")
                                return {
                                    "status": "success",
                                    "message": f"Clicked (JS) using strategy #{idx+1}: {by}",
                                    "strategy": by,
                                    "js_click": True,
                                    "target": target
                                }
                        except:
                            # Questa strategia non funziona, continua con prossimo target
                            continue

            except Exception as e:
                # Questa strategia non ha funzionato, prova la prossima
                continue

        # Nessuna strategia ha funzionato
        strategies_tried = [t.get("by") for t in targets]
        return {
            "status": "error",
            "message": f"No target matched. Tried: {', '.join(strategies_tried)}",
            "strategies_tried": strategies_tried
        }

    async def fill_smart(
        self,
        targets: List[Dict],
        value: str,
        timeout_per_try: int = 2000,
        clear_first=True
    ) -> dict:
        """
        Compila input usando strategie multiple (fallback chain).

        Args:
            targets: Lista di strategie (stesso formato di click_smart)
            value: Valore da inserire
            timeout_per_try: Timeout per ogni tentativo (ms)

        Returns:
            dict con status e strategia usata

        Example:
            await fill_smart([
                {"by": "label", "label": "Username"},
                {"by": "placeholder", "placeholder": "Username"},
                {"by": "role", "role": "textbox", "name": "Username"}
            ], "test@example.com")
        """
        if not self.page:
            return {
                "status": "error",
                "message": "Browser non avviato"
            }

        for idx, target in enumerate(targets):
            try:
                locator = None
                by = target.get("by")

                # Stesse strategie di click_smart
                if by == "role":
                    locator = self.page.get_by_role(
                        target.get("role"),
                        name=target.get("name")
                    )
                elif by == "label":
                    locator = self.page.get_by_label(target.get("label"))
                elif by == "placeholder":
                    locator = self.page.get_by_placeholder(
                        target.get("placeholder"))
                elif by == "tfa":
                    locator = self.page.locator(
                        f'[data-tfa="{target.get("tfa")}"]')
                elif by == "css":
                    locator = self.page.locator(target.get("selector"))
                elif by == "xpath":
                    locator = self.page.locator(f"xpath={target.get('xpath')}")

                if locator:
                    # RETRY LOOP (coerenza con click_smart)
                    # - Gestisce input in caricamento/animazione
                    # - Backoff progressivo: 0.5s → 1.5s → 3s
                    max_retries = 1  # Ridotto da 3 per velocità
                    retry_delays = [500, 1500, 3000]  # ms

                    for retry in range(max_retries):
                        try:
                            # Wait for visible
                            await locator.first.wait_for(
                                state="visible",
                                timeout=timeout_per_try
                            )

                            # Clear first (se possibile)
                            if clear_first:
                                try:
                                    await locator.first.clear(timeout=timeout_per_try)
                                except:
                                    # Se clear fallisce (input readonly), continua
                                    pass

                            # Fill
                            await locator.first.fill(value, timeout=timeout_per_try)

                            retry_info = f" (retry {retry+1})" if retry > 0 else ""
                            return {
                                "status": "success",
                                "message": f"Filled using strategy #{idx+1}: {by}{retry_info}",
                                "strategy": by,
                                "target": target,
                                "value_length": len(value),
                                "retries": retry
                            }

                        except Exception as fill_error:
                            # Se non è l'ultimo retry, aspetta e riprova
                            if retry < max_retries - 1:
                                await self.page.wait_for_timeout(retry_delays[retry])
                                continue
                            # Ultimo retry fallito, passa a prossima strategia
                            pass

            except asyncio.TimeoutError:
                # Timeout su questo tentativo, prova prossima strategia
                continue
            except Exception as e:
                # Altro errore, prova prossima strategia
                continue

        strategies_tried = [t.get("by") for t in targets]
        return {
            "status": "error",
            "message": f"No target matched for fill. Tried: {', '.join(strategies_tried)}",
            "strategies_tried": strategies_tried
        }

    # =====================================================================
    # TOOL ORIGINALI (mantieni compatibilità)
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
                screenshot_base64 = base64.b64encode(
                    screenshot_bytes).decode('utf-8')
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

    async def inspect_interactive_elements(self):
        """
        Scansiona TUTTI gli elementi interattivi della pagina usando solo standard web.
        Trova: iframe, button, link, input, select, textarea + ARIA roles.
        Estrae: accessible_name, aria-label, role, testo visibile.

        IGNORA attributi custom (data-*, ng-*, class) - usa solo standard WCAG.

        Returns:
            dict con iframe, clickable_elements, form_fields, page_info

        Example:
            result = await inspect_interactive_elements()
            # Trova: {"iframes": [...], "clickable": [...], "inputs": [...]}
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "Browser non avviato"
                }

            # === 1. IFRAME ===
            iframes = await self.page.locator("iframe").all()
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
            # Selector bilanciato tra copertura e precisione:
            # - HTML nativi: button, a, input[submit/button] (semantici, standard)
            # - ARIA roles: [role='button/link/menuitem'] (framework moderni - Angular/React)
            # INCLUSIONI: copre 99% UI moderne, trova Micrologistica (DIV con role="button")
            # ESCLUSIONI: NO div/span senza role (troppi falsi positivi), NO [onclick] (deprecato)
            clickable_selector = "button, a, input[type='submit'], input[type='button'], [role='button'], [role='link'], [role='menuitem']"
            clickables = await self.page.locator(clickable_selector).all()
            clickable_info = []

            for idx, elem in enumerate(clickables):
                try:
                    tag = await elem.evaluate("el => el.tagName.toLowerCase()")

                    # Accessible name (WCAG standard) - RICHIEDE JAVASCRIPT:
                    # 1. aria-labelledby richiede DOM traversal (getElementById) - impossibile da Python
                    # 2. Algoritmo prioritario condizionale (aria-label → aria-labelledby → text → title → value)
                    # 3. Python get_attribute() restituirebbe solo stringhe grezze, non il "nome computato"
                    # Spec: https://www.w3.org/TR/accname-1.1/
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

                    # ARIA attributes
                    role = await elem.get_attribute("role")
                    aria_label = await elem.get_attribute("aria-label")
                    
                    # Test automation ID
                    data_tfa = await elem.get_attribute("data-tfa")

                    # Effective role (se non esplicito, deduci dal tag)
                    effective_role = role if role else {
                        'button': 'button',
                        'a': 'link',
                        'input': 'button'
                    }.get(tag, None)

                    # Testo visibile
                    visible_text = ""
                    try:
                        visible_text = await elem.inner_text()
                        visible_text = visible_text.strip()[:100]
                    except:
                        pass

                    # Playwright locator suggestions (TUTTE le strategie supportate da click_smart)
                    # Ordine di preferenza: role > text > css_aria > tfa (ultima - più fragile)
                    suggestions = []
                    
                    # 1. Role (WCAG - più affidabile)
                    if effective_role and accessible_name:
                        suggestions.append({
                            "strategy": "role",
                            "click_smart": {"by": "role", "role": effective_role, "name": accessible_name}
                        })
                    
                    # 2. Text content (semplice e robusto)
                    if visible_text:
                        suggestions.append({
                            "strategy": "text",
                            "click_smart": {"by": "text", "text": visible_text}
                        })
                    
                    # 3. Aria-label via CSS (fallback)
                    if aria_label:
                        suggestions.append({
                            "strategy": "css_aria",
                            "click_smart": {"by": "css", "selector": f'[aria-label="{aria_label}"]'}
                        })
                    
                    # 4. Data-tfa (ultima - IDs possono cambiare con refactoring)
                    if data_tfa:
                        suggestions.append({
                            "strategy": "tfa",
                            "click_smart": {"by": "tfa", "tfa": data_tfa}
                        })

                    clickable_info.append({
                        "index": idx,
                        "tag": tag,
                        "role": effective_role,
                        "accessible_name": accessible_name,
                        "text": visible_text,
                        "aria_label": aria_label,
                        "data_tfa": data_tfa,
                        "playwright_suggestions": suggestions
                    })
                except Exception as e:
                    print(f"Error inspecting clickable {idx}: {e}")
                    continue

            # === 3. FORM FIELDS ===
            form_fields = await self.page.locator("input, select, textarea").all()
            field_info = []

            for idx, field in enumerate(form_fields):
                try:
                    tag = await field.evaluate("el => el.tagName.toLowerCase()")
                    field_type = await field.get_attribute("type") if tag == "input" else tag

                    # Accessible name per input
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

                    # Playwright locator suggestions (TUTTE le strategie supportate da fill_smart)
                    # Ordine di preferenza: label > placeholder > role > CSS fallback > tfa (ultima)
                    suggestions = []
                    
                    # 1. Label (form best practice)
                    if accessible_name:
                        suggestions.append({
                            "strategy": "label",
                            "fill_smart": {"by": "label", "label": accessible_name}
                        })
                    
                    # 2. Placeholder (visual hint)
                    if placeholder:
                        suggestions.append({
                            "strategy": "placeholder",
                            "fill_smart": {"by": "placeholder", "placeholder": placeholder}
                        })
                    
                    # 3. Role (ARIA)
                    if field_type:
                        role_map = {
                            "text": "textbox",
                            "email": "textbox",
                            "password": "textbox",
                            "search": "searchbox",
                            "tel": "textbox",
                            "url": "textbox",
                            "select": "combobox",
                            "textarea": "textbox"
                        }
                        role_name = role_map.get(field_type)
                        if role_name and accessible_name:
                            suggestions.append({
                                "strategy": "role",
                                "fill_smart": {"by": "role", "role": role_name, "name": accessible_name}
                            })
                    
                    # 4. CSS fallback - name attribute
                    if name:
                        suggestions.append({
                            "strategy": "css_name",
                            "fill_smart": {"by": "css", "selector": f'[name="{name}"]'}
                        })
                    
                    # 5. CSS fallback - id attribute
                    if input_id:
                        suggestions.append({
                            "strategy": "css_id",
                            "fill_smart": {"by": "css", "selector": f'#{input_id}'}
                        })
                    
                    # 6. CSS fallback - aria-label
                    if aria_label:
                        suggestions.append({
                            "strategy": "css_aria",
                            "fill_smart": {"by": "css", "selector": f'[aria-label="{aria_label}"]'}
                        })
                    
                    # 7. Data-tfa (ultima - IDs possono cambiare con refactoring)
                    data_tfa = await field.get_attribute("data-tfa")
                    if data_tfa:
                        suggestions.append({
                            "strategy": "tfa",
                            "fill_smart": {"by": "tfa", "tfa": data_tfa}
                        })

                    field_info.append({
                        "index": idx,
                        "tag": tag,
                        "type": field_type,
                        "accessible_name": accessible_name,
                        "aria_label": aria_label,
                        "placeholder": placeholder,
                        "name": name,
                        "id": input_id,
                        "playwright_suggestions": suggestions
                    })
                except Exception as e:
                    print(f"Error inspecting field {idx}: {e}")
                    continue

            return {
                "status": "success",
                "message": f"Found: {len(iframe_info)} iframes, {len(clickable_info)} clickable, {len(field_info)} form fields",
                "page_info": {
                    "url": self.page.url,
                    "title": await self.page.title()
                },
                "iframes": iframe_info,
                "clickable_elements": clickable_info,
                "form_fields": field_info
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error inspecting page: {str(e)}"
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

    async def wait_for_text_content(
        self,
        text: str,
        timeout: int = 30000,
        case_sensitive: bool = False
    ):
        """
        Aspetta che un testo specifico appaia OVUNQUE nella pagina.
        Utile per verificare messaggi di successo, titoli, nomi elementi dopo azioni AJAX.

        Args:
            text: Testo da cercare
            timeout: Timeout in ms (default: 30000)
            case_sensitive: Se True, match esatto (default: False)

        Returns:
            dict con status e informazioni sul testo trovato

        Example:
            # Dopo login, aspetta che appaia "Dashboard"
            await wait_for_text_content("Dashboard", timeout=10000)

            # Dopo click su CDC, aspetta il nome
            await wait_for_text_content("CDC #3", timeout=5000)
        """
        if not self.page:
            return {
                "status": "error",
                "message": "Browser non avviato"
            }
        try:
            # Costruisci selector Playwright per text
            if case_sensitive:
                selector = f"text={text}"
            else:
                # Case-insensitive con regex
                selector = f"text=/{text}/i"

            # Aspetta che l'elemento con quel testo sia visibile
            await self.page.wait_for_selector(
                selector,
                timeout=timeout,
                state="visible"
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

    async def wait_for_load_state(
        self,
        state: Literal["load", "domcontentloaded", "networkidle"] = "domcontentloaded",  # load=tutto caricato, domcontentloaded=DOM pronto, networkidle=rete inattiva
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

    async def inspect_dom_changes(
        self,
        click_target: dict,
        wait_after_click: int = 2000
    ):
        """
        Ispeziona cosa cambia nel DOM dopo un click.
        Utile per capire se un click apre menu, submenu, popup, nuove sezioni.

        Args:
            click_target: Target da cliccare (formato click_smart)
            wait_after_click: Millisecondi da aspettare dopo click (default: 2000)

        Returns:
            dict con:
            - elements_added: nuovi elementi apparsi
            - elements_removed: elementi scomparsi
            - visibility_changed: elementi che hanno cambiato visibilità
            - recommendations: suggerimenti su cosa fare dopo

        Example:
            # Scopri cosa succede dopo click su "Micrologistica"
            changes = await inspect_dom_changes(
                click_target={"by": "text", "text": "Micrologistica"},
                wait_after_click=3000
            )
        """
        if not self.page:
            return {"status": "error", "message": "Browser non avviato"}

        try:
            # 1. Cattura stato PRIMA del click
            before_state = await self.page.evaluate("""
                () => {
                    const state = {
                        interactive: [],
                        visible_text: []
                    };
                    
                    // Cattura tutti gli elementi interattivi visibili
                    const selectors = ['button', 'a', '[role="button"]', '[role="menuitem"]', '[role="tab"]'];
                    selectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                const text = el.textContent?.trim().substring(0, 50) || '';
                                const id = el.id || '';
                                const classes = el.className || '';
                                
                                state.interactive.push({
                                    tag: el.tagName.toLowerCase(),
                                    text: text,
                                    id: id,
                                    classes: classes,
                                    role: el.getAttribute('role') || '',
                                    signature: `${el.tagName}:${text}:${id}`
                                });
                            }
                        });
                    });
                    
                    return state;
                }
            """)

            # 2. Esegui il click
            result = await self.click_smart([click_target])

            if result["status"] != "success":
                return {
                    "status": "error",
                    "message": f"Click fallito: {result['message']}"
                }

            # 3. Aspetta dopo click
            await self.page.wait_for_timeout(wait_after_click)

            # 4. Cattura stato DOPO il click
            after_state = await self.page.evaluate("""
                () => {
                    const state = {
                        interactive: [],
                        visible_text: []
                    };
                    
                    const selectors = ['button', 'a', '[role="button"]', '[role="menuitem"]', '[role="tab"]'];
                    selectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                const text = el.textContent?.trim().substring(0, 50) || '';
                                const id = el.id || '';
                                const classes = el.className || '';
                                
                                state.interactive.push({
                                    tag: el.tagName.toLowerCase(),
                                    text: text,
                                    id: id,
                                    classes: classes,
                                    role: el.getAttribute('role') || '',
                                    signature: `${el.tagName}:${text}:${id}`
                                });
                            }
                        });
                    });
                    
                    return state;
                }
            """)

            # 5. Confronta stati
            before_sigs = set(el['signature']
                              for el in before_state['interactive'])
            after_sigs = set(el['signature']
                             for el in after_state['interactive'])

            # Nuovi elementi
            added_sigs = after_sigs - before_sigs
            elements_added = [
                el for el in after_state['interactive'] if el['signature'] in added_sigs]

            # Elementi rimossi
            removed_sigs = before_sigs - after_sigs
            elements_removed = [
                el for el in before_state['interactive'] if el['signature'] in removed_sigs]

            # Genera raccomandazioni
            recommendations = []

            if elements_added:
                # Nuovi elementi -> probabilmente menu/submenu
                menu_items = [
                    el for el in elements_added if 'menu' in el.get('role', '').lower()]
                buttons = [
                    el for el in elements_added if el['tag'] == 'button']
                links = [el for el in elements_added if el['tag'] == 'a']

                if menu_items:
                    recommendations.append({
                        "type": "submenu_detected",
                        "message": f"Rilevato submenu con {len(menu_items)} item",
                        "action": f"Clicca su uno dei menu item: {[m['text'] for m in menu_items[:3]]}"
                    })

                if buttons:
                    recommendations.append({
                        "type": "new_buttons",
                        "message": f"{len(buttons)} nuovi button apparsi",
                        "action": f"Prova a cliccare: {[b['text'] for b in buttons[:3]]}"
                    })

                if links:
                    recommendations.append({
                        "type": "new_links",
                        "message": f"{len(links)} nuovi link apparsi",
                        "action": f"Naviga a: {[l['text'] for l in links[:3]]}"
                    })
            else:
                # Nessun nuovo elemento -> forse navigazione o stato interno
                recommendations.append({
                    "type": "no_visible_changes",
                    "message": "Nessun nuovo elemento visibile apparso",
                    "action": "Potrebbe essere: 1) navigazione SPA (URL non cambia), 2) serve doppio click, 3) serve più tempo"
                })

            return {
                "status": "success",
                "click_performed": True,
                "elements_added": elements_added[:10],  # max 10 per brevità
                "elements_removed": elements_removed[:10],
                "count_added": len(elements_added),
                "count_removed": len(elements_removed),
                "recommendations": recommendations
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore durante ispezione: {str(e)}"
            }

    # =====================================================================
    # IFRAME SUPPORT
    # =====================================================================
    async def get_frame(
        self,
        selector: str = None,
        url_pattern: str = None,
        timeout: int = 10000,
        return_frame: bool = False,
    ):
        """
        Accede al contenuto di un iframe.

        Args:
            selector: CSS selector dell'iframe (es: 'iframe[src*="movementreason"]')
            url_pattern: Pattern dell'URL dell'iframe (alternativa a selector)
            timeout: Timeout in ms

        Returns:
            dict JSON-serializzabile con metadata iframe/frame.
            Se return_frame=True include anche l'oggetto Frame (NON serializzabile) per uso interno.

        Example:
            frame = await get_frame(url_pattern="registry/movementreason")
            await frame.fill("input[type='text']", "carm")
        """
        if not self.page:
            return {"status": "error", "message": "Browser non avviato"}

        try:
            # Trova iframe
            iframe_selector_used = None
            if selector:
                iframe_selector_used = selector
            elif url_pattern:
                iframe_selector_used = f'iframe[src*="{url_pattern}"]'
            else:
                iframe_selector_used = 'iframe'

            iframe_element = await self.page.wait_for_selector(iframe_selector_used, timeout=timeout)

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
    # SMART NAVIGATION (procedural approach)
    # =====================================================================
    async def fill_and_search(
        self,
        input_selector: str,
        search_value: str,
        verify_result_text: str = None,
        in_iframe: dict = None,
        timeout: int = 10000,
    ):
        """
        Riempie campo input e verifica risultati (approccio procedurale).
        Supporta iframe automaticamente.

        Args:
            input_selector: Selettore del campo input
            search_value: Valore da inserire
            verify_result_text: Testo da verificare nei risultati (opzionale)
            in_iframe: {"selector": "..."} o {"url_pattern": "..."} se dentro iframe

        Returns:
            dict con status

        Example:
            await fill_and_search(
                input_selector="input[type='text']",
                search_value="carm",
                verify_result_text="CARMAG",
                in_iframe={"url_pattern": "movementreason"}
            )
        """
        try:
            # 1. Accedi al contesto (page o iframe)
            context = self.page

            if in_iframe:
                frame_result = await self.get_frame(**in_iframe, timeout=timeout, return_frame=True)
                if frame_result["status"] == "error":
                    return frame_result
                context = frame_result["frame"]

            # 2. Riempie campo
            await context.fill(input_selector, search_value)
            await asyncio.sleep(1)  # Aspetta risultati

            # 3. Verifica risultato (se specificato)
            if verify_result_text:
                count = await context.locator(f"text={verify_result_text}").count()
                if count == 0:
                    return {
                        "status": "warning",
                        "message": f"Campo riempito ma risultato '{verify_result_text}' non trovato"
                    }

                return {
                    "status": "success",
                    "message": f"Ricerca OK - {count} risultati trovati",
                    "results_count": count
                }

            return {
                "status": "success",
                "message": "Campo riempito correttamente"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Errore fill_and_search: {str(e)}"
            }
