## Guida pratica ai tool Playwright MCP

Questa guida descrive i tool definiti in `tools.py` e esposti dal server MCP: cosa fanno, quali input si aspettano (a livello concettuale), esempi di output e perché li usiamo nei flussi AMC / LAB.

**Elenco dei 15 tool esposti dal server** (coerente con `mcp_servers/tool_names.py` e con la sezione "Tool Playwright Disponibili" del `backend/README.md`):

1. `start_browser`  
2. `navigate_to_url`  
3. `wait_for_load_state`  
4. `capture_screenshot`  
5. `close_browser`  
6. `get_page_info`  
7. `wait_for_element`  
8. `get_text`  
9. `press_key`  
10. `inspect_interactive_elements`  
11. `handle_cookie_banner`  
12. `click_smart`  
13. `fill_smart`  
14. `wait_for_text_content`  
15. `get_frame`  

Le categorie in questa guida:
- **Lifecycle & pagina**: `start_browser`, `navigate_to_url`, `close_browser`, `capture_screenshot`, `get_page_info`
- **Wait & load**: `wait_for_load_state`, `wait_for_text_content`, `wait_for_element`
- **Discovery**: `inspect_interactive_elements`
- **Smart locators**: `click_smart`, `fill_smart`
- **Base aggiuntivi**: `get_text`, `press_key`, `handle_cookie_banner`, `get_frame`

Gli esempi di input/output sono semplificati per chiarezza (il vero payload JSON passa attraverso MCP).

---

### Lifecycle & pagina

#### `start_browser(headless: bool = False)`

- **Scopo**: avvia Chromium in modalità “stealth” con viewport/locale/timezone presi da `AppConfig.PLAYWRIGHT`.
- **Input concettuale**

```json
{
  "headless": false
}
```

- **Output tipico**

```json
{
  "status": "success",
  "message": "Browser avviato con successo (stealth mode)",
  "headless": false
}
```

Usato come primo step di tutti i flussi agentici.

#### `navigate_to_url(url: str)`

- **Scopo**: naviga a un URL e aspetta `domcontentloaded`.
- **Perché**: evitare timeout infiniti di `networkidle` su SPA moderne.

```json
{
  "url": "https://lab.example.com/"
}
```

```json
{
  "status": "success",
  "url": "https://lab.example.com/",
  "title": "Preanalitica",
  "viewport": {"width": 960, "height": 1080}
}
```

#### `get_page_info()`

- **Scopo**: leggere rapidamente `url`, `title`, viewport senza navigare.
- **Perché**: verifiche rapide tipo “sei davvero nel modulo Laboratory?” senza azioni pesanti.
- **Input**: nessuno (chiamata senza parametri).
- **Output tipico**: `{"status": "success", "url": "...", "title": "...", "viewport": {"width": 960, "height": 1080}}`.

#### `wait_for_load_state(state: str, timeout: int = 30000)`

- **Scopo**: aspettare che la pagina raggiunga un certo stato di caricamento (eventi DOM/rete).
- **Parametri**:
  - `state`: `"domcontentloaded"` (DOM pronto, più veloce), `"load"` (risorse caricate), `"networkidle"` (rete quasi ferma; utile dopo login/navigazione ma può andare in timeout su SPA con polling).
  - `timeout`: millisecondi.
- **Perché ci serve**: dopo login, dopo click su “Continua” o sul tile LAB, usiamo questo come “barriera” prima di ispezionare o cliccare (evita click su elementi non ancora pronti).
- **Input esempio**: `{"state": "networkidle", "timeout": 30000}`.
- **Output successo**: `{"status": "success", "message": "Load state 'networkidle' raggiunto", "state": "networkidle", "timeout_ms": 30000}`.

#### `capture_screenshot(filename: str | None, return_base64: bool = False)`

- **Scopo**: catturare screenshot per debug/report.
- **Decisione importante**: usiamo `return_base64=false` anche sullo **screenshot di successo** per non superare il limite di contesto del modello.

Esempio di chiamata su successo:

