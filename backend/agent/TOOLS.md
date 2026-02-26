# Guida ai tool Playwright MCP

Tool definiti in `tools.py` ed esposti dal server MCP (`mcp_servers/tool_names.py`).

---

## Mappa rapida

| Tool | Categoria | Output chiave |
|------|-----------|---------------|
| `start_browser` | Lifecycle | `status`, `headless` |
| `close_browser` | Lifecycle | `status` |
| `navigate_to_url` | Lifecycle | `status`, `url`, `title` |
| `get_page_info` | Lifecycle | `url`, `title`, `viewport` |
| `capture_screenshot` | Lifecycle | `filename`, `size_bytes`, `base64?` |
| `wait_for_load_state` | Wait | `status`, `state` |
| `wait_for_text_content` | Wait | `status`, `text`, `location` |
| `wait_for_element_state` | Wait | `status`, `strategy`, `state` |
| `wait_for_dom_change` | Wait | `status`, `mutation_summary` |
| `inspect_interactive_elements` | Discovery | `iframes`, `clickable_elements`, `interactive_controls`, `form_fields` |
| `inspect_region` | Discovery | stesso di inspect, limitato a un container |
| `click_smart` | Smart locator | `status`, `used_strategy`, `strategies_tried` |
| `fill_smart` | Smart locator | `status`, `used_strategy`, `strategies_tried` |
| `wait_for_clickable_by_name` | Wait name-based | `status`, `element`, `targets` |
| `wait_for_control_by_name_and_type` | Wait name-based | `status`, `element`, `targets` |
| `wait_for_field_by_name` | Wait name-based | `status`, `element`, `targets` |
| `click_and_wait_for_text` | Procedurale | `status`, `click`, `text_check` |
| `get_text` | Base | `status`, `text` |
| `press_key` | Base | `status`, `key` |
| `handle_cookie_banner` | Base | `status`, `strategy_used` |
| `get_frame` | Base | `status`, `url`, `selector` |

**Quale tool usare?**
- Scoprire cosa c'è in pagina → `inspect_interactive_elements`
- Cliccare/compilare qualcosa già scoperto → `click_smart` / `fill_smart`
- Aspettare un testo → `wait_for_text_content`
- Aspettare che compaia un bottone/campo per nome → `wait_for_clickable_by_name` / `wait_for_field_by_name`
- Aspettare uno stato di un elemento già noto → `wait_for_element_state`
- Rilevare cambiamenti in un'area specifica → `wait_for_dom_change` + `inspect_region`

---

## Formato `playwright_suggestions`

`inspect_interactive_elements` e `inspect_region` restituiscono per ogni elemento un array `playwright_suggestions`. Il formato **reale** (da `tools.py`) è una lista di oggetti con `strategy` e il payload:

**Elementi cliccabili** (`clickable_elements`, `interactive_controls`):
```json
"playwright_suggestions": [
  { "strategy": "role",       "click_smart": {"by": "role", "role": "button", "name": "Aggiungi gruppo"} },
  { "strategy": "css_aria",   "click_smart": {"by": "css",  "selector": "[aria-label='Aggiungi gruppo']"} },
  { "strategy": "text_label", "click_smart": {"by": "text", "text": "AGGIUNGI GRUPPO"} },
  { "strategy": "text",       "click_smart": {"by": "text", "text": "add\nAGGIUNGI GRUPPO"} },
  { "strategy": "tfa",        "click_smart": {"by": "tfa",  "tfa": "add-group-btn"} }
]
```

**Campi form** (`form_fields`):
```json
"playwright_suggestions": [
  { "strategy": "label",       "fill_smart": {"by": "label",       "label": "Username"} },
  { "strategy": "placeholder", "fill_smart": {"by": "placeholder", "placeholder": "Enter username"} },
  { "strategy": "role",        "fill_smart": {"by": "role",        "role": "textbox", "name": "Username"} },
  { "strategy": "css_name",    "fill_smart": {"by": "css",         "selector": "[name='username']"} },
  { "strategy": "css_id",      "fill_smart": {"by": "css",         "selector": "#mat-input-3"} },
  { "strategy": "css_aria",    "fill_smart": {"by": "css",         "selector": "[aria-label='Username']"} },
  { "strategy": "tfa",         "fill_smart": {"by": "tfa",         "tfa": "login-username"} }
]
```

