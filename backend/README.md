# AI Test Automation Agent (MCP)

Sistema di test automation intelligente che usa **MCP (Model Context Protocol)**, LangGraph e Playwright per automatizzare test di interfacce web enterprise con AI agent.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![MCP](https://img.shields.io/badge/MCP-1.12.3-purple)
![Version](https://img.shields.io/badge/version-3.2.0-green)

---

## Indice

- [Architettura](#architettura)
- [Struttura del Progetto](#struttura-del-progetto)
- [Setup](#setup)
- [Configurazione](#configurazione)
- [Tool Playwright (23 tools)](#tool-playwright)
- [Orchestratore LAB](#orchestratore-lab)
- [API Endpoints](#api-endpoints)
- [MCP: Locale vs Remoto](#mcp-locale-vs-remoto)

---

## Architettura

```
Frontend (Angular)
       │ HTTP REST
       ▼
Backend (Flask)
       │ Python call
       ▼
AI Agent (LangGraph - ReAct)
  ├─ prompts/*          ← system prompts per AMC/LAB/Prefix/Extraction
  ├─ core/evaluation.py ← pass/fail da tool results (non dal modello)
  └─ pipelines/*        ← Prefix Agent + Scenario Agent (es. LAB)
       │ MCP Protocol
       ▼
MCP Client (langchain-mcp-adapters)
       │ stdio | HTTP
       ▼
MCP Server (playwright_server_local / remote)
  └─ 23 Playwright tools async
       │
       ▼
Playwright Async (Chromium)
```

**Flusso orchestrato (LAB):**
1. **Prefix Agent** → login, selezione organizzazione, navigazione al modulo Laboratory (browser rimane aperto)
2. **Scenario Agent** → esegue lo scenario LAB dalla dashboard Laboratory, chiude il browser

Il pass/fail è deciso da `core/evaluation.py` sui tool results, non dall'output testuale del modello.

---

### Codegen Playwright deterministico (senza LLM)

Quando abiliti la generazione dello script Playwright, il flusso è:

```
run_lab_scenario()
    └─ produce scenario_result["steps"]
           │
           ▼
    codegen/trace_extractor.py
    extract_trace(steps)
           │  filtra: solo tool_end + status=success
           │  esclude: infrastruttura (start_browser, screenshot, ecc.)
           │  normalizza: [{tool, args, result}, ...]
           ▼
    codegen/trace_to_playwright.py
    generate_script_from_trace(trace)
           │  header imports
           │  helper do_login_and_go_to_laboratory() — template fisso
           │  per ogni step → _compile_step(tool, args)
           │       └─ _pick_locator_from_targets(targets)
           ▼
    script Python sync pronto (pytest + playwright.sync_api)
           │
           ▼
    codegen/script_generator.py
    generate_playwright_script()  ← unico punto di ingresso da app.py
```

Tutta la compilazione trace → script è **deterministica**: non viene mai chiamato un LLM in questa fase, e le regole di traduzione MCP → Playwright vivono unicamente in `trace_to_playwright.py`.

**Dettagli importanti (pratici):**

- **Trace = success-only**: `extract_trace(...)` include solo step `tool_end` con `output.status="success"`.
  Se uno step necessario fallisce/non viene eseguito durante la run (es. click su un contatore o un wait), **non apparirà nello script generato**.
- **Strict mode Playwright**: per evitare errori quando un locator risolve a più elementi (es. due bottoni con lo stesso nome),
  il codegen applica `.first` ai locator `get_by_*` quando non sono già scoped.
  Quando disponibile, usa anche `target["scope"]` (scope detection best-effort di `click_smart`/`fill_smart`) per generare un locator scoped
  del tipo `page.locator("<scope>").nth(i).get_by_role(...)`.
- **Scroll esplicito**: `scroll_to_bottom(selector=...)` è mappato nel codegen. Per i wrapper elenco
  campioni (`AppConfig.UI.is_scroll_sample_table_wrapper`) il tool usa
  `get_scroll_sample_table_list_locator` + `get_scroll_sample_table_footer_text`; altri selettori
  restano scroll su `locator(selector)`.

**Esempi rapidi (trace → Playwright):**

1) `click_smart` (locator ambiguo → `.first`):

```python
# trace step (semplificato)
{"tool": "click_smart", "result": {"target": {"by": "role", "role": "button", "name": "Aggiungi filtro"}}}

# codice generato
page.get_by_role("button", name="Aggiungi filtro").first.click()
```

2) `scroll_to_bottom` su contenitore (wrapper elenco campioni → lista + footer):

```python
# trace step (semplificato)
{"tool": "scroll_to_bottom", "args": {"selector": ".sample-table-container"}}

# codice generato (valori da AppConfig.PLAYWRIGHT.get_scroll_sample_table_*)
_sr = page.locator("sample-table div.search-results")
if _sr.count() > 0:
    _sr.first.evaluate("el => { el.scrollTop = el.scrollHeight; }")
_foot = page.get_by_text("Totale righe visualizzate", exact=False)
if _foot.count() > 0:
    _foot.first.scroll_into_view_if_needed()
```

## Struttura del Progetto

```
backend/
├── app.py                          # Flask server
├── requirements.txt
├── .env                            # Variabili d'ambiente (non committare)
├── .env.example
│
├── config/
│   └── settings.py                 # Configurazione centralizzata (LLM, MCP, Playwright)
│
├── agent/
│   ├── tools.py                    # Implementazione Playwright (tool esposti via MCP, vedi tool_names.py)
│   ├── prompts/                    # Prompt per app (AMC/LAB/Prefix/Extraction)
│   ├── core/                       # Logica core deterministica (es. evaluation)
│   ├── lab_scenarios.py            # Definizione 4 scenari LAB
│   ├── pipelines/                  # Orchestrazioni/pipeline (es. LAB)
│   ├── extraction/                 # Estrazione scenari da documenti
│   ├── test_agent_mcp.py           # TestAgentMCP: init, run_test_async, stream
│   └── utils.py                    # Serializzazione, logging, export grafo
│
├── mcp_servers/
│   ├── playwright_server_local.py  # Server MCP via stdio
│   ├── playwright_server_remote.py # Server MCP via HTTP
│   └── tool_names.py               # Source of truth lista tool
│
└── tests/
    ├── test_mcp_remote.py
    ├── test_amc_workflow_native.py
    └── test_lab_workflow_native.py
```

---

## Setup

### Prerequisiti

- Python 3.10+
- API key per uno dei provider LLM supportati (OpenAI, Azure OpenAI, OpenRouter)

### Installazione

```bash
git clone <repository-url>
cd ai-test-automation/backend

python -m venv venv
source venv/bin/activate          # Windows: .\venv\Scripts\Activate

pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

### Verifica

```bash
python -c "import flask, playwright, langchain, mcp; print('OK')"
python -c "from langchain_mcp_adapters.client import MultiServerMCPClient; print('MCP OK')"
```

### Avvio

```bash
python app.py
```

---

## Configurazione

Crea `backend/.env` dal template `.env.example`:

```bash
# LLM — scegli UNO dei tre provider

# OpenRouter (consigliato: accesso a Claude, Gemini, GPT con una sola key)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Azure OpenAI (enterprise)
# AZURE_OPENAI_API_KEY=...
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
# AZURE_OPENAI_API_VERSION=2024-08-01-preview

# OpenAI standard
# OPENAI_API_KEY=sk-proj-...

# App under test (LAB)
LAB_URL=https://...
LAB_USERNAME=user@example.com
LAB_PASSWORD=...

# Flask
FLASK_PORT=5000
FLASK_DEBUG=True

# Playwright
PLAYWRIGHT_HEADLESS=False
```

**Priorità provider:** OpenRouter → Azure → OpenAI (primo trovato nelle env).

**MCP mode:** configurabile in `config/settings.py` → `MCPConfig.MODE = "local"` oppure `"remote"`.

---

## Tool Playwright

Il MCP server espone **23 tool async**. Fonte unica: `mcp_servers/tool_names.py`.

### Lifecycle & navigazione
| Tool | Descrizione |
|------|-------------|
| `start_browser(headless)` | Avvia Chromium (stealth mode) |
| `close_browser()` | Chiude browser e libera risorse |
| `navigate_to_url(url)` | Naviga e attende `domcontentloaded` |
| `get_page_info()` | Restituisce URL, titolo, viewport |
| `get_frame(selector, url_pattern)` | Accesso a iframe (by CSS o URL pattern) |

### Interazione base
| Tool | Descrizione |
|------|-------------|
| `get_text(selector, selector_type)` | Estrae testo da elemento |
| `get_text_by_visible_content(search_text, timeout)` | Trova il primo elemento visibile che contiene `search_text` ed estrae il testo completo (innerText). Usare solo per testi espliciti negli expected results dello scenario. |
| `press_key(key)` | Simula pressione tasto (Enter, Escape, ...) |
| `scroll_to_bottom(selector)` | Scorre pagina o un contenitore (es. elenco campioni con lista + footer) |
| `capture_screenshot(filename, return_base64)` | Screenshot full-page; raro nei flussi LAB (payload grandi se `return_base64=True`) |
| `handle_cookie_banner(strategies, timeout)` | Gestione banner cookie con strategie multiple |

### Wait
| Tool | Descrizione |
|------|-------------|
| `wait_for_load_state(state, timeout)` | Attende stato pagina: `domcontentloaded`, `load`, `networkidle` |
| `wait_for_text_content(text, timeout, in_iframe)` | Attende comparsa testo nel DOM (supporta iframe) |
| `wait_for_element_state(targets, state, timeout)` | Attende che un elemento raggiunga uno stato (`visible`, `enabled`, `hidden`, ...) |
| `wait_for_dom_change(root_selector, timeout)` | Attende qualsiasi cambiamento DOM in un container (modale, card, panel) |

### Discovery
| Tool | Descrizione |
|------|-------------|
| `inspect_interactive_elements()` | **Tool chiave.** Scansione WCAG di tutta la pagina: restituisce `iframes`, `clickable_elements`, `form_fields`, ognuno con `playwright_suggestions` pronti per `click_smart`/`fill_smart` |
| `inspect_region(root_selector)` | Come `inspect_interactive_elements` ma limitato a un container CSS (modale, pannello) |

### Smart locators
| Tool | Descrizione |
|------|-------------|
| `click_smart(targets, timeout_per_try)` | Click con fallback chain: normal click → force click → JS click. `targets` viene da `playwright_suggestions` |
| `fill_smart(targets, value, timeout_per_try)` | Fill con retry e `clear_first`. Stessa logica di `click_smart` |

### Wait name-based (polling su inspect)
| Tool | Descrizione |
|------|-------------|
| `wait_for_clickable_by_name(name_substring, timeout)` | Attende e restituisce `targets` per un elemento cliccabile |
| `wait_for_control_by_name_and_type(name_substring, control_type, timeout)` | Attende un controllo specifico (`combobox`, `tab`, `checkbox`, ...) |
| `wait_for_field_by_name(name_substring, timeout)` | Attende un campo form e restituisce `targets` per `fill_smart` |

### Procedurale
| Tool | Descrizione |
|------|-------------|
| `click_and_wait_for_text(targets, text, text_timeout, in_iframe)` | `click_smart` + `wait_for_text_content` in un solo step |

### Pattern d'uso consigliati

**Discovery-first (obbligatorio dopo ogni navigazione):**
```
navigate_to_url → inspect_interactive_elements
  → prendi playwright_suggestions dell'elemento target
  → click_smart(targets=[...tutte le suggestions...])
```

**Elemento singolo (bottone che aspetti diventi enabled):**
```
inspect_interactive_elements → targets del bottone
→ wait_for_element_state(targets, state="enabled")
→ click_smart(targets)
```

**Area dinamica (modale/card che cambia dopo click):**
```
click_smart(...)
→ wait_for_dom_change(root_selector=".mat-dialog-container")
→ inspect_region(root_selector=".mat-dialog-container")
→ fill_smart / click_smart con suggestions della regione
```

---

## Orchestratore LAB

La pipeline LAB (`agent/pipelines/lab.py`) gestisce il flusso completo in due fasi con agenti separati.

```python
from agent.pipelines.lab import run_full_sync

result = run_full_sync(
    scenario_id="scenario_1",
    url="https://...",
    user="user@example.com",
    password="...",
    verbose=True,
)
print(result["passed"])   # True / False
print(result["errors"])   # lista errori per tool
```

**Scenari disponibili** (definiti in `lab_scenarios.py`):

| ID | Scenario |
|----|----------|
| `scenario_1` | Creazione filtro e visualizzazione in dashboard |
| `scenario_2` | Accesso tramite contatori |
| `scenario_3` | Accesso tramite filtro |
| `scenario_4` | Pagina di dettaglio campione |
| `scenario_5` | Creazione filtro con Piano di lavoro e Descrizione |

**Struttura risultato:**
```python
{
    "passed": True,
    "phase": "full",
    "prefix": { ... },   # risultato Prefix Agent
    "scenario": { ... }, # risultato Scenario Agent
    "errors": [],
    "artifacts": [],
    "duration_ms": 18400,
}
```

### Note importanti sulla codegen

- La generazione Playwright è **deterministica** e deriva solo dalla **trace MCP**.
- `extract_trace(...)` include solo step `tool_end` con `output.status="success"`: se uno step necessario fallisce/non viene eseguito durante la run, **non apparirà nello script generato**.
- Per evitare errori di Playwright strict mode su locator ambigui, il codegen applica `.first` ai locator `get_by_*` quando necessario; quando disponibile, usa anche `target["scope"]` (scope detection best-effort di `click_smart`/`fill_smart`) per generare locator scoped.

---

## API Endpoints

### Health & info

```
GET  /                       # server info
GET  /api/health             # health check + config
GET  /api/mcp/info           # configurazione MCP attiva
```

### AI Agent

```
POST /api/agent/mcp/test/run     # esegui test in linguaggio naturale
GET  /api/agent/mcp/test/stream  # stream real-time
```

**Esempio `/api/agent/mcp/test/run`:**
```bash
curl -X POST http://localhost:5000/api/agent/mcp/test/run \
  -H "Content-Type: application/json" \
  -d '{"test_description": "Go to google.com, search for AI automation, close browser"}'
```

```json
{
  "status": "success",
  "passed": true,
  "mcp_mode": "local",
  "artifacts": [],
  "errors": [],
  "duration_ms": 9200,
  "timestamp": "2025-..."
}
```

### Test AMC (login automation)

```
POST /api/test/amc/inspect   # ispeziona DOM pagina login
POST /api/test/amc/login     # test login automatico (credenziali da .env)
```

---

## MCP: Locale vs Remoto

| | Locale (`stdio`) | Remoto (`HTTP`) |
|---|---|---|
| Avvio server | subprocess automatico | `python mcp_servers/playwright_server_remote.py` |
| Comunicazione | stdin/stdout | HTTP `http://localhost:8001/mcp/` |
| Consigliato per | development, debug | production, più worker |
| Config | `MCPConfig.MODE = "local"` | `MCPConfig.MODE = "remote"` |

---

## Note tecniche

**Pass/fail:** deciso da `core/evaluation.py` sui tool results (non sull'output testuale del modello). Tolleranza: se l'ultimo uso di `click_smart`/`fill_smart` è `success`, errori precedenti dello stesso tool vengono ignorati.

**System prompts** (`agent/prompts/*`): prompt distinti per AMC/LAB/Prefix/Extraction. Il Prefix Agent lascia sempre il browser aperto (`close_browser` è esplicitamente vietato).

**LangGraph graph export:** a ogni inizializzazione agent vengono generati `langgraph.mmd`, `langgraph.txt`, `langgraph.png` nella working directory.