```json
{
  "filename": "test_success.png",
  "return_base64": false
}
```

Output:

```json
{
  "status": "success",
  "message": "Screenshot catturato: test_success.png",
  "filename": "test_success.png",
  "size_bytes": 60890
}
```

#### `close_browser()`

- **Scopo**: chiude pagina, context, browser e ferma Playwright.
- Nei prompt:
  - **AMC / LAB scenario**: va sempre chiamato alla fine (successo/errore).
  - **LAB prefix agent**: esplicitamente vietato (il browser deve restare aperto per la fase scenario).

---

### Wait & assert testo

#### `wait_for_text_content(text: str, timeout: int = 30000, case_sensitive: bool = False, in_iframe: dict | None = None)`

- **Scopo**: aspetta che un testo appaia nella pagina (o in un iframe).
- **Perché**: è il nostro “segnale forte” che una certa view è caricata (titolo pagina, messaggi di esito).

Esempio:

```json
{
  "text": "Preanalitica",
  "timeout": 30000
}
```

Successo:

```json
{
  "status": "success",
  "text": "Preanalitica",
  "location": {
    "frame_url": "https://lab.../preanalitica",
    "selector": "h1.page-title"
  }
}
```

Timeout:

```json
{
  "status": "error",
  "message": "Testo 'Preanalitica' non trovato dopo 30000ms",
  "text": "Preanalitica",
  "timeout_ms": 30000
}
```

Nei prompt LAB lo usiamo per verificare che il modulo sia caricato (prima `"Preanalitica"`, poi eventuali fallback `"Laboratorio"`, `"Clinica"`, `"Ceppoteca"`).

---

### Discovery: `inspect_interactive_elements`

#### `inspect_interactive_elements(in_iframe: dict | None = None)`

- **Scopo**: scansiona pagina/iframe e restituisce:
  - `iframes`
  - `clickable_elements`
  - `interactive_controls`
  - `form_fields`
  - `page_info`
- **Perché**: abilita il pattern **discovery-first**; il modello non deve inventare selettori.

Esempio di output (semplificato):

```json
{
  "status": "success",
  "page_info": { "url": "...", "title": "Preanalitica" },
  "clickable_elements": [
    {
      "accessible_name": "Laboratorio Analisi",
      "role": "button",
      "playwright_suggestions": {
        "click_smart": [
          {"by": "role", "role": "button", "name": "Laboratorio Analisi"},
          {"by": "text", "text": "Laboratorio Analisi"}
        ]
      }
    }
  ],
  "form_fields": [
    {
      "accessible_name": "Username",
      "playwright_suggestions": {
        "fill_smart": [
          {"by": "label", "label": "Username"},
          {"by": "placeholder", "placeholder": "Enter username"}
        ]
      }
    }
  ]
}
```

Gli agenti (AMC e LAB) sono istruiti a:
1. chiamare `inspect_interactive_elements()` dopo una navigazione o un cambio pagina
2. trovare l’elemento di interesse per `accessible_name`/testo
3. copiare **tutte** le strategie `playwright_suggestions` nel parametro `targets` per `click_smart`/`fill_smart`.

---

### Smart locators

#### `click_smart(targets: List[Dict], timeout_per_try: int, in_iframe: dict | None = None)`

- **Scopo**: cliccare un elemento provando una **catena** di strategie finché una riesce.
- **Input tipico** (da `inspect_interactive_elements`):

```json
{
  "targets": [
    {"by": "role", "role": "button", "name": "Login"},
    {"by": "text", "text": "Login"}
  ]
}
```

- **Output successo**:

```json
{
  "status": "success",
  "message": "Click eseguito con strategia 'role'",
  "used_strategy": {"by": "role", "role": "button", "name": "Login"},
  "strategies_tried": [ ... ]
}
```

- **Perché è importante**:
  - rende i test molto più robusti a piccoli cambiamenti di markup/accessibility
  - si integra bene con `wait_for_clickable_by_name` (prima trovi l’elemento, poi clicchi con i suoi `targets`).

