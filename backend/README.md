Sistema di test automation intelligente che usa **MCP (Model Context Protocol)**, LLM (Large Language Models) e Playwright per automatizzare test di interfacce web con architettura enterprise-ready.

![Tools](https://img.shields.io/badge/Playwright_Tools-12-blue)
![Version](https://img.shields.io/badge/version-2.2.0--inspect-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![MCP](https://img.shields.io/badge/MCP-1.12.3-purple)

---

## 📋 Indice

- [Cosa Fa Questo Progetto](#-cosa-fa-questo-progetto)
- [Architettura MCP](#-architettura-mcp)
- [Tecnologie Utilizzate](#️-tecnologie-utilizzate)
- [Struttura del Progetto](#-struttura-del-progetto)
- [Setup Completo](#-setup-completo)
- [Configurazione MCP](#-configurazione-mcp)
- [Configurazione LLM](#-configurazione-llm-openai--azure--openrouter)
- [Tool Playwright Disponibili](#️-tool-playwright-disponibili)
- [🆕 NEW: Inspect Page Structure](#-new-inspect-page-structure-tool-)
- [API Endpoints](#-api-endpoints)
- [Screenshot in Base64](#-screenshot-in-base64)
- [Esempi di Utilizzo](#-esempi-di-utilizzo)
- [Best Practices](#-best-practices)
- [MCP: Locale vs Remoto](#-mcp-locale-vs-remoto)
- [Troubleshooting](#-troubleshooting)
- [Per Martina](#-per-martina-setup-veloce)
- [Changelog](#-changelog)
- [Risorse](#-risorse)

---

## 🎯 Cosa Fa Questo Progetto

Questo sistema permette di:
- ✅ Descrivere test in **linguaggio naturale** (es. "vai su google.com e cerca 'test automation'")
- ✅ **AI Agent** (GPT-4, Claude, etc.) capisce il test e lo esegue automaticamente
- ✅ **MCP Protocol** gestisce i tool in modo isolato e scalabile
- ✅ **Playwright Async** controlla il browser (clicca, compila form, naviga)
- ✅ **Screenshot Base64** ritornati direttamente nella risposta JSON
- ✅ **Page Inspector** 🔍 per trovare selettori automaticamente (NEW!)
- ✅ **AJAX handling** automatico per caricamenti dinamici
- ✅ Test **robusti** con retry logic e wait strategies

### 🌟 Esempio Pratico

```
👤 User: "Go to google.com, search for 'AI testing', 
         wait for results, and take a screenshot"

🤖 AI Agent:
   1. ✅ start_browser()
   2. ✅ navigate_to_url("https://google.com")
   3. ✅ fill_input("textarea[name='q']", "AI testing")
   4. ✅ press_key("Enter")
   5. ✅ wait_for_element("#search", state="visible")
   6. ✅ capture_screenshot("search-results.png")
   7. ✅ close_browser()

📊 Result: Test PASSED
📸 Screenshot: Base64 in JSON response (no disk files!)
```

---

## 🏗️ Architettura MCP

### Cos'è MCP?

**MCP (Model Context Protocol)** è uno standard aperto per comunicazione tra LLM e tool esterni. Creato da Anthropic, supportato da OpenAI e altri.

### Architettura del Sistema

```
┌─────────────────────────────────────────────┐
│         FRONTEND (Angular)                  │
│  - UI per creare test                       │
│  - Dashboard risultati                      │
│  - Live streaming                           │
└──────────────────┬──────────────────────────┘
                   │ HTTP REST API
                   ▼
┌─────────────────────────────────────────────┐
│         BACKEND (Flask)                     │
│  - Endpoint REST                            │
│  - CORS handling                            │
│  - Screenshot base64 extraction             │
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
│  - Includes inspect_page_structure (NEW)    │
│  - Isolated process                         │
│  - Returns base64 screenshots               │
└──────────────────┬──────────────────────────┘
                   │ Async call
                   ▼
┌─────────────────────────────────────────────┐
│         Playwright Async (Chromium)         │
│  - Browser automation (async API)           │
│  - In-memory screenshots                    │
│  - Page structure analysis (NEW)            │
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
- **Playwright 1.49.1 (Async API)** ⭐ - Browser automation
- **LangChain 0.3.21** - Framework per LLM
- **LangGraph 0.4.3** - Workflow orchestration
- **MCP 1.12.3** ⭐ - Model Context Protocol
- **langchain-mcp-adapters 0.1.7** - MCP integration

### AI/LLM (Multi-Provider)
- **OpenAI GPT-4o-mini** - Fast & cost-effective
- **Azure OpenAI** - Enterprise compliance
- **OpenRouter** ⭐ - Access to Claude, Gemini, etc.
- **Temperature 0** - Deterministic per testing

### Frontend (Angular) - Coming Soon
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
│   │   ├── settings.py               # Centralized config
│   │   └── browser_config.py         # Browser fingerprint config
│   │
│   ├── agent/                        # AI Agent modules
│   │   ├── __init__.py
│   │   ├── tools.py                  # ⭐ Playwright tools ASYNC (12 tools)
│   │   └── test_agent_mcp.py        # ⭐ Agent con MCP (multi-LLM)
│   │
│   ├── mcp_servers/                  # ⭐ MCP Servers ASYNC
│   │   ├── __init__.py
│   │   ├── playwright_server_local.py    # Server locale (stdio) ASYNC
│   │   └── playwright_server_remote.py   # Server remoto (HTTP) ASYNC
│   │
│   └── tests/                        # Test scripts
│       ├── test_amc_cookies.py
│       ├── test_bot_detection.py
│       └── get_my_browser_config.py
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
  - [OpenRouter API Key](https://openrouter.ai/) ⭐ (accesso a Claude, Gemini, etc.)

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
- **MCP + langchain-mcp-adapters** ⭐
- OpenAI SDK

**⏱️ Tempo stimato:** 3-5 minuti

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
AMC_USERNAME=tuo.cognome@eng.it
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
🔧 VALIDAZIONE CONFIGURAZIONE
================================================================================
🟣 LLM Provider: OpenRouter
   Model: anthropic/claude-3.5-sonnet
   Temperature: 0

💻 MCP Mode: local (stdio)
   Remote: localhost:8000

🌐 Flask: localhost:5000
🎭 Playwright: headless=False
================================================================================

✅ AI Agent MCP caricato con successo!

================================================================================
🤖 AI TEST AUTOMATION SERVER (MCP Edition - Optimized)
================================================================================
URL: http://localhost:5000
MCP Mode: local

📋 ENDPOINT DISPONIBILI:

[BASE]
   - GET  /                      → Server info
   - GET  /api/health            → Health check

[BROWSER - Diretti]
   - POST /api/browser/start
   - POST /api/browser/navigate
   - GET  /api/browser/screenshot
   - POST /api/browser/close

[AI AGENT MCP] ⭐
   - POST /api/agent/mcp/test/run    → Esegui test generico
   - GET  /api/agent/mcp/test/stream → Stream real-time
   - GET  /api/mcp/info              → Info configurazione MCP

[AMC LOGIN TEST] 🔐
   - POST /api/test/amc/inspect      → Ispeziona form login
   - POST /api/test/amc/login        → Test login automatico
   ✅ Credenziali configurate: tuo.cognome@eng.it

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
  -d '{"test_description": "Go to google.com, take a screenshot, and close the browser"}'
```

**Risposta attesa (Test 3):**
```json
{
  "status": "success",
  "final_answer": "✅ Test completed successfully...",
  "passed": true,
  "mcp_mode": "local",
  "screenshots": [
    {
      "filename": "screenshot_1.png",
      "base64": "iVBORw0KGgoAAAANSUhEUg...",
      "size_bytes": 245678,
      "source": "ai_agent_response"
    }
  ],
  "screenshots_count": 1,
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

### 5. `wait_for_element(selector: str, state: str = "visible", selector_type: str = "css", timeout: int = 30000)` ⭐

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

### 12. `inspect_page_structure()` 🔍 **NEW!**

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
- ✅ Prima di scrivere test per pagine nuove
- ✅ Per trovare selettori corretti quando i test falliscono
- ✅ Debug di form complessi (login, registrazione, checkout)
- ✅ Documentazione struttura pagine per il team

**Quando NON usarlo:**
- ❌ Se conosci già i selettori (usa direttamente `fill_input`, `click_element`)
- ❌ Pagine molto dinamiche (React/Angular con ID random)
- ❌ Solo per curiosità (costa tempo/token LLM)

---

## 🆕 NEW: Inspect Page Structure Tool 🔍

### Quick Start

**Esempio 1: Ispeziona Login Form**

```bash
curl -X POST http://localhost:5000/api/agent/mcp/test/run \
  -H "Content-Type: application/json" \
  -d '{
    "test_description": "Go to https://amc.eng.it/multimodule/web/, wait 3 seconds, inspect page structure and close"
  }'
```

**Response include:**
```json
{
  "final_answer": "✅ Page Structure Analysis Complete\n\n📄 Page Info:\n   URL: https://amc.eng.it/multimodule/web/\n   Title: Ellipse COT |\n\n📝 INPUT FIELDS (3):\n\n   Input #0:\n      Type: text\n      Name: username\n      Suggested selectors:\n         - input[name='username']\n         - input[type='text']\n\n   Input #1:\n      Type: password\n      Name: password\n      Suggested selectors:\n         - input[name='password']\n\n🔘 BUTTONS (3):\n\n   Button #0:\n      Text: 'Login'\n      Suggested selectors:\n         - button:has-text('Login')\n         - button[type='submit']",
  "passed": true
}
```

---

**Esempio 2: Workflow Login Automation**

```bash
# Step 1: Ispeziona pagina
curl -X POST http://localhost:5000/api/agent/mcp/test/run \
  -H "Content-Type: application/json" \
  -d '{"test_description": "Inspect login page at https://example.com/login"}'

# Ottieni selettori: input[name='username'], input[name='password'], button:has-text('Login')

# Step 2: Usa selettori trovati nel test
curl -X POST http://localhost:5000/api/agent/mcp/test/run \
  -H "Content-Type: application/json" \
  -d '{
    "test_description": "Go to https://example.com/login, fill input[name=\"username\"] with \"testuser\", fill input[name=\"password\"] with \"password123\", click button:has-text(\"Login\"), wait for dashboard and close"
  }'
```

---

### Endpoint Dedicato AMC

Per ispezionare il form AMC:

```bash
curl -X POST http://localhost:5000/api/test/amc/inspect
```

**Response:**
```json
{
  "status": "success",
  "test_type": "amc_inspect",
  "final_answer": "📝 INPUT FIELDS:\n   - username: input[name='username']\n   - password: input[name='password']\n\n🔘 BUTTONS:\n   - Login: button:has-text('Login')",
  "note": "Use this info to update selectors in config/settings.py AMCConfig"
}
```

---

## 📸 Screenshot in Base64

### Come Funziona

Gli screenshot **NON vengono salvati su disco**. Il flusso è:

```
1. Browser cattura screenshot → genera bytes in memoria
2. Tool converte in base64
3. MCP Server ritorna base64 nel messaggio (con marker)
4. AI Agent riceve il messaggio
5. Flask estrae base64 dal messaggio AI
6. JSON response include base64 direttamente
```

**ZERO file su disco!** Solo base64 in memoria → JSON response.

---

### Response con Screenshot

```json
{
  "status": "success",
  "final_answer": "✅ Test completed...",
  "passed": true,
  "screenshots": [
    {
      "filename": "screenshot_1.png",
      "base64": "iVBORw0KGgoAAAANSUhEUgAAA...",
      "size_bytes": 245678,
      "source": "ai_agent_response"
    }
  ],
  "screenshots_count": 1
}
```

---

### Salvare Screenshot da PowerShell

```powershell
# Esegui test
$response = Invoke-RestMethod -Uri http://localhost:5000/api/agent/mcp/test/run `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"test_description": "Go to google.com, take a screenshot"}'

# Salva screenshot se presente
if ($response.screenshots_count -gt 0) {
    $screenshot = $response.screenshots[0]
    $bytes = [Convert]::FromBase64String($screenshot.base64)
    [IO.File]::WriteAllBytes("screenshot.png", $bytes)
    Write-Host "✅ Screenshot salvato: screenshot.png"
    start screenshot.png
}
```

---

### Salvare Screenshot da Python

```python
import requests
import base64

# Esegui test
response = requests.post("http://localhost:5000/api/agent/mcp/test/run",
    json={"test_description": "Go to google.com, take a screenshot"})

data = response.json()

# Salva screenshot
if data["screenshots_count"] > 0:
    screenshot_base64 = data["screenshots"][0]["base64"]
    screenshot_bytes = base64.b64decode(screenshot_base64)
    
    with open("screenshot.png", "wb") as f:
        f.write(screenshot_bytes)
    
    print("✅ Screenshot salvato!")
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
Ispeziona form di login AMC.

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
Test login automatico su AMC (usa credenziali da `.env`).

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
  "username": "tuo.cognome@eng.it",
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
    "test_description": "Go to google.com, search for test automation, wait for results to appear using wait_for_element, take screenshot and close"
  }'
```

**⚠️ IMPORTANTE:** L'AI Agent sa che deve usare `wait_for_element()` per AJAX!

---

### Esempio 3: Ispeziona Form di Login 🔍

**Caso d'uso:** Devi scrivere test per un'applicazione ma non conosci i selettori.

```bash
curl -X POST http://localhost:5000/api/agent/mcp/test/run \
  -H "Content-Type: application/json" \
  -d '{
    "test_description": "Go to https://amc.eng.it/multimodule/web/, wait 3 seconds, inspect page structure to find login form selectors, then close"
  }'
```

**Response include:**
```json
{
  "status": "success",
  "final_answer": "Page structure analyzed:\n\n📝 INPUT FIELDS (3):\n   Input #0: username (text)\n      - input[name='username']\n   Input #1: password (password)\n      - input[name='password']\n\n🔘 BUTTONS (3):\n   Button #0: 'Login'\n      - button:has-text('Login')",
  "passed": true
}
```

**Ora puoi usare i selettori trovati nei tuoi test!**

---

### Esempio 4: Login Automation con Inspect

**Step 1: Ispeziona pagina**
```bash
curl -X POST http://localhost:5000/api/test/amc/inspect
```

**Step 2: Usa selettori trovati**
```bash
curl -X POST http://localhost:5000/api/test/amc/login \
  -H "Content-Type: application/json" \
  -Body '{"take_screenshot": true}'
```

---

### Esempio 5: Test con OpenRouter + Claude

```bash
# .env configurato con OpenRouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Esegui test complesso
curl -X POST http://localhost:5000/api/agent/mcp/test/run \
  -H "Content-Type: application/json" \
  -d '{
    "test_description": "Go to complex-app.com, inspect the registration form, fill all required fields with test data, submit and wait for confirmation message"
  }'

# Claude interpreta, ispeziona il form, e esegue il test
```

---

## 💡 Best Practices

### Quando Usare `inspect_page_structure`

✅ **USA quando:**
- Prima di scrivere test per nuove pagine
- I selettori cambiano e i test falliscono
- Non conosci la struttura del form
- Devi documentare selettori per il team
- Debug di form complessi (multi-step, dinamici)

❌ **NON usare quando:**
- Conosci già i selettori (usa direttamente `fill_input`, `click_element`)
- Pagine molto dinamiche (React/Angular con ID random)
- Solo per curiosità (costa tempo/token LLM)
- Test semplici su pagine ben documentate

---

### Workflow Consigliato

```
1. Inspect → Trova selettori
   ↓
2. Documenta → Salva selettori in config
   ↓
3. Test → Usa selettori documentati
   ↓
4. Maintain → Re-inspect solo se test falliscono
```

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

**Pattern 2: Form Discovery**
```javascript
// Test description
"Inspect registration form on signup page"

// AI Agent execution:
1. start_browser()
2. navigate_to_url(signup_page)
3. inspect_page_structure()  // ← Documenta tutti i campi
4. [Save output for reference]
5. close_browser()
```

---

**Pattern 3: AJAX + Inspect**
```javascript
// Test description
"Search for products, wait for results, inspect first product card"

// AI Agent execution:
1. start_browser()
2. navigate_to_url(shop_url)
3. fill_input(search_box, "laptop")
4. press_key("Enter")
5. wait_for_element(results_container, "visible")  // ← AJAX wait
6. inspect_page_structure()  // ← Analizza risultati
7. close_browser()
```

---

### Error Handling

**Se `inspect_page_structure` fallisce:**

```javascript
// Possibile causa: Pagina non completamente caricata
"Go to slow-page.com, wait 5 seconds, inspect page structure"

// Soluzione: Aggiungi wait esplicito
"Go to slow-page.com, wait for element body to be visible, then inspect page structure"
```

---

### Token Optimization

**`inspect_page_structure` ritorna molto testo!**

```
Tipico output: ~500-1000 tokens per pagina complessa
```

**Ottimizzazione:**
- ✅ Usa solo quando necessario
- ✅ Salva output in documentazione (non re-ispezionare ogni volta)
- ✅ Combina con altri tool nello stesso test
- ❌ Non usare su pagine con 50+ input (output enorme)

---

## 🔄 MCP: Locale vs Remoto

### Modalità Locale (Default) ⭐

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

## 🐛 Troubleshooting

### Problema: Screenshot count = 0

**Causa:** Base64 non estratto correttamente dalla risposta AI.

**Soluzione:**
1. Verifica che `tools.py` usa **async Playwright**
2. Verifica che MCP server ritorna base64 con marker `🔑 SCREENSHOT_BASE64:`
3. Verifica regex in `app.py`:
   ```python
   pattern = r'🔑 SCREENSHOT_BASE64:\s*([A-Za-z0-9+/=]+)'
   ```

---

### Problema: inspect_page_structure ritorna vuoto

**Causa:** Pagina non completamente caricata o elementi dinamici.

**Soluzione:**
```javascript
// Aggiungi wait esplicito prima di inspect
"Go to page.com, wait 3 seconds, then inspect page structure"

// Oppure usa wait_for_element
"Go to page.com, wait for element body to be visible, then inspect"
```

---

### Problema: AsyncIO errors

**Causa:** Mixing sync/async code.

**Soluzione:**
- Usa **async Playwright** (`from playwright.async_api import async_playwright`)
- Tutti i tool devono essere `async def`
- Tutti i MCP server tool devono essere `async`

---

### Problema: Selettori non funzionano

**Causa:** Selettori suggeriti da `inspect_page_structure` potrebbero non essere unici.

**Soluzione:**
```python
# Se selector non funziona
"input[name='username']"  # Generic

# Prova selector più specifico
"form#login-form input[name='username']"  # Più preciso

# O usa XPath
"//form[@id='login-form']//input[@name='username']"
```

---

### Problema: MCP server non si connette (remote mode)

**Causa:** Server remoto non avviato o porta occupata.

**Soluzione:**
```bash
# 1. Avvia server manualmente
python mcp_servers/playwright_server_remote.py

# 2. Verifica porta disponibile
netstat -an | findstr 8000  # Windows
lsof -i :8000  # Mac/Linux

# 3. Cambia porta se necessario
# config/settings.py
MCPConfig.REMOTE_PORT = 8001
```

---

### Problema: Token limit exceeded (OpenRouter)

**Causa:** `inspect_page_structure` su pagina molto complessa.

**Soluzione:**
- ✅ Usa su pagine specifiche (login, checkout)
- ❌ Evita su dashboard con 100+ elementi
- ✅ Salva output e riusa invece di re-ispezionare

---

## 👥 Per Martina: Setup Veloce

### Quick Start (5 minuti)

```bash
# 1. Clone & Setup
cd ai-test-automation/backend
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
playwright install chromium

# 2. Config API Key
# Crea .env con Azure OpenAI key che ti ho dato
echo "AZURE_OPENAI_API_KEY=la_tua_key" > .env
echo "AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/" >> .env
echo "AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini" >> .env

# 3. Avvia
python app.py

# 4. Test (in altro terminale)
curl -X POST http://localhost:5000/api/agent/mcp/test/run \
  -H "Content-Type: application/json" \
  -d '{"test_description": "Go to google.com and take a screenshot"}'
```

### Test con AMC

```bash
# 1. Aggiungi credenziali AMC in .env
echo "AMC_USERNAME=martina.bertoldi@eng.it" >> .env
echo "AMC_PASSWORD=tua_password" >> .env

# 2. Ispeziona form
curl -X POST http://localhost:5000/api/test/amc/inspect

# 3. Test login
curl -X POST http://localhost:5000/api/test/amc/login
```

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

### Community & Support

- **Issues:** Apri issue su repository Git
- **Slack:** #test-automation channel
- **Contatti:**
  - Serena: serena@eng.it
  - Martina: martina.bertoldi@eng.it

---

## 📝 Changelog

### [2.2.0-inspect] - 2024-12-18

#### 🎉 New Tool: inspect_page_structure

**✨ Features:**
- [x] **Page Inspector** 🔍 - Rileva automaticamente form, input, button
- [x] **Selector Suggestions** - Genera selettori CSS/XPath consigliati
- [x] **Login Form Support** - Ottimizzato per form di autenticazione
- [x] **Debug Helper** - Facilita troubleshooting di test falliti
- [x] **AMC Integration** - Endpoint dedicato `/api/test/amc/inspect`

**🔧 Technical:**
- Nuovo tool `inspect_page_structure()` in `tools.py`
- Esposto via MCP server (locale e remoto)
- Supporto async completo
- JSON output strutturato con suggested selectors
- Performance: ~500-1000 tokens output per pagina media

**📦 Use Cases:**
- Analisi pagine login (es. AMC Ellipse COT)
- Discovery selettori per test automation
- Debug quando selettori CSS cambiano
- Documentazione struttura pagine per team
- Reverse engineering form complessi

**📝 Examples:**
```python
# Test description examples:
"Go to login page and inspect page structure"
"Inspect registration form at https://example.com/signup"
"Find all form fields on checkout page"
```

**🔗 Integration:**
- Works with all LLM providers (OpenAI, Azure, OpenRouter)
- Compatible with existing 11 Playwright tools
- Async/await throughout
- MCP protocol compliant

**📊 Output Structure:**
```json
{
  "page_info": {...},
  "inputs": [{selector_suggestions: [...]}],
  "buttons": [{selector_suggestions: [...]}],
  "forms": [...]
}
```

---

### [2.1.0-async] - 2024-12-15

#### 🎉 Major Update: Full Async + Base64 Screenshots

**✨ Features:**
- [x] **Async Playwright** - Full async/await API
- [x] **Screenshot Base64** - No disk files, memory only
- [x] **OpenRouter Support** ⭐ - Access to Claude, Gemini, etc.
- [x] **Multi-LLM** - OpenAI, Azure, OpenRouter
- [x] **Auto-detection** - LLM provider priority system
- [x] **Response Enhancement** - Screenshots array in JSON

**🔧 Technical:**
- Converted all Playwright tools to `async def`
- `async_playwright()` instead of `sync_playwright()`
- MCP servers return base64 with delimiters
- Flask extracts base64 from AI response via regex
- Zero filesystem I/O for screenshots

---

### [2.0.0-mcp] - 2024-12-10

#### 🎉 Major Release: MCP Integration

**✨ Features:**
- [x] **MCP Architecture** - Model Context Protocol
- [x] **11 Tool Playwright** - Via MCP protocol (now 12!)
- [x] **Dual Mode** - Locale/Remoto switchable
- [x] **LangChain Integration** - via mcp-adapters
- [x] **Async Support** - Non-blocking I/O

---

## 📄 Licenza

MIT License - Vedi LICENSE file per dettagli.

---

**Ultimo aggiornamento:** 18 Dicembre 2024  
**Versione:** 2.2.0-inspect  
**Status:** 🟢 Production Ready (Async + Inspect Edition)

**Maintainers:**
- Serena Celano (serena@eng.it) - Lead Developer
- Martina Bertoldi (martina.bertoldi@eng.it) - Collaborator

---

🚀 **Happy Testing with MCP + Inspect!** 🤖🔍
</parameter>