**Come costruire `targets`**: estrarre i valori del payload (`click_smart` o `fill_smart`) da **tutte** le suggestions, nell'ordine in cui compaiono:
```python
# Per click_smart
targets = [s["click_smart"] for s in element["playwright_suggestions"]]

# Per fill_smart
targets = [s["fill_smart"] for s in element["playwright_suggestions"]]
```

Non modificare i payload, non prenderne solo uno, non inventarne di nuovi.

---

## Pattern composti

### Discovery-first (obbligatorio dopo ogni navigazione)

```
navigate_to_url(url)
→ inspect_interactive_elements()
→ trova elemento per accessible_name
→ targets = [s["click_smart"] for s in element["playwright_suggestions"]]
→ click_smart(targets=targets)
```

### Elemento singolo (bottone che deve diventare enabled)

```
inspect_interactive_elements()
→ targets del bottone (es. "Aggiungi filtro")
→ wait_for_element_state(targets=targets, state="enabled")
→ click_smart(targets=targets)
```

Usa questo invece di fare polling con inspect quando hai già i targets.

### Area dinamica (modale/card che cambia dopo un click)

```
click_smart(targets=...)          ← apre modale / aggiorna card
→ wait_for_dom_change(root_selector=".mat-dialog-container")
→ inspect_region(root_selector=".mat-dialog-container")
→ fill_smart / click_smart con i targets dalla regione
```

Evita di fare un `inspect_interactive_elements` completo quando sai già quale container è cambiato.

---

## Tool nel dettaglio

### Lifecycle & pagina

#### `start_browser(headless=False)`
Avvia Chromium in stealth mode. Viewport, locale e timezone vengono da `AppConfig.PLAYWRIGHT`.

```json
// output
{ "status": "success", "message": "Browser avviato con successo (stealth mode)", "headless": false }
```

Nei prompt AMC e LAB standalone è sempre il primo step. Nel **LAB Prefix Agent** è il primo step; nello **Scenario Agent** non va chiamato (browser già aperto).

---

#### `navigate_to_url(url)`
Naviga e aspetta `domcontentloaded`. Non usa `networkidle` per evitare timeout su SPA con polling.

```json
{ "status": "success", "url": "https://lab.example.com/", "title": "Preanalitica", "viewport": {"width": 960, "height": 1080} }
```

---

#### `get_page_info()`
Legge URL, titolo e viewport senza navigare. Utile per verifiche rapide ("sono nel modulo giusto?").

```json
{ "status": "success", "url": "...", "title": "Laboratorio Analisi", "viewport": {"width": 960, "height": 1080} }
```

---

#### `capture_screenshot(filename=None, return_base64=False)`
Screenshot full-page. **Usare sempre `return_base64=False`** per non superare il limite di contesto del modello.

```json
// output (return_base64=False)
{ "status": "success", "filename": "test_success.png", "size_bytes": 60890 }
```

Nei prompt: un solo screenshot alla fine (su successo `"test_success.png"`, su errore `"error.png"`), nessun screenshot intermedio salvo esplicita richiesta.

---

#### `close_browser()`
Chiude pagina, context, browser e ferma Playwright.

- AMC / LAB Scenario Agent: chiamato sempre alla fine (successo o errore).
- **LAB Prefix Agent: esplicitamente vietato** (il browser deve restare aperto per la fase scenario).

---

### Wait & load

#### `wait_for_load_state(state, timeout=30000)`

| State | Quando usarlo |
|-------|---------------|
| `domcontentloaded` | dopo la maggior parte delle navigazioni (più veloce) |
| `load` | quando servono le risorse principali |
| `networkidle` | dopo login / redirect pesanti; può andare in timeout su SPA con polling |

```json
{ "status": "success", "message": "Load state 'domcontentloaded' raggiunto", "state": "domcontentloaded" }
```

---

#### `wait_for_text_content(text, timeout=30000, case_sensitive=False, in_iframe=None)`
Aspetta che un testo appaia nel DOM. È il segnale principale che una view è caricata.

```json
// successo
{ "status": "success", "text": "Preanalitica", "location": { "frame_url": "...", "selector": "h1.page-title" } }

// timeout
{ "status": "error", "message": "Testo 'Preanalitica' non trovato dopo 30000ms" }
```

Nel prompt LAB: usare solo testi visti in un precedente `inspect` o esplicitamente menzionati nella descrizione del test. Non inventare `"home"`, `"dashboard"`, `"success"`.

---

#### `wait_for_element_state(targets, state="visible", timeout=None, in_iframe=None)`
Aspetta che un elemento identificato da `targets` raggiunga uno stato logico.