#### `fill_smart(targets: List[Dict], value: str, timeout_per_try: int, clear_first: bool = True, in_iframe: dict | None = None)`

- **Scopo**: compilare un campo input con la stessa idea di fallback chain.
- **Input esempio**:

```json
{
  "targets": [
    {"by": "label", "label": "Username"},
    {"by": "placeholder", "placeholder": "Enter username"},
    {"by": "role", "role": "textbox", "name": "Username"}
  ],
  "value": "AMC-User",
  "clear_first": true
}
```

- **Output**:

```json
{
  "status": "success",
  "message": "Fill eseguito con strategia 'label'",
  "used_strategy": {"by": "label", "label": "Username"},
  "strategies_tried": [ ... ]
}
```

Nel prefix LAB li usiamo per compilare username e password in maniera deterministica dopo aver trovato i campi con `wait_for_field_by_name` / `inspect_interactive_elements`.

---

### Base tools aggiuntivi

Questi tool sono esposti dal server e usati per wait su elementi, lettura testo, tasti e banner/cookie; `get_frame` è necessario quando l’interfaccia è dentro un iframe.

#### `wait_for_element(selector, selector_type="css", state="visible", timeout=30000)`

- **Scopo**: aspettare che un elemento soddisfi una condizione (es. visibile, attached) prima di interagire.
- **Parametri**: `selector` (stringa, es. CSS), `selector_type` (`"css"`, `"xpath"`, …), `state` (`"visible"`, `"attached"`, `"hidden"`), `timeout` (ms).
- **Perché**: quando hai già un ref CSS da `inspect` e vuoi attendere che l’elemento sia visibile prima di `click_smart`/`fill_smart`.
- **Input esempio**: `{"selector": "#submit-btn", "selector_type": "css", "state": "visible", "timeout": 10000}`.
- **Output successo**: `{"status": "success", "message": "Elemento trovato e in stato 'visible'", "selector": "...", "state": "visible"}`.

#### `get_text(selector, selector_type="css")`

- **Scopo**: leggere il testo visibile (o attributi) di un elemento senza cliccare.
- **Parametri**: `selector`, `selector_type` (come in `wait_for_element`).
- **Perché**: verificare label, messaggi di errore, titoli di sezione; utile dopo un’azione per assert “contiene questo testo”.
- **Input esempio**: `{"selector": ".page-title", "selector_type": "css"}`.
- **Output tipico**: `{"status": "success", "text": "Laboratorio Analisi", "selector": "..."}`. In caso di errore: `{"status": "error", "message": "..."}`.

#### `press_key(key)`

- **Scopo**: inviare un tasto (o combinazione) alla pagina (focus sulla pagina o su un elemento già focalizzato).
- **Parametri**: `key` – stringa tipo `"Enter"`, `"Tab"`, `"Escape"`, `"Control+a"` (convenzione Playwright/Keyboard).
- **Perché**: confermare modali (Enter), chiudere popup (Escape), navigare tra campi (Tab).
- **Input esempio**: `{"key": "Enter"}`.
- **Output tipico**: `{"status": "success", "message": "Tasto inviato", "key": "Enter"}`.

#### `handle_cookie_banner(strategies: list | None, timeout: int = 5000)`

- **Scopo**: provare a chiudere/accettare un banner cookie in modo generico (click su pulsanti comuni tipo “Accetta”, “Accept”, “OK” o su overlay).
- **Parametri**: `strategies` (lista di strategie; se `None`, default del backend), `timeout` (ms).
- **Perché**: in LAB/AMC il cookie banner può bloccare la vista; chiamarlo subito dopo il load evita che gli smart locator puntino al banner invece che al form di login.
- **Input esempio**: `{}` (usa default) o `{"strategies": ["button:has-text('Accetta')"], "timeout": 5000}`.
- **Output tipico**: `{"status": "success", "message": "Banner gestito", "strategy_used": "..."}` oppure `{"status": "success", "message": "Nessun banner trovato"}`.

#### `get_frame(url_pattern: str | None, iframe_path: list | None, timeout: int = 10000, return_frame: bool = False)`

