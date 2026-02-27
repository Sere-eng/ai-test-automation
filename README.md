# AI Test Automation con LLM, MCP e Playwright

Sistema di **test automation intelligente** che usa:
- **LLM (GPT-4o, Claude, Gemini, …)** per capire test scritti in linguaggio naturale
- **MCP (Model Context Protocol)** per orchestrare tool esterni in modo sicuro
- **Playwright (async)** per pilotare il browser su **app enterprise Angular**

L'obiettivo è avere un **tester virtuale** che, dato un requisito funzionale in italiano/inglese, sia in grado di:
1. capire cosa fare
2. navigare l'applicazione web
3. eseguire i passi UI
4. verificare i risultati attesi
5. restituire un report strutturato (JSON + screenshot)

---

## Cosa fa questo progetto

**Automazione guidata da linguaggio naturale**

Esempio:
> "Avvia il browser, fai login su LAB, seleziona *organizzazione di sistema*, apri *Laboratory* e crea un nuovo filtro salvato."

**Automazione su app enterprise reale**

Sistemi AMC / LAB con login SSO, iframe, componenti Angular Material, dashboard con contatori, filtri e card KPI. Scenari concreti:
- creazione e salvataggio filtri
- navigazione tramite contatori
- elenco campioni e pagina dettaglio

**Best practice anti-allucinazioni**

- Discovery-first: prima `inspect_interactive_elements`, poi `click_smart` / `fill_smart`
- Niente selettori indovinati (`#username` & co.)
- Regole di system prompt rigide per gestione errori, uso corretto dei tool, divieto di stringhe generiche nei check (es. `"home"`, `"dashboard"`)

---

## Architettura

```
User / Tester
   │
   │  HTTP JSON { test_description }
   ▼
Flask API
   │
   ▼
Orchestrator (orchestrator.py)
   ├── Prefix Agent  → login → selezione org → tile Laboratory  (browser rimane aperto)
   └── Scenario Agent → esegue lo scenario LAB dalla dashboard  (chiude il browser)
         │
         │  LangGraph ReAct
         ▼
   LLM (OpenRouter / OpenAI / Azure)
         │
         │  MCP Protocol
         ▼
   MCP Client (langchain-mcp-adapters)
         │
         │  stdio | HTTP
         ▼
   MCP Server Playwright (async)
   21 tool: start_browser, navigate_to_url, inspect_interactive_elements,
            click_smart, fill_smart, wait_for_dom_change, inspect_region, …
         │
         ▼
   Chromium
         │
         ▼
JSON response + screenshot
```

Pass/fail deciso da `evaluation.py` sui tool results — non dall'output testuale del modello.

---

## Documentazione

| File | Contenuto |
|------|-----------|
| [`backend/README.md`](backend/README.md) | Setup, configurazione, API endpoints, riferimento completo ai tool |
| [`backend/agent/TOOLS.md`](backend/agent/TOOLS.md) | Guida operativa ai 21 tool Playwright MCP: input/output, pattern d'uso |