Stati nativi Playwright (`locator.wait_for`): `visible`, `hidden`, `attached`, `detached`.  
Stati logici (polling su `is_enabled()`): `enabled`, `disabled`.

```json
// input
{
  "targets": [
    {"by": "role", "role": "button", "name": "AGGIUNGI FILTRO"},
    {"by": "text", "text": "AGGIUNGI FILTRO"}
  ],
  "state": "enabled",
  "timeout": 15000
}

// output
{ "status": "success", "strategy": "role", "state": "enabled", "strategies_tried": ["role"] }
```

---

#### `wait_for_dom_change(root_selector="body", timeout=None, attributes=True, child_list=True, subtree=True, attribute_filter=None, in_iframe=None)`
Usa un `MutationObserver` per rilevare qualsiasi cambiamento DOM in un container.

```json
// input
{ "root_selector": "div.filters-card", "timeout": 10000, "attribute_filter": ["disabled", "class"] }

// output
{
  "status": "success",
  "root_selector": "div.filters-card",
  "mutation_summary": { "count": 3, "has_child_list": true, "has_attributes": true }
}
```

Usato nel pattern "area dinamica": dopo un click critico, aspetta che la card/modale cambi, poi chiama `inspect_region` su quella zona.

---

### Discovery

#### `inspect_interactive_elements(in_iframe=None)`
Scansiona tutta la pagina (o un iframe) e restituisce:
- `iframes` — src, name, title per `get_frame`
- `clickable_elements` — bottoni, link, tile, menu items
- `interactive_controls` — combobox, checkbox, tab, switch, radio
- `form_fields` — input, textarea, select
- `page_info` — url e titolo correnti

Ogni elemento ha `playwright_suggestions` (vedi sezione formato sopra).

```json
{
  "status": "success",
  "page_info": { "url": "...", "title": "Preanalitica" },
  "iframes": [{ "src": "https://.../movementreason", "name": "contentFrame", "title": "" }],
  "clickable_elements": [
    {
      "accessible_name": "Laboratorio Analisi",
      "role": "button",
      "text": "Laboratorio Analisi",
      "playwright_suggestions": [
        { "strategy": "role", "click_smart": {"by": "role", "role": "button", "name": "Laboratorio Analisi"} },
        { "strategy": "text", "click_smart": {"by": "text", "text": "Laboratorio Analisi"} }
      ]
    }
  ],
  "form_fields": [
    {
      "accessible_name": "Username",
      "placeholder": "Enter username",
      "playwright_suggestions": [
        { "strategy": "label",       "fill_smart": {"by": "label", "label": "Username"} },
        { "strategy": "placeholder", "fill_smart": {"by": "placeholder", "placeholder": "Enter username"} }
      ]
    }
  ]
}
```

**Regola**: chiamare dopo ogni navigazione o cambio pagina. Costruire i `targets` **solo** da `playwright_suggestions`, copiandoli tutti.

---

#### `inspect_region(root_selector, in_iframe=None)`
Identico a `inspect_interactive_elements`, ma limitato a un container CSS. Restituisce la stessa struttura (`clickable_elements`, `form_fields`, `interactive_controls`).

```json
// input
{ "root_selector": "div.ds-tool-card-wrapper.filters-card" }

// output — stessa struttura di inspect_interactive_elements, solo per quella regione
```

Usato nel pattern "area dinamica" dopo `wait_for_dom_change` per non re-ispezionare tutta la pagina.

---

### Smart locators

#### `click_smart(targets, timeout_per_try=2000, in_iframe=None)`
Prova ogni strategia in `targets` con una catena a 3 livelli:
1. click normale (con retry e backoff)
2. force click (bypassa actionability)
3. JS click (bypassa tutto — last resort)

```json
// input
{
  "targets": [
    {"by": "role", "role": "button", "name": "Login"},
    {"by": "text", "text": "Login"}
  ]
}

// output
{
  "status": "success",
  "message": "Click eseguito con strategia 'role'",
  "used_strategy": {"by": "role", "role": "button", "name": "Login"},
  "strategies_tried": [{"by": "role", ...}]
}
```

---

#### `fill_smart(targets, value, timeout_per_try=2000, clear_first=True, in_iframe=None)`
Stessa logica di `click_smart` per i campi form. `clear_first=True` svuota il campo prima di scrivere.

```json
// input
{
  "targets": [
    {"by": "label", "label": "Username"},
    {"by": "placeholder", "placeholder": "Enter username"}
  ],
  "value": "mario.rossi@example.com"
}

// output
{ "status": "success", "used_strategy": {"by": "label", "label": "Username"}, "strategies_tried": [...] }
```

