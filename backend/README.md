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
- [Tool Playwright (21 tools)](#tool-playwright)
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
  ├─ system_prompt.py   ← regole comportamento agent
  ├─ evaluation.py      ← pass/fail da tool results (non dal modello)
  └─ orchestrator.py    ← Prefix Agent + Scenario Agent
       │ MCP Protocol
       ▼
MCP Client (langchain-mcp-adapters)
       │ stdio | HTTP
       ▼
MCP Server (playwright_server_local / remote)
  └─ 21 Playwright tools async
       │
       ▼
Playwright Async (Chromium)
```

**Flusso orchestrato (LAB):**
1. **Prefix Agent** → login, selezione organizzazione, navigazione al modulo Laboratory (browser rimane aperto)
2. **Scenario Agent** → esegue lo scenario LAB dalla dashboard Laboratory, chiude il browser

Il pass/fail è deciso da `evaluation.py` sui tool results, non dall'output testuale del modello.

---

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
│   ├── tools.py                    # 21 Playwright tools async
│   ├── system_prompt.py            # Prompt AMC, LAB Scenario, LAB Prefix
│   ├── lab_scenarios.py            # Definizione 4 scenari LAB
│   ├── orchestrator.py             # Prefix Agent + Scenario Agent + run_full
│   ├── test_agent_mcp.py           # TestAgentMCP: init, run_test_async, stream
│   ├── evaluation.py               # Pass/fail logic da tool results
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

Il MCP server espone **21 tool async**. Fonte unica: `mcp_servers/tool_names.py`.

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
| `press_key(key)` | Simula pressione tasto (Enter, Escape, ...) |
| `capture_screenshot(filename, return_base64)` | Screenshot full-page; `return_base64=False` per default (risparmia token) |
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

`orchestrator.py` gestisce il flusso completo in due fasi con agenti separati.

```python
from agent.orchestrator import run_full_sync

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

**Struttura risultato:**
```python
{
    "passed": True,
    "phase": "full",
    "prefix": { ... },   # risultato Prefix Agent
    "scenario": { ... }, # risultato Scenario Agent
    "errors": [],
    "artifacts": [{"type": "screenshot", "filename": "test_success.png"}],
    "duration_ms": 18400,
}
```

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

**Pass/fail:** deciso da `evaluation.py` sui tool results (non sull'output testuale del modello). Tolleranza: se l'ultimo uso di `click_smart`/`fill_smart` è `success`, errori precedenti dello stesso tool vengono ignorati.

**System prompts** (`system_prompt.py`): tre prompt distinti — `AMC_SYSTEM_PROMPT`, `LAB_SYSTEM_PROMPT`, `LAB_PREFIX_PROMPT`. Il Prefix Agent lascia sempre il browser aperto (`close_browser` è esplicitamente vietato).

**LangGraph graph export:** a ogni inizializzazione agent vengono generati `langgraph.mmd`, `langgraph.txt`, `langgraph.png` nella working directory.