# 🤖 AI Test Automation Project

Sistema di test automation intelligente che usa LLM (Large Language Models) e Playwright per automatizzare test di interfacce web.

---

## 📋 Indice

- [Cosa Fa Questo Progetto](#cosa-fa-questo-progetto)
- [Tecnologie Utilizzate](#tecnologie-utilizzate)
- [Struttura del Progetto](#struttura-del-progetto)
- [Setup Iniziale](#setup-iniziale)
- [Tool Playwright Implementati](#tool-playwright-implementati)
- [API Endpoints Disponibili](#api-endpoints-disponibili)
- [Come Usare il Sistema](#come-usare-il-sistema)
- [Prossimi Step](#prossimi-step)

---

## 🎯 Cosa Fa Questo Progetto

Questo sistema permette di:
- ✅ Descrivere test in **linguaggio naturale** (es. "vai su google.com e cerca 'test automation'")
- ✅ L'**AI Agent** capisce il test e lo esegue automaticamente
- ✅ **Playwright** controlla il browser (clicca, compila form, naviga)
- ✅ **Vision AI** analizza screenshot per verificare i risultati
- ✅ Genera **report automatici** dei test eseguiti

### Esempio di Utilizzo

```
Input: "Vai su https://example.com, clicca su Login, 
        inserisci email test@test.com e password 123, 
        poi verifica che appaia il messaggio di benvenuto"

Output: ✅ Test PASSED
        - Navigato a https://example.com
        - Cliccato su bottone Login
        - Compilati campi email e password
        - Verificato messaggio "Benvenuto, test@test.com"
        - Screenshot salvato
```

---

## 🛠️ Tecnologie Utilizzate

### Backend (Python)
- **Python 3.12.10** - Linguaggio principale
- **Flask 3.1.2** - Framework web per API REST
- **Playwright** - Automazione browser
- **LangChain** - Framework per LLM Agent (coming soon)
- **LangGraph** - Orchestrazione workflow (coming soon)

### Frontend (Angular)
- **Angular 18+** - Framework frontend (coming soon)
- **TypeScript** - Linguaggio per Angular
- **Material UI** - Componenti UI

### AI/LLM
- **OpenAI GPT-4** - LLM principale per l'agent
- **GPT-4 Vision** - Analisi screenshot

---

## 📁 Struttura del Progetto

```
ai-test-automation/
│
├── backend/                    # Backend Python
│   ├── venv/                  # Ambiente virtuale Python
│   ├── .gitignore
│   ├── .env.example
│   ├── README.md
│   ├── app.py                 # Server Flask principale
│   ├── .env                   # Variabili d'ambiente (API keys)
│   ├── requirements.txt       # Dipendenze Python
│   │
│   ├── agent/                 # Moduli per AI Agent
│   │   ├── test_agent.py     # Agent LLM principale
│   │   ├── tools.py          # Tool per Playwright (IMPLEMENTATI!)
│   │   └── evaluator.py      # Valutazione risultati
│   │
│   └── tests/                 # Test cases
│       └── test_cases.json   # Dataset di test
│
└── frontend/                  # Frontend Angular
    └── (coming soon)
```

---

## 🚀 Setup Iniziale

### Prerequisiti

- **Python 3.10+** installato ([Download Python](https://www.python.org/downloads/))
- **Node.js 18+** per Angular (coming soon)
- **Git** per version control

### Step 1: Clona il Repository

```bash
git clone <repository-url>
cd ai-test-automation
```

### Step 2: Setup Backend Python

```bash
# Vai nella cartella backend
cd backend

# Crea ambiente virtuale
python -m venv venv

# Attiva ambiente virtuale
# Su Windows:
.\venv\Scripts\Activate
# Su Mac/Linux:
source venv/bin/activate

# Aggiorna pip
python -m pip install --upgrade pip

# Installa dipendenze
python -m pip install python-dotenv flask flask-cors playwright

# Installa browser Chromium per Playwright
playwright install chromium
```

### Step 3: Configura Variabili d'Ambiente

Crea un file `.env` nella cartella `backend/`:

```bash
# backend/.env
OPENAI_API_KEY=your_openai_api_key_here
FLASK_ENV=development
FLASK_DEBUG=True
```

> ⚠️ **IMPORTANTE:** Non committare mai il file `.env` su Git! Aggiungi `.env` al `.gitignore`.

### Step 4: Avvia il Server

```bash
# Assicurati di essere in backend/ con venv attivo
python app.py
```

Dovresti vedere:
```
==================================================
SERVER AI TEST AUTOMATION
==================================================
URL: http://localhost:5000
Endpoints disponibili:
   [Esistenti]
   - GET  /
   - GET  /api/health
   - GET  /api/test
   
   [Playwright - Browser Control]
   - POST /api/browser/start
   - POST /api/browser/navigate
   - GET  /api/browser/screenshot
   - GET  /api/browser/info
   - POST /api/browser/close
   
   [Playwright - Advanced Tools]
   - POST /api/browser/click
   - POST /api/browser/fill
   - POST /api/browser/wait
   - POST /api/browser/get-text
   - POST /api/browser/check-exists
   - POST /api/browser/press-key
==================================================
```

---

## 🛠️ Tool Playwright Implementati

Il sistema include una suite completa di tool per automatizzare interazioni con il browser.

### Tool Base

#### 1. `start_browser(headless=False)`
Avvia il browser Chromium con configurazioni ottimizzate.

**Parametri:**
- `headless`: Se `True`, browser invisibile. Se `False`, vedi il browser aprirsi.

**Esempio:**
```python
playwright_tools.start_browser(headless=False)  # Vedi il browser
```

---

#### 2. `navigate_to_url(url)`
Naviga a un URL specifico e aspetta il caricamento completo.

**Esempio:**
```python
playwright_tools.navigate_to_url("https://google.com")
```

---

#### 3. `capture_screenshot(filename=None)`
Cattura screenshot full-page della pagina corrente.

**Esempio:**
```python
playwright_tools.capture_screenshot("test-result.png")
```

---

#### 4. `close_browser()`
Chiude il browser e libera le risorse.

---

### Tool Avanzati ⭐

#### 5. `click_element(selector, selector_type="css", timeout=30000)`
Clicca su qualsiasi elemento della pagina.

**Parametri:**
- `selector`: Selettore dell'elemento
- `selector_type`: `"css"`, `"xpath"`, o `"text"`
- `timeout`: Tempo massimo di attesa in millisecondi

**Esempi:**
```python
# Click con CSS selector
click_element("#login-button", "css")

# Click cercando per testo visibile
click_element("Accedi", "text")

# Click con XPath
click_element("//button[@type='submit']", "xpath")
```

---

#### 6. `fill_input(selector, value, selector_type="css", clear_first=True)`
Compila campi input con testo.

**Parametri:**
- `selector`: Selettore del campo
- `value`: Testo da inserire
- `selector_type`: `"css"`, `"xpath"`, o `"placeholder"`
- `clear_first`: Se `True`, cancella il contenuto prima

**Esempi:**
```python
# Compila email
fill_input("#email", "test@example.com")

# Compila cercando per placeholder
fill_input("Inserisci password", "MyPass123", "placeholder")

# Aggiungi testo senza cancellare
fill_input("#notes", " - nota aggiuntiva", clear_first=False)
```

---

#### 7. `wait_for_element(selector, selector_type="css", state="visible", timeout=30000)`
Aspetta che un elemento appaia/scompaia. **FONDAMENTALE per caricamenti AJAX!**

**Parametri:**
- `state`: `"visible"`, `"hidden"`, `"attached"`, `"detached"`

**Esempi:**
```python
# Aspetta che appaia un messaggio
wait_for_element(".success-message", state="visible")

# Aspetta che scompaia lo spinner di caricamento
wait_for_element(".loading-spinner", state="hidden")
```

**💡 Quando usarlo:**
- Dopo click su bottoni che caricano dati (AJAX)
- Prima di leggere risultati di operazioni asincrone
- Quando aspetti che modali/popup appaiano o scompaiano

---

#### 8. `get_text(selector, selector_type="css")`
Estrae il testo visibile da un elemento.

**Esempi:**
```python
# Leggi messaggio di errore
result = get_text(".error-message")
print(result["text"])  # "Email non valida"

# Leggi titolo
result = get_text("h1")
```

---

#### 9. `check_element_exists(selector, selector_type="css")`
Verifica se un elemento esiste ed è visibile.

**Ritorna:**
```json
{
    "status": "success",
    "exists": true,
    "is_visible": true
}
```

**Esempi:**
```python
# Verifica presenza di errore
result = check_element_exists(".error-message")
if result["exists"]:
    print("❌ Test FAILED: c'è un errore")

# Verifica successo login
result = check_element_exists(".user-dashboard")
if result["exists"] and result["is_visible"]:
    print("✅ Login SUCCESS")
```

---

#### 10. `press_key(key)`
Simula pressione di tasti speciali.

**Tasti comuni:**
- `"Enter"` - Invio form
- `"Escape"` - Chiude modali
- `"Tab"` - Naviga tra campi
- `"ArrowDown"`, `"ArrowUp"` - Naviga dropdown
- `"Control+A"` - Seleziona tutto

**Esempi:**
```python
# Invio form con Enter
fill_input("#search", "test automation")
press_key("Enter")

# Chiudi modale
press_key("Escape")
```

---

## 🌐 API Endpoints Disponibili

### Endpoint Base

#### `GET /`
Health check del server.

#### `GET /api/health`
Status del servizio.

---

### Endpoint Browser Control

#### `POST /api/browser/start`
Avvia il browser.

**Body:**
```json
{
    "headless": false
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Browser avviato con successo"
}
```

---

#### `POST /api/browser/navigate`
Naviga a un URL.

**Body:**
```json
{
    "url": "https://google.com"
}
```

**Response:**
```json
{
    "status": "success",
    "url": "https://google.com",
    "page_title": "Google"
}
```

---

#### `GET /api/browser/screenshot`
Cattura screenshot.

**Response:**
```json
{
    "status": "success",
    "filename": "screenshot_20241210_143022.png",
    "screenshot": "base64_encoded_image...",
    "size_bytes": 245678
}
```

---

#### `POST /api/browser/close`
Chiude il browser.

---

### Endpoint Tool Avanzati (DA IMPLEMENTARE)

> ⚠️ **Nota:** Questi endpoint vanno ancora aggiunti in `app.py`

#### `POST /api/browser/click`
Clicca su un elemento.

**Body:**
```json
{
    "selector": "#login-button",
    "selector_type": "css",
    "timeout": 30000
}
```

---

#### `POST /api/browser/fill`
Compila un campo input.

**Body:**
```json
{
    "selector": "#email",
    "value": "test@test.com",
    "selector_type": "css",
    "clear_first": true
}
```

---

#### `POST /api/browser/wait`
Aspetta un elemento.

**Body:**
```json
{
    "selector": ".success-message",
    "selector_type": "css",
    "state": "visible",
    "timeout": 30000
}
```

---

#### `POST /api/browser/get-text`
Estrae testo da un elemento.

**Body:**
```json
{
    "selector": ".user-name",
    "selector_type": "css"
}
```

---

#### `POST /api/browser/check-exists`
Verifica esistenza elemento.

**Body:**
```json
{
    "selector": ".error-message",
    "selector_type": "css"
}
```

---

#### `POST /api/browser/press-key`
Simula pressione tasto.

**Body:**
```json
{
    "key": "Enter"
}
```

---

## 🧪 Come Usare il Sistema

### Test Manuale con cURL

```bash
# 1. Avvia il browser
curl -X POST http://localhost:5000/api/browser/start \
  -H "Content-Type: application/json" \
  -d '{"headless": false}'

# 2. Naviga a Google
curl -X POST http://localhost:5000/api/browser/navigate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://google.com"}'

# 3. Cattura screenshot
curl http://localhost:5000/api/browser/screenshot

# 4. Chiudi browser
curl -X POST http://localhost:5000/api/browser/close
```

---

### Esempio: Test di Login Completo

```python
from agent.tools import PlaywrightTools

tools = PlaywrightTools()

# 1. Setup
tools.start_browser(headless=False)
tools.navigate_to_url("https://example.com/login")

# 2. Compila form
tools.fill_input("#email", "test@test.com")
tools.fill_input("#password", "Password123")

# 3. Submit
tools.click_element("#login-button", "css")

# 4. Aspetta caricamento (AJAX)
tools.wait_for_element(".loading-spinner", state="visible")
tools.wait_for_element(".loading-spinner", state="hidden")

# 5. Verifica successo
result = tools.check_element_exists(".user-dashboard")

if result["exists"] and result["is_visible"]:
    print("✅ Login SUCCESS!")
    user_name = tools.get_text(".user-name")
    print(f"Benvenuto, {user_name['text']}")
else:
    print("❌ Login FAILED")
    error = tools.get_text(".error-message")
    print(f"Errore: {error['text']}")

# 6. Screenshot e cleanup
tools.capture_screenshot("login-test-result.png")
tools.close_browser()
```

---

## 📚 Comandi Utili

### Backend

```bash
# Attiva ambiente virtuale
.\venv\Scripts\Activate  # Windows
source venv/bin/activate  # Mac/Linux

# Installa nuova dipendenza
python -m pip install <package-name>

# Salva dipendenze
python -m pip freeze > requirements.txt

# Avvia server
python app.py

# Disattiva ambiente virtuale
deactivate
```

### Playwright

```bash
# Installa tutti i browser
playwright install

# Installa solo Chromium
playwright install chromium

# Esegui test Playwright
pytest
```

---

## 🔍 Cos'è AJAX e Perché è Importante

**AJAX** (Asynchronous JavaScript And XML) = Caricamento dati in background senza ricaricare la pagina.

### Esempi Quotidiani di AJAX:
- 📱 Facebook feed che carica nuovi post quando scrolli
- 🗺️ Google Maps che carica nuove zone quando sposti la mappa
- 📧 Gmail che mostra email senza cambiare pagina
- 🔍 Suggerimenti di ricerca mentre digiti

### Perché è Cruciale nei Test?

**Problema:** Il browser esegue azioni più veloce di quanto i dati arrivino dal server.

```python
# ❌ SBAGLIATO - Test fallisce!
click_element("#load-data")
get_text("#result")  # ERRORE: dati non ancora caricati!

# ✅ CORRETTO - Aspetta AJAX
click_element("#load-data")
wait_for_element("#result", state="visible", timeout=5000)
get_text("#result")  # OK: dati pronti
```

### Pattern Comuni:

#### 1. Spinner Pattern
```python
click_element("#submit")
wait_for_element(".loading-spinner", state="visible")   # Appare
wait_for_element(".loading-spinner", state="hidden")    # Scompare
wait_for_element(".success-message", state="visible")   # Risultato pronto
```

#### 2. Button Disabled Pattern
```python
click_element("#submit")
wait_for_element("#submit[disabled]")          # Bottone disabilitato
wait_for_element("#submit:not([disabled])")    # Bottone riabilitato
```

---

## 🔜 Prossimi Step

### Step 2: Endpoint API per Tool Avanzati ✅ (IN PROGRESS)
- [ ] Implementare endpoint `/api/browser/click`
- [ ] Implementare endpoint `/api/browser/fill`
- [ ] Implementare endpoint `/api/browser/wait`
- [ ] Implementare endpoint `/api/browser/get-text`
- [ ] Implementare endpoint `/api/browser/check-exists`
- [ ] Implementare endpoint `/api/browser/press-key`
- [ ] Test manuali con cURL/Postman

### Step 3: Creare l'AI Agent con LangChain (PLANNED)
- [ ] Setup LangChain + LangGraph
- [ ] Configurazione OpenAI API
- [ ] Definire tool per l'agent
- [ ] Agent con ReAct pattern
- [ ] Test agent con linguaggio naturale
- [ ] Esempi: "vai su google e cerca X"

### Step 4: Integrare Vision AI (PLANNED)
- [ ] Integrazione GPT-4 Vision
- [ ] Screenshot analysis
- [ ] Confronto expected vs actual
- [ ] Validazione automatica risultati
- [ ] Report visuale con annotazioni

### Step 5: Frontend Angular (PLANNED)
- [ ] Setup Angular project
- [ ] Dashboard UI
- [ ] API service per backend
- [ ] Test runner component
- [ ] Results viewer
- [ ] Test case creator

### Step 6: Tool Avanzati Extra (FUTURE)
- [ ] Database query tool
- [ ] API call tool
- [ ] Visual regression tool
- [ ] Performance monitoring tool
- [ ] Test data generator
- [ ] Multi-browser testing

---

## 🐛 Troubleshooting

### Problema: `pip` non funziona

**Soluzione:** Usa `python -m pip` invece di `pip`
```bash
python -m pip install <package>
```

### Problema: Server non si avvia

**Soluzione:** Verifica che la porta 5000 sia libera
```bash
# Windows
netstat -ano | findstr :5000

# Mac/Linux
lsof -i :5000
```

### Problema: Playwright non trova i browser

**Soluzione:** Reinstalla i browser
```bash
playwright install chromium --force
```

### Problema: Test fallisce con AJAX

**Soluzione:** Aggiungi `wait_for_element()` dopo ogni azione che carica dati
```python
click_element("#button")
wait_for_element(".result", state="visible", timeout=10000)
```

---

## 📖 Risorse Utili

### Documentazione

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Playwright Python](https://playwright.dev/python/)
- [LangChain Docs](https://python.langchain.com/)
- [OpenAI API](https://platform.openai.com/docs/)

### Tutorial

- [Playwright Tutorial](https://playwright.dev/python/docs/intro)
- [Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world)
- [LangChain Quickstart](https://python.langchain.com/docs/get_started/quickstart)

---

## 🤝 Contribuire

Questo è un progetto educativo in fase di sviluppo. 

### Workflow di Sviluppo

1. Ogni step viene implementato gradualmente
2. Testiamo ogni componente prima di procedere
3. Documentiamo ogni decisione tecnica
4. Committiamo spesso con messaggi descrittivi

---

## 📝 Changelog

### [0.2.0] - 2024-12-10

#### ✅ Tool Avanzati Implementati
- [x] `click_element()` - Click su elementi con CSS/XPath/Text
- [x] `fill_input()` - Compilazione campi input
- [x] `wait_for_element()` - Gestione caricamenti AJAX
- [x] `get_text()` - Estrazione testo da elementi
- [x] `check_element_exists()` - Verifica esistenza elementi
- [x] `press_key()` - Simulazione pressione tasti
- [x] Documentazione completa tool avanzati
- [x] Esempi pratici di utilizzo
- [x] Spiegazione AJAX e pattern comuni

#### 🔄 In Progress
- [ ] Endpoint API per tool avanzati

### [0.1.0] - 2024-12-10

#### ✅ Setup Base Completato
- [x] Setup ambiente Python
- [x] Installazione Flask
- [x] Creazione API REST base
- [x] Installazione Playwright
- [x] Test endpoint funzionanti
- [x] Tool base browser control

---

**Ultimo aggiornamento:** 10 Dicembre 2024  
**Versione:** 0.1.0  
**Status:** 🟢 In Development - Tool Avanzati Implementati