- **Scopo**: individuare un iframe (anche annidato) per URL o percorso, e opzionalmente restituire un handle per usarlo in tool successivi.
- **Parametri**: `url_pattern` (stringa nell’URL del frame, es. `"registry/movementreason"`), `iframe_path` (lista indici/nomi per iframe annidati), `timeout`, `return_frame` (se `True`, output può includere ref al frame).
- **Perché**: in LAB molte funzionalità (modifica, filtri) sono dentro iframe; `click_smart`/`fill_smart` con `in_iframe` usano internamente `get_frame` per risolvere il frame corretto.
- **Input esempio**: `{"url_pattern": "registry/movementreason", "timeout": 10000}`.
- **Output tipico**: `{"status": "success", "message": "Frame trovato", "url": "...", "selector": "..."}`.

---

### Wait avanzati per LAB

I tool seguenti sono definiti in `tools.py`; l’elenco effettivamente esposto dal server MCP dipende da `mcp_servers/tool_names.py` (vedi anche README, sezione “Tool Playwright Disponibili”).

#### `wait_for_clickable_by_name(name_substring: str, timeout: int | None = None, case_insensitive: bool = True)`

- **Scopo**: in polling, chiama `inspect_interactive_elements()` finché trova un **elemento cliccabile** il cui `accessible_name` o testo contiene `name_substring`.
- **Output**: ritorna direttamente l’elemento e i suoi `targets` per `click_smart`.

Esempio:

```json
{
  "name_substring": "Laboratorio Analisi",
  "timeout": 20000
}
```

Risultato:

```json
{
  "status": "success",
  "element": { "...": "..." },
  "targets": [
    {"by": "role", "role": "button", "name": "Laboratorio Analisi"},
    {"by": "text", "text": "Laboratorio Analisi"}
  ]
}
```

Nel prefix LAB:
- usato dopo “Continua” per trovare il tile **Laboratorio Analisi** (o, solo in fallback, “Clinical Laboratory”).

#### `wait_for_control_by_name_and_type(name_substring: str, control_type: str, timeout: int | None = None, case_insensitive: bool = True)`

- **Scopo**: simile al precedente, ma cercando nei `interactive_controls` un controllo di un certo tipo logico (`"combobox"`, `"checkbox"`, `"tab"`…).
- **Uso tipico**:
  - combobox “Seleziona Organizzazione” nel LAB.

Esempio:

```json
{
  "name_substring": "Seleziona Organizzazione",
  "control_type": "combobox",
  "timeout": 15000
}
```

Output:

```json
{
  "status": "success",
  "element": { "type": "combobox", "accessible_name": "Seleziona Organizzazione", ... },
  "targets": [
    {"by": "role", "role": "combobox", "name": "Seleziona Organizzazione"},
    ...
  ]
}
```

Il prompt del **LAB Prefix Agent** istruisce il modello a:
1. chiamare `wait_for_control_by_name_and_type("Seleziona Organizzazione", "combobox")`
2. cliccare il controllo con `click_smart(targets=...)`
3. usare `inspect_interactive_elements()` per trovare le opzioni del dropdown
4. cliccare quella che contiene “organizzazione” e “sistema”.

---

### Come usare questa guida

- Nel dubbio su **quale tool usare** per un certo passo UI, chiediti:
  - devo **scoprire** cosa c’è in pagina? → `inspect_interactive_elements`
  - devo **cliccare/compilare** qualcosa già scoperto? → `click_smart` / `fill_smart`
  - devo **aspettare** che compaia un testo? → `wait_for_text_content`
  - devo **aspettare** che compaia proprio un bottone o una combobox con un certo nome? → `wait_for_clickable_by_name` / `wait_for_control_by_name_and_type`
  - devo solo gestire il ciclo di vita del browser o fare screenshot? → lifecycle tools.

Per l’elenco completo e dettagli di tutti i tool (inclusi quelli legacy o meno usati) vedi anche `backend/README.md`, sezione **“Tool Playwright Disponibili”**.