---

### Wait name-based

Questi tre tool fanno polling su `inspect_interactive_elements` e restituiscono direttamente i `targets` pronti per `click_smart` / `fill_smart`.

#### `wait_for_clickable_by_name(name_substring, timeout=None, case_insensitive=True)`
Aspetta un elemento cliccabile il cui `accessible_name` o testo contiene `name_substring`.

```json
// output
{
  "status": "success",
  "element": { "accessible_name": "Laboratorio Analisi", "role": "button", ... },
  "targets": [
    {"by": "role", "role": "button", "name": "Laboratorio Analisi"},
    {"by": "text", "text": "Laboratorio Analisi"}
  ]
}
```

Nel LAB Prefix Agent: usato per trovare il tile "Laboratorio Analisi" dopo la tile grid.

---

#### `wait_for_control_by_name_and_type(name_substring, control_type, timeout=None, case_insensitive=True)`
Come sopra, ma cerca negli `interactive_controls` per tipo logico (`combobox`, `checkbox`, `tab`, `switch`, `radio`).

```json
// input
{ "name_substring": "Seleziona Organizzazione", "control_type": "combobox", "timeout": 15000 }

// output
{
  "status": "success",
  "element": { "type": "combobox", "accessible_name": "Seleziona Organizzazione", ... },
  "targets": [
    {"by": "role", "role": "combobox", "name": "Seleziona Organizzazione"},
    ...
  ]
}
```

Nel LAB Prefix Agent: usato per trovare il dropdown organizzazione prima di aprirlo.

---

#### `wait_for_field_by_name(name_substring, timeout=None, case_insensitive=True)`
Aspetta un campo form il cui `accessible_name`, `placeholder` o `name` contiene `name_substring`. Restituisce `targets` per `fill_smart`.

```json
// output
{
  "status": "success",
  "element": { "accessible_name": "Username", "placeholder": "Enter username", ... },
  "targets": [
    {"by": "label", "label": "Username"},
    {"by": "placeholder", "placeholder": "Enter username"},
    {"by": "role", "role": "textbox", "name": "Username"}
  ]
}
```

---

### Tool procedurali

#### `click_and_wait_for_text(targets, text, timeout_per_try, text_timeout=30000, in_iframe=None)`
`click_smart` + `wait_for_text_content` in un unico step. Se il click fallisce, non esegue il wait.

```json
// output
{
  "status": "success",
  "click":      { "status": "success", "used_strategy": {...} },
  "text_check": { "status": "success", "text": "Preanalitica" }
}
```

Usato per step critici dove click e comparsa del testo atteso vanno sempre insieme (es. click "Continua" → attesa "Preanalitica").

---

### Tool base

#### `get_text(selector, selector_type="css")`
Legge il testo visibile di un elemento. Utile per assert su label, messaggi, titoli di sezione.

```json
{ "status": "success", "text": "Laboratorio Analisi", "selector": ".page-title" }
```

---

#### `press_key(key)`
Invia un tasto (o combinazione) alla pagina. Notazione Playwright: `"Enter"`, `"Escape"`, `"Tab"`, `"Control+a"`.

```json
{ "status": "success", "key": "Enter" }
```

---

#### `handle_cookie_banner(strategies=None, timeout=5000)`
Prova a chiudere un banner cookie con strategie configurabili: `"generic_accept"` (default), `"generic_agree"`, `"reject_all"`. Se `strategies=None` usa `["generic_accept", "generic_agree"]`.

```json
// trovato e chiuso
{ "status": "success", "strategy_used": "generic_accept" }

// non trovato (non è un errore)
{ "status": "success", "message": "Nessun banner trovato" }
```

Chiamarlo subito dopo il load per evitare che i banner interferiscano con smart locators.

---

#### `get_frame(url_pattern=None, iframe_path=None, timeout=10000, return_frame=False)`
Individua un iframe per URL pattern o percorso. Usato internamente da `click_smart`/`fill_smart` quando si passa `in_iframe`.

```json
// input
{ "url_pattern": "registry/movementreason", "timeout": 10000 }

// output
{ "status": "success", "url": "https://.../movementreason", "selector": "iframe[src*='movementreason']" }
```

Negli inspect: se `inspect_interactive_elements` mostra un iframe nella lista `iframes`, usare `url_pattern` con una sottostringa dell'URL per riferirsi a quel frame nei tool successivi.

---