Sistema di test automation intelligente che usa **MCP (Model Context Protocol)**, LLM (Large Language Models) e Playwright per automatizzare test di interfacce web con architettura enterprise-ready.

![Tools](https://img.shields.io/badge/Playwright_Tools-12-blue)
![Version](https://img.shields.io/badge/version-2.2.0--inspect-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![MCP](https://img.shields.io/badge/MCP-1.12.3-purple)

---

## 📋 Indice

- [Cosa Fa Questo Progetto](#-cosa-fa-questo-progetto)
- [Architettura MCP](#️-architettura-mcp)
- [Tecnologie Utilizzate](#️-tecnologie-utilizzate)
- [Struttura del Progetto](#-struttura-del-progetto)
- [Setup Completo](#-setup-completo)
- [Configurazione LLM (OpenAI / Azure / OpenRouter)](#-configurazione-llm-openai--azure--openrouter)
- [Tool Playwright Disponibili](#️-tool-playwright-disponibili)
  - [1. start_browser](#1-start_browserheadless-bool--false)
  - [2. navigate_to_url](#2-navigate_to_urlurl-str)
  - [3. click_element](#3-click_elementselector-str-selector_type-str--css-timeout-int--30000)
  - [4. fill_input](#4-fill_inputselector-str-value-str-selector_type-str--css-clear_first-bool--true)
  - [5. wait_for_element](#5-wait_for_elementselector-str-state-str--visible-selector_type-str--css-timeout-int--30000)
  - [6. get_text](#6-get_textselector-str-selector_type-str--css)
  - [7. check_element_exists](#7-check_element_existsselector-str-selector_type-str--css)
  - [8. press_key](#8-press_keykey-str)
  - [9. capture_screenshot](#9-capture_screenshotfilename-str--none-return_base64-bool--false-)
  - [10. close_browser](#10-close_browser)
  - [11. get_page_info](#11-get_page_info)
  - [12. inspect_page_structure](#12-inspect_page_structure-)
- [API Endpoints](#-api-endpoints)
- [Esempi di Utilizzo](#-esempi-di-utilizzo)
- [MCP: Locale vs Remoto](#-mcp-locale-vs-remoto)
- [Risorse](#-risorse)

---

## 🎯 Cosa Fa Questo Progetto

Questo sistema permette di:
- ✅ Descrivere test in **linguaggio naturale** (es. "vai su google.com e cerca 'test automation'")
- ✅ **AI Agent** (GPT-4, Claude, etc.) capisce il test e lo esegue automaticamente
- ✅ **MCP Protocol** gestisce i tool in modo isolato e scalabile
- ✅ **Playwright Async** controlla il browser (clicca, compila form, naviga)
- ✅ **Screenshot Base64** ritornati direttamente nella risposta JSON
- ✅ **Page Inspector** per trovare selettori automaticamente
- ✅ **AJAX handling** automatico per caricamenti dinamici

---

## 🏗️ Architettura MCP

### Cos'è MCP?

**MCP (Model Context Protocol)** è uno standard aperto per comunicazione tra LLM e tool esterni. Creato da Anthropic, supportato da OpenAI e altri.

### Architettura del Sistema

```
┌─────────────────────────────────────────────┐
│         FRONTEND (Angular)                  │
│  - Comprende le dashboard da testare        │
│                                             │
│                                             │
└──────────────────┬──────────────────────────┘
                   │ HTTP REST API
                   ▼
┌─────────────────────────────────────────────┐
│         BACKEND (Flask)                     │
│  - Endpoint REST                            │
│  - CORS handling                            │
│                                             │
└──────────────────┬──────────────────────────┘
                   │ Python call
                   ▼
┌─────────────────────────────────────────────┐
│         AI AGENT (LangGraph)                │
│  - ReAct pattern                            │
│  - Natural language → Actions               │
│  - Tool selection                           │
│  - Multi-LLM support (OpenAI/Azure/Router)  │
└──────────────────┬──────────────────────────┘
                   │ MCP Protocol
                   ▼
┌─────────────────────────────────────────────┐
│         MCP CLIENT                          │
│  - Tool discovery                           │
│  - Request/Response handling (async)        │
└──────────────────┬──────────────────────────┘
                   │ stdio OR HTTP
                   ▼
┌─────────────────────────────────────────────┐
│    MCP SERVER (Playwright Tools)            │
│  - Exposes 12 async tools                   │
│  - Includes inspect_page_structure          │
│  - Isolated process                         │
│  - Returns base64 screenshots               │
└──────────────────┬──────────────────────────┘
                   │ Async call
                   ▼
┌─────────────────────────────────────────────┐
│         Playwright Async (Chromium)         │
│  - Browser automation (async API)           │
│  - In-memory screenshots                    │
│  - Page structure analysis                  │
└─────────────────────────────────────────────┘
```

### Vantaggi di MCP

| Vantaggio | Descrizione |
|-----------|-------------|
| **🔒 Isolamento** | Tool in processo separato → più robusto |
| **📈 Scalabile** | Tool su server dedicati se necessario |
| **🔄 Riusabile** | Tool condivisibili tra team/progetti |
| **📜 Standard** | Protocol aperto, 1000+ tool disponibili |
| **🛡️ Sicuro** | Security boundaries chiari |
| **⚡ Async** | Non-blocking I/O per performance |

---

## 🛠️ Tecnologie Utilizzate

### Backend (Python)
- **Python 3.10+** - Linguaggio principale
- **Flask 3.1.2** - Web framework per API REST
- **Playwright 1.49.1 (Async API)** - Browser automation
- **LangChain 0.3.21** - Framework per LLM
- **LangGraph 0.4.3** - Workflow orchestration
- **MCP 1.12.3** - Model Context Protocol
- **langchain-mcp-adapters 0.1.7** - MCP integration

### AI/LLM (Multi-Provider)
- **OpenAI GPT-4o-mini** - Fast & cost-effective
- **Azure OpenAI** - Enterprise compliance
- **OpenRouter** - Access to Claude, Gemini, etc.
- **Temperature 0** - Deterministic per testing

### Frontend (Angular)
- **Angular 18+** - Framework frontend
- **TypeScript** - Type-safe development
- **Material UI** - UI components

---

## 📁 Struttura del Progetto

```
ai-test-automation/
│
├── backend/                           # Backend Python
│   ├── venv/                         # Virtual environment
│   ├── .env                          # Environment variables (SECRET!)
│   ├── .env.example                  # Template per .env
│   ├── .gitignore                    # Git ignore rules
│   ├── requirements.txt              # Python dependencies (con MCP)
│   ├── app.py                        # Flask server principale
│   ├── README.md                     # Questa documentazione
│   │
│   ├── config/                       # Configuration modules
│   │   ├── __init__.py
│   │   └──settings.py               # Centralized config
│   │
│   ├── agent/                        # AI Agent modules
│   │   ├── __init__.py
│   │   ├── tools.py                  # Playwright tools ASYNC (12 tools)
│   │   └── test_agent_mcp.py        # Agent con MCP (multi-LLM)
│   │
│   ├── mcp_servers/                  # MCP Servers ASYNC
│   │   ├── __init__.py
│   │   ├── playwright_server_local.py    # Server locale (stdio) ASYNC
│   │   └── playwright_server_remote.py   # Server remoto (HTTP) ASYNC
│   │
│   └── tests/                        # Test scripts
│       ├── test_mcp_remote.py
│       └── test_webdriver_detection.py
│
└── frontend/                         # Frontend Angular
    └── (coming soon)
```

---

## 🚀 Setup Completo

### Prerequisiti

- ✅ **Python 3.10+** ([Download](https://www.python.org/downloads/))
- ✅ **Git** per version control
- ✅ **API Key** per uno di questi:
  - [OpenAI API Key](https://platform.openai.com/api-keys)
  - [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
  - [OpenRouter API Key](https://openrouter.ai/) (accesso a Claude, Gemini, etc.)

---

### Step 1: Clona il Repository

```bash
git clone <repository-url>
cd ai-test-automation/backend
```

---

### Step 2: Crea Ambiente Virtuale

```bash
# Crea venv
python -m venv venv

# Attiva venv
# Windows PowerShell:
.\venv\Scripts\Activate

# Mac/Linux:
source venv/bin/activate

# Verifica attivazione (dovresti vedere "(venv)" nel prompt)
```

---

### Step 3: Installa Dipendenze (incluso MCP)

```bash
# Aggiorna pip
python -m pip install --upgrade pip

# Installa tutte le dipendenze
pip install -r requirements.txt

# Verifica installazione MCP
python -c "import mcp; print('✅ MCP version:', mcp.__version__)"

# Installa browser Chromium
playwright install chromium
```

**Dipendenze installate:**
- Flask, Flask-CORS
- Playwright (async API)
- LangChain, LangGraph
- MCP + langchain-mcp-adapters
- OpenAI SDK

---

### Step 4: Configura Variabili d'Ambiente

Crea il file `.env` nella cartella `backend/`:

```bash
# backend/.env

# ============================================
# LLM Configuration (scegli UNO)
# ============================================

# Opzione 1: OpenRouter (Raccomandato - accesso a Claude, Gemini, GPT) ⭐
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
# Altri modelli: openai/gpt-4o-mini, google/gemini-2.0-flash-exp:free

# Opzione 2: OpenAI Standard
# OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE

# Opzione 3: Azure OpenAI (Enterprise)
# AZURE_OPENAI_API_KEY=your_azure_key
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
# AZURE_OPENAI_API_VERSION=2024-08-01-preview

# ============================================
# Flask Configuration
# ============================================
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_PORT=5000

# ============================================
# Playwright Configuration (opzionale)
# ============================================
PLAYWRIGHT_HEADLESS=False
PLAYWRIGHT_TIMEOUT=30000

# ============================================
# AMC Login Credentials (per test automation)
# ============================================
AMC_USERNAME=tuo.nome.cognome@eng.it
AMC_PASSWORD=tua_password_sicura
```

> 🔐 **IMPORTANTE:** 
> - Non committare MAI `.env` su Git!
> - Usa `.env.example` come template
> - Configura SOLO UNO dei provider LLM

**Priorità Detection:**
1. 🟣 OpenRouter (se `OPENROUTER_API_KEY` presente)
2. 🔵 Azure OpenAI (se `AZURE_OPENAI_API_KEY` presente)
3. 🟢 OpenAI Standard (se `OPENAI_API_KEY` presente)

---

### Step 5: Test Installazione

```bash
# Test 1: Verifica Python packages
python -c "import flask, playwright, langchain, mcp; print('✅ All packages OK')"

# Test 2: Verifica MCP
python -c "from langchain_mcp_adapters.client import MultiServerMCPClient; print('✅ MCP adapters OK')"

# Test 3: Verifica API key
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ API key loaded' if (os.getenv('OPENAI_API_KEY') or os.getenv('OPENROUTER_API_KEY') or os.getenv('AZURE_OPENAI_API_KEY')) else '❌ Missing API key')"
```

Se tutti i test passano: **✅ Setup completato!**

---

### Step 6: Avvia il Server

```bash
# Assicurati che venv sia attivo
python app.py
```

**Output atteso (con OpenRouter):**

```
================================================================================
VALIDAZIONE CONFIGURAZIONE
================================================================================
MCP Mode: REMOTE - Assicurati che il server sia attivo su http://localhost:8001/mcp/
LLM Provider: OPENROUTER
   Model: openai/gpt-4o-mini
Flask: localhost:5000
Playwright: headless=False
================================================================================

 AI Agent MCP caricato con successo!

================================================================================
AI TEST AUTOMATION SERVER (MCP Edition)
================================================================================
URL: http://localhost:5000
MCP Mode: remote

 ENDPOINT DISPONIBILI:

[BASE]
   - GET  /                      → Server info
   - GET  /api/health            → Health check

[BROWSER - Diretti (senza MCP)]
   - POST /api/browser/start     → Avvia browser
   - POST /api/browser/navigate  → Naviga a URL
   - GET  /api/browser/screenshot → Screenshot
   - POST /api/browser/close     → Chiudi browser

[AI AGENT MCP]
   - POST /api/agent/mcp/test/run    → Esegui test con AI+MCP
   - GET  /api/agent/mcp/test/stream → Stream test real-time
   - GET  /api/mcp/info              → Info configurazione MCP

   MCP Mode: REMOTE
      Server remoto: http://localhost:8001/mcp/
      (Assicurati che playwright_server_remote.py sia attivo)

[AMC LOGIN TEST]
   - POST /api/test/amc/inspect      → Ispeziona form login
   - POST /api/test/amc/login        → Test login automatico
  Credenziali configurate: tuo.nome.cognome@eng.it

================================================================================
Premi CTRL+C per fermare il server
================================================================================
```

---

### Step 7: Test Rapido

Apri un **nuovo terminale** e testa:

```bash
# Test 1: Health check
curl http://localhost:5000/api/health

# Test 2: MCP info
curl http://localhost:5000/api/mcp/info

# Test 3: Esegui test con AI Agent
curl -X POST http://localhost:5000/api/agent/mcp/test/run \
  -H "Content-Type: application/json" \
  -d '{"test_description": "Go to google.com, if a cookie consent banner appears handle cookie banner, search for 'AI test automation', wait for results, and close"}'
```

**Risposta attesa (Test 3):**
```json
{
  "status": "success",
  "final_answer": "✅ Test completed successfully...",
  "passed": true,
  "mcp_mode": "remote",
  "timestamp": "2024-12-18T..."
}
```

Se vedi questo: **🎉 Tutto funziona!**

---

## 🔧 Configurazione LLM (OpenAI / Azure / OpenRouter)

Il sistema supporta **3 provider LLM** con auto-detection:

### OpenRouter (Raccomandato) ⭐

**Vantaggi:**
- ✅ Accesso a Claude, Gemini, GPT, e altri
- ✅ API key unica per tutti i modelli
- ✅ Modelli gratuiti disponibili
- ✅ Economico per testing

**Setup:**
```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

**Modelli consigliati:**
- `anthropic/claude-3.5-sonnet` - Migliore qualità
- `anthropic/claude-3-haiku` - Economico
- `openai/gpt-4o-mini` - GPT via OpenRouter
- `google/gemini-2.0-flash-exp:free` - Gratuito

**Ottieni key:** [openrouter.ai](https://openrouter.ai/)

---

### Azure OpenAI (Enterprise)

**Vantaggi:**
- ✅ Compliance aziendale
- ✅ Data residency EU
- ✅ SLA garantito

**Setup:**
```bash
# .env
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

---

### OpenAI Standard

**Setup:**
```bash
# .env
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
```

**Modello:** `gpt-4o-mini` (hardcoded)

---

## 🛠️ Tool Playwright Disponibili

Il sistema espone **12 tool async** tramite MCP Server:

### 1. `start_browser(headless: bool = False)`
Avvia browser Chromium (async).

**Args:**
- `headless`: Se True, browser invisibile

**Esempio:**
```python
await start_browser(headless=False)  # Vedi il browser
```

---

### 2. `navigate_to_url(url: str)`
Naviga a URL e aspetta caricamento (async).

**Esempio:**
```python
await navigate_to_url("https://google.com")
```

---

### 3. `click_element(selector: str, selector_type: str = "css", timeout: int = 30000)`
Clicca su elemento (async).

**Selector types:**
- `"css"` - CSS selector (default)
- `"xpath"` - XPath
- `"text"` - Testo visibile

**Esempi:**
```python
await click_element("#login-button", "css")
await click_element("//button[@type='submit']", "xpath")
await click_element("Accedi", "text")
```

---

### 4. `fill_input(selector: str, value: str, selector_type: str = "css", clear_first: bool = True)`
Compila campo input (async).

**Esempio:**
```python
await fill_input("input[name='username']", "testuser")
```

---

### 5. `wait_for_element(selector: str, state: str = "visible", selector_type: str = "css", timeout: int = 30000)`

**FONDAMENTALE per AJAX!** Aspetta che elemento appaia/scompaia (async).

**States:**
- `"visible"` - Elemento visibile
- `"hidden"` - Elemento nascosto
- `"attached"` - Nel DOM
- `"detached"` - Rimosso dal DOM

**Esempio:**
```python
await wait_for_element("#search-results", "visible")
```

---

### 6. `get_text(selector: str, selector_type: str = "css")`
Estrae testo da elemento (async).

---

### 7. `check_element_exists(selector: str, selector_type: str = "css")`
Verifica esistenza elemento (async).

---

### 8. `press_key(key: str)`
Simula pressione tasto (async).

**Esempio:**
```python
await press_key("Enter")
await press_key("Escape")
```

---

### 9. `capture_screenshot(filename: str = None, return_base64: bool = False)` ⭐

Cattura screenshot full-page (async).

**IMPORTANTE:** Ritorna base64 solo se `return_base64=True` (risparmia token!)

**Esempio:**
```python
await capture_screenshot("page.png", return_base64=False)  # No base64
await capture_screenshot("page.png", return_base64=True)   # Con base64
```

---

### 10. `close_browser()`
Chiude browser e libera risorse (async).

---

### 11. `get_page_info()`
Ottiene URL, titolo, viewport correnti (async).

---

### 12. `inspect_page_structure()`

**Ispeziona la struttura della pagina** per trovare selettori corretti (form, input, button).

**Utilità:**
- 🔍 Debug di form di login
- 📋 Scoperta selettori per pagine sconosciute
- 🛠️ Analisi struttura DOM
- 📝 Documentazione automatica selettori

**Returns:**
```json
{
  "status": "success",
  "message": "Page structure analyzed: 3 inputs, 3 buttons, 1 forms",
  "page_info": {
    "url": "https://amc.eng.it/multimodule/web/",
    "title": "Ellipse COT |"
  },
  "inputs": [
    {
      "index": 0,
      "type": "text",
      "name": "username",
      "id": "",
      "placeholder": "Username",
      "class": "mat-input-element",
      "selector_suggestions": [
        "input[name='username']",
        "input[type='text']",
        "input[placeholder='Username']"
      ]
    },
    {
      "index": 1,
      "type": "password",
      "name": "password",
      "placeholder": "",
      "selector_suggestions": [
        "input[name='password']",
        "input[type='password']"
      ]
    },
    {
      "index": 2,
      "type": "checkbox",
      "name": "useDefaultProfiling",
      "selector_suggestions": [
        "input[name='useDefaultProfiling']",
        "input[type='checkbox']"
      ]
    }
  ],
  "buttons": [
    {
      "index": 0,
      "text": "Login",
      "type": "submit",
      "id": "",
      "class": "mat-raised-button",
      "selector_suggestions": [
        "button:has-text('Login')",
        "button[type='submit']"
      ]
    },
    {
      "index": 1,
      "text": "Accedi",
      "type": "button",
      "selector_suggestions": [
        "button:has-text('Accedi')"
      ]
    },
    {
      "index": 2,
      "text": "Recupera password",
      "type": "button",
      "selector_suggestions": [
        "button:has-text('Recupera password')"
      ]
    }
  ],
  "forms": [
    {
      "index": 0,
      "action": "/auth/login",
      "method": "POST",
      "id": "login-form"
    }
  ]
}
```

**Esempio uso AI Agent:**
```javascript
// Test description
"Go to https://example.com/login, inspect the page structure to find login form selectors, then close"

// AI Agent calls:
1. start_browser()
2. navigate_to_url("https://example.com/login")
3. wait_for_element("body", "visible")
4. inspect_page_structure()  // ⭐ NEW TOOL
5. close_browser()

// Output includes all selectors ready to use!
```

**Quando usarlo:**
- ✅ **Prima di scrivere test per pagine nuove** (scopri selettori in 5 secondi)
- ✅ **Test in linguaggio naturale** ("login with user/pass") → AI usa inspect automaticamente
- ✅ **Per trovare selettori corretti quando i test falliscono** (selettori cambiati?)
- ✅ **Debug di form complessi** (login, registrazione, checkout)
- ✅ **Documentazione struttura pagine per il team**
- ✅ **Anti-guessing strategy** → evita che AI inventi selettori inesistenti

**Quando NON usarlo:**
- ❌ Se conosci già i selettori E sono stabili (usa direttamente `fill_input`, `click_element`)
- ❌ Pagine molto dinamiche (React/Angular con ID random ogni render)
- ❌ Test ad alte performance (inspect aggiunge ~2-3 secondi)
- ❌ Solo per curiosità (costa tempo/token LLM)

---

### 💡 Anti-Guessing Strategy con inspect_page_structure

**Problema comune in AI test automation:**
```python
# AI che INVENTA selettori (MALE ❌)
fill_input("#username", "test")     # Elemento non esiste!
fill_input("#password", "pass")      # Elemento non esiste!
click_element("#login-btn")          # Elemento non esiste!
→ Test FALLISCE
```

**Soluzione in questo progetto:**
```python
# AI che SCOPRE selettori (BENE ✅)
inspect_page_structure()             # Ispeziona pagina reale
→ Trova: input[name='username'], input[name='password'], button:has-text('Login')

fill_input("input[name='username']", "test")   # Elemento esiste!
fill_input("input[name='password']", "pass")    # Elemento esiste!
click_element("button:has-text('Login')")       # Elemento esiste!
→ Test PASSA
```

**System Prompt istruisce l'AI:**
```
SELECTOR DISCOVERY (CRITICAL):
- NEVER guess selectors like #username, #password
- When test says "fill username/password" without exact selectors:
    1. Call inspect_page_structure() FIRST
    2. Use the suggested selectors from the output
    3. Then fill_input/click_element with discovered selectors
```
---

## 🌐 API Endpoints

### [BASE]

#### `GET /`
Server info e status.

#### `GET /api/health`
Health check con info configurazione.

---

### [AI AGENT MCP]

#### `POST /api/agent/mcp/test/run`
Esegue test con AI Agent tramite MCP.

**Body:**
```json
{
  "test_description": "Go to google.com and search for 'AI testing'"
}
```

**Response:**
```json
{
  "status": "success",
  "test_description": "Go to google.com...",
  "final_answer": "✅ Test completed successfully...",
  "passed": true,
  "mcp_mode": "local",
  "screenshots": [...],
  "screenshots_count": 1,
  "timestamp": "2024-12-18T..."
}
```

---

#### `GET /api/mcp/info`
Info configurazione MCP.

**Response:**
```json
{
  "mcp_mode": "local",
  "server_config": {
    "command": "python",
    "args": ["-m", "mcp_servers.playwright_server_local"],
    "transport": "stdio"
  },
  "tools_count": 12
}
```

---

### [AMC LOGIN TEST] 🔐

#### `POST /api/test/amc/inspect`
Ispeziona DOM.

**Response:**
```json
{
  "status": "success",
  "test_type": "amc_inspect",
  "final_answer": "📝 Page structure with selectors...",
  "note": "Use this info to update selectors in config"
}
```

---

#### `POST /api/test/amc/login`
Test login automatico (usa credenziali da `.env`).

**Body (opzionale):**
```json
{
  "take_screenshot": true,
  "wait_after_login": 5
}
```

**Response:**
```json
{
  "status": "success",
  "test_type": "amc_login",
  "username": "tuo.nome.cognome@eng.it",
  "passed": true,
  "final_answer": "✅ Login successful...",
  "note": "Credentials loaded from environment variables"
}
```

---

## 💡 Esempi di Utilizzo

### Esempio 1: Test Semplice con Screenshot

```bash
curl -X POST http://localhost:5000/api/agent/mcp/test/run \
  -H "Content-Type: application/json" \
  -d '{
    "test_description": "Go to google.com, take a screenshot, and close the browser"
  }' | jq '.'
```

---

### Esempio 2: Test AJAX con Wait

```bash
curl -X POST http://localhost:5000/api/agent/mcp/test/run \
  -H "Content-Type: application/json" \
  -d '{
    "test_description": "Go to google.com, search for test automation, wait for results to appear, take screenshot and close"
  }'
```

**⚠️ IMPORTANTE:** L'AI Agent deve usare `wait_for_element()` per AJAX!

---

### Tool Combinations

**Pattern 1: Login Automation**
```javascript
// Test description
"Go to login page, inspect structure, fill credentials, login"

// AI Agent execution:
1. start_browser()
2. navigate_to_url(login_page)
3. inspect_page_structure()  // ← Trova selettori
4. fill_input(username_selector, username)  // ← Usa selettori trovati
5. fill_input(password_selector, password)
6. click_element(login_button)
7. wait_for_element(dashboard_element)
8. close_browser()
```

---

## 🔄 MCP: Locale vs Remoto

### Modalità Locale (Default)

```python
# config/settings.py
MCPConfig.MODE = "local"
```

**Come funziona:**
- MCP Server avviato come **subprocess** da Python
- Comunicazione via **stdio** (stdin/stdout)
- Stesso processo Python

**Vantaggi:**
- ✅ Più semplice da debuggare
- ✅ No configurazione network
- ✅ Meno overhead
- ✅ Raccomandato per development

---

### Modalità Remota

```python
# config/settings.py
MCPConfig.MODE = "remote"
MCPConfig.REMOTE_HOST = "localhost"
MCPConfig.REMOTE_PORT = 8000
```

**Come funziona:**
- MCP Server come **processo separato**
- Comunicazione via **HTTP**
- Può essere su macchina diversa

**Avvio manuale server:**
```bash
python mcp_servers/playwright_server_remote.py
```

**Vantaggi:**
- ✅ Server scalabile (più worker)
- ✅ Server su macchina dedicata
- ✅ Isolamento completo
- ✅ Raccomandato per production
---

## 📚 Risorse

### Documentazione Ufficiale

- **MCP Protocol:** https://modelcontextprotocol.io/
- **Playwright Python:** https://playwright.dev/python/
- **LangChain:** https://python.langchain.com/
- **OpenRouter:** https://openrouter.ai/docs

### Tool Specifici

- **inspect_page_structure:** Vedi sezione [Tool Playwright Disponibili](#️-tool-playwright-disponibili)
- **Browser Config:** `backend/config/browser_config.py`
- **AMC Config:** `backend/config/settings.py` → `AMCConfig`
---

</parameter>