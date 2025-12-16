# 🤖 AI Test Automation Project (MCP Edition)

Sistema di test automation intelligente che usa **MCP (Model Context Protocol)**, LLM (Large Language Models) e Playwright per automatizzare test di interfacce web con architettura enterprise-ready.

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
- [API Endpoints](#-api-endpoints)
- [Screenshot in Base64](#-screenshot-in-base64)
- [Esempi di Utilizzo](#-esempi-di-utilizzo)
- [MCP: Locale vs Remoto](#-mcp-locale-vs-remoto)
- [Troubleshooting](#-troubleshooting)
- [Per Martina](#-per-martina-setup-veloce)
- [Risorse](#-risorse)

---

## 🎯 Cosa Fa Questo Progetto

Questo sistema permette di:
- ✅ Descrivere test in **linguaggio naturale** (es. "vai su google.com e cerca 'test automation'")
- ✅ **AI Agent** (GPT-4, Claude, etc.) capisce il test e lo esegue automaticamente
- ✅ **MCP Protocol** gestisce i tool in modo isolato e scalabile
- ✅ **Playwright Async** controlla il browser (clicca, compila form, naviga)
- ✅ **Screenshot Base64** ritornati direttamente nella risposta JSON
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
│  - Exposes 11 async tools                   │
│  - Isolated process                         │
│  - Returns base64 screenshots               │
└──────────────────┬──────────────────────────┘
                   │ Async call
                   ▼
┌─────────────────────────────────────────────┐
│         Playwright Async (Chromium)         │
│  - Browser automation (async API)           │
│  - In-memory screenshots                    │
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
│   ├── agent/                        # AI Agent modules
│   │   ├── __init__.py
│   │   ├── tools.py                  # ⭐ Playwright tools ASYNC (base)
│   │   └── test_agent_mcp.py        # ⭐ Agent con MCP (multi-LLM)
│   │
│   └── mcp_servers/                  # ⭐ MCP Servers ASYNC
│       ├── __init__.py
│       ├── playwright_server_local.py    # Server locale (stdio) ASYNC
│       └── playwright_server_remote.py   # Server remoto (HTTP) ASYNC
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
🟣 Usando OpenRouter
   Model: anthropic/claude-3.5-sonnet

💻 Usando MCP Server LOCALE (stdio)
✅ AI Agent MCP caricato con successo!

==================================================
🤖 AI TEST AUTOMATION SERVER (MCP Edition)
==================================================
URL: http://localhost:5000

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
   - POST /api/agent/mcp/test/run    → Esegui test con AI+MCP
   - GET  /api/agent/mcp/test/stream → Stream real-time
   - GET  /api/mcp/info              → Info configurazione MCP

   💡 MCP Mode: Locale (stdio) di default
   💡 Screenshots ritornati in base64 (no disk files)

==================================================
Premi CTRL+C per fermare il server
==================================================
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
  "timestamp": "2024-12-15T..."
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

Il sistema espone **11 tool async** tramite MCP Server:

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

---

### 5. `wait_for_element(selector: str, state: str = "visible", selector_type: str = "css", timeout: int = 30000)` ⭐

**FONDAMENTALE per AJAX!** Aspetta che elemento appaia/scompaia (async).

**States:**
- `"visible"` - Elemento visibile
- `"hidden"` - Elemento nascosto
- `"attached"` - Nel DOM
- `"detached"` - Rimosso dal DOM

---

### 6-11. Altri Tool

- `get_text()` - Estrae testo
- `check_element_exists()` - Verifica esistenza
- `press_key()` - Simula tasto
- `capture_screenshot()` ⭐ - **Ritorna base64**
- `close_browser()` - Chiude browser
- `get_page_info()` - Info pagina

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

### AI Agent MCP Endpoints

#### `POST /api/agent/mcp/test/run`
Esegue test con AI Agent tramite MCP.

**Body:**
```json
{
  "test_description": "Go to google.com and search for 'AI testing'",
  "use_remote": false
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
  "screenshots": [
    {
      "filename": "screenshot_1.png",
      "base64": "iVBORw0KGgo...",
      "size_bytes": 245678,
      "source": "ai_agent_response"
    }
  ],
  "screenshots_count": 1,
  "timestamp": "2024-12-15T..."
}
```

---

## 💡 Esempi di Utilizzo

### Esempio 1: Test con Screenshot Base64

```bash
curl -X POST http://localhost:5000/api/agent/mcp/test/run \
  -H "Content-Type: application/json" \
  -d '{
    "test_description": "Go to google.com, take a screenshot, and close the browser"
  }' | jq '.screenshots[0].base64' > screenshot.b64

# Decodifica base64 e salva
base64 -d screenshot.b64 > screenshot.png
```

---

### Esempio 2: Test con OpenRouter + Claude

```bash
# .env configurato con OpenRouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Esegui test
curl -X POST http://localhost:5000/api/agent/mcp/test/run \
  -H "Content-Type: application/json" \
  -d '{"test_description": "Complex test with AJAX..."}'

# Claude interpreta e esegue il test
```

---

## 🐛 Troubleshooting

### Problema: Screenshot count = 0

**Causa:** Base64 non estratto correttamente dalla risposta AI.

**Soluzione:**
1. Verifica che `tools.py` usa **async Playwright**
2. Verifica che MCP server ritorna base64 con marker `🔑 SCREENSHOT_BASE64_START`
3. Verifica che `app.py` estrae con regex corretta

---

### Problema: AsyncIO errors

**Causa:** Mixing sync/async code.

**Soluzione:**
- Usa **async Playwright** (`from playwright.async_api import async_playwright`)
- Tutti i tool devono essere `async def`
- Tutti i MCP server tool devono essere `async`

---

## 📝 Changelog

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

**📦 Dependencies:** (no changes)
- Same as 2.0.0-mcp

---

### [2.0.0-mcp] - 2024-12-10

#### 🎉 Major Release: MCP Integration

**✨ Features:**
- [x] **MCP Architecture** - Model Context Protocol
- [x] **12 Tool Playwright** - Via MCP protocol
- [x] **Dual Mode** - Locale/Remoto switchable
---

## 📄 Licenza
---

**Ultimo aggiornamento:** 15 Dicembre 2024  
**Versione:** 2.1.0-async  
**Status:** 🟢 Production Ready (Async Edition)

**Contatti:**
- Serena (serena@eng.it)
- Martina (martina.bertoldi@eng.it)

---

🚀 **Happy Testing with Async MCP!** 🤖